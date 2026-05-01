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
    st.error("❌ GEMINI_API_KEY belum diset!")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ── Model picker ──
@st.cache_data(show_spinner=False)
def get_available_models():
    try:
        models = client.models.list()
        return [m.name for m in models if "generateContent" in (m.supported_actions or [])]
    except Exception as e:
        return [str(e)]

def pick_model():
    priority = [
        "models/gemini-3-flash-preview",
        "models/gemini-3-pro-preview",
        "models/gemini-3.1-flash-lite-preview",
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
    ]
    available = get_available_models()
    for m in priority:
        if m in available:
            return m
    for m in available:
        if "flash" in m or "pro" in m:
            return m
    return "models/gemini-3-flash-preview"

# ====================== CONTRACT PARAMS ======================
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

BASE_WIN_RATES = {1:72, 2:68, 3:60, 4:62, 5:70, 6:68, 7:54, 8:52, 9:48, 10:78}

def get_params(symbol):
    p  = contract_params.get(symbol, contract_params["6E1"])
    oi = p["oiSpikePct"]
    return {
        "oiSpike":   oi,
        "oiROC":     round(oi * 0.7),
        "cvdMult":   p["cvdSpikeMult"],
        "oiCover":   oi,
        "oiExhaust": oi + 5,
        "tf":        p["tf"],
        "note":      p["note"],
    }

def get_win_rate(setup_id, symbol):
    base = BASE_WIN_RATES.get(setup_id, 60)
    adj  = contract_params[symbol].get("winRateAdj", 0)
    return min(85, max(40, base + adj))

# ====================== CONVERT INVERSE PRICE ======================
def convert_inverse_price(price_str, symbol):
    """Konversi harga futures inverse (JPY/USD dll) ke harga forex retail (USD/JPY dll)"""
    info = contract_params.get(symbol, {})
    if not info.get("inverseQuote"):
        return None
    try:
        price = float(price_str)
        if price <= 0:
            return None
        converted = 1 / price
        # Format tergantung pair
        base = info.get("baseAsli", "")
        if base == "JPY":
            return f"{converted:.2f}"
        elif base in ["CAD", "CHF"]:
            return f"{converted:.4f}"
        else:
            return f"{converted:.5f}"
    except Exception:
        return None

# ====================== AUTO DETECT SYMBOL ======================
def build_detect_prompt():
    symbols = list(contract_params.keys())
    return f"""
Kamu adalah sistem pendeteksi simbol futures.
Lihat screenshot chart TradingView dan identifikasi simbol futures yang ditampilkan.
Kembalikan HANYA JSON ini:
{{
  "symbol": "<salah satu dari: {', '.join(symbols)}>",
  "confidence": <60-99>,
  "reason": "<kenapa kamu yakin ini simbolnya, sebutkan tanda yang kamu lihat di chart>"
}}
Jika tidak yakin atau simbol tidak ada di list, kembalikan symbol yang paling mendekati dari list di atas.
"""

