import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings
import os

# --- KONFIGURASI ---
warnings.simplefilter(action='ignore', category=FutureWarning)
st.set_page_config(page_title="Scanner Saham Momentum", layout="wide")

def round_bei(price, direction="up"):
    """Fungsi pembulatan sesuai fraksi harga BEI terbaru."""
    if price <= 0: return 0
    if price < 200: f = 1
    elif price < 500: f = 2
    elif price < 2000: f = 5
    elif price < 5000: f = 10
    else: f = 25
    
    if direction == "up":
        return int(math.ceil(price / f) * f)
    else:
        return int(math.floor(price / f) * f)

def get_tick_down(price, ticks=4):
    """Menghitung harga N tick di bawah harga acuan dengan validasi fraksi."""
    for _ in range(ticks):
        if price <= 200: f = 1
        elif price <= 500: f = 2
        elif price <= 2000: f = 5
        elif price <= 5000: f = 10
        else: f = 25
        price -= f
    return int(price)

def load_tickers(file_path="tickers.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

def jalankan_scanner_final(tickers, tgl_acuan, tgl_target, jam):
    results = []
    tgl_start = tgl_acuan.strftime("%Y-%m-%d")
    # Buffer tgl_end untuk memastikan data hari terakhir tertangkap
    tgl_end_query = (tgl_target + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Konversi WIB ke UTC (-7)
    try:
        hour_wib = int(jam.split(':')[0])
        minute_wib = jam.split(':')[1]
        jam_utc = f"{hour_wib - 7:02d}:{minute_wib}"
    except:
        jam_utc = "08:20" # Default fallback
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            status_text.text(f"Scanning {i+1}/{len(tickers)}: {ticker}")
            
            # Download data intraday untuk cari LOW pada jam tertentu
            df_5m = yf.download(symbol, start=tgl_start, end=(tgl_acuan + timedelta(days=2)).strftime("%Y-%m-%d"), interval="5m", progress=False)
            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(start=tgl_start, end=tgl_end_query)
            
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            if not df_5m.empty and not df_day.empty:
                # Cari harga LOW pada jam acuan
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                if match.empty: 
                    # Jika jam tepat tidak ada, ambil data pertama di hari tersebut
                    match = df_5m.head(1)
                
                lo = float(match['Low'].iloc[0])
                target_val = lo * 1.24 
                
                max_high_val = float(df_day['High'].max())
                gain_h_pct = ((max_high_val - lo) / lo) * 100
                
                # Cek kapan target 24% tercapai
                df_target_hit = df_day[df_day['High'] >= target_val]
                tgl_target_hit = df_target_hit.index[0].strftime("%d-%m-%Y") if not df_target_hit.empty else "-"

                last_c = float(df_day['Close'].iloc[-1])
                gain_c_pct = ((last_c - lo) / lo) * 100

                # FILTER: Hanya saham dengan kenaikan signifikan (>23.5%)
                if gain_h_pct > 23.5:
                    range_fibo = target_val - lo

                    # Perhitungan Level Fibonacci
                    s1 = round_bei(lo + (range_fibo * 0.886))
                    s2 = round_bei(lo + (range_fibo * 0.618)) # S2 di Golden Ratio
                    s3 = round_bei(lo + (range_fibo * 0.382)) # S3 di Support Kuat
                    sl = get_tick_down(s3, ticks=4) # SL dari S3
                    
                    tp1 = round_bei(lo + (range_fibo * 1.128))
                    tp2 = round_bei(lo + (range_fibo * 1.272))
                    tp3 = round_bei(lo + (range_fibo * 1.414))

                    # Jika harga sekarang sudah di bawah SL, abaikan
                    if last_c < s3:
                        continue

                    # Tentukan label posisi harga saat ini
                    if last_c > s1: pos = "> S1 (Strong)"
                    elif last_c > s2: pos = "> S2"
                    elif last_c > s3: pos = "> S3"
                    else: pos = "Near SL"

                    results.append({
                        "Ticker": ticker,
                        "Base Low": int(lo),
                        "Max Gain %": f"{gain_h_pct:.2f}%",
                        "Close %": f"{gain_c_pct:.2f}%",
                        "Close": last_c,
                        "Position": pos,
                        "S1": s1, "S2": s2, "S3": s3, "SL": sl,
                        "TP1": tp1, "TP2": tp2, "TP3": tp3,
                        "Tgl Hit 24%": tgl_target_hit,
                        "Sort_Val": gain_c_pct
                    })
                    
        except Exception as e:
            continue
        finally:
            progress_bar.progress((i + 1) / len(tickers))
        
    status_text.empty()
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by="Sort_Val", ascending=False).drop(columns=["Sort_Val"])
        df.index = range(1, len(df) + 1)
    return df

# --- UI LOGIC ---
st.title("Scanner Saham Momentum 🚀")
st.markdown("""
*   **Strategi:** Mencari saham dengan kenaikan signifikan dan memetakan retracement Fibonacci-nya.
*   **Indeks:** JII70, KOMPAS100, IDX-MES-BUMN, IDX-SHA-GROW (Syariah).
*   **Setup:** Entry bertahap pada Support (S1, S2, dan S3).
""")

# Setup Tanggal Otomatis
today = datetime.now()
if today.day >= 15:
    default_acuan = datetime(today.year, today.month, 15)
else:
    default_acuan = (today.replace(day=1) - timedelta(days=1)).replace(day=15)

with st.sidebar:
    st.header("⚙️ Pengaturan")
    tgl_acuan = st.date_input("Tanggal Low Acuan", default_acuan)
    tgl_target = st.date_input("Tanggal Data Terakhir", today)
    jam_input = "15:20"
    btn_scan = st.button("Jalankan Scanner", use_container_width=True)

tickers = load_tickers()

if btn_scan:
    if not tickers:
        st.error("File 'tickers.txt' tidak ditemukan atau kosong!")
    else:
        df_hasil = jalankan_scanner_final(tickers, tgl_acuan, tgl_target, jam_input)
        
        if not df_hasil.empty:
            st.success(f"Ditemukan {len(df_hasil)} saham potensial!")
            st.dataframe(df_hasil, use_container_width=True)

            st.divider()
            st.subheader("📝 Trading Plan")
            
            # Tampilan Grid untuk Trading Plan
            cols = st.columns(2)
            for idx, row in enumerate(df_hasil.to_dict(orient='records')):
                with cols[idx % 2]:
                    with st.container(border=True):
                        # Hitung Avg Price 20-35-45
                        avg_p = (row['S1']*0.2) + (row['S2']*0.35) + (row['S3']*0.45)
                        risk_pct = ((row['SL'] - avg_p) / avg_p) * 100
                        tp1_pct = ((row['TP1'] - row['S1']) / row['S1']) * 100
                        tp2_pct = ((row['TP2'] - row['S1']) / row['S1']) * 100
                        
                        st.subheader(f"📈 {row['Ticker']}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success(f"**Buy:**")
                            st.write(f"- S1: **{row['S1']}**")
                            st.write(f"- S2: **{row['S2']}**")
                            st.write(f"- S3: **{row['S3']}**")
                        with c2:
                            st.error(f"**Exit:**")
                            st.write(f"- TP1: **{row['TP1']}**")
                            st.write(f"- TP2: **{row['TP2']}**")
                            st.write(f"- SL: **{row['SL']}**")
                        st.write(f"Risk dari harga rata-rata (**{int(avg_p)}**) ke Stop Loss (SL): **{risk_pct:.2f}%**.")
                        st.write(f"Reward dari S1 ke TP1: **{tp1_pct:.2f}%** dan TP2: **{tp2_pct:.2f}%**.")
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria kenaikan >23.5% pada periode ini.")
