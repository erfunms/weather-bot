import telebot
import requests
from datetime import datetime
from PIL import Image

# ---------------- تنظیمات اولیه ----------------
BOT_TOKEN = "توکن_ربات_خودت_اینجا"
API_KEY = "کلید_API_OpenWeather_اینجا"

bot = telebot.TeleBot(BOT_TOKEN)

# مختصات منطقه پانزده خرداد
LAT, LON = 35.6764, 51.4181
AREA_NAME = "پانزده خرداد"

# ---------------- تابع دریافت وضعیت هوا ----------------
def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=fa"
    data = requests.get(url).json()

    desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    temp_min = data["main"]["temp_min"]
    temp_max = data["main"]["temp_max"]

    return desc, temp, humidity, temp_min, temp_max

# ---------------- تابع پیش‌بینی ۱۲ ساعت آینده ----------------
def get_forecast():
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=fa"
    data = requests.get(url).json()
    next_12 = data["list"][:4]  # هر ۳ ساعت یک‌بار
    forecast_text = ""
    for item in next_12:
        time = datetime.fromtimestamp(item["dt"]).strftime("%H:%M")
        temp = item["main"]["temp"]
        desc = item["weather"][0]["description"]
        forecast_text += f"\n🕒 {time}: {desc}, 🌡 {temp}°C"
    return forecast_text

# ---------------- تابع دریافت آلودگی هوا ----------------
def get_air_quality():
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    data = requests.get(url).json()
    aqi = data["list"][0]["main"]["aqi"]

    levels = {
        1: "خیلی پاک 🌿",
        2: "پاک 🙂",
        3: "متوسط 😐",
        4: "ناسالم 😷",
        5: "خیلی ناسالم ☠️"
    }
    return levels.get(aqi, "نامشخص")

# ---------------- ارسال وضعیت هوا ----------------
@bot.message_handler(commands=["start", "weather"])
def send_weather(message):
    desc, temp, humidity, temp_min, temp_max = get_weather()
    air_quality = get_air_quality()
    forecast = get_forecast()

    weather_text = (
        f"📍 منطقه: {AREA_NAME}\n"
        f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d')}\n"
        f"🌤 وضعیت جوی: {desc}\n"
        f"🌡 دمای فعلی: {temp:.1f}°C\n"
        f"💧 رطوبت: {humidity}%\n"
        f"🌡 حداقل: {temp_min:.1f}°C | حداکثر: {temp_max:.1f}°C\n"
        f"🌫 وضعیت آلودگی هوا: {air_quality}\n"
        f"🔮 پیش‌بینی ۱۲ ساعت آینده:\n{forecast}"
    )

    with open("mision-vision.jpg", "rb") as photo:
        bot.send_photo(message.chat.id, photo, caption=weather_text)

# ---------------- اجرای ربات ----------------
print("🤖 ربات در حال اجراست ...")
bot.polling()
