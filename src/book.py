from dataclasses import dataclass, field
from typing import Dict, List, Optional
from src.order import Order, Side


@dataclass
class PriceLevel:
    """A FIFO queue of orders at a single price."""
    price: float
    orders: List[Order] = field(default_factory=list)
    total_qty: float = 0.0

    def add(self, order: Order) -> None:
        self.orders.append(order)
        self.total_qty += order.qty

    def remove(self, order: Order) -> bool:
        for i, o in enumerate(self.orders):
            if o.order_id == order.order_id:
                self.total_qty -= o.qty
                self.orders.pop(i)
                return True
        return False

    def is_empty(self) -> bool:
        return len(self.orders) == 0


class OrderBook:
    """Two-sided order book with price-time priority per level."""

    def __init__(self):
        self.bids: Dict[float, PriceLevel] = {}
        self.asks: Dict[float, PriceLevel] = {}

    def _levels_for(self, side: Side) -> Dict[float, PriceLevel]:
        return self.bids if side == Side.BUY else self.asks

    def add(self, order: Order) -> None:
        levels = self._levels_for(order.side)
        if order.price not in levels:
            levels[order.price] = PriceLevel(price=order.price)
        levels[order.price].add(order)

    def cancel(self, order: Order) -> bool:
        levels = self._levels_for(order.side)
        level = levels.get(order.price)
        if level is None:
            return False
        removed = level.remove(order)
        if removed and level.is_empty():
            del levels[order.price]
        return removed

    def best_bid(self) -> Optional[float]:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> Optional[float]:
        return min(self.asks.keys()) if self.asks else None

    def spread(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return ba - bb

    def mid_price(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    def depth(self, side: Side, n_levels: int = 5) -> List[tuple]:
        levels = self._levels_for(side)
        if side == Side.BUY:
            prices = sorted(levels.keys(), reverse=True)[:n_levels]
        else:
            prices = sorted(levels.keys())[:n_levels]
        return [(p, levels[p].total_qty) for p in prices]