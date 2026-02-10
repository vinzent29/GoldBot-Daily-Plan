import os
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import pytz

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ตั้งค่า AI (ใช้รุ่น 1.5-flash-latest เพื่อความชัวร์บน GitHub)
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    pass

# แหล่งข่าว RSS (สำหรับอ่านบทวิเคราะห์)
RSS_SOURCES = [
    "https://www.forexlive.com/feed/news",
    "https://www.fxstreet.com/rss/news/assets/gold",
    "https://www.investing.com/rss/news_1.rss"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# 1️⃣ ฟังก์ชันดึงปฏิทิน (เอาเวลาเป๊ะๆ)
def get_forex_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml" 
    feed = feedparser.parse(url)
    events = []
    
    thai_tz = pytz.timezone('Asia/Bangkok')
    now_thai = datetime.now(thai_tz)
    today_str = now_thai.strftime("%Y-%m-%d")

    for entry in feed.entries:
        if 'USD' not in entry.get('country', ''): continue
        if not entry.get('date', '').startswith(today_str): continue
        
        events.append(f"- [Calendar] {entry.get('time', '')} | ความแรง: {entry.get('impact', '')} | {entry.title}")
    
    return "\n".join(events) if events else "ไม่มี Event ในตารางวันนี้"

# 2️⃣ ฟังก์ชันดึงข่าว (เอาบทวิเคราะห์)
def get_market_news():
    news_items = []
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: # เอาแค่ 3 ข่าวล่าสุดต่อเว็บพอ (เดี๋ยวล้น)
                news_items.append(f"- [News] {entry.title}")
        except: continue
    return "\n".join(news_items)

def analyze_plan():
    print("🚀 Daily Plan (Hybrid) เริ่มทำงาน...")
    
    # ดึงข้อมูล 2 ทาง
    calendar_data = get_forex_calendar()
    news_data = get_market_news()
    
    now_thai = datetime.now(pytz.timezone('Asia/Bangkok'))
    
    # รวมข้อมูลส่งให้ AI
    prompt = f"""
    Context:
    วันนี้คือวันที่: {now_thai.strftime('%d/%m/%Y')} (เวลาไทย {now_thai.strftime('%H:%M')})
    
    ข้อมูล 1: ปฏิทินเศรษฐกิจ (เน้นเวลาและความแรง):
    {calendar_data}
    
    ข้อมูล 2: หัวข้อข่าวล่าสุดจากสำนักข่าว (เน้นอารมณ์ตลาด):
    {news_data}

    Task:
    วิเคราะห์แผนเทรดทองคำ (XAUUSD) โดยใช้ข้อมูลทั้ง 2 ส่วนประกอบกัน

    Instructions:
    1. **เช็คตาราง (Calendar):** ค้นหา Event ที่มีผลกับทอง (CPI, Fed, Jobless, GDP) แปลงเวลาเป็น **"เวลาไทยโดยประมาณ"** และบอกช่วงเวลาที่ควร **"ปิด EA"**
    2. **เช็คอารมณ์ (News):** จากหัวข้อข่าว ตลาดกำลังกังวลเรื่องอะไร? (War? Inflation? Recession?)
    3. **สรุปแผน:** เอามารวมกัน เป็นตารางเวลาหลบข่าว และคำแนะนำทิศทาง

    Output Format (HTML Telegram):
    ☯️ <b>Daily Plan: Hybrid Analysis</b>
    📅 {now_thai.strftime('%d/%m/%Y')}
    ➖➖➖➖➖➖➖➖
    
    🚨 <b>ตารางหลบข่าว (Time Zone):</b>
    
    🕒 <b>[เวลาไทย]</b> : <b>[ชื่อ Event]</b>
    🔥 ความแรง: [High/Medium]
    ⛔ <b>ช่วงปิด EA:</b> [เช่น 19:00 - 20:30]
    
    (ถ้าไม่มีข่าวแรง บอกว่า ✅ ทางสะดวก)
    
    ➖➖➖➖➖➖➖➖
    🌍 <b>จับกระแสข่าว (Market Sentiment):</b>
    [สรุปสั้นๆ ว่าข่าววันนี้พูดถึงอะไร และส่งผลให้ทอง อยากขึ้น หรือ อยากลง]
    
    🧠 <b>คำแนะนำวันนี้:</b>
    [ฟันธงสั้นๆ เช่น "วันนี้เทรดได้ แต่ระวังช่วง 2 ทุ่ม" หรือ "ข่าวแรงมาก นั่งทับมือดีกว่า"]
    """
    
    try:
        response = model.generate_content(prompt)
        send_telegram(response.text.strip())
        print("✅ ส่งแผน Hybrid เรียบร้อย")
        
    except Exception as e:
        print(f"❌ AI Error: {e}")
        send_telegram(f"⚠️ ระบบขัดข้อง: {e}")

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        analyze_plan()
