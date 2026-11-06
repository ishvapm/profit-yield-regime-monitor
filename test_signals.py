import unittest
import math
import pandas as pd
from regime_monitor.signals import build_history, classify_regime, latest_snapshot
from regime_monitor.event_study import build_event_returns, summarize_event_returns


class RegimeSignalTests(unittest.TestCase):
    def test_all_four_regimes(self):
        self.assertEqual(classify_regime(True, True), "Structural growth / higher cost of capital")
        self.assertEqual(classify_regime(True, False), "Risk-on easing")
        self.assertEqual(classify_regime(False, True), "Margin pressure / stagflation risk")
        self.assertEqual(classify_regime(False, False), "Cyclical slowdown")

    def test_history_calculations(self):
        quarter_dates = pd.date_range("2018-03-31", periods=24, freq="QE")
        profits = pd.Series(
            [100 * math.exp(0.002 * i * i) for i in range(24)],
            index=quarter_dates,
        )
        daily_dates = pd.date_range("2018-01-01", "2024-01-05", freq="B")
        ten_year = pd.Series([2.0 + i * 0.001 for i in range(len(daily_dates))], index=daily_dates)
        two_year = ten_year - 0.35
        breakeven = pd.Series(2.2, index=daily_dates)
        history = build_history(profits, ten_year, two_year, breakeven, yield_lookback_weeks=13)
        snapshot = latest_snapshot(history)
        self.assertGreater(snapshot.yield_change_bps, 0)
        self.assertAlmostEqual(snapshot.curve_slope_bps, 35.0, places=8)
        self.assertEqual(snapshot.regime, "Structural growth / higher cost of capital")

    def test_snapshot_rejects_empty_history(self):
        with self.assertRaises(ValueError):
            latest_snapshot(pd.DataFrame())

    def test_event_study_uses_regime_entries(self):
        dates = pd.date_range("2020-01-03", periods=10, freq="W-FRI")
        history = pd.DataFrame(
            {"regime": ["A", "A", "A", "B", "B", "B", "A", "A", "A", "A"]},
            index=dates,
        )
        spy = pd.Series(range(100, 110), index=dates, dtype=float)
        tlt = pd.Series(range(200, 210), index=dates, dtype=float)
        events = build_event_returns(history, {"SPY": spy, "TLT": tlt}, horizon_weeks=2)
        self.assertEqual(len(events), 6)
        self.assertEqual(events["date"].nunique(), 3)
        summary = summarize_event_returns(events)
        self.assertEqual(int(summary["observations"].sum()), 6)


if __name__ == "__main__":
    unittest.main()
