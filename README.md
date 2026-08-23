# AutoTick

AutoTick is a clean rebuild of a modular, broker-independent algorithmic trading framework.

## Goals

- Support Live, Paper, Backtest, and Replay modes.
- Use the same Strategy across every mode.
- Keep broker SDK code inside broker adapters.
- Keep TradingEngine mode-neutral.

## Foundation

Phase 1 provides the installable Python package, application entry point, and shared logging bootstrap.

## Status

- Version: 0.1.0
- Milestone: Foundation
- Completed: Phase 1 - Project skeleton, packaging, entry point, and logging
- Next: Phase 2 - YAML configuration loading and validation

## Plan

See [PLAN.md] for the implementation roadmap and [ARCHITECTURE_IMPLEMENTATION_GUIDE.txt] for detailed architecture rules.
