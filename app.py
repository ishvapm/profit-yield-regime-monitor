from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from regime_monitor.data import SERIES, load_asset_prices, load_market_data
from regime_monitor.event_study import build_event_returns, summarize_event_returns
from regime_monitor.signals import REGIME_DETAILS, build_history, latest_snapshot

st.set_page_config(page_title="Profit–Yield Regime Monitor", page_icon="↗", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1220px; padding-top: 2.2rem; }
    header[data-testid="stHeader"] { background: rgba(243,240,231,.88); }
    h1 { font-size: clamp(3rem, 7vw, 6.7rem) !important; line-height: .88 !important;
         letter-spacing: -.065em !important; max-width: 950px; }
    h2, h3 { letter-spacing: -.035em !important; }
    .kicker { font: 600 11px/1.2 monospace; letter-spacing: .14em; }
    .deck { max-width: 700px; font-size: 1.08rem; line-height: 1.65; color: #47514c; }
    .regime-card { border: 1px solid rgba(16,24,20,.2); padding: 24px 28px;
                   margin: 1.6rem 0 1.4rem; background: #101814; color: white; }
    .regime-card small { font: 600 10px monospace; letter-spacing: .12em; color: #aeb7b1; }
    .regime-card h2 { color: white; margin: .7rem 0 .5rem; font-size: 2rem; }
    .regime-card p { max-width: 800px; color: #d7ddd8; line-height: 1.6; }
    [data-testid="stMetric"] { border-top: 1px solid rgba(16,24,20,.22); padding-top: 16px; }
    [data-testid="stMetricLabel"] { font-family: monospace; text-transform: uppercase; letter-spacing: .05em; }
    .source-note { font: 11px/1.6 monospace; color: #68716c; }
    .stDownloadButton button { border-radius: 0; border-color: #101814; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def get_history(lookback_weeks: int) -> pd.DataFrame:
    data = load_market_data()
    return build_history(
        data["corporate_profits"],
        data["treasury_10y"],
        data["treasury_2y"],
        data["breakeven_10y"],
        yield_lookback_weeks=lookback_weeks,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_event_study(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = build_event_returns(history, load_asset_prices(), horizon_weeks=13)
    return events, summarize_event_returns(events)


with st.sidebar:
    st.markdown("### ↗ REGIME MONITOR")
    st.caption("ISHVA MEHTA")
    st.divider()
    history_years = st.select_slider(
        "Chart history",
        options=[5, 10, 15, 20],
        value=10,
        format_func=lambda value: f"{value} years",
    )
    lookback = st.select_slider(
        "Yield trend window",
        options=[4, 8, 13, 26],
        value=13,
        format_func=lambda value: f"{value} weeks",
    )
    st.divider()
    st.caption("PUBLIC DATA")
    for label, series_id in SERIES.items():
        st.markdown(f"**{series_id}** · {label.replace('_', ' ').title()}")

st.markdown('<div class="kicker">U.S. CAPITAL MARKETS · PUBLIC DATA</div>', unsafe_allow_html=True)
st.title("When profits and yields move together.")
st.markdown(
    '<p class="deck">A weekly read on U.S. corporate profit growth and the '
    "10-year Treasury yield. Two signals, four possible regimes.</p>",
    unsafe_allow_html=True,
)

try:
    history = get_history(lookback)
except Exception as error:
    st.error("Could not download the latest FRED data.")
    st.caption(str(error))
    st.stop()

snapshot = latest_snapshot(history)
detail = snapshot.details
st.markdown(
    f"""
    <div class="regime-card" style="border-left: 8px solid {detail['color']}">
      <small>CURRENT REGIME · WEEK ENDING {snapshot.as_of:%d %B %Y}</small>
      <h2>{snapshot.regime}</h2>
      <p>{detail['interpretation']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = st.columns(5)
metrics[0].metric("Profit growth", f"{snapshot.profit_growth:.1f}%", f"{snapshot.profit_acceleration:+.1f} pp q/q")
metrics[1].metric("10Y Treasury", f"{snapshot.treasury_10y:.2f}%", f"{snapshot.yield_change_bps:+.0f} bps / {lookback}w", delta_color="inverse")
metrics[2].metric("2s10s curve", f"{snapshot.curve_slope_bps:+.0f} bps")
metrics[3].metric("10Y breakeven", f"{snapshot.breakeven_10y:.2f}%")
metrics[4].metric(
    "Signal",
    "Profits ↑" if snapshot.profit_acceleration > 0 else "Profits ↓",
    "Yields ↑" if snapshot.yield_change_bps > 0 else "Yields ↓",
    delta_color="off",
)

cutoff = history.index.max() - pd.DateOffset(years=history_years)
chart_data = history.loc[history.index >= cutoff].copy()
figure = make_subplots(specs=[[{"secondary_y": True}]])
figure.add_trace(
    go.Scatter(
        x=chart_data.index,
        y=chart_data["profit_growth"],
        name="Corporate profit growth",
        line=dict(color="#101814", width=3),
        hovertemplate="%{x|%b %Y}<br>Profit growth: %{y:.1f}%<extra></extra>",
    ),
    secondary_y=False,
)
figure.add_trace(
    go.Scatter(
        x=chart_data.index,
        y=chart_data["treasury_10y"],
        name="10Y Treasury yield",
        line=dict(color="#3D7EA6", width=2),
        hovertemplate="%{x|%b %Y}<br>10Y yield: %{y:.2f}%<extra></extra>",
    ),
    secondary_y=True,
)

regime_runs = (chart_data["regime"] != chart_data["regime"].shift()).cumsum()
for _, segment in chart_data.groupby(regime_runs):
    regime = segment["regime"].iloc[0]
    figure.add_vrect(
        x0=segment.index.min(),
        x1=segment.index.max(),
        fillcolor=REGIME_DETAILS[regime]["color"],
        opacity=0.11,
        line_width=0,
        layer="below",
    )

figure.update_layout(
    height=560,
    margin=dict(l=15, r=15, t=70, b=25),
    paper_bgcolor="#F3F0E7",
    plot_bgcolor="#F3F0E7",
    hovermode="x unified",
    legend=dict(orientation="h", y=1.12, x=0),
    font=dict(color="#101814"),
    xaxis=dict(showgrid=False),
)
figure.update_yaxes(title_text="Corporate profit growth, year over year (%)", gridcolor="rgba(16,24,20,.09)", secondary_y=False)
figure.update_yaxes(title_text="10-year Treasury yield (%)", showgrid=False, secondary_y=True)
st.plotly_chart(figure, width="stretch")

legend_cols = st.columns(4)
for column, (regime, values) in zip(legend_cols, REGIME_DETAILS.items()):
    column.markdown(
        f"<div style='border-top:4px solid {values['color']};padding-top:9px'>"
        f"<b style='font-size:13px'>{regime}</b><br>"
        f"<span style='font:10px monospace;color:#68716c'>{values['short']}</span>"
        "</div>",
        unsafe_allow_html=True,
    )

st.divider()
st.subheader("What happened next?")
st.write(
    "The event study measures 13-week SPY and TLT price returns after each change in regime. "
    "Using regime entries avoids counting every week of the same episode as a new event."
)
try:
    events, event_summary = get_event_study(history)
except Exception as error:
    st.warning("The Yahoo Finance price history could not be downloaded, so the event study is unavailable.")
    st.caption(str(error))
else:
    regime_order = list(REGIME_DETAILS)
    chart_summary = event_summary.copy()
    chart_summary["regime"] = pd.Categorical(chart_summary["regime"], categories=regime_order, ordered=True)
    chart_summary = chart_summary.sort_values(["regime", "asset"])
    event_figure = go.Figure()
    for asset, color in [("SPY", "#101814"), ("TLT", "#3D7EA6")]:
        asset_data = chart_summary.loc[chart_summary["asset"] == asset]
        event_figure.add_bar(
            x=asset_data["regime"],
            y=asset_data["median_return"],
            name=asset,
            marker_color=color,
            customdata=asset_data[["observations", "hit_rate"]],
            hovertemplate=(
                "%{x}<br>Median 13-week return: %{y:.1f}%<br>"
                "Events: %{customdata[0]}<br>Positive: %{customdata[1]:.0f}%<extra></extra>"
            ),
        )
    event_figure.add_hline(y=0, line_width=1, line_color="rgba(16,24,20,.45)")
    event_figure.update_layout(
        barmode="group",
        height=430,
        margin=dict(l=15, r=15, t=35, b=90),
        paper_bgcolor="#F3F0E7",
        plot_bgcolor="#F3F0E7",
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis_title="Median 13-week price return (%)",
        xaxis_title=None,
        font=dict(color="#101814"),
    )
    st.plotly_chart(event_figure, width="stretch")

    display_summary = event_summary.copy()
    display_summary.columns = [
        "Regime", "Asset", "Events", "Median return (%)", "Mean return (%)", "Volatility (%)", "Positive (%)"
    ]
    st.dataframe(
        display_summary.style.format(
            {
                "Median return (%)": "{:.1f}",
                "Mean return (%)": "{:.1f}",
                "Volatility (%)": "{:.1f}",
                "Positive (%)": "{:.0f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Descriptive, not predictive. SPY and TLT returns use adjusted closes from Yahoo Finance. "
        "The profit series is revised, and the sample begins with available ETF history."
    )

st.divider()
left, right = st.columns([1.4, 1])
with left:
    st.subheader("Latest observations")
    table = history.tail(8)[["profit_growth", "treasury_10y", "yield_change_bps", "curve_slope_bps", "regime"]].copy()
    table.index = table.index.strftime("%Y-%m-%d")
    table.columns = ["Profit growth (%)", "10Y yield (%)", f"{lookback}w yield change (bps)", "2s10s (bps)", "Regime"]
    st.dataframe(
        table.style.format({
            "Profit growth (%)": "{:.1f}",
            "10Y yield (%)": "{:.2f}",
            f"{lookback}w yield change (bps)": "{:+.0f}",
            "2s10s (bps)": "{:+.0f}",
        }),
        width="stretch",
    )
with right:
    st.subheader("Export")
    st.write("Download the weekly inputs and regime labels as a CSV file.")
    st.download_button(
        "Download signal history",
        history.to_csv(index_label="date"),
        file_name="profit_yield_regimes.csv",
        mime="text/csv",
    )

with st.expander("Method and data notes"):
    st.markdown(
        f"""
        **Profit signal.** BEA corporate profits after tax (CP) are converted
        to year-over-year growth. The signal is rising when the latest quarterly
        growth rate is above the previous quarter's rate.

        **Yield signal.** The 10-year Treasury yield (DGS10) is rising when its
        change over the selected {lookback}-week window is positive.

        **Caveat.** BEA corporate profits are realized, economy-wide profits.
        They are used here because the series is public. This is not the same
        thing as forward S&P 500 earnings estimates.
        """
    )

st.markdown(
    '<p class="source-note">Sources: U.S. Bureau of Economic Analysis and '
    "Federal Reserve Bank of St. Louis (FRED). Data may be revised. "
    "For research and demonstration only; not investment advice.</p>",
    unsafe_allow_html=True,
)
