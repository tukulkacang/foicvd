import streamlit as st
from openai import OpenAI
from PIL import Image
import os
import json
import io
import base64
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="Cak To's OI + CVD Lab AI", page_icon="📊", layout="wide")

# ── API KEY ──
OR_KEY = os.getenv("OPENROUTER_API_KEY")
if not OR_KEY:
    try:
        OR_KEY = st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        OR_KEY = None

if not OR_KEY:
    st.error("❌ OPENROUTER_API_KEY belum diset! Tambahkan di .env atau Streamlit secrets.")
    st.stop()

# ── OpenRouter client (OpenAI-compatible) ──
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_KEY,
)

# ====================== MODEL DEFINITIONS ======================
# Model diurutkan: terbaik dulu, free tier di bawah
MODELS = {
    # ── Paid (terbaik untuk chart vision) ──
    "google/gemini-2.5-flash":           {"label": "Gemini 2.5 Flash",        "free": False, "vision": True},
    "google/gemini-2.0-flash-001":       {"label": "Gemini 2.0 Flash",        "free": False, "vision": True},
    "openai/gpt-4o":                     {"label": "GPT-4o",                   "free": False, "vision": True},
    "openai/gpt-4o-mini":                {"label": "GPT-4o Mini",              "free": False, "vision": True},
    "anthropic/claude-sonnet-4-5":       {"label": "Claude Sonnet 4.5",        "free": False, "vision": True},
    # ── Free tier (permanent free di OpenRouter) ──
    "google/gemini-2.0-flash-exp:free":  {"label": "Gemini 2.0 Flash (FREE)", "free": True,  "vision": True},
    "qwen/qwen2.5-vl-72b-instruct:free": {"label": "Qwen 2.5 VL 72B (FREE)", "free": True,  "vision": True},
    "meta-llama/llama-4-maverick:free":  {"label": "LLaMA 4 Maverick (FREE)", "free": True,  "vision": True},
    "meta-llama/llama-4-scout:free":     {"label": "LLaMA 4 Scout (FREE)",    "free": True,  "vision": True},
    "microsoft/phi-4-multimodal-instruct:free": {"label": "Phi-4 Multimodal (FREE)", "free": True, "vision": True},
}

FREE_MODELS     = [m for m, v in MODELS.items() if v["free"]]
PAID_MODELS     = [m for m, v in MODELS.items() if not v["free"]]
FALLBACK_ORDER  = [
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "meta-llama/llama-4-maverick:free",
    "meta-llama/llama-4-scout:free",
    "microsoft/phi-4-multimodal-instruct:free",
]

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

# ====================== IMAGE TO BASE64 ======================
def image_to_base64(image_bytes):
    """Konversi bytes gambar ke base64 string untuk OpenAI vision format."""
    return base64.b64encode(image_bytes).decode("utf-8")

# ====================== CALL MODEL WITH FALLBACK ======================
def call_model_with_fallback(messages, preferred_model, max_tokens=2048):
    """
    Coba preferred_model dulu.
    Kalau gagal (rate limit / error), auto-fallback ke free model berikutnya.
    Return: (response_text, model_used)
    """
    models_to_try = [preferred_model]

    # Tambahkan fallback: kalau preferred bukan free, tambah semua free model
    for m in FALLBACK_ORDER:
        if m != preferred_model:
            models_to_try.append(m)

    last_error = None
    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.05,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise ValueError("Model mengembalikan respons kosong")
            return text, model

        except Exception as e:
            err_str = str(e)
            last_error = err_str
            # Kalau rate limit atau quota, coba model berikutnya
            if any(x in err_str for x in ["429", "rate_limit", "quota", "RESOURCE_EXHAUSTED", "insufficient_quota"]):
                st.toast(f"⚠️ {MODELS.get(model,{}).get('label', model)} limit — mencoba model berikutnya...")
                continue
            # Error lain (model tidak support vision dll) — skip juga
            elif any(x in err_str for x in ["400", "vision", "image", "multimodal", "not supported"]):
                st.toast(f"⚠️ {MODELS.get(model,{}).get('label', model)} tidak support vision — skip...")
                continue
            else:
                raise  # Error lain langsung raise

    raise Exception(f"Semua model gagal. Error terakhir: {last_error}")

