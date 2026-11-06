from __future__ import annotations

from io import StringIO
import json
import time
from urllib.request import Request, urlopen
import pandas as pd

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1=0&period2={period2}&interval=1d&events=history"
)
SERIES = {
    "corporate_profits": "CP",
    "treasury_10y": "DGS10",
    "treasury_2y": "DGS2",
    "breakeven_10y": "T10YIE",
}


def fetch_fred_series(series_id: str) -> pd.Series:
    request = Request(
        FRED_CSV_URL.format(series_id=series_id),
        headers={"User-Agent": "profit-yield-regime-monitor/0.1"},
    )
    with urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
    frame = pd.read_csv(StringIO(payload))
    date_column = frame.columns[0]
    frame[date_column] = pd.to_datetime(frame[date_column])
    value_column = frame.columns[1]
    values = pd.to_numeric(frame[value_column], errors="coerce")
    return pd.Series(
        values.to_numpy(),
        index=frame[date_column],
        name=series_id,
    ).dropna()


def load_market_data() -> dict[str, pd.Series]:
    return {name: fetch_fred_series(series_id) for name, series_id in SERIES.items()}


def fetch_yahoo_adjusted_close(symbol: str) -> pd.Series:
    request = Request(
        YAHOO_CHART_URL.format(symbol=symbol.upper(), period2=int(time.time()) + 86400),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    result = payload.get("chart", {}).get("result")
    if not result:
        raise ValueError(f"Unexpected Yahoo Finance response for {symbol}")
    chart = result[0]
    timestamps = chart.get("timestamp", [])
    adjusted = chart.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    if not timestamps or len(timestamps) != len(adjusted):
        raise ValueError(f"Adjusted-close history was not found for {symbol}")
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_localize(None).normalize()
    return pd.Series(adjusted, index=dates, name=symbol.upper(), dtype=float).dropna().sort_index()


def load_asset_prices() -> dict[str, pd.Series]:
    return {
        "SPY": fetch_yahoo_adjusted_close("SPY"),
        "TLT": fetch_yahoo_adjusted_close("TLT"),
    }
