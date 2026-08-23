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
- Phase 11: Strategy base, StrategyContext, and lifecycle callbacks — committed for review.

## Running

Use the packaged default configuration:

`autotick`

Or pass an explicit configuration path:

`autotick --config path/to/config.yaml`

The repository-level `config/config.yaml` remains available for project-local configuration.

## Status

- Version: 0.1.0
- Completed milestones: Foundation, Mode-Neutral Core
- Completed: Phases 1-10
- Current milestone: Strategy Framework
- Current: Phase 11 - Strategy base, context, and lifecycle callbacks

## Plan

See [PLAN.md](PLAN.md) for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture rules.
