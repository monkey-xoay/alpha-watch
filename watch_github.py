import os, sys, time, datetime, requests

API    = "https://alpha6666.com/api/stability"
TOKEN  = os.environ["TG_TOKEN"]
CHAT   = os.environ["TG_CHAT"]
PROXY_URL = os.environ.get("PROXY_URL", "")
SYMBOL = "pPOLY"
LIMIT  = 1.31
HOLD   = 300
EVERY  = 2
START_H = int(os.environ.get("START_H") or 8)
END_H   = int(os.environ.get("END_H") or 21)

# --- ngưỡng thứ hai: báo nổi bật khi xuống dưới 1.0 ---
LIMIT_LOW = 1.0      # dưới mức này thì báo thêm 1 lần
HOLD_LOW  = 0        # giây phải dưới LIMIT_LOW mới báo (0 = báo ngay)
RESET_LOW = 1.03     # phải lên trên mức này thì lần sau mới báo lại (tránh báo lặp khi giá dao động quanh 1.0)

VN = datetime.timezone(datetime.timedelta(hours=7))
PROXY = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
HEADERS = {"User-Agent": "Mozilla/5.0"}

low_since = None
notified_low = False
low1_since = None
notified_low1 = False
fail = 0


def now_vn():
    return datetime.datetime.now(VN)


def send(text, html=False):
    params = {"chat_id": CHAT, "text": text}
    if html:
        params["parse_mode"] = "HTML"
    for _ in range(3):
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                params=params, timeout=(5, 10))
            if r.ok:
                return
        except Exception as e:
            print("Telegram lỗi:", type(e).__name__, flush=True)
            time.sleep(1)


def get_value():
    params = {
        "target_points": 65536,
        "current_points": 0,
        "round_usdt": 1000,
        "since": int(time.time() * 1000) - 5000,
    }
    try:
        r = requests.get(API, params=params, headers=HEADERS,
                         timeout=8, proxies=PROXY)
    except requests.RequestException as e:
        if not PROXY:
            raise
        print("Proxy lỗi, thử mạng thường:", type(e).__name__, flush=True)
        r = requests.get(API, params=params, headers=HEADERS, timeout=8)
    r.raise_for_status()
    for row in r.json()["rows"]:
        if row["symbol"] == SYMBOL:
            return row.get("quoted_target_total_loss_mean")
    return None


print(f"[GitHub] Theo dõi {SYMBOL}, ngưỡng {LIMIT}, ổn định {HOLD}s, "
      f"báo nổi bật khi dưới {LIMIT_LOW}, "
      f"khung {START_H}h-{END_H}h, proxy: {'BẬT' if PROXY else 'tắt'}",
      flush=True)

while True:
    h = now_vn().hour
    if h >= END_H:
        print("Hết giờ theo dõi, kết thúc.", flush=True)
        sys.exit(0)
    if h < START_H:
        time.sleep(30)
        continue
    try:
        v = get_value()
        fail = 0
        if v is not None:
            t = time.time()
            held = int(t - low_since) if low_since else 0
            print(now_vn().strftime("%H:%M:%S"), round(v, 4),
                  f"(dưới ngưỡng {held}s)" if low_since else "", flush=True)

            # ----- báo như cũ: dưới 1.31 ổn định đủ HOLD giây -----
            if v <= LIMIT:
                if low_since is None:
                    low_since = t
                if not notified_low and t - low_since >= HOLD:
                    send(f"🟢 {SYMBOL}: ổn định ≤ {LIMIT} trong {HOLD}s, "
                         f"hiện tại {v:.3f} U. Có thể chạy. [GitHub]")
                    notified_low = True
            else:
                low_since = None
                if notified_low:
                    send(f"🔴 {SYMBOL}: vượt {LIMIT}, hiện tại {v:.3f} U. NGƯNG! [GitHub]")
                    notified_low = False

            # ----- báo thêm, nổi bật: xuống dưới 1.0 -----
            if v < LIMIT_LOW:
                if low1_since is None:
                    low1_since = t
                if not notified_low1 and t - low1_since >= HOLD_LOW:
                    send(
                        "🚨🚨🚨🚨🚨🚨🚨🚨\n"
                        f"<b>🔥 {SYMBOL} DƯỚI {LIMIT_LOW} 🔥</b>\n"
                        f"<b>💰 Tổng chi phí: {v:.3f} U</b>\n"
                        "🚨🚨🚨🚨🚨🚨🚨🚨\n"
                        "[GitHub]",
                        html=True)
                    notified_low1 = True
            else:
                low1_since = None
                if v > RESET_LOW:
                    notified_low1 = False
    except Exception as e:
        fail += 1
        print("Lỗi:", type(e).__name__, flush=True)
        if fail == 12:
            send("⚠️ [GitHub] Không lấy được dữ liệu API")
    time.sleep(EVERY)
