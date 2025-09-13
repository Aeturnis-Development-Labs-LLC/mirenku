@echo off
REM Mirenku v0.3.2 Release Packaging Script

set VERSION=0.3.2
set RELEASE_NAME=mirenku_v%VERSION%_windows
set RELEASE_DIR=release
set DIST_DIR=dist

echo ================================================
echo   Mirenku v%VERSION% - Release Package Creator
echo ================================================
echo.

REM Create release directory
echo Creating release directory...
if exist %RELEASE_DIR% rmdir /s /q %RELEASE_DIR%
mkdir %RELEASE_DIR%

REM Copy executable
echo Copying executable...
if exist %DIST_DIR%\mirenku.exe (
    copy %DIST_DIR%\mirenku.exe %RELEASE_DIR%\mirenku.exe
    echo   + mirenku.exe
) else (
    echo   ERROR: mirenku.exe not found!
    exit /b 1
)

REM Copy documentation
echo Copying documentation...
if exist LICENSE copy LICENSE %RELEASE_DIR%\LICENSE.txt && echo   + LICENSE.txt
if exist SECURITY.md copy SECURITY.md %RELEASE_DIR%\SECURITY.txt && echo   + SECURITY.txt
if exist docs\RELEASE_NOTES_v%VERSION%.md copy docs\RELEASE_NOTES_v%VERSION%.md %RELEASE_DIR%\RELEASE_NOTES.txt && echo   + RELEASE_NOTES.txt
if exist %RELEASE_DIR%\README.txt echo   + README.txt

REM Generate checksums
echo.
echo Generating checksums...
cd %RELEASE_DIR%
echo Mirenku v%VERSION% - File Checksums > checksums.txt
echo Generated: %date% %time% >> checksums.txt
echo ================================================ >> checksums.txt
echo. >> checksums.txt

for %%f in (*) do (
    if not "%%f"=="checksums.txt" (
        echo File: %%f >> checksums.txt
        certutil -hashfile "%%f" SHA256 | findstr /v ":" >> checksums.txt
        echo. >> checksums.txt
        echo   + %%f - SHA256 computed
    )
)
cd ..

REM Create ZIP using PowerShell
echo.
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%RELEASE_NAME%.zip' -Force"

if exist %RELEASE_NAME%.zip (
    echo   + %RELEASE_NAME%.zip created

    REM Generate checksum for ZIP
    echo.
    echo Generating ZIP checksum...
    certutil -hashfile %RELEASE_NAME%.zip SHA256 | findstr /v ":" > %RELEASE_NAME%.sha256
    echo   + %RELEASE_NAME%.sha256 created
) else (
    echo   ERROR: Failed to create ZIP!
    exit /b 1
)

echo.
echo ================================================
echo   Release package created successfully!
echo ================================================
echo.
echo Release files:
echo   - %RELEASE_NAME%.zip (Main release package)
echo   - %RELEASE_NAME%.sha256 (ZIP checksum)
echo   - %RELEASE_DIR%\ (Extracted contents)
echo.
echo To verify the release:
echo   certutil -hashfile %RELEASE_NAME%.zip SHA256
echo.
pause
