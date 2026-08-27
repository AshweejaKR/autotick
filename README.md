# AutoTick

AutoTick is a clean rebuild of a modular, broker-independent algorithmic trading framework.

## Goals

- Support Live, Paper, Backtest, and Replay modes.
- Use the same Strategy across every mode.
- Keep broker SDK code inside broker adapters.
- Keep TradingEngine mode-neutral.

## Foundation

Foundation is complete through Phase 4:

- Phase 1: Project skeleton, packaging, entry point, and logging.
- Phase 2: YAML configuration loading and validation.
- Phase 3: Common market, signal, order, position, trade, account, and event models.
- Phase 4: MarketData, Account, and Execution interfaces.

## Mode-Neutral Core

- Phase 5: ProviderFactory, ProviderBundle, and mode mapping — completed.
- Phase 6: SessionPool and broker-session lifecycle — completed.
- Phase 7: Mode-aware CalendarSessionManager — completed.
- Phase 8: EventDispatcher and normalized events — completed.
- Phase 9: TradingEngine lifecycle and event loop — completed.

## Strategy Framework

- Phase 10: Indicator base and simple moving average (SMA) — completed.
- SMA default period: 20.
- Additional indicators are deferred until a strategy needs them.
- Phase 11: Strategy base, StrategyContext, lifecycle callbacks, and simple long strategy — completed.
- Simple strategy rule: BUY when LTP is more than 0.5% above previous-day close; otherwise no action.
- Previous-day close is loaded through MarketDataProvider during initial setup.
- Phase 12: Signal validation — completed.
- SignalValidator lives in the engine layer; Strategy only generates signals.
- Signal validation checks symbol, exchange, signal type, and positive quantity/price when supplied.
- quantity=None is valid; RiskManager/TradeManager decides quantity from configuration.
- Target, stop loss, duplicate-entry, re-entry, and other risk rules stay outside Strategy/SignalValidator.

## Provider Layer

- Phase 13: Shared HistoricalProvider — completed.
- Backtest and Replay share the same normalized historical market-data provider.
- Historical bars remain `list[MarketBar]`; pandas is kept outside the provider contract.
- Phase 14: Simulated provider adapters — completed.
- Simulated session, market-data, account, and execution adapters implement the same normalized contracts as AngelOne.
- AngelOne and simulated adapters use matching constructor arguments.
- Simulated market data accepts `exchange`; ticks and bars are loaded with `set_tick()` and `set_bars()`.
- The setter methods are simulation-only data-input helpers, not shared provider methods.
- Simulated market data is a standalone in-memory adapter; Paper still uses AngelOne data and Backtest/Replay still use HistoricalProvider.
- Account providers return the same normalized `Account` model.
- Simulated providers keep simple in-memory market/account/order state.
- Position/trade verification and reconciliation remain TradeManager responsibilities.
- Phase 15: AngelOne SmartAPI session and account adapters — completed.
- AngelOne session owns login, token refresh, logout, symbol resolution, and shared SmartConnect client.
- AngelOne account adapter exposes profile, balance, margin, and buying power through the normalized account interface.
- Phase 16: AngelOne SmartAPI market-data and execution adapters — completed.
- Market-data adapter provides normalized LTP/ticks and historical OHLCV candles.
- Execution adapter provides normalized orders, positions, holdings, trades, P&L, and order actions.

## Execution and Risk

- Phase 17: TradeManager and order state machine — completed.
- Orders follow NEW -> VALIDATED -> SUBMITTED -> OPEN/PARTIAL/FILLED or terminal rejected/cancelled/expired states.
- TradeManager validates transitions, timestamps state changes, tracks normalized orders, and reconciles execution-provider order state.
- Phase 18: TradeManager position lifecycle, exposure, and P&L — completed.
- Positions track pending/open/closed state, broker reconciliation, trades, realized/unrealized P&L, and total exposure.
- Phase 19: Risk validation, sizing, stop loss, and targets — completed.
- RiskManager caps configured quantity using capital, per-trade risk, price, and stop-loss distance.
- Stop loss and target are percentage-based; `target_pct` is user-configurable and defaults to 5.
- Market orders can use current LTP for risk sizing without forcing a limit price.
- Phase 20: Daily limits, square-off, and kill switch — completed.
- Daily P&L at or below configured `max_loss` activates the kill switch and blocks new trades until reset.
- Orders carry explicit `ENTRY` or `EXIT` intent. Only a FILLED `ENTRY` increments the daily trade count.
- Reaching `max_trades_per_day` activates the kill switch; EXIT, rejected, and cancelled orders do not consume the limit.
- Positions have `INTRADAY` or `POSITIONAL` type; default is `POSITIONAL`.
- Automatic square-off exits only `INTRADAY` positions. Positional/swing positions remain open overnight.

## Trading Modes

- Phase 21: Paper mode — completed.
- Paper mode uses AngelOne live market data with simulated account and execution providers.
- Paper MARKET orders fill immediately at the current AngelOne LTP; no broker order is sent.
- Paper mode uses real-time CalendarSessionManager timing.
- Phase 22: Backtest mode — completed.
- Backtest mode uses HistoricalProvider with simulated account/execution and fast CalendarSessionManager timing.
- Optional CSV source: enable `backtest.csv.enabled` and set `backtest.csv.data_file`.
- CSV columns: `symbol,exchange,interval,timestamp,open,high,low,close,volume`.
- When CSV is disabled, HistoricalProvider remains available for in-memory `MarketBar` data.
- Backtest mode does not log in to a broker.
- Phase 23: Replay mode — completed.
- Replay mode reuses the Backtest HistoricalProvider and simulated account/execution providers.
- Replay reads the same optional `backtest.csv` source and uses `session.replay_speed` for timed historical playback.
- Replay mode does not log in to a broker and does not add a separate ReplayProvider.
- TradingEngine detects historical date changes through `advance_time()`.
- Each new day closes the prior strategy session, resets daily risk state, then runs `on_market_open()` and `on_initial_setup()` again for daily strategy calculations.
- Phase 24: Live mode — completed.
- Live mode uses one shared AngelOne session for live market data, broker account, and broker execution.
- Live mode uses real-time CalendarSessionManager timing.
- Orders carry `position_type`; AngelOne maps `INTRADAY` to broker intraday and `POSITIONAL` to delivery/carry-forward products.

## Running

Use the repository default configuration:

`autotick`

Or pass an explicit configuration path:

`autotick --config path/to/config.yaml`

`config/default.yaml` is the only default YAML file. `autotick/config/` contains configuration code only.

## Status

- Version: 0.1.0
- Completed milestones: Foundation, Mode-Neutral Core, Strategy Framework, Provider Layer, Execution and Risk, Trading Modes
- Completed: Phases 1-24
- Current milestone: Recovery and Persistence
- Current: Phase 25 - Persistence, recovery, and reconciliation

## Plan

See [PLAN.md](PLAN.md) for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture rules.
