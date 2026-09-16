# AutoTick

Broker-independent trading framework for Live, Paper, Backtest, and Replay.

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Latest cleanup: removed obsolete `simulated_control_panel.py` and UI simulation flags
- Current: Milestone 10 — Production
- Next: Phase 33 — five-market-day Paper soak

## Modes

| Mode | Market data | Account and execution |
| --- | --- | --- |
| Live | Selected broker | Selected broker |
| Paper | Selected broker | Simulated |
| Backtest | Historical | Simulated |
| Replay | Historical | Simulated |

Paper uses broker market data with simulated account/execution, so Paper orders never reach the broker. Live and Paper recover SQLite state before strategy setup; Backtest and Replay start fresh.

## Run

Install:

    python -m pip install -e ".[test]"

Default configuration:

    python -m autotick.main

Another configuration:

    python -m autotick.main --config path/to/config.yaml

Tests:

    python -m pytest -q

Manual provider check:

    python provider_test.py

## Important Rules

- `autotick/config/default.yaml` is the packaged default YAML; relative paths resolve from its directory.
- Keep AngelOne secrets in the ignored `angelone_keys.env` file. Never commit it.
- Live requires persistence, reconnect, market-hours gating, and logging.
- Use one configured calendar profile for all symbols in a run.
- The old simulated desktop control panel and its config flags are removed.

## Documentation

- [Plan](PLAN.md) — milestone status.
- [Architecture guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) — behavior, configuration, recovery, reports, and design rules.
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md) — five-day Paper safety check.
