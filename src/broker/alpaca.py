"""Alpaca broker integration."""

from __future__ import annotations

import logging
from typing import Any, Sequence

import requests

from ..models import Order, Position
from .base import BrokerClient, BrokerError

LOGGER = logging.getLogger(__name__)


class AlpacaBrokerClient(BrokerClient):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets/v2",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        response = self._session.request(method, url, timeout=30, **kwargs)
        if response.status_code >= 400:
            LOGGER.error("Alpaca API error %s: %s", response.status_code, response.text)
            raise BrokerError(f"Alpaca API error {response.status_code}: {response.text}")
        if response.text:
            return response.json()
        return None

    def get_positions(self) -> list[Position]:
        records = self._request("GET", "/positions")
        positions: list[Position] = []
        for record in records or []:
            positions.append(
                Position(
                    symbol=record["symbol"].upper(),
                    quantity=float(record["qty"]),
                    avg_entry_price=float(record["avg_entry_price"]),
                )
            )
        return positions

    def get_account_equity(self) -> float:
        account = self._request("GET", "/account")
        return float(account["equity"])

    def submit_orders(self, orders: Sequence[Order]) -> list[dict]:
        responses: list[dict] = []
        for order in orders:
            payload = {
                "symbol": order.symbol,
                "qty": round(order.quantity, 4),
                "side": order.side,
                "type": order.order_type,
                "time_in_force": order.time_in_force,
            }
            if order.limit_price is not None:
                payload["limit_price"] = round(order.limit_price, 4)
            if order.comment:
                payload["client_order_id"] = order.comment[:48]

            LOGGER.info("Submitting Alpaca order: %s", payload)
            response = self._request("POST", "/orders", json=payload)
            responses.append(response)
        return responses
