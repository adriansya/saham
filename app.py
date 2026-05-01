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
            
            # 1. Ambil data 5 menit
            data_raw = yf.download(symbol, start=tgl_str, end=tgl_besok, interval="5m", progress=False)
            
            if isinstance(data_raw.columns, pd.MultiIndex):
                data_raw.columns = data_raw.columns.get_level_values(0)

            if data_raw.empty: continue

            # 2. Pastikan Timezone bersih
            data_raw.index = data_raw.index.tz_localize(None)
            
            # 3. Logika mencari jam 15:20 yang SANGAT KETAT
            target_time = datetime.strptime(f"{tgl_str} {jam}", "%Y-%m-%d %H:%M")
            
            # Kita cari index yang paling dekat dengan jam 15:20
            # method='pad' artinya mengambil data terakhir yang tersedia SEBELUM atau PAS jam tersebut
            idx = data_raw.index.get_indexer([target_time], method='pad')[0]
            
            if idx != -1:
                lo = float(data_raw['Low'].iloc[idx])
            else:
                continue

            # 4. Ambil data Daily untuk High & Close hari ini
            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(period="1d")
            if df_day.empty: continue

            last_c = float(df_day['Close'].iloc[-1])
            last_h = float(df_day['High'].iloc[-1])
            
            gain_h_pct = ((last_h - lo) / lo) * 100
            gain_c_pct = ((last_c - lo) / lo) * 100

            # 5. Filter kriteria (Sesuai Colab)
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
                
                # Cek Posisi
                if last_c >= s1: pos = "> S1"
                elif last_c >= cl: pos = "> CL"
                else: pos = "< CL"

                results.append({
                    "Ticker": ticker, "Low": int(lo), 
                    "Last H %": gain_h_pct, "Last H": int(last_h),
                    "Last C %": f"{gain_c_pct:.2f}%", "Last C": int(last_c), 
                    "Pos": pos, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "CL": cl,
                    "Target": round_bei(target_val), "TP1": tp1, "TP2": tp2
                })
                
        except Exception:
            continue
        
        progress_bar.progress((i + 1) / len(tickers))
    
    status_text.text("Scan selesai!")
    return pd.DataFrame(results)

# --- UI ---
st.title("🚀 Scanner Saham")

with st.sidebar:
    st.header("Input Parameter")
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
        
        # Sorting berdasarkan Last H % (yang masih berupa angka)
        df_hasil = df_hasil.sort_values("Last H %", ascending=False)
        
        # Baru ubah format tampilan Last H % menjadi string persen
        df_hasil["Last H %"] = df_hasil["Last H %"].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(df_hasil, use_container_width=True)
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria.")
