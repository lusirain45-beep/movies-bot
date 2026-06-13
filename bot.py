import telebot
import requests
import sqlite3
import os
import google.generativeai as genai
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
TMDB_KEY = os.environ.get("TMDB_KEY")
YOUTUBE_KEY = os.environ.get("YOUTUBE_KEY")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
SUBDL_KEY = os.environ.get("SUBDL_KEY")

ADMINS = [6154627247, 7451435181]
OWNER = 6154627247

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

user_mode = {}

# ═══════════════════════════════════════
#           قاعدة البيانات
# ═══════════════════════════════════════
def init_db():
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, name TEXT, joined TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                 (user_id INTEGER, item_id INTEGER, title TEXT, media_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ai_usage
                 (user_id INTEGER, date TEXT, count INTEGER,
                 PRIMARY KEY (user_id, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (user_id INTEGER, action TEXT, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_user(message):
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
        (message.from_user.id,
         message.from_user.username or "",
         message.from_user.first_name or "",
         str(datetime.now())))
    conn.commit()
    conn.close()

def log_action(user_id, action):
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("INSERT INTO stats VALUES (?,?,?)",
        (user_id, action, str(datetime.now())))
    conn.commit()
    conn.close()

def check_ai_limit(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("SELECT count FROM ai_usage WHERE user_id=? AND date=?", (user_id, today))
    row = c.fetchone()
    conn.close()
    if row is None:
        return True
    return row[0] < 10

def increment_ai_usage(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("INSERT INTO ai_usage VALUES (?,?,1) ON CONFLICT(user_id,date) DO UPDATE SET count=count+1",
        (user_id, today))
    conn.commit()
    conn.close()

def get_ai_remaining(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("SELECT count FROM ai_usage WHERE user_id=? AND date=?", (user_id, today))
    row = c.fetchone()
    conn.close()
    used = row[0] if row else 0
    return 10 - used

# ═══════════════════════════════════════
#           الأزرار السفلية
# ═══════════════════════════════════════
def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🎬 أفلام"), KeyboardButton("📺 مسلسلات"), KeyboardButton("🎌 أنمي"))
    markup.row(KeyboardButton("🔍 بحث"), KeyboardButton("🤖 AI"), KeyboardButton("📋 قائمتي"))
    return markup

def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🎬 أفلام"), KeyboardButton("📺 مسلسلات"), KeyboardButton("🎌 أنمي"))
    markup.row(KeyboardButton("🔍 بحث"), KeyboardButton("🤖 AI"), KeyboardButton("📋 قائمتي"))
    markup.row(KeyboardButton("📊 إحصائيات"), KeyboardButton("📢 broadcast"))
    return markup

# ═══════════════════════════════════════
#              START
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message)
    user_mode[message.chat.id] = "search"
    
    keyboard = admin_keyboard() if message.from_user.id in ADMINS else main_keyboard()
    
    bot.send_message(message.chat.id,
        "📽️ *Welcome to Cinema!*\n\nاكتب اسم فيلم أو مسلسل أو أنمي:",
        reply_markup=keyboard, parse_mode='Markdown')

# ═══════════════════════════════════════
#           الإحصائيات
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات")
def stats(message):
    if message.from_user.id not in ADMINS:
        return
    
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(DISTINCT user_id) FROM stats WHERE date LIKE ?", (f"{today}%",))
    active_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM stats WHERE action='search'")
    total_searches = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM stats WHERE action='torrent'")
    total_torrents = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM stats WHERE action='ai'")
    total_ai = c.fetchone()[0]
    
    c.execute("SELECT name, username FROM users ORDER BY joined DESC LIMIT 5")
    last_users = c.fetchall()
    
    conn.close()
    
    text = (
        f"📊 *إحصائيات Cinema*\n\n"
        f"👥 إجمالي المستخدمين: `{total_users}`\n"
        f"🟢 نشطين اليوم: `{active_today}`\n"
        f"🔍 إجمالي البحث: `{total_searches}`\n"
        f"⬇️ إجمالي التورنت: `{total_torrents}`\n"
        f"🤖 إجمالي AI: `{total_ai}`\n\n"
        f"*آخر 5 مستخدمين:*\n"
    )
    for u in last_users:
        text += f"• {u[0]} {'@'+u[1] if u[1] else ''}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ═══════════════════════════════════════
#           Broadcast
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📢 broadcast")
def broadcast_start(message):
    if message.from_user.id != OWNER:
        return
    user_mode[message.chat.id] = "broadcast"
    bot.send_message(message.chat.id, "📢 اكتب الرسالة اللي تبي ترسلها لكل المستخدمين:")

def do_broadcast(message, text):
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    success = 0
    fail = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 *إشعار من Cinema:*\n\n{text}", parse_mode='Markdown')
            success += 1
        except:
            fail += 1
    
    bot.send_message(message.chat.id, f"✅ تم الإرسال!\n\n📨 نجح: {success}\n❌ فشل: {fail}")

# ═══════════════════════════════════════
#           معالج الرسائل
# ═══════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    save_user(message)
    chat_id = message.chat.id
    text = message.text
    mode = user_mode.get(chat_id, "search")

    if mode == "broadcast" and message.from_user.id == OWNER:
        user_mode[chat_id] = "search"
        do_broadcast(message, text)
    elif mode == "ai":
        user_mode[chat_id] = "search"
        if not check_ai_limit(message.from_user.id):
            bot.send_message(chat_id, "❌ وصلت الحد اليومي للـ AI (10 استخدامات)\nيتجدد بكره ✅")
            return
        increment_ai_usage(message.from_user.id)
        log_action(message.from_user.id, "ai")
        ai_recommend(chat_id, text)
    elif text == "🎬 أفلام":
        movies_menu(chat_id)
    elif text == "📺 مسلسلات":
        tv_menu(chat_id)
    elif text == "🎌 أنمي":
        anime_menu(chat_id)
    elif text == "🤖 AI":
        remaining = get_ai_remaining(message.from_user.id)
        user_mode[chat_id] = "ai"
        bot.send_message(chat_id, f"🤖 اكتب لي وش تبي تشوف وأوصي لك!\n\n⚡ متبقي: {remaining}/10 استخدامات اليوم")
    elif text == "📋 قائمتي":
        show_watchlist(chat_id, message.from_user.id)
    elif text == "🔍 بحث":
        user_mode[chat_id] = "search"
        bot.send_message(chat_id, "🔍 اكتب اسم الفيلم أو المسلسل:")
    else:
        log_action(message.from_user.id, "search")
        search_all(chat_id, text)

# ═══════════════════════════════════════
#           القوائم
# ═══════════════════════════════════════
def movies_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 الرائجة", callback_data="trending_movie"),
        InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data="toprated_movie")
    )
    markup.row(
        InlineKeyboardButton("🎭 حسب النوع", callback_data="genres_movie"),
        InlineKeyboardButton("📅 قادمة قريباً", callback_data="upcoming_movie")
    )
    bot.send_message(chat_id, "🎬 *قسم الأفلام:*", reply_markup=markup, parse_mode='Markdown')

def tv_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 الرائجة", callback_data="trending_tv"),
        InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data="toprated_tv")
    )
    markup.row(
        InlineKeyboardButton("🎭 حسب النوع", callback_data="genres_tv"),
        InlineKeyboardButton("📡 تعرض الآن", callback_data="onair_tv")
    )
    bot.send_message(chat_id, "📺 *قسم المسلسلات:*", reply_markup=markup, parse_mode='Markdown')

def anime_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 الرائجة", callback_data="trending_anime"),
        InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data="toprated_anime")
    )
    markup.row(
        InlineKeyboardButton("🎭 حسب النوع", callback_data="genres_anime"),
        InlineKeyboardButton("📡 يعرض الآن", callback_data="onair_anime")
    )
    bot.send_message(chat_id, "🎌 *قسم الأنمي:*", reply_markup=markup, parse_mode='Markdown')

