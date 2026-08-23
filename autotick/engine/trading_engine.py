# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Mode-neutral TradingEngine lifecycle and event loop for AutoTick.
"""

from __future__ import annotations

from contextlib import suppress
from queue import Empty, Queue

from autotick.engine.dispatcher import EventDispatcher
from autotick.models.event import Event
from autotick.providers.factory import ProviderBundle


class TradingEngine:
    """Own provider lifecycle and dispatch normalized events."""

    def __init__(
        self,
        providers: ProviderBundle,
        dispatcher: EventDispatcher,
        loop_sleep_s: float = 1.0,
    ) -> None:
        if loop_sleep_s <= 0:
            raise ValueError("loop_sleep_s must be greater than zero")

        self.providers = providers
        self.dispatcher = dispatcher
        self.loop_sleep_s = loop_sleep_s
        self._events: Queue[Event] = Queue()
        self._initialized = False
        self._running = False

    def initialize(self) -> None:
        """Connect providers once before engine start."""
        if self._initialized:
            return

        try:
            self.providers.market_data.connect()
            self.providers.account.connect()
        except Exception:
            with suppress(Exception):
                self.providers.account.disconnect()
            with suppress(Exception):
                self.providers.market_data.disconnect()
            raise

        self._initialized = True

    def start(self) -> None:
        """Initialize the engine and enable its event loop."""
        self.initialize()
        self._running = True

    def submit(self, event: Event) -> None:
        """Queue one normalized event for processing."""
        self._events.put(event)

    def run(self) -> None:
        """Process queued events until stop is requested."""
        if not self._running:
            raise RuntimeError("TradingEngine must be started before run")

        while self._running:
            try:
                event = self._events.get(timeout=self.loop_sleep_s)
            except Empty:
                continue
            self.dispatcher.dispatch(event)

    def stop(self) -> None:
        """Request event-loop stop."""
        self._running = False

    def shutdown(self) -> None:
        """Stop engine and disconnect initialized providers."""
        self.stop()
        if not self._initialized:
            return

        self.providers.account.disconnect()
        self.providers.market_data.disconnect()
        if self.providers.calendar_session is not None:
            self.providers.calendar_session.reset()
        self._initialized = False
