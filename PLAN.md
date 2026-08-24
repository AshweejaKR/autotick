# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [x] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [x] Strategy Framework: indicators, Strategy contract, simple strategy, and signal validation.
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

- Completed milestone: Strategy Framework
- Completed phases: Phase 1 through Phase 15
- Phase 10: Indicator base and simple moving average (default period 20)
- Phase 11: Strategy base, StrategyContext, lifecycle callbacks, and simple long strategy
- Phase 12: Engine-layer SignalValidator for structural signal validation
- Phase 13: Shared HistoricalProvider for Backtest and Replay historical market data
- Phase 14: Simulated account and execution providers with in-memory state
- Phase 15: AngelOne SmartAPI shared session and account adapter
- Strategy rule: BUY when LTP > previous-day close + 0.5%; otherwise no action
- Previous-day close: fetched through MarketDataProvider during on_initial_setup()
- quantity=None is valid; RiskManager/TradeManager decides sizing from configuration
- Target, stop loss, duplicate-entry, and re-entry rules stay outside Strategy/SignalValidator
- Position/trade verification and reconciliation stay in TradeManager, not providers
- Current milestone: Provider Layer
- Current phase: Phase 16 - First broker market-data and execution adapters
- Status: Milestones 1-3 and Phases 1-15 completed

## Development Rule

Implement and commit one approved phase at a time.
