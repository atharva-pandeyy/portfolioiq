# app.py — PortfolioIQ
# Indian stock & MF analytics dashboard
# built by Atharva Pandey | run: python -m streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from data.fetcher import (get_stock, get_index, get_nifty, get_stock_info,
                           suggest_tickers, search_mf, get_mf_nav,
                           detect_benchmark, load_csv)
from analytics.metrics import (get_all, daily_returns, to_100, alpha_beta,
                                sma_backtest, portfolio_pnl)

st.set_page_config(page_title="PortfolioIQ", page_icon="📊", layout="wide")

C = {"accent": "#7C6AFF", "green": "#3ECF8E", "red": "#F87171", "amber": "#FBBF24"}

st.markdown("""<style>
[data-testid="stSidebar"]{background:#0e0e16}
[data-testid="stSidebar"] *{color:#c8c8d8!important}
.card{background:#111118;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px 18px;text-align:center}
.lbl{font-size:11px;color:#6b6b80;text-transform:uppercase;letter-spacing:.06em;display:flex;align-items:center;justify-content:center;gap:5px}
.val{font-size:26px;font-weight:700;margin-top:6px}
.sub{font-size:11px;color:#6b6b80;margin-top:3px}
.g{color:#3ECF8E}.r{color:#F87171}.a{color:#FBBF24}.w{color:#fff}
.tip-wrap{position:relative;display:inline-block;cursor:help}
.tip-wrap .tip{visibility:hidden;opacity:0;background:#1e1e2e;color:#c8c8d8;border:1px solid rgba(255,255,255,0.12);border-radius:6px;padding:8px 11px;font-size:11px;line-height:1.5;width:230px;text-align:left;position:absolute;bottom:130%;left:50%;transform:translateX(-50%);z-index:9999;transition:opacity .15s;pointer-events:none}
.tip-wrap:hover .tip{visibility:visible;opacity:1}
.ti{color:#6b6b80;font-size:12px}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.b-green{background:rgba(62,207,142,.13);color:#3ECF8E;border:1px solid rgba(62,207,142,.3)}
.b-purple{background:rgba(124,106,255,.13);color:#a594ff;border:1px solid rgba(124,106,255,.3)}
.sh{font-size:15px;font-weight:600;color:#e8e8f0;margin:18px 0 8px;padding-bottom:5px;border-bottom:1px solid rgba(255,255,255,0.06)}
.btag{display:inline-block;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:2px 8px;font-size:11px;color:#9ca3af;margin-bottom:6px}
</style>""", unsafe_allow_html=True)

TIPS = {
    "Total Return":  "Overall % gain/loss. +37% = ₹1L became ₹1.37L.",
    "CAGR":          "Yearly growth rate that gives the same end result. Better than simple return for comparing across time periods.",
    "Sharpe Ratio":  "Return per unit of risk. >1 = good, >2 = excellent, <0 = FD was better.",
    "Max Drawdown":  "Biggest fall from a recent peak. -27% = at worst you'd have been down 27% from the high.",
    "Volatility":    "How wildly price swings, annualised. Nifty ~15%, most stocks 20–45%.",
    "Alpha":         "Extra return above what benchmark predicted. Positive = outperformed.",
    "Beta":          "Sensitivity to benchmark. 1.2 = if benchmark falls 10%, this falls ~12%.",
    "Strategy Return":"Return from the SMA crossover strategy — only invested when fast > slow.",
    "Buy & Hold":    "Return from buying day 1 and holding. Most strategies fail to beat this.",
    "Win Rate":      "% of trades that were profitable.",
}

def tip(name):
    t = TIPS.get(name, "")
    if not t: return ""
    return f'<span class="tip-wrap"><span class="ti">ⓘ</span><span class="tip">{t}</span></span>'

def card(label, val, colour="w", sub=""):
    st.markdown(f'<div class="card"><div class="lbl">{label}&nbsp;{tip(label)}</div>'
                f'<div class="val {colour}">{val}</div>'
                f'{"<div class=sub>" + sub + "</div>" if sub else ""}</div>', unsafe_allow_html=True)

def pf(v, d=1):
    if v is None: return "N/A"
    return f"{'+' if v>0 else ''}{v*100:.{d}f}%"

def clr(v):
    return "w" if v is None else ("g" if v>=0 else "r")


# session state defaults
for k, v in {
    "s_df": None, "s_bench": None, "s_bname": "Nifty 50",
    "s_info": {}, "s_ticker": "", "s_period": None,
    "pending": None,
    "mf_df": None, "mf_bench": None, "mf_bname": "Nifty 50",
    "mf_name": "", "mf_code": None, "mf_byf": None, "mf_period": None,
    "pf_h": None, "pf_p": None,
}.items():
    if k not in st.session_state: st.session_state[k] = v

