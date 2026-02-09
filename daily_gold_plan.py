import os
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
# (ระบบจะดึงรหัสลับจาก GitHub มาใส่ให้เองอัตโนมัติ)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

RSS_SOURCES = [
    "https://www.forexlive.com/feed/news",
    "https://www.fxstreet.com/rss/news/assets/gold",
    "https://www.investing.com/rss/news_1.rss"
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def get_thai_time():
    return datetime.now(timezone(timedelta(hours=7)))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, json=payload)

def get_daily_analysis():
    combined_news = ""
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                combined_news += f"- {entry.title} (Link: {entry.link})\n"
        except: continue

    now_thai = get_thai_time()
    date_str = now_thai.strftime('%d/%m/%Y')
    
    prompt = f"""
    Context:
    วันนี้คือวันที่: {date_str} (เวลาไทย {now_thai.strftime('%H:%M')})
    News: {combined_news}

    Task:
    "ค้นหาตารางตัวเลขเศรษฐกิจ (Economic Calendar) วันนี้ เพื่อเตือนคนใช้ EA ให้ปิดหนีข่าว"

    Instructions:
    1. **Identify Events:** ค้นหา Keyword: CPI, PPI, NFP, FOMC, Rate Decision, GDP
    2. **Convert Time:** ระบุเวลาข่าวออกเป็น **"เวลาไทย (GMT+7)"** เท่านั้น
    3. **No-Trade Zone:** แนะนำช่วงเวลาที่ต้อง **"ปิด EA"**

    Output (HTML Thai):
    🛡️ <b>ตารางหลบข่าวเปิด EA</b> ({date_str})
    ➖➖➖➖➖➖➖➖
    🚨 <b>Event อันตราย (High Impact):</b>
    
    🕒 <b>เวลาไทย:</b> [ระบุเวลา]
    💣 <b>เหตุการณ์:</b> [ชื่อข่าว]
    🔥 <b>ความแรง:</b> 🔴 High
    ⛔ <b>ช่วงปิด EA:</b> [เช่น 19:00 - 20:30 น.]
    
    (ถ้าไม่มีข่าวแดง บอกว่า "✅ วันนี้ทางสะดวก ไม่มีข่าวแดง")
    ➖➖➖➖➖➖➖➖
    📉 <b>วิเคราะห์ความเสี่ยงรวม:</b> (สรุปสั้นๆ)
    🤖 <b>คำแนะนำสุดท้าย:</b> (เปิด EA ได้ไหม)
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {e}"

if __name__ == "__main__":
    if TELEGRAM_TOKEN and GEMINI_API_KEY:
        plan = get_daily_analysis()
        if plan:
            send_telegram(plan)
    else:
        print("❌ ไม่พบ Key (โปรดตั้งค่า Secrets ใน GitHub)")