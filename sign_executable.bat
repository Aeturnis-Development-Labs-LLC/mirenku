@echo off
REM Mirenku Executable Signing Script
REM Requires Windows SDK signtool.exe

echo ========================================
echo Mirenku v0.3.2 - Code Signing
echo ========================================

REM Configuration
set SIGNTOOL="C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
set EXECUTABLE=dist\mirenku.exe
set TIMESTAMP_SERVER=http://timestamp.digicert.com

REM Check if signtool exists
if not exist %SIGNTOOL% (
    echo ERROR: signtool.exe not found!
    echo Please install Windows SDK or update the path in this script
    exit /b 1
)

REM Check if executable exists
if not exist %EXECUTABLE% (
    echo ERROR: %EXECUTABLE% not found!
    echo Please build the executable first
    exit /b 1
)

REM Option 1: Sign with certificate from Windows Certificate Store
REM Uncomment if you have a certificate installed
REM %SIGNTOOL% sign /n "Aeturnis Development Labs LLC" /t %TIMESTAMP_SERVER% /fd SHA256 /v %EXECUTABLE%

REM Option 2: Sign with PFX file
REM Uncomment and update path if you have a PFX certificate file
REM set CERT_FILE=path\to\your\certificate.pfx
REM set CERT_PASSWORD=your_password
REM %SIGNTOOL% sign /f %CERT_FILE% /p %CERT_PASSWORD% /t %TIMESTAMP_SERVER% /fd SHA256 /v %EXECUTABLE%

REM Option 3: Sign with self-signed certificate (for testing)
echo Searching for code signing certificates...
%SIGNTOOL% sign /a /t %TIMESTAMP_SERVER% /fd SHA256 /v %EXECUTABLE%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Executable signed successfully!
    echo.
    echo Verifying signature...
    %SIGNTOOL% verify /pa /v %EXECUTABLE%
) else (
    echo.
    echo WARNING: Failed to sign executable
    echo This is normal if you don't have a code signing certificate
    echo.
    echo To sign the executable, you need:
    echo 1. A code signing certificate from a trusted CA, or
    echo 2. A self-signed certificate for testing
    echo.
    echo The executable will still work but may show security warnings
)

echo.
echo ========================================
echo Signing process complete
echo ========================================
pause
