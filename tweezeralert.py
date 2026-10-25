import requests, time, os
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home():
    return "Tweezer Bot Running - 5:31 AM IST - Binance Vision"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOLERANCE = 0.0015
last_report_date = ""
last_update_id = 0
IST = timezone(timedelta(hours=5, minutes=30))

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_candles():
    # Try 3 APIs one by one
    endpoints = [
        ("https://data-api.binance.vision/api/v3/klines", {"symbol": "BTCUSDT", "interval": "1d", "limit": 5}),
        ("https://api.binance.com/api/v3/klines", {"symbol": "BTCUSDT", "interval": "1d", "limit": 5}),
        ("https://api.bybit.com/v5/market/kline", {"category": "spot", "symbol": "BTCUSDT", "interval": "D", "limit": 5})
    ]
    
    for url, params in endpoints:
        try:
            print(f"Trying {url}")
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            
            # Binance format
            if isinstance(data, list) and len(data) > 0:
                result = []
                for k in data:
                    result.append({
                        'time': k[0]/1000,
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4])
                    })
                print(f"Success from {url} - {len(result)} candles")
                return result
            
            # Bybit format
            if isinstance(data, dict) and 'result' in data:
                bybit_list = data['result'].get('list', [])
                if bybit_list:
                    result = []
                    for k in reversed(bybit_list): # Bybit newest last? reverse
                        result.append({
                            'time': int(k[0])/1000,
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4])
                        })
                    print(f"Success from Bybit - {len(result)} candles")
                    return sorted(result, key=lambda x: x['time'])

        except Exception as e:
            print(f"Failed {url}: {e}")
            continue
    
    print("All endpoints failed")
    return []

def get_ist_time():
    return datetime.now(timezone.utc).astimezone(IST)

def format_report():
    candles = get_candles()
    if len(candles) < 2:
        return f"⚠️ No data - Got {len(candles)} candles. APIs blocked."

    prev = candles[-2]; curr = candles[-1]
    prev_o, prev_h, prev_l, prev_c = prev['open'], prev['high'], prev['low'], prev['close']
    curr_o, curr_h, curr_l, curr_c = curr['open'], curr['high'], curr['low'], curr['close']
    
    prev_date = datetime.fromtimestamp(prev['time'], tz=IST).strftime('%d-%b')
    curr_date = datetime.fromtimestamp(curr['time'], tz=IST).strftime('%d-%b-%Y')
    
    same_high = abs(curr_h - prev_h) / prev_h < TOLERANCE
    same_low = abs(curr_l - prev_l) / prev_l < TOLERANCE

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
                send_telegram("✅ *Bot LIVE - Binance Vision*\n/check - Check now")
            elif text in ['/check', '/today']:
                send_telegram(f"*Current Status:*\n{format_report()}")
    except:
        pass

def bot_loop():
    global last_report_date
    print("Bot Loop Started...")
    time.sleep(3)
    send_telegram("🚀 *Bot Restarted - Binance Vision Live*")
    while True:
        try:
            check_commands()
            ist_now = get_ist_time()
            if ist_now.hour == 5 and 31 <= ist_now.minute <= 35:
                today_str = ist_now.strftime('%d-%b-%Y')
                if last_report_date != today_str:
                    send_telegram(f"*5:31 AM Report (IST)*\n{format_report()}")
                    last_report_date = today_str
        except Exception as e:
            print(f"Loop Error: {e}")
        time.sleep(10)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