# ====================== BUILD MESSAGES ======================
def build_messages(system_prompt, user_text, image_bytes):
    """Build OpenAI-format messages dengan vision (base64 image)."""
    b64 = image_to_base64(image_bytes)
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text",      "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]
        }
    ]

# ====================== CONVERT INVERSE PRICE ======================
def convert_inverse_price(price_str, symbol):
    info = contract_params.get(symbol, {})
    if not info.get("inverseQuote"):
        return None
    try:
        price = float(price_str)
        if price <= 0:
            return None
        converted = 1 / price
        base = info.get("baseAsli", "")
        if base == "JPY":
            return f"{converted:.2f}"
        else:
            return f"{converted:.4f}"
    except Exception:
        return None

# ====================== AUTO DETECT SYMBOL ======================
def build_detect_prompt():
    symbols = list(contract_params.keys())
    return f"""
Kamu adalah sistem pendeteksi simbol futures dari screenshot chart TradingView.
Lihat nama simbol/pair yang tertulis di chart dan identifikasi simbolnya.
Kembalikan HANYA JSON valid:
{{"symbol": "<salah satu dari: {', '.join(symbols)}>", "confidence": <60-99>, "reason": "<tanda yang kamu lihat>"}}
"""

def auto_detect_symbol(image_bytes, preferred_model):
    messages = build_messages(
        build_detect_prompt(),
        "Identifikasi simbol futures di chart ini.",
        image_bytes
    )
    raw, model_used = call_model_with_fallback(messages, preferred_model, max_tokens=256)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    result = json.loads(raw)
    return result, model_used

