# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [x] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [ ] Strategy Framework: indicators, Strategy contract, and signal validation.
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
- Completed phase: Phase 9 - TradingEngine lifecycle and event loop
- Current phase: Phase 10 - Indicator base and simple moving average (default period 20)
- Status: Phases 1-9 completed; Phase 10 implementation committed for review

## Development Rule

Implement and commit one approved phase at a time.
