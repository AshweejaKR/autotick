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

## Running

Use the packaged default configuration:

`autotick`

Or pass an explicit configuration path:

`autotick --config path/to/config.yaml`

The repository-level `config/config.yaml` remains available for project-local configuration.

## Status

- Version: 0.1.0
- Completed milestones: Foundation, Mode-Neutral Core, Strategy Framework
- Completed: Phases 1-14
- Current milestone: Provider Layer
- Current: Phase 15 - First broker session and account adapters

## Plan

See [PLAN.md](PLAN.md) for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture rules.
