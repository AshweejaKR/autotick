# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 2026

@author: ashwe
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

import autotick.swing_watchlist_tool as tool
from autotick.strategy.swing_strategy import load_swing_watchlist


def _session(ltp=100):
    client = SimpleNamespace(ltpData=Mock(return_value={"status": True, "data": {"ltp": ltp}}))
    return SimpleNamespace(
        client=client, get_instrument=Mock(return_value=("INFY-EQ", "123")),
        call=lambda operation, *args: operation(*args),
    )


@pytest.mark.parametrize("trigger,note", [
    (100, "OK"), (105, "OK"), (105.01, "WARNING >5%"), (110, "WARNING >5%"),
    (110.01, "STRONG >10%"), (89, "STRONG >10%"),
])
def test_price_difference_and_warning_boundaries(trigger, note):
    session = _session()
    row = tool.validate_row(session, " infy ", trigger)
    assert row == ("INFY-EQ", trigger, 100, pytest.approx(trigger - 100), note)
    session.get_instrument.assert_called_once_with("INFY", "NSE")
    session.client.ltpData.assert_called_once_with("NSE", "INFY-EQ", "123")


@pytest.mark.parametrize("trigger", [0, -1, "bad", "nan", "inf"])
def test_invalid_trigger_never_fetches_a_quote(trigger):
    session = _session()
    with pytest.raises(ValueError, match="Trigger price"):
        tool.validate_row(session, "INFY-EQ", trigger)
    session.get_instrument.assert_not_called()


def test_unknown_symbol_is_rejected():
    session = _session()
    session.get_instrument.side_effect = ValueError("Token not found")
    with pytest.raises(ValueError, match="Token not found"):
        tool.validate_row(session, "INVALID-EQ", 100)


@pytest.mark.parametrize("data", [None, {}, {"ltp": 0}, {"ltp": "nan"}])
def test_missing_or_invalid_broker_ltp_is_rejected(data):
    session = _session()
    session.client.ltpData.return_value = {"status": True, "data": data}
    with pytest.raises(ValueError, match="LTP"):
        tool.validate_row(session, "INFY-EQ", 100)


def test_saved_csv_is_compatible_and_filename_uses_ist(tmp_path, monkeypatch):
    now = datetime(2026, 9, 30, 22, 30, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(tool, "datetime", SimpleNamespace(now=lambda tz: now.astimezone(tz)))
    path = tool.write_import(tmp_path, [tool.validate_row(_session(), "INFY-EQ", 110)])
    assert path.name == "swing_watchlist_import_20260930_223015.csv"
    assert path.read_text().splitlines() == ["symbol,trigger_price", "INFY-EQ,110.0"]
    assert load_swing_watchlist(path) == {"INFY-EQ": 110}
    with pytest.raises(FileExistsError):
        tool.write_import(tmp_path, [tool.validate_row(_session(), "INFY-EQ", 150)])
    assert load_swing_watchlist(path) == {"INFY-EQ": 110}


def test_scp_upload_renames_only_after_success(tmp_path, monkeypatch):
    key = tmp_path / "ssh_key.pem"
    key.write_text("test key")
    path = tool.write_import(tmp_path, [tool.validate_row(_session(), "INFY-EQ", 100)])
    run = Mock(return_value=SimpleNamespace(returncode=0, stderr=""))
    monkeypatch.setattr(tool.subprocess, "run", run)
    tool.upload_import(path, "ec2-user@server", str(key), "/home/ec2-user/autotick/autotick/config")
    commands = [call.args[0] for call in run.call_args_list]
    assert [command[0] for command in commands] == ["scp", "ssh"]
    assert commands[0][-1].endswith(f"/{path.name}.upload")
    assert commands[1][-1].endswith(f"/{path.name}.upload /home/ec2-user/autotick/autotick/config/{path.name}")
    assert path.exists()
    run.reset_mock()
    run.return_value = SimpleNamespace(returncode=1, stderr="permission denied")
    with pytest.raises(RuntimeError, match="permission denied"):
        tool.upload_import(path, "ec2-user@server", str(key), "/home/ec2-user/autotick/autotick/config")
    assert run.call_count == 1


@pytest.mark.parametrize("host,folder", [
    ("-oProxyCommand@server", "/home/ec2-user"), ("user@server;echo", "/home/ec2-user"),
    ("user@server", "/tmp;echo"), ("user@server", "relative/path"),
])
def test_unsafe_ssh_settings_never_start_a_process(tmp_path, monkeypatch, host, folder):
    run = Mock()
    monkeypatch.setattr(tool.subprocess, "run", run)
    with pytest.raises(ValueError):
        tool.upload_import(tmp_path / "file.csv", host, tmp_path / "key.pem", folder)
    run.assert_not_called()


def test_upload_requires_review_and_rejects_manual_edits(tmp_path, monkeypatch):
    window = object.__new__(tool.WatchlistWindow)
    window.saved = tool.write_import(tmp_path, [tool.validate_row(_session(), "INFY-EQ", 100)])
    window.saved_bytes = window.saved.read_bytes()
    window.run = Mock()
    confirm = Mock(return_value=False)
    error = Mock()
    monkeypatch.setattr(tool.messagebox, "askyesno", confirm)
    monkeypatch.setattr(tool.messagebox, "showerror", error)
    monkeypatch.setattr(tool.simpledialog, "askstring", Mock(side_effect=AssertionError("unreviewed upload")))
    window.upload()
    confirm.assert_called_once()
    window.run.assert_not_called()
    window.saved.write_text("symbol,trigger_price\nBAD-EQ,1\n")
    window.upload()
    error.assert_called_once()
    assert confirm.call_count == 1
    window.run.assert_not_called()


def test_create_refreshes_every_row_and_writes_nothing_if_any_quote_fails(tmp_path, monkeypatch):
    window = object.__new__(tool.WatchlistWindow)
    window.session = _session()
    row = tool.validate_row(window.session, "INFY-EQ", 100)
    window.rows = {"INFY-EQ": row, "TCS-EQ": ("TCS-EQ", 200, 200, 0, "OK")}
    window.saved = None
    actions = []
    window.run = lambda action, done: actions.append(action)
    monkeypatch.setattr(tool.filedialog, "askdirectory", lambda **kwargs: str(tmp_path))
    validate = Mock(side_effect=[row, ValueError("quote unavailable")])
    monkeypatch.setattr(tool, "validate_row", validate)
    window.create()
    with pytest.raises(ValueError, match="quote unavailable"):
        actions[0]()
    assert validate.call_count == 2
    assert not list(tmp_path.glob("*.csv"))
