from __future__ import annotations

import pandas as pd


def build_event_returns(
    history: pd.DataFrame,
    asset_prices: dict[str, pd.Series],
    horizon_weeks: int = 13,
) -> pd.DataFrame:
    if horizon_weeks < 1:
        raise ValueError("horizon_weeks must be positive")

    weekly_prices = pd.concat(
        [series.rename(symbol).resample("W-FRI").last() for symbol, series in asset_prices.items()],
        axis=1,
    )
    aligned = history[["regime"]].join(weekly_prices, how="left").ffill()
    entry_dates = aligned["regime"].ne(aligned["regime"].shift())

    records: list[dict[str, object]] = []
    for symbol in asset_prices:
        forward_return = aligned[symbol].shift(-horizon_weeks).div(aligned[symbol]).sub(1).mul(100)
        events = aligned.loc[entry_dates, ["regime"]].copy()
        events["forward_return"] = forward_return.loc[entry_dates]
        events = events.dropna()
        for date, row in events.iterrows():
            records.append(
                {
                    "date": pd.Timestamp(date),
                    "regime": row["regime"],
                    "asset": symbol,
                    "forward_return": float(row["forward_return"]),
                }
            )
    return pd.DataFrame.from_records(records)


def summarize_event_returns(events: pd.DataFrame) -> pd.DataFrame:
    columns = ["regime", "asset", "observations", "median_return", "mean_return", "volatility", "hit_rate"]
    if events.empty:
        return pd.DataFrame(columns=columns)

    summary = (
        events.groupby(["regime", "asset"])["forward_return"]
        .agg(observations="count", median_return="median", mean_return="mean", volatility="std")
        .reset_index()
    )
    hit_rate = (
        events.assign(positive=events["forward_return"] > 0)
        .groupby(["regime", "asset"])["positive"]
        .mean()
        .mul(100)
        .rename("hit_rate")
        .reset_index()
    )
    return summary.merge(hit_rate, on=["regime", "asset"])