# ====================== SYSTEM PROMPT ======================
def build_system_prompt(symbol):
    info = contract_params.get(symbol, {})
    p    = get_params(symbol)

    if info.get("inverseQuote"):
        base, pair_forex = info["baseAsli"], info["pairForex"]
        inverse_ctx = f"""
PAIR INVERSE - WAJIB DIPERHATIKAN:
Kontrak futures {symbol} sebenarnya adalah {base}/USD, bukan USD/{base}.
- Price NAIK di chart  = {info['descNaik']} → Setup BULLISH = LONG {base} / {pair_forex} TURUN
- Price TURUN di chart = {info['descTurun']} → Setup BEARISH = SHORT {base} / {pair_forex} NAIK
Tulis forex_recommendation sesuai arah di {pair_forex}.
"""
    else:
        pair = info.get("pair", symbol)
        inverse_ctx = f"Pair normal. BUY = LONG {pair}. SELL = SHORT {pair}. Kosongkan inverse_note & forex_recommendation."

    return f"""
Kamu adalah AI Master Analyst untuk sistem OI + CVD Futures Lab.
Analisa screenshot chart futures dan kembalikan rekomendasi trading dalam format JSON.

=== PARAMETER {symbol} ({info.get('name')}) ===
OI Spike min: +{p['oiSpike']}% | OI ROC: >{p['oiROC']}%/bar | CVD Mult: >={p['cvdMult']}x
OI Cover: turun {p['oiCover']}% = short covering | OI Exhaust: turun >{p['oiExhaust']}% = exhaustion
TF: {p['tf']} | {p['note']}

=== LOGIKA INVERSE ===
{inverse_ctx}

=== PANDUAN OI + PRICE ===
OI↑+Price↑ = Fresh LONGS (Long Buildup) | OI↑+Price↓ = Fresh SHORTS (Short Buildup)
OI↓+Price↑ = Short Covering (Weak Rally) | OI↓+Price↓ = Long Liquidation

=== 10 SETUP ===
[1] Strong Bullish Trend | BULLISH | WR~{get_win_rate(1,symbol)}%
OI naik 3+ bar (ROC>{p['oiROC']}%/bar) + CVD slope positif >={p['cvdMult']}x + HH/HL + no bearish div
Entry: Pullback EMA + CVD naik | SL: Bawah swing low | RR 1:2

[2] Strong Bearish Trend | BEARISH | WR~{get_win_rate(2,symbol)}%
OI↑ saat price↓ = fresh shorts +{p['oiSpike']}% + CVD↓ >={p['cvdMult']}x + LL/LH
Entry: Dead cat bounce gagal + CVD confirm | SL: Atas swing high | RR 1:2.5

[3] Bullish Divergence Reversal | NEUTRAL | WR~{get_win_rate(3,symbol)}%
Price LL tapi CVD HL (divergence bullish) + OI naik +{p['oiROC']}% dalam 5 bar + candle bullish konfirmasi + support kuat
Entry: Candle konfirmasi | SL: Bawah recent low | RR 1:3

[4] Bearish Divergence Reversal | NEUTRAL | WR~{get_win_rate(4,symbol)}%
Price HH tapi CVD LH (divergence bearish) + OI turun -{p['oiROC']}% dalam 3 bar + resistance kuat + volume turun
Entry: Rejection candle + CVD drop | SL: Atas recent high | RR 1:2

[5] Valid Breakout Long | BULLISH | WR~{get_win_rate(5,symbol)}%
Break resistance full-body bullish (body>50%) + OI spike +{p['oiSpike']}% fresh longs + CVD vertical >={p['cvdMult']}x + volume >150%
Entry: Retest resistance→support | SL: Bawah breakout level

[6] Valid Breakdown Short | BEARISH | WR~{get_win_rate(6,symbol)}%
Break support full-body bearish + OI spike +{p['oiSpike']}% fresh shorts + CVD waterfall >={p['cvdMult']}x + no absorption
Entry: Pullback broken support | SL: Atas breakdown level

[7] Accumulation Phase | BULLISH | WR~{get_win_rate(7,symbol)}%
CVD naik meski sideways + OI naik +{p['oiSpike']}% konsolidasi 5-10 periode + support hold + selling pressure turun
Entry: Support zone + CVD spike | SL: Bawah range low

[8] Distribution Phase | BEARISH | WR~{get_win_rate(8,symbol)}%
CVD turun meski sideways + OI naik +{p['oiSpike']}% tapi gagal breakout + resistance multi-test + HH makin lemah
Entry: Rejection + CVD drop | SL: Atas range high

[9] Weak Rally/Short Covering | BEARISH RISIKO TINGGI | WR~{get_win_rate(9,symbol)}%
Price↑ tapi OI↓ {p['oiCover']}% = short covering + CVD flat/turun + menuju resistance + volume turun
Entry: Short di resistance | SL: +0.5% atas resistance (RISIKO TINGGI)

[10] Trend Exhaustion | EXIT SIGNAL | Akurasi~{get_win_rate(10,symbol)}%
OI drop >{p['oiExhaust']}% dari puncak + CVD divergence + volatilitas turun + volume spike no follow-through
PENTING: signal = NO_ENTRY, rekomendasikan exit/kurangi posisi

=== OUTPUT JSON ===
{{"setup_id":<1-10>,"market_state":"<nama>","setup_type":"<BULLISH|BEARISH|NEUTRAL|EXIT>","logic_match":"<penjelasan OI/CVD/Price yang terlihat>","checklist_match":"<kondisi terpenuhi>","trading_setup":{{"signal":"<BUY|SELL|NO_ENTRY>","entry":"<harga>","sl":"<harga>","tp1":"<harga>","tp2":"<harga>","tp3":"<harga>"}},"confidence":<40-95>,"risk_note":"<invalidasi>","inverse_note":"<isi jika inverse>","forex_recommendation":"<isi jika inverse>"}}
"""

