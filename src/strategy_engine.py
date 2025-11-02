"""High-level orchestrator tying together market data, LLM directives, and execution."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .broker import BrokerClient
from .config import Settings
from .deepseek_client import DeepSeekClient, DeepSeekError
from .market import MarketDataProvider
from .models import MarketData, Position
from .planner import plan_orders
from .prompt_manager import PromptManager

LOGGER = logging.getLogger(__name__)


class StrategyEngine:
    def __init__(
        self,
        *,
        deepseek: DeepSeekClient,
        broker: BrokerClient,
        market_data: MarketDataProvider,
        prompts: PromptManager,
        settings: Settings,
        console: Console | None = None,
    ) -> None:
        self.deepseek = deepseek
        self.broker = broker
        self.market_data = market_data
        self.prompts = prompts
        self.settings = settings
        self.console = console or Console()

    async def run(self) -> None:
        self.prompts.ensure_prompt_file()

        while True:
            try:
                await self._run_once()
            except DeepSeekError as error:
                LOGGER.exception("DeepSeek error: %s", error)
            except Exception as error:  # noqa: BLE001
                LOGGER.exception("Unexpected error during strategy loop: %s", error)

            if self.settings.run_once:
                break

            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def _run_once(self) -> None:
        prompt = self.prompts.get_prompt()
        LOGGER.debug("Using prompt: %s", prompt)

        symbols = self.settings.symbols
        market_snapshot = self.market_data.get_snapshot(symbols)
        self._display_market_snapshot(market_snapshot)

        # Allow simulated broker to mark to market
        update_prices = getattr(self.broker, "update_market_prices", None)
        if callable(update_prices):
            update_prices(market_snapshot)

        positions = self.broker.get_positions()
        directive = self.deepseek.generate_directive(
            prompt,
            market_snapshot=market_snapshot,
            positions=positions,
        )

        self._display_directive(directive.summary, directive.target_allocations)

        equity = self.broker.get_account_equity()
        orders = plan_orders(
            directive,
            positions=positions,
            market_data=market_snapshot,
            equity=equity,
            max_position_fraction=self.settings.max_position_percent,
        )

        if not orders:
            LOGGER.info("No trades required this cycle.")
            return

        receipts = self.broker.submit_orders(orders)
        LOGGER.info("Submitted %d orders", len(receipts))

    def _display_market_snapshot(self, snapshot: Iterable[MarketData]) -> None:
        table = Table(title="Market Snapshot", show_lines=False)
        table.add_column("Symbol")
        table.add_column("Price", justify="right")
        table.add_column("Bid", justify="right")
        table.add_column("Ask", justify="right")
        table.add_column("Volume", justify="right")

        for data in snapshot:
            table.add_row(
                data.symbol,
                f"{data.price:.2f}" if data.price else "-",
                f"{data.bid:.2f}" if data.bid else "-",
                f"{data.ask:.2f}" if data.ask else "-",
                f"{data.volume:,.0f}" if data.volume else "-",
            )

        self.console.print(table)

    def _display_directive(self, summary: str, allocations) -> None:
        table = Table(title="DeepSeek Directive")
        table.add_column("Symbol")
        table.add_column("Weight", justify="right")
        table.add_column("Rationale", justify="left")

        for allocation in allocations:
            table.add_row(
                allocation.symbol,
                f"{allocation.weight:.2%}",
                allocation.rationale or "-",
            )

        panel = Panel.fit(summary or "No summary", title="Strategy Summary", border_style="cyan")
        self.console.print(panel)
        self.console.print(table)
