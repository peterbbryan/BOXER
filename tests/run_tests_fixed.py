#!/usr/bin/env python3
"""
Fixed test runner that handles imports correctly
"""
import sys
import os
import unittest
from pathlib import Path

# Change to project root directory for proper imports
project_root = Path(__file__).parent.parent
os.chdir(project_root)


def run_unit_tests():
    """Run unit tests"""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    # Import and run unit tests
    from tests.unit import test_annotation_coordinates
    from tests.unit import test_database_models
    from tests.unit import test_image_utils
    from tests.unit import test_zoom_pan
    from tests.unit import test_api_endpoints

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    suite.addTests(loader.loadTestsFromModule(test_annotation_coordinates))
    suite.addTests(loader.loadTestsFromModule(test_database_models))
    suite.addTests(loader.loadTestsFromModule(test_image_utils))
    suite.addTests(loader.loadTestsFromModule(test_zoom_pan))
    suite.addTests(loader.loadTestsFromModule(test_api_endpoints))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_integration_tests():
    """Run integration tests"""
    print("=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)

    # Import and run integration tests
    from tests.integration import test_database_migrations
    from tests.integration import test_api_contracts
    from tests.integration import test_full_workflows

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    suite.addTests(loader.loadTestsFromModule(test_database_migrations))
    suite.addTests(loader.loadTestsFromModule(test_api_contracts))
    suite.addTests(loader.loadTestsFromModule(test_full_workflows))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_performance_tests():
    """Run performance tests"""
    print("=" * 60)
    print("RUNNING PERFORMANCE TESTS")
    print("=" * 60)

    # Import and run performance tests
    from tests.performance import test_large_images

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    suite.addTests(loader.loadTestsFromModule(test_large_images))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures), len(result.errors)


def run_e2e_tests():
    """Run end-to-end tests"""
    print("=" * 60)
    print("RUNNING END-TO-END TESTS")
    print("=" * 60)

    from tests.e2e import test_ui_functionality

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_ui_functionality))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful(), len(result.failures), len(result.errors)


def main():
    """Main test runner"""
    print("VibeCortex Test Suite")
    print("=" * 20)
    print(f"Python version: {sys.version}")
    print(f"Test directory: {Path(__file__).parent}")
    print(f"Project root: {project_root}")
    print("=" * 60)

    # Run all test categories
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

    # Calculate totals
    total_failures = (
        unit_failures + integration_failures + performance_failures + e2e_failures
    )
    total_errors = unit_errors + integration_errors + performance_errors + e2e_errors
    total_tests_passed = (
        unit_success and integration_success and performance_success and e2e_success
    )

    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
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
    print(f"Total Time:        N/A seconds")
    print(f"Overall Result:    {'PASSED' if total_tests_passed else 'FAILED'}")
    print()
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors:   {total_errors}")

    return 0 if total_tests_passed else 1


if __name__ == "__main__":
    sys.exit(main())
