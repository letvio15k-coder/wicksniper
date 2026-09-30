import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# --- WEB GIẢ FIX 501 HEAD + GET ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type","text/plain")
        self.end_headers()
        self.wfile.write(f"Wick Sniper 100 coin Live - {datetime.now()}".encode())

    def do_HEAD(self):
        # FIX LỖI 501 Not Implemented trong ảnh của bạn
        self.send_response(200)
        self.send_header("Content-type","text/plain")
        self.end_headers()

    def log_message(self,*a): return

def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"WEB OPEN port {port} - Ready for UptimeRobot HEAD")
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# --- BOT CHÍNH ---
import time, requests
import pandas as pd

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALS = ["15m", "1h"]
WICK_MIN, BODY_MAX, VOL_X = 0.60, 0.35, 1.4
BINANCE_API = "https://data-api.binance.vision"
sent_cache = {}
top_symbols = []

def send_tele(msg, cid=None):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": cid or CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    print(msg)

def telegram_poller():
    last_id = 0
    while True:
        try:
            if not TELEGRAM_TOKEN: time.sleep(10); continue
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id+1}&timeout=30", timeout=35).json()
            if not r.get("ok"): time.sleep(5); continue
            for upd in r.get("result", []):
                last_id = upd["update_id"]
                msg = upd.get("message", {})
                text = (msg.get("text") or "").lower()
                cid = msg.get("chat", {}).get("id")
                if not text or not cid: continue
                if "/start" in text:
                    send_tele(f"✅ WICK SNIPER đã bật\nĐang quét {len(top_symbols)} coin\nKhung: {', '.join(INTERVALS)}\nGõ /status", cid)
                elif "/status" in text:
                    send_tele(f"🟢 Live {len(top_symbols)} coin - Cache {len(sent_cache)}", cid)
        except: time.sleep(5)

def get_top_symbols(limit=100):
    hard_100 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","PEPEUSDT","WIFUSDT","AVAXUSDT","SHIBUSDT","ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","ENAUSDT","TAOUSDT","RENDERSUSDT","FETUSDT","ARUSDT","SUIUSDT","SEIUSDT","TIAUSDT","WLDUSDT","STXUSDT","INJUSDT","FILUSDT","ETCUSDT","ATOMUSDT","IMXUSDT","AAVEUSDT","RUNEUSDT","GRTUSDT","LDOUSDT","MKRUSDT","ORDIUSDT","JUPUSDT","PYTHUSDT","BONKUSDT","FLOKIUSDT","1000SATSUSDT","1000PEPEUSDT","STRKUSDT","MANTAUSDT","ALTUSDT","JTOUSDT","ONDOUSDT","WUSDT","ZKUSDT","ZROUSDT","IOUSDT","NOTUSDT","TONUSDT","PENDLEUSDT","CFXUSDT","CHZUSDT","FLOWUSDT","KASUSDT","KAVAUSDT","THETAUSDT","AXSUSDT","SANDUSDT","MANAUSDT","EOSUSDT","KLAYUSDT","EGLDUSDT","XTZUSDT","NEOUSDT","IOTAUSDT","XLMUSDT","HBARUSDT","VETUSDT","ALGOUSDT","QNTUSDT","AGIXUSDT","OCEANUSDT","BLURUSDT","DYDXUSDT","GMXUSDT","1INCHUSDT","COMPUSDT","SNXUSDT","CRVUSDT","LRCUSDT","ENJUSDT","GALAUSDT","YGGUSDT","MAGICUSDT","BEAMXUSDT","RONINUSDT","PIXELUSDT"]
    try:
        r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=10).json()
        usdt = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol']]
        usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
        live = [x['symbol'] for x in usdt[:limit]]
        if len(live) >= 80: return live
    except: pass
    return hard_100[:limit]

def get_klines(sym, interval):
    r = requests.get(f"{BINANCE_API}/api/v3/klines", params={"symbol": sym, "interval": interval, "limit": 50}, timeout=10).json()
    df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    return df

def scan(interval, symbols):
    for sym in symbols:
        try:
            df = get_klines(sym, interval)
            if len(df)<25: continue
            avg_vol = df['v'].rolling(20).mean().iloc[-2]
            last = df.iloc[-1]
            total = last['h']-last['l']
            if total==0: continue
            body = abs(last['c']-last['o'])
            upper = last['h']-max(last['o'],last['c'])
            lower = min(last['o'],last['c'])-last['l']
            wr = max(upper,lower)/total
            br = body/total
            if wr>=WICK_MIN and br<=BODY_MAX and last['v']>=avg_vol*VOL_X:
                key = f"{sym}_{interval}"
                if key in sent_cache and time.time()-sent_cache[key]<1800: continue
                sent_cache[key]=time.time()
                side = "🟢 QUÉT ĐÁY" if lower>upper else "🔴 QUÉT ĐỈNH"
                send_tele(f"{side} | {sym} {interval}\nRâu {wr*100:.0f}% | Vol x{last['v']/avg_vol:.1f}\nGiá ${last['c']}")
            time.sleep(0.15)
        except: pass

if __name__ == "__main__":
    top_symbols = get_top_symbols(100)
    threading.Thread(target=telegram_poller, daemon=True).start()
    send_tele(f"✅ WICK SNIPER đã bật - Fix 501 HEAD\nQuét {len(top_symbols)} coin - {' + '.join(INTERVALS)}")
    while True:
        for itv in INTERVALS:
            scan(itv, top_symbols)
        time.sleep(120)
