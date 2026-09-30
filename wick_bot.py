import os, time, requests
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALS = ["15m", "1h"]
WICK_MIN = 0.60
BODY_MAX = 0.35
VOL_X = 1.4
BINANCE_API = "https://api.binance.com"
sent_cache = {}

def send_tele(msg):
    if not TELEGRAM_TOKEN:
        print(msg); return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def get_top_symbols(limit=100):
    # FIX LỖI TRONG ẢNH: dùng ticker thay vì exchangeInfo, không bị chặn
    try:
        r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=10).json()
        if isinstance(r, dict) and 'code' in r: # bị chặn thì dùng list cứng
            raise Exception("Binance blocked")
        usdt = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol'] and 'DOWN' not in x['symbol'] and 'BULL' not in x['symbol'] and 'BEAR' not in x['symbol']]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
        return [x['symbol'] for x in usdt_sorted[:limit]]
    except Exception as e:
        print(f"Binance API lỗi, dùng list cứng: {e}")
        # List cứng top coin để không bao giờ crash như trong ảnh
        return ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","POLUSDT","ARBUSDT","OPUSDT","AVAXUSDT","DOGEUSDT","XRPUSDT","ADAUSDT","DOTUSDT","LINKUSDT","MATICUSDT","LTCUSDT","TRXUSDT","SHIBUSDT","UNIUSDT"]

def get_klines(symbol, interval, limit=50):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(f"{BINANCE_API}/api/v3/klines", params=params, timeout=10).json()
    df = pd.DataFrame(r, columns=["t","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    return df

def is_wick_rejection(candle, avg_vol):
    o,h,l,c,v = candle['o'], candle['h'], candle['l'], candle['c'], candle['v']
    total = h - l
    if total == 0: return None
    body = abs(c - o)
    upper = h - max(o,c)
    lower = min(o,c) - l
    wick_ratio = max(upper, lower) / total
    body_ratio = body / total
    if wick_ratio >= WICK_MIN and body_ratio <= BODY_MAX and v >= avg_vol * VOL_X:
        return ("🟢 QUÉT ĐÁY" if lower > upper else "🔴 QUÉT ĐỈNH"), wick_ratio, body_ratio
    return None

def scan_interval(interval, symbols):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quét {interval}...")
    for sym in symbols:
        try:
            df = get_klines(sym, interval, 50)
            if len(df) < 25: continue
            avg_vol = df['v'].rolling(20).mean().iloc[-2]
            last = df.iloc[-1]
            res = is_wick_rejection(last, avg_vol)
            if res:
                signal, wick_ratio, body_ratio = res
                cache_key = f"{sym}_{interval}_{signal}"
                if cache_key in sent_cache and time.time() - sent_cache[cache_key] < 1800:
                    continue
                sent_cache[cache_key] = time.time()
                vol_x = last['v']/avg_vol if avg_vol>0 else 1
                tag = "⚡ SCALP 15m" if interval=="15m" else "💎 TREND 1h"
                msg = f"""{signal} | {sym} {interval}
{tag}
Râu {wick_ratio*100:.0f}% | Thân {body_ratio*100:.0f}% | Vol x{vol_x:.1f}
Giá ${last['c']}"""
                send_tele(msg)
                print(msg)
            time.sleep(0.2)
        except Exception as e:
            print(f"Lỗi {sym}: {e}"); time.sleep(0.5)

if __name__ == "__main__":
    top_symbols = get_top_symbols(100)
    send_tele(f"✅ Wick Sniper đã bật - {len(top_symbols)} coin - Khung {' + '.join(INTERVALS)}")
    while True:
        for interval in INTERVALS:
            scan_interval(interval, top_symbols)
        print("--- Nghỉ 2 phút ---")
        time.sleep(120)
