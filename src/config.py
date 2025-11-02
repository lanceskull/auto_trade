"""Configuration management for the DeepSeek quant trading client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, validator


class Settings(BaseModel):
    """Application settings sourced from environment variables or CLI overrides."""

    deepseek_api_key: str | None = Field(default=None, repr=False)
    deepseek_api_base: str = Field(
        default="https://api.deepseek.com/v1", description="DeepSeek REST API base URL"
    )
    deepseek_model: str = Field(default="deepseek-chat", description="Model identifier")

    broker_backend: str = Field(
        default="simulated",
        description="Broker backend to use: simulated or alpaca",
    )

    alpaca_api_key: str | None = Field(default=None, repr=False)
    alpaca_api_secret: str | None = Field(default=None, repr=False)
    alpaca_trading_base_url: str = Field(
        default="https://paper-api.alpaca.markets/v2",
        description="Base URL for Alpaca trading endpoints.",
    )
    alpaca_data_base_url: str = Field(
        default="https://data.alpaca.markets/v2",
        description="Base URL for Alpaca data endpoints.",
    )

    symbols: List[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA"],
        description="Universe of tradable symbols.",
    )
    poll_interval_seconds: int = Field(
        default=60,
        ge=5,
        description="Interval for refreshing market data and strategy directives.",
    )
    prompt_file: Path = Field(
        default=Path("strategy_prompt.txt"),
        description="Path to the strategy prompt file monitored for updates.",
    )
    max_position_percent: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Maximum fraction of account equity allocated per symbol.",
    )
    risk_free_rate: float = Field(
        default=0.03,
        ge=-1,
        description="Annualized risk-free rate applied in analytics.",
    )
    base_currency: str = Field(default="USD", description="Account base currency.")
    run_once: bool = Field(
        default=False,
        description="Execute a single loop iteration for testing instead of continuous run.",
    )

    log_level: str = Field(default="INFO", description="Python logging level name.")

    class Config:
        arbitrary_types_allowed = True

    @validator("broker_backend")
    def _validate_backend(cls, value: str) -> str:  # noqa: N805
        value = value.lower()
        if value not in {"simulated", "alpaca"}:
            raise ValueError(
                "Unsupported broker backend. Choose between 'simulated' or 'alpaca'."
            )
        return value

    @validator("symbols", pre=True)
    def _split_symbols(cls, value: str | list[str]) -> list[str]:  # noqa: N805
        if isinstance(value, str):
            return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
        return [symbol.upper() for symbol in value]

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""

        symbols = os.getenv("TRADER_SYMBOLS")

        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_api_base=os.getenv("DEEPSEEK_API_BASE", cls.model_fields["deepseek_api_base"].default),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", cls.model_fields["deepseek_model"].default),
            broker_backend=os.getenv("BROKER_BACKEND", cls.model_fields["broker_backend"].default),
            alpaca_api_key=os.getenv("ALPACA_API_KEY"),
            alpaca_api_secret=os.getenv("ALPACA_API_SECRET"),
            alpaca_trading_base_url=os.getenv(
                "ALPACA_TRADING_BASE_URL",
                cls.model_fields["alpaca_trading_base_url"].default,
            ),
            alpaca_data_base_url=os.getenv(
                "ALPACA_DATA_BASE_URL",
                cls.model_fields["alpaca_data_base_url"].default,
            ),
            symbols=symbols if symbols else cls.model_fields["symbols"].default_factory(),
            poll_interval_seconds=int(
                os.getenv(
                    "POLL_INTERVAL_SECONDS",
                    cls.model_fields["poll_interval_seconds"].default,
                )
            ),
            prompt_file=Path(
                os.getenv(
                    "PROMPT_FILE", str(cls.model_fields["prompt_file"].default)
                )
            ),
            max_position_percent=float(
                os.getenv(
                    "MAX_POSITION_PERCENT",
                    cls.model_fields["max_position_percent"].default,
                )
            ),
            risk_free_rate=float(
                os.getenv("RISK_FREE_RATE", cls.model_fields["risk_free_rate"].default)
            ),
            base_currency=os.getenv(
                "BASE_CURRENCY", cls.model_fields["base_currency"].default
            ),
            run_once=os.getenv("RUN_ONCE", "false").lower() in {"1", "true", "yes"},
            log_level=os.getenv("LOG_LEVEL", cls.model_fields["log_level"].default),
        )


def load_settings(prompt_file: Path | None = None) -> Settings:
    """Helper to load settings with an optional prompt file override."""

    settings = Settings.from_env()
    if prompt_file is not None:
        settings.prompt_file = prompt_file
    return settings
