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

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def get_candles():
    try:
        end = int(datetime.now().timestamp())
        start = end - (86400*7)
        url = "https://cdn.india.deltaex.org/v2/history/candles"
        params = {"resolution": "1d", "symbol": "BTCUSD", "start": start, "end": end}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        result = data.get('result', [])
        return result
    except Exception as e:
        print(f"Candle Error: {e}")
        return []

def get_ist_time():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def format_report():
    candles = get_candles()
    if len(candles) < 2:
        return f"No data available - Got {len(candles)} candles"
    
    # Handle dict format from new API
    if isinstance(candles[-1], dict):
        prev = candles[-2]
        curr = candles[-1]
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
        prev_time = prev[0]/1000; curr_time = curr[0]/1000

    prev_date = datetime.fromtimestamp(prev_time).strftime('%d-%b')
    curr_date = datetime.fromtimestamp(curr_time).strftime('%d-%b-%Y')
    
    same_high = abs(curr_h - prev_h) / prev_h < TOLERANCE if prev_h else False
    same_low = abs(curr_l - prev_l) / prev_l < TOLERANCE if prev_l else False

    if same_high and prev_c > prev_o and curr_c < curr_o:
        return f"🔴 *TOP FORMED*\n{prev_date} + {curr_date}\nHigh {prev_h:.1f} vs {curr_h:.1f}\nAction: SHORT"
    elif same_low and prev_c < prev_o and curr_c > curr_o:
        return f"🟢 *BOTTOM FORMED*\n{prev_date} + {curr_date}\nLow {prev_l:.1f} vs {curr_l:.1f}\nAction: LONG"
    else:
        return f"⚪ *NOT FORMED*\n{prev_date} + {curr_date}\nH: {prev_h:.0f}/{curr_h:.0f} L: {prev_l:.0f}/{curr_l:.0f}\nNo Tweezer Today"

def check_commands():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=10"
        r = requests.get(url, timeout=15).json()
        for update in r.get('result', []):
            last_update_id = update['update_id']
            text = update.get('message', {}).get('text', '').lower()
            if text == '/start':
                send_telegram("✅ *Bot is LIVE*\n\nDaily 5:31 AM IST Tweezer Report will be sent\nBTC Tweezer Top/Bottom Detection\n\nCommands:\n/start - Live check\n/info - Bot info\n/check - Check now\n/today - Today's status\n/help - Help")
            elif text == '/info':
                send_telegram("ℹ️ *TweezerAlert Bot Info*\n\nSymbol: BTCUSD (Delta India)\nStrategy: Tweezer Top/Bottom\nTime: Daily 5:31 AM IST\nTolerance: 0.15%\n\nDeveloped for Trading")
            elif text in ['/check', '/today']:
                report = format_report()
                send_telegram(f"*Current Status:*\n{report}")
            elif text == '/help':
                send_telegram("📋 *Commands:*\n\n/start - Bot live status\n/info - Bot information\n/check or /today - Check tweezer now\n/help - This menu")
    except:
        pass

def bot_loop():
    global last_report_date
    while True:
        check_commands()
        ist_now = get_ist_time()
        if ist_now.hour == 5 and ist_now.minute == 31:
            today_str = ist_now.strftime('%d-%b-%Y')
            if last_report_date != today_str:
                report = format_report()
                send_telegram(f"*5:31 AM Daily Report*\n{report}")
                last_report_date = today_str
        time.sleep(3)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
