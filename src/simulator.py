import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from src.order import Order, Side, OrderType
from src.book import OrderBook
from src.engine import MatchingEngine, Trade


@dataclass
class SimulationConfig:
    seed: int = 42
    initial_price: float = 100.0
    initial_spread: float = 0.05
    tick_size: float = 0.01
    n_levels: int = 5
    orders_per_level: int = 3
    initial_qty: int = 10
    order_rate: float = 100.0          # new orders per unit time
    cancel_rate: float = 50.0          # cancels per unit time
    market_order_prob: float = 0.2     # fraction of orders that are market
    limit_offset_scale: float = 0.05   # scale of exponential offset from spread
    limit_qty_mean: float = 5.0
    market_qty_mean: float = 8.0
    duration: float = 10.0


@dataclass
class SimulationResult:
    trades: List[Trade] = field(default_factory=list)
    mid_series: List[Tuple[float, Optional[float]]] = field(default_factory=list)
    final_book: Optional[OrderBook] = None


class Simulator:
    """Poisson-driven order flow simulator.

    Events are:
      - new order (limit or market), rate = order_rate
      - cancel of a random resting order, rate = cancel_rate

    Book is initialized with resting bids and asks around initial_price so
    that t=0 already has a defined spread.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.engine = MatchingEngine()
        self._initialize_book()

    def _initialize_book(self) -> None:
        mid = self.config.initial_price
        half_spread = self.config.initial_spread / 2.0
        for i in range(self.config.n_levels):
            bid_price = round(mid - half_spread - i * self.config.tick_size, 2)
            ask_price = round(mid + half_spread + i * self.config.tick_size, 2)
            for _ in range(self.config.orders_per_level):
                self.engine.book.add(Order(
                    side=Side.BUY,
                    qty=self.config.initial_qty,
                    price=bid_price,
                ))
                self.engine.book.add(Order(
                    side=Side.SELL,
                    qty=self.config.initial_qty,
                    price=ask_price,
                ))

    def _sample_limit_price(self, side: Side) -> float:
        mid = self.engine.book.mid_price()
        if mid is None:
            mid = self.config.initial_price
        half_spread = self.config.initial_spread / 2.0
        offset = max(
            self.rng.exponential(scale=self.config.limit_offset_scale),
            self.config.tick_size,
        )
        if side == Side.BUY:
            return round(mid - half_spread - offset, 2)
        return round(mid + half_spread + offset, 2)

    def _sample_qty(self, mean: float) -> int:
        return max(1, int(self.rng.exponential(mean)))

    def _submit_random_order(self, t: float) -> None:
        side = Side.BUY if self.rng.random() < 0.5 else Side.SELL
        is_market = self.rng.random() < self.config.market_order_prob
        if is_market:
            qty = self._sample_qty(self.config.market_qty_mean)
            order = Order(
                side=side, qty=qty, price=0.0,
                order_type=OrderType.MARKET, timestamp=t,
            )
        else:
            qty = self._sample_qty(self.config.limit_qty_mean)
            price = self._sample_limit_price(side)
            order = Order(
                side=side, qty=qty, price=price,
                order_type=OrderType.LIMIT, timestamp=t,
            )
        self.engine.submit(order)

    def _cancel_random_order(self) -> None:
        all_orders: List[Order] = []
        for level in self.engine.book.bids.values():
            all_orders.extend(level.orders)
        for level in self.engine.book.asks.values():
            all_orders.extend(level.orders)
        if not all_orders:
            return
        victim = all_orders[int(self.rng.integers(len(all_orders)))]
        self.engine.book.cancel(victim)

    def run(self) -> SimulationResult:
        cfg = self.config
        t = 0.0
        mid_series: List[Tuple[float, Optional[float]]] = [
            (0.0, self.engine.book.mid_price())
        ]
        total_rate = cfg.order_rate + cfg.cancel_rate

        while t < cfg.duration:
            dt = self.rng.exponential(1.0 / total_rate)
            t += dt
            if t > cfg.duration:
                break

            is_order = self.rng.random() < (cfg.order_rate / total_rate)
            if is_order:
                self._submit_random_order(t)
            else:
                self._cancel_random_order()

            mid_series.append((t, self.engine.book.mid_price()))

        return SimulationResult(
            trades=list(self.engine.trades),
            mid_series=mid_series,
            final_book=self.engine.book,
        )