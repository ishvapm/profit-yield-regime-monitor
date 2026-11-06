# Profit–Yield Regime Monitor

**Author:** Ishva Mehta

This repo tracks two slow-moving market signals: U.S. corporate profit growth
and the direction of the 10-year Treasury yield. I built it after reading
BlackRock Investment Institute's weekly commentary, which often puts growth
and rates on the same page.

The model classifies each week into 1 of 4 regimes:

| Profit growth | 10Y yield | Regime |
|---|---|---|
| Accelerating | Rising | Structural growth / higher cost of capital |
| Accelerating | Falling | Risk-on easing |
| Decelerating | Rising | Margin pressure / stagflation risk |
| Decelerating | Falling | Cyclical slowdown |

The app also includes a small event study. It finds each date when the regime
changes and measures the following 13-week price return for SPY and TLT. The
summary reports the median, mean, standard deviation, positive-return share,
and number of events. These are conditional historical results, not forecasts.

## Data

The app downloads four public FRED series:

- CP: BEA corporate profits after tax
- DGS10: 10-year Treasury yield
- DGS2: 2-year Treasury yield
- T10YIE: 10-year breakeven inflation

SPY and TLT adjusted closes come from Yahoo Finance and are used only in the
event study.

Corporate profit growth is calculated year over year. Profit acceleration is
the quarterly change in that growth rate. The yield signal is the change in the
10-year Treasury yield over a configurable number of weeks.

I use BEA corporate profits because the history is public and reproducible.
It is an imperfect substitute for forward S&P 500 earnings: it covers the
domestic corporate sector, arrives quarterly, and is revised.

## Run locally

~~~bash
git clone <repository-url>
cd profit-yield-regime-monitor
python -m venv .venv

# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
~~~

## Test

~~~bash
python -m unittest discover -s tests -v
~~~

## Structure

~~~text
profit-yield-regime-monitor/
├── app.py
├── regime_monitor/
│   ├── data.py
│   ├── event_study.py
│   └── signals.py
├── tests/test_signals.py
├── .streamlit/config.toml
├── .github/workflows/tests.yml
├── requirements.txt
└── pyproject.toml
~~~

## Sources

- [BEA corporate profits](https://www.bea.gov/data/income-saving/corporate-profits)
- [FRED corporate profits](https://fred.stlouisfed.org/series/CP)
- [FRED 10-year Treasury](https://fred.stlouisfed.org/series/DGS10)
- [FRED 2-year Treasury](https://fred.stlouisfed.org/series/DGS2)
- [FRED 10-year breakeven](https://fred.stlouisfed.org/series/T10YIE)
- [Yahoo Finance](https://finance.yahoo.com/)

For research and demonstration only. Not investment advice.
