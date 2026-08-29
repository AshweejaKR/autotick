# AutoTick

AutoTick is a modular, broker-independent algorithmic trading framework for Live, Paper, Backtest, and Replay modes.

## Goals

- Use the same strategy contract in every mode.
- Keep broker SDK code inside broker adapters.
- Select providers through ProviderFactory.
- Keep order, risk, and session behavior outside strategies.
- Add production features only in their planned phase.

## Current Status

- Version: 0.1.0
- Completed milestones: Foundation, Mode-Neutral Core, Strategy Framework, Provider Layer, Execution and Risk, Trading Modes
- Completed phases: 1 through 24
- Provider cleanup: completed
- Current milestone: Recovery and Persistence
- Next phase: Phase 25 - persistence, recovery, and reconciliation
- Automated tests: intentionally deferred until Phase 29

## Implemented Architecture

### Foundation and Core

- YAML loading, path resolution, and validation.
- Normalized market, signal, order, position, trade, account, and event models.
- MarketData, Account, and Execution provider contracts.
- ProviderFactory and ProviderBundle mode mapping.
- Shared broker sessions through SessionPool.
- CalendarSessionManager for realtime, fast, and replay clocks.
- EventDispatcher and TradingEngine core components.
- Centralized colored console logging and plain rotating file logging.

### Strategy

- SMA indicator with default period 20.
- Strategy base and StrategyContext.
- Simple long strategy:
  - Load the latest completed daily close during initial setup.
  - Generate BUY when LTP is greater than previous close by 0.5%.
  - Generate no signal otherwise.
- SignalValidator performs structural validation only.
- RiskManager and TradeManager own quantity and order workflow.

### Providers

- HistoricalProvider returns normalized list[MarketBar] data.
- get_bars() accepts optional start and end dates.
- Default end: current provider time.
- Default start: 5 days earlier, or 30 days for daily bars.
- AngelOne session, account, market-data, and execution adapters.
- Simulated session, shared state, account, market-data, and execution adapters.
- AngelOne and simulated adapters use aligned constructors, exchanges, arguments, and normalized return models.
- Simulated setters are input helpers, not shared interface methods.

## Mode Mapping

| Mode | Market data | Account | Execution | Clock |
|---|---|---|---|---|
| Live | Selected broker | Selected broker | Selected broker | Realtime |
| Paper, UI disabled | Selected broker | Simulated | Simulated | Realtime |
| Paper, UI enabled | Shared UI simulated data | Simulated | Simulated | Realtime |
| Backtest | HistoricalProvider | Simulated | Simulated | Fast |
| Replay | HistoricalProvider | Simulated | Simulated | Replay speed |

Paper orders never reach the broker. MARKET orders use the active market-data provider's current LTP and fill in simulated execution.

## Paper UI Behavior

Set simulated.ui_data_enabled to true to start the Windows control panel and Paper runner in one process.

- The UI controls balance, funds, ticks, LTP, volume, price changes, CSV data, and bars.
- The UI and strategy share one SimulatedSession and SimulatedState.
- broker_auto_fetch false keeps UI data fully manual.
- broker_auto_fetch true copies initial data from the selected real broker.
- broker_auto_fetch is used only when UI data is enabled.
- When UI is disabled, normal Paper mode uses the selected broker for market data.

## Realtime Market-Hours Behavior

- only_market_hours true: if the market is closed, log a warning and exit the realtime loop.
- only_market_hours false: ignore the market-hours gate and keep processing at engine.loop_sleep_s intervals.
- Live and Paper use wall-clock time.
- Backtest and Replay use historical timestamps.
- POSITIONAL orders are not automatically squared off.
- TradeManager exposes intraday square-off, but the current CLI runner does not call it yet.

Running Paper with only_market_hours false can use stale after-market broker LTP. Use true for normal market-hours Paper runs.

## Execution and Risk

Implemented core behavior:

- Order states: NEW, VALIDATED, SUBMITTED, OPEN, PARTIAL, FILLED, REJECTED, CANCELLED, EXPIRED.
- Risk-based quantity cap using capital, risk percentage, price, and stop-loss distance.
- Filled ENTRY orders increment the daily trade count.
- max_trades_per_day activates the kill switch.
- Stop-loss and target price helpers.
- Position lifecycle, exposure, realized P&L, and unrealized P&L methods.
- Intraday-only square-off method.

Current CLI runner wiring:

- Uses signal validation, risk sizing, order creation, and filled-entry counting.
- Does not yet monitor target, stop-loss, trailing stop, or P&L exits.
- Does not yet call automatic square-off.
- persistence configuration is validated but persistence starts in Phase 25.

## Logging

Console colors:

- ERROR: red
- WARNING: yellow
- INFO: white
- DONE: green

Use logger.done() for successful completions such as login, logout, token refresh, configuration load, order placement, and shutdown. Rotating log files remain plain text without color codes.

## Configuration

The only default YAML is config/default.yaml. Relative credential and CSV paths resolve from the YAML file's directory.

Important flags:

- mode: live, paper, backtest, or replay
- broker: selected broker adapter
- simulated.ui_data_enabled: enable Paper control panel
- simulated.broker_auto_fetch: load UI starting data from a real broker
- session.only_market_hours: enforce or ignore the realtime market-hours gate
- trade.position_type: INTRADAY or POSITIONAL

## Running

Install the package in editable mode:

    python -m pip install -e .

Run with the default configuration:

    python -m autotick.main

Run with another configuration:

    python -m autotick.main --config path/to/config.yaml

The installed command is also available:

    autotick

## Manual Tools

Provider check:

    python provider_test.py

- Put angelone_keys.env beside config/default.yaml when that relative path is configured.
- GET_MARKET_DATA stays false until manual market-data calls are intended.
- PLACE_LIVE_ORDERS stays false until live BUY/SELL testing is explicitly intended.
- AngelOne order APIs require the API application's registered static public IP.
- Rejected orders have no broker order ID, so status lookup is skipped.

Windows simulated control panel:

    python simulated_control_panel.py

The control panel is normally started automatically by main.py when simulated.ui_data_enabled is true.

## Roadmap

See [PLAN.md](PLAN.md) for milestone tracking and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture and current implementation rules.
