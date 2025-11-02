"""Abstract broker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import Order, Position


class BrokerError(RuntimeError):
    """Raised when trade execution fails."""


class BrokerClient(ABC):
    """Common interface for trade execution backends."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return current open positions."""

    @abstractmethod
    def get_account_equity(self) -> float:
        """Return current account equity in USD."""

    @abstractmethod
    def submit_orders(self, orders: Sequence[Order]) -> list[dict]:
        """Submit one or more orders, returning backend acknowledgements."""

    def flatten_all(self) -> list[dict]:
        """Close all open positions by submitting opposite market orders."""

        positions = self.get_positions()
        closing_orders = []
        for position in positions:
            side = "sell" if position.quantity > 0 else "buy"
            closing_orders.append(
                Order(
                    symbol=position.symbol,
                    side=side,
                    quantity=abs(position.quantity),
                    order_type="market",
                    comment="Auto-flatten",
                )
            )
        return self.submit_orders(closing_orders)
