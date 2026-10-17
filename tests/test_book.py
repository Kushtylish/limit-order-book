import pytest
from src.order import Order, Side
from src.book import OrderBook, PriceLevel


def test_empty_book():
    book = OrderBook()
    assert book.best_bid() is None
    assert book.best_ask() is None
    assert book.spread() is None
    assert book.mid_price() is None


def test_add_and_best_prices():
    book = OrderBook()
    book.add(Order(side=Side.BUY, qty=10, price=99.0))
    book.add(Order(side=Side.BUY, qty=5, price=100.0))
    book.add(Order(side=Side.SELL, qty=10, price=101.0))
    book.add(Order(side=Side.SELL, qty=5, price=102.0))
    assert book.best_bid() == 100.0
    assert book.best_ask() == 101.0
    assert book.spread() == 1.0
    assert book.mid_price() == 100.5


def test_fifo_at_same_level():
    book = OrderBook()
    o1 = Order(side=Side.BUY, qty=10, price=99.0)
    o2 = Order(side=Side.BUY, qty=5, price=99.0)
    book.add(o1)
    book.add(o2)
    level = book.bids[99.0]
    assert [o.order_id for o in level.orders] == [o1.order_id, o2.order_id]
    assert level.total_qty == 15


def test_cancel_partial():
    book = OrderBook()
    o1 = Order(side=Side.BUY, qty=10, price=99.0)
    o2 = Order(side=Side.BUY, qty=5, price=99.0)
    book.add(o1)
    book.add(o2)
    assert book.cancel(o1) is True
    assert book.bids[99.0].total_qty == 5
    assert 99.0 in book.bids


def test_cancel_clears_empty_level():
    book = OrderBook()
    o = Order(side=Side.SELL, qty=10, price=101.0)
    book.add(o)
    assert book.cancel(o) is True
    assert 101.0 not in book.asks
    assert book.best_ask() is None


def test_cancel_nonexistent_returns_false():
    book = OrderBook()
    o = Order(side=Side.BUY, qty=10, price=99.0)
    assert book.cancel(o) is False


def test_depth():
    book = OrderBook()
    for p, q in [(99.0, 10), (99.0, 5), (98.0, 20), (97.0, 30)]:
        book.add(Order(side=Side.BUY, qty=q, price=p))
    depth = book.depth(Side.BUY, n_levels=2)
    assert depth == [(99.0, 15), (98.0, 20)]