#!/usr/bin/env python
"""
Chat Function Test Runner

Comprehensive test runner for all chat-related functionality.
Runs unit tests, integration tests, and performance tests.
"""

import os

import django
from django.core.management import execute_from_command_line


def run_chat_tests():
    """Run all chat-related tests with coverage reporting"""

    # Set up Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.local")
    django.setup()

    # Test modules to run
    test_modules = [
        "apps.job.tests.test_gemini_chat_service",
        "apps.job.tests.test_chat_api_endpoints",
        "apps.job.tests.test_job_quote_chat_model",
        "apps.job.tests.test_mcp_tool_integration",
        "apps.job.tests.test_chat_performance",
    ]

    print("=" * 80)
    print("CHAT FUNCTION TEST SUITE")
    print("=" * 80)
    print()

    # Run tests with coverage
    print("Running comprehensive chat function tests...")
    print(f"Test modules: {len(test_modules)}")
    print()

    for module in test_modules:
        print(f"  - {module}")

    print()
    print("Starting test execution...")
    print("-" * 80)

    # Execute tests
    test_args = [
        "manage.py",
        "test",
        "--verbosity=2",
        "--failfast",
        "--keepdb",
    ] + test_modules

    execute_from_command_line(test_args)


def run_with_coverage():
    """Run tests with coverage reporting"""
    try:
        import coverage

        # Start coverage
        cov = coverage.Coverage(source=["apps.job"])
        cov.start()

        # Run tests
        run_chat_tests()

        # Stop coverage and generate report
        cov.stop()
        cov.save()

        print("\n" + "=" * 80)
        print("COVERAGE REPORT")
        print("=" * 80)

        # Console report
        cov.report()

        # HTML report
        cov.html_report(directory="coverage_html")
        print("\nHTML coverage report generated in: coverage_html/")

    except ImportError:
        print("Coverage not available, running tests without coverage...")
        run_chat_tests()


def run_performance_tests_only():
    """Run only performance tests"""
    print("=" * 80)
    print("CHAT PERFORMANCE TESTS")
    print("=" * 80)

    test_args = [
        "manage.py",
        "test",
        "--verbosity=2",
        "apps.job.tests.test_chat_performance",
    ]

    execute_from_command_line(test_args)


def run_unit_tests_only():
    """Run only unit tests (fast tests)"""
    print("=" * 80)
    print("CHAT UNIT TESTS")
    print("=" * 80)

    test_modules = [
        "apps.job.tests.test_gemini_chat_service",
        "apps.job.tests.test_job_quote_chat_model",
        "apps.job.tests.test_mcp_tool_integration",
    ]

    test_args = [
        "manage.py",
        "test",
        "--verbosity=2",
        "--failfast",
    ] + test_modules

    execute_from_command_line(test_args)


def run_integration_tests_only():
    """Run only integration tests"""
    print("=" * 80)
    print("CHAT INTEGRATION TESTS")
    print("=" * 80)

    test_args = [
        "manage.py",
        "test",
        "--verbosity=2",
        "apps.job.tests.test_chat_api_endpoints",
    ]

    execute_from_command_line(test_args)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run chat function tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )

    args = parser.parse_args()

    if args.performance:
        run_performance_tests_only()
    elif args.unit:
        run_unit_tests_only()
    elif args.integration:
        run_integration_tests_only()
    elif args.coverage:
        run_with_coverage()
    else:
        run_chat_tests()
