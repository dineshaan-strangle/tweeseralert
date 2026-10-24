import requests, time, os
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Tweezer Bot - 5:31 AM IST Running!"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOLERANCE = 0.0015
last_report_date = ""

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def get_candles():
    url = "https://api.india.delta.exchange/v2/history/candles"
    params = {
        "resolution": "1d",
        "symbol": "BTCUSD",
        "start": int((datetime.now().timestamp() - 86400*6)*1000),
        "end": int(datetime.now().timestamp()*1000)
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json().get('result', [])
    except:
        return []

def get_ist_time():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)

def bot_loop():
    global last_report_date
    while True:
        ist_now = get_ist_time()
        if ist_now.hour == 5 and ist_now.minute == 31:
            today_str = ist_now.strftime('%d-%b-%Y')
            if last_report_date != today_str:
                candles = get_candles()
                if len(candles) >= 3:
                    prev_closed = candles[-3]
                    curr_closed = candles[-2]
                    prev_o = float(prev_closed[1])
                    prev_h = float(prev_closed[2])
                    prev_l = float(prev_closed[3])
                    prev_c = float(prev_closed[4])
                    curr_o = float(curr_closed[1])
                    curr_h = float(curr_closed[2])
                    curr_l = float(curr_closed[3])
                    curr_c = float(curr_closed[4])
                    prev_date = datetime.fromtimestamp(prev_closed[0]/1000).strftime('%d-%b')
                    curr_date = datetime.fromtimestamp(curr_closed[0]/1000).strftime('%d-%b-%Y')
                    same_high = abs(curr_h - prev_h) / prev_h < TOLERANCE
                    same_low = abs(curr_l - prev_l) / prev_l < TOLERANCE
                    if same_high and prev_c > prev_o and curr_c < curr_o:
                        send_telegram(f"🔴 *5:31 AM - TOP FORMED*\n{prev_date}+{curr_date}\nHigh {prev_h:.1f} vs {curr_h:.1f}\nAction: SHORT")
                    elif same_low and prev_c < prev_o and curr_c > curr_o:
                        send_telegram(f"🟢 *5:31 AM - BOTTOM FORMED*\n{prev_date}+{curr_date}\nLow {prev_l:.1f} vs {curr_l:.1f}\nAction: LONG")
                    else:
                        send_telegram(f"⚪ *5:31 AM - NOT FORMED*\n{prev_date}+{curr_date}\nNo Tweezer Today")
                    last_report_date = today_str
        time.sleep(30)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
