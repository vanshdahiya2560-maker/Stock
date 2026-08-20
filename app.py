"""StockPulse — a small, runnable daily stock-market dashboard."""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(page_title="StockPulse", page_icon="📈", layout="wide")

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "RELIANCE.NS"]


@st.cache_data(ttl=900, show_spinner=False)
def history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Get daily OHLCV prices, cached for 15 minutes."""
    frame = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    if frame.empty:
        raise ValueError(f"No price history found for {symbol}. Check the ticker symbol.")
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame.dropna(subset=["Close"])


def indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    close = result["Close"]
    result["SMA 20"] = close.rolling(20).mean()
    result["SMA 50"] = close.rolling(50).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    result["RSI 14"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))
    result["Daily change %"] = close.pct_change() * 100
    return result


def snapshot(symbol: str) -> dict:
    frame = indicators(history(symbol, "6mo"))
    last, prior = frame.iloc[-1], frame.iloc[-2]
    return {
        "Symbol": symbol.upper(),
        "Price": float(last["Close"]),
        "Change %": float((last["Close"] / prior["Close"] - 1) * 100),
        "Volume": int(last["Volume"]),
        "RSI": float(last["RSI 14"]) if pd.notna(last["RSI 14"]) else None,
        "20-day trend": "Bullish" if last["Close"] >= last["SMA 20"] else "Bearish",
    }


def money(value: float) -> str:
    return f"{value:,.2f}"


if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_WATCHLIST.copy()
if "alerts" not in st.session_state:
    st.session_state.alerts = []

st.title("📈 StockPulse")
st.caption("Daily prices, market trends, watchlists, reports, and price alerts. Data is delayed and for education only—not investment advice.")

with st.sidebar:
    st.header("Watchlist")
    symbol = st.text_input("Add a ticker", placeholder="e.g. TCS.NS or AAPL").strip().upper()
    if st.button("Add ticker", width="stretch") and symbol:
        if symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(symbol)
            st.cache_data.clear()
            st.rerun()
    selected = st.multiselect("Your tickers", st.session_state.watchlist, default=st.session_state.watchlist)
    st.session_state.watchlist = selected
    if st.button("Refresh market data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

if not st.session_state.watchlist:
    st.info("Add at least one ticker in the sidebar to begin.")
    st.stop()

tab_overview, tab_stock, tab_alerts, tab_report = st.tabs(["Overview", "Stock detail", "Alerts", "Daily report"])

with tab_overview:
    cards, failures = [], []
    for ticker in st.session_state.watchlist:
        try:
            cards.append(snapshot(ticker))
        except Exception as exc:
            failures.append(f"{ticker}: {exc}")
    if cards:
        table = pd.DataFrame(cards)
        st.dataframe(
            table.style.format({"Price": "{:.2f}", "Change %": "{:+.2f}%", "Volume": "{:,.0f}", "RSI": "{:.1f}"}),
            width="stretch",
            hide_index=True,
        )
        st.bar_chart(table.set_index("Symbol")["Change %"], color="#20c997")
    for error in failures:
        st.warning(error)

with tab_stock:
    ticker = st.selectbox("Ticker", st.session_state.watchlist)
    period = st.select_slider("History", options=["1mo", "3mo", "6mo", "1y", "2y"], value="6mo")
    try:
        prices = indicators(history(ticker, period))
        latest = prices.iloc[-1]
        change = prices["Daily change %"].iloc[-1]
        a, b, c, d = st.columns(4)
        a.metric("Last close", money(latest["Close"]), f"{change:+.2f}%")
        b.metric("Day high", money(latest["High"]))
        c.metric("Day low", money(latest["Low"]))
        d.metric("RSI (14)", "—" if pd.isna(latest["RSI 14"]) else f"{latest['RSI 14']:.1f}")
        st.line_chart(prices[["Close", "SMA 20", "SMA 50"]], width="stretch")
        st.bar_chart(prices["Volume"], width="stretch")
        csv = prices.reset_index().to_csv(index=False).encode("utf-8")
        st.download_button("Download price data (CSV)", csv, f"{ticker}_prices.csv", "text/csv")
    except Exception as exc:
        st.error(str(exc))

with tab_alerts:
    st.write("Alerts are evaluated whenever this dashboard refreshes. For automatic alerts, schedule the included command with Task Scheduler or a cloud worker.")
    with st.form("new_alert", clear_on_submit=True):
        ticker = st.selectbox("Ticker to watch", st.session_state.watchlist, key="alert_ticker")
        direction = st.selectbox("Alert when price is", ["above", "below"])
        threshold = st.number_input("Price threshold", min_value=0.01, value=100.00, step=0.01)
        if st.form_submit_button("Create alert"):
            st.session_state.alerts.append({"ticker": ticker, "direction": direction, "threshold": threshold})
    if st.session_state.alerts:
        rows = []
        for alert in st.session_state.alerts:
            try:
                last_price = snapshot(alert["ticker"])["Price"]
                hit = last_price >= alert["threshold"] if alert["direction"] == "above" else last_price <= alert["threshold"]
                rows.append({**alert, "latest price": last_price, "status": "TRIGGERED" if hit else "Waiting"})
            except Exception:
                rows.append({**alert, "latest price": None, "status": "Data unavailable"})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("No alerts yet.")

with tab_report:
    report_rows = []
    for ticker in st.session_state.watchlist:
        try:
            report_rows.append(snapshot(ticker))
        except Exception:
            continue
    report = pd.DataFrame(report_rows)
    st.subheader(f"Daily watchlist report — {date.today():%d %b %Y}")
    if not report.empty:
        winners = report.nlargest(min(3, len(report)), "Change %")
        losers = report.nsmallest(min(3, len(report)), "Change %")
        left, right = st.columns(2)
        left.write("**Top movers**")
        left.dataframe(winners[["Symbol", "Price", "Change %", "RSI"]], hide_index=True, width="stretch")
        right.write("**Weakest movers**")
        right.dataframe(losers[["Symbol", "Price", "Change %", "RSI"]], hide_index=True, width="stretch")
        st.download_button("Download today’s report (CSV)", report.to_csv(index=False).encode(), "daily_market_report.csv", "text/csv")
