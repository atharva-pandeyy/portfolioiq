# PortfolioIQ 📊
### Indian Stock & Mutual Fund Analytics Dashboard

A publicly hosted financial analytics tool for Indian equity and mutual fund investors. Built with Python and Streamlit.

**Live Demo:** [Add your Streamlit Cloud URL here after deployment]

---

## Features

### Stock Analysis
- Historical price performance vs Nifty 50 benchmark (indexed to 100)
- Key risk-return metrics: CAGR, Sharpe Ratio, Max Drawdown, Annualised Volatility
- Alpha and Beta calculation vs Nifty 50
- Daily returns distribution histogram
- **SMA Crossover Backtest** — test any short/long moving average strategy with configurable capital, view trade log and equity curve

### Mutual Fund Analysis
- Search any Indian mutual fund by name (powered by mfapi.in)
- Historical NAV performance vs Nifty 50 benchmark
- Same risk-return metric suite as stock analysis

### My Portfolio
- Upload your holdings as a CSV (ticker, shares, avg_buy_price)
- Live P&L calculation using current market prices
- Portfolio allocation pie chart
- P&L breakdown by holding

---

## Tech Stack

| Layer | Tool |
|---|---|
| UI / App framework | Streamlit |
| Stock data | yfinance (NSE/BSE via Yahoo Finance) |
| Mutual fund data | [mfapi.in](https://www.mfapi.in/) — free Indian MF NAV API |
| Data processing | pandas, numpy |
| Charts | Plotly |
| Deployment | Streamlit Cloud |

---

## Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/portfolioiq.git
cd portfolioiq

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

---

## Portfolio CSV Format

To use the "My Portfolio" tab, upload a CSV with this exact format:

```csv
ticker,shares,avg_buy_price
RELIANCE,10,2450.00
HDFCBANK,5,1580.00
INFY,8,1420.00
TCS,3,3800.00
```

Use NSE ticker symbols (same as what you'd search on NSE India website).

---

## About

Built by **Atharva Pandey** — a finance-oriented IT engineering student at Thakur College of Engineering & Technology, Mumbai.

This project was built to demonstrate applied financial analytics using real Indian market data — combining quantitative finance concepts (Sharpe ratio, drawdown analysis, systematic strategy backtesting) with production-grade software engineering.

**Connect:** [linkedin.com/in/atharva-pandey-600826322](https://linkedin.com/in/atharva-pandey-600826322)

---

## Disclaimer

This tool is for educational and analytical purposes only. It does not constitute investment advice. Past performance of any backtested strategy does not guarantee future results.