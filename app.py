import os
import telebot
from flask import Flask, request

# 1. جلب التوكن من المتغيرات البيئية (أو ضع التوكن الخاص بك هنا مباشرة بين علامتي التنصيص)
TOKEN = os.environ.get('TOKEN', 'ضع_توكن_البوت_هنا_إذا_لم_تستخدم_المتغيرات_البيئية')

# 2. تعريف البوت وسيرفر Flask
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 3. دالة استقبال التحديثات من تليجرام (Webhook)
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# 4. دالة فحص عمل السيرفر عند فتح الرابط في المتصفح
@app.route("/")
def webhook():
    bot.remove_webhook()
    # استبدل YOUR_VERCEL_URL برابط مشروعك الذي سيعطيك إياه Vercel لاحقاً
    # bot.set_webhook(url='https://YOUR_VERCEL_URL.vercel.app/' + TOKEN)
    return "Cinema Bot is Running via Webhook on Vercel 24/7!", 200

# ==========================================
# 5. ضع هنا كل كود البوت الأساسي الخاص بك (الأوامر، أزرار الأفلام، البحث، والذكاء الاصطناعي)
# ==========================================

# مثال لأمر start (تأكد من دمج أكوادك هنا بالكامل):
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك في بوت السينما المطور على سيرفر Vercel! 🎬")

# ==========================================
# لضمان تشغيل السيرفر محلياً أو على Vercel
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
