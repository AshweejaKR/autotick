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
- Completed milestones: Foundation, Mode-Neutral Core, Strategy Framework, Provider Layer, Execution and Risk, Trading Modes, Recovery and Persistence, Reports
- Completed phases: 1 through 28
- Provider cleanup: completed
- Current milestone: Testing
- Next phase: Phase 29 - unit and provider-contract tests
- Automated tests: intentionally deferred until Phase 29

## Implemented Architecture

### Foundation and Core

- YAML loading, path resolution, and validation.
- Normalized market, signal, order, position, trade, account, and event models.
- MarketData, Account, and Execution provider contracts.
- ProviderFactory and ProviderBundle mode mapping.
- Shared broker sessions through SessionPool.
- CalendarSessionManager for DAILY, WEEKLY, and ALWAYS_OPEN schedules across realtime, fast, and replay clocks.
- EventDispatcher and TradingEngine core components.
- Broker-neutral ReconnectManager with hybrid retry policy.
- Centralized colored console logging and plain rotating file logging.
- Shared production secret-file validation for AngelOne broker access.
- Append-only completed-trade CSV reporting with strategy and combined summaries.

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

Paper orders never reach the broker. MARKET orders use the active market-data provider's current LTP and fill in simulated execution. Filled buys subtract their cost from simulated funds; filled sells add proceeds and realized P&L. Buys with insufficient funds are rejected.

## Paper UI Behavior

Set simulated.ui_data_enabled to true to start the Windows control panel and Paper runner in one process.

- The UI controls balance, funds, ticks, LTP, volume, price changes, CSV data, and bars.
- The displayed balance, margin, and buying power refresh every 500 ms after simulated fills.
- The UI and strategy share one SimulatedSession and SimulatedState.
- broker_auto_fetch false keeps UI data fully manual.
- broker_auto_fetch true copies initial data from the selected real broker.
- broker_auto_fetch is used only when UI data is enabled.
- When UI is disabled, normal Paper mode uses the selected broker for market data.

## Market Schedule Behavior

One AutoTick run supports one market and one exchange. Configure one calendar profile for all symbols in that run.

| schedule_type | Use case | Required schedule fields |
|---|---|---|
| DAILY | Equity and other daily sessions | trading_days, market_start, market_end, square_off_time |
| WEEKLY | Forex and other weekly sessions | week_start_day/time, week_end_day/time; optional daily_break_start/end |
| ALWAYS_OPEN | Spot crypto and other continuous markets | no opening or closing times |

- timezone is required and uses an IANA name such as Asia/Kolkata, America/New_York, or UTC.
- closed_dates optionally closes specific dates for DAILY and WEEKLY schedules.
- only_market_hours true: Live and Paper check the calendar before provider login, subscription, or strategy setup. A closed market logs a warning with the next opening and stops the runner.
- only_market_hours false: the schedule gate is ignored and processing continues every engine.loop_sleep_s.
- Realtime strategy tick processing is independent of account balance. A zero balance keeps on_tick() active while RiskManager blocks order submission.
- Live and Paper use wall-clock time. Backtest and Replay use historical timestamps.
- DAILY supports configured square-off timing. WEEKLY and ALWAYS_OPEN do not create an automatic daily square-off signal.
- POSITIONAL orders are not automatically squared off. TradeManager exposes intraday square-off, but the current CLI runner does not call it yet.

Running Paper with only_market_hours false can use stale after-market broker LTP. Keep the gate enabled for normal exchange-hours Paper runs.

## Execution and Risk

Implemented core behavior:

- Order states: NEW, VALIDATED, SUBMITTED, OPEN, PARTIAL, FILLED, REJECTED, CANCELLED, EXPIRED.
- Risk-based quantity cap using capital, risk percentage, price, and stop-loss distance.
- Filled ENTRY orders increment the daily trade count.
- max_trades_per_day activates the kill switch.
- Stop-loss, target, and trailing-stop price helpers.
- Filled entries create tracked positions with fixed stop-loss and target levels.
- Target activates trailing protection when trailing_sl_pct is greater than zero; zero exits directly at target.
- Position lifecycle, exposure, realized P&L, and unrealized P&L methods.
- Intraday-only square-off method.

Current CLI runner wiring:

- Uses signal validation, risk sizing, order creation, and filled-entry counting.
- Monitors fixed stop-loss and target-activated trailing-stop exits on every tick.
- Reconciles pending broker orders before monitoring filled positions.
- Logs rounded buy/sell prices, cost/proceeds, stop-loss, target, P&L, and remaining simulated funds.
- Does not yet call automatic square-off.
- Saves changed runtime state and reconciles it before strategy startup.

## Persistence and Recovery

