"""Prompt management, allowing hot-reloads from a text file."""

from __future__ import annotations

from pathlib import Path


DEFAULT_PROMPT = """You are managing a market-neutral US equities strategy. Optimize for Sharpe ratio while respecting risk constraints."""


class PromptManager:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._last_mtime: float | None = None
        self._prompt_cache: str = ""

    def ensure_prompt_file(self) -> None:
        if not self.path.exists():
            self.path.write_text(DEFAULT_PROMPT, encoding="utf-8")
            self._last_mtime = self.path.stat().st_mtime
            self._prompt_cache = DEFAULT_PROMPT

    def get_prompt(self) -> str:
        """Return the latest prompt contents, reloading if the file changed."""

        if not self.path.exists():
            self.ensure_prompt_file()

        current_mtime = self.path.stat().st_mtime
        if self._last_mtime is None or current_mtime > self._last_mtime:
            self._prompt_cache = self.path.read_text(encoding="utf-8")
            self._last_mtime = current_mtime
        return self._prompt_cache

    def update_prompt(self, new_prompt: str) -> None:
        self.path.write_text(new_prompt, encoding="utf-8")
        self._last_mtime = self.path.stat().st_mtime
        self._prompt_cache = new_prompt
