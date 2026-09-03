# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe

AutoTick command-line entry point and mode runner.
"""

from __future__ import annotations

import argparse
from contextlib import suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Event
from time import sleep
from uuid import uuid4

from autotick.config.loader import load_config
from autotick.engine import (
    CalendarSessionManager,
    ReconnectManager,
    ReconnectStopped,
    RiskManager,
    SignalValidator,
    TradeManager,
)
from autotick.indicators import AverageTrueRange
from autotick.models import (
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PositionType,
    SignalType,
)
from autotick.persistence import PersistenceError, RecoveryManager, RecoveryResult
from autotick.providers.factory import ProviderFactory
from autotick.providers.session_pool import (
    BrokerAuthenticationError,
    BrokerError,
    BrokerWriteUncertainError,
)
from autotick.strategy.context import StrategyContext
from autotick.strategy.simple_strategy import SimpleStrategy
from autotick.utils.logger import configure_logging, get_logger, log_call

logger = get_logger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AutoTick algorithmic trading framework"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args()


def _symbols(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _setup_strategy(providers, symbol: str) -> SimpleStrategy | None:
    """Create one strategy when its tick and completed daily bars are ready."""
    logger.debug("_setup_strategy entry symbol=%s strategy_class=%s", symbol, SimpleStrategy.__name__)
    tick = providers.market_data.get_tick(symbol)
    if tick is None:
        logger.debug("_setup_strategy exit symbol=%s reason=no_tick", symbol)
        return None

    strategy = SimpleStrategy()
    logger.debug("_setup_strategy created symbol=%s strategy=%s", symbol, type(strategy).__name__)
    strategy.initialize(StrategyContext(providers.market_data, symbol, tick=tick))
    strategy.on_market_open()
    try:
        strategy.on_initial_setup()
    except RuntimeError as exc:
        logger.debug("Strategy waiting for %s data: %s", symbol, exc)
        logger.debug("_setup_strategy exit symbol=%s reason=waiting", symbol)
        return None
    logger.debug("_setup_strategy exit symbol=%s strategy=%s", symbol, type(strategy).__name__)
    return strategy


@log_call()
def _setup_strategies(
    providers,
    symbols: list[str],
) -> dict[str, SimpleStrategy]:
    strategies: dict[str, SimpleStrategy] = {}
    for symbol in symbols:
        strategy = _setup_strategy(providers, symbol)
        if strategy is not None:
            strategies[symbol] = strategy
    return strategies


@log_call(log_result=True)
def _place_order(
    trades: TradeManager,
    risk: RiskManager,
    signal,
    quantity: int,
    position_type: PositionType,
) -> Order:
    order = Order(
        order_id=str(uuid4()),
        symbol=signal.symbol,
        exchange=signal.exchange,
        side=OrderSide.BUY,
        quantity=quantity,
        price=signal.price,
        position_type=position_type,
    )
    return trades.create_order(risk.validate_order(order, signal.price))


def _reconcile_orders(trades: TradeManager, entered: set[str]) -> None:
    """Refresh pending orders and allow retries after failed entries."""
    failed = {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}
    for order in trades.reconcile_orders():
        if order.intent == OrderIntent.ENTRY and order.status in failed:
            entered.discard(order.symbol)


def _save_state(
    persistence: RecoveryManager | None,
    risk: RiskManager,
    trading_date: date,
    last_processed_at: datetime | None = None,
) -> None:
    """Save changed state and block new entries after a write failure."""
    if persistence is None:
        return
    try:
        persistence.save(trading_date, last_processed_at)
    except PersistenceError:
        risk.activate_kill_switch()
        logger.exception("State persistence failed; new entries blocked")


def _trailing_atr(providers, risk: RiskManager, symbol: str, now: datetime | None) -> float | None:
    """Calculate ATR from the latest completed configured candles."""
    if not risk.trailing_enabled or now is None:
        return None
    interval = risk.trailing_atr_interval
    bars = providers.market_data.get_bars(symbol, interval)
    if interval == "1d":
        completed = [bar for bar in bars if bar.timestamp.date() < now.date()]
    else:
        completed = [
            bar
            for bar in bars
            if _comparable_time(bar.timestamp) + timedelta(minutes=15)
            <= _comparable_time(now)
        ]
    value = AverageTrueRange(risk.trailing_atr_period).calculate(completed)
    if value is None:
        logger.warning(
            "ATR unavailable for %s interval=%s period=%s; target exit will be used",
            symbol,
            interval,
            risk.trailing_atr_period,
        )
    return value


def _comparable_time(value: datetime) -> datetime:
    """Compare provider timestamps safely when CSV bars are timezone-naive."""
    return value.replace(tzinfo=None)


def _process_symbols(
    providers,
    symbols: list[str],
    strategies: dict[str, SimpleStrategy],
    trades: TradeManager,
    risk: RiskManager,
    entered: set[str],
    quantity: int,
    position_type: PositionType,
    mode: str,
) -> None:
    logger.debug(
        "_process_symbols entry mode=%s symbols=%s strategies=%s entered=%s",
        mode,
        symbols,
        sorted(strategies),
        sorted(entered),
    )
    for symbol in symbols:
        logger.debug("_process_symbols symbol entry symbol=%s", symbol)
        tick = providers.market_data.get_tick(symbol)
        if tick is None or tick.ltp is None:
            logger.debug("_process_symbols symbol exit symbol=%s reason=no_tick", symbol)
            continue

        logger.debug(
            "_process_symbols tick symbol=%s exchange=%s ltp=%s",
            symbol,
            tick.exchange,
            tick.ltp,
        )
        exit_prices = trades.get_exit_prices(symbol, tick.exchange)
        trailing_atr = None
        if (
            exit_prices is not None
            and risk.trailing_enabled
            and exit_prices[2] is None
            and tick.ltp >= exit_prices[1]
        ):
            trailing_atr = _trailing_atr(
                providers,
                risk,
                symbol,
                tick.timestamp,
            )
        exit_result = trades.monitor_exit(
            symbol,
            tick.exchange,
            tick.ltp,
            trailing_atr,
        )
        updated_prices = trades.get_exit_prices(symbol, tick.exchange)
        if trailing_atr is not None and exit_result is None:
            if updated_prices is not None and updated_prices[2] is not None:
                logger.info(
                    "ATR trailing stop activated %s: interval=%s period=%s "
                    "atr=%.2f multiplier=%.2f stop=%.2f",
                    symbol,
                    risk.trailing_atr_interval,
                    risk.trailing_atr_period,
                    trailing_atr,
                    risk.trailing_atr_multiplier,
                    updated_prices[2],
                )
        if exit_result is not None:
            order, reason = exit_result
            if order.status == OrderStatus.FILLED:
                position = trades.get_position(symbol, tick.exchange)
                logger.done(
                    "%s %s SELL filled %s: %s qty=%s buy_price=%.2f "
                    "sell_price=%.2f proceeds=%.2f pnl=%.2f funds=%.2f",
                    mode.upper(),
                    reason,
                    order.order_id,
                    symbol,
                    order.quantity,
                    position.average_price,
                    order.price,
                    float(order.price) * order.quantity,
                    position.realized_pnl,
                    providers.account.get_balance(),
                )
            else:
                log_order = (
                    logger.error
                    if order.status == OrderStatus.REJECTED
                    else logger.info
                )
                log_order(
                    "%s %s SELL order %s: %s qty=%s sell_price=%.2f status=%s",
                    mode.upper(),
                    reason,
                    order.order_id,
                    symbol,
                    order.quantity,
                    order.price,
                    order.status.value,
                )
            logger.debug("_process_symbols symbol exit symbol=%s reason=exit_order", symbol)
            continue

        active_trade = trades.has_active_trade(symbol, tick.exchange)
        already_entered = symbol in entered
        if active_trade or already_entered:
            logger.debug(
                "Strategy skipped symbol=%s active_trade=%s already_entered=%s",
                symbol,
                active_trade,
                already_entered,
            )
            continue

        strategy = strategies.get(symbol)
        if strategy is None:
            logger.debug("Strategy missing for %s; setup requested", symbol)
            strategy = _setup_strategy(providers, symbol)
            if strategy is None:
                logger.debug("_process_symbols symbol exit symbol=%s reason=strategy_not_ready", symbol)
                continue
            strategies[symbol] = strategy

        logger.debug(
            "Calling strategy.on_tick symbol=%s strategy=%s",
            symbol,
            type(strategy).__name__,
        )
        strategy.context.tick = tick
        signal = strategy.on_tick(tick)
        logger.debug(
            "strategy.on_tick returned symbol=%s strategy=%s signal=%s",
            symbol,
            type(strategy).__name__,
            signal.signal_type.value if signal is not None else None,
        )
        if signal is None or signal.signal_type != SignalType.BUY:
            logger.debug("_process_symbols symbol exit symbol=%s reason=no_buy_signal", symbol)
            continue

        SignalValidator.validate(signal)
        if signal.price is None or not risk.can_trade(signal.price):
            logger.debug(
                "Order blocked by risk limits: %s price=%s",
                symbol,
                signal.price,
            )
            continue

        order = _place_order(trades, risk, signal, quantity, position_type)
        if order.status != OrderStatus.REJECTED:
            entered.add(symbol)
        if order.status == OrderStatus.FILLED:
            stop_loss, target, _ = trades.get_exit_prices(symbol, tick.exchange)
            logger.done(
                "%s BUY filled %s: %s qty=%s buy_price=%.2f cost=%.2f "
                "stop_loss=%.2f target=%.2f funds=%.2f",
                mode.upper(),
                order.order_id,
                symbol,
                order.quantity,
                order.price,
                float(order.price) * order.quantity,
                stop_loss,
                target,
                providers.account.get_balance(),
            )
        else:
            log_order = (
                logger.error if order.status == OrderStatus.REJECTED else logger.info
            )
            log_order(
                "%s BUY order %s: %s qty=%s buy_price=%.2f status=%s funds=%.2f",
                mode.upper(),
                order.order_id,
                symbol,
                order.quantity,
                order.price,
                order.status.value,
                providers.account.get_balance(),
            )
        logger.debug("_process_symbols symbol exit symbol=%s order_status=%s", symbol, order.status.value)
    logger.debug("_process_symbols exit")


def _run_realtime(
    providers,
    config: dict,
    symbols: list[str],
    trades: TradeManager,
    risk: RiskManager,
    position_type: PositionType,
    recovery: RecoveryResult | None = None,
    persistence: RecoveryManager | None = None,
    state_manager: RecoveryManager | None = None,
    reconnect: ReconnectManager | None = None,
    stop_event: Event | None = None,
) -> date:
    strategies: dict[str, SimpleStrategy] | None = None
    blocked = set(recovery.blocked_symbols) if recovery else set()
    entered = set(recovery.entered_symbols) | blocked if recovery else set()
    trading_date = (
        recovery.trading_date
        if recovery is not None
        else providers.calendar_session.now().date()
    )
    loop_sleep = float(config["engine"]["loop_sleep_s"])
    loop_count = 0
    logger.debug(
        "_run_realtime entry symbols=%s trading_date=%s blocked=%s entered=%s loop_sleep=%s",
        symbols,
        trading_date,
        sorted(blocked),
        sorted(entered),
        loop_sleep,
    )

    while stop_event is None or not stop_event.is_set():
        loop_count += 1
        now = providers.calendar_session.now()
        market_open = providers.calendar_session.is_market_open(now)
        logger.debug(
            "_run_realtime loop=%s now=%s market_open=%s strategies=%s entered=%s blocked=%s",
            loop_count,
            now,
            market_open,
            sorted(strategies or {}),
            sorted(entered),
            sorted(blocked),
        )
        if config["session"]["only_market_hours"] and not market_open:
            logger.warning(
                "Market is closed at %s; next open is %s. Exiting realtime runner.",
                now,
                providers.calendar_session.next_open(now),
            )
            break

        if now.date() != trading_date and market_open:
            for strategy in (strategies or {}).values():
                strategy.on_market_close()
            risk.reset_daily_state()
            entered = set(blocked)
            strategies = None
            trading_date = now.date()
            logger.debug("_run_realtime new trading day=%s", trading_date)

        try:
            if strategies is None:
                logger.debug("_run_realtime setting up strategies")
                strategies = _setup_strategies(providers, symbols)
                logger.debug("_run_realtime strategies ready=%s", sorted(strategies))

            if not config["session"]["only_market_hours"] or market_open:
                balance = providers.account.get_balance()
                logger.debug("_run_realtime balance=%s", balance)
                risk.update(balance)
                _reconcile_orders(trades, entered)
                _process_symbols(
                    providers,
                    symbols,
                    strategies,
                    trades,
                    risk,
                    entered,
                    config["trade"]["quantity"],
                    position_type,
                    config["mode"],
                )
                _save_state(persistence, risk, trading_date)
        except BrokerError as exc:
            logger.debug("_run_realtime broker error=%s", type(exc).__name__)
            if reconnect is None or state_manager is None:
                raise
            uncertain_write = isinstance(exc, BrokerWriteUncertainError)
            try:
                reconciled = reconnect.recover(
                    exc,
                    lambda: state_manager.reconcile(trading_date),
                )
            except ReconnectStopped:
                logger.done("Broker recovery stopped by shutdown request")
                break
            except BrokerAuthenticationError:
                risk.activate_kill_switch()
                _save_state(persistence, risk, trading_date)
                logger.error(
                    "Broker authentication recovery exhausted; safe shutdown started"
                )
                break

            blocked.update(reconciled.blocked_symbols)
            entered = set(reconciled.entered_symbols) | blocked
            strategies = None
            _save_state(persistence, risk, trading_date)
            logger.debug(
                "_run_realtime recovery completed blocked=%s entered=%s",
                sorted(blocked),
                sorted(entered),
            )
            if uncertain_write:
                risk.activate_kill_switch()
                _save_state(persistence, risk, trading_date)
                logger.error(
                    "Broker write result remains uncertain; state reconciled and "
                    "safe shutdown started"
                )
                break
            continue

        if stop_event is None:
            sleep(loop_sleep)
        else:
            stop_event.wait(loop_sleep)
    logger.debug("_run_realtime exit trading_date=%s loops=%s", trading_date, loop_count)
    return trading_date


def _run_historical(
    providers,
    config: dict,
    symbols: list[str],
    trades: TradeManager,
    risk: RiskManager,
    position_type: PositionType,
    persistence: RecoveryManager | None = None,
) -> date | None:
    logger.debug("_run_historical entry symbols=%s", symbols)
    timestamps = providers.market_data.timestamps()
    strategies: dict[str, SimpleStrategy] = {}
    entered: set[str] = set()
    trading_date = None
    last_processed_at = None

    for value in timestamps:
        logger.debug("_run_historical loop timestamp=%s", value)
        last_processed_at = value
        providers.calendar_session.wait_until(value)
        providers.calendar_session.update_time(value)
        providers.market_data.update_time(value)

        if trading_date != value.date():
            for strategy in strategies.values():
                strategy.on_market_close()
            if trading_date is not None:
                risk.reset_daily_state()
            entered.clear()
            strategies = _setup_strategies(providers, symbols)
            trading_date = value.date()

        if config["session"]["only_market_hours"]:
            if not providers.calendar_session.is_market_open(value):
                continue
        _reconcile_orders(trades, entered)
        _process_symbols(
            providers,
            symbols,
            strategies,
            trades,
            risk,
            entered,
            config["trade"]["quantity"],
            position_type,
            config["mode"],
        )
    if trading_date is not None:
        _save_state(persistence, risk, trading_date, last_processed_at)
    logger.debug("_run_historical exit trading_date=%s", trading_date)
    return trading_date


def _run_providers(
    providers,
    config: dict,
    stop_event: Event | None = None,
) -> None:
    mode = config["mode"].lower()
    symbols = _symbols(config["market"]["symbols"])
    logger.debug("_run_providers entry mode=%s symbols=%s", mode, symbols)
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    state_manager = RecoveryManager(
        config,
        trades,
        risk,
        providers.account,
        providers.execution,
    )
    persistence = state_manager if config["persistence"]["enabled"] else None
    reconnect = (
        ReconnectManager(
            providers.broker_session,
            providers.market_data,
            symbols,
            config["reconnect"],
            stop_event,
        )
        if mode in {"live", "paper"}
        and config["reconnect"]["enabled"]
        and providers.broker_session is not None
        else None
    )
    position_type = PositionType(
        config["trade"].get("position_type", "POSITIONAL").upper()
    )

    runtime_date = (
        date.min
        if mode in {"backtest", "replay"}
        else providers.calendar_session.now().date()
    )
    persistence_ready = False
    try:
        if mode in {"live", "paper"} and config["session"]["only_market_hours"]:
            now = providers.calendar_session.now()
            if not providers.calendar_session.is_market_open(now):
                logger.warning(
                    "Market is closed at %s; next open is %s. Provider setup skipped.",
                    now,
                    providers.calendar_session.next_open(now),
                )
                return

        try:
            logger.debug("_run_providers connecting market data")
            providers.market_data.connect()
            logger.debug("_run_providers connecting account")
            providers.account.connect()
            recovery = (
                persistence.recover(runtime_date)
                if persistence is not None
                else RecoveryResult(runtime_date)
            )
            logger.debug(
                "_run_providers recovery complete entered=%s blocked=%s",
                sorted(recovery.entered_symbols),
                sorted(recovery.blocked_symbols),
            )
            providers.market_data.subscribe(symbols)
            logger.debug("_run_providers subscribed symbols=%s", symbols)
        except BrokerError as exc:
            logger.debug("_run_providers startup broker error=%s", type(exc).__name__)
            if reconnect is None:
                raise
            try:
                recovery = reconnect.recover(
                    exc,
                    lambda: (
                        persistence.recover(runtime_date)
                        if persistence is not None
                        else state_manager.reconcile(runtime_date)
                    ),
                )
            except ReconnectStopped:
                logger.done("Broker startup recovery stopped by shutdown request")
                return
            except BrokerAuthenticationError:
                risk.activate_kill_switch()
                _save_state(persistence, risk, runtime_date)
                logger.error(
                    "Broker authentication recovery exhausted; startup stopped safely"
                )
                return
        persistence_ready = persistence is not None
        if mode in {"backtest", "replay"}:
            logger.debug("_run_providers entering historical runner")
            runtime_date = _run_historical(
                providers,
                config,
                symbols,
                trades,
                risk,
                position_type,
                persistence,
            )
        else:
            logger.debug("_run_providers entering realtime runner")
            runtime_date = _run_realtime(
                providers,
                config,
                symbols,
                trades,
                risk,
                position_type,
                recovery,
                persistence,
                state_manager,
                reconnect,
                stop_event,
            )
    finally:
        logger.debug("_run_providers shutdown entry runtime_date=%s", runtime_date)
        if (
            persistence_ready
            and runtime_date is not None
            and mode not in {"backtest", "replay"}
        ):
            _save_state(persistence, risk, runtime_date)
        with suppress(Exception):
            providers.market_data.unsubscribe(symbols)
        with suppress(Exception):
            providers.account.disconnect()
        with suppress(Exception):
            providers.market_data.disconnect()
        if providers.broker_session is not None:
            with suppress(Exception):
                providers.broker_session.logout()
        logger.done("AutoTick provider shutdown completed")
        logger.debug("_run_providers exit")


def _run_ui_data(config: dict) -> None:
    """Run Paper mode with UI-backed simulated providers in one process."""
    from simulated_control_panel import run_control_panel

    symbols = _symbols(config["market"]["symbols"])
    broker = str(config["broker"]).strip().lower()
    simulated_config = config.get("simulated", {})
    broker_auto_fetch = simulated_config.get("broker_auto_fetch", False)
    credentials_file = (
        config.get("broker_config", {}).get(broker, {}).get("credentials_file")
    )

    def runner(providers, stop_event: Event) -> None:
        calendar = CalendarSessionManager(config["session"])
        calendar.configure_mode("paper")
        providers.calendar_session = calendar
        _run_providers(providers, config, stop_event)

    run_control_panel(
        strategy_runner=runner,
        configured_capital=float(config["capital"]),
        exchange=config["market"]["exchange"],
        initial_symbol=symbols[0],
        initial_interval="1d",
        credentials_file=credentials_file,
        source_broker=broker if broker != "simulated" else None,
        source_config=config,
        broker_auto_fetch=broker_auto_fetch,
    )


def main() -> None:
    print("..... main start .....")
    try:
        args = _parse_args()
        config_path = args.config.expanduser().resolve()
        config = load_config(config_path)
        logging_config = config["logging"]
        configure_logging(
            level=logging_config["level"],
            log_file=logging_config["log_file"],
            file=logging_config["enabled"],
            timestamp=logging_config["timestamp"],
        )

        mode = config["mode"].lower()
        logger.debug("main entry config=%s strategy_class=%s", config_path, SimpleStrategy.__name__)
        logger.done("Configuration loaded from %s", config_path)
        logger.info("Starting mode=%s", mode.upper())

        if config.get("simulated", {}).get("ui_data_enabled", False):
            logger.info("Starting Paper mode with simulated UI data")
            _run_ui_data(config)
        else:
            logger.debug("main creating providers mode=%s", mode)
            providers = ProviderFactory.create_bundle(mode, config)
            logger.debug(
                "main providers created market_data=%s account=%s execution=%s",
                type(providers.market_data).__name__,
                type(providers.account).__name__,
                type(providers.execution).__name__,
            )
            _run_providers(providers, config)
    except KeyboardInterrupt:
        logger.done("AutoTick stopped by user")
    except Exception:
        logger.exception("AutoTick runner failed")
        raise
    finally:
        logger.debug("main exit")
        print("..... main   end .....")


if __name__ == "__main__":
    main()
