# AutoTick Paper Soak and Controlled Live Rollout

## Scope

Run Paper mode for five complete market days before any new Live verification.
Paper uses simulated execution. It must never place a broker order.

## Before Each Day

1. Confirm `mode: paper`; do not use a Live config.
2. Keep persistence, reconnect, reports, logging, and `only_market_hours` enabled.
3. Keep `reports.enabled: true` so trade, summary, and audit CSVs are saved.
4. Keep the prior SQLite state. Do not delete it between soak days.

## Daily Pass Check

1. Start AutoTick during market hours and let it run for the session.
2. If a managed position is open, restart once and confirm recovery prevents a duplicate entry.
3. Check logs for an unrecovered error, uncertain write, or forced safe shutdown.
4. Check report and audit CSVs for consistent order, recovery, and completed-trade records.
5. Confirm no broker order was placed.

| Day | Date | Startup/recovery | Reports/audit | No broker order | Result |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

## Gate After Day Five

Proceed only when all five rows pass. Stop and investigate any failed row before
continuing. Keep the logs, SQLite state, reports, and audit CSVs as evidence.

## Controlled Live Verification

After the Paper gate passes, use the existing [Live verification guide](LIVE_VERIFICATION.md):

1. Use its one-lot, one-entry, separate-state configuration.
2. Submit no order until the contract, margin, trigger, stop-loss, and target are checked manually.
3. Run one controlled entry only; restart once while the position is open when practical.
4. Confirm recovery, protective exit, report row, and audit rows.
5. Stop on any uncertain write, unresolved order, or recovery failure. Do not retry a broker write automatically.

This runbook does not authorize or place Live orders. Operator approval is required
for each Live verification.
