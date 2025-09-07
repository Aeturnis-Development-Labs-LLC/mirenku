#!/usr/bin/env python3
"""
Build script for creating Anime Tracker executable
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess


def clean_build_dirs():
    """Remove old build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"Removing {spec_file}")
        spec_file.unlink()


def read_version():
    """Read version from VERSION file"""
    version_file = Path('VERSION')
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.1.0-dev"


def build_executable():
    """Build the executable using PyInstaller"""
    version = read_version()
    
    # Check if icon exists
    icon_path = Path('assets/icon.ico')
    icon_arg = f'--icon={icon_path}' if icon_path.exists() else ''
    
    # PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', f'AnimeTracker-{version}',
        '--add-data', 'assets;assets',
        '--clean',
        '--noconfirm'
    ]
    
    if icon_arg:
        cmd.append(icon_arg)
    
    cmd.append('src/main.py')
    
    print(f"Building Anime Tracker v{version}...")
    print(f"Command: {' '.join(cmd)}")
    
    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Build failed!")
        print(result.stderr)
        return False
    
    print(f"Build successful! Executable created in dist/")
    return True


def create_release_package():
    """Create a release package with executable and documentation"""
    version = read_version()
    release_dir = Path(f'release-{version}')
    
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # Copy executable
    exe_name = f'AnimeTracker-{version}.exe'
    exe_path = Path('dist') / exe_name
    if exe_path.exists():
        shutil.copy(exe_path, release_dir / 'AnimeTracker.exe')
    
    # Copy documentation
    docs_to_copy = ['README.md', 'LICENSE', 'CHANGELOG.md']
    for doc in docs_to_copy:
        if Path(doc).exists():
            shutil.copy(doc, release_dir / doc)
    
    # Create zip archive
    shutil.make_archive(f'anime-tracker-{version}-windows', 'zip', release_dir)
    
    print(f"Release package created: anime-tracker-{version}-windows.zip")
    
    # Clean up
    shutil.rmtree(release_dir)


def main():
    """Main build process"""
    print("=" * 50)
    print("Anime Tracker Build Script")
    print("=" * 50)
    
    # Clean old builds
    print("\n1. Cleaning old build files...")
    clean_build_dirs()
    
    # Build executable
    print("\n2. Building executable...")
    if not build_executable():
        print("Build failed. Exiting.")
        sys.exit(1)
    
    # Create release package
    print("\n3. Creating release package...")
    create_release_package()
    
    print("\n" + "=" * 50)
    print("Build complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()