# ═══════════════════════════════════════
#           البحث
# ═══════════════════════════════════════
def search_all(chat_id, query):
    bot.send_message(chat_id, f"🔍 Searching: {query}...")

    movies = search_tmdb(query, "movie")
    tvs = search_tmdb(query, "tv")

    if not movies and not tvs:
        try:
            response = model.generate_content(f"Translate to English, return ONLY the name: {query}")
            english = response.text.strip()
            movies = search_tmdb(english, "movie")
            tvs = search_tmdb(english, "tv")
        except:
            pass

    if not movies and not tvs:
        bot.send_message(chat_id, "❌ No results found!")
        return

    markup = InlineKeyboardMarkup()
    if movies:
        for m in movies[:3]:
            markup.add(InlineKeyboardButton(
                f"🎬 {m['title']} ({m.get('release_date', '')[:4]})",
                callback_data=f"movie_{m['id']}"
            ))
    if tvs:
        for t in tvs[:3]:
            markup.add(InlineKeyboardButton(
                f"📺 {t['name']} ({t.get('first_air_date', '')[:4]})",
                callback_data=f"tv_{t['id']}"
            ))
    bot.send_message(chat_id, "اختار:", reply_markup=markup)

def search_tmdb(query, media_type):
    try:
        url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_KEY}&query={query}"
        return requests.get(url).json().get('results', [])
    except:
        return []

