#!/usr/bin/env python
"""Platform-specific checks for CI - The Mirenku Way"""

import sys
import os
import platform

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_platform():
    """Check platform-specific features"""

    # What platform are we on?
    system = platform.system()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f'[OK] Running on {system} with Python {python_version}')

    # Test config paths work on this platform
    from utils.config import Config
    config = Config()
    db_path = config.get_db_path()
    print(f'[OK] Config paths work: {db_path}')

    # Test that paths are appropriate for the platform
    if system == 'Windows':
        assert 'AppData' in str(db_path) or 'Users' in str(db_path), "Windows path incorrect"
        print('[OK] Windows-specific paths configured')
    elif system == 'Darwin':  # macOS
        assert 'Library' in str(db_path) or 'Users' in str(db_path), "macOS path incorrect"
        print('[OK] macOS-specific paths configured')
    else:  # Linux
        assert '.local' in str(db_path) or 'home' in str(db_path), "Linux path incorrect"
        print('[OK] Linux-specific paths configured')

    # Test that tkinter is available (but don't create windows)
    try:
        import tkinter
        print('[OK] Tkinter available')
    except ImportError:
        print('[WARN] Tkinter not available (GUI tests will be skipped)')
        # This is OK for headless CI

    # Test file operations work
    test_file = config.get_data_dir() / 'test_write.tmp'
    try:
        test_file.write_text('test')
        test_file.unlink()
        print('[OK] File operations work')
    except Exception as e:
        print(f'[WARN] File operations limited: {e}')

    print(f'\n[SUCCESS] Platform checks passed for {system}!')
    return True

if __name__ == '__main__':
    try:
        success = check_platform()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'[FAIL] Platform check failed: {e}')
        sys.exit(1)