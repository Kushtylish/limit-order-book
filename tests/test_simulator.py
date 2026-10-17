import pytest
from src.simulator import Simulator, SimulationConfig


def test_simulation_completes():
    cfg = SimulationConfig(seed=42, duration=1.0)
    result = Simulator(cfg).run()
    assert result is not None
    assert len(result.mid_series) > 1
    assert result.final_book is not None


def test_simulation_produces_trades():
    cfg = SimulationConfig(seed=42, duration=5.0, order_rate=200.0)
    result = Simulator(cfg).run()
    assert len(result.trades) > 0


def test_simulation_reproducible():
    cfg1 = SimulationConfig(seed=42, duration=2.0)
    cfg2 = SimulationConfig(seed=42, duration=2.0)
    r1 = Simulator(cfg1).run()
    r2 = Simulator(cfg2).run()
    assert len(r1.trades) == len(r2.trades)
    assert [t.price for t in r1.trades] == [t.price for t in r2.trades]
    assert [t.qty for t in r1.trades] == [t.qty for t in r2.trades]


def test_book_not_crossed_after_simulation():
    cfg = SimulationConfig(seed=7, duration=3.0)
    result = Simulator(cfg).run()
    book = result.final_book
    bb = book.best_bid()
    ba = book.best_ask()
    if bb is not None and ba is not None:
        assert bb < ba


def test_mid_series_always_defined():
    cfg = SimulationConfig(seed=1, duration=1.0)
    result = Simulator(cfg).run()
    for t, mid in result.mid_series:
        assert mid is not None and mid > 0


def test_trades_have_valid_prices():
    cfg = SimulationConfig(seed=3, duration=2.0, order_rate=150.0)
    result = Simulator(cfg).run()
    for t in result.trades:
        assert t.price > 0
        assert t.qty > 0
        assert t.taker_id != t.maker_id


def test_initial_book_has_spread():
    cfg = SimulationConfig(seed=1, duration=0.0)  # run zero time
    sim = Simulator(cfg)
    # don't run — just check initialized book
    bb = sim.engine.book.best_bid()
    ba = sim.engine.book.best_ask()
    assert bb is not None
    assert ba is not None
    assert bb < ba