# stock name lookup - common NSE stocks
MASTER_TICKERS = {
    "RELIANCE": ["reliance industries", "reliance", "ril"],
    "TCS": ["tcs", "tata consultancy services", "tata consultancy"],
    "HDFCBANK": ["hdfc bank", "hdfc"],
    "INFY": ["infosys"],
    "ICICIBANK": ["icici bank", "icici"],
    "SBIN": ["state bank of india", "sbi"],
    "KOTAKBANK": ["kotak mahindra bank", "kotak"],
    "LT": ["larsen & toubro", "larsen and toubro", "l&t"],
    "ITC": ["itc"],
    "HINDUNILVR": ["hindustan unilever", "hul"],
    "BAJFINANCE": ["bajaj finance"],
    "MARUTI": ["maruti suzuki"],
    "TATASTEEL": ["tata steel"],
    "ADANIPORTS": ["adani ports"],
    "ADANIENT": ["adani enterprises"],
    "ADANIGREEN": ["adani green"],
    "ATGL": ["adani total gas"],
    "DMART": ["dmart", "avenue supermarts"],
    "ETERNAL": ["zomato", "eternal"],
    "PAYTM": ["paytm", "one97"],
    "NYKAA": ["nykaa"],
    "INDIGO": ["indigo", "interglobe aviation"],
    "BEL": ["bharat electronics"],
    "HAL": ["hindustan aeronautics"],
    "TATAPOWER": ["tata power"],
    "VBL": ["varun beverages"],
    "DLF": ["dlf"]
}

def generate_ticker_map(master):
    ticker_map = {}
    for ticker, names in master.items():
        for name in names:
            base = name.lower().strip()
            variants = {
                base,
                base.replace(" ", ""),
                base.replace("&", "and"),
                base.replace("and", "&"),
                base.replace("-", ""),
            }
            for v in variants:
                ticker_map[v] = ticker
    return ticker_map

TICKERS = generate_ticker_map(MASTER_TICKERS)

def find_ticker(q):
    q = q.lower().strip()
    results = []
    for k, v in TICKERS.items():
        if q in k:
            results.append((k.upper(), v))
    return list(dict.fromkeys(results))[:8]


# align two series to common dates (handles MF NAV vs index date mismatch)
def align(s1, s2):
    s1 = s1.dropna(); s2 = s2.dropna()
    common = s1.index.intersection(s2.index)
    return s1.loc[common], s2.loc[common]


