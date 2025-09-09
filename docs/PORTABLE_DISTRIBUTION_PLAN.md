# Portable Distribution Plan for Mirenku

## Distribution Structure

```
Mirenku_v0.4.0_Portable/
├── Mirenku.exe                    # Main executable
├── register_protocol.ps1          # One-click protocol registration
├── unregister_protocol.ps1        # Clean uninstall
├── README.txt                     # 2-minute quick start guide
├── checksums.txt                  # SHA256 checksums for verification
├── _internal/                     # PyInstaller dependencies
│   └── (bundled libraries)
└── assets/                        # Icons and resources
    └── mirenku.ico
```

## Golden Path User Experience

### 2-Minute Setup Flow
1. **Extract ZIP** → Downloads/Mirenku folder
2. **Right-click `register_protocol.ps1`** → Run with PowerShell
3. **Double-click `Mirenku.exe`** → App launches
4. **Click "Connect MAL"** → Browser opens for authorization
5. **Done!** → Start tracking anime

## PowerShell Scripts

### register_protocol.ps1
```powershell
#Requires -Version 5.0
# Mirenku Protocol Registration Script
# Registers mirenku:// protocol for OAuth2 callbacks

param(
    [switch]$Silent = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "   Mirenku Protocol Installer    " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "Mirenku.exe"

# Verify executable exists
if (-not (Test-Path $exePath)) {
    Write-Host "ERROR: Mirenku.exe not found!" -ForegroundColor Red
    Write-Host "Please ensure this script is in the same folder as Mirenku.exe" -ForegroundColor Yellow
    if (-not $Silent) { Read-Host "Press Enter to exit" }
    exit 1
}

# Create registry entries (HKCU - no admin required)
try {
    Write-Host "Installing protocol handler..." -ForegroundColor Yellow
    
    $protocolName = "mirenku"
    $regPath = "HKCU:\Software\Classes\$protocolName"
    
    # Create main key
    New-Item -Path $regPath -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "(Default)" -Value "URL:Mirenku Protocol" -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "URL Protocol" -Value "" -Force | Out-Null
    
    # Set icon
    New-Item -Path "$regPath\DefaultIcon" -Force | Out-Null
    New-ItemProperty -Path "$regPath\DefaultIcon" -Name "(Default)" -Value "`"$exePath`",0" -Force | Out-Null
    
    # Set command
    New-Item -Path "$regPath\shell\open\command" -Force | Out-Null
    New-ItemProperty -Path "$regPath\shell\open\command" -Name "(Default)" -Value "`"$exePath`" `"%1`"" -Force | Out-Null
    
    Write-Host "✓ Protocol handler installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "1. Run Mirenku.exe" -ForegroundColor White
    Write-Host "2. Click 'Connect MAL' to link your account" -ForegroundColor White
    Write-Host "3. Start tracking your anime!" -ForegroundColor White
    Write-Host ""
    
    if (-not $Silent) {
        Write-Host "Would you like to start Mirenku now? (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq 'Y' -or $response -eq 'y') {
            Start-Process $exePath
        }
    }
} catch {
    Write-Host "ERROR: Failed to register protocol" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if (-not $Silent) { Read-Host "Press Enter to exit" }
    exit 1
}

if (-not $Silent) {
    Write-Host "Press Enter to close this window..." -ForegroundColor Gray
    Read-Host
}
```

### unregister_protocol.ps1
```powershell
#Requires -Version 5.0
# Mirenku Protocol Uninstaller
# Removes mirenku:// protocol registration

param(
    [switch]$Silent = $false
)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Mirenku Protocol Uninstaller   " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$protocolName = "mirenku"
$regPath = "HKCU:\Software\Classes\$protocolName"

