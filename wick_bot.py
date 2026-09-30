import os, time, requests, threading
import pandas as pd
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. WEB GIẢ ĐỂ CHẠY FREE TRÊN RENDER (FIX No open ports) ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Wick Sniper 100 coin Live")
    def log_message(self, *args): return

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# --- 2. CẤU HÌNH ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALS = ["15m", "1h"]
WICK_MIN, BODY_MAX, VOL_X = 0.60, 0.35, 1.4
BINANCE_API = "https://data-api.binance.vision"
BINANCE_API2 = "https://api.binance.com"
sent_cache = {}
last_update_id = 0
top_symbols = []

def send_tele(msg, chat_id=None):
    cid = chat_id or CHAT_ID
    if not TELEGRAM_TOKEN or not cid:
        print(f"[NO TELE] {msg}")
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Tele error: {e}")
    print(msg)

# --- 3. LỆNH /start /status ---
def telegram_poller():
    global last_update_id
    print("Poller started - san sang tra loi /start")
    while True:
        try:
            if not TELEGRAM_TOKEN:
                time.sleep(10); continue
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"
            r = requests.get(url, timeout=35).json()
            if not r.get("ok"):
                time.sleep(5); continue
            for upd in r.get("result", []):
                last_update_id = upd["update_id"]
                msg = upd.get("message", {})
                text = (msg.get("text") or "").lower()
                cid = msg.get("chat", {}).get("id")
                if not text or not cid: continue
                if "/start" in text:
                    send_tele(f"""✅ WICK SNIPER đã bật

Đang quét {len(top_symbols)} coin Binance
Khung: {', '.join(INTERVALS)}
Logic: Râu >60% + Thân <35% + Vol x1.4

Bot sẽ tự bắn khi có QUÉT ĐỈNH / QUÉT ĐÁY như ảnh bạn khoanh.
Gõ /status để xem trạng thái.""", chat_id=cid)
                elif "/status" in text:
                    send_tele(f"🟢 Đang chạy\n- Quét: {len(top_symbols)} coin\n- Đã lọc trùng: {len(sent_cache)}\n- Khung: {', '.join(INTERVALS)}", chat_id=cid)
        except Exception as e:
            print(f"Poller lỗi: {e}")
            time.sleep(5)

# --- 4. LẤY 100 COIN - FIX LỖI 10 COIN TRONG ẢNH CỦA BẠN ---
def get_top_symbols(limit=100):
    hard_100 = [
    "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","PEPEUSDT","WIFUSDT","AVAXUSDT","SHIBUSDT",
    "ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT","APTUSDT",
    "ARBUSDT","OPUSDT","ENAUSDT","TAOUSDT","RENDERSUSDT","FETUSDT","ARUSDT","SUIUSDT","SEIUSDT","TIAUSDT",
    "WLDUSDT","STXUSDT","INJUSDT","FILUSDT","ETCUSDT","ATOMUSDT","IMXUSDT","AAVEUSDT","RUNEUSDT","GRTUSDT",
    "LDOUSDT","MKRUSDT","ORDIUSDT","JUPUSDT","PYTHUSDT","BONKUSDT","FLOKIUSDT","1000SATSUSDT","1000PEPEUSDT",
    "STRKUSDT","MANTAUSDT","ALTUSDT","JTOUSDT","ONDOUSDT","WUSDT","ZKUSDT","ZROUSDT","IOUSDT","NOTUSDT",
    "TONUSDT","PENDLEUSDT","CFXUSDT","CHZUSDT","FLOWUSDT","KASUSDT","KAVAUSDT","THETAUSDT","AXSUSDT","SANDUSDT",
    "MANAUSDT","EOSUSDT","KLAYUSDT","EGLDUSDT","XTZUSDT","NEOUSDT","IOTAUSDT","XLMUSDT","HBARUSDT","VETUSDT",
    "ALGOUSDT","QNTUSDT","AGIXUSDT","OCEANUSDT","BLURUSDT","DYDXUSDT","GMXUSDT","1INCHUSDT","COMPUSDT","SNXUSDT",
    "CRVUSDT","LRCUSDT","ENJUSDT","GALAUSDT","YGGUSDT","MAGICUSDT","BEAMXUSDT","RONINUSDT","PIXELUSDT","STRKUSDT"
    ]
    # Thử lấy live từ endpoint không bị chặn
    for api in [BINANCE_API, BINANCE_API2]:
        try:
            r = requests.get(f"{api}/api/v3/ticker/24hr", timeout=10).json()
            if isinstance(r, dict): continue
            usdt = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol'] and 'DOWN' not in x['symbol'] and 'BEAR' not in x['symbol'] and 'BULL' not in x['symbol']]
            usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
            live = [x['symbol'] for x in usdt[:limit]]
            if len(live) >= 80:
                print(f"Lay live {len(live)} coin tu {api}")
                return live
        except Exception as e:
            print(f"Fail {api}: {e}")
            continue
    print(f"Dung list cung {limit} coin")
    return hard_100[:limit]

def get_klines(sym, interval):
    for api in [BINANCE_API, BINANCE_API2]:
        try:
            r = requests.get(f"{api}/api/v3/klines", params={"symbol": sym, "interval": interval, "limit": 50}, timeout=10).json()
            df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
            df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
            return df
        except: continue
    raise Exception("klines fail")

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quet {interval} - {len(symbols)} coin")
    for sym in symbols:
        try:
            df = get_klines(sym, interval)
            if len(df)<25: continue
            avg_vol = df['v'].rolling(20).mean().iloc[-2]
            if pd.isna(avg_vol): continue
            last = df.iloc[-1]
            res = is_wick(last, avg_vol)
            if res:
                side, wr, br = res
                key = f"{sym}_{interval}_{side}"
                if key in sent_cache and time.time()-sent_cache[key]<1800: continue
                sent_cache[key]=time.time()
                tag = "⚡ SCALP 15m" if interval=="15m" else "💎 TREND 1h"
                send_tele(f"{side} | {sym} {interval}\n{tag}\nRâu {wr*100:.0f}% | Thân {br*100:.0f}% | Vol x{last['v']/avg_vol:.1f}\nGiá ${last['c']}")
            time.sleep(0.15)
        except Exception as e:
            print(f"Loi {sym}: {e}")

if __name__ == "__main__":
    top_symbols = get_top_symbols(100)
    threading.Thread(target=telegram_poller, daemon=True).start()
    send_tele(f"✅ WICK SNIPER đã bật\nĐang quét {len(top_symbols)} coin Binance\nKhung: {', '.join(INTERVALS)}\nLogic: Râu >60% + Thân <35% + Vol x1.4")
    while True:
        for itv in INTERVALS:
            scan(itv, top_symbols)
        print("--- Nghi 2 phut ---")
        time.sleep(120)