# ═══════════════════════════════════════
#           AI
# ═══════════════════════════════════════
def ai_recommend(chat_id, query):
    bot.send_message(chat_id, "🤖 AI يفكر...")
    try:
        response = model.generate_content(
            f"""وصي بـ 4 أفلام أو مسلسلات أو أنمي بناءً على: "{query}"
            رد بهذا الشكل فقط:
            اسم|سنة|movie
            اسم|سنة|tv"""
        )
        lines = response.text.strip().split('\n')
        markup = InlineKeyboardMarkup()
        text = "🤖 *AI يوصي لك:*\n\n"
        for line in lines:
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    title = parts[0].strip()
                    year = parts[1].strip()
                    mtype = parts[2].strip()
                    results = search_tmdb(title, mtype)
                    if results:
                        item = results[0]
                        icon = "🎬" if mtype == "movie" else "📺"
                        name = item.get('title') or item.get('name', title)
                        text += f"{icon} {name} ({year})\n"
                        markup.add(InlineKeyboardButton(
                            f"{icon} {name}",
                            callback_data=f"{mtype}_{item['id']}"
                        ))
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

# ═══════════════════════════════════════
#           تفاصيل الفيلم
# ═══════════════════════════════════════
def show_movie(chat_id, movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}&append_to_response=credits"
    data = requests.get(url).json()

    title = data.get('title', '')
    year = data.get('release_date', '')[:4]
    rating = data.get('vote_average', 0)
    overview = data.get('overview', '')
    poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"
    genres = ", ".join([g['name'] for g in data.get('genres', [])])
    director = next((c['name'] for c in data.get('credits', {}).get('crew', []) if c['job'] == 'Director'), 'Unknown')

    try:
        ai_summary = model.generate_content(f"ملخص ممتع بالعربي بسطرين للفيلم: {title}").text.strip()
    except:
        ai_summary = overview[:200]

    caption = (
        f"🎬 *{title}* ({year})\n"
        f"⭐ {round(rating, 1)}/10\n"
        f"🎭 {genres}\n"
        f"🎬 المخرج: {director}\n\n"
        f"📖 {ai_summary}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⬇️ تورنت", callback_data=f"torrent_movie_{movie_id}_{title}"),
        InlineKeyboardButton("🗣 ترجمة", callback_data=f"subtitle_{movie_id}_{title}_movie")
    )
    markup.row(
        InlineKeyboardButton("🎞 تريلر", callback_data=f"trailer_{title}"),
        InlineKeyboardButton("➕ قائمتي", callback_data=f"addwatch_{movie_id}_{title}_movie")
    )

    try:
        bot.send_photo(chat_id, poster, caption=caption, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')

# ═══════════════════════════════════════
#           تفاصيل المسلسل/الأنمي
# ═══════════════════════════════════════
def show_tv(chat_id, tv_id):
    url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={TMDB_KEY}"
    data = requests.get(url).json()

    name = data.get('name', '')
    year = data.get('first_air_date', '')[:4]
    rating = data.get('vote_average', 0)
    overview = data.get('overview', '')
    poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"
    genres = ", ".join([g['name'] for g in data.get('genres', [])])
    seasons = data.get('number_of_seasons', '?')
    episodes = data.get('number_of_episodes', '?')
    status = data.get('status', '')

    is_anime = any(g['id'] == 16 for g in data.get('genres', []))
    icon = "🎌" if is_anime else "📺"

    try:
        ai_summary = model.generate_content(f"ملخص ممتع بالعربي بسطرين للمسلسل: {name}").text.strip()
    except:
        ai_summary = overview[:200]

    caption = (
        f"{icon} *{name}* ({year})\n"
        f"⭐ {round(rating, 1)}/10\n"
        f"🎭 {genres}\n"
        f"📊 {seasons} مواسم | {episodes} حلقة\n"
        f"📡 {status}\n\n"
        f"📖 {ai_summary}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⬇️ تورنت", callback_data=f"torrent_tv_{tv_id}_{name}_{seasons}"),
        InlineKeyboardButton("🗣 ترجمة", callback_data=f"subtitle_{tv_id}_{name}_tv")
    )
    markup.row(
        InlineKeyboardButton("🎞 تريلر", callback_data=f"trailer_{name}"),
        InlineKeyboardButton("➕ قائمتي", callback_data=f"addwatch_{tv_id}_{name}_tv")
    )

    try:
        bot.send_photo(chat_id, poster, caption=caption, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')

# ═══════════════════════════════════════
#           التورنت - أفلام
# ═══════════════════════════════════════
def torrent_movie_quality(chat_id, movie_id, title):
    log_action(chat_id, "torrent")
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎯 1080p", callback_data=f"tmq_{title}_1080p"),
        InlineKeyboardButton("🎯 720p", callback_data=f"tmq_{title}_720p"),
        InlineKeyboardButton("🎯 480p", callback_data=f"tmq_{title}_480p")
    )
    bot.send_message(chat_id, "🎬 اختار الجودة:", reply_markup=markup)

