import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings
import os
# --- TAMBAHAN IMPORT UNTUK CHART ---
import plotly.graph_objects as go 


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
    tgl_end_query = (tgl_target + timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        hour_wib = int(jam.split(':')[0])
        minute_wib = jam.split(':')[1]
        jam_utc = f"{hour_wib - 7:02d}:{minute_wib}"
    except:
        jam_utc = "08:20" 
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            status_text.text(f"Scanning {i+1}/{len(tickers)}: {ticker}")
            
            df_5m = yf.download(symbol, start=tgl_start, end=(tgl_acuan + timedelta(days=2)).strftime("%Y-%m-%d"), interval="5m", progress=False)
            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(start=tgl_start, end=tgl_end_query)
            
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            if not df_5m.empty and not df_day.empty:
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                if match.empty: 
                    match = df_5m.head(1)
                
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

                    s1 = round_bei(lo + (range_fibo * 0.886))
                    s2 = round_bei(lo + (range_fibo * 0.618))
                    s3 = round_bei(lo + (range_fibo * 0.382))
                    s4 = get_tick_down(s3, ticks=2) # 2 tick di bawah S3
                    sl = get_tick_down(s3, ticks=4) # 4 tick di bawah S3 (Cutloss)
                    
                    tp1 = round_bei(lo + (range_fibo * 1.128))
                    tp2 = round_bei(lo + (range_fibo * 1.272))
                    tp3 = round_bei(lo + (range_fibo * 1.414))

                    if last_c < s3:
                        continue

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
                        "S1": s1, "S2": s2, "S3": s3, "S4": s4, "SL": sl,
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

# ... (kode fungsi sebelumnya: round_bei, get_tick_down, load_tickers, jalankan_scanner_final) ...

def plot_interactive_chart(ticker, levels):
    """Membuat chart candlestick interaktif dengan garis Support, TP, dan SL."""
    symbol = ticker + ".JK"
    
    # Hitung rentang waktu: 1 bulan ke belakang dari hari ini
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    with st.spinner(f'Mengambil data chart 2H untuk {ticker}...'):
        # Ambil data 2 jam (2h)
        df_chart = yf.download(symbol, start=start_date, end=end_date, interval="2h", progress=False)
        
        # Perbaikan MultiIndex Columns jika ada
        if isinstance(df_chart.columns, pd.MultiIndex):
            df_chart.columns = df_chart.columns.get_level_values(0)

    if df_chart.empty:
        st.error(f"Tidak dapat mengambil data chart untuk {ticker}.")
        return

    # Buat figure Candlestick
    fig = go.Figure(data=[go.Candlestick(x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="Candlestick")])

    # --- TAMBAHKAN GARIS HORIZONTAL (SUPPORT, TP, CL) ---
    
    # Definisi Level (Warna disesuaikan: Ijo buat Buy/TP, Merah buat SL)
    plot_levels = [
        {'id': 'S1', 'val': levels['S1'], 'color': 'rgba(34, 139, 34, 0.6)', 'dash': 'dash'}, # ForestGreen
        {'id': 'S2', 'val': levels['S2'], 'color': 'rgba(50, 205, 50, 0.7)', 'dash': 'dash'}, # LimeGreen
        {'id': 'S3', 'val': levels['S3'], 'color': 'rgba(173, 255, 47, 0.8)', 'dash': 'dash'}, # GreenYellow
        {'id': 'S4', 'val': levels['S4'], 'color': 'rgba(255, 215, 0, 0.8)', 'dash': 'dot'},  # Gold
        {'id': 'TP1', 'val': levels['TP1'], 'color': 'rgba(0, 0, 255, 0.8)', 'dash': 'solid'}, # Blue
        {'id': 'TP2', 'val': levels['TP2'], 'color': 'rgba(0, 0, 139, 0.9)', 'dash': 'solid'}, # DarkBlue
        {'id': 'CL (SL)', 'val': levels['SL'], 'color': 'rgba(255, 0, 0, 0.9)', 'dash': 'solid'}, # Red
    ]

    for level in plot_levels:
        if level['val'] > 0: # Pastikan harganya valid
            fig.add_hline(y=level['val'], 
                          line_dash=level['dash'],
                          line_color=level['color'],
                          line_width=2,
                          annotation_text=f"{level['id']} ({int(level['val'])})", 
                          annotation_position="top right",
                          annotation_font_color=level['color'])

    # Konfigurasi Layout
    fig.update_layout(
        title=f"Chart 2 Jam (2H) - 1 Bulan Terakhir: {ticker}",
        yaxis_title="Harga (IDR)",
        xaxis_title="Waktu",
        xaxis_rangeslider_visible=False, # Matikan range slider bawah agar chart utama lebih luas
        height=600, # Tinggi chart
        template="plotly_dark", # Tema gelap (cocok buat trader)
        hovermode='x unified' # Tampilan hover yang rapi
    )

    # Tampilkan di Streamlit
    st.plotly_chart(fig, use_container_width=True)

# --- UI LOGIC STARTS HERE ---
# ... (kode UI Logic sebelumnya) ...

# --- UI LOGIC ---
st.title("Scanner Saham Momentum 🚀")
st.markdown("""
* **Strategi:** Momentum dengan Fibonacci Retracement.
* **Skema Entry:** Bertahap di Support dengan skema Piramida **20% (S1)**, **30% (S2)**, dan **50% (S3)**.
""")

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
        st.error("File 'tickers.txt' tidak ditemukan!")
    else:
        df_hasil = jalankan_scanner_final(tickers, tgl_acuan, tgl_target, jam_input)
        
        if not df_hasil.empty:
            st.success(f"Ditemukan {len(df_hasil)} saham potensial!")
            st.dataframe(df_hasil, use_container_width=True)

            st.divider()
            st.subheader("📝 Trading Plan")
            
            cols = st.columns(2)
            # ... (di dalam if btn_scan: ... if not df_hasil.empty: ... st.subheader("📝 Trading Plan")) ...
            
            # --- MODIFIKASI DISINI ---
            
            # Inisialisasi session state untuk menyimpan saham mana yang sedang dipilih/diklik
            if 'selected_ticker' not in st.session_state:
                st.session_state.selected_ticker = None

            # Tampilan Grid untuk Trading Plan
            cols = st.columns(2)
            for idx, row in enumerate(df_hasil.to_dict(orient='records')):
                with cols[idx % 2]:
                    with st.container(border=True):
                        # Hitung Avg Price dengan skema 20-30-40-10
                        avg_p = (row['S1']*0.20) + (row['S2']*0.30) + (row['S3']*0.40) + (row['S4']*0.10)
                        
                        risk_pct = ((row['SL'] - avg_p) / avg_p) * 100
                        tp1_pct = ((row['TP1'] - avg_p) / avg_p) * 100
                        tp2_pct = ((row['TP2'] - avg_p) / avg_p) * 100
                        
                        # --- GANTI SUBHEADER MENJADI TOMBOL ---
                        # Buat key unik untuk setiap tombol menggunakan ticker dan index
                        btn_key = f"btn_{row['Ticker']}_{idx}"
                        if st.button(f"📈 {row['Ticker']} (Klik untuk Chart)", key=btn_key, use_container_width=True):
                            st.session_state.selected_ticker = row['Ticker']
                            # Menyimpan data level untuk chart di session state
                            st.session_state.current_levels = {
                                'S1': row['S1'], 'S2': row['S2'], 'S3': row['S3'], 'S4': row['S4'],
                                'TP1': row['TP1'], 'TP2': row['TP2'], 'SL': row['SL']
                            }
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success(f"**Buy Zone:**")
                            st.write(f"- S1 (20%): **{row['S1']}**")
                            st.write(f"- S2 (30%): **{row['S2']}**")
                            st.write(f"- S3-S4 (50%): **{row['S3']}-{row['S4']}**")
                        with c2:
                            st.error(f"**Sell Zone:**")
                            st.write(f"- TP1: **{row['TP1']}**")
                            st.write(f"- TP2: **{row['TP2']}**")
                            st.write(f"- SL: **<{row['SL']}**") # Tampilan diubah jadi < CL
                        
                        st.info(f"**Avg Price:** {int(avg_p)} | **Risk:** {abs(risk_pct):.2f}%")
                        st.write(f"Potensi Reward TP1: **{tp1_pct:.2f}%**")

            # --- AREA UNTUK MENAMPILKAN CHART JIKA SAHAM DIKLIK ---
            st.divider()
            if st.session_state.selected_ticker:
                st.subheader(f"📊 Detil Chart: {st.session_state.selected_ticker}")
                # Panggil fungsi chart dengan data yang disimpan di session state
                plot_interactive_chart(st.session_state.selected_ticker, st.session_state.current_levels)
                
                # Tombol untuk menutup chart
                if st.button("Tutup Chart"):
                    st.session_state.selected_ticker = None
                    st.rerun() # Refresh untuk menghilangkan chart
        
        else:
            # ... (Tampilan jika tidak ada saham yang memenuhi kriteria)