def auto_detect_symbol(image_file):
    """Deteksi simbol dari screenshot chart secara otomatis."""
    img    = Image.open(image_file)
    model  = pick_model()
    prompt = build_detect_prompt()

    response = client.models.generate_content(
        model=model,
        contents=[prompt, img],
        config={"response_mime_type": "application/json", "temperature": 0.05, "max_output_tokens": 256}
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

# ====================== SYSTEM PROMPT ======================
def build_system_prompt(symbol):
    info = contract_params.get(symbol, {})
    p    = get_params(symbol)

    if info.get("inverseQuote"):
        base       = info["baseAsli"]
        pair_forex = info["pairForex"]
        inverse_ctx = f"""
PAIR INVERSE - WAJIB DIPERHATIKAN:
Kontrak futures {symbol} sebenarnya adalah {base}/USD, bukan USD/{base}.
- Price NAIK di chart  = {info['descNaik']}
  Setup BULLISH {symbol} = LONG {base} / SHORT USD = {pair_forex} TURUN
- Price TURUN di chart = {info['descTurun']}
  Setup BEARISH {symbol} = SHORT {base} / LONG USD = {pair_forex} NAIK
Tulis forex_recommendation: arah di pasangan forex retail {pair_forex}.
"""
    else:
        pair = info.get("pair", symbol)
        inverse_ctx = f"Pair normal. BUY futures = LONG {pair}. SELL = SHORT {pair}. Kosongkan inverse_note & forex_recommendation."

    return f"""
Kamu adalah AI Master Analyst untuk sistem OI + CVD Futures Lab.
Analisa screenshot chart futures, identifikasi setup yang cocok dari 10 setup berikut, dan berikan rekomendasi trading dalam format JSON.

=== PARAMETER SIMBOL: {symbol} ({info.get('name')}) ===
OI Spike min   : +{p['oiSpike']}%
OI ROC per bar : >{p['oiROC']}%
CVD Multiplier : >= {p['cvdMult']}x rata-rata
OI Cover       : OI turun {p['oiCover']}% = short covering
OI Exhaust     : OI turun >{p['oiExhaust']}% dari puncak = exhaustion
TF Rekomendasi : {p['tf']}
Catatan        : {p['note']}

=== LOGIKA INVERSE ===
{inverse_ctx}

=== PANDUAN BACA OI + PRICE ===
OI naik  + Price naik  = Fresh LONGS masuk (Long Buildup)   -> Bullish conviction
OI naik  + Price turun = Fresh SHORTS masuk (Short Buildup) -> Bearish conviction
OI turun + Price naik  = Short Covering (Weak Rally)        -> Bukan buyer baru
OI turun + Price turun = Long Liquidation (Weak Selloff)    -> Bukan seller baru

=== 10 SETUP TRADING ===

[SETUP 1] Strong Bullish Trend | BULLISH | WR ~{get_win_rate(1,symbol)}%
- OI naik konsisten 3+ bar (ROC >{p['oiROC']}%/bar)
- CVD slope positif kuat >= {p['cvdMult']}x
- Price: higher highs & higher lows
- Tidak ada bearish divergence CVD vs price
Entry: Pullback ke EMA + CVD naik lagi | SL: Bawah swing low | RR 1:2

[SETUP 2] Strong Bearish Trend | BEARISH | WR ~{get_win_rate(2,symbol)}%
- OI naik saat price turun = fresh shorts min +{p['oiSpike']}%
- CVD turun tajam >= {p['cvdMult']}x
- Price: lower lows & lower highs
- Dead cat bounce ke resistance gagal
Entry: Bounce gagal + CVD confirm turun | SL: Atas swing high | RR 1:2.5

[SETUP 3] Bullish Divergence Reversal | NEUTRAL | WR ~{get_win_rate(3,symbol)}%
- Price lower low TAPI CVD higher low (divergence bullish)
- OI naik dari level rendah +{p['oiROC']}% dalam 5 bar
- Konfirmasi candle bullish (hammer/engulfing/pin bar)
- Support kuat multi-test hold
Entry: Setelah candle bullish konfirmasi | SL: Bawah recent low | RR 1:3

[SETUP 4] Bearish Divergence Reversal | NEUTRAL | WR ~{get_win_rate(4,symbol)}%
- Price higher high TAPI CVD lower high (divergence bearish)
- OI turun saat price rally -{p['oiROC']}% dalam 3 bar
- Resistance kuat terbukti valid
- Volume menurun saat naik
Entry: Rejection candle resistance + CVD drop | SL: Atas recent high | RR 1:2

[SETUP 5] Valid Breakout Long | BULLISH | WR ~{get_win_rate(5,symbol)}%
- Price break resistance full-body bullish candle (body >50%)
- OI spike +{p['oiSpike']}% = fresh longs (BUKAN short covering)
- CVD vertical spike >= {p['cvdMult']}x
- Volume >150% avg 20 bar
Entry: Retest resistance jadi support | SL: Bawah breakout level

[SETUP 6] Valid Breakdown Short | BEARISH | WR ~{get_win_rate(6,symbol)}%
- Price break support full-body bearish candle
- OI spike +{p['oiSpike']}% = fresh shorts
- CVD waterfall >= {p['cvdMult']}x selling
- Tidak ada buying absorption
Entry: Pullback ke broken support | SL: Atas breakdown level

[SETUP 7] Accumulation Phase | BULLISH | WR ~{get_win_rate(7,symbol)}%
- CVD naik konsisten meski price sideways (hidden accumulation)
- OI naik +{p['oiSpike']}% selama konsolidasi 5-10 periode
- Support multi-test hold
- Selling pressure berkurang
Entry: Support zone + CVD spike kecil ke atas | SL: Bawah range low

[SETUP 8] Distribution Phase | BEARISH | WR ~{get_win_rate(8,symbol)}%
- CVD turun konsisten meski price sideways (hidden selling)
- OI naik +{p['oiSpike']}% tapi price gagal breakout resistance
- Resistance multi-test rejection 2-3x
- Higher highs makin lemah
Entry: Rejection candle resistance + CVD drop | SL: Atas range high

[SETUP 9] Weak Rally / Short Covering | BEARISH RISIKO TINGGI | WR ~{get_win_rate(9,symbol)}%
- Price naik TAPI OI TURUN {p['oiCover']}% = short covering bukan fresh longs
- CVD flat atau turun saat price naik
- Rally menuju resistance/Fibonacci
- Volume menurun selama rally
Entry: Short di resistance dengan rejection | SL: +0.5% atas resistance

[SETUP 10] Trend Exhaustion | EXIT SIGNAL | Akurasi ~{get_win_rate(10,symbol)}%
- OI drop >{p['oiExhaust']}% dari puncak = long liquidation massal
- CVD divergence: price naik tapi CVD flat/turun
- Volatilitas menurun, candle mengecil
PENTING: INI BUKAN ENTRY. Signal = NO_ENTRY. Rekomendasikan exit posisi.

=== OUTPUT JSON ===
Kembalikan HANYA JSON valid ini:
{{
  "setup_id": <1-10>,
  "market_state": "<nama setup>",
  "setup_type": "<BULLISH|BEARISH|NEUTRAL|EXIT>",
  "logic_match": "<jelaskan OI/CVD/Price yang terlihat>",
  "checklist_match": "<kondisi yang terpenuhi>",
  "trading_setup": {{
    "signal": "<BUY|SELL|NO_ENTRY>",
    "entry": "<harga>",
    "sl": "<harga>",
    "tp1": "<harga>",
    "tp2": "<harga>",
    "tp3": "<harga>"
  }},
  "confidence": <40-95>,
  "risk_note": "<kondisi invalidasi>",
  "inverse_note": "<isi jika inverse, kosongkan jika tidak>",
  "forex_recommendation": "<isi jika inverse contoh: LONG JPY / USD/JPY TURUN, kosongkan jika tidak>"
}}
"""

# ====================== ANALYZE ONE CHART ======================
def analyze_chart(image_file, symbol):
    img     = Image.open(image_file)
    prompt  = build_system_prompt(symbol)
    info    = contract_params.get(symbol, {})
    model   = pick_model()

    user_msg = f"Analisa chart ini untuk {symbol} ({info.get('name')}, {info.get('pair')}) dan kembalikan JSON."

    response = client.models.generate_content(
        model=model,
        contents=[prompt, user_msg, img],
        config={"response_mime_type": "application/json", "temperature": 0.05, "max_output_tokens": 2048}
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip()), model

# ====================== SCORE CALCULATOR ======================
def calculate_score(result, symbol):
    """
    Hitung skor potensi setup untuk ranking.
    Faktor: confidence AI + win rate sistem + bonus setup high-prob + penalti setup berisiko
    """
    confidence = result.get("confidence", 50)
    setup_id   = result.get("setup_id", 0)
    wr         = get_win_rate(setup_id, symbol)
    signal     = result["trading_setup"]["signal"]

    if signal == "NO_ENTRY":
        return 0  # setup exit tidak diranking

    # Skor dasar = rata-rata confidence AI dan win rate sistem
    score = (confidence * 0.6) + (wr * 0.4)

    # Bonus untuk high-prob setups (1,2,5,6)
    if setup_id in [1, 2, 5, 6]:
        score += 5

    # Bonus kecil untuk reversal setup dengan konfirmasi kuat
    if setup_id in [3, 4] and confidence >= 75:
        score += 3

    # Penalti setup berisiko tinggi
    if setup_id == 9:
        score -= 15

    # Penalti untuk akumulasi/distribusi (medium prob)
    if setup_id in [7, 8]:
        score -= 5

    return round(score, 1)

# ====================== DISPLAY ONE RESULT ======================
def display_result(result, symbol, rank=None, model_used=None):
    info      = contract_params.get(symbol, {})
    setup_id  = result.get("setup_id", 0)
    setup_type = result.get("setup_type", "")
    signal    = result["trading_setup"]["signal"]
    confidence = result.get("confidence", 75)

    # ── Header rank ──
    if rank:
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        st.markdown(f"### {medal} Rank #{rank} — {symbol} ({info.get('name')})")
        score = calculate_score(result, symbol)
        st.caption(f"Skor Potensi: **{score}** | Model: `{model_used or pick_model()}`")
    else:
        st.caption(f"Model: `{model_used or pick_model()}`")

    # ── Setup state ──
    if setup_type == "BULLISH":
        st.success(f"📈 **{result.get('market_state')}** (Setup #{setup_id})")
    elif setup_type == "BEARISH":
        st.error(f"📉 **{result.get('market_state')}** (Setup #{setup_id})")
    elif setup_type == "EXIT":
        st.warning(f"🚪 **{result.get('market_state')}** — EXIT SIGNAL")
    else:
        st.info(f"🔄 **{result.get('market_state')}** (Setup #{setup_id})")

    # ── Signal ──
    if signal == "NO_ENTRY":
        st.warning("⛔ **NO ENTRY** — Kurangi/close posisi yang ada.")
    else:
        emoji = "🟢" if signal == "BUY" else "🔴"
        st.markdown(f"**{emoji} Futures Signal: {signal} {symbol}**")
        if result.get("forex_recommendation"):
            st.markdown(f"**🔄 Forex Equivalent: {result['forex_recommendation']}**")

    # ── Entry / SL ──
    entry = result["trading_setup"].get("entry", "-")
    sl    = result["trading_setup"].get("sl",    "-")
    tp1   = result["trading_setup"].get("tp1",   "-")
    tp2   = result["trading_setup"].get("tp2",   "-")
    tp3   = result["trading_setup"].get("tp3",   "-")

    # Konversi harga untuk inverse pair
    if info.get("inverseQuote"):
        pair_forex = info["pairForex"]
        entry_conv = convert_inverse_price(entry, symbol)
        sl_conv    = convert_inverse_price(sl,    symbol)
        tp1_conv   = convert_inverse_price(tp1,   symbol)
        tp2_conv   = convert_inverse_price(tp2,   symbol)
        tp3_conv   = convert_inverse_price(tp3,   symbol)

        c1, c2 = st.columns(2)
        c1.metric("📍 ENTRY (Futures)", entry,
                  delta=f"{pair_forex}: {entry_conv}" if entry_conv else None,
                  delta_color="off")
        c2.metric("🛑 SL (Futures)", sl,
                  delta=f"{pair_forex}: {sl_conv}" if sl_conv else None,
                  delta_color="off")

        st.markdown("**🎯 Take Profit:**")
        tp_c1, tp_c2, tp_c3 = st.columns(3)
        tp_c1.metric("TP1", tp1, delta=f"{pair_forex}: {tp1_conv}" if tp1_conv else None, delta_color="off")
        tp_c2.metric("TP2", tp2, delta=f"{pair_forex}: {tp2_conv}" if tp2_conv else None, delta_color="off")
        tp_c3.metric("TP3", tp3, delta=f"{pair_forex}: {tp3_conv}" if tp3_conv else None, delta_color="off")
    else:
        c1, c2 = st.columns(2)
        c1.metric("📍 ENTRY", entry)
        c2.metric("🛑 STOP LOSS", sl)

        st.markdown("**🎯 Take Profit:**")
        tp_c1, tp_c2, tp_c3 = st.columns(3)
        tp_c1.metric("TP1", tp1)
        tp_c2.metric("TP2", tp2)
        tp_c3.metric("TP3", tp3)

    # ── Confidence ──
    st.metric("🎯 Confidence AI", f"{confidence}%")
    st.progress(confidence / 100)

    if setup_id in BASE_WIN_RATES:
        wr    = get_win_rate(setup_id, symbol)
        label = "Akurasi sinyal exit" if setup_id == 10 else "Win Rate referensi sistem"
        st.caption(f"📊 {label} Setup #{setup_id} untuk {symbol}: **{wr}%**")

    # ── Logic & Risk ──
    with st.expander("📊 Detail Analisa AI"):
        st.info(result.get("logic_match", "-"))
        st.caption(f"✅ Checklist: {result.get('checklist_match', '-')}")
        if result.get("risk_note"):
            st.warning(f"⚠️ **Risk / Invalidation:** {result['risk_note']}")
        if result.get("inverse_note"):
            st.error(f"🔄 **INVERSE NOTE:** {result['inverse_note']}")

# ====================== MAIN APP ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI")
    st.caption("Cak To Aja • Powered by Gemini • Auto-Detect + Multi-Chart Ranking")

    # ── Sidebar ──
    with st.sidebar:
        st.header("⚙️ Mode Analisa")

        mode = st.radio(
            "Pilih Mode:",
            ["🔍 Single Chart", "📊 Multi Chart + Ranking"],
            index=0
        )

        st.markdown("---")
        st.markdown("**🔧 Tools**")
        if st.button("🔍 Cek Model Tersedia"):
            with st.spinner("Mengambil daftar model..."):
                models = get_available_models()
            st.code("\n".join(models))
            st.caption(f"Model aktif: **{pick_model()}**")

    # ═══════════════════════════════════════
    # MODE 1: SINGLE CHART
    # ═══════════════════════════════════════
    if mode == "🔍 Single Chart":
        st.header("🔍 Analisa Single Chart")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📤 Upload Chart")
            uploaded_file = st.file_uploader(
                "Upload Screenshot", type=["png", "jpg", "jpeg", "webp"], key="single"
            )

            if uploaded_file:
                st.image(uploaded_file, width="stretch")

                # Auto-detect simbol
                st.markdown("---")
                st.markdown("**🤖 Auto-Detect Simbol:**")
                col_auto, col_manual = st.columns([1, 1])

                with col_auto:
                    if st.button("🔎 Detect Otomatis"):
                        with st.spinner("Mendeteksi simbol..."):
                            try:
                                detect = auto_detect_symbol(uploaded_file)
                                detected_sym = detect.get("symbol", "6E1")
                                st.session_state["detected_symbol"] = detected_sym
                                st.success(f"Terdeteksi: **{detected_sym}** ({contract_params[detected_sym]['name']}) — {detect.get('confidence')}% yakin")
                                st.caption(detect.get("reason", ""))
                            except Exception as e:
                                st.error(f"Gagal detect: {e}")

                # Pilih simbol (default ke hasil detect jika ada)
                default_sym = st.session_state.get("detected_symbol", "6E1")
                default_idx = list(contract_params.keys()).index(default_sym) if default_sym in contract_params else 0

                symbol = st.selectbox(
                    "🎯 Simbol (konfirmasi/ubah):",
                    options=list(contract_params.keys()),
                    index=default_idx,
                    format_func=lambda x: f"{x} — {contract_params[x]['name']}",
                    key="single_symbol"
                )

                info = contract_params[symbol]
                p    = get_params(symbol)

                # Info parameter
                with st.expander("📋 Parameter Aktif"):
                    st.markdown(f"- OI Spike min: **+{p['oiSpike']}%**")
                    st.markdown(f"- CVD Multiplier: **≥{p['cvdMult']}×**")
                    st.markdown(f"- OI Exhaust: **>{p['oiExhaust']}%**")
                    st.markdown(f"- TF: **{p['tf']}**")
                    st.caption(p["note"])

                if info.get("inverseQuote"):
                    st.warning(
                        f"⚠️ **INVERSE** — Kontrak: {info['baseAsli']}/USD\n\n"
                        f"📈 Price naik → {info['descNaik']}\n\n"
                        f"📉 Price turun → {info['descTurun']}"
                    )

        with col2:
            st.subheader("🤖 Hasil Analisa")
            if uploaded_file:
                if info.get("inverseQuote"):
                    st.error(
                        f"⚠️ **INVERSE** — {symbol} = kontrak {info['baseAsli']}/USD. "
                        f"Price NAIK = {info['baseAsli']} menguat = {info['pairForex']} TURUN."
                    )

                if st.button("🚀 Jalankan Analisa", type="primary", key="btn_single"):
                    try:
                        with st.spinner("AI menganalisa..."):
                            result, model_used = analyze_chart(uploaded_file, symbol)
                        display_result(result, symbol, model_used=model_used)

                        # Simpan history
                        if "history" not in st.session_state:
                            st.session_state.history = []
                        signal = result["trading_setup"]["signal"]
                        st.session_state.history.append({
                            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "symbol":       symbol,
                            "setup_id":     result.get("setup_id"),
                            "market_state": result.get("market_state"),
                            "signal":       signal,
                            "entry":        result["trading_setup"].get("entry", "-"),
                            "sl":           result["trading_setup"].get("sl",    "-"),
                            "tp1":          result["trading_setup"].get("tp1",   "-"),
                            "confidence":   result.get("confidence", 75),
                            "forex_rec":    result.get("forex_recommendation", ""),
                            "score":        calculate_score(result, symbol),
                        })

                    except json.JSONDecodeError as e:
                        st.error(f"❌ JSON tidak valid: {e}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            else:
                st.info("👆 Upload screenshot chart dulu.\nPastikan OI + CVD + Price terlihat semua.")

    # ═══════════════════════════════════════
    # MODE 2: MULTI CHART + RANKING
    # ═══════════════════════════════════════
    else:
        st.header("📊 Multi Chart + Ranking Potensi")
        st.caption("Upload beberapa chart sekaligus — AI akan menganalisa semua dan meranking dari yang paling potensial.")

        # Upload multiple files
        uploaded_files = st.file_uploader(
            "Upload Screenshots (bisa lebih dari 1)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="multi"
        )

        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} chart diupload.** Konfirmasi simbol masing-masing:")

            # Assign simbol per file
            symbol_assignments = {}
            auto_detect_all = st.checkbox("🤖 Auto-detect semua simbol", value=True)

            cols = st.columns(min(len(uploaded_files), 3))
            for i, f in enumerate(uploaded_files):
                with cols[i % 3]:
                    st.image(f, width="stretch", caption=f.name)

                    if auto_detect_all:
                        # Default ke deteksi nanti saat analisa
                        sym = st.selectbox(
                            f"Simbol {i+1}:",
                            options=["🔎 Auto-detect"] + list(contract_params.keys()),
                            key=f"sym_{i}",
                            format_func=lambda x: x if x == "🔎 Auto-detect" else f"{x} — {contract_params[x]['name']}"
                        )
                    else:
                        sym = st.selectbox(
                            f"Simbol {i+1}:",
                            options=list(contract_params.keys()),
                            key=f"sym_{i}",
                            format_func=lambda x: f"{x} — {contract_params[x]['name']}"
                        )
                    symbol_assignments[i] = sym

            st.markdown("---")

            if st.button("🚀 Analisa Semua & Ranking", type="primary", key="btn_multi"):
                all_results = []
                progress_bar = st.progress(0, text="Memulai analisa...")

                for i, f in enumerate(uploaded_files):
                    sym = symbol_assignments[i]
                    progress_bar.progress(
                        (i) / len(uploaded_files),
                        text=f"Menganalisa chart {i+1}/{len(uploaded_files)}..."
                    )

                    try:
                        # Auto-detect jika dipilih
                        if sym == "🔎 Auto-detect":
                            with st.spinner(f"Mendeteksi simbol chart {i+1}..."):
                                detect = auto_detect_symbol(f)
                                sym    = detect.get("symbol", "6E1")
                                st.toast(f"Chart {i+1} terdeteksi: **{sym}**")

                        with st.spinner(f"Menganalisa {sym}..."):
                            result, model_used = analyze_chart(f, sym)

                        score = calculate_score(result, sym)
                        all_results.append({
                            "file":       f,
                            "symbol":     sym,
                            "result":     result,
                            "model":      model_used,
                            "score":      score,
                            "image":      f,
                        })

                    except Exception as e:
                        st.warning(f"⚠️ Chart {i+1} ({sym}) gagal: {e}")

                progress_bar.progress(1.0, text="Analisa selesai!")

                if not all_results:
                    st.error("Semua analisa gagal. Coba lagi.")
                    return

                # Sort by score descending
                all_results.sort(key=lambda x: x["score"], reverse=True)

                # ── Tampilkan ranking ──
                st.markdown("---")
                st.subheader("🏆 Ranking Setup Paling Potensial")
                st.caption("Diurutkan berdasarkan: Confidence AI × Win Rate Sistem × Bonus/Penalti Setup")

                # Summary table dulu
                st.markdown("**📋 Ringkasan:**")
                summary_cols = st.columns([1, 2, 2, 2, 1, 1])
                summary_cols[0].markdown("**Rank**")
                summary_cols[1].markdown("**Simbol**")
                summary_cols[2].markdown("**Setup**")
                summary_cols[3].markdown("**Signal**")
                summary_cols[4].markdown("**Conf.**")
                summary_cols[5].markdown("**Skor**")

                for rank, item in enumerate(all_results, 1):
                    r      = item["result"]
                    signal = r["trading_setup"]["signal"]
                    medal  = {1:"🥇", 2:"🥈", 3:"🥉"}.get(rank, f"#{rank}")
                    sig_em = "🟢" if signal=="BUY" else ("🔴" if signal=="SELL" else "⛔")
                    cols   = st.columns([1, 2, 2, 2, 1, 1])
                    cols[0].write(medal)
                    cols[1].write(f"**{item['symbol']}** ({contract_params[item['symbol']]['name']})")
                    cols[2].write(r.get("market_state", "-"))
                    cols[3].write(f"{sig_em} {signal}")
                    cols[4].write(f"{r.get('confidence')}%")
                    cols[5].write(f"**{item['score']}**")

                st.markdown("---")

                # Detail tiap ranking
                for rank, item in enumerate(all_results, 1):
                    with st.expander(
                        f"{'🥇' if rank==1 else '🥈' if rank==2 else '🥉' if rank==3 else f'#{rank}'} "
                        f"Rank #{rank} — {item['symbol']} ({contract_params[item['symbol']]['name']}) "
                        f"| Skor: {item['score']}",
                        expanded=(rank <= 3)  # auto-expand top 3
                    ):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.image(item["image"], width="stretch")
                        with c2:
                            display_result(item["result"], item["symbol"], rank=rank, model_used=item["model"])

                # Simpan ke history
                if "history" not in st.session_state:
                    st.session_state.history = []
                for item in all_results:
                    r = item["result"]
                    st.session_state.history.append({
                        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "symbol":       item["symbol"],
                        "setup_id":     r.get("setup_id"),
                        "market_state": r.get("market_state"),
                        "signal":       r["trading_setup"]["signal"],
                        "entry":        r["trading_setup"].get("entry", "-"),
                        "sl":           r["trading_setup"].get("sl",    "-"),
                        "tp1":          r["trading_setup"].get("tp1",   "-"),
                        "confidence":   r.get("confidence", 75),
                        "forex_rec":    r.get("forex_recommendation", ""),
                        "score":        item["score"],
                    })

    # ═══════════════════════════════════════
    # HISTORY
    # ═══════════════════════════════════════
    st.markdown("---")
    st.subheader("📜 Riwayat Analisa")
    if "history" in st.session_state and st.session_state.history:
        col_clr, _ = st.columns([1, 4])
        if col_clr.button("🗑️ Hapus Riwayat"):
            st.session_state.history = []
            st.rerun()

        # Sort history by score desc
        sorted_hist = sorted(st.session_state.history, key=lambda x: x.get("score", 0), reverse=True)

        for item in sorted_hist[-10:]:
            sig_em    = "🟢" if item["signal"]=="BUY" else ("🔴" if item["signal"]=="SELL" else "⛔")
            forex_str = f" | 🔄 **{item['forex_rec']}**" if item.get("forex_rec") else ""
            score_str = f" | Skor: **{item.get('score', '-')}**"
            st.markdown(
                f"**{item['timestamp']}** — **{item['symbol']}** | "
                f"Setup #{item.get('setup_id')} {item['market_state']}  \n"
                f"{sig_em} **{item['signal']}** | "
                f"Entry: `{item['entry']}` | SL: `{item['sl']}` | "
                f"TP1: `{item.get('tp1')}` | Conf: **{item['confidence']}%**"
                f"{score_str}{forex_str}"
            )
            st.divider()
    else:
        st.info("Belum ada riwayat analisa.")


if __name__ == "__main__":
    main()
