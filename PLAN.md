# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [x] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [x] Strategy Framework: indicators, Strategy contract, simple strategy, and signal validation.
- [x] Provider Layer: historical, simulated, and broker adapters.
- [x] Execution and Risk: orders, positions, P&L, limits, and kill switch.
- [ ] Trading Modes: Paper, Backtest, Replay, and Live.
- [ ] Recovery and Persistence: persistence, recovery, reconciliation, and reconnect.
- [ ] Reports: performance metrics and trade export.
- [ ] Testing: unit, integration, parity, recovery, and end-to-end tests.
- [ ] Production: documentation, audit trail, soak test, and controlled rollout.

## Detailed Plan
Detailed phase definitions and architecture rules: ARCHITECTURE_IMPLEMENTATION_GUIDE.txt

## Current Status

- Completed milestone: Execution and Risk
- Completed phases: Phase 1 through Phase 21
- Phase 10: Indicator base and simple moving average (default period 20)
- Phase 11: Strategy base, StrategyContext, lifecycle callbacks, and simple long strategy
- Phase 12: Engine-layer SignalValidator for structural signal validation
- Phase 13: Shared HistoricalProvider for Backtest and Replay historical market data
- Phase 14: Simulated account and execution providers with in-memory state
- Phase 15: AngelOne SmartAPI shared session and account adapter
- Phase 16: AngelOne SmartAPI market-data and execution adapters
- Phase 17: TradeManager and validated, timestamped order state machine
- Phase 18: TradeManager position lifecycle, broker reconciliation, exposure, trades, and realized/unrealized P&L
- Phase 19: RiskManager validation, risk-based quantity cap, stop loss, and configurable target
- Phase 20: Daily loss limit, filled-entry trade limit, kill switch, and intraday-only square-off
- Phase 21: Paper mode uses AngelOne live market data with simulated account/execution and real-time session timing
- Paper MARKET orders fill immediately using current broker LTP without sending broker orders
- Strategy rule: BUY when LTP > previous-day close + 0.5%; otherwise no action
- Previous-day close: fetched through MarketDataProvider during on_initial_setup()
- quantity=None is valid at signal level; RiskManager/TradeManager decides sizing from configuration
- Orders use explicit ENTRY/EXIT intent; only FILLED ENTRY orders increment the daily trade count
- Reaching `risk.max_trades_per_day` activates the kill switch; default is 5
- Position type defaults to POSITIONAL; only INTRADAY positions are auto squared off
- Target and stop loss are risk configuration; duplicate-entry and re-entry remain outside Strategy/SignalValidator
- Position/trade verification and reconciliation stay in TradeManager, not providers
- Current milestone: Trading Modes
- Current phase: Phase 22 - Backtest mode
- Status: Milestones 1-5 and Phases 1-21 completed

## Development Rule

Implement and commit one approved phase at a time.
