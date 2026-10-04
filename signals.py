import os
import pandas as pd
import requests

SYMBOLS = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT", "XRP-USDT",
    "DOGE-USDT", "TON-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT",
]
RR = 2
BAR = "5m"


def fetch(inst):
    r = requests.get(
        "https://www.okx.com/api/v5/market/candles",
        params={"instId": inst, "bar": BAR, "limit": 150},
        timeout=20,
    )
    rows = r.json()["data"]
    df = pd.DataFrame(
        rows,
        columns=["ts", "Open", "High", "Low", "Close", "v", "vc", "vq", "confirm"],
    )
    df = df[df["confirm"] == "1"].copy()
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)
    df.index = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    return df.sort_index()


def add_ichimoku(df):
    h, l = df["High"], df["Low"]
    df["tenkan"] = (h.rolling(9).max() + l.rolling(9).min()) / 2
    df["kijun"] = (h.rolling(26).max() + l.rolling(26).min()) / 2
    span_a = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    span_b = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    both = pd.concat([span_a, span_b], axis=1)
    df["cloud_bot"] = both.min(axis=1, skipna=False)
    df["cloud_top"] = both.max(axis=1, skipna=False)
    return df


def check(df):
    if len(df) < 80:
        return []
    df = add_ichimoku(df)
    c, p = df.iloc[-1], df.iloc[-2]
    if pd.isna(c["cloud_bot"]) or pd.isna(p["tenkan"]) or pd.isna(p["kijun"]):
        return []

    out = []
    t = df.index[-1]

    # خرید
    cross_up = p["tenkan"] <= p["kijun"] and c["tenkan"] > c["kijun"]
    under_cloud = max(c["tenkan"], c["kijun"]) < c["cloud_bot"]
    green = c["Close"] > c["Open"]
    above_tenkan = c["Close"] > c["tenkan"]
    risk_buy = c["Close"] - c["Low"]
    if cross_up and under_cloud and green and above_tenkan and risk_buy > 0:
        entry = float(c["Close"])
        out.append(("buy", entry, float(c["Low"]), entry + RR * risk_buy, t))

    # فروش
    cross_down = p["tenkan"] >= p["kijun"] and c["tenkan"] < c["kijun"]
    over_cloud = min(c["tenkan"], c["kijun"]) > c["cloud_top"]
    red = c["Close"] < c["Open"]
    below_tenkan = c["Close"] < c["tenkan"]
    risk_sell = c["High"] - c["Close"]
    if cross_down and over_cloud and red and below_tenkan and risk_sell > 0:
        entry = float(c["Close"])
        out.append(("sell", entry, float(c["High"]), entry - RR * risk_sell, t))

    return out


def send(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20,
    )


def main():
    for inst in SYMBOLS:
        try:
            signals = check(fetch(inst))
        except Exception as e:
            print(inst, "error:", e)
            continue
        if not signals:
            print(inst, "no signal")
            continue
        for side, entry, sl, tp, t in signals:
            if side == "buy":
                title = "🟢 سیگنال خرید (کریپتو)"
            else:
                title = "🔴 سیگنال فروش (کریپتو)"
            send(
                f"{title}\n"
                f"{inst}\n"
                f"تایم‌فریم: {BAR}\n"
                f"ورود: {entry:.6g}\n"
                f"حد ضرر: {sl:.6g}\n"
                f"حد سود: {tp:.6g}\n"
                f"ریسک به ریوارد: 1:{RR}\n"
                f"کندل: {t:%Y-%m-%d %H:%M} UTC"
            )
            print(inst, side.upper(), "SIGNAL")


if __name__ == "__main__":
    main()
