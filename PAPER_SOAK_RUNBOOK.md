# AutoTick Paper Soak

## Scope

Run Paper mode for five complete market days. Paper uses simulated execution and
must never place a broker order.

## Before Each Day

1. Confirm mode: paper; do not use a Live config.
2. Keep persistence, reconnect, reports, logging, and only_market_hours enabled.
3. Keep reports.enabled: true so trade, summary, and audit CSVs are saved.
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

## Completion Gate

All five rows must pass. Stop and investigate any failure. Keep the logs,
SQLite state, reports, and audit CSVs as evidence.
