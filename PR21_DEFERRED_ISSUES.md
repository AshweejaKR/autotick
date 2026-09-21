# PR #21 Deferred Issues

Status: Deferred for later fix.

## P1 — Partial Fill Handling

- `TradeManager.reconcile_orders()` can skip cumulative fill growth when broker status stays `PARTIAL`.
- AngelOne `averageprice` is cumulative; current incremental fill handling can calculate wrong position average/P&L for split fills.
- Completed-trade reporting can be incomplete after PARTIAL -> CANCELLED -> later EXIT.

Required later:
- Handle PARTIAL -> PARTIAL when `filled_quantity` increases.
- Apply cumulative average/fill quantity correctly.
- Add tests for PARTIAL -> PARTIAL and PARTIAL -> CANCELLED -> EXIT.

## P1 — Live Risk / Default Safety

- `RiskManager.position_size(..., margin_aware=True)` returns configured fixed quantity directly, so `risk_per_trade_pct` is not used as an additional cap.
- Packaged `autotick/config/default.yaml` currently uses `mode: live`; running AutoTick with no custom config can enter the real-broker flow.

Required later:
- Keep broker-margin sizing while also enforcing the configured risk-per-trade limit.
- Make Live usage explicit; avoid a packaged default that can unintentionally select real-order mode.

## Current Decision

- Do not block current PR work for these items.
- Keep both issues documented and fix in a separate follow-up change before broader production rollout.
- Phase 33 Paper soak remains pending.
