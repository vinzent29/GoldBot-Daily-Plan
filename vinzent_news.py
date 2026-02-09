import os
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import dateutil.parser

# ================= 🔐 ดึง Key เดิมจาก GitHub Secrets =================
# (ใช้ Key ชุดเดียวกับโปรเจกต์ที่แล้วได้เลยครับ ไม่ต้องสร้างใหม่)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

RSS_URL = "https://www.fxstreet.com/rss/news/assets/gold"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': False}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending msg: {e}")

def analyze_news_ai(title, desc):
    prompt = f"""วิเคราะห์ข่าวทองคำ (XAUUSD): {title}\n{desc}\n
    ตอบสั้นๆ HTML: <b>ความแรง:</b> (1-10)/10 🔥\n<b>ทิศทาง:</b> (Bullish/Bearish/Neutral)\n<b>สรุป:</b> 1 ประโยค"""
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return "⚠️ AI วิเคราะห์ไม่ได้"

def check_news():
    print("🔄 VinzentNews กำลังทำงาน...")
    feed = feedparser.parse(RSS_URL)
    
    if not feed.entries:
        return

    # เช็คข่าวย้อนหลัง 6 นาที (เผื่อดีเลย์นิดหน่อยสำหรับ Cron 5 นาที)
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(minutes=6)

    found_news = False
    for entry in feed.entries[:3]:
        try:
            pub_date = dateutil.parser.parse(entry.published)
        except:
            continue

        # ถ้าข่าวใหม่กว่า 6 นาทีที่แล้ว -> แจ้งเตือน!
        if pub_date > time_limit:
            print(f"🔔 เจอข่าวใหม่: {entry.title}")
            ai_result = analyze_news_ai(entry.title, entry.description)
            msg = f"📰 <b>VinzentNews Alert!</b>\n➖➖➖➖➖➖\n<b>{entry.title}</b>\n\n{ai_result}\n\n🔗 <a href='{entry.link}'>อ่านข่าวเต็ม</a>"
            send_telegram(msg)
            found_news = True
    
    if not found_news:
        print("💤 ไม่มีข่าวใหม่ในช่วง 5-6 นาทีที่ผ่านมา")

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        check_news()
    else:
        print("❌ ไม่พบ Key")