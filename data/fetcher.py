# data/fetcher.py
# handles all data pulling - stocks from yfinance, MFs from mfapi.in

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta


def _date_range(years):
    end = datetime.today()
    return end - timedelta(days=years * 365), end


def get_stock(ticker, years=3):
    t = ticker.strip().upper()
    if not (t.endswith(".NS") or t.endswith(".BO")):
        t += ".NS"
    start, end = _date_range(years)
    try:
        df = yf.download(t, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).normalize()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except:
        return None


def get_index(yf_ticker, years=3):
    # fetch index (nifty 50, bank nifty etc) and fill weekends so it aligns with MF NAVs
    start, end = _date_range(years)
    try:
        df = yf.download(yf_ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Close"]].dropna()
        df.index = pd.to_datetime(df.index).normalize()
        df = df[~df.index.duplicated(keep="last")]
        idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
        return df.reindex(idx).ffill().rename_axis("Date")
    except:
        return None


def get_nifty(years=3):
    return get_index("^NSEI", years)


def get_stock_info(ticker):
    t = ticker.strip().upper()
    if not (t.endswith(".NS") or t.endswith(".BO")):
        t += ".NS"

    result = {"name": ticker.replace(".NS","").replace(".BO",""),
              "sector": "N/A", "industry": "N/A",
              "price": None, "52h": None, "52l": None, "pe": None}

    tk = yf.Ticker(t)

    # fast_info is lightweight and reliable on Streamlit Cloud — no rate limiting
    try:
        fi = tk.fast_info
        result["price"] = round(fi.last_price, 2) if fi.last_price else None
        result["52h"]   = round(fi.fifty_two_week_high, 2) if fi.fifty_two_week_high else None
        result["52l"]   = round(fi.fifty_two_week_low,  2) if fi.fifty_two_week_low  else None
    except:
        pass

    # .info is heavier — try for name/sector/industry but don't block if it fails
    try:
        info = tk.info
        # only use if we got a real response (empty/throttled responses have <5 keys)
        if info and len(info) > 5:
            result["name"]     = info.get("longName")  or result["name"]
            result["sector"]   = info.get("sector")    or "N/A"
            result["industry"] = info.get("industry")  or "N/A"
            result["pe"]       = info.get("trailingPE")
            if not result["price"]:
                result["price"] = info.get("currentPrice")
    except:
        pass

    return result


def suggest_tickers(query):
    # fallback when user types something we don't recognise
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&region=IN&quotesCount=8&newsCount=0"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8).json()
        out = []
        for q in data.get("quotes", []):
            sym, name, exch = q.get("symbol",""), q.get("longname") or q.get("shortname",""), q.get("exchange","")
            if sym and name and exch in ("NSI", "BSE", "NSE"):
                out.append({"ticker": sym, "name": name, "exchange": "NSE" if exch in ("NSI","NSE") else "BSE"})
        return out[:6]
    except:
        return []


# ── mutual fund stuff ─────────────────────────────────────────────────────────

# maps fund type keywords → benchmark index
BENCHMARKS = [
    (["smallcap","small cap","small-cap","250"],   ("^CNXSC",     "Nifty Smallcap 100")),
    (["midcap","mid cap","mid-cap","150"],          ("^NSMIDCP",   "Nifty Midcap 50")),
    (["large & mid","large and mid"],              ("^NSEI",      "Nifty 50")),
    (["flexi","multi","diversified"],              ("^NSEI",      "Nifty 50")),
    (["largecap","large cap","bluechip","top 100"],("^NSEI",      "Nifty 50")),
    (["index","nifty 50","nifty50"],               ("^NSEI",      "Nifty 50")),
    (["banking","bank","finserv"],                 ("^NSEBANK",   "Nifty Bank")),
    (["pharma","health"],                          ("^CNXPHARMA", "Nifty Pharma")),
    (["it","technology","tech"],                   ("^CNXIT",     "Nifty IT")),
    (["infra","infrastructure"],                   ("^CNXINFRA",  "Nifty Infra")),
    (["fmcg","consumption"],                       ("^CNXFMCG",   "Nifty FMCG")),
    (["elss","tax","equity linked"],               ("^NSEI",      "Nifty 50")),
    (["hybrid","balanced"],                        ("^NSEI",      "Nifty 50")),
    (["gilt","debt","bond","liquid","overnight"],   (None,         None)),
]

def detect_benchmark(fund_name):
    n = fund_name.lower()
    for keywords, bench in BENCHMARKS:
        if any(k in n for k in keywords):
            return bench
    return ("^NSEI", "Nifty 50")


def search_mf(query):
    try:
        r = requests.get(f"https://api.mfapi.in/mf/search?q={query}", timeout=10)
        return r.json()
    except:
        return []


def get_mf_nav(scheme_code, years=3):
    try:
        r = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=10).json()
        df = pd.DataFrame(r.get("data", []))
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
        df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
        df = df.dropna().sort_values("date").set_index("date").rename(columns={"nav": "Close"})
        cutoff = datetime.today() - timedelta(days=years * 365)
        df = df[df.index >= cutoff][["Close"]]
        df.index = pd.to_datetime(df.index).normalize()
        df = df[~df.index.duplicated(keep="last")]
        return df if not df.empty else None
    except:
        return None


def load_csv(file):
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()
        needed = {"ticker", "shares", "avg_buy_price"}
        if not needed.issubset(df.columns):
            return None, f"Need columns: {needed}"
        df["ticker"] = df["ticker"].str.strip().str.upper()
        df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
        df["avg_buy_price"] = pd.to_numeric(df["avg_buy_price"], errors="coerce")
        return df.dropna(), None
    except Exception as e:
        return None, str(e)
