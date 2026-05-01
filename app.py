import streamlit as st
from google import genai
from PIL import Image
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="Cak To's OI + CVD Lab AI", page_icon="📊", layout="wide")

# ── API KEY ──
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None
if not API_KEY:
    st.error("❌ GEMINI_API_KEY belum diset! Tambahkan di .env atau Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ====================== CONTRACT PARAMS ======================
# inverseQuote: True  = kontrak sebenarnya BASE/USD (bukan USD/BASE)
#   Price NAIK di chart = mata uang BASE menguat = pasangan forex USD/BASE TURUN
# inverseQuote: False = pair normal, price naik = pair menguat
contract_params = {
    "6E1": {
        "name": "EUR/USD", "pair": "EUR/USD",
        "tickValue": 12.50, "contractSize": 125000,
        "oiSpikePct": 5, "cvdSpikeMult": 1.5, "winRateAdj": 0,
        "tf": "15M-4H", "note": "Likuid tinggi, setup standar",
        "inverseQuote": False,
    },
    "6B1": {
        "name": "GBP/USD", "pair": "GBP/USD",
        "tickValue": 6.25, "contractSize": 62500,
        "oiSpikePct": 6, "cvdSpikeMult": 1.6, "winRateAdj": -2,
        "tf": "15M-4H", "note": "Volatil, spread 1-2 tick",
        "inverseQuote": False,
    },
    "6A1": {
        "name": "AUD/USD", "pair": "AUD/USD",
        "tickValue": 10.00, "contractSize": 100000,
        "oiSpikePct": 5, "cvdSpikeMult": 1.4, "winRateAdj": 0,
        "tf": "30M-4H", "note": "Sensitif komoditas & risk sentiment",
        "inverseQuote": False,
    },
    "6N1": {
        "name": "NZD/USD", "pair": "NZD/USD",
        "tickValue": 10.00, "contractSize": 100000,
        "oiSpikePct": 4, "cvdSpikeMult": 1.3, "winRateAdj": -3,
        "tf": "1H-4H", "note": "Likuiditas tipis, konfirmasi lebih ketat",
        "inverseQuote": False,
    },
    # ⚠️ INVERSE PAIRS
    # 6C1 = kontrak CAD/USD (bukan USD/CAD)
    # 6S1 = kontrak CHF/USD (bukan USD/CHF)
    # 6J1 = kontrak JPY/USD (bukan USD/JPY)
    # Price NAIK = mata uang non-USD menguat = pasangan forex USD/XXX TURUN
    "6C1": {
        "name": "USD/CAD", "pair": "USD/CAD",
        "tickValue": 10.00, "contractSize": 100000,
        "oiSpikePct": 5, "cvdSpikeMult": 1.5, "winRateAdj": -1,
        "tf": "30M-4H", "note": "Korelasi harga minyak",
        "inverseQuote": True, "baseAsli": "CAD", "pairForex": "USD/CAD",
        "descNaik":  "CAD menguat → USD melemah → USD/CAD TURUN",
        "descTurun": "CAD melemah → USD menguat → USD/CAD NAIK",
    },
    "6S1": {
        "name": "USD/CHF", "pair": "USD/CHF",
        "tickValue": 12.50, "contractSize": 125000,
        "oiSpikePct": 4, "cvdSpikeMult": 1.3, "winRateAdj": -2,
        "tf": "1H-4H", "note": "Safe haven pair",
        "inverseQuote": True, "baseAsli": "CHF", "pairForex": "USD/CHF",
        "descNaik":  "CHF menguat → USD melemah → USD/CHF TURUN",
        "descTurun": "CHF melemah → USD menguat → USD/CHF NAIK",
    },
    "6J1": {
        "name": "USD/JPY", "pair": "USD/JPY",
        "tickValue": 12.50, "contractSize": 12500000,
        "oiSpikePct": 6, "cvdSpikeMult": 1.7, "winRateAdj": -1,
        "tf": "1H-4H", "note": "Carry trade sensitive",
        "inverseQuote": True, "baseAsli": "JPY", "pairForex": "USD/JPY",
        "descNaik":  "JPY menguat → USD melemah → USD/JPY TURUN",
        "descTurun": "JPY melemah → USD menguat → USD/JPY NAIK",
    },
    "GC1": {
        "name": "Gold", "pair": "XAU/USD",
        "tickValue": 10.00, "contractSize": 100,
        "oiSpikePct": 7, "cvdSpikeMult": 1.8, "winRateAdj": 2,
        "tf": "1H-Daily", "note": "Volume breakout perlu >150% avg",
        "inverseQuote": False,
    },
    "SI1": {
        "name": "Silver", "pair": "XAG/USD",
        "tickValue": 5.00, "contractSize": 5000,
        "oiSpikePct": 8, "cvdSpikeMult": 2.0, "winRateAdj": -3,
        "tf": "4H-Daily", "note": "CVD smoothing disarankan, likuiditas tipis",
        "inverseQuote": False,
    },
    "CL1": {
        "name": "Crude Oil", "pair": "CL/USD",
        "tickValue": 10.00, "contractSize": 1000,
        "oiSpikePct": 12, "cvdSpikeMult": 2.2, "winRateAdj": 0,
        "tf": "15M-1H", "note": "OI spike >20% saat laporan EIA/API",
        "inverseQuote": False,
    },
}

# Win rate base per setup (sama dengan FINAL.html)
BASE_WIN_RATES = {1:72, 2:68, 3:60, 4:62, 5:70, 6:68, 7:54, 8:52, 9:48, 10:78}

def get_params(symbol):
    p = contract_params.get(symbol, contract_params["6E1"])
    oi = p["oiSpikePct"]
    return {
        "oiSpike":    oi,
        "oiROC":      round(oi * 0.7),  # ROC per bar ~70% dari threshold spike
        "cvdMult":    p["cvdSpikeMult"],
        "oiCover":    oi,               # OI turun = short covering
        "oiExhaust":  oi + 5,           # OI turun dari puncak = exhaustion
        "tf":         p["tf"],
        "note":       p["note"],
    }

def get_win_rate(setup_id, symbol):
    base = BASE_WIN_RATES.get(setup_id, 60)
    adj  = contract_params[symbol].get("winRateAdj", 0)
    return min(85, max(40, base + adj))

# ====================== SYSTEM PROMPT ======================
def build_system_prompt(symbol):
    info   = contract_params.get(symbol, {})
    p      = get_params(symbol)

    # Inverse context yang benar
    if info.get("inverseQuote"):
        base       = info["baseAsli"]
        pair_forex = info["pairForex"]
        inverse_ctx = f"""
⚠️ PAIR INVERSE — BACA DENGAN TELITI:
Kontrak futures {symbol} sebenarnya adalah {base}/USD, bukan USD/{base}.
Artinya:
- Price NAIK di chart  → {info['descNaik']}
  → Setup BULLISH di {symbol} = LONG {base} / SHORT USD = {pair_forex} arah TURUN
- Price TURUN di chart → {info['descTurun']}
  → Setup BEARISH di {symbol} = SHORT {base} / LONG USD = {pair_forex} arah NAIK

PENTING: Tulis forex_recommendation sesuai arah di pasangan forex retail.
Contoh jika bullish: "LONG {base} / {pair_forex} TURUN"
Contoh jika bearish: "SHORT {base} / {pair_forex} NAIK"
"""
    else:
        pair = info.get("pair", symbol)
        inverse_ctx = f"Pair normal. BUY futures = LONG {pair}. SELL futures = SHORT {pair}. Kosongkan inverse_note dan forex_recommendation."

    return f"""
Kamu adalah AI Master Analyst untuk sistem OI + CVD Futures Lab.
Analisa screenshot chart futures dan identifikasi setup yang paling cocok dari 10 setup di bawah.

=== PARAMETER SIMBOL: {symbol} ({info.get('name')}) ===
Tick Value     : ${info.get('tickValue')}
Contract Size  : {info.get('contractSize'):,}
OI Spike min   : +{p['oiSpike']}% (fresh position masuk)
OI ROC per bar : >{p['oiROC']}%
CVD Multiplier : ≥{p['cvdMult']}x rata-rata
OI Cover thresh: turun {p['oiCover']}% = short covering
OI Exhaust     : turun >{p['oiExhaust']}% dari puncak = exhaustion
TF Rekomendasi : {p['tf']}
Catatan        : {p['note']}

=== LOGIKA INVERSE ===
{inverse_ctx}

=== PANDUAN BACA OI + PRICE ===
OI naik + Price naik  = Fresh LONGS masuk (Long Buildup) → Bullish conviction
OI naik + Price turun = Fresh SHORTS masuk (Short Buildup) → Bearish conviction
OI turun + Price naik = SHORT COVERING (Weak Rally) → Tidak ada buyer baru
OI turun + Price turun = LONG LIQUIDATION (Weak Selloff) → Bukan seller baru

=== 10 SETUP TRADING ===

[SETUP 1] Strong Bullish Trend — BULLISH — WR ~{get_win_rate(1,symbol)}%
Kondisi wajib:
- OI naik konsisten 3+ bar berturut (ROC >{p['oiROC']}%/bar)
- CVD slope positif kuat, breakout ≥{p['cvdMult']}x rata-rata
- Price: higher highs & higher lows
- Tidak ada bearish divergence CVD vs price
Entry: Pullback ke EMA + CVD naik lagi | SL: Bawah swing low | Target RR 1:2

[SETUP 2] Strong Bearish Trend — BEARISH — WR ~{get_win_rate(2,symbol)}%
Kondisi wajib:
- OI naik saat price turun = fresh shorts (bukan long liquidation), min +{p['oiSpike']}%
- CVD turun tajam slope negatif ≥{p['cvdMult']}x
- Price: lower lows & lower highs
- Dead cat bounce ke resistance gagal
Entry: Setelah bounce gagal + CVD confirm turun | SL: Atas swing high | Target RR 1:2.5

[SETUP 3] Bullish Divergence Reversal — NEUTRAL/REVERSAL — WR ~{get_win_rate(3,symbol)}%
Kondisi wajib:
- Price lower low TAPI CVD higher low = divergence bullish
- OI mulai naik dari level rendah (+{p['oiROC']}% dalam 5 bar)
- Konfirmasi candle: hammer / bullish engulfing / pin bar
- Area support kuat (multi-test hold)
Entry: Setelah candle bullish konfirmasi | SL: Bawah recent low | Target RR 1:3

[SETUP 4] Bearish Divergence Reversal — NEUTRAL/REVERSAL — WR ~{get_win_rate(4,symbol)}%
Kondisi wajib:
- Price higher high TAPI CVD lower high = divergence bearish
- OI menurun saat price rally (-{p['oiROC']}% dalam 3 bar = longs keluar)
- Resistance kuat terbukti valid
- Volume menurun saat price naik (no conviction)
Entry: Rejection candle di resistance + CVD drop | SL: Atas recent high | Target RR 1:2

[SETUP 5] Valid Breakout Long — BULLISH — WR ~{get_win_rate(5,symbol)}%
Kondisi wajib:
- Price break resistance dengan full-body bullish candle (body >50% dari range)
- OI spike +{p['oiSpike']}% dalam 1-2 bar = fresh longs (BUKAN short covering)
- CVD vertical spike ke atas ≥{p['cvdMult']}x
- Volume breakout >150% avg 20-bar
Entry: Retest resistance jadi support + CVD hold | SL: Bawah breakout level

[SETUP 6] Valid Breakdown Short — BEARISH — WR ~{get_win_rate(6,symbol)}%
Kondisi wajib:
- Price break support dengan full-body bearish candle
- OI spike +{p['oiSpike']}% = fresh shorts (bukan hanya long liquidation)
- CVD waterfall ≥{p['cvdMult']}x selling
- Tidak ada buying absorption (tidak ada long wick besar di bawah)
Entry: Pullback ke broken support jadi resistance | SL: Atas breakdown level

[SETUP 7] Accumulation Phase — BULLISH — WR ~{get_win_rate(7,symbol)}%
Kondisi wajib:
- CVD naik konsisten MESKI price sideways (hidden accumulation)
- OI naik +{p['oiSpike']}% selama konsolidasi (minimal 5-10 periode)
- Support multi-test hold
- Candle lower lows makin kecil (selling pressure berkurang)
Entry: Support zone + CVD spike kecil ke atas | SL: Bawah range low

[SETUP 8] Distribution Phase — BEARISH — WR ~{get_win_rate(8,symbol)}%
Kondisi wajib:
- CVD turun konsisten MESKI price sideways (hidden selling)
- OI naik +{p['oiSpike']}% tapi price gagal breakout resistance berulang
- Resistance multi-test rejection (2-3x ditolak)
- Higher highs makin lemah
Entry: Rejection candle resistance + CVD drop | SL: Atas range high

[SETUP 9] Weak Rally / Short Covering — BEARISH RISIKO TINGGI — WR ~{get_win_rate(9,symbol)}%
Kondisi wajib:
- Price naik TAPI OI TURUN ({p['oiCover']}% drop) = short covering, bukan fresh longs
- CVD flat atau turun saat price naik
- Rally menuju resistance atau Fibonacci retracement
- Volume menurun selama rally
Entry: Short di resistance dengan rejection konfirmasi | SL: Ketat +0.5% atas resistance
⚠️ SETUP BERISIKO TINGGI — rentan short squeeze

[SETUP 10] Trend Exhaustion — EXIT SIGNAL — Akurasi ~{get_win_rate(10,symbol)}%
Kondisi:
- OI drop >{p['oiExhaust']}% dari puncak = long liquidation massal
- CVD divergence: price masih naik tapi CVD flat/turun = buyers habis
- Volatilitas menurun, candle mengecil
- Volume spike tanpa follow-through (distribusi di top)
⚠️ INI BUKAN SETUP ENTRY. Signal = EXIT atau KURANGI posisi yang ada.
Tulis signal: "NO_ENTRY"

=== FORMAT OUTPUT JSON ===
Kembalikan HANYA JSON valid berikut, tanpa teks tambahan:
{{
  "setup_id": <angka 1-10>,
  "market_state": "<nama setup>",
  "setup_type": "<BULLISH|BEARISH|NEUTRAL|EXIT>",
  "logic_match": "<jelaskan OI/CVD/Price yang terlihat di chart dan kenapa cocok dengan setup ini>",
  "checklist_match": "<sebutkan kondisi mana saja yang terpenuhi>",
  "trading_setup": {{
    "signal": "<BUY|SELL|NO_ENTRY>",
    "entry": "<harga entry dalam satuan futures>",
    "sl": "<harga stop loss>",
    "tp1": "<harga TP1>",
    "tp2": "<harga TP2>",
    "tp3": "<harga TP3>"
  }},
  "confidence": <angka 40-95>,
  "risk_note": "<kondisi invalidasi dan risiko utama>",
  "inverse_note": "<isi jika inverseQuote=true, kosongkan jika tidak>",
  "forex_recommendation": "<isi jika inverseQuote=true contoh: LONG JPY / USD/JPY TURUN, kosongkan jika tidak>"
}}
"""

# ====================== ANALYZE ======================
def analyze_chart(image_file, symbol):
    img    = Image.open(image_file)
    prompt = build_system_prompt(symbol)
    info   = contract_params.get(symbol, {})

    user_msg = (
        f"Analisa chart ini untuk {symbol} ({info.get('name')}, {info.get('pair')}).\n"
        f"Identifikasi setup OI+CVD yang paling cocok dan kembalikan JSON."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-04-17",
        contents=[prompt, user_msg, img],
        config={
            "response_mime_type": "application/json",
            "temperature": 0.05,
            "max_output_tokens": 2048,
        }
    )

    raw = response.text.strip()
    # Bersihkan markdown fence jika ada
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

# ====================== MAIN APP ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI")
    st.caption("Cak To Aja • Powered by Gemini • Full Setup Logic")

    # ── Sidebar: pilih simbol + info params ──
    with st.sidebar:
        st.header("⚙️ Instrumen")
        symbol = st.selectbox(
            "🎯 Pilih Simbol",
            options=list(contract_params.keys()),
            format_func=lambda x: f"{x} — {contract_params[x]['name']}"
        )
        info = contract_params[symbol]
        p    = get_params(symbol)

        st.markdown("---")
        st.markdown("**📋 Parameter Aktif:**")
        st.markdown(f"- OI Spike min: **+{p['oiSpike']}%**")
        st.markdown(f"- OI ROC/bar: **>{p['oiROC']}%**")
        st.markdown(f"- CVD Multiplier: **≥{p['cvdMult']}×**")
        st.markdown(f"- OI Exhaust: **>{p['oiExhaust']}% dari puncak**")
        st.markdown(f"- TF Rekomendasi: **{p['tf']}**")
        st.caption(p["note"])

        if info.get("inverseQuote"):
            st.markdown("---")
            st.warning(
                f"⚠️ **INVERSE PAIR**\n\n"
                f"Kontrak ini adalah **{info['baseAsli']}/USD**\n\n"
                f"📈 Price naik → {info['descNaik']}\n\n"
                f"📉 Price turun → {info['descTurun']}"
            )

    # ── Banner inverse di main area ──
    if info.get("inverseQuote"):
        st.error(
            f"⚠️ **INVERSE PAIR** — {symbol} adalah kontrak {info['baseAsli']}/USD. "
            f"Price NAIK = **{info['baseAsli']} menguat** = **{info['pairForex']} TURUN**."
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Chart")
        st.caption("Screenshot TradingView — OI + CVD + Price harus terlihat semua")
        uploaded_file = st.file_uploader(
            "Upload Screenshot", type=["png", "jpg", "jpeg", "webp"]
        )
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)

    with col2:
        st.header("🤖 AI Analysis")
        if uploaded_file:
            if st.button("🚀 Jalankan Analisa OI-CVD", type="primary", use_container_width=True):
                try:
                    with st.spinner("AI menganalisa OI + CVD + Price..."):
                        result = analyze_chart(uploaded_file, symbol)

                    setup_type = result.get("setup_type", "")
                    signal     = result["trading_setup"]["signal"]
                    setup_id   = result.get("setup_id", 0)

                    # ── Header result ──
                    if setup_type == "BULLISH":
                        st.success(f"📈 **{result.get('market_state')}** (Setup #{setup_id})")
                    elif setup_type == "BEARISH":
                        st.error(f"📉 **{result.get('market_state')}** (Setup #{setup_id})")
                    elif setup_type == "EXIT":
                        st.warning(f"🚪 **{result.get('market_state')}** — EXIT SIGNAL, jangan entry baru!")
                    else:
                        st.info(f"🔄 **{result.get('market_state')}** (Setup #{setup_id})")

                    # ── Signal ──
                    st.markdown("---")
                    if signal == "NO_ENTRY":
                        st.warning("⛔ **NO ENTRY** — Kurangi/close posisi yang ada, tunggu setup berikutnya.")
                    else:
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        st.markdown(f"### {emoji} Futures Signal: **{signal} {symbol}**")
                        if result.get("forex_recommendation"):
                            st.markdown(f"### 🔄 Forex Equivalent: **{result['forex_recommendation']}**")

                    # ── Entry / SL ──
                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    c1.metric("📍 ENTRY",     result["trading_setup"].get("entry", "-"))
                    c2.metric("🛑 STOP LOSS", result["trading_setup"].get("sl",    "-"))

                    st.markdown("**🎯 Take Profit:**")
                    tp1, tp2, tp3 = st.columns(3)
                    tp1.metric("TP1", result["trading_setup"].get("tp1", "-"))
                    tp2.metric("TP2", result["trading_setup"].get("tp2", "-"))
                    tp3.metric("TP3", result["trading_setup"].get("tp3", "-"))

                    # ── Confidence ──
                    st.markdown("---")
                    confidence = result.get("confidence", 75)
                    st.metric("🎯 Confidence AI", f"{confidence}%")
                    st.progress(confidence / 100)

                    # Win rate referensi dari sistem
                    if setup_id in BASE_WIN_RATES:
                        wr    = get_win_rate(setup_id, symbol)
                        label = "Akurasi sinyal exit" if setup_id == 10 else "Win Rate referensi sistem"
                        st.caption(f"📊 {label} Setup #{setup_id} untuk {symbol}: **{wr}%**")

                    # ── Logic & Checklist ──
                    st.markdown("---")
                    st.markdown("**📊 Analisa AI:**")
                    st.info(result.get("logic_match", "-"))
                    st.caption(f"✅ Checklist terpenuhi: {result.get('checklist_match', '-')}")

                    # ── Risk Note ──
                    if result.get("risk_note"):
                        st.warning(f"⚠️ **Risk / Invalidation:** {result['risk_note']}")

                    # ── Inverse Note ──
                    if result.get("inverse_note"):
                        st.error(f"🔄 **INVERSE NOTE:** {result['inverse_note']}")

                    # ── Simpan history ──
                    if "history" not in st.session_state:
                        st.session_state.history = []
                    st.session_state.history.append({
                        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "symbol":       symbol,
                        "setup_id":     setup_id,
                        "market_state": result.get("market_state"),
                        "signal":       signal,
                        "entry":        result["trading_setup"].get("entry", "-"),
                        "sl":           result["trading_setup"].get("sl",    "-"),
                        "tp1":          result["trading_setup"].get("tp1",   "-"),
                        "confidence":   confidence,
                        "forex_rec":    result.get("forex_recommendation", ""),
                    })

                except json.JSONDecodeError as e:
                    st.error(f"❌ AI tidak mengembalikan JSON valid: {e}")
                    st.code(response.text if 'response' in dir() else "Tidak ada response")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        else:
            st.info("👆 Upload screenshot chart terlebih dahulu.\nPastikan panel OI + CVD + Price terlihat semua.")

    # ====================== HISTORY ======================
    st.markdown("---")
    st.subheader("📜 Riwayat Analisa")

    if "history" in st.session_state and st.session_state.history:
        col_clr, _ = st.columns([1, 4])
        if col_clr.button("🗑️ Hapus Riwayat"):
            st.session_state.history = []
            st.rerun()

        for item in reversed(st.session_state.history[-10:]):
            sig_emoji = "🟢" if item["signal"] == "BUY" else ("🔴" if item["signal"] == "SELL" else "⛔")
            forex_str = f" | 🔄 **{item['forex_rec']}**" if item.get("forex_rec") else ""
            st.markdown(
                f"**{item['timestamp']}** — **{item['symbol']}** | "
                f"Setup #{item.get('setup_id')} {item['market_state']}  \n"
                f"{sig_emoji} **{item['signal']}** | "
                f"Entry: `{item['entry']}` | SL: `{item['sl']}` | "
                f"TP1: `{item.get('tp1')}` | Confidence: **{item['confidence']}%**{forex_str}"
            )
            st.divider()
    else:
        st.info("Belum ada riwayat analisa.")


if __name__ == "__main__":
    main()
