@echo off
echo Building Mirenku v0.3.0...
echo ================================

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build executable using spec file
pyinstaller build.spec --clean

echo.
echo Build complete! Check the dist folder for Mirenku_v0.3.0.exe
pause