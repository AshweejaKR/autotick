"""YAML configuration loader for AutoTick."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autotick.config.validator import validate_config


class ConfigLoadError(ValueError):
    """Raised when configuration cannot be loaded."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and validate its contents."""
    config_path = Path(path)

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

    validate_config(config)
    return config
