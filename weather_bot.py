# main.py
import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
import requests

# ---------- تنظیمات از Environment ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")         # مقدار در Render: BOT_TOKEN
API_KEY = os.environ.get("API_KEY")             # مقدار در Render: API_KEY (OpenWeatherMap)
SEND_SECRET = os.environ.get("SEND_SECRET")     # یک راز ساده مثلاً "mysecret123"
SUBSCRIBERS_FILE = "subscribers.json"
LAT, LON = 35.6764, 51.4181
AREA_NAME = "پانزده خرداد"

if not BOT_TOKEN or not API_KEY or not SEND_SECRET:
    raise RuntimeError("لطفاً متغیرهای محیطی BOT_TOKEN, API_KEY, SEND_SECRET را تنظیم کنید.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ---------- مدیریت مشترک‌ها ----------
def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_subscribers(list_ids):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list_ids, f, ensure_ascii=False)

def add_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        save_subscribers(subs)
    return subs

def remove_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id in subs:
        subs.remove(chat_id)
        save_subscribers(subs)
    return subs

# ---------- فراخوانی های API هوا ----------
def get_weather_now():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=fa"
    r = requests.get(url, timeout=10).json()
    desc = r["weather"][0]["description"].capitalize()
    temp = r["main"]["temp"]
    humidity = r["main"]["humidity"]
    temp_min = r["main"]["temp_min"]
    temp_max = r["main"]["temp_max"]
    return desc, temp, humidity, temp_min, temp_max

def get_forecast_12h():
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=fa"
    r = requests.get(url, timeout=10).json()
    items = r.get("list", [])[:4]   # هر 3 ساعت یکبار => 4 آیتم ~ 12 ساعت
    lines = []
    for it in items:
        dt_txt = it.get("dt_txt", "")
        timepart = dt_txt.split(" ")[1] if " " in dt_txt else dt_txt
        temp = it["main"]["temp"]
        hum = it["main"]["humidity"]
        desc = it["weather"][0]["description"]
        lines.append(f"{timepart[:5]} — {desc}, {temp:.1f}°C, رطوبت {hum}%")
    return "\n".join(lines)

def get_aqi_text():
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    r = requests.get(url, timeout=10).json()
    try:
        aqi = r["list"][0]["main"]["aqi"]
    except Exception:
        return "نامشخص"
    mapping = {1: "خیلی پاک 🌿", 2: "پاک 🙂", 3: "متوسط 😐", 4: "ناسالم 😷", 5: "خیلی ناسالم ☠️"}
    return mapping.get(aqi, "نامشخص")

def build_message():
    desc, temp, humidity, tmin, tmax = get_weather_now()
    aqi = get_aqi_text()
    forecast = get_forecast_12h()
    return (
        f"📍 منطقه: {AREA_NAME}\n"
        f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d')}\n\n"
        f"🔹 وضعیت جوی: {desc}\n"
        f"🌡 دمای فعلی: {temp:.1f}°C\n"
        f"💧 رطوبت: {humidity}%\n"
        f"🌡 حداقل: {tmin:.1f}°C | حداکثر: {tmax:.1f}°C\n"
        f"🌫 کیفیت هوا: {aqi}\n\n"
        f"📊 پیش‌بینی ۱۲ ساعت آینده:\n{forecast}"
    )

# ---------- ارسال به یک یا همه مشترک‌ها ----------
def send_to_chat(chat_id):
    msg = build_message()
    # عکس محلی اگر وجود دارد ارسال کن، در غیر این صورت فقط متن بفرست
    photo_path = "mision-vision.jpg"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as ph:
                bot.send_photo(chat_id, ph, caption=msg)
        else:
            bot.send_message(chat_id, msg)
        return True
    except Exception as e:
        print("خطا در ارسال به", chat_id, e)
        return False

def send_to_all():
    subs = load_subscribers()
    results = {"sent": [], "failed": []}
    for cid in subs:
        ok = send_to_chat(cid)
        (results["sent"] if ok else results["failed"]).append(cid)
    return results

# ---------- دستورات تلگرام ----------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    add_subscriber(message.chat.id)
    bot.reply_to(message, "✅ شما عضو شدی. از حالا گزارش‌ها برات ارسال میشه.\nبرای لغو اشتراک /stop رو بفرست.")

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    remove_subscriber(message.chat.id)
    bot.reply_to(message, "✅ اشتراکت لغو شد.")

@bot.message_handler(commands=["weather"])
def cmd_weather(message):
    msg = build_message()
    photo_path = "mision-vision.jpg"
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as ph:
            bot.send_photo(message.chat.id, ph, caption=msg)
    else:
        bot.send_message(message.chat.id, msg)

# ---------- Flask endpoints ----------
@app.route("/")
def health():
    return "ok", 200

@app.route("/send", methods=["GET"])
def send_endpoint():
    s = request.args.get("secret", "")
    if s != SEND_SECRET:
        return jsonify({"error": "forbidden"}), 403
    res = send_to_all()
    return jsonify(res), 200

# ---------- اجرا: بوت در Thread و Flask توسط gunicorn اجرا میشه ----------
def run_bot_polling():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # اگر محلی اجرا می‌کنی می‌تونی این بلاک رو اجرا کنی
    threading.Thread(target=run_bot_polling, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
