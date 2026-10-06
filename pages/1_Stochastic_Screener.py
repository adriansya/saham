import streamlit as st
from screener_stochastic import load_tickers, jalankan_screener

# --- KONFIGURASI ---
st.set_page_config(page_title="Screener Stochastic Golden Cross", layout="wide")

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
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(fraksi, pesan):
            progress_bar.progress(fraksi)
            status_text.text(pesan)

        interval = "1d" if tf == "Harian" else "1wk"
        df_hasil = jalankan_screener(tickers, interval, int(k_period), int(k_smooth), int(d_period),
                                     int(lookback), max_k, min_price, min_value_m * 1e9,
                                     on_progress=update_progress)
        status_text.empty()
        if not df_hasil.empty:
            st.success(f"Ditemukan {len(df_hasil)} saham dengan golden cross Stochastic "
                       f"({k_period},{k_smooth},{d_period})!")
            st.dataframe(df_hasil, use_container_width=True)
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
