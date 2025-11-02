"""Alpaca market data provider."""

from __future__ import annotations

import logging
from typing import Any, Iterable

import requests

from ..models import MarketData
from .base import MarketDataProvider

LOGGER = logging.getLogger(__name__)


class AlpacaMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://data.alpaca.markets/v2",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            }
        )

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self._session.get(url, params=params, timeout=30)
        if response.status_code >= 400:
            LOGGER.error("Alpaca data error %s: %s", response.status_code, response.text)
            raise RuntimeError(f"Alpaca data error {response.status_code}: {response.text}")
        return response.json()

    def get_snapshot(self, symbols: Iterable[str]) -> list[MarketData]:
        snapshots: list[MarketData] = []
        for symbol in symbols:
            data = self._request(f"/stocks/{symbol}/snapshot")
            latest_trade = data.get("latestTrade") or {}
            latest_quote = data.get("latestQuote") or {}
            market_data = MarketData(
                symbol=symbol,
                price=float(latest_trade.get("price") or latest_quote.get("midpoint") or 0.0),
                bid=float(latest_quote.get("bp") or 0.0) or None,
                ask=float(latest_quote.get("ap") or 0.0) or None,
                volume=float(latest_trade.get("size") or 0.0) or None,
            )
            snapshots.append(market_data)
        return snapshots
