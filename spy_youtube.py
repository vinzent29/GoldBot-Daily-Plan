import os
import feedparser
import requests
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from datetime import datetime, timedelta, timezone
import dateutil.parser

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ================= 🎯 รายชื่อช่องเป้าหมาย =================
TARGET_CHANNELS = {
    # สายข่าวโลก
    "Kitco News (ข่าวทองโลก)": "UCN9N8i1A15_XhQ6F-0WJc9w",
    "Bloomberg TV (ศก.โลก)": "UCIALMKvObZNtJ6AmdCLP7Lg",
    # สายเทคนิค & ไทย
    "Rayner Teo (Price Action)": "UCFSn-h8wTnhpKJMteN76Abg",
    "The Secret Sauce (ศก.ไทย)": "UC9WlLtavtOylaWHDl6Uk00Q",
}

# ตั้งค่า AI
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
except:
    pass

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def fetch_rss_feed(channel_id):
    # ใช้ User-Agent ปลอมตัวเป็น Browser เพื่อแก้ 404
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content) if response.status_code == 200 else None
    except:
        return None

def get_transcript(video_id):
    try:
        # 1. ลองใช้ list_transcripts (วิธีใหม่)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 2. พยายามหาภาษาไทย/อังกฤษ (ทั้งคนทำและ Auto)
        try:
            t = transcript_list.find_transcript(['th', 'en', 'a.th', 'a.en'])
        except:
            # 3. ถ้าไม่เจอภาษาที่ชอบ เอาอันแรกสุดที่มี (Fallback)
            t = next(iter(transcript_list))
            
        return " ".join([i['text'] for i in t.fetch()])

    except:
        # 4. ถ้าวิธีใหม่พัง ลองวิธีเก่า (get_transcript)
        try:
            t = YouTubeTranscriptApi.get_transcript(video_id, languages=['th', 'en', 'a.th', 'a.en'])
            return " ".join([i['text'] for i in t])
        except:
            return None

def summarize_video(channel_name, title, transcript, link):
    if not GEMINI_API_KEY: return "⚠️ (No API Key)"
    
    print(f"🤖 AI กำลังสรุป: {title}")
    prompt = f"""
    สรุปคลิป YouTube: "{title}" จากช่อง "{channel_name}"
    
    เนื้อหา (Transcript):
    {transcript[:12000]} (ตัดตอนมา)

    คำสั่ง:
    1. สรุปประเด็นสำคัญเกี่ยวกับ "ราคาทองคำ" หรือ "ทิศทางเศรษฐกิจ"
    2. ถ้ามีตัวเลขแนวรับ-แนวต้าน หรือคำแนะนำ (Buy/Sell) ให้ระบุ
    3. เขียนเป็นภาษาไทย อ่านง่ายๆ ใช้ Bullet point
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Error: {e}"

def check_youtube():
    print("🕵️‍♂️ Spy Bot เริ่มทำงาน...")
    
    # เช็คย้อนหลัง 24 ชั่วโมง (เผื่อรันครั้งแรกจะได้เห็นผลเลย)
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(hours=24) 

    for name, channel_id in TARGET_CHANNELS.items():
        feed = fetch_rss_feed(channel_id)
        
        if not feed or not feed.entries:
            print(f"❌ {name}: เข้าถึง Feed ไม่ได้ (อาจจะไม่มีคลิปใหม่)")
            continue

        # เช็คแค่คลิปล่าสุด 1 คลิปพอ
        entry = feed.entries[0]
        try:
            pub_date = dateutil.parser.parse(entry.published)
        except:
            continue

        # เงื่อนไข: ต้องเป็นคลิปใหม่ใน 24 ชม. ที่ผ่านมา
        if pub_date > time_limit:
            print(f"🎥 เจอคลิปใหม่! [{name}] {entry.title}")
            
            transcript = get_transcript(entry.yt_videoid)
            
            if transcript:
                summary = summarize_video(name, entry.title, transcript, entry.link)
                msg = f"🎥 <b>Spy Report: {name}</b>\n\n📺 <b>{entry.title}</b>\n\n📝 <b>สรุปเนื้อหา:</b>\n{summary}\n\n🔗 <a href='{entry.link}'>ดูคลิปเต็ม</a>"
                send_telegram(msg)
            else:
                print(f"   ❌ คลิปนี้ไม่มีซับให้อ่าน")
                # ส่งแจ้งเตือนแม้ไม่มีซับ (เผื่อคุณอยากกดดูเอง)
                msg = f"🎥 <b>คลิปใหม่! ({name})</b>\n📺 {entry.title}\n⚠️ (ไม่มี Subtitle ให้ AI อ่าน)\n🔗 {entry.link}"
                send_telegram(msg)
        else:
            print(f"   💤 {name}: ยังไม่มีคลิปใหม่ (ล่าสุดเมื่อ {pub_date})")

if __name__ == "__main__":
    if TELEGRAM_TOKEN: check_youtube()
    else: print("❌ ไม่พบ Key")