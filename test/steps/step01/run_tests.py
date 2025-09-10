#!/usr/bin/env python3
"""
Test runner script for Step 01 tests.
Demonstrates how to run the comprehensive test suite.
"""

import os
import sys
from pathlib import Path

# Add the source directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

import pytest


def run_step01_tests():
    """Run all Step 01 tests."""
    
    test_dir = Path(__file__).parent
    
    # Validate that test directory exists
    if not test_dir.exists():
        print(f"Error: Test directory does not exist: {test_dir}")
        return 1
    
    # Test arguments for different scenarios
    test_configs = {
        "unit": [
            str(test_dir),
            "-v",
            "-m", "unit",
            "--tb=short"
        ],
        "integration": [
            str(test_dir),
            "-v", 
            "-m", "integration",
            "--tb=short"
        ],
        "all": [
            str(test_dir),
            "-v",
            "--tb=short"
        ],
        "coverage": [
            str(test_dir),
            "-v",
            "--cov=steps.step01",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--tb=short"
        ]
    }
    
    print("Step 01 Test Runner")
    print("==================")
    print("Available test configurations:")
    for config_name in test_configs.keys():
        print(f"  - {config_name}")
    print()
    print("Usage: python run_tests.py [config_name]")
    print("If no config is specified, 'all' will be used.")
    
    # Get configuration from command line or default to 'all'
    config_name = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    if config_name not in test_configs:
        print(f"Unknown configuration: {config_name}")
        print(f"Available: {list(test_configs.keys())}")
        return 1
    
    print(f"\nRunning tests with configuration: {config_name}")
    print("-" * 50)
    
    # Run pytest with the selected configuration
    return pytest.main(test_configs[config_name])


def main():
    """Main entry point."""
    try:
        exit_code = run_step01_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except (RuntimeError, SystemExit) as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
