import pytest
from src.order import Order, Side, OrderType
from src.engine import MatchingEngine


def _rest(engine, side, qty, price):
    engine.book.add(Order(side=side, qty=qty, price=price))


def test_market_buy_fills_against_ask():
    e = MatchingEngine()
    _rest(e, Side.SELL, 10, 101.0)
    trades = e.submit(Order(side=Side.BUY, qty=8, order_type=OrderType.MARKET))
    assert len(trades) == 1
    assert trades[0].price == 101.0
    assert trades[0].qty == 8
    assert trades[0].taker_side == Side.BUY


def test_market_buy_empty_book():
    e = MatchingEngine()
    trades = e.submit(Order(side=Side.BUY, qty=10, order_type=OrderType.MARKET))
    assert trades == []
    assert e.book.best_ask() is None
    assert e.book.best_bid() is None  # market order remainder discarded


def test_market_buy_partial_fill_then_discard():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 101.0)
    trades = e.submit(Order(side=Side.BUY, qty=10, order_type=OrderType.MARKET))
    assert sum(t.qty for t in trades) == 5
    assert e.book.best_ask() is None
    assert e.book.best_bid() is None  # nothing rests


def test_limit_buy_crosses_and_rests_remainder():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 100.0)
    e.submit(Order(side=Side.BUY, qty=10, price=101.0))
    assert e.book.best_bid() == 101.0
    assert e.book.bids[101.0].total_qty == 5


def test_limit_buy_does_not_cross():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 105.0)
    trades = e.submit(Order(side=Side.BUY, qty=10, price=100.0))
    assert trades == []
    assert e.book.best_bid() == 100.0
    assert e.book.best_ask() == 105.0


def test_fifo_within_level():
    e = MatchingEngine()
    o1 = Order(side=Side.SELL, qty=5, price=100.0)
    o2 = Order(side=Side.SELL, qty=5, price=100.0)
    e.book.add(o1)
    e.book.add(o2)
    trades = e.submit(Order(side=Side.BUY, qty=5, order_type=OrderType.MARKET))
    assert trades[0].maker_id == o1.order_id  # first in gets filled


def test_price_priority():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 102.0)
    _rest(e, Side.SELL, 5, 101.0)
    trades = e.submit(Order(side=Side.BUY, qty=5, order_type=OrderType.MARKET))
    assert trades[0].price == 101.0  # better price filled first


def test_sweep_multiple_levels():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 101.0)
    _rest(e, Side.SELL, 10, 102.0)
    trades = e.submit(Order(side=Side.BUY, qty=12, order_type=OrderType.MARKET))
    assert len(trades) == 2
    assert trades[0].price == 101.0 and trades[0].qty == 5
    assert trades[1].price == 102.0 and trades[1].qty == 7
    assert e.book.best_ask() == 102.0
    assert e.book.asks[102.0].total_qty == 3


def test_sell_matches_best_bid():
    e = MatchingEngine()
    _rest(e, Side.BUY, 10, 100.0)
    trades = e.submit(Order(side=Side.SELL, qty=6, order_type=OrderType.MARKET))
    assert trades[0].price == 100.0
    assert e.book.bids[100.0].total_qty == 4


def test_trades_accumulate():
    e = MatchingEngine()
    _rest(e, Side.SELL, 5, 100.0)
    _rest(e, Side.SELL, 5, 101.0)
    e.submit(Order(side=Side.BUY, qty=5, order_type=OrderType.MARKET))
    e.submit(Order(side=Side.BUY, qty=5, order_type=OrderType.MARKET))
    assert len(e.trades) == 2