# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 2026

@author: ashwe
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import autotick.main as main_module
import autotick.strategy.swing_strategy as swing_module
from autotick.engine.market_session import CalendarSessionManager
from autotick.models.market import MarketTick
from autotick.models.signal import SignalType
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle
from autotick.strategy.swing_strategy import SwingStrategy, load_swing_watchlist


def _csv(tmp_path, filename, rows):
    path = tmp_path / filename
    path.write_text("symbol,trigger_price\n" + rows, encoding="utf-8")
    return path


def test_imports_multiple_files_oldest_first_and_preserves_existing_rows(tmp_path):
    path = tmp_path / "swing_watchlist.csv"
    original = "symbol,trigger_price,note\ninfy-eq,100.00,keep"
    path.write_text(original, encoding="utf-8")
    newest = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv",
                  "TCS-EQ,999\nHDFC-EQ,300\n")
    oldest = _csv(tmp_path, "swing_watchlist_import_20260929_180000.csv",
                  "INFY-EQ,999\nTCS-EQ,200\ntcs-eq,201\n")
    untouched = _csv(tmp_path, "swing_watchlist_import_notes.csv", "OTHER-EQ,400\n")

    assert load_swing_watchlist(path, import_pending=True) == {
        "INFY-EQ": 100, "TCS-EQ": 200, "HDFC-EQ": 300,
    }
    assert path.read_text(encoding="utf-8").startswith(original + "\n")
    assert not oldest.exists() and not newest.exists()
    assert untouched.exists()
    assert load_swing_watchlist(path) == {"INFY-EQ": 100, "TCS-EQ": 200, "HDFC-EQ": 300}


@pytest.mark.parametrize("rows", ["INFY-EQ,999\ninfy-eq,888\n", ""])
def test_duplicate_only_or_empty_import_is_deleted_without_rewriting_master(tmp_path, rows):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    original = path.read_bytes()
    source = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv", rows)

    assert load_swing_watchlist(path, import_pending=True) == {"INFY-EQ": 100}
    assert path.read_bytes() == original
    assert not source.exists()


@pytest.mark.parametrize("value", ["bad", "0", "-1", "nan", "inf"])
def test_invalid_import_keeps_entire_source_and_master_unchanged(tmp_path, value):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    original = path.read_bytes()
    source = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv",
                  f"TCS-EQ,200\nBAD-EQ,{value}\n")

    with pytest.raises(ValueError):
        load_swing_watchlist(path, import_pending=True)
    assert source.exists()
    assert path.read_bytes() == original


def test_invalid_headers_are_retained(tmp_path):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    source = tmp_path / "swing_watchlist_import_20260930_180000.csv"
    source.write_text("symbol,price\nTCS-EQ,200\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires symbol,trigger_price"):
        load_swing_watchlist(path, import_pending=True)
    assert source.exists()
    assert load_swing_watchlist(path) == {"INFY-EQ": 100}


def test_import_accepts_bom_and_normalizes_headers_and_symbols(tmp_path):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    source = tmp_path / "swing_watchlist_import_20260930_180000.csv"
    source.write_text("symbol , trigger_price\n tcs-eq ,200\n", encoding="utf-8-sig")

    assert load_swing_watchlist(path, import_pending=True) == {"INFY-EQ": 100, "TCS-EQ": 200}
    assert not source.exists()


def test_failed_atomic_save_keeps_source_and_master(tmp_path, monkeypatch):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    original = path.read_bytes()
    source = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv", "TCS-EQ,200\n")

    def unavailable(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(swing_module.os, "replace", unavailable)
    with pytest.raises(OSError, match="disk unavailable"):
        load_swing_watchlist(path, import_pending=True)
    assert source.exists()
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_delete_can_be_reprocessed_without_duplicate_rows(tmp_path, monkeypatch):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    source = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv", "TCS-EQ,200\n")
    unlink = Path.unlink

    def locked(self, *args, **kwargs):
        if self == source:
            raise PermissionError("import is locked")
        return unlink(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", locked)
        with pytest.raises(PermissionError, match="import is locked"):
            load_swing_watchlist(path, import_pending=True)
    saved = path.read_bytes()
    assert source.exists()
    assert load_swing_watchlist(path, import_pending=True) == {"INFY-EQ": 100, "TCS-EQ": 200}
    assert path.read_bytes() == saved
    assert not source.exists()


def test_invalid_later_file_keeps_earlier_successful_import(tmp_path):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\n")
    first = _csv(tmp_path, "swing_watchlist_import_20260929_180000.csv", "TCS-EQ,200\n")
    second = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv", "BAD-EQ,bad\n")

    with pytest.raises(ValueError):
        load_swing_watchlist(path, import_pending=True)
    assert not first.exists() and second.exists()
    assert load_swing_watchlist(path) == {"INFY-EQ": 100, "TCS-EQ": 200}


def test_startup_imports_but_daily_reload_and_strategy_setup_do_not(tmp_path, make_config, monkeypatch):
    path = _csv(tmp_path, "swing_watchlist.csv", "")
    source = _csv(tmp_path, "swing_watchlist_import_20260929_180000.csv", "INFY-EQ,100\n")
    config = make_config()
    config.update({
        "strategy": "swing", "strategy_config": {"csv_file": str(path)},
        "engine": {"loop_sleep_s": 1}, "reconnect": {"enabled": False},
        "session": {"schedule_type": "ALWAYS_OPEN", "only_market_hours": False},
    })
    config["persistence"]["enabled"] = False
    session = SimulatedSession()
    calendar = CalendarSessionManager(config["session"])
    providers = ProviderBundle(
        SimulatedMarketDataProvider(session), SimulatedAccountProvider(session, 1000),
        SimulatedExecutionProvider(session), calendar,
    )

    def realtime(providers, config, symbols, trades, *args):
        assert symbols == ["INFY-EQ"]
        assert not source.exists()
        later = _csv(tmp_path, "swing_watchlist_import_20260930_180000.csv", "TCS-EQ,200\n")
        main_module._reload_swing_symbols(providers, config, symbols, trades, calendar.now().date())
        assert symbols == ["INFY-EQ"]
        strategy = SwingStrategy(path)
        strategy.context = SimpleNamespace(symbol="INFY-EQ")
        strategy.on_initial_setup()
        assert strategy.trigger_price == 100
        signal = strategy.on_tick(MarketTick("INFY-EQ", "NSE", 101, 1, calendar.now()))
        assert signal.signal_type == SignalType.BUY
        assert later.exists()
        assert load_swing_watchlist(path) == {"INFY-EQ": 100}
        return calendar.now().date()

    monkeypatch.setattr(main_module, "_run_realtime", realtime)
    main_module._run_providers(providers, config)


def test_duplicate_master_rows_still_rejected(tmp_path):
    path = _csv(tmp_path, "swing_watchlist.csv", "INFY-EQ,100\ninfy-eq,200\n")
    with pytest.raises(ValueError, match="Duplicate swing symbol"):
        load_swing_watchlist(path)
