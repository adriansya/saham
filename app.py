import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# Konfigurasi Halaman
st.set_page_config(page_title="Scanner Saham Fibo", layout="wide")

def round_bei(price):
    if price <= 0: return 0
    if price < 200: f = 1
    elif price < 500: f = 2
    elif price < 2000: f = 5
    elif price < 5000: f = 10
    else: f = 25
    return int(math.floor(price / f) * f)

def jalankan_scanner(tickers, tgl, jam):
    results = []
    tgl_str = tgl.strftime("%Y-%m-%d")
    tgl_besok = (tgl + timedelta(days=1)).strftime("%Y-%m-%d")
    jam_utc = f"{int(jam.split(':')[0]) - 7:02d}:{jam.split(':')[1]}"

    progress_bar = st.progress(0)
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            df_5m = yf.download(symbol, start=tgl_str, end=tgl_besok, interval="5m", progress=False)
            df_day = yf.Ticker(symbol).history(period="1d")

            if not df_5m.empty and not df_day.empty:
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                if not match.empty:
                    lo = float(match['Low'].iloc[0])
                    last_c = float(df_day['Close'].iloc[-1])
                    last_h = float(df_day['High'].iloc[-1])
                    
                    gain_c_pct = ((last_c - lo) / lo) * 100
                    gain_h_pct = ((last_h - lo) / lo) * 100

                    if gain_h_pct > 21.26:
                        target_val = lo * 1.24
                        range_fibo = target_val - lo
                        
                        s1 = round_bei(lo + (range_fibo * 0.886))
                        s2 = round_bei(lo + (range_fibo * 0.786))
                        s3 = round_bei(lo + (range_fibo * 0.618))
                        s4 = round_bei(lo + (range_fibo * 0.500))
                        cl = round_bei(lo + (range_fibo * 0.382))
                        tp1 = round_bei(lo + (range_fibo * 1.272))
                        tp2 = round_bei(lo + (range_fibo * 1.618))
                        
                        if last_c >= s1: pos = "> S1"
                        elif last_c >= s2: pos = "> S2"
                        elif last_c >= s3: pos = "> S3"
                        elif last_c >= s4: pos = "> S4"
                        elif last_c >= cl: pos = "> CL"
                        else: pos = "< CL"

                        results.append({
                            "Ticker": ticker, "Low": int(lo), "Last H": int(last_h),
                            "% Last H": f"{gain_h_pct:.2f}%", "Last C": int(last_c), 
                            "% Last C": f"{gain_c_pct:.2f}%", "Pos": pos,
                            "S1": s1, "S2": s2, "S3": s3, "S4": s4, "CL": cl,
                            "Target": round_bei(target_val), "TP1": tp1, "TP2": tp2,
                            "sort": gain_h_pct
                        })
        except: continue
        progress_bar.progress((i + 1) / total)
    
    return pd.DataFrame(results)

# --- Tampilan Web ---
st.title("🚀 Scanner Saham JII70 - Fibo Target 24%")
st.sidebar.header("Input Parameter")

tgl_input = st.sidebar.date_input("Tanggal Acuan Low", datetime.now() - timedelta(days=1))
jam_input = st.sidebar.text_input("Jam Acuan (WIB)", "15:20")

tickers_jii = ["AADI", "ACES", "ADMR", "ADRO", "AKRA", "ANTM", "ASII", "AVIA", "BKSL", "BRIS", 
               "BRMS", "BRPT", "BSDE", "BTPS", "BUMI", "CMRY", "CPIN", "CTRA", "DSNG", "DSSA", 
               "ELSA", "ENRG", "ERAA", "ESSA", "EXCL", "HEAL", "HRUM", "ICBP", "INCO", "INDF", 
               "INDY", "INKP", "INTP", "ISAT", "ITMG", "JPFA", "JSMR", "KIJA", "KLBF", "KPIG", 
               "LSIP", "MAPA", "MAPI", "MARK", "MBMA", "MDKA", "MEDC", "MIKA", "MTEL", "MYOR", 
               "NCKL", "PANI", "PGAS", "PGEO", "PTBA", "PTPP", "PWON", "RATU", "SIDO", "SMGR", 
               "SMRA", "SRTG", "SSIA", "TAPG", "TCPI", "TKIM", "TLKM", "TPIA", "UNTR", "UNVR"]

if st.sidebar.button("Mulai Scan"):
    with st.spinner("Sedang menarik data dari Yahoo Finance..."):
        df_hasil = jalankan_scanner(tickers_jii, tgl_input, jam_input)
        
        if not df_hasil.empty:
            df_hasil = df_hasil.sort_values(by="sort", ascending=False).drop(columns=["sort"])
            st.success(f"Ditemukan {len(df_hasil)} saham dengan % Last H > 21.26%")
            st.dataframe(df_hasil, use_container_width=True)
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
