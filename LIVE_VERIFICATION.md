# AutoTick Live Verification

This is a temporary manual smoke flow for validating the implemented AutoTick runtime against the real AngelOne broker without unit or integration tests.

## Safety Scope

- Uses real Live mode and places real broker orders.
- Default verification contract: `GOLDPETAL30SEP26FUT` on `MCX`.
- Quantity: `1` lot.
- Maximum filled entries per day: `1`.
- Position type: `POSITIONAL`.
- Stop-loss: `2%`.
- Target: `5%`.
- Trailing stop: disabled.
- Long trigger: LTP above previous-day high plus `0.15%`.
- Short trigger: LTP below previous-day low minus `0.15%`.
- Verification market window: `09:00` to `23:30` Asia/Kolkata.
- Uses separate SQLite state: `state/live_verification.db`.
- Uses separate log: `logs/live_verification.log`.

These values are only for plumbing verification and are not a trading recommendation.

## Swing Live Observation

- Edit the same `autotick/config/swing_watchlist.csv` each day using the header `symbol,trigger_price`.
- Run `python -m autotick.swing_verification_main`; this places real NSE orders up to ₹5,000 each and maximum 5 filled entries per day.
- Entry requires LTP above the CSV trigger. Fixed stop-loss is 2%; daily ATR(14) at 2.5x starts after a 5% gain, with no fixed profit target.
- Keep the process running for automatic next-day reload. Open positions stay managed; after close, their symbols leave runtime subscriptions immediately.

## Before Market

1. Use branch `feature/autotick-rebuild-phase_25_28`.
2. Keep valid AngelOne credentials in `autotick/config/angelone_keys.env`.
3. Confirm `GOLDPETAL30SEP26FUT` is returned by AngelOne and is tradable in the account before allowing an order.
4. Confirm sufficient commodity margin is available for one lot plus charges.
5. Delete `state/live_verification.db` only when intentionally starting a completely fresh verification profile.

## Run

    python -m autotick.live_verification_main --config autotick/config/live_verification.yaml

## Expected Flow

1. Configuration and AngelOne login succeed.
2. Log shows `Reports enabled`.
3. Log shows `LIVE_VERIFY ready` with previous high, low, and both triggers.
4. When LTP crosses first, log shows `LIVE_VERIFY BUY TRIGGER` or `LIVE_VERIFY SELL TRIGGER`.
5. Before the real broker call, log shows `AngelOne PLACE ORDER`.
6. Successful broker acceptance logs `AngelOne order accepted` with broker order ID.
7. AutoTick reconciliation detects the broker fill and opens the managed position.
8. Stop AutoTick manually while the position is still open.
9. Restart with the exact same command and config.
10. Recovery should log the recovered order/position/trade counts and must not place a second entry order.
11. When the configured stop-loss or target is reached, AutoTick places the opposite protective EXIT order: SELL for a long position or BUY for a short position.
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
- `LIVE_VERIFY ENTRY RANGE`
- `LIVE_VERIFY POSITION RANGE`
- `LIVE_VERIFY BUY TRIGGER`
- `LIVE_VERIFY SELL TRIGGER`
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

The manual Live verification passes when one real entry order (BUY or SELL) is accepted and filled, AutoTick is stopped and restarted while the position is open, recovery prevents a duplicate entry, one opposite protective exit order is accepted and filled, the broker position closes, and both strategy-specific and combined report files contain exactly one new completed trade with the correct P&L.
