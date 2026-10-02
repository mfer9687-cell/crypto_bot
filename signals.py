import os
import pandas as pd
import requests

# جفت‌ارزها (فرمت OKX). برای تغییر لیست، همین‌جا ویرایش کن.
SYMBOLS = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT", "XRP-USDT",
    "DOGE-USDT", "TON-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT",
]
RR = 2
BAR = "15m"


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
    df = df[df["confirm"] == "1"].copy()  # فقط کندل‌های بسته‌شده
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)
