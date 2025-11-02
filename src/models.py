"""Core data models used by the trading client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Sequence


@dataclass(slots=True)
class MarketData:
    symbol: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume: float | None = None
    timestamp: datetime | None = None


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float


@dataclass(slots=True)
class TargetAllocation:
    symbol: str
    weight: float
    rationale: str | None = None


@dataclass(slots=True)
class StrategyDirective:
    summary: str
    target_allocations: Sequence[TargetAllocation]
    confidence: float | None = None
    holding_period_minutes: int | None = None
    risk_notes: str | None = None

    def symbols(self) -> List[str]:
        return [allocation.symbol for allocation in self.target_allocations]


@dataclass(slots=True)
class Order:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    limit_price: float | None = None
    time_in_force: str = "day"
    comment: str | None = None


def normalize_allocations(
    allocations: Iterable[TargetAllocation],
) -> list[TargetAllocation]:
    """Normalize allocation weights to sum to 1.0 while preserving rationale."""

    allocations = list(allocations)
    total = sum(abs(a.weight) for a in allocations)
    if total == 0:
        return allocations

    normalized: list[TargetAllocation] = []
    for allocation in allocations:
        weight = allocation.weight / total
        normalized.append(
            TargetAllocation(
                symbol=allocation.symbol,
                weight=weight,
                rationale=allocation.rationale,
            )
        )
    return normalized
