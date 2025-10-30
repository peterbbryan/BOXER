#!/usr/bin/env python3
"""
Test runner for BOXER test suite
"""

import unittest
import sys
import os
import time
from pathlib import Path

# Change to project root directory for proper imports
project_root = Path(__file__).parent.parent
os.chdir(project_root)


def cleanup_test_artifacts():
    """Clean up test artifacts after running tests"""
    try:
        from tests.cleanup_utils import cleanup_all

        cleanup_all()
    except Exception as e:
        print(f"⚠️  Warning: Cleanup failed: {e}")


def run_unit_tests():
    """Run unit tests"""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), "unit")
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_integration_tests():
    """Run integration tests"""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)

    # Discover and run integration tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), "integration")
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_performance_tests():
    """Run performance tests"""
    print("\n" + "=" * 60)
    print("RUNNING PERFORMANCE TESTS")
    print("=" * 60)

    # Discover and run performance tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), "performance")
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_e2e_tests():
    """Run end-to-end tests"""
    print("\n" + "=" * 60)
    print("RUNNING END-TO-END TESTS")
    print("=" * 60)

    # Check if e2e tests exist
    start_dir = os.path.join(os.path.dirname(__file__), "e2e")
    if not os.path.exists(start_dir) or not os.listdir(start_dir):
        print("No end-to-end tests found - skipping")
        return True, 0, 0

    # Discover and run e2e tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def main():
    """Main test runner"""
    print("BOXER Test Suite")
    print("====================")
    print(f"Python version: {sys.version}")
    print(f"Test directory: {os.path.dirname(__file__)}")
    print(f"Project root: {project_root}")

    start_time = time.time()

    # Run all test suites
    unit_success, unit_failures, unit_errors = run_unit_tests()
    (
        integration_success,
        integration_failures,
        integration_errors,
    ) = run_integration_tests()
    (
        performance_success,
        performance_failures,
        performance_errors,
    ) = run_performance_tests()
    e2e_success, e2e_failures, e2e_errors = run_e2e_tests()

    end_time = time.time()
    total_time = end_time - start_time

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total_failures = (
        unit_failures + integration_failures + performance_failures + e2e_failures
    )
    total_errors = unit_errors + integration_errors + performance_errors + e2e_errors
    total_tests_passed = (
        unit_success and integration_success and performance_success and e2e_success
    )

    print(
        f"Unit Tests:        {'PASSED' if unit_success else 'FAILED'} ({unit_failures} failures, {unit_errors} errors)"
    )
    print(
        f"Integration Tests: {'PASSED' if integration_success else 'FAILED'} ({integration_failures} failures, {integration_errors} errors)"
    )
    print(
        f"Performance Tests: {'PASSED' if performance_success else 'FAILED'} ({performance_failures} failures, {performance_errors} errors)"
    )
    print(
        f"End-to-End Tests:  {'PASSED' if e2e_success else 'FAILED'} ({e2e_failures} failures, {e2e_errors} errors)"
    )
    print(f"Total Time:        {total_time:.2f} seconds")
    print(f"Overall Result:    {'PASSED' if total_tests_passed else 'FAILED'}")
    print()

    # Clean up after running tests
    print("=" * 60)
    cleanup_test_artifacts()
    print("=" * 60)

    if total_failures > 0 or total_errors > 0:
        print(f"\nTotal Failures: {total_failures}")
        print(f"Total Errors:   {total_errors}")
        sys.exit(1)
    else:
        print("\nAll tests passed! 🎉")
        sys.exit(0)


if __name__ == "__main__":
    main()
