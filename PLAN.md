# AutoTick Plan

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Latest cleanup: removed obsolete simulated desktop control panel and UI-only config flags
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
- Live and Paper recover state before strategy setup.
- Strategies create signals only. RiskManager and TradeManager own sizing and execution.
- `autotick/config/default.yaml` is the packaged default configuration.
- Simulated desktop UI/control-panel support is removed.
- README, this plan, and the architecture guide must show the same status.

## References

- [Architecture and implementation guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt)
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md)
