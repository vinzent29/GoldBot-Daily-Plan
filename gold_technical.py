import os
import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ตั้งค่า AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    pass

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Error sending msg: {e}")

def get_data():
    # ดึงกราฟทองคำรายชั่วโมง (1h) ย้อนหลัง 7 วัน
    df = yf.download("XAUUSD=X", period="7d", interval="1h", progress=False)
    if df.empty: return None
    
    # คำนวณอินดิเคเตอร์พื้นฐาน
    df['RSI'] = df.ta.rsi(length=14)
    df.ta.macd(append=True) # ได้ MACD_12_26_9, MACDh, MACDs
    df['EMA_200'] = df.ta.ema(length=200)
    
    # 🌟 1. คำนวณความผันผวน (ATR) สำหรับสายซิ่ง
    df['ATR'] = df.ta.atr(length=14)
    
    # 🌟 2. คำนวณ Swing High/Low ย้อนหลัง 20 แท่ง สำหรับสายโครงสร้าง
    df['Swing_High'] = df['High'].rolling(window=20).max()
    df['Swing_Low'] = df['Low'].rolling(window=20).min()
    
    return df.iloc[-1] # ส่งคืนแท่งล่าสุด

def analyze_market():
    print("📈 Technical Analyst เริ่มทำงาน...")
    
    data = get_data()
    if data is None:
        print("❌ ดึงข้อมูลกราฟไม่ได้")
        return

    close_price = data['Close']
    rsi = data['RSI']
    macd_line = data['MACD_12_26_9']
    signal_line = data['MACDs_12_26_9']
    ema_200 = data['EMA_200']
    atr = data['ATR']
    swing_high = data['Swing_High']
    swing_low = data['Swing_Low']

    # --- คำนวณจุด TP/SL ทั้ง 2 แบบ (ล่วงหน้า) ---
    
    # แบบที่ 1: สาย Volatility (ATR)
    # สมมติถ้าเล่น Buy
    buy_sl_atr = close_price - (atr * 2) 
    buy_tp_atr = close_price + (atr * 3)
    # สมมติถ้าเล่น Sell
    sell_sl_atr = close_price + (atr * 2)
    sell_tp_atr = close_price - (atr * 3)

    # แบบที่ 2: สาย Structure (Swing High/Low)
    # สมมติถ้าเล่น Buy (SL ที่โลว์เดิม)
    buy_sl_swing = swing_low
    buy_tp_swing = close_price + (close_price - swing_low) * 2 # RR 1:2
    # สมมติถ้าเล่น Sell (SL ที่ไฮเดิม)
    sell_sl_swing = swing_high
    sell_tp_swing = close_price - (swing_high - close_price) * 2 # RR 1:2

    # สร้าง Prompt ให้ AI
    prompt = f"""
    คุณคือผู้เชี่ยวชาญด้าน Technical Analysis ของทองคำ (XAUUSD)
    
    ข้อมูลตลาดล่าสุด (Timeframe 1H):
    - ราคาปัจจุบัน: {close_price:.2f}
    - RSI (14): {rsi:.2f}
    - MACD Line: {macd_line:.4f} / Signal Line: {signal_line:.4f}
    - EMA 200: {ema_200:.2f} (เทรนด์หลัก: {"ขาขึ้น" if close_price > ema_200 else "ขาลง"})
    
    แผนสำรองที่เตรียมไว้ (Strategic Plan):
    1. แผน ATR (ตามความผันผวน):
       - ถ้า BUY: SL={buy_sl_atr:.2f}, TP={buy_tp_atr:.2f}
       - ถ้า SELL: SL={sell_sl_atr:.2f}, TP={sell_tp_atr:.2f}
       
    2. แผน Swing Structure (ตามแนวรับต้าน):
       - Swing High ล่าสุด: {swing_high:.2f}
       - Swing Low ล่าสุด: {swing_low:.2f}

    คำสั่ง:
    1. วิเคราะห์แนวโน้มปัจจุบัน (Trend & Momentum) ว่าควร Wait, Buy หรือ Sell
    2. แนะนำ "Setup ที่ดีที่สุด" โดยเลือกตัวเลขจากแผน ATR หรือ Swing มาผสมกันตามความเหมาะสม
    3. ระบุเหตุผลสั้นๆ เช่น "ใช้ SL แบบ Swing เพราะปลอดภัยกว่า" หรือ "ใช้แบบ ATR เพราะตลาดผันผวน"
    4. สรุปเป็นข้อความสั้นๆ ภาษาไทย เข้าใจง่าย ใส่ Emoji
    """
    
    try:
        response = model.generate_content(prompt)
        ai_analysis = response.text
        
        # ส่งเข้า Telegram
        msg = f"""
📈 <b>Technical Analyst (1H)</b>
💰 ราคา: <b>{close_price:.2f}</b>
➖➖➖➖➖➖➖➖
📊 <b>Indicators:</b>
• RSI: {rsi:.1f}
• MACD: {macd_line:.2f} / {signal_line:.2f}
• Trend: {"🟢 Bullish" if close_price > ema_200 else "🔴 Bearish"}

🧠 <b>AI Strategy:</b>
{ai_analysis}

⚠️ <i>(การลงทุนมีความเสี่ยง โปรดใช้วิจารณญาณ)</i>
"""
        send_telegram(msg)
        print("✅ ส่งวิเคราะห์เรียบร้อย")
        
    except Exception as e:
        print(f"❌ AI Error: {e}")

if __name__ == "__main__":
    if TELEGRAM_TOKEN:
        analyze_market()
    else:
        print("❌ ไม่พบ Key")