# ====================== ANALYZE ======================
def analyze_chart(image_bytes, symbol, preferred_model):
    info     = contract_params.get(symbol, {})
    messages = build_messages(
        build_system_prompt(symbol),
        f"Analisa chart {symbol} ({info.get('name')}) dan kembalikan JSON.",
        image_bytes
    )
    raw, model_used = call_model_with_fallback(messages, preferred_model)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw), model_used

# ====================== SCORE ======================
def calculate_score(result, symbol):
    confidence = result.get("confidence", 50)
    setup_id   = result.get("setup_id", 0)
    signal     = result["trading_setup"]["signal"]
    if signal == "NO_ENTRY":
        return 0
    wr    = get_win_rate(setup_id, symbol)
    score = (confidence * 0.6) + (wr * 0.4)
    if setup_id in [1, 2, 5, 6]: score += 5
    if setup_id in [3, 4] and confidence >= 75: score += 3
    if setup_id == 9:  score -= 15
    if setup_id in [7, 8]: score -= 5
    return round(score, 1)

# ====================== DISPLAY RESULT ======================
def display_result(result, symbol, rank=None, model_used=None):
    info       = contract_params.get(symbol, {})
    setup_id   = result.get("setup_id", 0)
    setup_type = result.get("setup_type", "")
    signal     = result["trading_setup"]["signal"]
    confidence = result.get("confidence", 75)

    if rank:
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(rank, f"#{rank}")
        st.markdown(f"### {medal} Rank #{rank} — {symbol} ({info.get('name')})")
        st.caption(f"Skor: **{calculate_score(result, symbol)}** | Model: `{model_used}`")
    else:
        st.caption(f"Model: `{model_used}`")

    if setup_type == "BULLISH":
        st.success(f"📈 **{result.get('market_state')}** (Setup #{setup_id})")
    elif setup_type == "BEARISH":
        st.error(f"📉 **{result.get('market_state')}** (Setup #{setup_id})")
    elif setup_type == "EXIT":
        st.warning(f"🚪 **{result.get('market_state')}** — EXIT SIGNAL")
    else:
        st.info(f"🔄 **{result.get('market_state')}** (Setup #{setup_id})")

    if signal == "NO_ENTRY":
        st.warning("⛔ **NO ENTRY** — Kurangi/close posisi yang ada.")
    else:
        emoji = "🟢" if signal == "BUY" else "🔴"
        st.markdown(f"**{emoji} Futures Signal: {signal} {symbol}**")
        if result.get("forex_recommendation"):
            st.markdown(f"**🔄 Forex Equivalent: {result['forex_recommendation']}**")

    # Entry/SL/TP dengan konversi inverse
    entry = result["trading_setup"].get("entry", "-")
    sl    = result["trading_setup"].get("sl",    "-")
    tp1   = result["trading_setup"].get("tp1",   "-")
    tp2   = result["trading_setup"].get("tp2",   "-")
    tp3   = result["trading_setup"].get("tp3",   "-")

    if info.get("inverseQuote"):
        pf = info["pairForex"]
        c1, c2 = st.columns(2)
        c1.metric("📍 ENTRY (Futures)", entry,
                  delta=f"{pf}: {convert_inverse_price(entry, symbol)}", delta_color="off")
        c2.metric("🛑 SL (Futures)", sl,
                  delta=f"{pf}: {convert_inverse_price(sl, symbol)}", delta_color="off")
        st.markdown("**🎯 Take Profit:**")
        t1, t2, t3 = st.columns(3)
        t1.metric("TP1", tp1, delta=f"{pf}: {convert_inverse_price(tp1, symbol)}", delta_color="off")
        t2.metric("TP2", tp2, delta=f"{pf}: {convert_inverse_price(tp2, symbol)}", delta_color="off")
        t3.metric("TP3", tp3, delta=f"{pf}: {convert_inverse_price(tp3, symbol)}", delta_color="off")
    else:
        c1, c2 = st.columns(2)
        c1.metric("📍 ENTRY",     entry)
        c2.metric("🛑 STOP LOSS", sl)
        st.markdown("**🎯 Take Profit:**")
        t1, t2, t3 = st.columns(3)
        t1.metric("TP1", tp1)
        t2.metric("TP2", tp2)
        t3.metric("TP3", tp3)

    st.metric("🎯 Confidence AI", f"{confidence}%")
    st.progress(confidence / 100)
    if setup_id in BASE_WIN_RATES:
        wr    = get_win_rate(setup_id, symbol)
        label = "Akurasi exit" if setup_id == 10 else "Win Rate referensi"
        st.caption(f"📊 {label} Setup #{setup_id} untuk {symbol}: **{wr}%**")

    with st.expander("📊 Detail Analisa"):
        st.info(result.get("logic_match", "-"))
        st.caption(f"✅ Checklist: {result.get('checklist_match', '-')}")
        if result.get("risk_note"):
            st.warning(f"⚠️ **Invalidation:** {result['risk_note']}")
        if result.get("inverse_note"):
            st.error(f"🔄 **INVERSE NOTE:** {result['inverse_note']}")

