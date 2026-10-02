# AutoTick Paper Soak

## Status

- Phase 33: pending
- Target: five complete Paper market days
- Paper mode: selected-broker market data + simulated account/execution
- Simulated execution: LONG and SHORT supported
- Simulated desktop control panel: removed
- GitHub pytest CI: enabled

## Scope

Run Paper mode for five complete market days. Paper uses real broker market data with simulated execution and must never place a broker order.

## Before Each Day

1. Confirm `mode: paper`; packaged default.yaml is Live NSE delivery swing.
2. Confirm latest GitHub pytest CI is passing.
3. Keep persistence, reconnect, reports, logging, and `only_market_hours` enabled.
4. Keep `reports.enabled: true` so trade, summary, and audit CSVs are saved.
5. Keep the prior SQLite state. Do not delete it between soak days.
6. Use normal AutoTick Paper mode; no simulated control-panel settings are required.
7. Confirm `simulated.margin_pct` suits the instrument; packaged default uses 100% for NSE delivery.
8. Start up to 30 minutes before market open; otherwise start during market hours.
9. For positional futures/options, configure the exact symbol and quoted expiry date under `trade.expiry_exit.contracts`.
10. Keep `session.closed_dates` updated for exchange holidays used by the expiry cutoff.
11. For Swing, place pending `swing_watchlist_import_YYYYMMDD_HHMMSS.csv` files beside the configured watchlist before startup. Confirm missing symbols are appended, existing trigger prices stay unchanged, and successfully processed files are deleted. Files added during a run wait for restart; fix retained invalid files before restarting.
12. Optionally create Swing imports using `python -m autotick.swing_watchlist_tool` on Windows. Review broker LTP differences and the saved CSV before confirming EC2 upload to the watchlist folder.

## Daily Pass Check

1. Start AutoTick during market hours and let it run for the session.
2. If a managed position is open, restart once and confirm recovery prevents a duplicate entry.
3. Check logs for unrecovered errors, uncertain writes, or forced safe shutdown.
4. Check report and audit CSVs for consistent order, recovery, and completed-trade records.
5. Confirm simulated LONG/SHORT behavior is correct for any generated signals.
6. Confirm no broker order was placed.
7. If an expiry cutoff occurs, confirm the simulated MARKET exit and `EXPIRY_EXIT` audit row.
8. For Swing, confirm shutdown at configured DAILY `session.market_end`, saved state, and open positional holdings preserved. Restart for each next market day.

| Day | Date | Startup/recovery | Reports/audit | No broker order | Result |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

## Completion Gate

All five rows must pass. Stop and investigate any failure. Keep logs, SQLite state, reports, and audit CSVs as evidence.
