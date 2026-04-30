import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv

# ====================== SETUP ======================
load_dotenv()

st.set_page_config(
    page_title="Cak To's OI + CVD Lab AI",
    page_icon="📊",
    layout="wide"
)

# Ambil API Key
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key Gemini belum diset di .env atau Secrets!")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ====================== CONTRACT PARAMS ======================
contract_params = {
    "6E1": {"name": "EUR/USD", "inverse": False},
    "6B1": {"name": "GBP/USD", "inverse": False},
    "6A1": {"name": "AUD/USD", "inverse": False},
    "6N1": {"name": "NZD/USD", "inverse": False},
    "6C1": {"name": "USD/CAD", "inverse": True},
    "6S1": {"name": "USD/CHF", "inverse": True},
    "6J1": {"name": "USD/JPY", "inverse": True},
    "GC1": {"name": "Gold", "inverse": False},
    "SI1": {"name": "Silver", "inverse": False},
    "CL1": {"name": "Crude Oil", "inverse": False},
}

# ====================== SYSTEM PROMPT ======================
SYSTEM_PROMPT = """
Kamu adalah AI Master Analyst Futures OI + CVD Lab yang mengikuti persis framework dari https://tukulkacang.github.io/futures-oi-cvd-lab/

Analisa screenshot TradingView dengan teliti, lalu tentukan setup yang paling cocok dari 10 setup berikut:

### 10 SETUP UTAMA:
1. Strong Bullish Trend (Long Build Up)
2. Strong Bearish Trend (Short Build Up)
3. Bullish Divergence Reversal
4. Bearish Divergence Reversal
5. Valid Breakout Long
6. Valid Breakdown Short
7. Accumulation Phase (Long)
8. Distribution Phase (Short)
9. Weak Rally / Short Covering
10. Trend Exhaustion (Exit Signal)

### LOGIKA ANALISA WAJIB:
- Long Build Up: Harga ↑ + OI ↑ (fresh longs)
- Short Build Up: Harga ↓ + OI ↑ (fresh shorts)
- Long Unwinding: Harga ↓ + OI ↓
- Short Covering: Harga ↑ + OI ↓
- Perhatikan kekuatan CVD

Tugasmu:
- Pilih satu setup yang paling matching
- Berikan Entry, SL, TP berdasarkan level harga di chart
- Signal hanya: BUY / SELL / WAIT

**Output WAJIB JSON:**
{
  "setup_id": 1,
  "market_state": "Strong Bullish Trend",
  "logic_match": "Penjelasan singkat kenapa cocok",
  "trading_setup": {
    "signal": "BUY",
    "entry": "1.0850",
    "sl": "1.0815",
    "tp": "1.0940"
  },
  "checklist_match": "4/5 kondisi terpenuhi",
  "risk_note": "Catatan risiko",
  "inverse_note": "Penjelasan jika inverse"
}
"""

# ====================== FUNGSI ANALISA (FIXED) ======================
def analyze_chart(image_file, symbol):
    img = Image.open(image_file)
    
    prompt_text = f"""
Simbol: {symbol} - {contract_params.get(symbol, {}).get('name', symbol)}
Analisa chart ini sesuai 10 setup OI+CVD Lab di atas.
"""

    # Format yang benar untuk SDK terbaru
    contents = [
        SYSTEM_PROMPT,
        prompt_text,
        img
    ]
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
            "max_output_tokens": 2000,
        }
    )
    return json.loads(response.text)

# ====================== MAIN UI ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI")
    st.caption("Cak To Aja - Versi AI • Mengikuti tukulkacang.github.io")

    symbol = st.selectbox(
        "🎯 Pilih Instrumen",
        options=list(contract_params.keys()),
        format_func=lambda x: f"{x} — {contract_params[x]['name']}"
    )

    if contract_params[symbol]["inverse"]:
        st.warning("⚠️ **INVERSE Pair** - Price naik di chart = mata uang base menguat")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        uploaded_file = st.file_uploader("Upload Screenshot TradingView", 
                                       type=['png', 'jpg', 'jpeg', 'webp'])

        if uploaded_file:
            st.image(uploaded_file, caption="Chart yang diupload", width="stretch")

    with col2:
        st.header("🤖 AI Analysis Result")
        if uploaded_file:
            if st.button("🚀 Jalankan Analisa OI-CVD", type="primary", use_container_width=True):
                try:
                    with st.spinner("AI sedang menganalisa chart..."):
                        result = analyze_chart(uploaded_file, symbol)

                    st.success(f"**{result.get('market_state', 'Analysis Complete')}**")

                    signal = result['trading_setup']['signal']
                    if signal == "BUY":
                        st.markdown(f"### 🟢 **SIGNAL: BUY**")
                    elif signal == "SELL":
                        st.markdown(f"### 🔴 **SIGNAL: SELL**")
                    else:
                        st.markdown(f"### ⚪ **SIGNAL: WAIT**")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", result['trading_setup'].get('entry', '-'))
                    c2.metric("STOP LOSS", result['trading_setup'].get('sl', '-'))
                    c3.metric("TAKE PROFIT", result['trading_setup'].get('tp', '-'))

                    st.info(f"**Logic:** {result.get('logic_match', '')}")
                    st.write(f"**Checklist:** {result.get('checklist_match', '')}")

                    if result.get('risk_note'):
                        st.warning(f"**Risk Note:** {result['risk_note']}")
                    if result.get('inverse_note'):
                        st.error(f"**Inverse Note:** {result['inverse_note']}")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.info("⬆️ Upload screenshot chart terlebih dahulu")

    st.markdown("---")
    st.caption("AI ini dirancang mengikuti 10 setup resmi Futures OI + CVD Lab")

if __name__ == "__main__":
    main()
