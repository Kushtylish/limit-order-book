import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from src.simulator import Simulator, SimulationConfig
from src.metrics import compute_market_stats, impact_curve
from src.order import Side

st.set_page_config(layout="wide", page_title="Limit Order Book Simulator")
st.title("Limit Order Book Simulator")
st.caption("Poisson-driven order flow, price-time priority matching, market impact analysis")


@st.cache_data
def run_sim(seed, duration, order_rate, cancel_rate, market_prob, n_levels, init_qty):
    cfg = SimulationConfig(
        seed=seed,
        duration=duration,
        order_rate=order_rate,
        cancel_rate=cancel_rate,
        market_order_prob=market_prob,
        n_levels=n_levels,
        initial_qty=init_qty,
    )
    sim = Simulator(cfg)
    result = sim.run()
    stats = compute_market_stats(result)

    # Convert series to DataFrames for plotting
    mid_df = pd.DataFrame(
        [(t, m) for t, m in result.mid_series if m is not None],
        columns=["time", "mid"],
    )

    trades_df = pd.DataFrame(
        [(t.timestamp, t.price, t.qty, t.taker_side.value) for t in result.trades],
        columns=["time", "price", "qty", "side"],
    )

    # Depth snapshot
    book = result.final_book
    bid_depth = book.depth(Side.BUY, n_levels=10) if book else []
    ask_depth = book.depth(Side.SELL, n_levels=10) if book else []

    return stats, mid_df, trades_df, bid_depth, ask_depth


@st.cache_data
def run_impact(seed, sizes, n_trials):
    def factory(seed):
        return Simulator(SimulationConfig(
            seed=seed, duration=2.0,
            n_levels=10, initial_qty=5,
            order_rate=100.0, cancel_rate=50.0,
        ))
    return impact_curve(factory, sizes, n_trials=n_trials)


with st.sidebar:
    st.header("Simulation parameters")
    seed = st.number_input("Random seed", value=42, step=1)
    duration = st.slider("Duration (sim time)", 1.0, 30.0, 10.0, 1.0)
    order_rate = st.slider("Order arrival rate (per unit time)", 20.0, 400.0, 100.0, 10.0)
    cancel_rate = st.slider("Cancel rate (per unit time)", 10.0, 200.0, 50.0, 10.0)
    market_prob = st.slider("Market order probability", 0.0, 0.8, 0.2, 0.05)
    n_levels = st.slider("Initial book depth (levels)", 5, 30, 10, 1)
    init_qty = st.slider("Shares per initial order", 1, 30, 5, 1)

st.subheader("Market quality")
stats, mid_df, trades_df, bid_depth, ask_depth = run_sim(
    seed, duration, order_rate, cancel_rate, market_prob, n_levels, init_qty
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trades", stats.n_trades)
c2.metric("Volume", f"{stats.total_volume:.0f}")
c3.metric("Mean trade size", f"{stats.mean_trade_size:.1f}")
c4.metric("Volatility (per step)", f"{stats.volatility:.5f}")

st.subheader("Mid price over time")
if not mid_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mid_df["time"], y=mid_df["mid"], mode="lines", name="mid"))
    fig.update_layout(xaxis_title="time", yaxis_title="mid price", height=300,
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Final order book depth")
if bid_depth and ask_depth:
    bid_df = pd.DataFrame(bid_depth, columns=["price", "qty"])
    ask_df = pd.DataFrame(ask_depth, columns=["price", "qty"])

    fig = go.Figure()
    fig.add_trace(go.Bar(x=bid_df["price"], y=bid_df["qty"],
                         name="bids", marker_color="green"))
    fig.add_trace(go.Bar(x=ask_df["price"], y=ask_df["qty"],
                         name="asks", marker_color="red"))
    fig.update_layout(xaxis_title="price", yaxis_title="resting qty",
                      height=300, margin=dict(l=0, r=0, t=10, b=0),
                      barmode="overlay")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Book is empty — try longer duration or fewer cancels")

st.subheader("Trade tape")
if not trades_df.empty:
    fig = go.Figure()
    buys = trades_df[trades_df["side"] == "buy"]
    sells = trades_df[trades_df["side"] == "sell"]
    fig.add_trace(go.Scatter(x=buys["time"], y=buys["price"],
                             mode="markers", name="buys (aggressor)",
                             marker=dict(color="green", symbol="triangle-up", size=6)))
    fig.add_trace(go.Scatter(x=sells["time"], y=sells["price"],
                             mode="markers", name="sells (aggressor)",
                             marker=dict(color="red", symbol="triangle-down", size=6)))
    fig.update_layout(xaxis_title="time", yaxis_title="price", height=300,
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Market impact curve")
st.caption("Average execution price premium vs pre-trade mid, by order size")

impact_sizes = [2, 5, 10, 20, 40, 80, 150, 250]
curve = run_impact(seed=42, sizes=tuple(impact_sizes), n_trials=6)

if any(i > 0 for i in curve["impacts"]):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve["sizes"], y=curve["impacts"],
        error_y=dict(type="data", array=curve["errors"]),
        mode="lines+markers", name="impact",
    ))
    fig.update_layout(
        xaxis_title="order size", yaxis_title="impact (price units)",
        xaxis_type="log", yaxis_type="log",
        height=350, margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Concave impact is the expected shape. The fitted exponent depends on "
        "book depth relative to order size — see the notebook for full analysis."
    )
else:
    st.info("Not enough filled orders to compute impact")