# ====================== MAIN ======================
def main():
    st.title("📊 OI + CVD Futures Lab AI")
    st.caption("Cak To Aja • OpenRouter Multi-Model + Auto-Fallback")

    with st.sidebar:
        st.header("⚙️ Settings")

        # Model selector
        st.markdown("**🤖 Pilih Model:**")
        free_only = st.checkbox("Tampilkan free model saja", value=False)
        model_options = FREE_MODELS if free_only else list(MODELS.keys())
        preferred_model = st.selectbox(
            "Model:",
            options=model_options,
            format_func=lambda x: MODELS.get(x, {}).get("label", x),
            index=0
        )
        if MODELS.get(preferred_model, {}).get("free"):
            st.success("✅ Free tier")
        else:
            st.info("💳 Paid (lebih akurat)")

        st.caption("💡 Auto-fallback ke free model jika limit")

        st.markdown("---")
        mode = st.radio("**Mode Analisa:**", ["🔍 Single Chart", "📊 Multi Chart + Ranking"])

        st.markdown("---")
        st.markdown("**📋 Fallback Order:**")
        for i, m in enumerate(FALLBACK_ORDER, 1):
            st.caption(f"{i}. {MODELS.get(m,{}).get('label', m)}")

    # ═══════════ SINGLE MODE ═══════════
    if mode == "🔍 Single Chart":
        st.header("🔍 Analisa Single Chart")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📤 Upload Chart")
            uploaded = st.file_uploader("Upload Screenshot", type=["png","jpg","jpeg","webp"], key="single")

            if uploaded:
                uploaded.seek(0)
                st.image(uploaded, width="stretch")
                file_bytes = uploaded.read()

                st.markdown("---")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔎 Auto-detect Simbol"):
                        with st.spinner("Mendeteksi..."):
                            try:
                                det, det_model = auto_detect_symbol(file_bytes, preferred_model)
                                st.session_state["detected_symbol"] = det.get("symbol", "6E1")
                                st.success(f"**{det.get('symbol')}** — {det.get('confidence')}% yakin")
                                st.caption(f"via `{det_model}`")
                                st.caption(det.get("reason",""))
                            except Exception as e:
                                st.error(f"Gagal: {e}")

                default_sym = st.session_state.get("detected_symbol", "6E1")
                default_idx = list(contract_params.keys()).index(default_sym) if default_sym in contract_params else 0
                symbol = st.selectbox(
                    "🎯 Simbol:",
                    options=list(contract_params.keys()),
                    index=default_idx,
                    format_func=lambda x: f"{x} — {contract_params[x]['name']}",
                    key="single_sym"
                )
                info = contract_params[symbol]
                p    = get_params(symbol)
                with st.expander("📋 Parameter Aktif"):
                    st.markdown(f"- OI Spike: **+{p['oiSpike']}%** | CVD: **≥{p['cvdMult']}×** | TF: **{p['tf']}**")
                    st.caption(p["note"])
                if info.get("inverseQuote"):
                    st.warning(f"⚠️ INVERSE — {info['baseAsli']}/USD\n📈 {info['descNaik']}\n📉 {info['descTurun']}")

        with col2:
            st.subheader("🤖 Hasil Analisa")
            if uploaded:
                if info.get("inverseQuote"):
                    st.error(f"⚠️ INVERSE — Price NAIK = {info['baseAsli']} menguat = {info['pairForex']} TURUN")
                if st.button("🚀 Jalankan Analisa", type="primary", key="btn_single"):
                    try:
                        with st.spinner("AI menganalisa..."):
                            result, model_used = analyze_chart(file_bytes, symbol, preferred_model)
                        display_result(result, symbol, model_used=model_used)

                        if "history" not in st.session_state:
                            st.session_state.history = []
                        st.session_state.history.append({
                            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "symbol":       symbol,
                            "setup_id":     result.get("setup_id"),
                            "market_state": result.get("market_state"),
                            "signal":       result["trading_setup"]["signal"],
                            "entry":        result["trading_setup"].get("entry","-"),
                            "sl":           result["trading_setup"].get("sl","-"),
                            "tp1":          result["trading_setup"].get("tp1","-"),
                            "confidence":   result.get("confidence",75),
                            "forex_rec":    result.get("forex_recommendation",""),
                            "score":        calculate_score(result, symbol),
                            "model":        model_used,
                        })
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                st.info("👆 Upload chart dulu — pastikan OI + CVD + Price terlihat.")

    # ═══════════ MULTI MODE ═══════════
    else:
        st.header("📊 Multi Chart + Ranking Potensi")
        st.caption("Upload beberapa chart — AI analisa semua, ranking dari paling potensial.")

        uploaded_files = st.file_uploader(
            "Upload Screenshots (bisa lebih dari 1)",
            type=["png","jpg","jpeg","webp"],
            accept_multiple_files=True,
            key="multi"
        )

        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} chart diupload.**")
            auto_detect_all = st.checkbox("🤖 Auto-detect semua simbol", value=True)

            symbol_assignments = {}
            cols = st.columns(min(len(uploaded_files), 3))
            for i, f in enumerate(uploaded_files):
                with cols[i % 3]:
                    f.seek(0)
                    st.image(f, width="stretch", caption=f.name)
                    options = ["🔎 Auto-detect"] + list(contract_params.keys()) if auto_detect_all else list(contract_params.keys())
                    sym = st.selectbox(
                        f"Simbol {i+1}:", options=options, key=f"sym_{i}",
                        format_func=lambda x: x if x=="🔎 Auto-detect" else f"{x} — {contract_params[x]['name']}"
                    )
                    symbol_assignments[i] = sym

            st.markdown("---")
            if st.button("🚀 Analisa Semua & Ranking", type="primary", key="btn_multi"):
                all_results  = []
                progress_bar = st.progress(0, text="Memulai...")

                for i, f in enumerate(uploaded_files):
                    sym = symbol_assignments[i]
                    progress_bar.progress(i / len(uploaded_files), text=f"Chart {i+1}/{len(uploaded_files)}...")
                    try:
                        f.seek(0)
                        file_bytes = f.read()

                        if sym == "🔎 Auto-detect":
                            with st.spinner(f"Mendeteksi chart {i+1}..."):
                                det, _ = auto_detect_symbol(file_bytes, preferred_model)
                                sym = det.get("symbol", "6E1")
                                st.toast(f"Chart {i+1}: **{sym}** terdeteksi")

                        with st.spinner(f"Menganalisa {sym}..."):
                            result, model_used = analyze_chart(file_bytes, sym, preferred_model)

                        all_results.append({
                            "bytes":      file_bytes,
                            "symbol":     sym,
                            "result":     result,
                            "model":      model_used,
                            "score":      calculate_score(result, sym),
                        })
                    except Exception as e:
                        st.warning(f"⚠️ Chart {i+1} ({sym}) gagal: {e}")

                progress_bar.progress(1.0, text="Selesai!")

                if not all_results:
                    st.error("Semua analisa gagal.")
                    return

                all_results.sort(key=lambda x: x["score"], reverse=True)

                st.markdown("---")
                st.subheader("🏆 Ranking Setup Paling Potensial")

                # Summary table
                hcols = st.columns([1,2,2,2,1,1])
                for col, label in zip(hcols, ["Rank","Simbol","Setup","Signal","Conf.","Skor"]):
                    col.markdown(f"**{label}**")

                for rank, item in enumerate(all_results, 1):
                    r      = item["result"]
                    signal = r["trading_setup"]["signal"]
                    medal  = {1:"🥇",2:"🥈",3:"🥉"}.get(rank, f"#{rank}")
                    sig_em = "🟢" if signal=="BUY" else ("🔴" if signal=="SELL" else "⛔")
                    rcols  = st.columns([1,2,2,2,1,1])
                    rcols[0].write(medal)
                    rcols[1].write(f"**{item['symbol']}**")
                    rcols[2].write(r.get("market_state","-"))
                    rcols[3].write(f"{sig_em} {signal}")
                    rcols[4].write(f"{r.get('confidence')}%")
                    rcols[5].write(f"**{item['score']}**")

                st.markdown("---")
                for rank, item in enumerate(all_results, 1):
                    medal = {1:"🥇",2:"🥈",3:"🥉"}.get(rank, f"#{rank}")
                    with st.expander(
                        f"{medal} Rank #{rank} — {item['symbol']} | Skor: {item['score']}",
                        expanded=(rank <= 3)
                    ):
                        c1, c2 = st.columns([1,2])
                        with c1:
                            st.image(io.BytesIO(item["bytes"]), width="stretch")
                        with c2:
                            display_result(item["result"], item["symbol"], rank=rank, model_used=item["model"])

                # Simpan history
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
                        "entry":        r["trading_setup"].get("entry","-"),
                        "sl":           r["trading_setup"].get("sl","-"),
                        "tp1":          r["trading_setup"].get("tp1","-"),
                        "confidence":   r.get("confidence",75),
                        "forex_rec":    r.get("forex_recommendation",""),
                        "score":        item["score"],
                        "model":        item["model"],
                    })

    # ═══════════ HISTORY ═══════════
    st.markdown("---")
    st.subheader("📜 Riwayat Analisa")
    if "history" in st.session_state and st.session_state.history:
        col_clr, _ = st.columns([1,4])
        if col_clr.button("🗑️ Hapus Riwayat"):
            st.session_state.history = []
            st.rerun()
        for item in sorted(st.session_state.history, key=lambda x: x.get("score",0), reverse=True)[-10:]:
            sig_em    = "🟢" if item["signal"]=="BUY" else ("🔴" if item["signal"]=="SELL" else "⛔")
            forex_str = f" | 🔄 **{item['forex_rec']}**" if item.get("forex_rec") else ""
            st.markdown(
                f"**{item['timestamp']}** — **{item['symbol']}** | Setup #{item.get('setup_id')} {item['market_state']}  \n"
                f"{sig_em} **{item['signal']}** | Entry:`{item['entry']}` SL:`{item['sl']}` TP1:`{item.get('tp1')}` "
                f"Conf:**{item['confidence']}%** Skor:**{item.get('score','-')}**{forex_str} | `{item.get('model','')}`"
            )
            st.divider()
    else:
        st.info("Belum ada riwayat.")


if __name__ == "__main__":
    main()
