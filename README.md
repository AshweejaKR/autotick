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
- Phase 14: Simulated account and execution providers — completed.
- Simulated providers keep simple in-memory account/order state.
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
- Positions have `INTRADAY` or `POSITIONAL` type; default is `POSITIONAL`.
- Automatic square-off exits only `INTRADAY` positions. Positional/swing positions remain open overnight.

## Running

Use the packaged default configuration:

`autotick`

Or pass an explicit configuration path:

`autotick --config path/to/config.yaml`

The repository-level `config/config.yaml` remains available for project-local configuration.

## Status

- Version: 0.1.0
- Completed milestones: Foundation, Mode-Neutral Core, Strategy Framework, Provider Layer, Execution and Risk
- Completed: Phases 1-20
- Current milestone: Trading Modes
- Current: Phase 21 - Paper mode

## Plan

See [PLAN.md](PLAN.md) for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture rules.