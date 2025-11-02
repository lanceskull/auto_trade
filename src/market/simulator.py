"""Random-walk market data simulator for offline testing."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, Iterable

from ..models import MarketData
from .base import MarketDataProvider


class SimulatedMarketDataProvider(MarketDataProvider):
    def __init__(self, *, seed: int | None = None, base_price: float = 100.0) -> None:
        self.random = random.Random(seed)
        self.base_price = base_price
        self._prices: Dict[str, float] = {}

    def get_snapshot(self, symbols: Iterable[str]) -> list[MarketData]:
        snapshot: list[MarketData] = []
        for symbol in symbols:
            price = self._prices.get(symbol, self.base_price)
            drift = self.random.gauss(mu=0, sigma=0.5)
            price = max(1.0, price * (1 + drift / 100))
            self._prices[symbol] = price
            bid = price * (1 - 0.0005)
            ask = price * (1 + 0.0005)
            volume = abs(self.random.gauss(mu=1_000_000, sigma=250_000))

            snapshot.append(
                MarketData(
                    symbol=symbol,
                    price=price,
                    bid=bid,
                    ask=ask,
                    volume=volume,
                    timestamp=datetime.utcnow(),
                )
            )
        return snapshot
