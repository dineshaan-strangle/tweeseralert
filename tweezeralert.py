import requests, time, os
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Tweezer Bot Running - 5:31 AM IST - Binance Data"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOLERANCE = 0.0015
last_report_date = ""
last_update_id = 0
IST = timezone(timedelta(hours=5, minutes=30))

def send_telegram(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("BOT_TOKEN/CHAT_ID Missing!")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"Telegram Sent: {r.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_candles():
    try:
        # BINANCE - Most reliable
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 5}
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        # Binance format: [open_time, open, high, low, close, ...]
        # Convert to our format
        result = []
        for k in data:
            result.append({
                'time': k[0]/1000, # ms to sec
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4])
            })
        print(f"Got {len(result)} candles from Binance")
        return result
    except Exception as e:
        print(f"Candle Error: {e}")
        return []

def get_ist_time():
    return datetime.now(timezone.utc).astimezone(IST)

def format_report():
    candles = get_candles()
    if len(candles) < 2:
        return f"⚠️ No data - Got {len(candles)} candles"

    try:
        prev = candles[-2]
        curr = candles[-1]
        prev_o = prev['open']; prev_h = prev['high']; prev_l = prev['low']; prev_c = prev['close']
        curr_o = curr['open']; curr_h = curr['high']; curr_l = curr['low']; curr_c = curr['close']
        prev_time = prev['time']
        curr_time = curr['time']

        prev_date = datetime.fromtimestamp(prev_time, tz=IST).strftime('%d-%b')
        curr_date = datetime.fromtimestamp(curr_time, tz=IST).strftime('%d-%b-%Y')
        
        same_high = abs(curr_h - prev_h) / prev_h < TOLERANCE if prev_h else False
        same_low = abs(curr_l - prev_l) / prev_l < TOLERANCE if prev_l else False

        if same_high and prev_c > prev_o and curr_c < curr_o:
            return f"🔴 *TOP FORMED*\n{prev_date} + {curr_date}\nHigh {prev_h:.1f} vs {curr_h:.1f}\nAction: SHORT"
        elif same_low and prev_c < prev_o and curr_c > curr_o:
            return f"🟢 *BOTTOM FORMED*\n{prev_date} + {curr_date}\nLow {prev_l:.1f} vs {curr_l:.1f}\nAction: LONG"
        else:
            return f"⚪ *NOT FORMED*\n{prev_date} + {curr_date}\nH: {prev_h:.0f}/{curr_h:.0f} L: {prev_l:.0f}/{curr_l:.0f}\nNo Tweezer Today"
    except Exception as e:
        print(f"Format Error: {e}")
        return f"Error: {e}"

def check_commands():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=10"
        r = requests.get(url, timeout=15).json()
        for update in r.get('result', []):
            last_update_id = update['update_id']
            text = update.get('message', {}).get('text', '').lower()
            if text == '/start':
                send_telegram("✅ *Bot is LIVE (Binance Data)*\nDaily 5:31 AM IST\n/check - Check now")
            elif text in ['/check', '/today', '/info', '/help']:
                report = format_report()
                send_telegram(f"*Current Status:*\n{report}")
    except Exception as e:
        print(f"Command Error: {e}")

def bot_loop():
    global last_report_date
    print("Bot Loop Started...")
    time.sleep(5)
    send_telegram("🚀 *Bot Restarted - Binance Live Data (IST)*")
    while True:
        try:
            check_commands()
            ist_now = get_ist_time()
            if ist_now.hour == 5 and 31 <= ist_now.minute <= 35:
                today_str = ist_now.strftime('%d-%b-%Y')
                if last_report_date != today_str:
                    print(f"Triggering 5:31 report for {today_str}")
                    report = format_report()
                    send_telegram(f"*5:31 AM Daily Report (IST)*\n{report}")
                    last_report_date = today_str
        except Exception as e:
            print(f"Loop Error: {e}")
        time.sleep(10)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
