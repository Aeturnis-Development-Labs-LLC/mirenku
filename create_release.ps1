# Mirenku v0.3.2 Release Packaging Script
# Creates a release package with checksums

$Version = "0.3.2"
$ReleaseName = "mirenku_v${Version}_windows"
$ReleaseDir = "release"
$DistDir = "dist"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mirenku v$Version - Release Package Creator" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Create release directory
Write-Host "Creating release directory..." -ForegroundColor Yellow
if (Test-Path $ReleaseDir) {
    Remove-Item -Path "$ReleaseDir\*" -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
}

# Copy executable
Write-Host "Copying executable..." -ForegroundColor Yellow
if (Test-Path "$DistDir\mirenku.exe") {
    Copy-Item "$DistDir\mirenku.exe" "$ReleaseDir\mirenku.exe"
    Write-Host "  ✓ mirenku.exe" -ForegroundColor Green
} else {
    Write-Host "  ✗ mirenku.exe not found! Build it first." -ForegroundColor Red
    exit 1
}

# Copy documentation files
Write-Host "Copying documentation..." -ForegroundColor Yellow

# Copy LICENSE
if (Test-Path "LICENSE") {
    Copy-Item "LICENSE" "$ReleaseDir\LICENSE.txt"
    Write-Host "  ✓ LICENSE.txt" -ForegroundColor Green
}

# Copy SECURITY.md as SECURITY.txt
if (Test-Path "SECURITY.md") {
    Copy-Item "SECURITY.md" "$ReleaseDir\SECURITY.txt"
    Write-Host "  ✓ SECURITY.txt" -ForegroundColor Green
}

# Copy Release Notes
if (Test-Path "docs\RELEASE_NOTES_v$Version.md") {
    Copy-Item "docs\RELEASE_NOTES_v$Version.md" "$ReleaseDir\RELEASE_NOTES.txt"
    Write-Host "  ✓ RELEASE_NOTES.txt" -ForegroundColor Green
}

# README.txt should already exist
if (Test-Path "$ReleaseDir\README.txt") {
    Write-Host "  ✓ README.txt" -ForegroundColor Green
}

# Generate file checksums
Write-Host ""
Write-Host "Generating checksums..." -ForegroundColor Yellow
$ChecksumFile = "$ReleaseDir\checksums.txt"

"Mirenku v$Version - File Checksums" | Out-File $ChecksumFile
"Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $ChecksumFile -Append
"================================================" | Out-File $ChecksumFile -Append
"" | Out-File $ChecksumFile -Append

Get-ChildItem -Path $ReleaseDir -File | Where-Object { $_.Name -ne "checksums.txt" } | ForEach-Object {
    $Hash = Get-FileHash -Path $_.FullName -Algorithm SHA256
    $Size = (Get-Item $_.FullName).Length
    $SizeMB = [math]::Round($Size / 1MB, 2)

    "File: $($_.Name)" | Out-File $ChecksumFile -Append
    "Size: $Size bytes ($($SizeMB) MB)" | Out-File $ChecksumFile -Append
    "SHA256: $($Hash.Hash)" | Out-File $ChecksumFile -Append
    "" | Out-File $ChecksumFile -Append

    Write-Host "  ✓ $($_.Name) - SHA256 computed" -ForegroundColor Green
}

# Create ZIP archive
Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
$ZipPath = "${ReleaseName}.zip"

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

# Use .NET compression to create ZIP
Add-Type -Assembly System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($ReleaseDir, $ZipPath, 'Optimal', $false)

if (Test-Path $ZipPath) {
    $ZipSize = (Get-Item $ZipPath).Length
    $ZipSizeMB = [math]::Round($ZipSize / 1MB, 2)
    Write-Host "  ✓ $ZipPath created ($($ZipSizeMB) MB)" -ForegroundColor Green

    # Generate checksum for ZIP
    $ZipHash = Get-FileHash -Path $ZipPath -Algorithm SHA256
    Write-Host "  ✓ SHA256: $($ZipHash.Hash.Substring(0,16))..." -ForegroundColor Green

    # Create a separate checksum file for the ZIP
    $ZipChecksumFile = "${ReleaseName}.sha256"
    "$($ZipHash.Hash)  $ZipPath" | Out-File $ZipChecksumFile -Encoding ASCII
    Write-Host "  ✓ Checksum saved to $ZipChecksumFile" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to create ZIP archive!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Release package created successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Release files:" -ForegroundColor Yellow
Write-Host "  - $ZipPath (Main release package)" -ForegroundColor White
Write-Host "  - $ZipChecksumFile (ZIP checksum)" -ForegroundColor White
Write-Host "  - $ReleaseDir\ (Extracted contents)" -ForegroundColor White
Write-Host ""
Write-Host "To verify the release:" -ForegroundColor Yellow
Write-Host "  certutil -hashfile $ZipPath SHA256" -ForegroundColor White
Write-Host ""
