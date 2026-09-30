# AutoTick

Broker-independent trading framework for Live, Paper, Backtest, and Replay.

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Latest hardening: AngelOne response recovery, safer margin handling, concise logging, IST audits, and derivative expiry exits
- Default: Live NSE positional delivery swing strategy with a CSV trigger watchlist
- Current: Milestone 10 — Production
- Next: Phase 33 — five-market-day Paper soak

## Modes

| Mode | Market data | Account and execution |
| --- | --- | --- |
| Live | Selected broker | Selected broker |
| Paper | Selected broker | Simulated |
| Backtest | Historical | Simulated |
| Replay | Historical | Simulated |

Paper uses broker market data with simulated account/execution, supports LONG and SHORT simulation, and never sends Paper orders to the broker. Live and Paper recover SQLite state before strategy setup; Backtest and Replay start fresh.

## Run

Install:

    python -m pip install -e ".[test]"

Default configuration:

    python -m autotick.main

Another configuration:

    python -m autotick.main --config path/to/config.yaml

Tests:

    python -m pytest -q

GitHub Actions also runs pytest on every push and pull request.

Manual provider check:

    python provider_test.py

## Important Rules

- `autotick/config/default.yaml` is Live NSE delivery swing. Add exact NSE cash symbols and positive buy trigger prices to `autotick/config/swing_watchlist.csv` before trading; the shipped watchlist has only its header, so no new entries are placed.
- Set `trade.expiry_exit.contracts` to exact uppercase symbol → quoted `YYYY-MM-DD` expiry dates. Broker expiry takes priority; configured dates cover broker metadata outages. Backtest/Replay require dates for configured positional futures/options when expiry exits are enabled. If both sources are missing in Live/Paper, entries are blocked and an open position raises a critical alert.
- Keep AngelOne secrets in the ignored `angelone_keys.env` file. Never commit it.
- Live requires persistence, reconnect, market-hours gating, and logging.
- Live AngelOne entries use broker margin before placement; MCX skips the unreliable charge-estimate endpoint.
- AngelOne usable funds come from `availablecash`; cash-equity positional short entries are rejected.
- Broker read failures recover with backoff; broker writes are never automatically retried.
- Live/Paper startup waits only during the final configured pre-market window (30 minutes by default).
- Paper uses `simulated.margin_pct` for simple futures margin; the default NSE delivery setting is 100% of trade value.
- Default file logging is `INFO` with timestamped filenames; active strategy ranges remain console-only and throttled.
- Audit timestamps use IST and forced derivative exits add an `EXPIRY_EXIT` record.
- Use one configured calendar profile for all symbols in a run.
- Normal CLI SIGNAL validation routes through `TradingEngine` + `EventDispatcher`; recovery/reconnect remains in the main runtime loop.
- The old simulated desktop control panel and its config flags are removed.

## Swing watchlist imports

Place CSV files named `swing_watchlist_import_YYYYMMDD_HHMMSS.csv` in the same
folder as the configured `strategy_config.csv_file`. For example, use
`swing_watchlist_import_20260930_180000.csv`. Each file must have `symbol` and
`trigger_price` columns with positive finite prices, just like the main watchlist.

At Swing startup, `load_swing_watchlist()` processes all matching files from
oldest to newest. Missing symbols are appended; existing symbols and trigger
prices stay unchanged. The first occurrence of a new symbol wins across import
files and duplicate rows. Each valid file is deleted after its additions are
saved, including files containing only duplicates or a header.

Imports run once at startup. Daily reload and strategy setup only read the main
watchlist; files added during a run wait for the next restart. An invalid import
or failed save stops startup and keeps that source file. Earlier successful
imports remain saved. Saves use an atomic replacement; if source deletion fails,
restart safely ignores already-added symbols and retries deletion.

## Swing watchlist builder (Windows)

Install once from the repository folder:

    python -m pip install -e ".[watchlist]"

Double-click `swing_watchlist_tool.bat`, or run:

    python -m autotick.swing_watchlist_tool

1. Click **Login: choose keys file** and select your `angelone_keys.env`.
2. Enter an NSE symbol (prefer the exact cash symbol, such as `INFY-EQ`) and
   trigger price. Click **Add + Validate** for each row. The table shows the
   broker-resolved symbol, LTP, signed difference, and warning note. Difference
   is `(trigger - LTP) / LTP * 100`; absolute differences above 5% warn and
   above 10% show a stronger warning. Closed-market LTP may be the last price.
   Remove a row and add it again to change its trigger.
3. Click **Create CSV** and choose the folder containing your main watchlist.
   All rows are revalidated with fresh broker reads before saving. The filename
   timestamp uses IST, and the CSV contains only `symbol,trigger_price`.
4. Click **Review saved CSV** to open it in your Windows default CSV app. Review
   the saved file and the warning notes in the window.
5. Optionally click **Upload to EC2** and confirm manual review. Provide
   `ec2-user@hostname`, your SSH private key file, and the absolute EC2 folder
   containing `swing_watchlist.csv` (not merely the repository root).

Upload requires Windows OpenSSH Client (`ssh` and `scp`) and a reachable server.
Only the generated CSV is transferred; the credentials file stays local. The
remote folder must already exist. Transfer uses a temporary name followed by a
rename so startup cannot import a partially transferred CSV. Existing SSH host
key changes are rejected; first-time hosts are recorded. The local CSV stays
available after upload. If the saved CSV was edited outside the window, update
the rows and create a new validated CSV before uploading. EC2 consumes the
import at its next Swing startup, preserving existing main-watchlist triggers.

## Documentation

- [Plan](PLAN.md) — milestone status.
- [Architecture guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) — behavior, configuration, recovery, reports, and design rules.
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md) — five-day Paper safety check.
