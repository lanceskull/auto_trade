"""Order planning utilities that translate allocation directives into broker orders."""

from __future__ import annotations

import logging
from typing import Dict, Sequence

from .models import MarketData, Order, Position, StrategyDirective

LOGGER = logging.getLogger(__name__)


def plan_orders(
    directive: StrategyDirective,
    *,
    positions: Sequence[Position],
    market_data: Sequence[MarketData],
    equity: float,
    max_position_fraction: float,
    min_notional: float = 100.0,
) -> list[Order]:
    """Compute the orders required to implement the given strategy directive."""

    price_map: Dict[str, float] = {data.symbol: data.price for data in market_data if data.price}
    position_map: Dict[str, float] = {position.symbol: position.quantity for position in positions}

    orders: list[Order] = []

    symbols = set(price_map.keys()) | set(position_map.keys()) | set(directive.symbols())

    for symbol in symbols:
        price = price_map.get(symbol)
        current_qty = position_map.get(symbol, 0.0)

        allocation = next(
            (alloc for alloc in directive.target_allocations if alloc.symbol == symbol),
            None,
        )
        weight = allocation.weight if allocation else 0.0

        if abs(weight) > max_position_fraction:
            LOGGER.warning(
                "Clipping allocation weight for %s from %.3f to %.3f", symbol, weight, max_position_fraction
            )
            weight = max(-max_position_fraction, min(max_position_fraction, weight))

        if price is None or price <= 0:
            if weight != 0:
                LOGGER.warning("Skipping %s due to missing price data", symbol)
            target_qty = current_qty  # hold
        else:
            target_notional = weight * equity
            target_qty = target_notional / price if price else 0.0

        delta_qty = target_qty - current_qty
        notional_change = abs(delta_qty) * (price or 0)

        if notional_change < min_notional:
            continue

        if delta_qty > 0:
            side = "buy"
        else:
            side = "sell"

        orders.append(
            Order(
                symbol=symbol,
                side=side,
                quantity=abs(delta_qty),
                order_type="market",
                comment=(allocation.rationale if allocation else None),
            )
        )

    return orders
