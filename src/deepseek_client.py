"""Client for interacting with DeepSeek chat completion API."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, Sequence

import requests

from .models import MarketData, Position, StrategyDirective, TargetAllocation, normalize_allocations

LOGGER = logging.getLogger(__name__)


class DeepSeekError(RuntimeError):
    """Raised when the DeepSeek API returns an error."""


class DeepSeekClient:
    """Simple REST client wrapping DeepSeek chat completions."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()

    def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
        }
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        LOGGER.debug("Sending request to DeepSeek: %s", payload)
        response = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:  # noqa: BLE001
                detail = {"text": response.text}
            raise DeepSeekError(f"DeepSeek API error {response.status_code}: {detail}")

        data = response.json()
        LOGGER.debug("Received response from DeepSeek: %s", data)
        return data

    def generate_directive(
        self,
        prompt: str,
        *,
        market_snapshot: Iterable[MarketData],
        positions: Iterable[Position],
    ) -> StrategyDirective:
        """Call DeepSeek with the trading prompt and parse the resulting directive."""

        if not self.api_key:
            raise DeepSeekError("Missing DEEPSEEK_API_KEY environment variable.")

        system_prompt = _build_system_prompt()
        context_message = _build_context_message(market_snapshot, positions)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt.strip()},
            {"role": "user", "content": context_message},
        ]

        response = self.chat(
            messages,
            response_format={"type": "json_object"},
        )

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as error:
            raise DeepSeekError(f"Unexpected DeepSeek response format: {response}") from error

        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise DeepSeekError(
                "DeepSeek response was not valid JSON. Ensure the prompt enforces JSON output."
            ) from error

        return _parse_directive(data)


def _build_system_prompt() -> str:
    return (
        "You are an autonomous US equities portfolio manager. "
        "Always respond with JSON that follows this schema: "
        "{\n"
        "  \"summary\": string,\n"
        "  \"target_allocations\": [\n"
        "    {\n"
        "      \"symbol\": string,\n"
        "      \"weight\": number between -1 and 1,\n"
        "      \"rationale\": string\n"
        "    }\n"
        "  ],\n"
        "  \"confidence\": number between 0 and 1 optional,\n"
        "  \"holding_period_minutes\": integer optional,\n"
        "  \"risk_notes\": string optional\n"
        "}\n"
        "Weights represent target fraction of account equity (e.g. 0.25 = 25% long, -0.1 = 10% short)."
    )


def _build_context_message(
    market_snapshot: Iterable[MarketData],
    positions: Iterable[Position],
) -> str:
    market_lines = ["Market snapshot:"]
    for data in market_snapshot:
        parts = [
            f"symbol={data.symbol}",
            f"price={data.price:.2f}",
        ]
        if data.bid is not None and data.ask is not None:
            parts.append(f"bid/ask={data.bid:.2f}/{data.ask:.2f}")
        if data.volume is not None:
            parts.append(f"volume={data.volume:.0f}")
        market_lines.append("  " + ", ".join(parts))

    position_lines = ["Open positions:"]
    for position in positions:
        position_lines.append(
            f"  symbol={position.symbol}, qty={position.quantity:.4f}, avg_price={position.avg_entry_price:.2f}"
        )

    if len(position_lines) == 1:
        position_lines.append("  none")

    return "\n".join(market_lines + position_lines)


def _parse_directive(payload: Dict[str, Any]) -> StrategyDirective:
    summary = payload.get("summary", "")
    confidence = payload.get("confidence")
    holding_period = payload.get("holding_period_minutes")
    risk_notes = payload.get("risk_notes")

    raw_allocations = payload.get("target_allocations", [])
    allocations: list[TargetAllocation] = []
    for item in raw_allocations:
        try:
            symbol = item["symbol"].upper()
            weight = float(item["weight"])
            rationale = item.get("rationale")
        except (KeyError, TypeError, ValueError) as error:
            LOGGER.warning("Skipping malformed allocation %s: %s", item, error)
            continue
        allocations.append(TargetAllocation(symbol=symbol, weight=weight, rationale=rationale))

    normalized_allocations = normalize_allocations(allocations)

    return StrategyDirective(
        summary=summary,
        target_allocations=normalized_allocations,
        confidence=confidence,
        holding_period_minutes=holding_period,
        risk_notes=risk_notes,
    )