- Python's built-in SQLite stores state in `state/autotick.db`; no extra database package is required.
- One database file keeps separate profile rows by mode, broker, exchange, strategy, and symbols.
- Live and Paper restore managed orders, positions, trades, exit levels, trailing state, and daily risk state.
- Paper also restores simulated funds, positions, orders, trades, and realized P&L.
- Live reconciliation trusts broker status and quantity only for known AutoTick records.
- Unknown manual broker orders and holdings are logged, left unmanaged, and blocked from duplicate AutoTick entries.
- Same-day unresolved orders and runtime save failures activate the kill switch for new entries while protective exits remain available.
- Backtest and Replay start fresh and save final state for reporting; historical cursor resume is not part of Phase 25.
- Live and broker-backed Paper pause processing during broker recovery.
- Temporary network and service outages retry indefinitely with exponential backoff capped at 60 seconds.
- Authentication recovery tries token refresh before full TOTP login and stops safely after three failed attempts.
- Configured market-data subscriptions restore before Phase 25 reconciliation and strategy processing resume.
- Broker writes are never retried automatically. An uncertain write reconciles state, activates the kill switch, and stops safely.
- Fully simulated Paper, Backtest, and Replay do not use broker reconnect behavior.

## Production Configuration and Secrets

- AngelOne secrets stay in the configured `angelone_keys.env` file beside `autotick/config/default.yaml` when using the default relative path.
- Required keys are `API_KEY`, `CLIENT_ID`, `PASSWORD`, and `TOTP_SECRET`.
- Missing files, directories, unreadable files, duplicate keys, missing keys, and blank required values fail before broker login.
- Secret errors name keys only; secret values and file contents are not logged.
- Paper validates AngelOne secrets only when it uses AngelOne market data or broker auto-fetch.
- Fully simulated Paper, Backtest, and Replay do not require AngelOne secrets.
- Live mode requires `persistence.enabled`, `reconnect.enabled`, `session.only_market_hours`, and `logging.enabled` to all be true.
- `angelone_keys.env` is explicitly ignored by Git and must never be committed.

## Reports

A completed report trade is one filled ENTRY + one filled EXIT pair.

- Trade CSV files append only new completed trades; duplicate exit trade IDs are skipped.
- Summary CSV files are recalculated from the full accumulated trade CSV whenever a new trade is appended.
- Per-report OS file locks protect concurrent strategy processes on Windows and Linux.
- Summary replacement is atomic; corrupt report files are logged without stopping trading or blocking the other report scope.
- Strategy files use `broker_userid_strategy_mode_trades.csv` and `broker_userid_strategy_mode_summary.csv`.
- Combined files use `broker_userid_mode_trades.csv` and `broker_userid_mode_summary.csv` and contain all strategies sharing that broker, user ID, and mode.
- `reports.user_id` may contain any user label. When blank, AngelOne uses its broker client ID when available; otherwise `user` is used.
- Metrics: completed trades, wins, losses, win rate, gross profit, gross loss, net P&L, average P&L, best trade, and worst trade.
- Trade rows include strategy, broker, user ID, mode, symbol, exchange, quantity, entry/exit price, P&L, and entry/exit time.
- No timestamp is added to report filenames.

## Logging

Console colors:

- ERROR: red
- WARNING: yellow
- INFO: white
- DONE: green

Use logger.done() for successful completions such as login, logout, token refresh, configuration load, order placement, and shutdown. Rotating file logs remain plain text without color codes.

## Configuration

The only default YAML is config/default.yaml. Relative credential, CSV, persistence, and report paths resolve from the YAML file's directory.

Important flags:

- mode: live, paper, backtest, or replay
- broker: selected broker adapter
- market.exchange: the single exchange used by this run
- simulated.ui_data_enabled: enable Paper control panel
- simulated.broker_auto_fetch: load UI starting data from a real broker
- session.schedule_type: DAILY, WEEKLY, or ALWAYS_OPEN
- session.timezone: calendar timezone in IANA format
- session.only_market_hours: enforce or ignore the realtime schedule gate
- trade.position_type: INTRADAY or POSITIONAL
- persistence.enabled: enable SQLite persistence and startup recovery
- persistence.state_path: SQLite `.db` file shared by isolated runtime profiles
- reconnect.enabled: enable recovery for Live and broker-backed Paper
- reconnect.initial_delay_s and reconnect.max_delay_s: exponential backoff range
- reconnect.auth_max_attempts: bounded authentication recovery attempts
- reports.enabled: enable completed-trade CSV export and summaries
- reports.user_id: optional filename identity; blank uses broker client ID when available
- reports.output_dir: directory for strategy and combined CSV files

Schedule-specific fields:

- DAILY: trading_days, closed_dates, market_start, market_end, square_off_time
- WEEKLY: closed_dates, week_start_day, week_start_time, week_end_day, week_end_time, and optional paired daily_break_start/daily_break_end
- ALWAYS_OPEN: no day or time fields; weekends remain open

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
