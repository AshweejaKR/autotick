# AutoTick Live Verification

This is a temporary manual smoke flow for validating the implemented AutoTick runtime against the real AngelOne broker without unit or integration tests.

## Safety Scope

- Uses real Live mode and places real broker orders.
- Default verification contract: `SILVER10030SEP26FUT` on `MCX`.
- Silver100 is the 100 gram MCX silver futures contract.
- Quantity: `1` lot.
- Maximum filled entries per day: `1`.
- Position type: `POSITIONAL`.
- Stop-loss: `0.10%`.
- Target: `0.15%`.
- Trailing stop: disabled.
- Entry trigger: LTP above previous close by `0.05%`.
- Verification market window: `09:00` to `23:30` Asia/Kolkata.
- Uses separate SQLite state: `state/live_verification.db`.
- Uses separate log: `logs/live_verification.log`.

These values are only for plumbing verification and are not a trading recommendation.

## Before Market

1. Use branch `feature/autotick-rebuild-phase_25_28`.
2. Keep valid AngelOne credentials in `autotick/config/angelone_keys.env`.
3. Confirm `SILVER10030SEP26FUT` is returned by AngelOne and is tradable in the account before allowing an order.
4. Confirm sufficient commodity margin is available for one lot plus charges.
5. Delete `state/live_verification.db` only when intentionally starting a completely fresh verification profile.

## Run

    python -m autotick.live_verification_main --config autotick/config/live_verification.yaml

## Expected Flow

1. Configuration and AngelOne login succeed.
2. Log shows `Reports enabled`.
3. Log shows `LIVE_VERIFY ready` with previous close and entry trigger.
4. When LTP crosses the trigger, log shows `LIVE_VERIFY ENTRY TRIGGER`.
5. Before the real broker call, log shows `AngelOne PLACE ORDER`.
6. Successful broker acceptance logs `AngelOne order accepted` with broker order ID.
7. AutoTick reconciliation detects the broker fill and opens the managed position.
8. Stop AutoTick manually while the position is still open.
9. Restart with the exact same command and config.
10. Recovery should log the recovered order/position/trade counts and must not place a second BUY.
11. When the configured stop-loss or target is reached, AutoTick places the real SELL order.
12. After the completed EXIT fill, reports are updated.

## Report Files

Strategy-specific:

- `reports/angelone_live_verify_live_verification_live_trades.csv`
- `reports/angelone_live_verify_live_verification_live_summary.csv`

Combined:

- `reports/angelone_live_verify_live_trades.csv`
- `reports/angelone_live_verify_live_summary.csv`

One completed ENTRY + EXIT pair must append exactly one completed-trade row. Restarting must not duplicate that row.

## Useful Log Markers

Search `logs/live_verification.log` for:

- `LIVE_VERIFY ready`
- `LIVE_VERIFY ENTRY TRIGGER`
- `AngelOne PLACE ORDER`
- `AngelOne order accepted`
- `AngelOne order rejected`
- `Recovered state`
- `No saved state found`
- `Reconciled state`
- `Recovery found`
- `STOP_LOSS`
- `TARGET`
- `Report updated`
- `Report skipped duplicate`
- `Broker authentication recovery exhausted`
- `Broker write result remains uncertain`

## Pass Criteria

The manual Live verification passes when one real BUY is accepted and filled, AutoTick is stopped and restarted while the position is open, recovery prevents a duplicate entry, one real protective SELL is accepted and filled, the broker position closes, and both strategy-specific and combined report files contain exactly one new completed trade with the correct P&L.
