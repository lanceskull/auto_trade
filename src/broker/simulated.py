"""In-memory paper trading broker used for development and testing."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, Iterable, Sequence

from ..models import MarketData, Order, Position
from .base import BrokerClient, BrokerError

LOGGER = logging.getLogger(__name__)


class SimulatedBrokerClient(BrokerClient):
    def __init__(self, starting_cash: float = 1_000_000.0) -> None:
        self.cash = starting_cash
        self._positions: Dict[str, Position] = {}
        self._last_prices: Dict[str, float] = defaultdict(lambda: 0.0)

    def update_market_prices(self, snapshot: Iterable[MarketData]) -> None:
        for data in snapshot:
            if data.price:
                self._last_prices[data.symbol] = data.price

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_account_equity(self) -> float:
        equity = self.cash
        for symbol, position in self._positions.items():
            last_price = self._last_prices.get(symbol)
            if last_price:
                equity += position.quantity * last_price
        return equity

    def submit_orders(self, orders: Sequence[Order]) -> list[dict]:
        receipts: list[dict] = []
        for order in orders:
            price = order.limit_price or self._last_prices.get(order.symbol)
            if not price:
                raise BrokerError(
                    f"No price available for {order.symbol}. Provide a limit price or update market data."
                )

            quantity = order.quantity if order.side == "buy" else -order.quantity
            cost = price * quantity
            self.cash -= cost

            LOGGER.info(
                "Simulated fill: %s %s @ %.2f (qty=%.4f)",
                order.side.upper(),
                order.symbol,
                price,
                order.quantity,
            )

            existing = self._positions.get(order.symbol)
            if existing is None:
                avg_price = price
                new_qty = quantity
            else:
                new_qty = existing.quantity + quantity
                if new_qty == 0:
                    avg_price = 0.0
                else:
                    avg_price = (
                        existing.avg_entry_price * existing.quantity + price * quantity
                    ) / new_qty

            if new_qty == 0:
                self._positions.pop(order.symbol, None)
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=new_qty,
                    avg_entry_price=avg_price,
                )

            receipts.append(
                {
                    "symbol": order.symbol,
                    "side": order.side,
                    "filled_qty": quantity,
                    "price": price,
                    "cash_balance": self.cash,
                }
            )

        return receipts
