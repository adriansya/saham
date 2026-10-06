"""Logika screener Stochastic golden cross, dipakai oleh versi Streamlit dan Gradio."""
import yfinance as yf
import pandas as pd
import warnings
import os

warnings.simplefilter(action='ignore', category=FutureWarning)

BATCH_SIZE = 50

def load_tickers(file_path="tickers.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

def hitung_stochastic(df, k_period=14, k_smooth=5, d_period=5):
    """Slow Stochastic: %K = SMA(fast %K, k_smooth), %D = SMA(%K, d_period)."""
    low_min = df['Low'].rolling(k_period).min()
    high_max = df['High'].rolling(k_period).max()
    rentang = (high_max - low_min).replace(0, float('nan'))
    fast_k = 100 * (df['Close'] - low_min) / rentang
    k = fast_k.rolling(k_smooth).mean()
    d = k.rolling(d_period).mean()
    return k, d

def cari_golden_cross(k, d, lookback=1):
    """Return posisi (index) golden cross terakhir dalam `lookback` candle terakhir, atau None."""
    cross = (k > d) & (k.shift(1) <= d.shift(1))
    cross_terakhir = cross.iloc[-lookback:]
    if not cross_terakhir.any():
        return None
    return cross_terakhir[cross_terakhir].index[-1]

def download_batch(tickers, period, interval):
    symbols = [t + ".JK" for t in tickers]
    data = yf.download(symbols, period=period, interval=interval, group_by='ticker',
                       auto_adjust=False, progress=False, threads=True)
    hasil = {}
    for t, s in zip(tickers, symbols):
        try:
            df = data[s] if isinstance(data.columns, pd.MultiIndex) else data
            df = df.dropna(subset=['High', 'Low', 'Close'])
            if not df.empty:
                hasil[t] = df
        except KeyError:
            continue
    return hasil

def jalankan_screener(tickers, interval, k_period, k_smooth, d_period, lookback,
                      max_k, min_price, min_value, on_progress=None):
    """`on_progress(fraksi, pesan)` dipanggil tiap batch selesai (opsional)."""
    period = "1y" if interval == "1d" else "5y"
    min_bars = k_period + k_smooth + d_period + 1
    results = []

    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start + BATCH_SIZE]
        if on_progress:
            on_progress(start / len(tickers),
                        f"Download data {start + 1}-{start + len(batch)} dari {len(tickers)} ticker...")
        try:
            data = download_batch(batch, period, interval)
        except Exception:
            data = {}

        for ticker, df in data.items():
            try:
                if len(df) < min_bars:
                    continue
                k, d = hitung_stochastic(df, k_period, k_smooth, d_period)
                tgl_cross = cari_golden_cross(k, d, lookback)
                if tgl_cross is None:
                    continue

                k_cross = float(k.loc[tgl_cross])
                if k_cross > max_k:
                    continue

                close = float(df['Close'].iloc[-1])
                volume = float(df['Volume'].iloc[-1])
                value = close * volume
                if close < min_price or value < min_value:
                    continue

                prev_close = float(df['Close'].iloc[-2])
                chg_pct = (close - prev_close) / prev_close * 100 if prev_close else 0

                results.append({
                    "Ticker": ticker,
                    "Tgl Cross": pd.Timestamp(tgl_cross).strftime("%d-%m-%Y"),
                    "%K saat Cross": round(k_cross, 2),
                    "%K": round(float(k.iloc[-1]), 2),
                    "%D": round(float(d.iloc[-1]), 2),
                    "Close": int(close),
                    "Chg %": round(chg_pct, 2),
                    "Volume (lot)": int(volume / 100),
                    "Value (M)": round(value / 1e9, 2),
                })
            except Exception:
                continue

    if on_progress:
        on_progress(1.0, "Selesai")
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by="%K saat Cross").reset_index(drop=True)
        df.index = range(1, len(df) + 1)
    return df
