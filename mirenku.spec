# -*- mode: python ; coding: utf-8 -*-
# Mirenku PyInstaller Spec File

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Get the root directory
ROOT_DIR = Path.cwd()

# Read the version from the single source in src/__init__.py
sys.path.insert(0, str(ROOT_DIR / 'src'))
from __init__ import __version__ as APP_VERSION

a = Analysis(
    ['src/main.py'],
    pathex=[str(ROOT_DIR / 'src')],
    binaries=[],
    datas=[
        (str(ROOT_DIR / 'assets'), 'assets'),
        (str(ROOT_DIR / 'LICENSE'), '.'),
        (str(ROOT_DIR / 'README.md'), '.'),
        (str(ROOT_DIR / 'docs' / 'RELEASE_NOTES_v0.3.2.md'), 'docs'),
    ] + collect_data_files('sv_ttk'),
    hiddenimports=[
        'PIL._tkinter_finder',
        'requests',
        'cryptography',
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'psutil',
        'sv_ttk',
        'darkdetect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'ipython',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mirenku',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,  # Version info file not required for CI builds
    icon=str(ROOT_DIR / 'assets' / 'mirenku.ico'),
    uac_admin=False,
    uac_uiaccess=False,
)

# For future app bundle support (macOS)
app = BUNDLE(
    exe,
    name='Mirenku.app',
    icon=str(ROOT_DIR / 'assets' / 'mirenku.ico'),
    bundle_identifier='com.mirenku.tracker',
    info_plist={
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.12.0',
    },
)
