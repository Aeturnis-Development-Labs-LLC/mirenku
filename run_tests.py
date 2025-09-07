#!/usr/bin/env python3
"""Test runner for Anime Tracker"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))


def run_all_tests():
    """Run all tests"""
    # Discover and run tests
    loader = unittest.TestLoader()
    test_dir = Path(__file__).parent / 'tests'
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def run_specific_test(test_module):
    """Run specific test module
    
    Args:
        test_module: Name of test module (e.g., 'test_database')
    """
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{test_module}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test module
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all tests
        print("Running all tests...")
        print("=" * 70)
        exit_code = run_all_tests()
        print("=" * 70)
        
        if exit_code == 0:
            print("All tests passed!")
        else:
            print("Some tests failed!")
    
    sys.exit(exit_code)