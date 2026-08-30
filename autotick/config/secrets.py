# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from pathlib import Path


ANGELONE_REQUIRED_KEYS = ("API_KEY", "CLIENT_ID", "PASSWORD", "TOTP_SECRET")


def load_secrets(path: str, required_keys: tuple[str, ...] = ANGELONE_REQUIRED_KEYS) -> dict[str, str]:
    """Load and validate a simple KEY=VALUE secrets file."""
    secret_path = Path(path)
    if not secret_path.is_file():
        raise ValueError(f"Secrets file not found or not a regular file: {secret_path}")

    try:
        lines = secret_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Unable to read secrets file: {secret_path}") from exc

    values: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in values:
            raise ValueError(f"Duplicate secret key: {key}")
        values[key] = value

    unexpected = sorted(values.keys() - set(required_keys))
    if unexpected:
        raise ValueError(f"Unexpected secret key: {unexpected[0]}")
    for key in required_keys:
        if key not in values:
            raise ValueError(f"Missing secret key: {key}")
        if not values[key]:
            raise ValueError(f"Empty secret key: {key}")
    return values
