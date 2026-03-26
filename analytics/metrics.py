# analytics/metrics.py
# wrote these myself while studying for CFA L1 - atharva

import pandas as pd
import numpy as np


def daily_returns(df, col="Close"):
    return df[col].pct_change().dropna()


def cagr(df, col="Close"):
    p = df[col].dropna()
    if len(p) < 2: return None
    years = (p.index[-1] - p.index[0]).days / 365.25
    return (p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1 if years > 0 else None


def sharpe(returns, rf=0.065):
    # rf = risk free rate, using ~6.5% (Indian 10Y gsec approx)
    if returns.empty or returns.std() == 0: return None
    daily_rf = rf / 252
    return round(((returns - daily_rf).mean() / returns.std()) * np.sqrt(252), 2)


def max_drawdown(df, col="Close"):
    p = df[col].dropna()
    dd = (p - p.cummax()) / p.cummax()
    return round(dd.min(), 4)


def volatility(returns):
    return round(returns.std() * np.sqrt(252), 4) if not returns.empty else None


def get_all(df, col="Close", rf=0.065):
    r = daily_returns(df, col)
    p = df[col].dropna()
    total = round(p.iloc[-1] / p.iloc[0] - 1, 4) if len(p) > 1 else None
    return {
        "total_return": total,
        "cagr":         cagr(df, col),
        "sharpe":       sharpe(r, rf),
        "max_drawdown": max_drawdown(df, col),
        "volatility":   volatility(r),
        "start":        round(p.iloc[0], 2),
        "end":          round(p.iloc[-1], 2),
    }


def to_100(df, col="Close"):
    # index to 100 at start - makes comparing two assets fair
    p = df[col].dropna()
    return (p / p.iloc[0]) * 100


def alpha_beta(asset_r, bench_r):
    df = pd.concat([asset_r, bench_r], axis=1).dropna()
    if len(df) < 30: return {"alpha": None, "beta": None}
    df.columns = ["a", "b"]
    cov = np.cov(df["a"], df["b"])
    beta = cov[0, 1] / cov[1, 1]
    alpha = (df["a"].mean() - beta * df["b"].mean()) * 252
    return {"alpha": round(alpha, 4), "beta": round(beta, 4)}


def sma_backtest(df, fast=20, slow=50, col="Close", capital=100000):
    p = df[col].dropna().copy()
    bt = pd.DataFrame({"price": p})
    bt["fast"] = p.rolling(fast).mean()
    bt["slow"] = p.rolling(slow).mean()
    bt["signal"] = (bt["fast"] > bt["slow"]).astype(int)
    bt["cross"] = bt["signal"].diff()

    cash, shares, in_trade = capital, 0, False
    entry_date = entry_price = None
    trades, curve = [], []

    for date, row in bt.iterrows():
        if pd.isna(row["slow"]):
            curve.append({"date": date, "value": cash})
            continue

        if row["cross"] == 1 and not in_trade:
            shares = cash / row["price"]
            cash = 0
            entry_date, entry_price = date, row["price"]
            in_trade = True

        elif row["cross"] == -1 and in_trade:
            cash = shares * row["price"]
            trades.append({
                "entry_date": entry_date, "entry_price": round(entry_price, 2),
                "exit_date": date,        "exit_price":  round(row["price"], 2),
                "return_pct": round((row["price"] / entry_price - 1) * 100, 2),
            })
            shares, in_trade = 0, False

        val = (shares * row["price"]) if in_trade else cash
        curve.append({"date": date, "value": val + cash if in_trade else cash})

    # close open position at end
    if in_trade:
        fp = bt["price"].iloc[-1]
        cash = shares * fp
        trades.append({
            "entry_date": entry_date, "entry_price": round(entry_price, 2),
            "exit_date": bt.index[-1], "exit_price": round(fp, 2),
            "return_pct": round((fp / entry_price - 1) * 100, 2),
        })

    eq = pd.DataFrame(curve).set_index("date")
    tr = pd.DataFrame(trades) if trades else pd.DataFrame()
    final = eq["value"].iloc[-1]
    n_yrs = (p.index[-1] - p.index[0]).days / 365.25

    wins = len(tr[tr["return_pct"] > 0]) if not tr.empty else 0

    return {
        "equity": eq, "trades": tr,
        "signals": bt[["price", "fast", "slow", "signal"]],
        "summary": {
            "strat_return":  round((final / capital - 1) * 100, 2),
            "bah_return":    round((p.iloc[-1] / p.iloc[0] - 1) * 100, 2),
            "strat_cagr":    round((final / capital) ** (1/n_yrs) - 1, 4) if n_yrs > 0 else None,
            "bah_cagr":      round((p.iloc[-1] / p.iloc[0]) ** (1/n_yrs) - 1, 4) if n_yrs > 0 else None,
            "total_trades":  len(tr),
            "wins":          wins,
            "win_rate":      round(wins / len(tr) * 100, 1) if not tr.empty else 0,
            "fast": fast, "slow": slow,
        }
    }


def portfolio_pnl(holdings, prices):
    # holdings = df with ticker, shares, avg_buy_price
    rows = []
    for _, h in holdings.iterrows():
        cp = prices.get(h["ticker"])
        if not cp: continue
        inv = h["shares"] * h["avg_buy_price"]
        val = h["shares"] * cp
        rows.append({
            "Ticker": h["ticker"],
            "Shares": h["shares"],
            "Avg Buy": round(h["avg_buy_price"], 2),
            "LTP": round(cp, 2),
            "Invested": round(inv, 2),
            "Value": round(val, 2),
            "P&L": round(val - inv, 2),
            "P&L %": round((val - inv) / inv * 100, 2) if inv else 0,
        })
    return pd.DataFrame(rows)