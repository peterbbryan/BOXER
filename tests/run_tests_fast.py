#!/usr/bin/env python3
"""
Fast test runner for pre-commit hooks
Runs only essential tests to keep pre-commit fast
"""

import unittest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_fast_tests():
    """Run only fast, essential tests"""
    print("Running fast tests for pre-commit...")

    # Only run unit tests (they're fast)
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), "unit")
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    if result.wasSuccessful():
        print("✅ Fast tests passed!")
        return True
    else:
        print(
            f"❌ Fast tests failed: {len(result.failures)} failures, {len(result.errors)} errors"
        )
        return False


if __name__ == "__main__":
    success = run_fast_tests()
    sys.exit(0 if success else 1)
