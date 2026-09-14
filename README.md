# AutoTick

Broker-independent trading framework for Live, Paper, Backtest, and Replay.

## Status

- Version: 0.1.0
- Completed: Milestones 1–9, Phases 1–32
- Current: Milestone 10 — Production
- Next: Phase 33 — five-market-day Paper soak

## Modes

| Mode | Market data | Account and execution |
| --- | --- | --- |
| Live | Selected broker | Selected broker |
| Paper | Selected broker or UI simulation | Simulated |
| Backtest | Historical | Simulated |
| Replay | Historical | Simulated |

Paper orders never reach the broker. Live and Paper recover SQLite state before
strategy setup; Backtest and Replay start fresh.

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

Paper control panel:

    python simulated_control_panel.py

## Important Rules

- `config/default.yaml` is the only default YAML; relative paths resolve from its directory.
- Keep AngelOne secrets in the ignored `angelone_keys.env` file. Never commit it.
- Live requires persistence, reconnect, market-hours gating, and logging.
- Use one configured calendar profile for all symbols in a run.

## Documentation

- [Plan](PLAN.md) — milestone status.
- [Architecture guide](ARCHITECTURE_IMPLEMENTATION_GUIDE.txt) — detailed behavior, configuration, recovery, reports, and design rules.
- [Paper soak runbook](PAPER_SOAK_RUNBOOK.md) — five-day Paper safety check.
