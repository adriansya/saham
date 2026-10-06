import gradio as gr
from screener_stochastic import load_tickers, jalankan_screener

def scan(k_period, k_smooth, d_period, tf, lookback, max_k, min_price, min_value_m,
         progress=gr.Progress()):
    tickers = load_tickers()
    if not tickers:
        raise gr.Error("File 'tickers.txt' tidak ditemukan!")

    interval = "1d" if tf == "Harian" else "1wk"
    df = jalankan_screener(tickers, interval, int(k_period), int(k_smooth), int(d_period),
                           int(lookback), max_k, min_price, min_value_m * 1e9,
                           on_progress=lambda fraksi, pesan: progress(fraksi, desc=pesan))
    if df.empty:
        return "⚠️ Tidak ada saham yang memenuhi kriteria.", None
    pesan = (f"✅ Ditemukan **{len(df)}** saham dengan golden cross Stochastic "
             f"({int(k_period)},{int(k_smooth)},{int(d_period)})!")
    return pesan, df

with gr.Blocks(title="Screener Stochastic Golden Cross") as demo:
    gr.Markdown("""
# Screener Stochastic Golden Cross 📈
* **Indikator:** Slow Stochastic (default 14, 5, 5).
* **Sinyal:** Golden cross = garis %K memotong ke atas garis %D.
* **Tips:** Golden cross di area oversold (%K < 20) biasanya sinyal yang lebih kuat.
""")
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Pengaturan Stochastic")
            with gr.Row():
                k_period = gr.Number(label="%K", value=14, minimum=1, precision=0)
                k_smooth = gr.Number(label="Slow", value=5, minimum=1, precision=0)
                d_period = gr.Number(label="%D", value=5, minimum=1, precision=0)
            tf = gr.Radio(["Harian", "Mingguan"], value="Harian", label="Timeframe")
            lookback = gr.Slider(1, 10, value=1, step=1, label="Cross dalam N candle terakhir",
                                 info="1 = cross terjadi di candle terakhir saja")

            gr.Markdown("### 🔎 Filter")
            max_k = gr.Slider(0, 100, value=100, step=1, label="Maks. %K saat cross",
                              info="Isi 20 untuk hanya mencari cross di area oversold")
            min_price = gr.Number(label="Harga minimum", value=50, minimum=0)
            min_value_m = gr.Number(label="Nilai transaksi minimum (Miliar Rp)", value=0, minimum=0)
            btn = gr.Button("Jalankan Screener", variant="primary")

        with gr.Column(scale=3):
            status = gr.Markdown()
            hasil = gr.Dataframe(label="Hasil Screener", interactive=False)

    btn.click(scan,
              inputs=[k_period, k_smooth, d_period, tf, lookback, max_k, min_price, min_value_m],
              outputs=[status, hasil])

if __name__ == "__main__":
    demo.launch()
