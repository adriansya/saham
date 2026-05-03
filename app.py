import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings
import os

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Scanner Saham", layout="wide")

def round_bei(price, direction="up"):
    """Fungsi pembulatan sesuai fraksi harga BEI."""
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

def get_tick_down(price, ticks=3):
    """Menghitung harga N tick di bawah harga acuan."""
    for _ in range(ticks):
        if price <= 200: f = 1
        elif price <= 500: f = 2
        elif price <= 2000: f = 5
        elif price <= 5000: f = 10
        else: f = 25
        price -= f
    return int(price)

def load_tickers(file_path="tickers.txt"):
    """Mengambil daftar ticker dari file eksternal."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            lines = f.readlines()
            return [line.strip().upper() for line in lines if line.strip()]
    else:
        st.error(f"File {file_path} tidak ditemukan!")
        return []

def jalankan_scanner_final(tickers, tgl_acuan, tgl_target, jam):
    results = []
    tgl_start = tgl_acuan.strftime("%Y-%m-%d")
    tgl_end = (tgl_target + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Konversi WIB ke UTC (-7)
    jam_utc = f"{int(jam.split(':')[0]) - 7:02d}:{jam.split(':')[1]}"
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            status_text.text(f"Memeriksa {ticker} ...")
            
            df_5m = yf.download(symbol, start=tgl_start, end=(tgl_acuan + timedelta(days=1)).strftime("%Y-%m-%d"), interval="5m", progress=False)
            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(start=tgl_start, end=tgl_end)
            
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            if not df_5m.empty and not df_day.empty:
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                if match.empty: continue

                lo = float(match['Low'].iloc[0])
                target_val = lo * 1.24 
                
                max_high_val = float(df_day['High'].max())
                gain_h_pct = ((max_high_val - lo) / lo) * 100
                
                df_target_hit = df_day[df_day['High'] >= target_val]
                tgl_target_hit = df_target_hit.index[0].strftime("%d-%m-%Y") if not df_target_hit.empty else "-"

                last_c = float(df_day['Close'].iloc[-1])
                gain_c_pct = ((last_c - lo) / lo) * 100

                if gain_h_pct > 23.5:
                    range_fibo = target_val - lo

                    # Perhitungan Level
                    s1 = round_bei(lo + (range_fibo * 0.886))
                    s2 = round_bei(lo + (range_fibo * 0.786))
                    s3 = round_bei(lo + (range_fibo * 0.618))
                    s4 = round_bei(lo + (range_fibo * 0.382))
                    cl = get_tick_down(s4, ticks=3)
                    
                    tp1 = round_bei(lo + (range_fibo * 1.128))
                    tp2 = round_bei(lo + (range_fibo * 1.272))
                    tp3 = round_bei(lo + (range_fibo * 1.414))

                    if last_c <= cl:
                        continue
                    if last_c > s1: pos = "> S1"
                    elif last_c > s2: pos = "> S2"
                    elif last_c > s3: pos = "> S3"
                    elif last_c > s4: pos = "> S4"
                    elif last_c > cl: pos = "> CL"
                    else: pos = "< CL"

                    results.append({
                        "Ticker": ticker,
                        "Low": int(lo),
                        "Max High %": f"{gain_h_pct:.2f}%",
                        "Max High": int(max_high_val),
                        "Close %": f"{gain_c_pct:.2f}%",
                        "Close": int(last_c),
                        "Position": pos,
                        "S1": s1, "S2": s2, "S3": s3, "S4": s4, "CL": cl,
                        "TP1": tp1, "TP2": tp2, "TP3": tp3,
                        "Target 24%": round_bei(target_val),
                        "Tgl Target 24%": tgl_target_hit,
                        "Sort_Val": gain_c_pct
                    })
                    
        except Exception: 
            continue
            
        progress_bar.progress((i + 1) / len(tickers))
        
    status_text.text("Scan selesai!")
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by="Sort_Val", ascending=False).drop(columns=["Sort_Val"])
        df = df.reset_index(drop=True)
        df.index = df.index + 1 
    return df

# --- LOGIKA TANGGAL OTOMATIS ---
today = datetime.now()
if today.day >= 15:
    default_acuan = datetime(today.year, today.month, 15)
else:
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    default_acuan = datetime(last_day_last_month.year, last_day_last_month.month, 15)

# --- ANTARMUKA PENGGUNA (UI) ---
st.title("Scanner Saham Naik 🚀")
st.write("✅ Mencari saham syariah dengan lonjakan harga signifikan diatas 24% kurang dari 1 bulan. Kriteria saham syariah adalah masuk dalam gabungan Indeks JII70, KOMPAS100, IDX-MES-BUMN, & IDX-SHA-GROW.")
st.write("✅ Perhitungan Support (S), Cut Loss (CL), dan Taking Profit (TP) dengan Fibonacci.\n Support terkuat pada area Golden Ratio S3 (0.618) dan S4 (0.382)")

with st.sidebar:
    st.header("Parameter Scan")
    tgl_acuan = st.date_input("Tanggal Acuan Low", default_acuan)
    tgl_target = st.date_input("Tanggal Target (Data Terakhir)", today)
    jam_input = "15:20"
    btn_scan = st.button("Mulai Scan")

stock_ticker = load_tickers("tickers.txt")

if btn_scan:
    if not stock_ticker:
        st.error("Daftar saham kosong. Periksa file tickers.txt")
    else:
        df_hasil = jalankan_scanner_final(stock_ticker, tgl_acuan, tgl_target, jam_input)
        if not df_hasil.empty:
            st.success(f"Ditemukan {len(df_hasil)} saham!")
            st.dataframe(df_hasil, use_container_width=True)

            # --- TRADING PLAN ---
            st.divider()
            st.subheader("📝 Trading Plan")
            
            for index, row in df_hasil.iterrows():
                # Hitung Harga Avg (Skema 10-20-30-40)
                avg_p = (row['S1']*0.1) + (row['S2']*0.2) + (row['S3']*0.3) + (row['S4']*0.4)
                # Risk dari Avg ke CL
                risk_pct = ((row['CL'] - avg_p) / avg_p) * 100
                # Profit dari S1
                tp1_p = ((row['TP1'] - row['S1']) / row['S1']) * 100
                tp2_p = ((row['TP2'] - row['S1']) / row['S1']) * 100
                tp3_p = ((row['TP3'] - row['S1']) / row['S1']) * 100
                
                st.markdown(f"### **{row['Ticker']}**")
                st.write(f"**Buy :** {row['S1']}-{row['S2']}, {row['S3']}, {row['S4']}")
                st.write(f"**CL :** {row['CL']} ({risk_pct:.2f}% risk dari avg)")
                st.write(f"**TP :** {row['TP1']} ({tp1_p:.2f}%), {row['TP2']} ({tp2_p:.2f}%), {row['TP3']} ({tp3_p:.2f}%)")
                st.write("---")
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
