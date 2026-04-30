import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="Cak To's OI + CVD Lab AI", page_icon="📊", layout="wide")

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

# ====================== SYSTEM PROMPT SUPER ======================
SYSTEM_PROMPT = """
Kamu adalah AI Master Analyst Futures OI + CVD Lab.

**ATURAN INVERSE:**
Bullish di 6J1 = SHORT USD/JPY
Bearish di 6J1 = LONG USD/JPY

Analisa chart dan berikan output JSON:
{
  "setup_id": 1,
  "market_state": "Strong Bullish Trend",
  "logic_match": "...",
  "trading_setup": {
    "signal": "BUY",
    "entry": "0.006380",
    "sl": "0.006320",
    "tp1": "0.006500",
    "tp2": "0.006650",
    "tp3": "0.006850"
  },
  "confidence": 85,
  "checklist_match": "...",
  "risk_note": "...",
  "inverse_note": "REKOMENDASI FOREX: SHORT USD/JPY ...",
  "forex_recommendation": "SHORT USD/JPY"
}
"""

def analyze_chart(image_file, symbol):
    img = Image.open(image_file)
    info = contract_params.get(symbol, {})
    
    inverse_text = ""
    if info.get("inverse"):
        base = info.get("base")
        inverse_text = f"Bullish = SHORT USD/{base} | Bearish = LONG USD/{base}"

    user_prompt = f"Simbol: {symbol} - {info.get('name', symbol)}\n{inverse_text}\nAnalisa profesional."

    contents = [SYSTEM_PROMPT, user_prompt, img]

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config={"response_mime_type": "application/json", "temperature": 0.05, "max_output_tokens": 2048}
    )
    return json.loads(response.text)

# ====================== MAIN APP ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI v4.0")
    st.caption("Cak To Aja • Full Feature + History")

    symbol = st.selectbox("🎯 Pilih Instrumen", options=list(contract_params.keys()),
                         format_func=lambda x: f"{x} — {contract_params[x]['name']}")

    if contract_params[symbol]["inverse"]:
        st.error("⚠️ INVERSE PAIR — Perhatikan Forex Recommendation")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        uploaded_file = st.file_uploader("Upload Screenshot", type=['png', 'jpg', 'jpeg', 'webp'])
        if uploaded_file:
            st.image(uploaded_file, width="stretch")

    with col2:
        st.header("🤖 AI Analysis")
        if uploaded_file and st.button("🚀 Jalankan Analisa", type="primary", use_container_width=True):
            try:
                with st.spinner("AI menganalisa..."):
                    result = analyze_chart(uploaded_file, symbol)

                # Tampilan
                st.success(f"**{result.get('market_state')}**")

                signal = result['trading_setup']['signal']
                emoji = "🟢" if signal == "BUY" else "🔴"
                st.markdown(f"### {emoji} SIGNAL: **{signal}**")

                # Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("ENTRY", result['trading_setup'].get('entry'))
                c2.metric("STOP LOSS", result['trading_setup'].get('sl'))
                
                st.markdown("**Take Profit:**")
                tp_col1, tp_col2, tp_col3 = st.columns(3)
                tp_col1.metric("TP1", result['trading_setup'].get('tp1'))
                tp_col2.metric("TP2", result['trading_setup'].get('tp2'))
                tp_col3.metric("TP3", result['trading_setup'].get('tp3'))

                st.metric("**Confidence**", f"{result.get('confidence', 75)}%")

                st.info(result.get('logic_match'))
                st.caption(result.get('checklist_match'))

                if result.get('risk_note'):
                    st.warning(f"**Risk Note:** {result['risk_note']}")
                if result.get('inverse_note'):
                    st.error(f"**🔄 FOREX NOTE:** {result['inverse_note']}")

                # Save to History
                if 'history' not in st.session_state:
                    st.session_state.history = []
                
                analysis_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "symbol": symbol,
                    "market_state": result.get('market_state'),
                    "signal": signal,
                    "entry": result['trading_setup'].get('entry'),
                    "sl": result['trading_setup'].get('sl'),
                    "tp1": result['trading_setup'].get('tp1'),
                    "confidence": result.get('confidence')
                }
                st.session_state.history.append(analysis_data)

            except Exception as e:
                st.error(f"Error: {e}")

    # ====================== HISTORY ======================
    st.markdown("---")
    st.subheader("📜 Riwayat Analisa")
    if 'history' in st.session_state and st.session_state.history:
        for item in reversed(st.session_state.history[-10:]):  # tampilkan 10 terakhir
            st.markdown(f"""
            **{item['timestamp']}** — **{item['symbol']}** | {item['market_state']}  
            Signal: **{item['signal']}** | Entry: {item['entry']} | SL: {item['sl']} | TP1: {item.get('tp1')} | Confidence: {item['confidence']}%
            """)
            st.divider()
    else:
        st.info("Belum ada riwayat analisa.")

if __name__ == "__main__":
    main()
