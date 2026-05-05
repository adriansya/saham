import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings
import os
import plotly.graph_objects as go

# --- KONFIGURASI ---
warnings.simplefilter(action='ignore', category=FutureWarning)
st.set_page_config(page_title="Scanner Saham Momentum", layout="wide")

def round_bei(price, direction="up"):
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

def plot_interactive_chart(ticker, levels):
    symbol = ticker + ".JK"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    with st.spinner(f'Mengambil data chart 2H untuk {ticker}...'):
        df_chart = yf.download(symbol, start=start_date, end=end_date, interval="2h", progress=False)
        if isinstance(df_chart.columns, pd.MultiIndex):
            df_chart.columns = df_chart.columns.get_level_values(0)

    if df_chart.empty:
        st.error(f"Data chart {ticker} kosong.")
        return

    fig = go.Figure(data=[go.Candlestick(x=df_chart.index,
                    open=df_chart['Open'], high=df_chart['High'],
                    low=df_chart['Low'], close=df_chart['Close'], name="2H Chart")])

    plot_levels = [
        {'id': 'S1', 'val': levels['S1'], 'color': '#00FF00', 'dash': 'dash'},
        {'id': 'S2', 'val': levels['S2'], 'color': '#ADFF2F', 'dash': 'dash'},
        {'id': 'S3', 'val': levels['S3'], 'color': '#FFFF00', 'dash': 'dash'},
        {'id': 'S4', 'val': levels['S4'], 'color': '#FFA500', 'dash': 'dot'},
        {'id': 'TP1', 'val': levels['TP1'], 'color': '#00BFFF', 'dash': 'solid'},
        {'id': 'TP2', 'val': levels['TP2'], 'color': '#1E90FF', 'dash': 'solid'},
        {'id': 'CL', 'val': levels['SL'], 'color': '#FF4B4B', 'dash': 'solid'},
    ]

    for level in plot_levels:
        fig.add_hline(y=level['val'], line_dash=level['dash'], line_color=level['color'],
                      annotation_text=f"{level['id']} ({int(level['val'])})", annotation_position="top right")

    fig.update_layout(title=f"{ticker} - 2H Interaktif", template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

def jalankan_scanner_final(tickers, tgl_acuan, tgl_target, jam):
    results = []
    tgl_start = tgl_acuan.strftime("%Y-%m-%d")
    tgl_end_query = (tgl_target + timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        hour_wib = int(jam.split(':')[0])
        jam_utc = f"{hour_wib - 7:02d}:{jam.split(':')[1]}"
    except:
        jam_utc = "08:20" 
    
    progress_bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            df_5m = yf.download(symbol, start=tgl_start, end=(tgl_acuan + timedelta(days=2)).strftime("%Y-%m-%d"), interval="5m", progress=False)
            ticker_obj = yf.Ticker(symbol)
            df_day = ticker_obj.history(start=tgl_start, end=tgl_end_query)
            
            if isinstance(df_5m.columns, pd.MultiIndex): df_5m.columns = df_5m.columns.get_level_values(0)

            if not df_5m.empty and not df_day.empty:
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                lo = float(match['Low'].iloc[0]) if not match.empty else float(df_5m['Low'].iloc[0])
                target_val = lo * 1.24 
                
                max_high_val = float(df_day['High'].max())
                gain_h_pct = ((max_high_val - lo) / lo) * 100
                
                if gain_h_pct > 23.5:
                    range_fibo = target_val - lo
                    s1, s2, s3 = round_bei(lo+(range_fibo*0.886)), round_bei(lo+(range_fibo*0.618)), round_bei(lo+(range_fibo*0.382))
                    s4, sl = get_tick_down(s3, ticks=2), get_tick_down(s3, ticks=4)
                    tp1, tp2 = round_bei(lo+(range_fibo*1.128)), round_bei(lo+(range_fibo*1.272))

                    last_c = float(df_day['Close'].iloc[-1])
                    if last_c < s3: continue

                    results.append({
                        "Ticker": ticker, "Close": last_c, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "SL": sl,
                        "TP1": tp1, "TP2": tp2, "Sort_Val": ((last_c - lo) / lo) * 100
                    })
        except: continue
        finally: progress_bar.progress((i + 1) / len(tickers))
    return pd.DataFrame(results).sort_values(by="Sort_Val", ascending=False) if results else pd.DataFrame()

# --- UI LOGIC ---
st.title("Scanner Saham Momentum 🚀")

if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None

with st.sidebar:
    st.header("⚙️ Pengaturan")
    tgl_acuan = st.date_input("Tanggal Low Acuan", datetime.now() - timedelta(days=20))
    tgl_target = st.date_input("Tanggal Data Terakhir", datetime.now())
    btn_scan = st.button("Jalankan Scanner", use_container_width=True)

tickers = load_tickers()

if btn_scan:
    df_hasil = jalankan_scanner_final(tickers, tgl_acuan, tgl_target, "15:20")
    if not df_hasil.empty:
        st.session_state.df_hasil = df_hasil
        st.success(f"Ditemukan {len(df_hasil)} saham!")
    else:
        st.warning("Kriteria tidak terpenuhi.")

if 'df_hasil' in st.session_state:
    st.dataframe(st.session_state.df_hasil, use_container_width=True)
    st.divider()
    st.subheader("📝 Trading Plan (Klik Ticker untuk Chart)")
    
    cols = st.columns(2)
    for idx, row in enumerate(st.session_state.df_hasil.to_dict(orient='records')):
        with cols[idx % 2]:
            with st.container(border=True):
                if st.button(f"📊 {row['Ticker']}", key=f"btn_{row['Ticker']}"):
                    st.session_state.selected_ticker = row['Ticker']
                    st.session_state.current_levels = row

                avg_p = (row['S1']*0.2) + (row['S2']*0.3) + (row['S3']*0.4) + (row['S4']*0.1)
                st.write(f"**Buy Zone:** S1:{row['S1']} | S2:{row['S2']} | S3-S4:{row['S3']}-{row['S4']}")
                st.write(f"**Avg:** {int(avg_p)} | **SL:** {row['SL']} | **TP1:** {row['TP1']}")

    if st.session_state.selected_ticker:
        st.divider()
        plot_interactive_chart(st.session_state.selected_ticker, st.session_state.current_levels)
        if st.button("Tutup Chart"):
            st.session_state.selected_ticker = None
            st.rerun()