def get_movie_torrents(chat_id, title, quality):
    results = []
    try:
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={title}&limit=5"
        data = requests.get(url, timeout=10).json()
        if data['data']['movie_count'] > 0:
            for m in data['data']['movies']:
                for t in m['torrents']:
                    if quality.replace('p', '') in t['quality']:
                        results.append({
                            "name": f"{m['title']} ({m['year']})",
                            "size": t['size'],
                            "seeds": t['seeds'],
                            "quality": t['quality'],
                            "source": "YTS",
                            "magnet": f"magnet:?xt=urn:btih:{t['hash']}&dn={m['title']}"
                        })
    except:
        pass

    try:
        url = f"https://apibay.org/q.php?q={title} {quality}&cat=200"
        data = requests.get(url, timeout=10).json()
        if data and data[0]['name'] != 'No results returned':
            for t in data[:3]:
                size_gb = round(int(t['size']) / 1073741824, 2)
                results.append({
                    "name": t['name'],
                    "size": f"{size_gb} GB",
                    "seeds": t['seeders'],
                    "quality": quality,
                    "source": "TPB",
                    "magnet": f"magnet:?xt=urn:btih:{t['info_hash']}&dn={t['name']}"
                })
    except:
        pass

    if not results:
        bot.send_message(chat_id, "❌ ما لقينا تورنت بهذي الجودة!")
        return

    for r in results[:4]:
        text = (
            f"🎬 {r['name']}\n"
            f"📦 {r['size']}\n"
            f"🎯 {r['quality']}\n"
            f"🌱 Seeds: {r['seeds']}\n"
            f"📡 {r['source']}\n\n"
            f"🔗 <code>{r['magnet']}</code>"
        )
        bot.send_message(chat_id, text, parse_mode='HTML')

