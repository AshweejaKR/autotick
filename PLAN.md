# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [ ] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
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

- Current milestone: Mode-Neutral Core
- Completed phase: Phase 6 - SessionPool and broker-session lifecycle
- Current phase: Phase 7 - Mode-aware CalendarSessionManager
- Status: Phases 1-6 completed; Foundation milestone completed; Mode-Neutral Core in progress

## Development Rule

Implement and commit one approved phase at a time.
