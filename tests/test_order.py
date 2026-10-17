import pytest
from src.order import Order, Side, OrderType


def test_order_creation():
    o = Order(side=Side.BUY, qty=10, price=100.0)
    assert o.qty == 10
    assert o.price == 100.0
    assert o.side == Side.BUY
    assert o.order_type == OrderType.LIMIT
    assert o.order_id > 0


def test_order_ids_are_unique():
    a = Order(side=Side.BUY, qty=1, price=100.0)
    b = Order(side=Side.BUY, qty=1, price=100.0)
    assert a.order_id != b.order_id


def test_invalid_qty():
    with pytest.raises(ValueError):
        Order(side=Side.BUY, qty=0, price=100.0)
    with pytest.raises(ValueError):
        Order(side=Side.BUY, qty=-1, price=100.0)


def test_limit_order_needs_price():
    with pytest.raises(ValueError):
        Order(side=Side.BUY, qty=10, price=0, order_type=OrderType.LIMIT)


def test_market_order_no_price_required():
    o = Order(side=Side.SELL, qty=10, price=0, order_type=OrderType.MARKET)
    assert o.price == 0
    assert o.order_type == OrderType.MARKET