# ═══════════════════════════════════════
#           التورنت - مسلسلات
# ═══════════════════════════════════════
def torrent_tv_type(chat_id, tv_id, title, seasons):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📦 Batch (كامل)", callback_data=f"tvbatch_{tv_id}_{title}_{seasons}"),
        InlineKeyboardButton("🎬 منفصل", callback_data=f"tvsingle_{tv_id}_{title}_{seasons}")
    )
    bot.send_message(chat_id, "📺 اختار نوع التحميل:", reply_markup=markup)

def torrent_tv_seasons(chat_id, tv_id, title, seasons, mode):
    markup = InlineKeyboardMarkup()
    row = []
    for s in range(1, int(seasons)+1):
        row.append(InlineKeyboardButton(f"S{s:02d}", callback_data=f"tvs_{mode}_{title}_{s}"))
        if len(row) == 4:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    bot.send_message(chat_id, "📺 اختار الموسم:", reply_markup=markup)

def torrent_tv_episodes(chat_id, title, season):
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_KEY}&query={title}"
    data = requests.get(url).json()
    if not data['results']:
        return
    tv_id = data['results'][0]['id']
    url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}?api_key={TMDB_KEY}"
    data = requests.get(url).json()
    episodes = data.get('episodes', [])

    markup = InlineKeyboardMarkup()
    row = []
    for ep in episodes:
        ep_num = ep['episode_number']
        row.append(InlineKeyboardButton(f"E{ep_num:02d}", callback_data=f"tvepisode_{title}_{season}_{ep_num}"))
        if len(row) == 5:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)

    markup.row(InlineKeyboardButton("🎯 اختار الجودة أولاً", callback_data=f"tvepq_{title}_{season}"))
    bot.send_message(chat_id, f"📺 اختار الحلقة - الموسم {season}:", reply_markup=markup)

