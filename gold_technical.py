import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests

# ================= 🔐 ดึง Key จาก GitHub Secrets =================
# ระบบจะดึงจากตู้เซฟ Secrets อัตโนมัติ
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# สัญลักษณ์ทองคำ (Gold Futures)
SYMBOL = "GC=F"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        print(f"❌ Error sending msg: {e}")

def check_technical():
    print(f"📈 กำลังดึงกราฟ {SYMBOL} (Timeframe 1H)...")
    
    try:
        # 1. ดึงข้อมูลย้อนหลัง 5 วัน
        df = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
        
        if df.empty:
            print("❌ ไม่พบข้อมูลราคา (Yahoo Finance อาจมีปัญหา)")
            return

        # 🛠️ [IMPORTANT] แก้บั๊ก yfinance คืนค่าตารางซ้อน (MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        return

    # 2. คำนวณ Indicators
    # RSI (14)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # MACD (12, 26, 9)
    macd_df = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd_df], axis=1)
    
    # EMA (50)
    df['EMA_50'] = ta.ema(df['Close'], length=50)

    # 3. ดึงค่าแท่งล่าสุด (Real-time)
    try:
        last_bar = df.iloc[-1]
        
        # แปลงค่าเป็นตัวเลข (Float) ให้ชัวร์
        curr_price = float(last_bar['Close'])
        rsi_val = float(last_bar['RSI'])
        macd_val = float(last_bar['MACD_12_26_9'])
        macd_signal = float(last_bar['MACDs_12_26_9'])
        ema_50 = float(last_bar['EMA_50'])
    except Exception as e:
        print(f"❌ Error parsing data: {e}")
        return

    # 4. วิเคราะห์สัญญาณ (Signal Logic)
    signals = []
    
    # --- เงื่อนไข RSI ---
    if rsi_val > 70:
        signals.append(f"⚠️ <b>RSI Overbought</b> ({rsi_val:.1f}) ระวังโดนทุบ!")
    elif rsi_val < 30:
        signals.append(f"✅ <b>RSI Oversold</b> ({rsi_val:.1f}) ราคาน่าจะดีด!")

    # --- เงื่อนไข MACD Cross ---
    # เทียบกับแท่งก่อนหน้า (Previous Bar)
    prev_bar = df.iloc[-2]
    prev_macd = float(prev_bar['MACD_12_26_9'])
    prev_signal = float(prev_bar['MACDs_12_26_9'])

    if prev_macd < prev_signal and macd_val > macd_signal:
        signals.append("🚀 <b>MACD Golden Cross</b> (ตัดขึ้น)")
    elif prev_macd > prev_signal and macd_val < macd_signal:
        signals.append("🔻 <b>MACD Death Cross</b> (ตัดลง)")

    # --- เช็ค Trend ---
    trend = "ขาขึ้น 🐂" if curr_price > ema_50 else "ขาลง 🐻"

    # 5. ส่งแจ้งเตือน (เฉพาะเมื่อเจอสัญญาณ)
    if signals:
        print(f"🔔 เจอ {len(signals)} สัญญาณ! กำลังส่ง Telegram...")
        
        msg_body = "\n".join([f"- {s}" for s in signals])
        msg = f"""
📈 <b>Gold Technical Alert</b>
➖➖➖➖➖➖➖➖
💰 <b>ราคา:</b> ${curr_price:.2f}
🧭 <b>เทรนด์:</b> {trend} (EMA50)

⚡ <b>สัญญาณที่พบ:</b>
{msg_body}

📊 <b>Indicators:</b>
RSI: {rsi_val:.1f} | MACD: {macd_val:.2f}
"""
        send_telegram(msg)
    else:
        # Log ไว้ดูใน GitHub Actions (แต่ไม่ส่งเข้ามือถือ)
        print(f"💤 กราฟนิ่งๆ (Price=${curr_price:.2f}, RSI={rsi_val:.1f})")

if __name__ == "__main__":
    if TELEGRAM_TOKEN and CHAT_ID:
        check_technical()
    else:
        print("❌ ไม่พบ Key (โปรดตั้งค่า Secrets ใน GitHub)")
