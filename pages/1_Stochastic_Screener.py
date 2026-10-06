import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import os

# --- KONFIGURASI ---
warnings.simplefilter(action='ignore', category=FutureWarning)
st.set_page_config(page_title="Screener Stochastic Golden Cross", layout="wide")

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
                      max_k, min_price, min_value):
    period = "1y" if interval == "1d" else "5y"
    min_bars = k_period + k_smooth + d_period + 1
    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start + BATCH_SIZE]
        status_text.text(f"Download data {start + 1}-{start + len(batch)} dari {len(tickers)} ticker...")
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

        progress_bar.progress(min((start + BATCH_SIZE) / len(tickers), 1.0))

    status_text.empty()
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by="%K saat Cross").reset_index(drop=True)
        df.index = range(1, len(df) + 1)
    return df

# --- UI LOGIC ---
st.title("Screener Stochastic Golden Cross 📈")
st.markdown("""
* **Indikator:** Slow Stochastic (default 14, 5, 5).
* **Sinyal:** Golden cross = garis %K memotong ke atas garis %D.
* **Tips:** Golden cross di area oversold (%K < 20) biasanya sinyal yang lebih kuat.
""")

with st.sidebar:
    st.header("⚙️ Pengaturan Stochastic")
    c1, c2, c3 = st.columns(3)
    k_period = c1.number_input("%K", min_value=1, value=14)
    k_smooth = c2.number_input("Slow", min_value=1, value=5)
    d_period = c3.number_input("%D", min_value=1, value=5)
    tf = st.selectbox("Timeframe", ["Harian", "Mingguan"])
    lookback = st.number_input("Cross dalam N candle terakhir", min_value=1, max_value=10, value=1,
                               help="1 = cross terjadi di candle terakhir saja")

    st.header("🔎 Filter")
    max_k = st.slider("Maks. %K saat cross", 0, 100, 100,
                      help="Isi 20 untuk hanya mencari cross di area oversold")
    min_price = st.number_input("Harga minimum", min_value=0, value=50)
    min_value_m = st.number_input("Nilai transaksi minimum (Miliar Rp)", min_value=0.0, value=0.0, step=0.5)
    btn_scan = st.button("Jalankan Screener", use_container_width=True)

tickers = load_tickers()

if btn_scan:
    if not tickers:
        st.error("File 'tickers.txt' tidak ditemukan!")
    else:
        interval = "1d" if tf == "Harian" else "1wk"
        df_hasil = jalankan_screener(tickers, interval, int(k_period), int(k_smooth), int(d_period),
                                     int(lookback), max_k, min_price, min_value_m * 1e9)
        if not df_hasil.empty:
            st.success(f"Ditemukan {len(df_hasil)} saham dengan golden cross Stochastic "
                       f"({k_period},{k_smooth},{d_period})!")
            st.dataframe(df_hasil, use_container_width=True)
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
