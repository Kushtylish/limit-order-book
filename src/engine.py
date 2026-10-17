from dataclasses import dataclass
from typing import List
from src.order import Order, Side, OrderType
from src.book import OrderBook


@dataclass
class Trade:
    price: float
    qty: float
    taker_id: int
    maker_id: int
    taker_side: Side
    timestamp: float = 0.0


class MatchingEngine:
    """
    Continuous double auction matching engine.

    Rules:
    - Buy orders match against resting asks while crossing (or always, if market).
    - Sell orders match against resting bids while crossing (or always, if market).
    - Within a price level, FIFO.
    - Trades print at the *passive* order's price (standard exchange convention).
    - Limit order remainder rests in the book.
    - Market order remainder is discarded (no resting).
    """

    def __init__(self):
        self.book = OrderBook()
        self.trades: List[Trade] = []

    def submit(self, order: Order) -> List[Trade]:
        if order.side == Side.BUY:
            new_trades = self._match_buy(order)
        else:
            new_trades = self._match_sell(order)

        if order.qty > 0 and order.order_type == OrderType.LIMIT:
            self.book.add(order)

        self.trades.extend(new_trades)
        return new_trades

    def _match_buy(self, order: Order) -> List[Trade]:
        trades = []
        while order.qty > 0 and self.book.asks:
            best_ask = self.book.best_ask()
            if order.order_type == OrderType.LIMIT and order.price < best_ask:
                break

            level = self.book.asks[best_ask]
            while order.qty > 0 and level.orders:
                passive = level.orders[0]
                trade_qty = min(order.qty, passive.qty)

                trades.append(Trade(
                    price=best_ask,
                    qty=trade_qty,
                    taker_id=order.order_id,
                    maker_id=passive.order_id,
                    taker_side=Side.BUY,
                    timestamp=order.timestamp,
                ))

                order.qty -= trade_qty
                passive.qty -= trade_qty
                level.total_qty -= trade_qty

                if passive.qty <= 0:
                    level.orders.pop(0)

            if not level.orders:
                del self.book.asks[best_ask]

        return trades

    def _match_sell(self, order: Order) -> List[Trade]:
        trades = []
        while order.qty > 0 and self.book.bids:
            best_bid = self.book.best_bid()
            if order.order_type == OrderType.LIMIT and order.price > best_bid:
                break

            level = self.book.bids[best_bid]
            while order.qty > 0 and level.orders:
                passive = level.orders[0]
                trade_qty = min(order.qty, passive.qty)

                trades.append(Trade(
                    price=best_bid,
                    qty=trade_qty,
                    taker_id=order.order_id,
                    maker_id=passive.order_id,
                    taker_side=Side.SELL,
                    timestamp=order.timestamp,
                ))

                order.qty -= trade_qty
                passive.qty -= trade_qty
                level.total_qty -= trade_qty

                if passive.qty <= 0:
                    level.orders.pop(0)

            if not level.orders:
                del self.book.bids[best_bid]

        return trades