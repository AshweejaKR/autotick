# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

import autotick.main as runner
from autotick.strategy.live_verification import LiveVerificationStrategy
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Run the normal AutoTick pipeline with the verification strategy."""
    print("..... live verification main start .....")
    runner.SimpleStrategy = LiveVerificationStrategy
    try:
        runner.main()
    finally:
        logger.debug("Live verification main exit")
        print("..... live verification main end .....")


if __name__ == "__main__":
    main()
