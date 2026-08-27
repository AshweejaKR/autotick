# AutoTick — Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Foundation: project structure, configuration, models, and interfaces.
- [x] Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [x] Strategy Framework: indicators, Strategy contract, simple strategy, and signal validation.
- [x] Provider Layer: historical, simulated, and broker adapters.
- [x] Execution and Risk: orders, positions, P&L, limits, and kill switch.
- [x] Trading Modes: Paper, Backtest, Replay, and Live.
- [ ] Recovery and Persistence: persistence, recovery, reconciliation, and reconnect.
- [ ] Reports: performance metrics and trade export.
- [ ] Testing: unit, integration, parity, recovery, and end-to-end tests.
- [ ] Production: documentation, audit trail, soak test, and controlled rollout.

## Detailed Plan
Detailed phase definitions and architecture rules: ARCHITECTURE_IMPLEMENTATION_GUIDE.txt

## Current Status

- Completed milestone: Trading Modes
- Completed phases: Phase 1 through Phase 24
- Phase 10: Indicator base and simple moving average (default period 20)
- Phase 11: Strategy base, StrategyContext, lifecycle callbacks, and simple long strategy
- Phase 12: Engine-layer SignalValidator for structural signal validation
- Phase 13: Shared HistoricalProvider for Backtest and Replay historical market data
- Phase 14: Simulated session, market-data, account, and execution providers with in-memory state
- Simulated market data remains standalone; mode mapping keeps Paper on AngelOne and Backtest/Replay on HistoricalProvider
- AngelOne and simulated account providers return the same normalized Account model
- Phase 15: AngelOne SmartAPI shared session and account adapter
- Phase 16: AngelOne SmartAPI market-data and execution adapters
- Phase 17: TradeManager and validated, timestamped order state machine
- Phase 18: TradeManager position lifecycle, broker reconciliation, exposure, trades, and realized/unrealized P&L
- Phase 19: RiskManager validation, risk-based quantity cap, stop loss, and configurable target
- Phase 20: Daily loss limit, filled-entry trade limit, kill switch, and intraday-only square-off
- Phase 21: Paper mode uses AngelOne live market data with simulated account/execution and real-time session timing
- Paper MARKET orders fill immediately using current broker LTP without sending broker orders
- Phase 22: Backtest mode uses HistoricalProvider with simulated account/execution and fast session timing
- Backtest can optionally load normalized OHLCV bars from configured CSV; otherwise HistoricalProvider accepts in-memory bars
- Backtest does not require broker login or broker credentials
- Phase 23: Replay mode reuses HistoricalProvider and simulated account/execution with replay-speed session timing
- Replay uses the same optional historical CSV source as Backtest and does not require broker login
- Backtest and Replay detect trading-date changes through TradingEngine.advance_time()
- New trading day closes prior strategy session, resets RiskManager daily state, then reruns on_market_open() and on_initial_setup()
- Phase 24: Live mode uses one shared AngelOne session for market data, account, and execution with real-time session timing
- Orders carry position_type; AngelOne maps INTRADAY to INTRADAY and POSITIONAL to DELIVERY/CARRYFORWARD
- Strategy rule: BUY when LTP > previous-day close + 0.5%; otherwise no action
- Previous-day close: fetched through MarketDataProvider during on_initial_setup()
- quantity=None is valid at signal level; RiskManager/TradeManager decides sizing from configuration
- Orders use explicit ENTRY/EXIT intent; only FILLED ENTRY orders increment the daily trade count
- Reaching `risk.max_trades_per_day` activates the kill switch; default is 5
- Position type defaults to POSITIONAL; only INTRADAY positions are auto squared off
- Target and stop loss are risk configuration; duplicate-entry and re-entry remain outside Strategy/SignalValidator
- Position/trade verification and reconciliation stay in TradeManager, not providers
- Current milestone: Recovery and Persistence
- Current phase: Phase 25 - Persistence, recovery, and reconciliation
- Status: Milestones 1-6 and Phases 1-24 completed

## Development Rule

Implement and commit one approved phase at a time.
