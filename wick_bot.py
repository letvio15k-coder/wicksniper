import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# MỞ CỔNG NGAY LẬP TỨC - FIX 501
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type","text/plain")
        self.end_headers()
        self.wfile.write(f"Wick Sniper Live {datetime.now()}".encode())
    def log_message(self,*a): return

def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"WEB OPEN port {port}")
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# Sau đó mới import nặng
import time, requests
import pandas as pd

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALS = ["15m", "1h"]
sent_cache = {}
top_symbols = []

def send_tele(msg, cid=None):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": cid or CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass
    print(msg)

def get_top_symbols(limit=100):
    hard_100 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","PEPEUSDT","WIFUSDT","AVAXUSDT","SHIBUSDT","ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","ENAUSDT","TAOUSDT","RENDERSUSDT","FETUSDT","ARUSDT","SUIUSDT","SEIUSDT","TIAUSDT","WLDUSDT","STXUSDT","INJUSDT","FILUSDT","ETCUSDT","ATOMUSDT","IMXUSDT","AAVEUSDT","RUNEUSDT","GRTUSDT","LDOUSDT","MKRUSDT","ORDIUSDT","JUPUSDT","PYTHUSDT","BONKUSDT","FLOKIUSDT","1000SATSUSDT","1000PEPEUSDT","STRKUSDT","MANTAUSDT","ALTUSDT","JTOUSDT","ONDOUSDT","WUSDT","ZKUSDT","ZROUSDT","IOUSDT","NOTUSDT","TONUSDT","PENDLEUSDT","CFXUSDT","CHZUSDT","FLOWUSDT","KASUSDT","KAVAUSDT","THETAUSDT","AXSUSDT","SANDUSDT","MANAUSDT","EOSUSDT","KLAYUSDT","EGLDUSDT","XTZUSDT","NEOUSDT","IOTAUSDT","XLMUSDT","HBARUSDT","VETUSDT","ALGOUSDT","QNTUSDT","AGIXUSDT","OCEANUSDT","BLURUSDT","DYDXUSDT","GMXUSDT","1INCHUSDT","COMPUSDT","SNXUSDT","CRVUSDT","LRCUSDT","ENJUSDT","GALAUSDT","YGGUSDT","MAGICUSDT","BEAMXUSDT","RONINUSDT","PIXELUSDT"]
    return hard_100[:limit]

def get_klines(sym, interval):
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/klines", params={"symbol": sym, "interval": interval, "limit": 50}, timeout=10).json()
        df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
        df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
        return df
    except Exception as e:
        raise e

def scan(interval, symbols):
    print(f"Quet {interval} {len(symbols)} coin")
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
            if wr>=0.60 and br<=0.35 and last['v']>=avg_vol*1.4:
                key = f"{sym}_{interval}"
                if key in sent_cache and time.time()-sent_cache[key]<1800: continue
                sent_cache[key]=time.time()
                side = "🟢 QUÉT ĐÁY" if lower>upper else "🔴 QUÉT ĐỈNH"
                send_tele(f"{side} | {sym} {interval}\nRâu {wr*100:.0f}% | Vol x{last['v']/avg_vol:.1f}\nGiá ${last['c']}")
            time.sleep(0.15)
        except: time.sleep(0.3)

if __name__ == "__main__":
    top_symbols = get_top_symbols(100)
    send_tele(f"✅ WICK SNIPER đã bật\nQuét {len(top_symbols)} coin - {' + '.join(INTERVALS)}")
    while True:
        for itv in INTERVALS:
            scan(itv, top_symbols)
        time.sleep(120)
