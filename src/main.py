"""CLI entrypoint for the DeepSeek-powered quant trading client."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from .broker import AlpacaBrokerClient, BrokerClient, SimulatedBrokerClient
from .config import Settings, load_settings
from .deepseek_client import DeepSeekClient
from .logger import configure_logging
from .market import AlpacaMarketDataProvider, MarketDataProvider, SimulatedMarketDataProvider
from .prompt_manager import PromptManager
from .strategy_engine import StrategyEngine

app = typer.Typer(help="DeepSeek strategy runner for US equities.")


def _build_market_data(settings: Settings) -> MarketDataProvider:
    if settings.broker_backend == "alpaca":
        if not settings.alpaca_api_key or not settings.alpaca_api_secret:
            raise typer.BadParameter("ALPACA_API_KEY and ALPACA_API_SECRET must be set for Alpaca backend")
        return AlpacaMarketDataProvider(
            api_key=settings.alpaca_api_key,
            api_secret=settings.alpaca_api_secret,
            base_url=settings.alpaca_data_base_url,
        )
    return SimulatedMarketDataProvider()


def _build_broker(settings: Settings) -> BrokerClient:
    if settings.broker_backend == "alpaca":
        if not settings.alpaca_api_key or not settings.alpaca_api_secret:
            raise typer.BadParameter("ALPACA_API_KEY and ALPACA_API_SECRET must be set for Alpaca backend")
        return AlpacaBrokerClient(
            api_key=settings.alpaca_api_key,
            api_secret=settings.alpaca_api_secret,
            base_url=settings.alpaca_trading_base_url,
        )
    return SimulatedBrokerClient()


@app.command()
def run(
    prompt_file: Path = typer.Option(
        None,
        help="Path to the prompt file used to condition DeepSeek.",
    ),
    symbols: list[str] = typer.Option(
        None,
        help="Comma separated list of ticker symbols to trade.",
    ),
    once: bool = typer.Option(False, help="Run only a single iteration for testing."),
) -> None:
    """Start the continuous trading loop."""

    load_dotenv()

    settings = load_settings(prompt_file)
    if symbols:
        settings.symbols = [symbol.upper() for symbol in symbols]
    settings.run_once = once or settings.run_once

    if not settings.deepseek_api_key:
        raise typer.BadParameter("DEEPSEEK_API_KEY must be provided.")

    configure_logging(settings.log_level)
    console = Console()

    prompt_manager = PromptManager(settings.prompt_file)
    market_data = _build_market_data(settings)
    broker = _build_broker(settings)
    deepseek_client = DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_api_base,
        model=settings.deepseek_model,
    )

    engine = StrategyEngine(
        deepseek=deepseek_client,
        broker=broker,
        market_data=market_data,
        prompts=prompt_manager,
        settings=settings,
        console=console,
    )

    asyncio.run(engine.run())


@app.command("prompt")
def set_prompt(
    text: str = typer.Argument(..., help="New prompt text for the strategy."),
    prompt_file: Optional[Path] = typer.Option(None, help="Optional path to prompt file."),
) -> None:
    """Overwrite the current strategy prompt."""

    load_dotenv()
    settings = load_settings(prompt_file)
    manager = PromptManager(settings.prompt_file)
    manager.update_prompt(text)
    typer.secho(f"Updated prompt at {settings.prompt_file}", fg=typer.colors.GREEN)


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
