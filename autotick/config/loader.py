# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe

YAML configuration loader for AutoTick.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autotick.config.validator import validate_config


class ConfigLoadError(ValueError):
    """Raised when configuration cannot be loaded."""


def _resolve_file_paths(config: dict[str, Any], config_path: Path) -> None:
    """Resolve configured input files relative to the YAML file location."""
    base = config_path.parent

    for broker_config in config.get("broker_config", {}).values():
        path = broker_config.get("credentials_file")
        if path:
            value = Path(path)
            broker_config["credentials_file"] = str(
                value if value.is_absolute() else (base / value).resolve()
            )

    csv_config = config.get("backtest", {}).get("csv", {})
    path = csv_config.get("data_file")
    if path:
        value = Path(path)
        csv_config["data_file"] = str(
            value if value.is_absolute() else (base / value).resolve()
        )

    path = config.get("persistence", {}).get("state_path")
    if path:
        value = Path(path)
        config["persistence"]["state_path"] = str(
            value if value.is_absolute() else (base / value).resolve()
        )


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML file, resolve file paths, and validate its contents."""
    config_path = Path(path).expanduser().resolve()

    if not config_path.is_file():
        raise ConfigLoadError(f"Configuration file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ConfigLoadError(
            f"Invalid YAML in configuration file: {config_path}"
        ) from exc
    except OSError as exc:
        raise ConfigLoadError(
            f"Unable to read configuration file: {config_path}"
        ) from exc

    if not isinstance(config, dict):
        raise ConfigLoadError("Configuration root must be a YAML mapping")

    _resolve_file_paths(config, config_path)
    validate_config(config)
    return config
