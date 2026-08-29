# AutoTick - Plan

## Project Goal

Build one modular trading framework for Live, Paper, Backtest, and Replay modes.

## Milestones

- [x] Milestone 1 - Foundation: structure, configuration, models, interfaces, and logging.
- [x] Milestone 2 - Mode-Neutral Core: providers, sessions, events, and TradingEngine.
- [x] Milestone 3 - Strategy Framework: indicators, strategy contract, context, simple strategy, and signal validation.
- [x] Milestone 4 - Provider Layer: historical, simulated, and AngelOne adapters.
- [x] Milestone 5 - Execution and Risk: order states, positions, P&L, sizing, limits, and square-off methods.
- [x] Milestone 6 - Trading Modes: Paper, Backtest, Replay, and Live provider wiring.
- [ ] Milestone 7 - Recovery and Persistence: persistence, recovery, reconciliation, reconnect, and production configuration.
- [ ] Milestone 8 - Reports: performance metrics and trade export.
- [ ] Milestone 9 - Testing: unit, provider-contract, integration, parity, recovery, and end-to-end tests.
- [ ] Milestone 10 - Production: documentation, audit trail, soak testing, and controlled Live rollout.

## Completed Phases

- [x] Phase 1 - Project skeleton, packaging, entry point, and logging.
- [x] Phase 2 - YAML configuration loading and validation.
- [x] Phase 3 - Common models.
- [x] Phase 4 - Provider interfaces.
- [x] Phase 5 - ProviderFactory and mode mapping.
- [x] Phase 6 - SessionPool and broker-session lifecycle.
- [x] Phase 7 - CalendarSessionManager.
- [x] Phase 8 - EventDispatcher.
- [x] Phase 9 - TradingEngine lifecycle and event loop.
- [x] Phase 10 - Indicator base and SMA.
- [x] Phase 11 - Strategy base, context, callbacks, and simple long strategy.
- [x] Phase 12 - Engine-owned SignalValidator.
- [x] Phase 13 - Shared HistoricalProvider.
- [x] Phase 14 - Simulated providers and shared in-memory state.
- [x] Phase 15 - AngelOne session and account adapters.
- [x] Phase 16 - AngelOne market-data and execution adapters.
- [x] Phase 17 - TradeManager and order state machine.
- [x] Phase 18 - Position lifecycle, exposure, trades, and P&L.
- [x] Phase 19 - Risk validation, quantity sizing, stop-loss, and target helpers.
- [x] Phase 20 - Daily trade limit, kill switch, and intraday square-off method.
- [x] Phase 21 - Paper mode.
- [x] Phase 22 - Backtest mode.
- [x] Phase 23 - Replay mode.
- [x] Phase 24 - Live mode.

## Post-Phase Cleanup Completed

- Aligned AngelOne and simulated interfaces, constructors, arguments, exchanges, and normalized return models.
- Added shared SimulatedSession and SimulatedState.
- Added optional get_bars() dates with 5-day intraday and 30-day daily defaults.
- Removed duplicate YAML.
- Added root provider_test.py.
- Added Windows simulated_control_panel.py.
- Connected UI balance, funds, ticks, LTP, volume, price changes, CSV, and bars to the running Paper strategy.
- Added UI-only and broker-auto-fetch behavior.
- Added colored console logging and logger.done().
- Added market-closed warning and realtime-loop exit when only_market_hours is true.
- Removed tests until the planned Testing milestone.

## Current Runtime Wiring

- Paper with UI disabled: broker market data plus simulated account and execution.
- Paper with UI enabled: shared UI simulated data plus simulated account and execution.
- Backtest and Replay: HistoricalProvider plus simulated account and execution.
- Live: broker market data, account, and execution.
- Simple strategy buys when LTP exceeds previous close by 0.5%.
- RiskManager caps configured quantity.
- One filled ENTRY increments the daily trade count.
- POSITIONAL is the default position type.

Not yet wired in the CLI runner:

- Target, stop-loss, trailing-stop monitoring and exit orders.
- Daily P&L feed into max-loss enforcement.
- Automatic square-off call.
- Persistence, recovery, startup reconciliation, and reconnect.
- Reports and exports.
- Automated tests.

## Current Work

- Completed milestone: Milestone 6 - Trading Modes
- Completed phases: 1 through 24
- Current milestone: Milestone 7 - Recovery and Persistence
- Next phase: Phase 25 - persistence, recovery, and reconciliation
- Phase 25 status: not started
- Test implementation starts at Phase 29

## Development Rules

- Implement and commit one approved phase at a time.
- Keep the code short and simple.
- Update README.md, PLAN.md, and ARCHITECTURE_IMPLEMENTATION_GUIDE.txt together.
- Keep strategies focused on market conditions and signal generation.
- Keep broker SDK calls inside broker adapters.
- Keep normalized models and interfaces broker-independent.
- Do not add optional components before their planned phase.
