# AutoTick Plan

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Latest cleanup: removed obsolete simulated desktop control panel and UI-only config flags
- Default: Live MCX GoldPetal previous-day range breakout, one configured unit
- Current: Milestone 10 — Production
- Next: Phase 33 — five-market-day Paper soak

## Milestones

| Milestone | Scope | Status |
| --- | --- | --- |
| 1 | Foundation | Complete |
| 2 | Mode-neutral core | Complete |
| 3 | Strategy framework | Complete |
| 4 | Provider layer | Complete |
| 5 | Execution and risk | Complete |
| 6 | Trading modes | Complete |
| 7 | Recovery and persistence | Complete |
| 8 | Reports | Complete |
| 9 | Testing | Complete |
| 10 | Production: documentation, audit, and soak | Phase 33 pending |

## Current Rules

- One run uses one market and one exchange.
- Paper uses selected-broker market data with simulated account/execution; Paper never sends broker orders.
- Simulated execution supports LONG and SHORT positions and square-off in both directions.
- Live and Paper recover state before strategy setup.
- Normal CLI SIGNAL validation routes through TradingEngine/EventDispatcher; recovery and reconnect stay in the main runtime loop.
- Strategies create signals only. RiskManager and TradeManager own sizing and execution.
- Live AngelOne entries use broker-calculated margin and charges before placement.
- GitHub Actions runs pytest on push and pull request.
- `autotick/config/default.yaml` is the packaged default configuration.
- Default strategy: LONG above prior-day high + 0.15%; SHORT below prior-day low - 0.15%.
- Simulated desktop UI/control-panel support is removed.
- README, this plan, architecture guide, and soak runbook must show the same status.

## Deferred Observation

- 2026-09-17: AngelOne startup recovery reported unknown broker orders/position and blocked GoldPetal, while the broker terminal showed GoldPetal and NIFTYBEES closed. Keep the current safety block; revisit broker-history filtering after more live observation.

## References

- [Architecture and implementation guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt)
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md)
