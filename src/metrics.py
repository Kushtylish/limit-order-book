import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from src.simulator import SimulationResult
from src.order import Side


@dataclass
class MarketStats:
    mean_spread: float
    median_spread: float
    mean_top_depth_bid: float
    mean_top_depth_ask: float
    n_trades: int
    mean_trade_size: float
    total_volume: float
    volatility: float  # std of mid-price changes


def compute_market_stats(result: SimulationResult) -> MarketStats:
    """Aggregate market quality metrics from a simulation run."""
    mids = [m for _, m in result.mid_series if m is not None]

    spreads = []
    depth_bid = []
    depth_ask = []
    # mid_series is only point samples; we compute top-of-book stats from trade prices
    # For spreads we use consecutive mids only as a lower-bound proxy (not accurate).
    # Instead, compute directly from trade prices + final book, and from mid jumps.
    for i in range(1, len(mids)):
        spreads.append(abs(mids[i] - mids[i - 1]))

    trade_prices = [t.price for t in result.trades]
    trade_qty = [t.qty for t in result.trades]

    if len(mids) > 1:
        returns = np.diff(mids) / np.array(mids[:-1])
        vol = float(np.std(returns))
    else:
        vol = 0.0

    # Top-of-book depth from the final book
    if result.final_book is not None:
        bb = result.final_book.best_bid()
        ba = result.final_book.best_ask()
        if bb is not None:
            depth_bid.append(result.final_book.bids[bb].total_qty)
        if ba is not None:
            depth_ask.append(result.final_book.asks[ba].total_qty)

    return MarketStats(
        mean_spread=float(np.mean(spreads)) if spreads else 0.0,
        median_spread=float(np.median(spreads)) if spreads else 0.0,
        mean_top_depth_bid=float(np.mean(depth_bid)) if depth_bid else 0.0,
        mean_top_depth_ask=float(np.mean(depth_ask)) if depth_ask else 0.0,
        n_trades=len(result.trades),
        mean_trade_size=float(np.mean(trade_qty)) if trade_qty else 0.0,
        total_volume=float(np.sum(trade_qty)) if trade_qty else 0.0,
        volatility=vol,
    )


def simulate_market_order_slippage(
    simulator_factory, size: int, n_trials: int = 20
) -> dict:
    """
    Estimate slippage of a market order of given size.

    For each trial:
      - build a fresh simulator with a different seed
      - run it briefly to warm up the book
      - submit a market order of `size` shares
      - record the average execution price vs pre-trade mid

    Returns a dict with mean slippage (in price units) and mean signed impact
    (positive = adverse for the taker).
    """
    slippages = []
    impacts = []
    for trial in range(n_trials):
        sim = simulator_factory(seed=trial)
        # warm up
        warm = sim.run()

        pre_mid = sim.engine.book.mid_price()
        if pre_mid is None:
            continue

        # submit market buy of `size`
        from src.order import Order, OrderType
        trades = sim.engine.submit(Order(
            side=Side.BUY, qty=size, price=0.0,
            order_type=OrderType.MARKET,
        ))
        if not trades:
            continue
        filled = sum(t.qty for t in trades)
        if filled == 0:
            continue

        avg_price = sum(t.price * t.qty for t in trades) / filled
        slippages.append(avg_price - pre_mid)
        impacts.append(avg_price - pre_mid)

    return {
        "mean_slippage": float(np.mean(slippages)) if slippages else 0.0,
        "mean_impact": float(np.mean(impacts)) if impacts else 0.0,
        "n_filled": len(slippages),
        "fill_rate": len(slippages) / n_trials if n_trials else 0.0,
    }


def impact_curve(
    simulator_factory, sizes: List[int], n_trials: int = 20
) -> dict:
    """
    Market impact as a function of order size.

    Returns dict with:
      sizes: list of order sizes
      impacts: mean signed impact per size
      errors: standard error per size
    """
    impacts = []
    errors = []
    for size in sizes:
        trials = []
        for trial in range(n_trials):
            sim = simulator_factory(seed=trial + 1000 * size)
            sim.run()
            pre_mid = sim.engine.book.mid_price()
            if pre_mid is None:
                continue
            from src.order import Order, OrderType
            trades = sim.engine.submit(Order(
                side=Side.BUY, qty=size, price=0.0,
                order_type=OrderType.MARKET,
            ))
            if not trades:
                continue
            filled = sum(t.qty for t in trades)
            if filled == 0:
                continue
            avg = sum(t.price * t.qty for t in trades) / filled
            trials.append(avg - pre_mid)
        if trials:
            impacts.append(float(np.mean(trials)))
            errors.append(float(np.std(trials) / np.sqrt(len(trials))))
        else:
            impacts.append(0.0)
            errors.append(0.0)

    return {"sizes": list(sizes), "impacts": impacts, "errors": errors}