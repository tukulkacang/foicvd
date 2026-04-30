import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Cak To's OI + CVD Lab AI", page_icon="📊", layout="wide")

API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key belum diset!")
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

# ====================== SYSTEM PROMPT (Inverse Diperkuat) ======================
SYSTEM_PROMPT = """
Kamu adalah AI Master Analyst Futures OI + CVD Lab sesuai tukulkacang.github.io.

**ATURAN INVERSE SANGAT PENTING:**
- Untuk simbol **6C1 (USD/CAD)**, **6S1 (USD/CHF)**, **6J1 (USD/JPY)** → ini adalah kontrak INVERSE.
- Price naik di chart = mata uang base (CAD/CHF/JPY) menguat → artinya USD melemah.
- Price turun di chart = mata uang base melemah → USD menguat.

**Contoh:**
- Chart 6J1 price naik + OI naik + CVD positif → ini **Bullish untuk JPY** (LONG JPY / SHORT USD)
- Chart 6J1 price turun + OI naik + CVD negatif → ini **Bearish untuk JPY** (SHORT JPY / LONG USD)

Analisa chart dan pilih salah satu dari 10 setup berikut:

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

**Output WAJIB JSON:**
{
  "setup_id": 1,
  "market_state": "Strong Bullish Trend",
  "logic_match": "...",
  "trading_setup": {
    "signal": "BUY",
    "entry": "...",
    "sl": "...",
    "tp": "..."
  },
  "checklist_match": "...",
  "risk_note": "...",
  "inverse_note": "Jelaskan implikasi untuk trader yang trading pair forex asli (contoh: LONG JPY / SHORT USD)"
}
"""

def analyze_chart(image_file, symbol):
    img = Image.open(image_file)
    
    info = contract_params.get(symbol, {})
    inverse_info = ""
    if info.get("inverse"):
        base = info.get("base")
        inverse_info = f"""
Simbol ini INVERSE ({symbol} - {info['name']}).
Price naik = {base} menguat = USD melemah.
Price turun = {base} melemah = USD menguat.
"""
    
    prompt_text = f"""
Simbol: {symbol} - {info.get('name', symbol)}
{inverse_info}
Analisa chart ini sesuai framework OI+CVD Lab.
"""

    contents = [SYSTEM_PROMPT, prompt_text, img]
    
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

# ====================== UI ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI")
    st.caption("Cak To Aja • Inverse Handling Improved")

    symbol = st.selectbox(
        "🎯 Pilih Instrumen",
        options=list(contract_params.keys()),
        format_func=lambda x: f"{x} — {contract_params[x]['name']}"
    )

    if contract_params[symbol]["inverse"]:
        st.error("⚠️ INVERSE PAIR — Perhatikan penjelasan inverse_note dari AI")

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
            if st.button("🚀 Jalankan Analisa", type="primary", use_container_width=True):
                try:
                    with st.spinner("Menganalisa..."):
                        result = analyze_chart(uploaded_file, symbol)

                    st.success(f"**{result.get('market_state')}**")

                    signal = result['trading_setup']['signal']
                    color = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
                    st.markdown(f"### {color} SIGNAL: **{signal}**")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRY", result['trading_setup'].get('entry'))
                    c2.metric("SL", result['trading_setup'].get('sl'))
                    c3.metric("TP", result['trading_setup'].get('tp'))

                    st.info(result.get('logic_match', ''))
                    st.write("**Checklist:**", result.get('checklist_match', ''))

                    if result.get('risk_note'):
                        st.warning(f"**Risk Note:** {result['risk_note']}")
                    
                    if result.get('inverse_note'):
                        st.error(f"**🔄 INVERSE NOTE:** {result['inverse_note']}")

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Upload chart dulu bro")

if __name__ == "__main__":
    main()
