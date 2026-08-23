# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:50:13 2026

@author: ashwe
"""

from __future__ import annotations

"""Centralized logging utilities for AutoTick.

Provides:
- Console + rotating file handlers
- Configurable log level
- Consistent log format
- Reusable get_logger()
- Reusable log_call decorator
"""

import pendulum as pdlm
import logging
import time
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, TypeVar, cast


DEFAULT_LOG_DIR = Path("logs")
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

F = TypeVar("F", bound=Callable[..., Any])


def _create_log_file_name() -> Path:
    """Create a timestamped log filename using Asia/Kolkata time."""
    date_time = pdlm.now(DEFAULT_TIMEZONE).strftime("%Y%m%d_%H%M%S")

    return DEFAULT_LOG_DIR / f"logger_file_{date_time}.log"


def _resolve_log_level(level: str | int) -> int:
    """Convert a string/int log level into a logging level constant."""
    if isinstance(level, int):
        return level

    resolved = getattr(logging, level.upper(), None)
    if not isinstance(resolved, int):
        raise ValueError(f"Invalid log level: {level}")

    return resolved


def configure_logging(
    *,
    level: str | int = DEFAULT_LOG_LEVEL,
    log_file: str | Path | None = None,
    console: bool = True,
    file: bool = True,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Configure centralized application logging.

    Call this once during application startup.
    """
    resolved_level = _resolve_log_level(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    # Prevent duplicate output if configuration is repeated.
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(resolved_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if file:
        log_path = Path(log_file) if log_file else _create_log_file_name()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for a module."""
    return logging.getLogger(name)


def log_call(
    *,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[F], F]:
    """Log call entry, optional args/result, failures, and elapsed time.

    Avoid log_args/log_result for functions carrying passwords, tokens,
    account identifiers, or other sensitive values.
    """

    def decorator(func: F) -> F:
        func_logger = logging.getLogger(func.__module__)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()

            try:
                if log_args:
                    func_logger.debug(
                        "%s called args=%r kwargs=%r",
                        func.__qualname__,
                        args,
                        kwargs,
                    )
                else:
                    func_logger.debug(
                        "%s called",
                        func.__qualname__,
                    )

                result = func(*args, **kwargs)

                if log_result:
                    func_logger.debug(
                        "%s returned %r",
                        func.__qualname__,
                        result,
                    )

                return result

            except Exception:
                func_logger.exception(
                    "%s failed",
                    func.__qualname__,
                )
                raise

            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                func_logger.debug(
                    "%s completed in %.2f ms",
                    func.__qualname__,
                    elapsed_ms,
                )

        return cast(F, wrapper)

    return decorator