if (Test-Path $regPath) {
    try {
        Write-Host "Removing protocol handler..." -ForegroundColor Yellow
        Remove-Item -Path $regPath -Recurse -Force
        Write-Host "✓ Protocol handler removed successfully!" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to remove protocol" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        if (-not $Silent) { Read-Host "Press Enter to exit" }
        exit 1
    }
} else {
    Write-Host "Protocol handler not found (already uninstalled)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Mirenku has been unregistered." -ForegroundColor Green
Write-Host "You can delete the Mirenku folder to complete uninstallation." -ForegroundColor Gray

if (-not $Silent) {
    Write-Host ""
    Write-Host "Press Enter to close this window..." -ForegroundColor Gray
    Read-Host
}
```

## README.txt Content

```text
=====================================
    MIRENKU - Anime Tracking App
        Quick Start Guide (2 min)
=====================================

Thank you for downloading Mirenku v0.4.0!

QUICK START (2 MINUTES):
------------------------
1. RIGHT-CLICK on "register_protocol.ps1"
   → Select "Run with PowerShell"
   → Click "Yes" if Windows asks for permission
   
2. DOUBLE-CLICK "Mirenku.exe" to start the app

3. CLICK "Connect MAL" button in the app
   → Your browser will open
   → Log in to MyAnimeList
   → Click "Allow" to authorize Mirenku
   
4. START TRACKING your anime!

FEATURES:
---------
• Track watching progress
• Sync with MyAnimeList
• Manage your anime library
• Update episode counts
• Add notes and ratings

TROUBLESHOOTING:
----------------
If "Connect MAL" doesn't work:
1. Make sure you ran register_protocol.ps1 first
2. Try running as Administrator
3. Check Windows Defender/Antivirus isn't blocking

UNINSTALL:
----------
1. Run "unregister_protocol.ps1"
2. Delete the Mirenku folder

CHECKSUMS:
----------
Verify file integrity with checksums.txt

SUPPORT:
--------
GitHub: https://github.com/yourusername/mirenku
Email: support@mirenku.app

=====================================
```

## checksums.txt

```text
# SHA256 Checksums for Mirenku v0.4.0
# Generated: 2024-01-20 12:00:00 UTC
#
# To verify on Windows PowerShell:
# Get-FileHash -Algorithm SHA256 .\Mirenku.exe
#
# To verify on Linux/Mac:
# sha256sum Mirenku.exe

Mirenku.exe                 a3f5b8c9d2e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9
register_protocol.ps1       b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5
unregister_protocol.ps1     c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
README.txt                  d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7
assets/mirenku.ico          e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8
```

## Build Script for Portable Distribution

### build_portable.py
```python
"""
Build portable distribution of Mirenku
Creates a ready-to-distribute ZIP file
"""

import os
import sys
import shutil
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime

def calculate_sha256(filepath):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_portable_dist(version="0.4.0"):
    """Create portable distribution package"""
    
    # Paths
    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    portable_dir = dist_dir / f"Mirenku_v{version}_Portable"
    
    print(f"Creating portable distribution v{version}...")
    
    # Clean and create directory
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir(parents=True)
    
    # Step 1: Build executable
    print("Building executable...")
    os.system("pyinstaller mirenku.spec --clean")
    
    # Step 2: Copy files
    print("Copying files...")
    
    # Copy main executable and dependencies
    shutil.copytree(dist_dir / "Mirenku", portable_dir, dirs_exist_ok=True)
    
    # Copy PowerShell scripts
    shutil.copy2("scripts/register_protocol.ps1", portable_dir)
    shutil.copy2("scripts/unregister_protocol.ps1", portable_dir)
    
    # Copy README
    shutil.copy2("README.txt", portable_dir)
    
    # Step 3: Generate checksums
    print("Generating checksums...")
    checksums = []
    for file in portable_dir.glob("**/*"):
        if file.is_file() and file.name != "checksums.txt":
            rel_path = file.relative_to(portable_dir)
            checksum = calculate_sha256(file)
            checksums.append(f"{str(rel_path).ljust(30)} {checksum}")
    
    # Write checksums
    checksum_content = f"""# SHA256 Checksums for Mirenku v{version}
# Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
#
# To verify on Windows PowerShell:
# Get-FileHash -Algorithm SHA256 .\\Mirenku.exe
#
# To verify on Linux/Mac:
# sha256sum Mirenku.exe

""" + "\n".join(checksums)
    
    (portable_dir / "checksums.txt").write_text(checksum_content)
    
    # Step 4: Create ZIP
    print("Creating ZIP archive...")
    zip_path = dist_dir / f"Mirenku_v{version}_Portable.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in portable_dir.rglob("*"):
            if file.is_file():
                arcname = f"Mirenku_v{version}_Portable/{file.relative_to(portable_dir)}"
                zipf.write(file, arcname)
    
    # Step 5: Final checksum of ZIP
    zip_checksum = calculate_sha256(zip_path)
    print(f"\n✓ Build complete!")
    print(f"  Package: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"  SHA256: {zip_checksum}")
    
    # Create release notes
    release_notes = f"""
Mirenku v{version} Portable Release
====================================
File: Mirenku_v{version}_Portable.zip
Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB
SHA256: {zip_checksum}

Installation:
1. Extract ZIP to any folder
2. Run register_protocol.ps1
3. Launch Mirenku.exe
4. Click "Connect MAL" to authenticate
"""
    
    (dist_dir / f"RELEASE_v{version}.txt").write_text(release_notes)
    print(f"\n  Release notes: {dist_dir}/RELEASE_v{version}.txt")

if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "0.4.0"
    create_portable_dist(version)
```

## GitHub Release Template

```markdown
## Mirenku v0.4.0 - Portable Edition

### 🎯 Quick Start (2 minutes)
1. Download `Mirenku_v0.4.0_Portable.zip`
2. Extract to any folder
3. Run `register_protocol.ps1` (right-click → Run with PowerShell)
4. Launch `Mirenku.exe`
5. Click "Connect MAL" to link your account

### ✨ What's New
- Custom protocol handler (`mirenku://`) for seamless OAuth
- Portable distribution - no installation required
- One-click MAL authentication
- Improved token security with keyring support

### 📦 Package Contents
- `Mirenku.exe` - Main application
- `register_protocol.ps1` - Protocol registration (run once)
- `unregister_protocol.ps1` - Clean uninstall
- `README.txt` - Quick start guide
- `checksums.txt` - File integrity verification

### 🔐 Verification
```
SHA256: [checksum_here]
Size: 45.2 MB
```

Verify with: `Get-FileHash -Algorithm SHA256 .\Mirenku_v0.4.0_Portable.zip`

### 🚀 Golden Path
The easiest way to get started:
1. Extract → 2. Register Protocol → 3. Connect MAL → 4. Track Anime!

### ⚠️ Requirements
- Windows 10/11
- PowerShell 5.0+
- Internet connection for MAL sync

### 🗑️ Uninstall
1. Run `unregister_protocol.ps1`
2. Delete the Mirenku folder
3. That's it - no registry cleanup needed!
```

## Advantages of This Approach

1. **Zero Friction Setup**: Extract and run - no installer needed
2. **Golden Path Clear**: Register → Launch → Connect MAL
3. **Trust Building**: Checksums provide verification
4. **Clean Uninstall**: PowerShell script removes all traces
5. **Portable**: Can run from USB drive or any location
6. **No Admin Rights**: Uses HKCU registry only
7. **Self-Contained**: Everything in one folder
8. **Professional**: Matches modern app distribution patterns

This distribution method makes the OAuth setup seamless while maintaining portability and ease of use!