def get_tv_torrent(chat_id, title, season, episode, quality="1080p"):
    query = f"{title} S{int(season):02d}E{int(episode):02d} {quality}"
    try:
        url = f"https://apibay.org/q.php?q={query}&cat=200"
        data = requests.get(url, timeout=10).json()
        if data and data[0]['name'] != 'No results returned':
            for t in data[:3]:
                size_gb = round(int(t['size']) / 1073741824, 2)
                magnet = f"magnet:?xt=urn:btih:{t['info_hash']}&dn={t['name']}"
                text = (
                    f"📺 {t['name']}\n"
                    f"📦 {size_gb} GB\n"
                    f"🌱 Seeds: {t['seeders']}\n\n"
                    f"🔗 <code>{magnet}</code>"
                )
                bot.send_message(chat_id, text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, "❌ ما لقينا تورنت!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

def get_tv_batch(chat_id, title, season, quality="1080p"):
    query = f"{title} Season {season} {quality}"
    try:
        url = f"https://apibay.org/q.php?q={query}&cat=200"
        data = requests.get(url, timeout=10).json()
        if data and data[0]['name'] != 'No results returned':
            for t in data[:3]:
                size_gb = round(int(t['size']) / 1073741824, 2)
                magnet = f"magnet:?xt=urn:btih:{t['info_hash']}&dn={t['name']}"
                text = (
                    f"📦 {t['name']}\n"
                    f"💾 {size_gb} GB\n"
                    f"🌱 Seeds: {t['seeders']}\n\n"
                    f"🔗 <code>{magnet}</code>"
                )
                bot.send_message(chat_id, text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, "❌ ما لقينا تورنت!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

# ═══════════════════════════════════════
#           الترجمة
# ═══════════════════════════════════════
def get_subtitles(chat_id, item_id, title, media_type):
    markup = InlineKeyboardMarkup()
    if media_type == "tv":
        markup.row(
            InlineKeyboardButton("🇸🇦 عربي", callback_data=f"tvsubseason_{item_id}_{title}_ar"),
            InlineKeyboardButton("🇺🇸 English", callback_data=f"tvsubseason_{item_id}_{title}_en")
        )
    else:
        markup.row(
            InlineKeyboardButton("🇸🇦 عربي", callback_data=f"subdl_{item_id}_{title}_ar"),
            InlineKeyboardButton("🇺🇸 English", callback_data=f"subdl_{item_id}_{title}_en")
        )
    markup.row(
        InlineKeyboardButton("🇫🇷 Français", callback_data=f"subdl_{item_id}_{title}_fr"),
        InlineKeyboardButton("🇪🇸 Español", callback_data=f"subdl_{item_id}_{title}_es")
    )
    bot.send_message(chat_id, "🗣 اختار لغة الترجمة:", reply_markup=markup)

def download_subtitle(chat_id, item_id, title, lang, season=None, episode=None):
    try:
        url = f"https://api.subdl.com/api/v1/subtitles?api_key={SUBDL_KEY}&tmdb_id={item_id}&languages={lang}&subs_per_page=5"
        if season:
            url += f"&season_number={season}&episode_number={episode}"
        data = requests.get(url).json()

        if not data.get('subtitles'):
            bot.send_message(chat_id, "❌ ما فيه ترجمة بهذي اللغة!")
            return

        sub = data['subtitles'][0]
        dl_url = f"https://dl.subdl.com{sub['url']}"
        sub_content = requests.get(dl_url).content
        bot.send_document(chat_id, sub_content, visible_file_name=f"{title}_{lang}.srt")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

# ═══════════════════════════════════════
#           التريلر
# ═══════════════════════════════════════
def get_trailer(chat_id, title):
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={title}+trailer&type=video&key={YOUTUBE_KEY}"
        data = requests.get(url).json()
        video_id = data['items'][0]['id']['videoId']
        bot.send_message(chat_id, f"🎞 *{title}*\nhttps://youtube.com/watch?v={video_id}", parse_mode='Markdown')
    except:
        bot.send_message(chat_id, "❌ ما لقينا تريلر!")

# ═══════════════════════════════════════
#           قائمة المشاهدة
# ═══════════════════════════════════════
def show_watchlist(chat_id, user_id):
    conn = sqlite3.connect("cinema.db")
    c = conn.cursor()
    c.execute("SELECT item_id, title, media_type FROM watchlist WHERE user_id=?", (user_id,))
    items = c.fetchall()
    conn.close()

    if not items:
        bot.send_message(chat_id, "📋 قائمتك فاضية!")
        return

    markup = InlineKeyboardMarkup()
    for item in items:
        icon = "🎬" if item[2] == "movie" else "📺"
        markup.add(InlineKeyboardButton(f"{icon} {item[1]}", callback_data=f"{item[2]}_{item[0]}"))
    bot.send_message(chat_id, "📋 *قائمة مشاهدتك:*", reply_markup=markup, parse_mode='Markdown')

# ═══════════════════════════════════════
#           الأفلام والمسلسلات
# ═══════════════════════════════════════
def show_results(chat_id, items, media):
    markup = InlineKeyboardMarkup()
    icon = "🎬" if media == "movie" else ("🎌" if media == "anime" else "📺")
    for item in items:
        name = item.get('title') or item.get('name', '')
        date = item.get('release_date') or item.get('first_air_date', '')
        markup.add(InlineKeyboardButton(
            f"{icon} {name} ({date[:4]})",
            callback_data=f"{'movie' if media == 'movie' else 'tv'}_{item['id']}"
        ))
    bot.send_message(chat_id, "اختار:", reply_markup=markup)

# ═══════════════════════════════════════
#           Callback Handler
# ═══════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data.startswith("movie_"):
        show_movie(chat_id, data.split("_")[1])

    elif data.startswith("tv_"):
        show_tv(chat_id, data.split("_")[1])

    elif data == "trending_movie":
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "movie")

    elif data == "trending_tv":
        url = f"https://api.themoviedb.org/3/trending/tv/week?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "tv")

    elif data == "trending_anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_KEY}&with_genres=16&sort_by=popularity.desc"
        show_results(chat_id, requests.get(url).json()['results'][:5], "anime")

    elif data == "toprated_movie":
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "movie")

    elif data == "toprated_tv":
        url = f"https://api.themoviedb.org/3/tv/top_rated?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "tv")

    elif data == "toprated_anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_KEY}&with_genres=16&sort_by=vote_average.desc"
        show_results(chat_id, requests.get(url).json()['results'][:5], "anime")

    elif data == "upcoming_movie":
        url = f"https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "movie")

    elif data == "onair_tv":
        url = f"https://api.themoviedb.org/3/tv/on_the_air?api_key={TMDB_KEY}"
        show_results(chat_id, requests.get(url).json()['results'][:5], "tv")

    elif data == "onair_anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_KEY}&with_genres=16&sort_by=first_air_date.desc"
        show_results(chat_id, requests.get(url).json()['results'][:5], "anime")

    elif data == "genres_movie":
        url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_KEY}"
        data2 = requests.get(url).json()
        markup = InlineKeyboardMarkup()
        genres = data2['genres']
        for i in range(0, len(genres[:12]), 2):
            row = [InlineKeyboardButton(genres[i]['name'], callback_data=f"genre_{genres[i]['id']}_movie")]
            if i+1 < len(genres[:12]):
                row.append(InlineKeyboardButton(genres[i+1]['name'], callback_data=f"genre_{genres[i+1]['id']}_movie"))
            markup.row(*row)
        bot.send_message(chat_id, "🎭 اختار النوع:", reply_markup=markup)

    elif data == "genres_tv" or data == "genres_anime":
        url = f"https://api.themoviedb.org/3/genre/tv/list?api_key={TMDB_KEY}"
        data2 = requests.get(url).json()
        markup = InlineKeyboardMarkup()
        genres = data2['genres']
        mtype = "tv"
        for i in range(0, len(genres[:12]), 2):
            row = [InlineKeyboardButton(genres[i]['name'], callback_data=f"genre_{genres[i]['id']}_{mtype}")]
            if i+1 < len(genres[:12]):
                row.append(InlineKeyboardButton(genres[i+1]['name'], callback_data=f"genre_{genres[i+1]['id']}_{mtype}"))
            markup.row(*row)
        bot.send_message(chat_id, "🎭 اختار النوع:", reply_markup=markup)

    elif data.startswith("genre_"):
        parts = data.split("_")
        genre_id, media = parts[1], parts[2]
        url = f"https://api.themoviedb.org/3/discover/{media}?api_key={TMDB_KEY}&with_genres={genre_id}"
        show_results(chat_id, requests.get(url).json()['results'][:5], media)

    elif data.startswith("torrent_movie_"):
        parts = data.split("_")
        movie_id, title = parts[2], parts[3]
        torrent_movie_quality(chat_id, movie_id, title)

    elif data.startswith("tmq_"):
        parts = data.split("_")
        title, quality = parts[1], parts[2]
        get_movie_torrents(chat_id, title, quality)

    elif data.startswith("torrent_tv_"):
        parts = data.split("_")
        tv_id, title, seasons = parts[2], parts[3], parts[4]
        torrent_tv_type(chat_id, tv_id, title, seasons)

    elif data.startswith("tvbatch_"):
        parts = data.split("_")
        tv_id, title, seasons = parts[1], parts[2], parts[3]
        torrent_tv_seasons(chat_id, tv_id, title, seasons, "batch")

    elif data.startswith("tvsingle_"):
        parts = data.split("_")
        tv_id, title, seasons = parts[1], parts[2], parts[3]
        torrent_tv_seasons(chat_id, tv_id, title, seasons, "single")

    elif data.startswith("tvs_"):
        parts = data.split("_")
        mode, title, season = parts[1], parts[2], parts[3]
        if mode == "batch":
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🎯 1080p", callback_data=f"tvbatchq_{title}_{season}_1080p"),
                InlineKeyboardButton("🎯 720p", callback_data=f"tvbatchq_{title}_{season}_720p"),
                InlineKeyboardButton("🎯 480p", callback_data=f"tvbatchq_{title}_{season}_480p")
            )
            bot.send_message(chat_id, "🎯 اختار الجودة:", reply_markup=markup)
        else:
            torrent_tv_episodes(chat_id, title, season)

    elif data.startswith("tvbatchq_"):
        parts = data.split("_")
        title, season, quality = parts[1], parts[2], parts[3]
        get_tv_batch(chat_id, title, season, quality)

    elif data.startswith("tvepisode_"):
        parts = data.split("_")
        title, season, episode = parts[1], parts[2], parts[3]
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🎯 1080p", callback_data=f"tveq_{title}_{season}_{episode}_1080p"),
            InlineKeyboardButton("🎯 720p", callback_data=f"tveq_{title}_{season}_{episode}_720p"),
            InlineKeyboardButton("🎯 480p", callback_data=f"tveq_{title}_{season}_{episode}_480p")
        )
        bot.send_message(chat_id, "🎯 اختار الجودة:", reply_markup=markup)

    elif data.startswith("tveq_"):
        parts = data.split("_")
        title, season, episode, quality = parts[1], parts[2], parts[3], parts[4]
        get_tv_torrent(chat_id, title, season, episode, quality)

    elif data.startswith("subtitle_"):
        parts = data.split("_")
        item_id, title, media_type = parts[1], parts[2], parts[3]
        get_subtitles(chat_id, item_id, title, media_type)

    elif data.startswith("tvsubseason_"):
        parts = data.split("_")
        item_id, title, lang = parts[1], parts[2], parts[3]
        url = f"https://api.themoviedb.org/3/tv/{item_id}?api_key={TMDB_KEY}"
        seasons = requests.get(url).json().get('number_of_seasons', 1)
        markup = InlineKeyboardMarkup()
        row = []
        for s in range(1, int(seasons)+1):
            row.append(InlineKeyboardButton(f"S{s:02d}", callback_data=f"tvsubep_{item_id}_{title}_{lang}_{s}"))
            if len(row) == 4:
                markup.row(*row)
                row = []
        if row:
            markup.row(*row)
        bot.send_message(chat_id, "اختار الموسم:", reply_markup=markup)

    elif data.startswith("tvsubep_"):
        parts = data.split("_")
        item_id, title, lang, season = parts[1], parts[2], parts[3], parts[4]
        url = f"https://api.themoviedb.org/3/tv/{item_id}/season/{season}?api_key={TMDB_KEY}"
        episodes = requests.get(url).json().get('episodes', [])
        markup = InlineKeyboardMarkup()
        row = []
        for ep in episodes:
            ep_num = ep['episode_number']
            row.append(InlineKeyboardButton(f"E{ep_num:02d}", callback_data=f"subdlep_{item_id}_{title}_{lang}_{season}_{ep_num}"))
            if len(row) == 5:
                markup.row(*row)
                row = []
        if row:
            markup.row(*row)
        bot.send_message(chat_id, f"اختار الحلقة - الموسم {season}:", reply_markup=markup)

    elif data.startswith("subdlep_"):
        parts = data.split("_")
        item_id, title, lang, season, episode = parts[1], parts[2], parts[3], parts[4], parts[5]
        download_subtitle(chat_id, item_id, title, lang, season, episode)

    elif data.startswith("subdl_"):
        parts = data.split("_")
        item_id, title, lang = parts[1], parts[2], parts[3]
        download_subtitle(chat_id, item_id, title, lang)

    elif data.startswith("trailer_"):
        get_trailer(chat_id, data.replace("trailer_", ""))

    elif data.startswith("addwatch_"):
        parts = data.split("_")
        item_id, title, media_type = parts[1], parts[2], parts[3]
        conn = sqlite3.connect("cinema.db")
        c = conn.cursor()
        c.execute("INSERT INTO watchlist VALUES (?,?,?,?)", (user_id, item_id, title, media_type))
        conn.commit()
        conn.close()
        bot.send_message(chat_id, f"✅ تمت الإضافة: {title}")

bot.polling()
