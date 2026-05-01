import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math

# --- KONFIGURASI ---
st.set_page_config(page_title="Scanner Saham", layout="wide")

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
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            symbol = f"{ticker}.JK"
            status_text.text(f"Memeriksa {symbol}...")
            
            data_raw = yf.download(symbol, start=tgl_str, end=tgl_besok, interval="5m", progress=False)
            
            if isinstance(data_raw.columns, pd.MultiIndex):
                data_raw.columns = data_raw.columns.get_level_values(0)

            if data_raw.empty: continue

            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(period="1d")
            if df_day.empty: continue

            data_raw.index = data_raw.index.tz_localize(None)
            match = data_raw[data_raw.index.strftime('%H:%M') == jam]
            
            if match.empty:
                # Fallback mencari waktu terdekat jika 15:20 tepat tidak ada
                search_time = datetime.combine(tgl, datetime.strptime(jam, "%H:%M").time())
                idx = data_raw.index.get_indexer([search_time], method='pad')[0]
                if idx == -1: continue
                lo = float(data_raw['Low'].iloc[idx])
            else:
                lo = float(match['Low'].iloc[0])

            last_c = float(df_day['Close'].iloc[-1])
            last_h = float(df_day['High'].iloc[-1])
            
            gain_h_pct = ((last_h - lo) / lo) * 100
            gain_c_pct = ((last_c - lo) / lo) * 100

            # Filter Kriteria Anda (> 21.26%)
            if gain_h_pct > 21.26:
                target_val = lo * 1.24
                range_fibo = target_val - lo
                
                # Kalkulasi Support & Target Lengkap
                s1 = round_bei(lo + (range_fibo * 0.886))
                s2 = round_bei(lo + (range_fibo * 0.786))
                s3 = round_bei(lo + (range_fibo * 0.618))
                s4 = round_bei(lo + (range_fibo * 0.500))
                cl = round_bei(lo + (range_fibo * 0.382))
                tp1 = round_bei(lo + (range_fibo * 1.272))
                tp2 = round_bei(lo + (range_fibo * 1.618))
                
                # Menentukan Posisi
                if last_c >= s1: pos = "> S1"
                elif last_c >= s2: pos = "> S2"
                elif last_c >= s3: pos = "> S3"
                elif last_c >= s4: pos = "> S4"
                elif last_c >= cl: pos = "> CL"
                else: pos = "< CL"

                # Masukkan semua kolom agar lengkap seperti di Colab
                results.append({
                    "Ticker": ticker, 
                    "Low": int(lo), 
                    "Last H %": f"{gain_h_pct:.2f}%",
                    "Last H": int(last_h),
                    "Last C %": f"{gain_c_pct:.2f}%",
                    "Last C": int(last_c), 
                    "Pos": pos,
                    "S1": s1, "S2": s2, "S3": s3, "S4": s4, "CL": cl,
                    "Target": round_bei(target_val), 
                    "TP1": tp1, 
                    "TP2": tp2,
                    "sort_val": gain_h_pct # Untuk sorting saja
                })
                
        except Exception:
            continue
        
        progress_bar.progress((i + 1) / len(tickers))
    
    status_text.text("Scan selesai!")
    if not results:
        return pd.DataFrame()
    
    # Urutkan berdasarkan kenaikan tertinggi
    final_df = pd.DataFrame(results).sort_values("sort_val", ascending=False)
    return final_df.drop(columns=['sort_val'])

# --- UI ---
st.title("🚀 Scanner Saham")

with st.sidebar:
    st.header("Parameter")
    tgl_input = st.date_input("Tanggal Acuan Low", datetime(2026, 4, 15))
    jam_input = st.text_input("Jam Acuan (WIB)", "15:20")
    btn_scan = st.button("Mulai Scan")

tickers_jii = ["AADI", "ACES", "ADMR", "ADRO", "AKRA", "ANTM", "ASII", "AVIA", "BKSL", "BRIS", 
               "BRMS", "BRPT", "BSDE", "BTPS", "BUMI", "CMRY", "CPIN", "CTRA", "DSNG", "DSSA", 
               "ELSA", "ENRG", "ERAA", "ESSA", "EXCL", "HEAL", "HRUM", "ICBP", "INCO", "INDF", 
               "INDY", "INKP", "INTP", "ISAT", "ITMG", "JPFA", "JSMR", "KIJA", "KLBF", "KPIG", 
               "LSIP", "MAPA", "MAPI", "MARK", "MBMA", "MDKA", "MEDC", "MIKA", "MTEL", "MYOR", 
               "NCKL", "PANI", "PGAS", "PGEO", "PTBA", "PTPP", "PWON", "RATU", "SIDO", "SMGR", 
               "SMRA", "SRTG", "SSIA", "TAPG", "TCPI", "TKIM", "TLKM", "TPIA", "UNTR", "UNVR"]

if btn_scan:
    df_hasil = jalankan_scanner(tickers_jii, tgl_input, jam_input)
    if not df_hasil.empty:
        st.success(f"Ditemukan {len(df_hasil)} saham!")
        
        # Perbaikan ada di sini: ganti "sort" menjadi "sort_val"
        df_display = df_hasil.sort_values("sort_val", ascending=False).drop(columns=['sort_val'])
        
        st.dataframe(df_display, use_container_width=True)
    else:
        st.error("Tidak ada saham yang memenuhi kriteria.")
