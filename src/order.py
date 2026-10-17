import itertools
from dataclasses import dataclass, field
from enum import Enum

_id_counter = itertools.count(1)


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


@dataclass
class Order:
    side: Side
    qty: float
    price: float = 0.0
    order_type: OrderType = OrderType.LIMIT
    timestamp: float = 0.0
    order_id: int = field(default_factory=lambda: next(_id_counter))

    def __post_init__(self):
        if self.qty <= 0:
            raise ValueError(f"qty must be positive, got {self.qty}")
        if self.order_type == OrderType.LIMIT and self.price <= 0:
            raise ValueError(f"limit order price must be positive, got {self.price}")