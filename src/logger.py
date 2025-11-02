"""Logging configuration utilities."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def configure_logging(level: str = "INFO", *, console: Optional[Console] = None) -> None:
    """Configure global logging with Rich handler."""

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RichHandler(
                console=console or Console(file=sys.stderr),
                show_path=False,
                rich_tracebacks=True,
            )
        ],
    )
