# -*- coding: utf-8 -*-
"""
Created on Sun Sep 06 2026

@author: ashwe

Live swing-observation entry point for AutoTick.
"""

from __future__ import annotations

from pathlib import Path

import autotick.main as runner

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "swing_verification.yaml"


def main() -> None:
    """Run the CSV swing strategy using its dedicated Live configuration."""
    runner.main(CONFIG_PATH)


if __name__ == "__main__":
    main()
