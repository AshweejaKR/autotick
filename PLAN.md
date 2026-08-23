# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [x] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [ ] Strategy Framework: indicators, Strategy contract, simple strategy, and signal validation.
- [ ] Provider Layer: historical, simulated, and broker adapters.
- [ ] Execution and Risk: orders, positions, P&L, limits, and kill switch.
- [ ] Trading Modes: Paper, Backtest, Replay, and Live.
- [ ] Recovery and Persistence: persistence, recovery, reconciliation, and reconnect.
- [ ] Reports: performance metrics and trade export.
- [ ] Testing: unit, integration, parity, recovery, and end-to-end tests.
- [ ] Production: documentation, audit trail, soak test, and controlled rollout.

## Detailed Plan
Detailed phase definitions and architecture rules: ARCHITECTURE_IMPLEMENTATION_GUIDE.txt

## Current Status

- Current milestone: Strategy Framework
- Completed phase: Phase 10 - Indicator base and simple moving average (default period 20)
- Phase 11: Strategy base, context, lifecycle callbacks, and simple long strategy committed for review
- Current phase: Phase 12 - Signal validation
- Signal validation: validates symbol, exchange, signal type, and positive quantity/price when provided
- quantity=None is valid; RiskManager/TradeManager decides sizing from configuration
- Risk, target, stop loss, duplicate-entry, and re-entry checks stay outside signal validation
- Status: Phases 1-10 completed; Phases 11-12 implementation committed for review

## Development Rule

Implement and commit one approved phase at a time.
