# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Normalized event registration and dispatch for AutoTick.
"""

from __future__ import annotations

from collections.abc import Callable

from autotick.models.event import Event, EventType

EventHandler = Callable[[Event], None]


class EventDispatcher:
    """Route normalized events to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = {}

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for one event type."""
        handlers = self._handlers.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)

    def unregister(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a registered handler."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event_type: EventType, data: object) -> Event:
        """Create a normalized event and dispatch it."""
        event = Event(event_type=event_type, data=data)
        self.dispatch(event)
        return event

    def dispatch(self, event: Event) -> None:
        """Dispatch an event to matching handlers."""
        for handler in tuple(self._handlers.get(event.event_type, [])):
            handler(event)
