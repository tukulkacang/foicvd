import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Cak To's OI + CVD Lab AI",
    page_icon="📊",
    layout="wide"
)

# ====================== API SETUP ======================
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ GEMINI_API_KEY belum diset di .env atau Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ====================== CONTRACT PARAMS ======================
contract_params = {
    "6E1": {"name": "EUR/USD", "inverse": False},
    "6B1": {"name": "GBP/USD", "inverse": False},
    "6A1": {"name": "AUD/USD", "inverse": False},
    "6N1": {"name": "NZD/USD", "inverse": False},
    "6C1": {"name": "USD/CAD", "inverse": True, "base": "CAD"},
    "6S1": {"name": "USD/CHF", "inverse": True, "base": "CHF"},
    "6J1": {"name": "USD/JPY", "inverse": True, "base": "JPY"},
    "GC1": {"name": "Gold", "inverse": False},
    "SI1": {"name": "Silver", "inverse": False},
    "CL1": {"name": "Crude Oil", "inverse": False},
}

# ====================== SYSTEM PROMPT TERBAIK ======================
SYSTEM_PROMPT = """
Kamu adalah AI Master Analyst Futures OI + CVD Lab sesuai framework tukulkacang.github.io.

**ATURAN INVERSE (WAJIB):**
Simbol 6C1, 6S1, 6J1 adalah kontrak INVERSE.
- Price naik + setup bullish = mata uang base (CAD/CHF/JPY) menguat → SHORT USD
- Price turun + setup bearish = mata uang base melemah → LONG USD

Analisa screenshot TradingView dengan teliti, lalu tentukan setup yang paling cocok dari 10 setup berikut:

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

**Output HARUS JSON yang valid dan lengkap:**
{
  "setup_id": 1,
  "market_state": "Strong Bullish Trend",
  "logic_match": "Penjelasan singkat dan jelas",
  "trading_setup": {
    "signal": "BUY",
    "entry": "0.006380",
    "sl": "0.006320",
    "tp": "0.006500"
  },
  "checklist_match": "4 dari 5 kondisi terpenuhi",
  "risk_note": "Catatan risiko dan invalidasi",
  "inverse_note": "Penjelasan implikasi untuk trader Forex (contoh: SHORT USD/JPY)"
}
"""

def analyze_chart(image_file, symbol):
    img = Image.open(image_file)
    info = contract_params.get(symbol, {})
    
    inverse_text = ""
    if info.get("inverse"):
        base = info.get("base")
        inverse_text = f"""
Simbol {symbol} adalah INVERSE pair.
Price naik = {base} menguat vs USD.
Price turun = {base} melemah vs USD.
"""

    user_prompt = f"""
Simbol: {symbol} - {info.get('name', symbol)}
{inverse_text}
Analisa chart ini secara profesional sesuai OI + CVD Lab.
"""

    contents = [SYSTEM_PROMPT, user_prompt, img]

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.05,        # lebih konsisten
            "max_output_tokens": 2048,
        }
    )
    return json.loads(response.text)


# ====================== UI ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI v3")
    st.caption("Cak To Aja • Versi Terbaik • Inverse Optimized")

    symbol = st.selectbox(
        "🎯 Pilih Instrumen",
        options=list(contract_params.keys()),
        format_func=lambda x: f"{x} — {contract_params[x]['name']}"
    )

    if contract_params[symbol]["inverse"]:
        st.error("⚠️ INVERSE PAIR — Perhatikan baik-baik Inverse Note dari AI")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        uploaded_file = st.file_uploader("Upload Screenshot TradingView", 
                                       type=['png', 'jpg', 'jpeg', 'webp'])
        if uploaded_file:
            st.image(uploaded_file, caption="Chart Original", width="stretch")

    with col2:
        st.header("🤖 AI Analysis")
        if uploaded_file:
            if st.button("🚀 Jalankan Analisa OI-CVD", type="primary", use_container_width=True):
                try:
                    with st.spinner("AI sedang menganalisa chart..."):
                        result = analyze_chart(uploaded_file, symbol)

                    # Hasil
                    st.success(f"**{result.get('market_state', 'Analysis Complete')}**")

                    signal = result['trading_setup']['signal']
                    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
                    st.markdown(f"### {emoji} SIGNAL: **{signal}**")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", result['trading_setup'].get('entry', '-'))
                    c2.metric("STOP LOSS", result['trading_setup'].get('sl', '-'))
                    c3.metric("TAKE PROFIT", result['trading_setup'].get('tp', '-'))

                    st.info(f"**Logic:** {result.get('logic_match', '')}")
                    st.caption(f"**Checklist:** {result.get('checklist_match', '')}")

                    if result.get('risk_note'):
                        st.warning(f"**Risk Note:** {result['risk_note']}")
                    
                    if result.get('inverse_note'):
                        st.error(f"**🔄 INVERSE NOTE:** {result['inverse_note']}")

                except Exception as e:
                    st.error(f"Terjadi kesalahan: {str(e)}")
        else:
            st.info("⬆️ Silakan upload screenshot chart terlebih dahulu")

    st.markdown("---")
    st.caption("Versi terbaik • Prompt + Inverse Handling telah dioptimasi")

if __name__ == "__main__":
    main()
