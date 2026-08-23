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
- Phase 6: SessionPool and broker-session lifecycle — current.

## Running

Use the default repository configuration:

`autotick`

Or pass an explicit configuration path:

`autotick --config path/to/config.yaml`

## Status

- Version: 0.1.0
- Completed milestone: Foundation
- Completed: Phases 1-5
- Current milestone: Mode-Neutral Core
- Current: Phase 6 - SessionPool and broker-session lifecycle

## Plan

See [PLAN.md](PLAN.md) for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) for detailed architecture rules.
