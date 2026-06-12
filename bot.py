import telebot
import requests
import sqlite3
import os
import google.generativeai as genai
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get("TOKEN")
TMDB_KEY = os.environ.get("TMDB_KEY")
OPENSUB_KEY = os.environ.get("OPENSUB_KEY")
YOUTUBE_KEY = os.environ.get("YOUTUBE_KEY")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-pro")

search_results = {}

def init_db():
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                 (user_id INTEGER, movie_id INTEGER, title TEXT, poster TEXT)''')
    conn.commit()
    conn.close()

init_db()

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 الرائجة", callback_data="trending"),
        InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data="toprated")
    )
    markup.row(
        InlineKeyboardButton("🎭 حسب النوع", callback_data="genres"),
        InlineKeyboardButton("📅 قادمة قريباً", callback_data="upcoming")
    )
    markup.row(
        InlineKeyboardButton("📋 قائمتي", callback_data="watchlist"),
        InlineKeyboardButton("🤖 اسأل AI", callback_data="ask_ai")
    )
    bot.send_message(message.chat.id,
        "🍿 *Welcome to Movie's Home!*\n\nاكتب اسم فيلم أو اختار من القائمة:",
        reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def search_movie(message):
    query = message.text
    chat_id = message.chat.id

    try:
        response = model.generate_content(
            f"Translate this movie name to English, return ONLY the English name nothing else: {query}"
        )
        english_query = response.text.strip()
    except:
        english_query = query

    bot.send_message(chat_id, f"🔍 Searching for: {english_query}...")

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={english_query}"
    data = requests.get(url).json()

    if not data['results']:
        bot.send_message(chat_id, "❌ No results found!")
        return

    search_results[chat_id] = data['results']
    send_movie_results(chat_id, data['results'][:5])

def send_movie_results(chat_id, movies):
    markup = InlineKeyboardMarkup()
    for m in movies:
        markup.add(InlineKeyboardButton(
            f"🎬 {m['title']} ({m.get('release_date', '')[:4]})",
            callback_data=f"movie_{m['id']}"
        ))
    bot.send_message(chat_id, "اختار الفيلم:", reply_markup=markup)

def show_movie(chat_id, movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}&append_to_response=credits"
    data = requests.get(url).json()

    title = data.get('title', '')
    year = data.get('release_date', '')[:4]
    rating = data.get('vote_average', 0)
    overview = data.get('overview', 'No description')
    poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"
    genres = ", ".join([g['name'] for g in data.get('genres', [])])
    director = next((c['name'] for c in data.get('credits', {}).get('crew', []) if c['job'] == 'Director'), 'Unknown')

    try:
        ai_summary = model.generate_content(
            f"Write a fun 2-line Arabic summary for the movie: {title}"
        ).text.strip()
    except:
        ai_summary = overview[:200]

    caption = (
        f"🎬 *{title}* ({year})\n"
        f"⭐ {rating}/10\n"
        f"🎭 {genres}\n"
        f"🎬 المخرج: {director}\n\n"
        f"📖 {ai_summary}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⬇️ تحميل تورنت", callback_data=f"torrent_{title}_{year}"),
        InlineKeyboardButton("🗣 ترجمة", callback_data=f"subtitle_{movie_id}_{title}")
    )
    markup.row(
        InlineKeyboardButton("🎞 تريلر", callback_data=f"trailer_{title}"),
        InlineKeyboardButton("➕ قائمتي", callback_data=f"addwatch_{movie_id}_{title}")
    )

    try:
        bot.send_photo(chat_id, poster, caption=caption,
                      reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='Markdown')

def get_torrents(chat_id, title, year):
    results = []

    try:
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={title}&limit=3"
        data = requests.get(url, timeout=10).json()
        if data['data']['movie_count'] > 0:
            for m in data['data']['movies']:
                for t in m['torrents']:
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
        url = f"https://apibay.org/q.php?q={title}&cat=200"
        data = requests.get(url, timeout=10).json()
        if data and data[0]['name'] != 'No results returned':
            for t in data[:3]:
                size_gb = round(int(t['size']) / 1073741824, 2)
                results.append({
                    "name": t['name'],
                    "size": f"{size_gb} GB",
                    "seeds": t['seeders'],
                    "quality": "",
                    "source": "TPB",
                    "magnet": f"magnet:?xt=urn:btih:{t['info_hash']}&dn={t['name']}"
                })
    except:
        pass

    if not results:
        bot.send_message(chat_id, "❌ No torrents found!")
        return

    for r in results[:5]:
        quality = f"🎯 {r['quality']}\n" if r['quality'] else ""
        text = (
            f"🎬 {r['name']}\n"
            f"📦 {r['size']}\n"
            f"{quality}"
            f"🌱 Seeds: {r['seeds']}\n"
            f"📡 {r['source']}\n\n"
            f"🔗 <code>{r['magnet']}</code>"
        )
        bot.send_message(chat_id, text, parse_mode='HTML')

def get_subtitles(chat_id, movie_id, title):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇸🇦 عربي", callback_data=f"subdl_{movie_id}_{title}_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data=f"subdl_{movie_id}_{title}_en")
    )
    markup.row(
        InlineKeyboardButton("🇫🇷 Français", callback_data=f"subdl_{movie_id}_{title}_fr"),
        InlineKeyboardButton("🇪🇸 Español", callback_data=f"subdl_{movie_id}_{title}_es")
    )
    bot.send_message(chat_id, "🗣 اختار لغة الترجمة:", reply_markup=markup)

def download_subtitle(chat_id, movie_id, title, lang):
    try:
        headers = {
            "Api-Key": OPENSUB_KEY,
            "Content-Type": "application/json",
            "User-Agent": "MoviesHomeBot v1.0"
        }
        url = f"https://api.opensubtitles.com/api/v1/subtitles?tmdb_id={movie_id}&languages={lang}"
        data = requests.get(url, headers=headers).json()

        if not data.get('data'):
            bot.send_message(chat_id, "❌ ما فيه ترجمة بهذي اللغة!")
            return

        sub = data['data'][0]
        file_id = sub['attributes']['files'][0]['file_id']

        dl_url = "https://api.opensubtitles.com/api/v1/download"
        dl_data = requests.post(dl_url, headers=headers,
                               json={"file_id": file_id}).json()

        sub_content = requests.get(dl_data['link']).content
        bot.send_document(chat_id, sub_content,
                         visible_file_name=f"{title}_{lang}.srt")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

def get_trailer(chat_id, title):
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={title}+trailer&type=video&key={YOUTUBE_KEY}"
        data = requests.get(url).json()
        video_id = data['items'][0]['id']['videoId']
        bot.send_message(chat_id, f"🎞 *{title} - Trailer*\nhttps://youtube.com/watch?v={video_id}",
                        parse_mode='Markdown')
    except:
        bot.send_message(chat_id, "❌ ما لقينا تريلر!")

def add_to_watchlist(user_id, movie_id, title):
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("INSERT INTO watchlist VALUES (?,?,?,?)", (user_id, movie_id, title, ""))
    conn.commit()
    conn.close()

def get_watchlist(user_id):
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("SELECT movie_id, title FROM watchlist WHERE user_id=?", (user_id,))
    movies = c.fetchall()
    conn.close()
    return movies

def get_trending(chat_id):
    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_KEY}"
    data = requests.get(url).json()
    send_movie_results(chat_id, data['results'][:5])

def get_top_rated(chat_id):
    url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_KEY}"
    data = requests.get(url).json()
    send_movie_results(chat_id, data['results'][:5])

def get_upcoming(chat_id):
    url = f"https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_KEY}"
    data = requests.get(url).json()
    send_movie_results(chat_id, data['results'][:5])

def get_genres(chat_id):
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_KEY}"
    data = requests.get(url).json()
    markup = InlineKeyboardMarkup()
    genres = data['genres']
    for i in range(0, len(genres[:12]), 2):
        row = [InlineKeyboardButton(genres[i]['name'], callback_data=f"genre_{genres[i]['id']}")]
        if i+1 < len(genres[:12]):
            row.append(InlineKeyboardButton(genres[i+1]['name'], callback_data=f"genre_{genres[i+1]['id']}"))
        markup.row(*row)
    bot.send_message(chat_id, "🎭 اختار النوع:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "trending":
        get_trending(chat_id)
    elif data == "toprated":
        get_top_rated(chat_id)
    elif data == "upcoming":
        get_upcoming(chat_id)
    elif data == "genres":
        get_genres(chat_id)
    elif data == "ask_ai":
        bot.send_message(chat_id, "🤖 اكتب لي وش تبي تشوف وأوصي لك!")
    elif data == "watchlist":
        movies = get_watchlist(user_id)
        if not movies:
            bot.send_message(chat_id, "📋 قائمتك فاضية!")
        else:
            markup = InlineKeyboardMarkup()
            for m in movies:
                markup.add(InlineKeyboardButton(f"🎬 {m[1]}", callback_data=f"movie_{m[0]}"))
            bot.send_message(chat_id, "📋 قائمة مشاهدتك:", reply_markup=markup)
    elif data.startswith("movie_"):
        movie_id = data.split("_")[1]
        show_movie(chat_id, movie_id)
    elif data.startswith("torrent_"):
        parts = data.split("_")
        title, year = parts[1], parts[2]
        get_torrents(chat_id, title, year)
    elif data.startswith("subtitle_"):
        parts = data.split("_")
        movie_id, title = parts[1], parts[2]
        get_subtitles(chat_id, movie_id, title)
    elif data.startswith("subdl_"):
        parts = data.split("_")
        movie_id, title, lang = parts[1], parts[2], parts[3]
        download_subtitle(chat_id, movie_id, title, lang)
    elif data.startswith("trailer_"):
        title = data.replace("trailer_", "")
        get_trailer(chat_id, title)
    elif data.startswith("addwatch_"):
        parts = data.split("_")
        movie_id, title = parts[1], parts[2]
        add_to_watchlist(user_id, movie_id, title)
        bot.send_message(chat_id, f"✅ تمت الإضافة: {title}")
    elif data.startswith("genre_"):
        genre_id = data.split("_")[1]
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_KEY}&with_genres={genre_id}"
        result = requests.get(url).json()
        send_movie_results(chat_id, result['results'][:5])

bot.polling()
