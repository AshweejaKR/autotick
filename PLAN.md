# AutoTick Plan

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Latest hardening: AngelOne recovery, margin safety, concise logging, IST audits, and derivative expiry exits
- Default: Live NSE positional delivery swing strategy with a CSV trigger watchlist
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
- Paper futures reserve configured `simulated.margin_pct`; the default NSE delivery setting is 100%.
- Simulated execution supports LONG and SHORT positions and square-off in both directions.
- Live and Paper recover state before strategy setup.
- Normal CLI SIGNAL validation routes through TradingEngine/EventDispatcher; recovery and reconnect stay in the main runtime loop.
- Strategies create signals only. RiskManager and TradeManager own sizing and execution.
- Live AngelOne entries use broker-calculated margin; MCX skips the unreliable charge-estimate endpoint.
- AngelOne uses `availablecash`; positional cash-equity short entries are rejected.
- Expiry exits use broker contract metadata first, then configured per-symbol dates; historical derivatives require configured dates when the policy is enabled.
- Positional derivatives close at the configured cutoff before expiry; late entries are blocked and exits are audited as `EXPIRY_EXIT`.
- Default logging is `INFO` with timestamped filenames; frequent strategy range messages are console-only and throttled.
- Live/Paper startup waits only during `session.startup_wait_minutes` before market open; otherwise it exits.
- GitHub Actions runs pytest on push and pull request.
- `autotick/config/default.yaml` is the packaged Live NSE delivery swing configuration. Its CSV watchlist ships empty, so no new entries are placed until symbols and trigger prices are supplied.
- Default strategy: BUY when NSE cash LTP rises above the CSV trigger price; `trade.position_type: POSITIONAL` maps to AngelOne DELIVERY. The MCX GoldPetal ORB strategy remains available through a custom YAML.
- Simulated desktop UI/control-panel support is removed.
- README, this plan, architecture guide, and soak runbook must show the same status.

## Deferred Production Fixes

- Broker rejection of an expiry exit can be valid, but `TradeManager` disallows `OPEN -> REJECTED`. A later order-book reconciliation raises `ValueError` outside broker recovery, stops the runner before its normal state save, and leaves position closure unconfirmed. Accept the terminal transition, restore the open position when the exit failed, and test the full rejection/reconciliation path. Do not assume the broker position closed; verify it separately. No automatic broker-write retry is requested now.
- Expiry processing skips a symbol when `get_tick()` returns no valid LTP. An open derivative can miss its configured cutoff without an exit attempt; handle the missing-price case safely and test it.
- Reconciliation skips increased cumulative fills when broker status remains `PARTIAL`; handle `PARTIAL -> PARTIAL`, cumulative average price, and completed reporting after cancellation.
- Broker-margin fixed quantity bypasses the `risk_per_trade_pct` sizing cap; enforce both limits before wider production use.
- Packaged default remains `mode: live`; the empty watchlist prevents entries until configured. Consider a safer non-live default before wider distribution.
- Add focused tests for repeated partial fills and partial-fill cancellation followed by exit.

## Deferred Observation

- 2026-09-17: AngelOne startup recovery reported unknown broker orders/position and blocked GoldPetal, while the broker terminal showed GoldPetal and NIFTYBEES closed. Keep the current safety block; revisit broker-history filtering after more live observation.

## References

- [Architecture and implementation guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt)
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md)
