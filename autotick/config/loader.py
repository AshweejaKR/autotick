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


def _resolve_path(mapping: Any, key: str, base: Path) -> None:
    """Resolve one valid string path and leave invalid types for validation."""
    if not isinstance(mapping, dict):
        return
    path = mapping.get(key)
    if not isinstance(path, str) or not path:
        return
    value = Path(path)
    mapping[key] = str(value if value.is_absolute() else (base / value).resolve())


def _resolve_file_paths(config: dict[str, Any], config_path: Path) -> None:
    """Resolve configured input files relative to the YAML file location."""
    base = config_path.parent

    broker_configs = config.get("broker_config", {})
    if isinstance(broker_configs, dict):
        for broker_config in broker_configs.values():
            _resolve_path(broker_config, "credentials_file", base)

    backtest = config.get("backtest", {})
    csv_config = backtest.get("csv", {}) if isinstance(backtest, dict) else {}
    _resolve_path(csv_config, "data_file", base)
    _resolve_path(config.get("persistence"), "state_path", base)
    _resolve_path(config.get("reports"), "output_dir", base)


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
