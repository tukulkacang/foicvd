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
    st.error("❌ GEMINI_API_KEY belum diset!")
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

# ====================== SYSTEM PROMPT FINAL (Paling Ketat) ======================
SYSTEM_PROMPT = """
Kamu adalah AI Master Analyst Futures OI + CVD Lab sesuai tukulkacang.github.io.

**ATURAN INVERSE WAJIB (JANGAN SAMPAI SALAH):**
- Simbol 6J1, 6C1, 6S1 adalah kontrak INVERSE.
- Bullish setup (harga naik + OI naik + CVD positif) = mata uang base menguat → **REKOMENDASI FOREX: SHORT USD**
- Bearish setup = mata uang base melemah → **REKOMENDASI FOREX: LONG USD**

**Khusus 6J1 (Japanese Yen):**
- Strong Bullish / Long Build Up → **REKOMENDASI: SHORT USD/JPY**
- Strong Bearish / Short Build Up → **REKOMENDASI: LONG USD/JPY**

Selalu berikan rekomendasi Forex yang tegas dan jelas.

Analisa chart dan pilih salah satu dari 10 setup.

**Output JSON:**
{
  "setup_id": 1,
  "market_state": "Strong Bullish Trend",
  "logic_match": "...",
  "trading_setup": {
    "signal": "BUY",
    "entry": "0.006380",
    "sl": "0.006320",
    "tp": "0.006550"
  },
  "checklist_match": "...",
  "risk_note": "...",
  "inverse_note": "REKOMENDASI FOREX: SHORT USD/JPY karena JPY menguat kuat",
  "forex_recommendation": "SHORT USD/JPY"
}
"""

def analyze_chart(image_file, symbol):
    img = Image.open(image_file)
    info = contract_params.get(symbol, {})
    
    inverse_text = ""
    if info.get("inverse"):
        base = info.get("base")
        inverse_text = f"""
Simbol ini INVERSE ({symbol}).
Bullish = {base} menguat vs USD → Rekomendasi SHORT USD/{base}
"""

    user_prompt = f"""
Simbol: {symbol} - {info.get('name', symbol)}
{inverse_text}
Berikan analisa lengkap dan rekomendasi Forex yang sangat jelas.
"""

    contents = [SYSTEM_PROMPT, user_prompt, img]

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.05,
            "max_output_tokens": 2048,
        }
    )
    return json.loads(response.text)


# ====================== UI ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI v3.1")
    st.caption("Cak To Aja • Inverse + Forex Recommendation Optimized")

    symbol = st.selectbox(
        "🎯 Pilih Instrumen",
        options=list(contract_params.keys()),
        format_func=lambda x: f"{x} — {contract_params[x]['name']}"
    )

    if contract_params[symbol]["inverse"]:
        st.error("⚠️ INVERSE PAIR — Perhatikan Inverse Note & Forex Recommendation")

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
                    with st.spinner("AI sedang menganalisa..."):
                        result = analyze_chart(uploaded_file, symbol)

                    st.success(f"**{result.get('market_state')}**")

                    signal = result['trading_setup']['signal']
                    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
                    st.markdown(f"### {emoji} SIGNAL (Futures): **{signal}**")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", result['trading_setup'].get('entry'))
                    c2.metric("STOP LOSS", result['trading_setup'].get('sl'))
                    c3.metric("TAKE PROFIT", result['trading_setup'].get('tp'))

                    st.info(result.get('logic_match', ''))
                    st.caption(result.get('checklist_match', ''))

                    if result.get('risk_note'):
                        st.warning(f"**Risk Note:** {result['risk_note']}")
                    
                    if result.get('inverse_note'):
                        st.error(f"**🔄 INVERSE & FOREX NOTE:** {result['inverse_note']}")

                    if result.get('forex_recommendation'):
                        st.success(f"**Rekomendasi Forex:** {result['forex_recommendation']}")

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Upload chart dulu bro")

if __name__ == "__main__":
    main()
