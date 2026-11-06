from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

REGIME_DETAILS = {
    "Structural growth / higher cost of capital": {
        "short": "Profits accelerating · yields rising",
        "interpretation": "Profit growth is picking up, but the discount rate is also rising. That is a better growth backdrop with a less forgiving cost of capital.",
        "color": "#C9FF57",
    },
    "Risk-on easing": {
        "short": "Profits accelerating · yields falling",
        "interpretation": "Profit growth is picking up while long-term yields fall. Both signals are moving in a direction that tends to help risky assets.",
        "color": "#72D6FF",
    },
    "Margin pressure / stagflation risk": {
        "short": "Profits decelerating · yields rising",
        "interpretation": "Profit growth is slowing while long-term yields rise. Earnings and valuation support are weakening at the same time.",
        "color": "#FF9B71",
    },
    "Cyclical slowdown": {
        "short": "Profits decelerating · yields falling",
        "interpretation": "Profit growth and long-term yields are both falling, a combination usually associated with a softer nominal growth outlook.",
        "color": "#B9B2E9",
    },
}


@dataclass(frozen=True)
class RegimeSnapshot:
    as_of: pd.Timestamp
    regime: str
    profit_growth: float
    profit_acceleration: float
    treasury_10y: float
    yield_change_bps: float
    curve_slope_bps: float
    breakeven_10y: float

    @property
    def details(self) -> dict[str, str]:
        return REGIME_DETAILS[self.regime]


def classify_regime(profits_accelerating: bool, yields_rising: bool) -> str:
    if profits_accelerating and yields_rising:
        return "Structural growth / higher cost of capital"
    if profits_accelerating:
        return "Risk-on easing"
    if yields_rising:
        return "Margin pressure / stagflation risk"
    return "Cyclical slowdown"


def build_history(
    corporate_profits: pd.Series,
    treasury_10y: pd.Series,
    treasury_2y: pd.Series,
    breakeven_10y: pd.Series,
    yield_lookback_weeks: int = 13,
) -> pd.DataFrame:
    profits = corporate_profits.sort_index()
    profit_growth = profits.pct_change(4) * 100
    profit_acceleration = profit_growth.diff()
    rates = pd.concat(
        [
            treasury_10y.rename("treasury_10y"),
            treasury_2y.rename("treasury_2y"),
            breakeven_10y.rename("breakeven_10y"),
        ],
        axis=1,
    ).sort_index().ffill()
    weekly = rates.resample("W-FRI").last().dropna()
    weekly["profit_growth"] = profit_growth.reindex(weekly.index, method="ffill")
    weekly["profit_acceleration"] = profit_acceleration.reindex(weekly.index, method="ffill")
    weekly["yield_change_bps"] = weekly["treasury_10y"].diff(yield_lookback_weeks) * 100
    weekly["curve_slope_bps"] = (weekly["treasury_10y"] - weekly["treasury_2y"]) * 100
    weekly = weekly.dropna()
    weekly["profits_accelerating"] = weekly["profit_acceleration"] > 0
    weekly["yields_rising"] = weekly["yield_change_bps"] > 0
    weekly["regime"] = [
        classify_regime(profits_up, yields_up)
        for profits_up, yields_up in zip(weekly["profits_accelerating"], weekly["yields_rising"])
    ]
    return weekly


def latest_snapshot(history: pd.DataFrame) -> RegimeSnapshot:
    if history.empty:
        raise ValueError("No overlapping observations were found")
    row = history.iloc[-1]
    return RegimeSnapshot(
        as_of=pd.Timestamp(history.index[-1]),
        regime=str(row["regime"]),
        profit_growth=float(row["profit_growth"]),
        profit_acceleration=float(row["profit_acceleration"]),
        treasury_10y=float(row["treasury_10y"]),
        yield_change_bps=float(row["yield_change_bps"]),
        curve_slope_bps=float(row["curve_slope_bps"]),
        breakeven_10y=float(row["breakeven_10y"]),
    )
