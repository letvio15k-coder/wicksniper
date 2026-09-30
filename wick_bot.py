import os, time, requests
import pandas as pd

# ========= CẤU HÌNH =========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") # điền token vào Render
CHAT_ID = os.getenv("CHAT_ID")
INTERVAL = "1h"  # bắt đỉnh đáy thì để 1h, muốn bắt nhanh như 2 vòng nhỏ bên phải ảnh thì đổi thành 15m
WICK_MIN = 0.60  # râu phải >60% cây nến mới tính là quét
BODY_MAX = 0.35  # thân phải nhỏ <35%
VOL_X = 1.4      # volume phải to hơn trung bình 1.4 lần

BINANCE_API = "https://api.binance.com"

def send_tele(msg):
    if not TELEGRAM_TOKEN: 
        print(msg)
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(e)

def get_all_usdt_symbols():
    # Lấy hết coin USDT trên Binance, tự động
    r = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=10).json()
    symbols = [s['symbol'] for s in r['symbols'] if s['quoteAsset']=='USDT' and s['status']=='TRADING' and 'UP' not in s['symbol'] and 'DOWN' not in s['symbol']]
    # Lọc top 150 coin cho đỡ nặng
    return symbols[:150]

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

    # ĐIỀU KIỆN BẮT NHƯ ẢNH BẠN KHOANH
    if wick_ratio >= WICK_MIN and body_ratio <= BODY_MAX and v >= avg_vol * VOL_X:
        if lower > upper:
            # Quét đáy - như 3 vòng dưới trong ảnh của bạn
            return f"🟢 QUÉT ĐÁY {wick_ratio*100:.0f}%", f"Râu dưới dài {lower/(total)*100:.0f}%, thân chỉ {body_ratio*100:.0f}%"
        else:
            # Quét đỉnh - như 3 vòng trên trong ảnh
            return f"🔴 QUÉT ĐỈNH {wick_ratio*100:.0f}%", f"Râu trên dài {upper/(total)*100:.0f}%, thân chỉ {body_ratio*100:.0f}%"
    return None

def scan():
    symbols = get_all_usdt_symbols()
    print(f"Đang quét {len(symbols)} coin Binance khung {INTERVAL}...")
    for sym in symbols:
        try:
            df = get_klines(sym, INTERVAL)
            if len(df) < 25: continue
            avg_vol = df['v'].rolling(20).mean().iloc[-2] # volume trung bình, bỏ cây hiện tại
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # Check 2 nến gần nhất cho đỡ miss
            for candle in [prev, last]:
                res = is_wick_rejection(candle, avg_vol)
                if res:
                    title, detail = res
                    price = candle['c']
                    msg = f"""💎 {title} | {sym} {INTERVAL}
{detail}
Giá ${price} - Vol x{candle['v']/avg_vol:.1f}
Khả năng đảo chiều cao"""
                    send_tele(msg)
                    print(msg)
                    break # báo 1 lần thôi
            time.sleep(0.2) # tránh bị Binance ban
        except Exception as e:
            print(f"Lỗi {sym}: {e}")
            time.sleep(1)

if __name__ == "__main__":
    send_tele(f"✅ Wick Sniper Bot đã bật - Khung {INTERVAL} - Bắt râu như ảnh bạn khoanh")
    while True:
        scan()
        print("Nghỉ 3 phút...")
        time.sleep(180)
