import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Scanner Saham", layout="wide")

def round_bei(price):
    """Fungsi pembulatan ke ATAS sesuai fraksi harga BEI."""
    if price <= 0: return 0
    if price < 200: f = 1
    elif price < 500: f = 2
    elif price < 2000: f = 5
    elif price < 5000: f = 10
    else: f = 25
    # Menggunakan math.ceil untuk pembulatan ke atas
    return int(math.ceil(price / f) * f)

def jalankan_scanner_final(tickers, tgl, jam):
    results = []
    
    tgl_str = tgl.strftime("%Y-%m-%d")
    tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d")
    tgl_besok = (tgl_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Logika Konversi WIB ke UTC (-7) sesuai Colab
    jam_utc = f"{int(jam.split(':')[0]) - 7:02d}:{jam.split(':')[1]}"
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        try:
            symbol = ticker + ".JK"
            status_text.text(f"Memeriksa {symbol}...")
            
            df_5m = yf.download(symbol, start=tgl_str, end=tgl_besok, interval="5m", progress=False)
            df_day = yf.Ticker(symbol).history(period="1d")
            
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            if not df_5m.empty and not df_day.empty:
                # Cari jam berdasarkan format string UTC
                match = df_5m[df_5m.index.strftime('%H:%M') == jam_utc]
                if match.empty: continue

                lo = float(match['Low'].iloc[0])
                last_c = float(df_day['Close'].iloc[-1])
                last_h = float(df_day['High'].iloc[-1])

                gain_c_pct = ((last_c - lo) / lo) * 100
                gain_h_pct = ((last_h - lo) / lo) * 100

                # FILTER: Area S1 (21.26%)
                if gain_h_pct > 21.26:
                    target_val = lo * 1.24
                    range_fibo = target_val - lo

                    # Perhitungan level dengan pembulatan ke atas
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

# --- ANTARMUKA PENGGUNA (UI) ---
st.title("🚀 Scanner Saham")
st.write("Mencari saham dengan lonjakan harga signifikan. Sudah naik 24% sejak tanggal 15.")

with st.sidebar:
    st.header("Parameter Scan")
    tgl_input = st.date_input("Tanggal Acuan Low", datetime(2026, 4, 15).date())
    jam_input = st.text_input("Jam Acuan (WIB)", "15:20")
    btn_scan = st.button("Mulai Scan")

stock_ticker = [
   'AADI', 'AALI', 'ABMM', 'ACES', 'ACST', 'ADCP', 'ADES', 'ADHI', 'ADMG', 'ADMR', 
    'ADRO', 'AGAR', 'AGII', 'AIMS', 'AISA', 'AKKU', 'AKPI', 'AKRA', 'AKSI', 'ALDO', 
    'ALKA', 'AMAN', 'AMFG', 'AMIN', 'ANDI', 'ANJT', 'ANTM', 'APII', 'APLI', 'APLN', 
    'ARCI', 'AREA', 'ARGO', 'ARII', 'ARNA', 'ARTA', 'ASGR', 'ASHA', 'ASII', 'ASLC', 
    'ASLI', 'ASPI', 'ASRI', 'ASSA', 'ATAP', 'ATIC', 'ATLA', 'AUTO', 'AVIA', 'AWAN', 
    'AXIO', 'AYAM', 'AYLS', 'BABY', 'BAIK', 'BANK', 'BAPI', 'BATA', 'BATR', 'BAUT', 
    'BAYU', 'BBRM', 'BBSS', 'BCIP', 'BDKR', 'BEEF', 'BELI', 'BELL', 'BESS', 'BEST', 
    'BIKE', 'BINO', 'BIPP', 'BIRD', 'BISI', 'BKDP', 'BKSL', 'BLES', 'BLOG', 'BLTA', 
    'BLTZ', 'BLUE', 'BMHS', 'BMSR', 'BMTR', 'BNBR', 'BOAT', 'BOBA', 'BOGA', 'BOLA', 
    'BOLT', 'BRAM', 'BRIS', 'BRMS', 'BRNA', 'BRPT', 'BRRC', 'BSBK', 'BSDE', 'BSML', 
    'BSSR', 'BTPS', 'BUAH', 'BUKK', 'BULL', 'BUMI', 'BUVA', 'BYAN', 'CAKK', 'CAMP', 
    'CANI', 'CARE', 'CASS', 'CBDK', 'CBPE', 'CBRE', 'CCSI', 'CEKA', 'CGAS', 'CHEK', 
    'CHEM', 'CINT', 'CITA', 'CITY', 'CLEO', 'CLPI', 'CMNP', 'CMPP', 'CMRY', 'CNKO', 
    'CNMA', 'COAL', 'CPIN', 'CPRO', 'CRAB', 'CRSN', 'CSAP', 'CSIS', 'CSMI', 'CSRA', 
    'CTBN', 'CTRA', 'CYBR', 'DAAZ', 'DADA', 'DATA', 'DAYA', 'DCII', 'DEFI', 'DEPO', 
    'DEWA', 'DEWI', 'DGIK', 'DGNS', 'DGWG', 'DILD', 'DIVA', 'DKFT', 'DKHH', 'DMAS', 
    'DMMX', 'DMND', 'DOOH', 'DOSS', 'DRMA', 'DSFI', 'DSNG', 'DSSA', 'DUTI', 'DVLA', 
    'DWGL', 'DYAN', 'EAST', 'ECII', 'EDGE', 'EKAD', 'ELIT', 'ELPI', 'ELSA', 'ELTY', 
    'EMDE', 'ENAK', 'ENRG', 'EPAC', 'EPMT', 'ERAA', 'ERAL', 'ESIP', 'ESSA', 'ESTA', 
    'EXCL', 'FAST', 'FASW', 'FILM', 'FIRE', 'FISH', 'FITT', 'FMII', 'FOLK', 'FOOD', 
    'FORE', 'FPNI', 'FUTR', 'FWCT', 'GDST', 'GDYR', 'GEMA', 'GEMS', 'GGRP', 'GHON', 
    'GIAA', 'GJTL', 'GLVA', 'GMTD', 'GOLD', 'GOLF', 'GOOD', 'GPRA', 'GPSO', 'GRIA', 
    'GRPH', 'GTBO', 'GTRA', 'GTSI', 'GULA', 'GUNA', 'GWSA', 'GZCO', 'HADE', 'HAIS', 
    'HALO', 'HATM', 'HDIT', 'HEAL', 'HERO', 'HEXA', 'HGII', 'HITS', 'HOKI', 'HOMI', 
    'HOPE', 'HRME', 'HRUM', 'HUMI', 'HYGN', 'IATA', 'IBST', 'ICBP', 'ICON', 'IDPR', 
    'IFII', 'IFSH', 'IGAR', 'IIKP', 'IKAI', 'IKAN', 'IKBI', 'IKPM', 'IMPC', 'INCI', 
    'INCO', 'INDF', 'INDR', 'INDS', 'INDX', 'INDY', 'INET', 'INKP', 'INPP', 'INTD', 
    'INTP', 'IOTF', 'IPCC', 'IPCM', 'IPOL', 'IPTV', 'IRRA', 'IRSX', 'ISAT', 'ISSP', 
    'ITMA', 'ITMG', 'JAST', 'JATI', 'JAWA', 'JAYA', 'JECC', 'JGLE', 'JIHD', 'JKON', 
    'JMAS', 'JPFA', 'JRPT', 'JSMR', 'JSPT', 'JTPE', 'KAQI', 'KARW', 'KBAG', 'KBLI', 
    'KBLM', 'KDSI', 'KDTN', 'KEEN', 'KEJU', 'KETR', 'KIAS', 'KICI', 'KIJA', 'KINO', 
    'KIOS', 'KJEN', 'KKES', 'KKGI', 'KLAS', 'KLBF', 'KMDS', 'KOBX', 'KOCI', 'KOIN', 
    'KOKA', 'KONI', 'KOPI', 'KOTA', 'KPIG', 'KREN', 'KRYA', 'KSIX', 'KUAS', 'LABA', 
    'LABS', 'LAJU', 'LAND', 'LCKM', 'LION', 'LIVE', 'LMPI', 'LMSH', 'LPCK', 'LPIN', 
    'LPKR', 'LPLI', 'LPPF', 'LRNA', 'LSIP', 'LTLS', 'LUCK', 'MAHA', 'MAIN', 'MAPA', 
    'MAPB', 'MAPI', 'MARK', 'MAXI', 'MBAP', 'MBMA', 'MBTO', 'MCAS', 'MCOL', 'MDIY', 
    'MDKA', 'MDKI', 'MDLA', 'MEDC', 'MEDS', 'MERI', 'MERK', 'META', 'MFMI', 'MGNA', 
    'MHKI', 'MICE', 'MIDI', 'MIKA', 'MINA', 'MINE', 'MIRA', 'MITI', 'MKAP', 'MKPI', 
    'MKTR', 'MLIA', 'MLPL', 'MLPT', 'MMIX', 'MMLP', 'MNCN', 'MORA', 'MPIX', 'MPMX', 
    'MPOW', 'MPPA', 'MPRO', 'MRAT', 'MSIN', 'MSJA', 'MSKY', 'MSTI', 'MTDL', 'MTEL', 
    'MTFN', 'MTLA', 'MTMH', 'MTPS', 'MTSM', 'MUTU', 'MYOH', 'MYOR', 'NAIK', 'NASA', 
    'NASI', 'NCKL', 'NELY', 'NEST', 'NETV', 'NFCX', 'NICE', 'NICL', 'NIKL', 'NPGF', 
    'NRCA', 'NTBK', 'NZIA', 'OASA', 'OBAT', 'OBMD', 'OILS', 'OKAS', 'OMED', 'OMRE', 
    'PADA', 'PALM', 'PAMG', 'PANI', 'PANR', 'PART', 'PBID', 'PBSA', 'PCAR', 'PDES', 
    'PDPP', 'PEHA', 'PEVE', 'PGAS', 'PGEO', 'PGLI', 'PGUN', 'PICO', 'PIPA', 'PJAA', 
    'PJHB', 'PKPK', 'PLIN', 'PMJS', 'PMUI', 'PNBS', 'PNGO', 'PNSE', 'POLI', 'POLU', 
    'PORT', 'POWR', 'PPRE', 'PPRI', 'PPRO', 'PRAY', 'PRDA', 'PRIM', 'PSAB', 'PSAT', 
    'PSDN', 'PSGO', 'PSKT', 'PSSI', 'PTBA', 'PTIS', 'PTMP', 'PTMR', 'PTPP', 'PTPS', 
    'PTPW', 'PTSN', 'PTSP', 'PURA', 'PURI', 'PWON', 'PZZA', 'RAAM', 'RAFI', 'RAJA', 
    'RALS', 'RANC', 'RATU', 'RBMS', 'RDTX', 'RGAS', 'RIGS', 'RISE', 'RMKE', 'RMKO', 
    'ROCK', 'RODA', 'RONY', 'ROTI', 'RSGK', 'RUIS', 'SAFE', 'SAGE', 'SAME', 'SAMF', 
    'SAPX', 'SATU', 'SBMA', 'SCCO', 'SCNP', 'SCPI', 'SEMA', 'SGER', 'SGRO', 'SHID', 
    'SHIP', 'SICO', 'SIDO', 'SILO', 'SIMP', 'SIPD', 'SKBM', 'SKLT', 'SKRN', 'SLIS', 
    'SMAR', 'SMBR', 'SMCB', 'SMDM', 'SMDR', 'SMGA', 'SMGR', 'SMIL', 'SMKL', 'SMLE', 
    'SMMT', 'SMRA', 'SMSM', 'SNLK', 'SOCI', 'SOHO', 'SOLA', 'SONA', 'SOSS', 'SOTS', 
    'SPMA', 'SPTO', 'SRTG', 'SSIA', 'SSTM', 'STAA', 'STTP', 'SULI', 'SUNI', 'SUPR', 
    'SURI', 'SWID', 'TALF', 'TAMA', 'TAMU', 'TAPG', 'TARA', 'TAXI', 'TBMS', 'TCID', 
    'TCPI', 'TEBE', 'TFAS', 'TFCO', 'TGKA', 'TGUK', 'TINS', 'TIRA', 'TIRT', 'TKIM', 
    'TLDN', 'TLKM', 'TMAS', 'TMPO', 'TNCA', 'TOBA', 'TOOL', 'TOSK', 'TOTL', 'TOTO', 
    'TPIA', 'TPMA', 'TRIS', 'TRJA', 'TRON', 'TRST', 'TRUE', 'TRUK', 'TSPC', 'TYRE', 
    'UANG', 'UCID', 'UFOE', 'ULTJ', 'UNIC', 'UNIQ', 'UNTR', 'UNVR', 'UVCR', 'VAST', 
    'VERN', 'VICI', 'VISI', 'VKTR', 'VOKS', 'WAPO', 'WEGE', 'WEHA', 'WINR', 'WINS', 
    'WIRG', 'WMUU', 'WOOD', 'WOWS', 'WTON', 'YELO', 'YPAS', 'YUPI', 'ZATA', 'ZONE', 
    'ZYRX'
]

if btn_scan:
    df_hasil = jalankan_scanner_final(stock_ticker, tgl_input, jam_input)
    
    if not df_hasil.empty:
        st.success(f"Ditemukan {len(df_hasil)} saham!")
        st.dataframe(df_hasil, use_container_width=True)
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria % Last H > 21.26%")
