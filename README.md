# StockPulse

A runnable Python dashboard for daily stock updates. It has a watchlist, delayed price data, performance overview, 20/50-day moving averages, RSI, volume chart, CSV downloads, daily report, and in-session price alerts.

## Run it

1. Install Python 3.10 or newer.
2. In this folder, install the packages:

   ```powershell
   python -m pip install -r requirement.txt
   ```

3. Start the app:

   ```powershell
   python -m streamlit run app.py
   ```

Open the local address shown in the terminal, usually `http://localhost:8501`.

## Tickers

Use Yahoo Finance symbols. Examples: `AAPL`, `MSFT`, `NVDA`; Indian NSE symbols generally use `.NS`, such as `RELIANCE.NS`, `TCS.NS`, and `INFY.NS`.

## Production additions

For a real deployed app, replace the demonstration price feed with a licensed provider appropriate for your market, persist watchlists and alerts in a database, authenticate users, run alert checks on a scheduler, and send notifications through email/push/SMS. Market data can be delayed or unavailable; this project is for learning, not financial advice.
