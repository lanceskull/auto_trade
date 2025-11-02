"""Abstract market data provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ..models import MarketData


class MarketDataProvider(ABC):
    @abstractmethod
    def get_snapshot(self, symbols: Iterable[str]) -> list[MarketData]:
        """Fetch the latest market snapshot for the given symbols."""