def compare_chart(df1, df2, n1, n2="Nifty 50"):
    p1, p2 = df1["Close"].dropna(), df2["Close"].dropna()
    p1, p2 = align(p1, p2)
    if len(p1) < 5 or len(p2) < 5:
        # not enough overlap, just show asset alone
        a = (p1 / p1.iloc[0] * 100).round(2)
        fig = go.Figure(go.Scatter(x=a.index, y=a, line=dict(color=C["accent"], width=2.5)))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#c8c8d8", height=340, margin=dict(l=0,r=0,t=30,b=0))
        return fig
    a = (p1 / p1.iloc[0] * 100).round(2)
    b = (p2 / p2.iloc[0] * 100).round(2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a.index, y=a, name=n1,
        line=dict(color=C["accent"], width=2.5),
        hovertemplate="%{y:.1f}<extra>"+n1+"</extra>"))
    fig.add_trace(go.Scatter(x=b.index, y=b, name=n2,
        line=dict(color="#9ca3af", width=2, dash="dot"),
        hovertemplate="%{y:.1f}<extra>"+n2+"</extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d8", height=360,
        xaxis=dict(showgrid=False, color="#6b6b80"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6b6b80", title="Start = 100"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02, x=0),
        margin=dict(l=0,r=0,t=36,b=0), hovermode="x unified")
    return fig


def dd_chart(df):
    p = df["Close"].dropna()
    dd = (p - p.cummax()) / p.cummax() * 100
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.round(2), fill="tozeroy",
        fillcolor="rgba(248,113,113,0.10)", line=dict(color=C["red"], width=1),
        hovertemplate="%{y:.1f}%<extra>Drawdown</extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d8", height=210,
        xaxis=dict(showgrid=False, color="#6b6b80"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6b6b80", ticksuffix="%"),
        margin=dict(l=0,r=0,t=10,b=0), hovermode="x unified")
    return fig


def dist_chart(returns):
    fig = go.Figure(go.Histogram(x=(returns*100).round(3), nbinsx=60,
        marker_color=C["accent"], opacity=0.8,
        hovertemplate="%{x:.2f}%: %{y} days<extra></extra>"))
    m = returns.mean()*100
    fig.add_vline(x=m, line_color=C["green"], line_width=1.5,
        annotation_text=f"Mean {m:.3f}%", annotation_font_color=C["green"],
        annotation_position="top right")
    fig.add_vline(x=0, line_color="#6b6b80", line_width=1)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d8", height=230,
        xaxis=dict(title="Daily Return (%)", showgrid=False, color="#6b6b80"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#6b6b80"),
        margin=dict(l=0,r=0,t=10,b=0))
    return fig


def bt_chart(res):
    sig, eq, tr, s = res["signals"], res["equity"], res["trades"], res["summary"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.62, 0.38], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=sig.index, y=sig["price"].round(2), name="Price",
        line=dict(color="#c8c8d8", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sig.index, y=sig["fast"].round(2),
        name=f"SMA {s['fast']}", line=dict(color=C["accent"], width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sig.index, y=sig["slow"].round(2),
        name=f"SMA {s['slow']}", line=dict(color=C["amber"], width=1.5)), row=1, col=1)
    if not tr.empty:
        fig.add_trace(go.Scatter(x=tr["entry_date"], y=tr["entry_price"], mode="markers",
            name="Buy", marker=dict(symbol="triangle-up", size=10, color=C["green"])), row=1, col=1)
        fig.add_trace(go.Scatter(x=tr["exit_date"], y=tr["exit_price"], mode="markers",
            name="Sell", marker=dict(symbol="triangle-down", size=10, color=C["red"])), row=1, col=1)
    fig.add_trace(go.Scatter(x=eq.index, y=eq["value"].round(0), fill="tozeroy",
        fillcolor="rgba(124,106,255,0.10)", line=dict(color=C["accent"], width=2),
        name="Portfolio ₹", hovertemplate="₹%{y:,.0f}<extra></extra>"), row=2, col=1)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d8", height=490,
        xaxis2=dict(showgrid=False, color="#6b6b80"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#6b6b80", tickprefix="₹"),
        yaxis2=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#6b6b80", tickprefix="₹"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02),
        margin=dict(l=0,r=0,t=36,b=0), hovermode="x unified")
    return fig


def ai_insights(m, bench_m, info, name, period):
    """
    Generates plain-English interpretation of the metrics.
    Uses Claude API so it reads like an analyst wrote it, not a template.
    Falls back to rule-based text if API is unavailable.
    """
    import requests as req

    cagr_pct  = round((m["cagr"] or 0) * 100, 1)
    nifty_cagr = round((bench_m["cagr"] or 0) * 100, 1) if bench_m else None
    sharpe    = m["sharpe"] or 0
    dd        = round((m["max_drawdown"] or 0) * 100, 1)
    vol       = round((m["volatility"] or 0) * 100, 1)
    tr        = round((m["total_return"] or 0) * 100, 1)

    prompt = f"""You are a concise financial analyst. Given these metrics for {name} over {period} years:
- Total Return: {tr}%
- CAGR: {cagr_pct}% (Nifty 50: {nifty_cagr}%)
- Sharpe Ratio: {sharpe}
- Max Drawdown: {dd}%
- Annualised Volatility: {vol}%
- Sector: {info.get('sector','N/A')}

Write 3-4 short bullet points interpreting these numbers for a retail investor.
Be direct and specific. Start each bullet with a verdict word like "Underperformed", "Strong", "Risky", "Solid", etc.
Keep each bullet under 20 words. No markdown headers, no intro sentence."""

    try:
        resp = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15
        )
        text = resp.json()["content"][0]["text"].strip()
        return text
    except:
        # rule-based fallback if API fails
        lines = []
        if nifty_cagr is not None:
            diff = cagr_pct - nifty_cagr
            lines.append(f"{'Outperformed' if diff > 0 else 'Underperformed'} Nifty 50 by {abs(diff):.1f}% CAGR over {period} years.")
        if sharpe > 1:    lines.append(f"Strong risk-adjusted returns — Sharpe of {sharpe:.2f} is above the 1.0 threshold.")
        elif sharpe > 0:  lines.append(f"Modest risk-adjusted returns — Sharpe of {sharpe:.2f}. Could do better per unit of risk.")
        else:             lines.append(f"Poor risk-adjusted returns — Sharpe of {sharpe:.2f}. A fixed deposit may have been safer.")
        if abs(dd) > 30:  lines.append(f"High drawdown risk — fell {abs(dd):.1f}% from peak at worst. Not for weak stomachs.")
        elif abs(dd) > 15:lines.append(f"Moderate drawdown of {abs(dd):.1f}%. Manageable if you held through the dip.")
        else:             lines.append(f"Relatively stable — max drawdown was only {abs(dd):.1f}%.")
        return "\n".join(f"• {l}" for l in lines)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 PortfolioIQ")
    st.caption("Analyse Indian stocks & mutual funds like a pro.")
    st.markdown("""
<div style="display:flex;gap:8px;margin-top:6px">
  <a href="https://github.com/atharva-pandeyy/portfolioiq" target="_blank"
     style="font-size:11px;color:#7C6AFF;text-decoration:none;background:rgba(124,106,255,.12);
            border:1px solid rgba(124,106,255,.3);padding:3px 10px;border-radius:20px">
    GitHub ↗
  </a>
  <a href="https://linkedin.com/in/atharva-pandey-600826322" target="_blank"
     style="font-size:11px;color:#3ECF8E;text-decoration:none;background:rgba(62,207,142,.10);
            border:1px solid rgba(62,207,142,.3);padding:3px 10px;border-radius:20px">
    LinkedIn ↗
  </a>
</div>""", unsafe_allow_html=True)
    st.caption("Built by Atharva Pandey")
    st.divider()
    mode_label = st.radio("Experience Mode", ["🟢 Beginner", "🔵 Pro"], index=0)
    pro = mode_label == "🔵 Pro"
    st.divider()
    section = st.radio("Section", ["Stock Analysis", "Mutual Fund", "My Portfolio"])
    st.divider()
    period = st.select_slider("Time Period", [1,2,3,5], value=3,
                              format_func=lambda x: f"{x}Y", key="period_sl")
    rf = st.slider("Risk-Free Rate (%)", 5.0, 9.0, 6.5, 0.1, key="rf_sl") / 100 if pro else 0.065
    st.divider()
    st.caption("Data: Yahoo Finance · mfapi.in")
    st.caption("Not investment advice.")


# ══════════════════════════════════════════════════════════════════════════════
# STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
q = none
if section == "Stock Analysis":
    badge_cls = "b-green" if not pro else "b-purple"
    badge_txt = "Beginner" if not pro else "Pro"
    st.markdown(f'# Stock Analysis &nbsp;<span class="badge {badge_cls}">{badge_txt} Mode</span>',
                unsafe_allow_html=True)

    # landing hook — only shows before any stock is loaded
    st.markdown("""
<div style="background:rgba(124,106,255,0.07);border:1px solid rgba(124,106,255,0.2);
        border-radius:10px;padding:16px 20px;margin-bottom:20px">
<div style="font-size:14px;font-weight:600;color:#e8e8f0;margin-bottom:6px">
What can you do here?
</div>
<div style="font-size:13px;color:#9ca3af;line-height:1.7">
📈 &nbsp;Compare any NSE stock against Nifty 50 — see if it actually beat the market<br>
📊 &nbsp;Get risk metrics: CAGR, Sharpe Ratio, Max Drawdown explained in plain English<br>
🔁 &nbsp;Backtest a moving average strategy on any stock with your own capital amount<br>
💼 &nbsp;Upload your portfolio CSV and track live P&L across all your holdings
</div>
</div>""", unsafe_allow_html=True)

    # quick-pick buttons that auto-load
    st.caption("Quick load:")
    qc = st.columns(5)
    for i, (name, tkr) in enumerate([
        ("HDFC Bank","HDFCBANK"),("Reliance","RELIANCE"),
        ("TCS","TCS"),("ITC","ITC"),("ONGC","ONGC")
    ]):
        with qc[i]:
            if st.button(name, key=f"quick_{i}", use_container_width=True):
                st.session_state["pending"] = tkr
                st.rerun()

    q = st.text_input(
    "Search by company name or NSE ticker",
    placeholder="e.g. HDFC Bank, ONGC, Sona BLW, ZOMATO …",
    key="s_q"
)

# ===== SMART TICKER RESOLUTION =====
def smart_resolve_ticker(q):
    q = q.strip().upper()

    # 1. Direct try
    df = get_stock(q, 1)
    if df is not None and not df.empty:
        return q

    # 2. Try NSE format
    df = get_stock(q + ".NS", 1)
    if df is not None and not df.empty:
        return q

    # 3. Yahoo suggestions
    sugg = suggest_tickers(q)
    if sugg:
        return sugg[0]["ticker"].replace(".NS", "").replace(".BO", "")

    return None


# ===== PRIORITY ENGINE (FIXED) =====
sel_ticker = None

# 1. Button click priority
if st.session_state.get("pending"):
    sel_ticker = st.session_state["pending"]

# 2. Search input
elif q:
    hits = find_ticker(q)

    if hits:
        lbls, tkrs = zip(*hits)
        ch = st.selectbox("Select company", list(lbls), key="s_sel")
        sel_ticker = tkrs[list(lbls).index(ch)]
        st.caption(f"Ticker: **{sel_ticker}**")
    else:
        resolved = smart_resolve_ticker(q)
        if resolved:
            sel_ticker = resolved
            st.caption(f"Auto-resolved to: **{sel_ticker}**")
        else:
            sel_ticker = q.strip().upper()
            st.caption(f"Searching directly for: **{sel_ticker}**")


nifty_on = st.checkbox("Compare vs Nifty 50", value=True, key="s_nifty")

period_changed = (
    st.session_state.s_df is not None
    and st.session_state.s_period != period
)

auto = bool(st.session_state.get("pending"))

# 🔥 FORCE pending usage
if st.session_state.get("pending"):
    sel_ticker = st.session_state["pending"]


if (st.button("Analyse →", type="primary", use_container_width=True, key="s_btn")
        and sel_ticker) or auto or period_changed:

    # ❌ NO pop() anymore
    t = st.session_state.get("pending") or sel_ticker or st.session_state.s_ticker

    if t:
        with st.spinner(f"Fetching {t}…"):
            df = get_stock(t, period)
            bench = get_nifty(period) if nifty_on else None
            info  = get_stock_info(t)

        if df is None or df.empty:
            st.error(f"Couldn't find data for **{t}**. Check for spelling errors or the exact NSE ticker.")

            with st.spinner("Looking for similar companies…"):
                sugg = suggest_tickers(t)

            if sugg:
                st.warning("Did you mean one of these?")
                cols = st.columns(min(len(sugg), 3))

                for i, s in enumerate(sugg):
                    with cols[i % 3]:
                        if st.button(
                            f"{s['name']}  ·  {s['ticker']}  ({s['exchange']})",
                            key=f"sg_{i}"
                        ):
                            st.session_state["pending"] = (
                                s["ticker"]
                                .replace(".NS", "")
                                .replace(".BO", "")
                            )
                            st.rerun()
            else:
                st.info("No matches found. Try a simpler name.")

        else:
            # ✅ SUCCESS → NOW CLEAR pending
            st.session_state.update({
                "s_df": df,
                "s_bench": bench,
                "s_bname": "Nifty 50",
                "s_info": info,
                "s_ticker": t,
                "s_period": period,
                "pending": None
            })

    # render
    if st.session_state.s_df is not None:
        df    = st.session_state.s_df
        bench = st.session_state.s_bench
        bn    = st.session_state.s_bname
        info  = st.session_state.s_info
        m     = get_all(df, rf=rf)
        r     = daily_returns(df)

        st.markdown(f"### {info.get('name', st.session_state.s_ticker)}")
        c1, c2, c3 = st.columns(3)
        c1.caption(f"Sector: **{info.get('sector','N/A')}**")
        c2.caption(f"Industry: **{info.get('industry','N/A')}**")
        if info.get("price"): c3.caption(f"LTP: **₹{info['price']:,.2f}**")
        if info.get("52h"):   st.caption(f"52W: ₹{info.get('52l',0):,.2f} – ₹{info['52h']:,.2f}")
        st.divider()

        if not pro:
            c1, c2, c3 = st.columns(3)
            with c1: card("Total Return", pf(m["total_return"]), clr(m["total_return"]), f"Over {period}Y")
            with c2: card("CAGR", pf(m["cagr"]), clr(m["cagr"]), "Per year average")
            with c3: card("Max Drawdown", pf(m["max_drawdown"]), "r", "Worst fall from peak")
            st.markdown('<div class="sh">Price vs Nifty 50 (Both start at 100)</div>', unsafe_allow_html=True)
            if bench is not None: st.caption("Purple = stock   ·   Grey dotted = Nifty 50")
            st.plotly_chart(compare_chart(df, bench if bench is not None else df,
                            info.get("name","Stock"), bn), use_container_width=True)
            with st.expander("📖 What do these numbers mean?"):
                end_val = 100000 * (1 + (m["total_return"] or 0))
                st.markdown(f"""
**Total Return ({pf(m['total_return'])})** — ₹1,00,000 invested at the start is now ₹{end_val:,.0f}.

**CAGR ({pf(m['cagr'])})** — The "effective" yearly growth. Compare to FD ~7%, Nifty avg ~12–13%, good stock 15–25%.

**Max Drawdown ({pf(m['max_drawdown'])})** — Worst paper loss from a peak. This is the pain you'd have felt holding through the dip.

**Chart** — Purple above grey = beat the market. Both start at 100 for fair comparison.
                """)

            # AI insights — works in both modes
            bench_m = get_all(bench) if bench is not None and not bench.empty else None
            with st.expander("🧠 AI Analyst Insights — what do these numbers actually mean?", expanded=True):
                with st.spinner("Generating insights…"):
                    insight_text = ai_insights(m, bench_m, info, info.get("name","this stock"), period)
                st.markdown(f"""
<div style="background:rgba(124,106,255,0.06);border:1px solid rgba(124,106,255,0.18);
            border-radius:8px;padding:14px 18px;font-size:13px;line-height:1.8;color:#c8c8d8">
{insight_text.replace(chr(10), '<br>')}
</div>""", unsafe_allow_html=True)
                st.caption("Powered by Claude · For educational purposes only, not investment advice.")

        else:
            cols = st.columns(5)
            data = [
                ("Total Return", pf(m["total_return"]), clr(m["total_return"]), ""),
                ("CAGR", pf(m["cagr"]), clr(m["cagr"]), f"{period}Y annualised"),
                ("Sharpe Ratio", f"{m['sharpe']:.2f}" if m["sharpe"] else "N/A",
                 "g" if m["sharpe"] and m["sharpe"]>1 else "a" if m["sharpe"] and m["sharpe"]>0 else "r", ""),
                ("Max Drawdown", pf(m["max_drawdown"]), "r", ""),
                ("Volatility", f"{m['volatility']*100:.1f}%" if m["volatility"] else "N/A", "a", "annualised"),
            ]
            for i, (l,v,c,s) in enumerate(data):
                with cols[i]: card(l,v,c,s)

            if bench is not None and not bench.empty:
                br = daily_returns(bench.resample("B").ffill())
                ab = alpha_beta(r, br)
                c1, c2 = st.columns(2)
                with c1: card("Alpha", f"{ab['alpha']*100:+.2f}%" if ab["alpha"] else "N/A",
                              clr(ab["alpha"]), "vs Nifty 50")
                with c2: card("Beta", f"{ab['beta']:.2f}" if ab["beta"] else "N/A",
                              "a", "1.0 = moves with market")
            st.divider()

            st.markdown('<div class="sh">Price vs Nifty 50 (Both start at 100)</div>', unsafe_allow_html=True)
            if bench is not None: st.caption("Purple = stock   ·   Grey dotted = Nifty 50")
            st.plotly_chart(compare_chart(df, bench if bench is not None else df,
                            info.get("name","Stock"), bn), use_container_width=True)

            ca, cb = st.columns(2)
            with ca:
                st.markdown('<div class="sh">Drawdown</div>', unsafe_allow_html=True)
                st.plotly_chart(dd_chart(df), use_container_width=True)
            with cb:
                st.markdown('<div class="sh">Returns Distribution</div>', unsafe_allow_html=True)
                st.plotly_chart(dist_chart(r), use_container_width=True)
            st.divider()

            st.markdown('<div class="sh">SMA Crossover Backtest</div>', unsafe_allow_html=True)
            st.caption("Buy when fast MA > slow MA. Sell when it crosses below.")
            bc1, bc2, bc3 = st.columns(3)
            with bc1: fw = st.slider("Fast SMA", 5, 50, 20, key="fw")
            with bc2: sw = st.slider("Slow SMA", 20, 200, 50, key="sw")
            with bc3: cap = st.number_input("Capital (₹)", 10000, 10000000, 100000, 10000, key="cap")

            if fw >= sw:
                st.warning("Fast SMA must be < Slow SMA.")
            else:
                res = sma_backtest(df, fw, sw, capital=cap)
                s = res["summary"]
                m1, m2, m3, m4 = st.columns(4)
                with m1: card("Strategy Return", f"{s['strat_return']:+.1f}%",
                              "g" if s["strat_return"]>0 else "r")
                with m2: card("Buy & Hold", f"{s['bah_return']:+.1f}%",
                              "g" if s["bah_return"]>0 else "r")
                with m3: card("Win Rate", f"{s['win_rate']:.0f}%",
                              "g" if s["win_rate"]>=50 else "a")
                with m4: card("Total Trades", str(s["total_trades"]), "w",
                              f"{s['wins']} winning")
                st.plotly_chart(bt_chart(res), use_container_width=True)
                if not res["trades"].empty:
                    with st.expander("Trade Log"):
                        td = res["trades"].copy()
                        for col in ["entry_date","exit_date"]:
                            td[col] = td[col].dt.strftime("%d %b %Y")
                        td["return_pct"] = td["return_pct"].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(td, use_container_width=True, hide_index=True)

            st.divider()
            bench_m = get_all(bench) if bench is not None and not bench.empty else None
            with st.expander("🧠 AI Analyst Insights", expanded=False):
                with st.spinner("Generating…"):
                    insight_text = ai_insights(m, bench_m, info, info.get("name","this stock"), period)
                st.markdown(f"""
<div style="background:rgba(124,106,255,0.06);border:1px solid rgba(124,106,255,0.18);
            border-radius:8px;padding:14px 18px;font-size:13px;line-height:1.8;color:#c8c8d8">
{insight_text.replace(chr(10), '<br>')}
</div>""", unsafe_allow_html=True)
                st.caption("Powered by Claude · Not investment advice.")


# ══════════════════════════════════════════════════════════════════════════════
# MUTUAL FUND
# ══════════════════════════════════════════════════════════════════════════════
elif section == "Mutual Fund":
    badge_cls = "b-green" if not pro else "b-purple"
    badge_txt = "Beginner" if not pro else "Pro"
    st.markdown(f'# Mutual Fund &nbsp;<span class="badge {badge_cls}">{badge_txt} Mode</span>',
                unsafe_allow_html=True)

    q = st.text_input("Search fund by name",
                      placeholder="e.g. Mirae Asset Largecap, Parag Parikh Flexi …", key="mf_q")
    if q:
        with st.spinner("Searching…"):
            results = search_mf(q)
        valid = [r for r in results if r.get("schemeCode") and str(r["schemeCode"]) != "0"]
        if not valid:
            st.error("No funds found — try a shorter or different name.")
        else:
            opts = {r["schemeName"]: str(r["schemeCode"]) for r in valid[:20]}
            sel = st.selectbox("Select fund", list(opts.keys()), key="mf_sel")
            sc  = opts[sel]

            auto_yf, auto_name = detect_benchmark(sel)
            st.markdown(f'<span class="btag">Auto benchmark: <strong>{auto_name or "None (debt)"}</strong></span>',
                        unsafe_allow_html=True)

            BMAP = {
                "Auto-detected": (auto_yf, auto_name),
                "Nifty 50":      ("^NSEI",     "Nifty 50"),
                "Nifty Midcap 50":("^NSMIDCP", "Nifty Midcap 50"),
                "Nifty Smallcap 100":("^CNXSC","Nifty Smallcap 100"),
                "Nifty Bank":    ("^NSEBANK",  "Nifty Bank"),
                "Nifty IT":      ("^CNXIT",    "Nifty IT"),
                "Nifty Pharma":  ("^CNXPHARMA","Nifty Pharma"),
                "None":          (None, None),
            }
            bch = st.selectbox("Compare against", list(BMAP.keys()), key="mf_bch")
            cyf, cname = BMAP[bch]

            if st.button("Analyse Fund →", type="primary", use_container_width=True, key="mf_btn"):
                with st.spinner("Fetching…"):
                    mf_df = get_mf_nav(sc, period)
                    mf_b  = get_index(cyf, period) if cyf else None
                if mf_df is None or mf_df.empty:
                    st.error(f"Couldn't get NAV data (code: {sc}). Try a different plan variant (Direct/Regular, Growth/IDCW).")
                else:
                    st.session_state.update({
                        "mf_df": mf_df, "mf_bench": mf_b, "mf_bname": cname or "Benchmark",
                        "mf_name": sel, "mf_code": sc, "mf_byf": cyf, "mf_period": period,
                    })

    # period changed auto-reload
    if (st.session_state.mf_df is not None and
            st.session_state.mf_period != period and st.session_state.mf_code):
        with st.spinner(f"Reloading for {period}Y…"):
            mf_df = get_mf_nav(st.session_state.mf_code, period)
            mf_b  = get_index(st.session_state.mf_byf, period) if st.session_state.mf_byf else None
        if mf_df is not None and not mf_df.empty:
            st.session_state.mf_df    = mf_df
            st.session_state.mf_bench = mf_b
            st.session_state.mf_period = period

    if st.session_state.mf_df is not None:
        df    = st.session_state.mf_df
        bench = st.session_state.mf_bench
        bn    = st.session_state.mf_bname
        name  = st.session_state.mf_name
        m     = get_all(df, rf=rf)

        st.markdown(f"### {name}")
        st.divider()

        if not pro:
            c1, c2, c3 = st.columns(3)
            with c1: card("Total Return", pf(m["total_return"]), clr(m["total_return"]), f"Over {period}Y")
            with c2: card("CAGR", pf(m["cagr"]), clr(m["cagr"]), "Per year")
            with c3: card("Max Drawdown", pf(m["max_drawdown"]), "r", "Worst fall")
        else:
            cols = st.columns(4)
            with cols[0]: card("Total Return", pf(m["total_return"]), clr(m["total_return"]))
            with cols[1]: card("CAGR", pf(m["cagr"]), clr(m["cagr"]))
            with cols[2]:
                sh = m["sharpe"]
                card("Sharpe Ratio", f"{sh:.2f}" if sh else "N/A",
                     "g" if sh and sh>1 else "a")
            with cols[3]: card("Max Drawdown", pf(m["max_drawdown"]), "r")

        st.markdown(f'<div class="sh">NAV vs {bn} (Both start at 100)</div>', unsafe_allow_html=True)
        if bench is not None and not bench.empty:
            st.caption(f"Purple = fund   ·   Grey dotted = {bn}")
            st.plotly_chart(compare_chart(df, bench, name[:45], bn), use_container_width=True)
        else:
            n = (df["Close"] / df["Close"].iloc[0] * 100).round(2)
            fig = go.Figure(go.Scatter(x=n.index, y=n, line=dict(color=C["accent"], width=2.5)))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#c8c8d8", height=340, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)

        if pro:
            ca, cb = st.columns(2)
            with ca:
                st.markdown('<div class="sh">Drawdown</div>', unsafe_allow_html=True)
                st.plotly_chart(dd_chart(df), use_container_width=True)
            with cb:
                st.markdown('<div class="sh">Returns Distribution</div>', unsafe_allow_html=True)
                st.plotly_chart(dist_chart(daily_returns(df)), use_container_width=True)

        if not pro:
            with st.expander("📖 What do these numbers mean?"):
                st.markdown(f"""
**CAGR ({pf(m['cagr'])})** — Compare to FD ~7%, Nifty avg ~12–13%, good active fund ~14–18%.

**Max Drawdown** — During COVID (Mar 2020) most funds fell 30–40%. This is the worst pain you'd have felt.

**Chart** — If purple stays above grey, this fund beat {bn}. Most active funds don't do this consistently.
                """)


# ══════════════════════════════════════════════════════════════════════════════
# MY PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif section == "My Portfolio":
    badge_cls = "b-green" if not pro else "b-purple"
    badge_txt = "Beginner" if not pro else "Pro"
    st.markdown(f'# My Portfolio &nbsp;<span class="badge {badge_cls}">{badge_txt} Mode</span>',
                unsafe_allow_html=True)

    with st.expander("📋 How to upload", expanded=True):
        st.markdown("""Upload a CSV with columns: `ticker`, `shares`, `avg_buy_price`
```
ticker,shares,avg_buy_price
RELIANCE,10,2450.00
HDFCBANK,5,1580.00
SONACOMS,20,520.00
```""")

    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="pf_up")
    if uploaded:
        holdings, err = load_csv(uploaded)
        if err:
            st.error(f"CSV error: {err}")
        elif st.button("Load →", type="primary", use_container_width=True, key="pf_btn"):
            with st.spinner("Fetching live prices…"):
                prices = {t: (get_stock_info(t) or {}).get("price")
                          for t in holdings["ticker"]}
                prices = {k: v for k, v in prices.items() if v}
            st.session_state.pf_h = holdings
            st.session_state.pf_p = prices

    if st.session_state.pf_h is not None:
        pf_df = portfolio_pnl(st.session_state.pf_h, st.session_state.pf_p)
        if pf_df.empty:
            st.error("Couldn't fetch prices for any tickers.")
        else:
            ti = pf_df["Invested"].sum(); tv = pf_df["Value"].sum()
            tp = pf_df["P&L"].sum(); tp_pct = tp/ti*100 if ti else 0
            st.divider()
            c1,c2,c3,c4 = st.columns(4)
            with c1: card("Total Invested",  f"₹{ti:,.0f}", "w")
            with c2: card("Current Value",   f"₹{tv:,.0f}", "w")
            with c3: card("Total P&L",       f"₹{tp:+,.0f}", "g" if tp>=0 else "r")
            with c4: card("P&L %",           f"{tp_pct:+.2f}%", "g" if tp_pct>=0 else "r")
            st.divider()

            ct, cp = st.columns([3,2])
            with ct:
                st.markdown('<div class="sh">Holdings</div>', unsafe_allow_html=True)
                d = pf_df.copy()
                d["P&L %"] = d["P&L %"].apply(lambda x: f"{x:+.2f}%")
                st.dataframe(d, use_container_width=True, hide_index=True)
            with cp:
                st.markdown('<div class="sh">Allocation</div>', unsafe_allow_html=True)
                fig = px.pie(pf_df, values="Value", names="Ticker",
                             color_discrete_sequence=px.colors.sequential.Purples_r, hole=0.45)
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#c8c8d8",
                                  height=300, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="sh">P&L by Stock</div>', unsafe_allow_html=True)
            ps = pf_df.sort_values("P&L %")
            fig = go.Figure(go.Bar(
                x=ps["Ticker"], y=ps["P&L"],
                marker_color=[C["green"] if x>=0 else C["red"] for x in ps["P&L"]],
                text=ps["P&L %"].apply(lambda x: f"{x:+.1f}%"), textposition="outside",
                hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>"))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#c8c8d8", height=300,
                xaxis=dict(showgrid=False, color="#6b6b80"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                           color="#6b6b80", tickprefix="₹"),
                margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)

            # portfolio vs nifty — compare total portfolio value growth vs benchmark
            st.markdown('<div class="sh">Portfolio vs Nifty 50</div>', unsafe_allow_html=True)
            st.caption("How your overall portfolio performed vs just putting it all in a Nifty 50 index fund.")
            try:
                bench_pf = get_nifty(3)
                if bench_pf is not None and not bench_pf.empty:
                    # weighted average of individual stock returns as proxy
                    weights = pf_df["Invested"] / pf_df["Invested"].sum()
                    # fetch individual stock data and compute weighted returns
                    stock_curves = []
                    for _, row in pf_df.iterrows():
                        sdf = get_stock(row["Ticker"], 3)
                        if sdf is not None and not sdf.empty:
                            norm = (sdf["Close"] / sdf["Close"].iloc[0]) * 100
                            stock_curves.append(norm * weights[row.name] if row.name < len(weights) else norm * 0)
                    if stock_curves:
                        pf_curve = sum(stock_curves)
                        pf_curve = pf_curve / pf_curve.iloc[0] * 100
                        bp = bench_pf["Close"].dropna()
                        bp = (bp / bp.iloc[0] * 100)
                        common = pf_curve.index.intersection(bp.index)
                        if len(common) > 10:
                            fig2 = go.Figure()
                            fig2.add_trace(go.Scatter(x=common, y=pf_curve.loc[common].round(2),
                                name="Your Portfolio", line=dict(color=C["accent"], width=2.5)))
                            fig2.add_trace(go.Scatter(x=common, y=bp.loc[common].round(2),
                                name="Nifty 50", line=dict(color="#9ca3af", width=2, dash="dot")))
                            fig2.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#c8c8d8", height=300,
                                xaxis=dict(showgrid=False, color="#6b6b80"),
                                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                                           color="#6b6b80", title="Start = 100"),
                                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02),
                                margin=dict(l=0,r=0,t=36,b=0), hovermode="x unified")
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("Not enough overlapping data for portfolio vs Nifty chart.")
            except Exception:
                st.info("Portfolio vs Nifty chart unavailable — try again after loading.")
