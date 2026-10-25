import requests, time, os
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Tweezer Bot Running - 5:31 AM IST"

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
        print(f"Telegram Sent: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_candles():
    try:
        end = int(datetime.now(timezone.utc).timestamp())
        start = end - (86400*10) # 10 days for safety
        url = "https://cdn.india.deltaex.org/v2/history/candles"
        params = {"resolution": "1d", "symbol": "BTCUSD", "start": start, "end": end}
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        result = data.get('result', [])
        print(f"Got {len(result)} candles")
        return result
    except Exception as e:
        print(f"Candle Error: {e}")
        return []

def get_ist_time():
    return datetime.now(timezone.utc).astimezone(IST)

def format_report():
    candles = get_candles()
    if len(candles) < 2:
        return f"⚠️ No data - Got {len(candles)} candles. API Issue."

    try:
        if isinstance(candles[-1], dict):
            prev = candles[-2]; curr = candles[-1]
            prev_o = float(prev.get('open', prev.get('o', 0)))
            prev_h = float(prev.get('high', prev.get('h', 0)))
            prev_l = float(prev.get('low', prev.get('l', 0)))
            prev_c = float(prev.get('close', prev.get('c', 0)))
            curr_o = float(curr.get('open', curr.get('o', 0)))
            curr_h = float(curr.get('high', curr.get('h', 0)))
            curr_l = float(curr.get('low', curr.get('l', 0)))
            curr_c = float(curr.get('close', curr.get('c', 0)))
            prev_time = prev.get('time', 0)
            curr_time = curr.get('time', 0)
        else:
            prev = candles[-2]; curr = candles[-1]
            prev_o, prev_h, prev_l, prev_c = float(prev[1]), float(prev[2]), float(prev[3]), float(prev[4])
            curr_o, curr_h, curr_l, curr_c = float(curr[1]), float(curr[2]), float(curr[3]), float(curr[4])
            prev_time = prev[0]/1000 if prev[0] > 1e12 else prev[0]
            curr_time = curr[0]/1000 if curr[0] > 1e12 else curr[0]

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
        return f"Error in format_report: {e}"

def check_commands():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=10"
        r = requests.get(url, timeout=15).json()
        for update in r.get('result', []):
            last_update_id = update['update_id']
            text = update.get('message', {}).get('text', '').lower()
            if text == '/start':
                send_telegram("✅ *Bot is LIVE*\nDaily 5:31 AM IST Tweezer Report\n/check - Check now")
            elif text in ['/check', '/today', '/info', '/help']:
                report = format_report()
                send_telegram(f"*Current Status:*\n{report}")
    except Exception as e:
        print(f"Command Error: {e}")

def bot_loop():
    global last_report_date
    print("Bot Loop Started...")
    # Send startup message
    send_telegram("🚀 *Bot Restarted & Live on Render*")
    while True:
        try:
            check_commands()
            ist_now = get_ist_time()
            # FIX: 5:31 to 5:35 window + date check
            if ist_now.hour == 5 and 31 <= ist_now.minute <= 35:
                today_str = ist_now.strftime('%d-%b-%Y')
                if last_report_date != today_str:
                    print(f"Triggering report for {today_str}")
                    report = format_report()
                    send_telegram(f"*5:31 AM Daily Report*\n{report}")
                    last_report_date = today_str
        except Exception as e:
            print(f"Loop Error: {e}")
        time.sleep(10)

# IMPORTANT: Thread start here, not inside __main__
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
