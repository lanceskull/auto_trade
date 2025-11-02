# DeepSeek Quant Trading Client

An autonomous US equities trading loop that combines the latest DeepSeek large language model with configurable execution backends. The agent continuously ingests market data, queries the DeepSeek model for allocation directives driven by a prompt you control, and converts the model output into executable orders via either a live Alpaca brokerage connection or an in-memory simulator.

## Features

- Continuous strategy execution with configurable polling interval
- Prompt-driven strategy updates: edit `strategy_prompt.txt` on disk or use the CLI to change behaviour in real time
- DeepSeek chat-completions integration with enforced JSON directives
- Order planning layer that converts allocation targets into delta orders with position limits
- Broker abstraction supporting Alpaca (paper/live) and an offline simulator for sandbox testing
- Rich terminal dashboards for market snapshots and strategy directives every cycle

## Quick Start

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEEPSEEK_API_KEY="your_deepseek_key"
# Optional for live trading
export BROKER_BACKEND="alpaca"
export ALPACA_API_KEY="your_alpaca_key"
export ALPACA_API_SECRET="your_alpaca_secret"

python -m src.main run
```

The first run creates `strategy_prompt.txt`. Update the prompt at any time to influence the next DeepSeek directive.

## Configuration

Configuration is driven by environment variables and optional CLI flags:

| Variable | Default | Description |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | - | API key for DeepSeek chat completions (required) |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com/v1` | Base URL for DeepSeek API |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name to query |
| `BROKER_BACKEND` | `simulated` | `simulated` or `alpaca` |
| `ALPACA_API_KEY` / `ALPACA_API_SECRET` | - | Credentials for Alpaca trading/data |
| `POLL_INTERVAL_SECONDS` | `60` | Seconds between strategy refreshes |
| `TRADER_SYMBOLS` | `AAPL,MSFT,NVDA` | Comma separated watchlist |
| `MAX_POSITION_PERCENT` | `0.3` | Max fraction of equity per symbol |
| `PROMPT_FILE` | `strategy_prompt.txt` | Path to monitored prompt file |

CLI overrides:

```shell
python -m src.main run --symbols AAPL --symbols MSFT --once
python -m src.main prompt "Rotate into semiconductor momentum while hedged with QQQ shorts."
```

## Strategy Loop

Each cycle performs the following steps:

1. Load the active prompt (auto-refresh when the file changes)
2. Pull the latest market snapshot from the configured provider
3. Send prompt plus state context to DeepSeek and parse the JSON directive
4. Convert target allocations into incremental orders while respecting risk limits
5. Submit orders through the selected broker backend

The loop runs indefinitely unless `--once` or `RUN_ONCE=true` is used.

## Extending

- Implement new brokers by subclassing `broker.base.BrokerClient`
- Add custom market data feeds under `market/`
- Enhance planning logic in `planner.plan_orders` for advanced risk or execution handling
- Integrate persistence or analytics layers by extending `StrategyEngine`

## Disclaimer

This project is provided for educational purposes. Automated trading in live markets carries significant financial risk. Validate thoroughly in simulation and comply with all regulatory requirements before deploying to production.
