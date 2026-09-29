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

## Documentation

- [Plan](PLAN.md) — milestone status.
- [Architecture guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) — behavior, configuration, recovery, reports, and design rules.
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md) — five-day Paper safety check.
