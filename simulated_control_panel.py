# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 02:00:00 2026

@author: ashwe

Desktop control panel for manually changing simulated account and market data.
"""

from __future__ import annotations

import csv
import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from math import isfinite
from pathlib import Path
from queue import Empty, Queue
from threading import Event, RLock, Thread
from tkinter import filedialog, ttk
from typing import Any
from zoneinfo import ZoneInfo

from autotick.models.account import Account
from autotick.models.market import MarketBar, MarketTick
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle, ProviderFactory

DEFAULT_CAPITAL = 100_000.0
DEFAULT_EXCHANGE = "NSE"
DEFAULT_SYMBOL = "INFY-EQ"
DEFAULT_LTP = 100.0
DEFAULT_VOLUME = 0
ACCOUNT_REFRESH_MS = 500
TIMEZONE = ZoneInfo("Asia/Kolkata")
INTERVALS = ("1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d")


class EditableSimulatedAccountProvider(SimulatedAccountProvider):
    """Thread-safe simulated account with manual fund controls."""

    def __init__(
        self,
        session: SimulatedSession,
        configured_capital: float = 0.0,
    ) -> None:
        super().__init__(session, configured_capital)
        self._initial_capital = float(configured_capital)
        self._lock = RLock()

    def set_balance(self, value: float) -> float:
        """Set balance, margin, and buying power to the same value."""
        amount = self._valid_amount(value)
        with self._lock:
            self._account = replace(
                self._account,
                balance=amount,
                available_margin=amount,
                buying_power=amount,
            )
        return amount

    def add_funds(self, value: float) -> float:
        """Add funds and return the new balance."""
        amount = self._valid_amount(value)
        with self._lock:
            return self.set_balance(float(self._account.balance or 0.0) + amount)

    def remove_funds(self, value: float) -> float:
        """Remove funds without allowing a negative balance."""
        amount = self._valid_amount(value)
        with self._lock:
            balance = float(self._account.balance or 0.0)
            if amount > balance:
                raise ValueError("Remove amount cannot exceed current balance")
            return self.set_balance(balance - amount)

    def reset_balance(self) -> float:
        """Restore the opening configured capital."""
        return self.set_balance(self._initial_capital)

    def get_balance(self) -> float:
        with self._lock:
            return super().get_balance()

    def get_margin(self) -> float:
        with self._lock:
            return super().get_margin()

    def get_buying_power(self) -> float:
        with self._lock:
            return super().get_buying_power()

    def get_profile(self) -> Account:
        with self._lock:
            return replace(super().get_profile())

    @staticmethod
    def _valid_amount(value: float) -> float:
        if isinstance(value, bool):
            raise ValueError("Amount must be a number")
        amount = float(value)
        if not isfinite(amount) or amount < 0:
            raise ValueError("Amount must be zero or greater")
        return amount


class ControlledSimulatedMarketDataProvider(SimulatedMarketDataProvider):
    """Thread-safe simulated market data used by both GUI and strategy."""

    def __init__(
        self,
        session: SimulatedSession,
        exchange: str = "NSE",
    ) -> None:
        self._lock = RLock()
        super().__init__(session, exchange)

    def set_tick(self, tick: MarketTick) -> None:
        with self._lock:
            super().set_tick(replace(tick))

    def set_bars(self, symbol: str, interval: str, bars: list[MarketBar]) -> None:
        with self._lock:
            super().set_bars(symbol, interval, [replace(bar) for bar in bars])

    def get_tick(self, symbol: str) -> MarketTick | None:
        with self._lock:
            tick = super().get_tick(symbol)
            return replace(tick) if tick is not None else None

    def get_bars(
        self,
        symbol: str,
        interval: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[MarketBar]:
        with self._lock:
            return [
                replace(bar)
                for bar in super().get_bars(symbol, interval, start_date, end_date)
            ]

    def get_ticks(self) -> list[MarketTick]:
        """Return stored ticks for the UI table."""
        with self._lock:
            return [replace(self._ticks[key]) for key in sorted(self._ticks)]

    def get_stored_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        """Return all stored bars without applying a date filter."""
        with self._lock:
            bars = self._bars.get((symbol.upper(), interval.lower()), [])
            return [replace(bar) for bar in bars]

    def clear_bars(self, symbol: str, interval: str) -> None:
        """Remove one stored symbol and interval."""
        with self._lock:
            self._bars.pop((symbol.upper(), interval.lower()), None)


@dataclass(slots=True)
class SimulationRuntime:
    """Shared provider objects used by the UI and strategy."""

    session: SimulatedSession
    account: EditableSimulatedAccountProvider
    market_data: ControlledSimulatedMarketDataProvider
    execution: SimulatedExecutionProvider
    providers: ProviderBundle


@dataclass(slots=True)
class BrokerInitialData:
    """Real-broker values copied into simulated providers at startup."""

    balance: float | None
    tick: MarketTick | None
    bars: list[MarketBar]
    errors: list[str]


class SimulationController:
    """Validate UI input and update normalized simulated provider data."""

    def __init__(
        self,
        account: EditableSimulatedAccountProvider,
        market_data: ControlledSimulatedMarketDataProvider,
        source_broker: str | None = None,
        source_config: dict[str, Any] | None = None,
    ) -> None:
        self.account = account
        self.market_data = market_data
        self._baseline_ticks: dict[str, MarketTick] = {}
        self.source_broker = str(source_broker or "").strip().lower()
        self._source_config = source_config
        self._broker_bundle: ProviderBundle | None = None
        self._credentials_file: str | None = None
        self._lock = RLock()

    def set_tick(
        self,
        symbol: str,
        ltp: float,
        volume: int,
        update_baseline: bool = True,
    ) -> MarketTick:
        """Create and store one normalized tick."""
        name = self._valid_symbol(symbol)
        price = self._valid_price(ltp)
        current_volume = self._valid_volume(volume)
        tick = MarketTick(
            symbol=name,
            exchange=self.market_data.exchange,
            ltp=price,
            volume=current_volume,
            timestamp=datetime.now(TIMEZONE),
        )
        with self._lock:
            self.market_data.set_tick(tick)
            if update_baseline or name not in self._baseline_ticks:
                self._baseline_ticks[name] = replace(tick)
        return tick

    def ensure_tick(self, symbol: str) -> MarketTick:
        """Return a stored tick or create the UI default tick."""
        name = self._valid_symbol(symbol)
        tick = self.market_data.get_tick(name)
        if tick is None:
            return self.set_tick(name, DEFAULT_LTP, DEFAULT_VOLUME)
        with self._lock:
            self._baseline_ticks.setdefault(name, replace(tick))
        return tick

    def adjust_tick(
        self,
        symbol: str,
        amount: float,
        mode: str,
        increase: bool,
    ) -> MarketTick:
        """Move the current LTP by an absolute value or percentage."""
        change = self._valid_positive(amount, "Adjustment")
        tick = self.ensure_tick(symbol)
        price = float(tick.ltp or 0.0)
        normalized_mode = mode.strip().lower()
        if normalized_mode == "percentage":
            if not increase and change >= 100:
                raise ValueError("Percentage decrease must be below 100")
            multiplier = 1 + change / 100 if increase else 1 - change / 100
            price *= multiplier
        elif normalized_mode == "value":
            price = price + change if increase else price - change
        else:
            raise ValueError("Adjustment mode must be Value or Percentage")
        return self.set_tick(
            tick.symbol,
            price,
            int(tick.volume or 0),
            update_baseline=False,
        )

    def reset_tick(self, symbol: str) -> MarketTick:
        """Restore one tick to its initial or last imported baseline."""
        name = self._valid_symbol(symbol)
        with self._lock:
            baseline = self._baseline_ticks.get(name)
        if baseline is None:
            return self.set_tick(name, DEFAULT_LTP, DEFAULT_VOLUME)
        return self.set_tick(
            name,
            float(baseline.ltp or DEFAULT_LTP),
            int(baseline.volume or 0),
            update_baseline=False,
        )

    def load_csv(self, path: str) -> dict[tuple[str, str], int]:
        """Load normalized OHLCV bars and return counts by symbol/interval."""
        csv_path = Path(path).expanduser().resolve()
        if not csv_path.is_file():
            raise ValueError("CSV file does not exist")

        required = {
            "symbol", "exchange", "interval", "timestamp",
            "open", "high", "low", "close", "volume",
        }
        grouped: dict[tuple[str, str], list[MarketBar]] = {}
        with csv_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
            for row_number, row in enumerate(reader, start=2):
                try:
                    symbol = self._valid_symbol(row["symbol"])
                    exchange = row["exchange"].strip().upper()
                    interval = self._valid_interval(row["interval"])
                    if exchange != self.market_data.exchange:
                        raise ValueError(
                            f"Expected exchange {self.market_data.exchange}, got {exchange}"
                        )
                    timestamp = datetime.fromisoformat(row["timestamp"].strip())
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=TIMEZONE)
                    else:
                        timestamp = timestamp.astimezone(TIMEZONE)
                    bar = MarketBar(
                        symbol=symbol,
                        exchange=exchange,
                        open=self._valid_price(row["open"]),
                        high=self._valid_price(row["high"]),
                        low=self._valid_price(row["low"]),
                        close=self._valid_price(row["close"]),
                        volume=self._valid_volume(row["volume"]),
                        timestamp=timestamp,
                    )
                    self._validate_ohlc(bar)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"CSV row {row_number}: {exc}") from exc
                grouped.setdefault((symbol, interval), []).append(bar)

        if not grouped:
            raise ValueError("CSV file has no data rows")
        counts: dict[tuple[str, str], int] = {}
        for key, bars in grouped.items():
            bars.sort(key=lambda item: item.timestamp)
            self.market_data.set_bars(key[0], key[1], bars)
            counts[key] = len(bars)
        return counts

    def clear_bars(self, symbol: str, interval: str) -> None:
        self.market_data.clear_bars(
            self._valid_symbol(symbol),
            self._valid_interval(interval),
        )

    def import_broker_tick(self, credentials_file: str, symbol: str) -> MarketTick:
        """Copy one real-broker tick snapshot into simulated market data."""
        tick = self.check_broker_connection(credentials_file, symbol)
        return self.set_tick(tick.symbol, float(tick.ltp), int(tick.volume or 0))

    def check_broker_connection(
        self,
        credentials_file: str,
        symbol: str,
    ) -> MarketTick:
        """Verify login and market-data access by fetching one current tick."""
        with self._lock:
            source = self._broker_source(credentials_file)
            tick = source.market_data.get_tick(self._valid_symbol(symbol))
            if tick is None or tick.ltp is None:
                raise RuntimeError(f"{self.source_broker} returned no tick")
            return tick

    def import_broker_bars(
        self,
        credentials_file: str,
        symbol: str,
        interval: str,
    ) -> list[MarketBar]:
        """Copy one real-broker historical snapshot into simulated market data."""
        with self._lock:
            name = self._valid_symbol(symbol)
            period = self._valid_interval(interval)
            source = self._broker_source(credentials_file)
            bars = source.market_data.get_bars(name, period)
            if not bars:
                raise RuntimeError(f"{self.source_broker} returned no bars")
            self.market_data.set_bars(name, period, bars)
            return bars

    def import_broker_initial_data(
        self,
        credentials_file: str,
        symbol: str,
        interval: str,
    ) -> BrokerInitialData:
        """Copy balance, current tick, and bars when the GUI starts."""
        with self._lock:
            name = self._valid_symbol(symbol)
            period = self._valid_interval(interval)
            source = self._broker_source(credentials_file)
            errors: list[str] = []
            balance: float | None = None
            tick: MarketTick | None = None
            bars: list[MarketBar] = []

            try:
                fetched_balance = float(source.account.get_balance())
                self.account.set_balance(fetched_balance)
                balance = fetched_balance
            except Exception as exc:
                errors.append(f"balance: {exc}")

            try:
                fetched_tick = source.market_data.get_tick(name)
                if fetched_tick is None or fetched_tick.ltp is None:
                    raise RuntimeError("no tick returned")
                tick = self.set_tick(
                    fetched_tick.symbol,
                    float(fetched_tick.ltp),
                    int(fetched_tick.volume or 0),
                )
            except Exception as exc:
                errors.append(f"tick: {exc}")

            try:
                bars = source.market_data.get_bars(name, period)
                if not bars:
                    raise RuntimeError("no bars returned")
                self.market_data.set_bars(name, period, bars)
            except Exception as exc:
                errors.append(f"bars: {exc}")
                bars = []

            if balance is None and tick is None and not bars:
                raise RuntimeError("; ".join(errors))
            return BrokerInitialData(balance, tick, bars, errors)

    def close(self) -> None:
        """Close the optional real-broker snapshot session."""
        with self._lock:
            if self._broker_bundle is not None:
                with suppress(Exception):
                    self._broker_bundle.market_data.disconnect()
                with suppress(Exception):
                    self._broker_bundle.account.disconnect()
            if self.source_broker:
                with suppress(Exception):
                    ProviderFactory.close_broker_session(self.source_broker)
            self._broker_bundle = None
            self._credentials_file = None

    def _broker_source(self, credentials_file: str) -> ProviderBundle:
        if not self.source_broker or self.source_broker == "simulated":
            raise ValueError("Real broker source is not configured")
        if self._source_config is None:
            raise ValueError("Real broker configuration is not available")
        path = str(Path(credentials_file).expanduser().resolve())
        if not Path(path).is_file():
            raise ValueError(f"{self.source_broker} credentials file does not exist")
        if self._broker_bundle is not None and path == self._credentials_file:
            return self._broker_bundle

        self.close()
        config = deepcopy(self._source_config)
        config["broker"] = self.source_broker
        broker_config = config.setdefault("broker_config", {}).setdefault(
            self.source_broker,
            {},
        )
        broker_config["credentials_file"] = path
        self._broker_bundle = ProviderFactory.create_bundle("live", config)
        self._broker_bundle.market_data.connect()
        self._broker_bundle.account.connect()
        self._credentials_file = path
        return self._broker_bundle

    @staticmethod
    def _valid_symbol(value: str) -> str:
        symbol = str(value).strip().upper()
        if not symbol:
            raise ValueError("Symbol is required")
        return symbol

    @staticmethod
    def _valid_price(value: object) -> float:
        price = float(value)
        if not isfinite(price) or price <= 0:
            raise ValueError("Price must be greater than zero")
        return price

    @staticmethod
    def _valid_volume(value: object) -> int:
        if isinstance(value, bool):
            raise ValueError("Volume must be a whole number")
        volume = int(value)
        if volume < 0 or float(value) != volume:
            raise ValueError("Volume must be a non-negative whole number")
        return volume

    @staticmethod
    def _valid_positive(value: object, name: str) -> float:
        number = float(value)
        if not isfinite(number) or number <= 0:
            raise ValueError(f"{name} must be greater than zero")
        return number

    @staticmethod
    def _valid_interval(value: str) -> str:
        interval = str(value).strip().lower()
        if interval not in INTERVALS:
            raise ValueError(f"Interval must be one of: {', '.join(INTERVALS)}")
        return interval

    @staticmethod
    def _validate_ohlc(bar: MarketBar) -> None:
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            raise ValueError("OHLC values must stay between low and high")


class SimulatedControlPanel:
    """One-window Tkinter UI for the shared simulation providers."""

    def __init__(
        self,
        root: tk.Tk,
        runtime: SimulationRuntime,
        controller: SimulationController,
        stop_event: Event,
        initial_symbol: str = DEFAULT_SYMBOL,
        initial_interval: str = "1m",
        credentials_file: str | None = None,
        source_broker: str | None = None,
        broker_auto_fetch: bool = False,
    ) -> None:
        self.root = root
        self.runtime = runtime
        self.controller = controller
        self.stop_event = stop_event
        self._results: Queue[tuple[str, str, object, Callable[[object], None] | None]] = Queue()
        self._closing = False
        self._initial_data_ready = False
        self._strategy_started = False
        self._strategy_runner: Callable[[ProviderBundle, Event], None] | None = None
        self.source_broker = str(source_broker or "").strip().lower()
        self.broker_label = (
            "AngelOne" if self.source_broker == "angelone"
            else self.source_broker.title() if self.source_broker
            else "Broker"
        )
        self.broker_auto_fetch = broker_auto_fetch

        self.balance_var = tk.StringVar()
        self.funds_var = tk.StringVar(value="1000.00")
        self.symbol_var = tk.StringVar(value=initial_symbol)
        self.ltp_var = tk.StringVar(value=f"{DEFAULT_LTP:.2f}")
        self.volume_var = tk.StringVar(value=str(DEFAULT_VOLUME))
        self.adjustment_var = tk.StringVar(value="1.00")
        self.adjustment_mode_var = tk.StringVar(value="Value")
        self.interval_var = tk.StringVar(
            value=initial_interval if initial_interval in INTERVALS else "1m"
        )
        self.csv_path_var = tk.StringVar()
        default_credentials = (
            Path(credentials_file).expanduser().resolve()
            if credentials_file
            else None
        )
        self.credentials_var = tk.StringVar(
            value=(
                str(default_credentials)
                if default_credentials and default_credentials.is_file()
                else ""
            )
        )
        self.bars_var = tk.StringVar(value="No bars loaded")
        self.status_var = tk.StringVar(value="Ready")
        self.strategy_var = tk.StringVar(value="Strategy: not configured")
        self.broker_status_var = tk.StringVar(value=f"● {self.broker_label}: not checked")

        self._build()
        self._refresh_account()
        self._refresh_ticks()
        self._refresh_bars()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_results)
        self.root.after(ACCOUNT_REFRESH_MS, self._auto_refresh_account)
        if self.broker_auto_fetch:
            self.root.after(250, self._auto_fetch_broker)
        else:
            self._set_broker_status(
                "unchecked",
                f"{self.broker_label}: automatic fetch disabled",
            )
            self.root.after(0, self._finish_initial_data)

    def _build(self) -> None:
        self.root.title("AutoTick Simulated Broker Control Panel")
        self.root.geometry("980x720")
        self.root.minsize(820, 650)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        account = ttk.LabelFrame(self.root, text="Account", padding=10)
        account.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        account.columnconfigure(7, weight=1)
        ttk.Label(account, text="Balance / Margin / Buying Power:").grid(row=0, column=0, padx=4)
        ttk.Label(account, textvariable=self.balance_var).grid(row=0, column=1, padx=8)
        ttk.Label(account, text="Amount:").grid(row=0, column=2, padx=4)
        ttk.Entry(account, textvariable=self.funds_var, width=14).grid(row=0, column=3, padx=4)
        ttk.Button(account, text="Set", command=lambda: self._funds("set")).grid(row=0, column=4, padx=3)
        ttk.Button(account, text="Add", command=lambda: self._funds("add")).grid(row=0, column=5, padx=3)
        ttk.Button(account, text="Remove", command=lambda: self._funds("remove")).grid(row=0, column=6, padx=3)
        ttk.Button(account, text="Reset", command=lambda: self._funds("reset")).grid(row=0, column=7, padx=3, sticky="w")

        tick = ttk.LabelFrame(self.root, text="Current Tick", padding=10)
        tick.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        for column in range(12):
            tick.columnconfigure(column, weight=1 if column in {1, 3, 5, 7} else 0)
        ttk.Label(tick, text="Symbol:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(tick, textvariable=self.symbol_var, width=16).grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        ttk.Label(tick, text="LTP:").grid(row=0, column=2, padx=3, pady=3)
        ttk.Entry(tick, textvariable=self.ltp_var, width=12).grid(row=0, column=3, padx=3, pady=3, sticky="ew")
        ttk.Label(tick, text="Volume:").grid(row=0, column=4, padx=3, pady=3)
        ttk.Entry(tick, textvariable=self.volume_var, width=12).grid(row=0, column=5, padx=3, pady=3, sticky="ew")
        ttk.Button(tick, text="Apply", command=self._apply_tick).grid(row=0, column=6, padx=3)
        ttk.Button(tick, text="Reset", command=self._reset_tick).grid(row=0, column=7, padx=3, sticky="w")

        ttk.Label(tick, text="Adjustment:").grid(row=1, column=0, padx=3, pady=3)
        ttk.Entry(tick, textvariable=self.adjustment_var, width=12).grid(row=1, column=1, padx=3, pady=3, sticky="ew")
        ttk.Combobox(
            tick,
            textvariable=self.adjustment_mode_var,
            values=("Value", "Percentage"),
            state="readonly",
            width=12,
        ).grid(row=1, column=2, columnspan=2, padx=3, pady=3, sticky="ew")
        ttk.Button(tick, text="Increase", command=lambda: self._adjust_tick(True)).grid(row=1, column=4, padx=3)
        ttk.Button(tick, text="Decrease", command=lambda: self._adjust_tick(False)).grid(row=1, column=5, padx=3)
        ttk.Button(
            tick,
            text=f"Import {self.broker_label} Tick",
            command=self._import_tick,
        ).grid(row=1, column=6, columnspan=2, padx=3, sticky="w")

        table_frame = ttk.LabelFrame(self.root, text="Simulated Stocks", padding=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.tick_table = ttk.Treeview(
            table_frame,
            columns=("symbol", "exchange", "ltp", "volume", "timestamp"),
            show="headings",
            height=8,
        )
        for name, title, width in (
            ("symbol", "Symbol", 150),
            ("exchange", "Exchange", 80),
            ("ltp", "LTP", 100),
            ("volume", "Volume", 100),
            ("timestamp", "Updated", 230),
        ):
            self.tick_table.heading(name, text=title)
            self.tick_table.column(name, width=width, anchor="center")
        self.tick_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tick_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tick_table.configure(yscrollcommand=scrollbar.set)
        self.tick_table.bind("<<TreeviewSelect>>", self._select_tick)

        bars = ttk.LabelFrame(self.root, text="Historical Bars", padding=10)
        bars.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        bars.columnconfigure(1, weight=1)
        ttk.Label(bars, text="CSV:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(bars, textvariable=self.csv_path_var).grid(row=0, column=1, columnspan=4, padx=3, pady=3, sticky="ew")
        ttk.Button(bars, text="Browse", command=self._browse_csv).grid(row=0, column=5, padx=3)
        ttk.Button(bars, text="Load CSV", command=self._load_csv).grid(row=0, column=6, padx=3)
        ttk.Label(bars, text="Interval:").grid(row=1, column=0, padx=3, pady=3)
        interval_box = ttk.Combobox(
            bars,
            textvariable=self.interval_var,
            values=INTERVALS,
            state="readonly",
            width=10,
        )
        interval_box.grid(row=1, column=1, padx=3, pady=3, sticky="w")
        interval_box.bind("<<ComboboxSelected>>", lambda _: self._refresh_bars())
        ttk.Button(
            bars,
            text=f"Import {self.broker_label} Bars",
            command=self._import_bars,
        ).grid(row=1, column=2, padx=3)
        ttk.Button(bars, text="Clear Selected Bars", command=self._clear_bars).grid(row=1, column=3, padx=3)
        ttk.Label(bars, textvariable=self.bars_var).grid(row=1, column=4, columnspan=3, padx=8, sticky="w")

        source = ttk.LabelFrame(
            self.root,
            text=f"Optional {self.broker_label} Snapshot Source",
            padding=10,
        )
        source.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text="Credentials:").grid(row=0, column=0, padx=3)
        ttk.Entry(source, textvariable=self.credentials_var).grid(row=0, column=1, padx=3, sticky="ew")
        ttk.Button(source, text="Browse", command=self._browse_credentials).grid(row=0, column=2, padx=3)
        self.broker_status_label = tk.Label(
            source,
            textvariable=self.broker_status_var,
            foreground="#6b7280",
        )
        self.broker_status_label.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=3,
            pady=(8, 0),
            sticky="w",
        )
        ttk.Button(source, text="Check Connection", command=self._check_broker).grid(
            row=1,
            column=2,
            padx=3,
            pady=(8, 0),
        )
        self.credentials_var.trace_add("write", self._credentials_changed)

        status = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        status.grid(row=5, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.strategy_var).grid(row=0, column=1, sticky="e")

    def start_strategy(
        self,
        runner: Callable[[ProviderBundle, Event], None],
    ) -> None:
        """Start the supplied strategy runner with the shared provider bundle."""
        self._strategy_runner = runner
        if not self._initial_data_ready:
            self.strategy_var.set("Strategy: waiting for initial data")
            return
        self._launch_strategy()

    def _launch_strategy(self) -> None:
        if self._strategy_started or self._strategy_runner is None:
            return
        self._strategy_started = True
        self.strategy_var.set("Strategy: running")
        runner = self._strategy_runner

        def work() -> object:
            runner(self.runtime.providers, self.stop_event)
            return None

        def done(_: object) -> None:
            self.strategy_var.set("Strategy: stopped")

        self._background("Strategy", work, done, strategy=True)

    def _funds(self, operation: str) -> None:
        try:
            if operation == "reset":
                self.runtime.account.reset_balance()
            else:
                value = float(self.funds_var.get())
                if operation == "set":
                    self.runtime.account.set_balance(value)
                elif operation == "add":
                    self.runtime.account.add_funds(value)
                else:
                    self.runtime.account.remove_funds(value)
            self._refresh_account()
            self._status("Account updated")
        except (TypeError, ValueError) as exc:
            self._status(str(exc), error=True)

    def _apply_tick(self) -> None:
        try:
            tick = self.controller.set_tick(
                self.symbol_var.get(),
                float(self.ltp_var.get()),
                int(self.volume_var.get()),
            )
            self._show_tick(tick)
            self._status(f"Tick updated: {tick.symbol}")
        except (TypeError, ValueError) as exc:
            self._status(str(exc), error=True)

    def _adjust_tick(self, increase: bool) -> None:
        try:
            tick = self.controller.adjust_tick(
                self.symbol_var.get(),
                float(self.adjustment_var.get()),
                self.adjustment_mode_var.get(),
                increase,
            )
            self._show_tick(tick)
            self._status(f"Tick updated: {tick.symbol}")
        except (TypeError, ValueError) as exc:
            self._status(str(exc), error=True)

    def _reset_tick(self) -> None:
        try:
            tick = self.controller.reset_tick(self.symbol_var.get())
            self._show_tick(tick)
            self._status(f"Tick reset: {tick.symbol}")
        except (TypeError, ValueError) as exc:
            self._status(str(exc), error=True)

    def _show_tick(self, tick: MarketTick) -> None:
        self.symbol_var.set(tick.symbol)
        self.ltp_var.set(f"{float(tick.ltp or 0.0):.2f}")
        self.volume_var.set(str(int(tick.volume or 0)))
        self._refresh_ticks()

    def _refresh_account(self) -> None:
        self.balance_var.set(f"₹ {self.runtime.account.get_balance():,.2f}")

    def _auto_refresh_account(self) -> None:
        """Keep the displayed funds synchronized with simulated fills."""
        if self._closing:
            return
        self._refresh_account()
        self.root.after(ACCOUNT_REFRESH_MS, self._auto_refresh_account)

    def _refresh_ticks(self) -> None:
        children = self.tick_table.get_children()
        if children:
            self.tick_table.delete(*children)
        for tick in self.runtime.market_data.get_ticks():
            timestamp = tick.timestamp.isoformat(sep=" ", timespec="seconds") if tick.timestamp else ""
            self.tick_table.insert(
                "",
                "end",
                iid=tick.symbol,
                values=(
                    tick.symbol,
                    tick.exchange,
                    f"{float(tick.ltp or 0.0):.2f}",
                    int(tick.volume or 0),
                    timestamp,
                ),
            )

    def _select_tick(self, _: object) -> None:
        selected = self.tick_table.selection()
        if not selected:
            return
        tick = self.runtime.market_data.get_tick(selected[0])
        if tick is not None:
            self.symbol_var.set(tick.symbol)
            self.ltp_var.set(f"{float(tick.ltp or 0.0):.2f}")
            self.volume_var.set(str(int(tick.volume or 0)))
            self._refresh_bars()

    def _refresh_bars(self) -> None:
        try:
            symbol = self.controller._valid_symbol(self.symbol_var.get())
            interval = self.controller._valid_interval(self.interval_var.get())
            bars = self.runtime.market_data.get_stored_bars(symbol, interval)
            if bars:
                latest = bars[-1]
                self.bars_var.set(
                    f"{symbol} {interval}: {len(bars)} bars, latest close {latest.close:.2f}"
                )
            else:
                self.bars_var.set(f"{symbol} {interval}: no bars")
        except ValueError as exc:
            self.bars_var.set(str(exc))

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select OHLCV CSV",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if path:
            self.csv_path_var.set(path)

    def _browse_credentials(self) -> None:
        path = filedialog.askopenfilename(
            title=f"Select {self.broker_label} credentials file",
            filetypes=(("Environment files", "*.env"), ("All files", "*.*")),
        )
        if path:
            self.credentials_var.set(path)
            if self.broker_auto_fetch:
                self.root.after(0, self._auto_fetch_broker)

    def _credentials_changed(self, *_: object) -> None:
        self._set_broker_status("unchecked", f"{self.broker_label}: not checked")

    def _auto_fetch_broker(self) -> None:
        credentials = self.credentials_var.get()
        if not credentials or not Path(credentials).expanduser().is_file():
            self._set_broker_status(
                "unchecked",
                f"{self.broker_label}: credentials not found — using defaults",
            )
            self._finish_initial_data()
            return

        symbol = self.symbol_var.get()
        interval = self.interval_var.get()
        self._set_broker_status(
            "checking",
            f"{self.broker_label}: loading balance, tick, and bars...",
        )

        def done(value: object) -> None:
            data = value if isinstance(value, BrokerInitialData) else None
            if data is None:
                self._finish_initial_data()
                return
            self._refresh_account()
            if data.tick is not None:
                self._show_tick(data.tick)
            self._refresh_bars()
            if data.errors:
                self._set_broker_status(
                    "partial",
                    f"{self.broker_label}: connected — {len(data.errors)} startup fetch failed",
                )
            else:
                self._set_broker_status(
                    "connected",
                    f"{self.broker_label}: connected — balance, tick, and bars fetched",
                )
            self._finish_initial_data()

        def failed(_: object) -> None:
            self._finish_initial_data()

        self._background(
            f"{self.broker_label} startup import",
            lambda: self.controller.import_broker_initial_data(
                credentials,
                symbol,
                interval,
            ),
            done,
            on_error=failed,
        )

    def _finish_initial_data(self) -> None:
        self._initial_data_ready = True
        self._launch_strategy()

    def _check_broker(self) -> None:
        credentials = self.credentials_var.get()
        symbol = self.symbol_var.get()
        self._set_broker_status("checking", f"{self.broker_label}: checking data...")

        def done(value: object) -> None:
            tick = value if isinstance(value, MarketTick) else None
            detail = f"{tick.symbol} LTP {float(tick.ltp):.2f}" if tick else "data fetched"
            self._set_broker_status(
                "connected",
                f"{self.broker_label}: connected — {detail}",
            )

        self._background(
            f"{self.broker_label} connection check",
            lambda: self.controller.check_broker_connection(credentials, symbol),
            done,
        )

    def _load_csv(self) -> None:
        path = self.csv_path_var.get()

        def done(value: object) -> None:
            counts = value if isinstance(value, dict) else {}
            total = sum(counts.values())
            self._refresh_bars()
            self._status(f"Loaded {total} bars across {len(counts)} symbol/interval groups")

        self._background("CSV import", lambda: self.controller.load_csv(path), done)

    def _import_tick(self) -> None:
        credentials = self.credentials_var.get()
        symbol = self.symbol_var.get()
        self._set_broker_status("checking", f"{self.broker_label}: fetching tick...")

        def done(value: object) -> None:
            if isinstance(value, MarketTick):
                self._show_tick(value)
                self._set_broker_status(
                    "connected",
                    f"{self.broker_label}: connected — {value.symbol} tick fetched",
                )

        self._background(
            f"{self.broker_label} tick import",
            lambda: self.controller.import_broker_tick(credentials, symbol),
            done,
        )

    def _import_bars(self) -> None:
        credentials = self.credentials_var.get()
        symbol = self.symbol_var.get()
        interval = self.interval_var.get()
        self._set_broker_status("checking", f"{self.broker_label}: fetching bars...")

        def done(_: object) -> None:
            self._refresh_bars()
            self._set_broker_status(
                "connected",
                f"{self.broker_label}: connected — {symbol.upper()} bars fetched",
            )

        self._background(
            f"{self.broker_label} bars import",
            lambda: self.controller.import_broker_bars(credentials, symbol, interval),
            done,
        )

    def _clear_bars(self) -> None:
        try:
            self.controller.clear_bars(self.symbol_var.get(), self.interval_var.get())
            self._refresh_bars()
            self._status("Selected bars cleared")
        except ValueError as exc:
            self._status(str(exc), error=True)

    def _background(
        self,
        label: str,
        action: Callable[[], object],
        on_success: Callable[[object], None] | None = None,
        on_error: Callable[[object], None] | None = None,
        strategy: bool = False,
    ) -> None:
        self._status(f"{label} running...")

        def work() -> None:
            try:
                result = action()
            except Exception as exc:
                self._results.put(
                    ("strategy_error" if strategy else "error", label, exc, on_error)
                )
            else:
                self._results.put(("ok", label, result, on_success))

        Thread(target=work, name=label, daemon=True).start()

    def _poll_results(self) -> None:
        if self._closing:
            return
        while True:
            try:
                state, label, value, callback = self._results.get_nowait()
            except Empty:
                break
            if state == "ok":
                if callback is not None:
                    callback(value)
                if label != "Strategy":
                    self._status(f"{label} completed")
            else:
                if callback is not None:
                    callback(value)
                self._status(f"{label}: {value}", error=True)
                if label.startswith(self.broker_label):
                    self._set_broker_status(
                        "failed",
                        f"{self.broker_label}: data fetch failed",
                    )
                if state == "strategy_error":
                    self.strategy_var.set("Strategy: failed")
        self.root.after(100, self._poll_results)

    def _set_broker_status(self, state: str, text: str) -> None:
        colors = {
            "unchecked": "#6b7280",
            "checking": "#d97706",
            "partial": "#d97706",
            "connected": "#15803d",
            "failed": "#b91c1c",
        }
        self.broker_status_var.set(f"● {text}")
        self.broker_status_label.configure(foreground=colors[state])

    def _status(self, text: str, error: bool = False) -> None:
        self.status_var.set(("ERROR: " if error else "") + text)

    def close(self) -> None:
        """Stop the runner and close simulated and optional broker sessions."""
        if self._closing:
            return
        self._closing = True
        self.stop_event.set()
        with suppress(Exception):
            self.controller.close()
        with suppress(Exception):
            self.runtime.market_data.disconnect()
        with suppress(Exception):
            self.runtime.account.disconnect()
        with suppress(Exception):
            self.runtime.session.logout()
        self.root.destroy()


def create_simulation_runtime(
    configured_capital: float = DEFAULT_CAPITAL,
    exchange: str = DEFAULT_EXCHANGE,
) -> SimulationRuntime:
    """Create one shared provider set for the GUI and strategy runner."""
    session = SimulatedSession()
    account = EditableSimulatedAccountProvider(session, configured_capital)
    market_data = ControlledSimulatedMarketDataProvider(session, exchange)
    execution = SimulatedExecutionProvider(session)
    providers = ProviderBundle(market_data, account, execution)
    return SimulationRuntime(session, account, market_data, execution, providers)


def run_control_panel(
    strategy_runner: Callable[[ProviderBundle, Event], None] | None = None,
    configured_capital: float = DEFAULT_CAPITAL,
    exchange: str = DEFAULT_EXCHANGE,
    initial_symbol: str = DEFAULT_SYMBOL,
    initial_interval: str = "1m",
    credentials_file: str | None = None,
    source_broker: str | None = None,
    source_config: dict[str, Any] | None = None,
    broker_auto_fetch: bool = False,
) -> None:
    """Run the GUI and optional strategy runner in the same process."""
    runtime = create_simulation_runtime(configured_capital, exchange)
    runtime.market_data.connect()
    runtime.account.connect()
    controller = SimulationController(
        runtime.account,
        runtime.market_data,
        source_broker,
        source_config,
    )
    controller.ensure_tick(initial_symbol)
    stop_event = Event()
    root = tk.Tk()
    panel = SimulatedControlPanel(
        root,
        runtime,
        controller,
        stop_event,
        initial_symbol,
        initial_interval,
        credentials_file,
        source_broker,
        broker_auto_fetch,
    )
    if strategy_runner is not None:
        panel.start_strategy(strategy_runner)
    try:
        root.mainloop()
    finally:
        if not panel._closing:
            panel.close()


def main() -> None:
    run_control_panel()


if __name__ == "__main__":
    main()
