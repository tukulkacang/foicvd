import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import json
from dotenv import load_dotenv

# 1. SETUP KONFIGURASI
load_dotenv()
st.set_page_config(
    page_title="Cak To's Order Flow AI", 
    page_icon="🎯", 
    layout="wide"
)

import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import json

# ==========================================
# PERBAIKAN LOGIKA PEMANGGILAN KEY (NILAI 10/10)
# ==========================================

# 1. Cek di Secrets Streamlit (Untuk Online)
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
# 2. Cek di Environment Variable (Untuk Lokal)
elif os.getenv("GEMINI_API_KEY"):
    API_KEY = os.getenv("GEMINI_API_KEY")
else:
    API_KEY = None

# Jika Key tidak ditemukan, tampilkan instruksi alih-alih error mentah
if not API_KEY:
    st.warning("⚠️ API Key tidak terdeteksi di Secrets Streamlit.")
    st.info("Pastikan di Dashboard Streamlit > Settings > Secrets, kamu sudah tulis: GEMINI_API_KEY = 'KUNCI_KAMU'")
    st.stop()

genai.configure(api_key=API_KEY)

# 2. SYSTEM PROMPT (Logika Persis tukulkacang.github.io)
SYSTEM_PROMPT = """
Kamu adalah AI Pakar Analisis Order Flow yang mengacu pada metodologi 'Futures OI-CVD Lab'. 
Tugasmu adalah membedah screenshot TradingView berdasarkan 3 indikator utama:

ATURAN PARAMETER (WAJIB):
1. Long Build Up: Harga Naik + Open Interest (OI) Naik (Tangga Hijau). Sinyal: Bullish/Buy.
2. Short Build Up: Harga Turun + Open Interest (OI) Naik (Tangga Hijau). Sinyal: Bearish/Sell.
3. Long Unwinding: Harga Turun + OI Menurun (Tangga Merah). Sinyal: Longs Closing/Bearish Reversal.
4. Short Covering: Harga Naik + OI Menurun (Tangga Merah). Sinyal: Shorts Closing/Short Squeeze.
5. Absorption: CVD bergerak agresif (ekstrim) tapi harga bergerak berlawanan atau stagnan.
6. Exhaustion: Harga mencapai high/low baru tapi OI dan CVD tidak mendukung (divergence).

TUGAS TAMBAHAN:
- Baca angka harga di sumbu kanan chart untuk menentukan level teknikal.
- Berikan rekomendasi Entry, SL, dan TP berdasarkan struktur candlestick terbaru.

OUTPUT FORMAT (JSON):
{
  "market_state": "...",
  "logic_match": "Penjelasan kenapa kondisi ini sesuai dengan parameter OI-CVD Lab",
  "checklist": {
    "price_action": "Naik/Turun/Side",
    "oi_status": "Rising/Falling",
    "cvd_status": "Aggressive/Passive"
  },
  "trading_setup": {
    "signal": "BUY/SELL/WAIT",
    "entry": "Angka estimasi harga",
    "sl": "Angka stop loss",
    "tp": "Angka take profit"
  },
  "risk_note": "Catatan khusus tentang penyerapan (absorption) atau squeeze"
}
"""

# 3. FUNGSI ANALISA
def analyze_chart(image_file):
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "temperature": 0.1, # Sangat rendah agar patuh pada aturan
            "response_mime_type": "application/json",
        }
    )
    
    img = Image.open(image_file)
    response = model.generate_content([SYSTEM_PROMPT, img])
    return json.loads(response.text)

# 4. UI STREAMLIT
def main():
    st.title("🎯 AI Order Flow Analyst")
    st.caption("Based on Futures OI-CVD Lab Methodology")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        uploaded_file = st.file_uploader("Upload screenshot dari TradingView (Pastikan OI & CVD terlihat)", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            st.image(uploaded_file, caption="Chart Original", use_container_width=True)

    with col2:
        st.header("🤖 AI Recommendation")
        if uploaded_file:
            if st.button("Jalankan Analisa 10/10", type="primary"):
                try:
                    with st.spinner("Mencocokkan parameter OI-CVD..."):
                        result = analyze_chart(uploaded_file)
                    
                    # Status Box
                    st.success(f"**STATUS: {result['market_state']}**")
                    st.write(f"_{result['logic_match']}_")
                    
                    # Checklist
                    st.markdown("### 📋 Parameter Check")
                    st.json(result['checklist'])

                    # SIGNAL BOX (ENTRY, SL, TP)
                    st.markdown("---")
                    setup = result['trading_setup']
                    color = "green" if "BUY" in setup['signal'] else "red" if "SELL" in setup['signal'] else "orange"
                    
                    st.markdown(f"### ⚡ SIGNAL: :{color}[{setup['signal']}]")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", setup['entry'])
                    c2.metric("STOP LOSS", setup['sl'], delta_color="inverse")
                    c3.metric("TAKE PROFIT", setup['tp'])

                    st.info(f"**Risk Note:** {result['risk_note']}")

                except Exception as e:
                    st.error(f"Gagal membedah gambar. Pastikan label OI dan CVD terbaca jelas.")
                    st.write(e)
        else:
            st.info("Upload chart-mu dulu bro untuk melihat keajaiban.")

if __name__ == "__main__":
    main()
