# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

import autotick.main as runner
from autotick.strategy.live_verification import LiveVerificationStrategy


def main() -> None:
    """Run the normal AutoTick pipeline with the verification strategy."""
    runner.SimpleStrategy = LiveVerificationStrategy
    runner.main()


if __name__ == "__main__":
    main()
