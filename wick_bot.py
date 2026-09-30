import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type","text/plain")
        self.end_headers()
        self.wfile.write(f"Wick V2 Live {datetime.now()}".encode())
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
    def log_message(self,*a): return

def run_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()

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
                      json={"chat_id": cid or CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=12)
    except: pass
    print(msg)

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_top_symbols(limit=100):
    hard_100 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","PEPEUSDT","WIFUSDT","AVAXUSDT","SHIBUSDT","ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","ENAUSDT","TAOUSDT","RENDERSUSDT","FETUSDT","ARUSDT","SUIUSDT","SEIUSDT","TIAUSDT","WLDUSDT","STXUSDT","INJUSDT","FILUSDT","ETCUSDT","ATOMUSDT","IMXUSDT","AAVEUSDT","RUNEUSDT","GRTUSDT","LDOUSDT","MKRUSDT","ORDIUSDT","JUPUSDT","PYTHUSDT","BONKUSDT","FLOKIUSDT","1000SATSUSDT","1000PEPEUSDT","STRKUSDT","MANTAUSDT","ALTUSDT","JTOUSDT","ONDOUSDT","WUSDT","ZKUSDT","ZROUSDT","IOUSDT","NOTUSDT","TONUSDT","PENDLEUSDT","CFXUSDT","CHZUSDT","FLOWUSDT","KASUSDT","KAVAUSDT","THETAUSDT","AXSUSDT","SANDUSDT","MANAUSDT","EOSUSDT","KLAYUSDT","EGLDUSDT","XTZUSDT","NEOUSDT","IOTAUSDT","XLMUSDT","HBARUSDT","VETUSDT","ALGOUSDT","QNTUSDT","AGIXUSDT","OCEANUSDT","BLURUSDT","DYDXUSDT","GMXUSDT","1INCHUSDT","COMPUSDT","SNXUSDT","CRVUSDT","LRCUSDT","ENJUSDT","GALAUSDT","YGGUSDT","MAGICUSDT","BEAMXUSDT","RONINUSDT","PIXELUSDT"]
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=10).json()
        usdt = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol']]
        usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
        live = [x['symbol'] for x in usdt[:limit]]
        if len(live)>=80: return live
    except: pass
    return hard_100[:limit]

def get_klines(sym, interval):
    r = requests.get("https://data-api.binance.vision/api/v3/klines", params={"symbol": sym, "interval": interval, "limit": 100}, timeout=10).json()
    df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    df['ma20'] = df['c'].rolling(20).mean()
    df['rsi'] = rsi(df['c'], 14)
    df['high20'] = df['h'].rolling(20).max()
    df['low20'] = df['l'].rolling(20).min()
    return df

def scan_v2(interval, symbols):
    for sym in symbols:
        try:
            df = get_klines(sym, interval)
            if len(df)<30: continue
            last = df.iloc[-1]
            prev = df.iloc[-2]
            avg_vol = df['v'].rolling(20).mean().iloc[-2]

            total = last['h']-last['l']
            if total==0: continue
            body = abs(last['c']-last['o'])
            upper = last['h']-max(last['o'],last['c'])
            lower = min(last['o'],last['c'])-last['l']
            wr = max(upper,lower)/total
            br = body/total
            vol_x = last['v']/avg_vol if avg_vol>0 else 0

            # --- BỘ LỌC V2 ---
            if wr < 0.60 or br > 0.35 or vol_x < 1.4:
                continue

            is_bottom = lower > upper
            side = "🟢 QUÉT ĐÁY" if is_bottom else "🔴 QUÉT ĐỈNH"

            # LỌC 1: RSI
            if is_bottom and last['rsi'] > 45: continue
            if not is_bottom and last['rsi'] < 55: continue

            # LỌC 2: CẤU TRÚC - phải quét qua MA20 hoặc đỉnh/đáy 20 nến
            is_structure_break = False
            if is_bottom and last['l'] < prev['low20']: is_structure_break = True
            if not is_bottom and last['h'] > prev['high20']: is_structure_break = True
            if abs(last['c'] - last['ma20'])/last['ma20'] < 0.03: is_structure_break = True # gần MA20

            if not is_structure_break: continue

            # --- CHẤM ĐIỂM ---
            score = 6
            if wr >= 0.75: score += 1
            if wr >= 0.85: score += 1
            if vol_x >= 2.5: score += 1
            if vol_x >= 3.5: score += 1
            if (is_bottom and last['rsi'] < 30) or (not is_bottom and last['rsi'] > 70): score += 1

            if score < 8: continue # CHỈ BẮN HÀNG ĐẸP

            key = f"{sym}_{interval}_{side}"
            if key in sent_cache and time.time()-sent_cache[key]<3600: continue
            sent_cache[key]=time.time()

            tag = "⚡ SCALP 15m" if interval=="15m" else "💎 TREND 1h"
            stars = "⭐" * (score-5)
            send_tele(f"{side} {stars} {score}/10\n{sym} {interval} | {tag}\nRâu {wr*100:.0f}% | Thân {br*100:.0f}% | Vol x{vol_x:.1f}\nRSI {last['rsi']:.0f} | MA20 {last['ma20']:.2f}\nGiá ${last['c']}")

            time.sleep(0.2)
        except Exception as e:
            # print(e)
            time.sleep(0.2)

if __name__ == "__main__":
    top_symbols = get_top_symbols(100)
    send_tele(f"✅ WICK SNIPER V2 MẠNH ĐÃ BẬT\nQuét {len(top_symbols)} coin | Lọc RSI+MA20\nChỉ bắn >=8/10 điểm\nFix 501 HEAD - UptimeRobot sẽ Up")
    while True:
        for itv in INTERVALS:
            scan_v2(itv, top_symbols)
        time.sleep(90)
