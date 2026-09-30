"""Offline checks for configured Swing shutdown and provider cleanup."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

import autotick.main as main
from autotick.engine.market_session import CalendarSessionManager
from autotick.models import PositionType
from autotick.persistence import RecoveryResult
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider, SimulatedExecutionProvider,
    SimulatedMarketDataProvider, SimulatedSession,
)
from autotick.providers.factory import ProviderBundle


@pytest.mark.parametrize('market_end', ['15:30', '14:00'])
@pytest.mark.parametrize('only_market_hours', [True, False])
def test_swing_stops_at_close_and_caps_sleep(monkeypatch, market_end, only_market_hours):
    close = datetime.fromisoformat('2026-09-30T' + market_end).replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    clock = [close - timedelta(seconds=2)]
    config = {
        'strategy': 'swing', 'engine': {'loop_sleep_s': 120},
        'session': {'market_end': market_end, 'only_market_hours': only_market_hours},
        'market': {'exchange': 'NSE'},
    }
    calendar = CalendarSessionManager(config['session'])
    monkeypatch.setattr(calendar, 'now', lambda: clock[0])
    providers = SimpleNamespace(calendar_session=calendar, account=Mock())
    process = Mock()
    trades, risk = Mock(), Mock()
    # Keep a positional holding present throughout the session and shutdown.
    holding = object()
    trades.positions = {'INFY-EQ': holding}
    monkeypatch.setattr(main, '_reload_swing_symbols', Mock())
    monkeypatch.setattr(main, '_setup_strategies', lambda *args: {})
    monkeypatch.setattr(main, '_reconcile_orders', Mock())
    monkeypatch.setattr(main, '_remove_closed_swing_symbols', Mock())
    square_off = Mock(return_value=False)
    monkeypatch.setattr(main, '_square_off_if_due', square_off)
    monkeypatch.setattr(main, '_process_symbols', process)
    monkeypatch.setattr(main, '_save_state', Mock())
    waits = []

    def advance(seconds):
        waits.append(seconds)
        clock[0] += timedelta(seconds=seconds)
        assert len(waits) < 3, 'runner waited overnight instead of stopping'

    monkeypatch.setattr(main, 'sleep', advance)
    assert main._run_realtime(providers, config, [], trades, risk, PositionType.POSITIONAL) == close.date()
    assert waits == [2]
    assert clock[0] == close
    process.assert_called_once()
    square_off.assert_called_once()
    assert trades.positions == {'INFY-EQ': holding}


@pytest.mark.parametrize('seconds_after', [0, 1, 3600])
def test_no_strategy_or_broker_work_at_or_after_close(monkeypatch, seconds_after):
    now = datetime(2026, 9, 30, 15, 30, tzinfo=ZoneInfo('Asia/Kolkata')) + timedelta(seconds=seconds_after)
    calendar = CalendarSessionManager({'market_end': '15:30'})
    monkeypatch.setattr(calendar, 'now', lambda: now)
    providers = SimpleNamespace(calendar_session=calendar, account=Mock())
    setup = Mock(side_effect=AssertionError('strategy started after close'))
    monkeypatch.setattr(main, '_setup_strategies', setup)
    config = {'strategy': 'swing', 'engine': {'loop_sleep_s': 1}, 'session': {'only_market_hours': False}}
    main._run_realtime(providers, config, [], Mock(), Mock(), PositionType.POSITIONAL)
    setup.assert_not_called()
    providers.account.get_balance.assert_not_called()


def test_provider_shutdown_saves_and_disconnects_at_close(tmp_path, make_config, monkeypatch):
    path = tmp_path / 'swing_watchlist.csv'
    path.write_text('symbol,trigger_price\n', encoding='utf-8')
    config = make_config()
    config.update({
        'strategy': 'swing', 'strategy_config': {'csv_file': str(path)},
        'engine': {'loop_sleep_s': 120}, 'reconnect': {'enabled': False},
        'session': {'market_end': '15:30', 'only_market_hours': True},
    })
    config['persistence']['enabled'] = True
    close = datetime(2026, 9, 30, 15, 30, tzinfo=ZoneInfo('Asia/Kolkata'))
    times = iter([close - timedelta(seconds=1)] * 2 + [close])
    calendar = CalendarSessionManager(config['session'])
    monkeypatch.setattr(calendar, 'now', lambda: next(times, close))
    session = SimulatedSession()
    providers = ProviderBundle(
        SimulatedMarketDataProvider(session), SimulatedAccountProvider(session, 1000),
        SimulatedExecutionProvider(session), calendar, broker_session=Mock(),
    )
    manager = Mock()
    manager.recover.return_value = RecoveryResult(close.date())
    monkeypatch.setattr(main, 'RecoveryManager', Mock(return_value=manager))
    save = Mock()
    monkeypatch.setattr(main, '_save_state', save)
    disconnect_data = Mock(wraps=providers.market_data.disconnect)
    disconnect_account = Mock(wraps=providers.account.disconnect)
    monkeypatch.setattr(providers.market_data, 'disconnect', disconnect_data)
    monkeypatch.setattr(providers.account, 'disconnect', disconnect_account)
    main._run_providers(providers, config)
    assert save.call_args.args[0] is manager
    assert save.call_args.args[2] == close.date()
    disconnect_data.assert_called_once()
    disconnect_account.assert_called_once()
    providers.broker_session.logout.assert_called_once()
