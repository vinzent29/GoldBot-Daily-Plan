import os
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ✅ ใช้ Model ตัวเดียวกับ Local (ตามที่คุณยืนยันว่าเวิร์ก)
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-flash-latest')
except:
    pass

# แหล่งข่าวเดียวกับ Local เป๊ะๆ
RSS_SOURCES = [
    "https://www.forexlive.com/feed/news",           # มักมีสรุป Calendar ช่วงเช้า
    "https://www.fxstreet.com/rss/news/assets/gold", # วิเคราะห์กราฟ
    "https://www.investing.com/rss/news_1.rss"       # ข่าว Forex ทั่วไป
]

# ฟังก์ชันเวลาไทย (สูตรเดียวกับ Local)
def get_thai_time():
    return datetime.now(timezone(timedelta(hours=7)))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML', 
        'disable_web_page_preview': True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def analyze_plan():
    print("🚀 Daily Plan (Local Clone) เริ่มทำงาน...")
    
    combined_news = ""
    print("🛡️ กำลังสแกนหา 'กับระเบิด' (Event) ในตลาด...")

    # 1. กวาดหัวข้อข่าว (Logic เดียวกับ Local)
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            # อ่าน 5-7 ข่าวเพื่อหา Keyword สำคัญ
            for entry in feed.entries[:7]: 
                combined_news += f"- {entry.title} (Link: {entry.link})\n"
        except Exception as e:
            print(f"   ⚠️ Feed Error ({url}): {e}")

    now_thai = get_thai_time()
    date_str = now_thai.strftime('%d/%m/%Y')
    
    # 2. Prompt ต้นฉบับจาก Local (ที่คุณชอบ)
    prompt = f"""
    Context:
    วันนี้คือวันที่: {date_str} (เวลาไทยปัจจุบัน {now_thai.strftime('%H:%M')})
    
    News Feed (หัวข้อข่าววันนี้):
    {combined_news}

    Task:
    "ค้นหาตารางตัวเลขเศรษฐกิจ (Economic Calendar) ที่จะประกาศในวันนี้ เพื่อเตือนคนใช้ EA ให้ปิดหนีข่าว"

    Instructions:
    1. **Identify Events:** ค้นหา Keyword: CPI, PPI, NFP, Payrolls, FOMC, Rate Decision, GDP, Retail Sales, Unemployment Claims, Data Deluge
    2. **Convert Time:** ระบุเวลาที่ข่าวจะออกเป็น **"เวลาไทย (GMT+7)"** (โดยใช้ความรู้รอบตัวของ AI + ข้อมูลในข่าว)
       *สำคัญ: ถ้าข่าวไม่บอกเวลา ให้ใช้ knowledge ของคุณระบุเวลามาตรฐานของข่าวนั้นๆ (เช่น US Data มักมา 19:30 หรือ 20:30 น.)*
    3. **Define Impact:** ระบุความแรง (🔴 High / 🟡 Medium)
    4. **No-Trade Zone:** แนะนำช่วงเวลาที่ต้อง **"ปิด EA"** (เช่น ก่อนข่าว 30 นาที - หลังข่าว 30 นาที)

    Output Format (HTML Thai):
    🛡️ <b>ตารางหลบข่าวเปิด EA</b> ({date_str})
    ➖➖➖➖➖➖➖➖
    
    🚨 <b>Event อันตรายวันนี้ (High Impact):</b>
    
    🕒 <b>เวลาไทย:</b> [ระบุเวลา เช่น 19:30 น.]
    💣 <b>เหตุการณ์:</b> [ชื่อข่าว เช่น USD CPI]
    🔥 <b>ความแรง:</b> 🔴🔴🔴 (High)
    ⛔ <b>ช่วงปิด EA:</b> [เช่น 19:00 - 20:30 น.]
    *วิเคราะห์:* [สั้นๆ ว่าทำไมข่าวนี้น่ากลัว]
    
    (ไล่ลงมาเรื่อยๆ / ถ้าไม่มีข่าวแดงเลย ให้บอกว่า "✅ วันนี้ทางสะดวก ไม่มีข่าวแดง")
    
    ➖➖➖➖➖➖➖➖
    📉 <b>วิเคราะห์ความเสี่ยงรวม:</b>
    (สรุปว่าวันนี้กราฟจะวิ่งแรงช่วงไหน และช่วงไหนค่อนข้างปลอดภัย Safe Zone)
    
    🤖 <b>คำแนะนำสุดท้าย:</b> (เปิด EA ได้ไหม หรือควรนั่งทับมือ)
    """
    
    try:
        response = model.generate_content(prompt)
        ai_plan = response.text.strip()
        
        send_telegram(ai_plan)
        print("✅ ส่งแผนเรียบร้อย")
        
    except Exception as e:
        print(f"❌ AI Error: {e}")
        # ระบบสำรองเผื่อ Model Name มีปัญหาอีก
        if "404" in str(e):
             print("⚠️ Model Error: กำลังลองเปลี่ยน Model เป็น gemini-1.5-flash แทน...")
             try:
                 # Backup plan: ใช้รุ่นมาตรฐานแต่ Prompt เดิม
                 backup_model = genai.GenerativeModel('gemini-1.5-flash')
                 response = backup_model.generate_content(prompt)
                 send_telegram(response.text.strip())
             except:
                 send_telegram(f"❌ AI Error (Final): {e}")

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        analyze_plan()
    else:
        print("❌ ไม่พบ Key")
