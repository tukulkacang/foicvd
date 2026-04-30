import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv

# 1. SETUP KONFIGURASI 2026
load_dotenv()
st.set_page_config(
    page_title="Cak To's Order Flow AI v3", 
    page_icon="🎯", 
    layout="wide"
)

# Ambil API Key dari Secrets
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("API Key belum diset di Secrets!")
    st.stop()

# Inisialisasi Client Baru (SDK 2026)
client = genai.Client(api_key=API_KEY)

# 2. SYSTEM PROMPT (Logika Tetap Sesuai tukulkacang.github.io)
SYSTEM_PROMPT = """
Kamu adalah AI Pakar Analisis Order Flow (Gemini 3 Flash). 
Analisa screenshot TradingView berdasarkan parameter 'Futures OI-CVD Lab':

LOGIKA UTAMA:
- Long Build Up: Harga Naik + OI Naik (Tangga Hijau).
- Short Build Up: Harga Turun + OI Naik (Tangga Hijau).
- Long Unwinding: Harga Turun + OI Turun (Tangga Merah).
- Short Covering: Harga Naik + OI Turun (Tangga Merah).
- Absorption: CVD ekstrim tapi harga stagnan/berlawanan.

TUGAS: Berikan estimasi Entry, SL, dan TP berdasarkan angka di sumbu kanan chart.

OUTPUT FORMAT (Wajib JSON):
{
  "market_state": "...",
  "logic_match": "...",
  "trading_setup": {
    "signal": "BUY/SELL/WAIT",
    "entry": "...",
    "sl": "...",
    "tp": "..."
  },
  "risk_note": "..."
}
"""

# 3. FUNGSI ANALISA (Migrasi ke Gemini 3 Flash)
def analyze_chart(image_file):
    img = Image.open(image_file)
    
    # Menggunakan model gemini-3-flash yang lebih baru dan akurat
    response = client.models.generate_content(
        model="gemini-3-flash-001",
        contents=[SYSTEM_PROMPT, img],
        config={
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    )
    return json.loads(response.text)

# 4. UI STREAMLIT (Fix Deprecated use_container_width)
def main():
    st.title("🎯 AI Order Flow Analyst v3")
    st.caption("Cak To Aja - 2026 Edition") # Identitas user
    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        uploaded_file = st.file_uploader("Upload screenshot TradingView", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            # Update 2026: use_container_width diganti width='stretch'
            st.image(uploaded_file, caption="Chart Original", width='stretch')

    with col2:
        st.header("🤖 Gemini 3 Analysis")
        if uploaded_file:
            if st.button("Jalankan Analisa 10/10", type="primary"):
                try:
                    with st.spinner("Memproses dengan Gemini 3 Flash..."):
                        result = analyze_chart(uploaded_file)
                    
                    st.success(f"**STATUS: {result['market_state']}**")
                    
                    st.markdown("### ⚡ SIGNAL: " + result['trading_setup']['signal'])
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", result['trading_setup']['entry'])
                    c2.metric("STOP LOSS", result['trading_setup']['sl'])
                    c3.metric("TAKE PROFIT", result['trading_setup']['tp'])

                    st.info(f"**Risk Note:** {result['risk_note']}")

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Silakan upload chart dulu, bro.")

if __name__ == "__main__":
    main()
