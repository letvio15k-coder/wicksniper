import os, time, requests, threading
import pandas as pd
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- WEB GIẢ ĐỂ CHẠY FREE TRÊN RENDER ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Live - 15m + 1h")

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()
# ----------------------------------------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALS = ["15m", "1h"]
WICK_MIN, BODY_MAX, VOL_X = 0.60, 0.35, 1.4
BINANCE_API = "https://api.binance.com"
sent_cache = {}

def send_tele(msg):
    print(msg)
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def get_top_symbols(limit=100):
    try:
        r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=10).json()
        usdt = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol'] and 'DOWN' not in x['symbol']]
        usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
        return [x['symbol'] for x in usdt[:limit]]
    except:
        return ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","ARBUSDT","OPUSDT","DOGEUSDT","XRPUSDT","PEPEUSDT","WIFUSDT","ENAUSDT","AVAXUSDT"]

def get_klines(sym, interval):
    r = requests.get(f"{BINANCE_API}/api/v3/klines", params={"symbol": sym, "interval": interval, "limit": 50}, timeout=10).json()
    df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    return df

def is_wick(c, avg_vol):
    o,h,l,close,v = c['o'],c['h'],c['l'],c['c'],c['v']
    total = h-l
    if total==0: return None
    body = abs(close-o); upper = h-max(o,close); lower = min(o,close)-l
    wr = max(upper,lower)/total; br = body/total
    if wr>=WICK_MIN and br<=BODY_MAX and v>=avg_vol*VOL_X:
        return ("🟢 QUÉT ĐÁY" if lower>upper else "🔴 QUÉT ĐỈNH"), wr, br
    return None

def scan(interval, symbols):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quet {interval}")
    for sym in symbols:
        try:
            df = get_klines(sym, interval)
            if len(df)<25: continue
            avg_vol = df['v'].rolling(20).mean().iloc[-2]
            last = df.iloc[-1]
            res = is_wick(last, avg_vol)
            if res:
                side, wr, br = res
                key = f"{sym}_{interval}_{side}"
                if key in sent_cache and time.time()-sent_cache[key]<1800: continue
                sent_cache[key]=time.time()
                send_tele(f"{side} | {sym} {interval}\n{'⚡ SCALP 15m' if interval=='15m' else '💎 TREND 1h'}\nRâu {wr*100:.0f}% | Thân {br*100:.0f}% | Vol x{last['v']/avg_vol:.1f}\nGiá ${last['c']}")
            time.sleep(0.2)
        except Exception as e:
            print(f"Loi {sym}: {e}")

if __name__ == "__main__":
    syms = get_top_symbols(100)
    send_tele(f"✅ Bot FREE Live - {len(syms)} coin - {' + '.join(INTERVALS)}")
    while True:
        for itv in INTERVALS: scan(itv, syms)
        time.sleep(120)
