#!/bin/bash
# Mirenku v0.3.2 - macOS Build Script
# Creates a macOS app bundle and DMG installer

VERSION="0.3.2"
APP_NAME="Mirenku"
BUNDLE_ID="dev.aeturnis.mirenku"

echo "================================================"
echo "   Mirenku v${VERSION} - macOS Build"
echo "================================================"
echo

# Check for required tools
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: PyInstaller not found. Install with: pip install pyinstaller"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist "${APP_NAME}.app" "mirenku_v${VERSION}_macos.dmg"

# Create the app bundle
echo "Building macOS app bundle..."
pyinstaller --clean \
    --onefile \
    --windowed \
    --name "${APP_NAME}" \
    --icon "assets/mirenku.icns" \
    --osx-bundle-identifier "${BUNDLE_ID}" \
    --add-data "assets:assets" \
    --hidden-import "tkinter" \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "requests" \
    --hidden-import "urllib3" \
    --hidden-import "certifi" \
    --hidden-import "keyring.backends.macOS" \
    --exclude-module "matplotlib" \
    --exclude-module "numpy" \
    --exclude-module "pandas" \
    --exclude-module "scipy" \
    --osx-entitlements-file "entitlements.plist" \
    src/main.py

if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "Error: Build failed!"
    exit 1
fi

echo "App bundle created successfully!"

# Create DMG installer
echo "Creating DMG installer..."
mkdir -p dmg_temp
cp -r "dist/${APP_NAME}.app" dmg_temp/
ln -s /Applications dmg_temp/Applications

# Add background image and positioning (optional)
# cp assets/dmg_background.png dmg_temp/.background/

# Create DMG
hdiutil create -volname "${APP_NAME}" \
    -srcfolder dmg_temp \
    -ov \
    -format UDZO \
    "mirenku_v${VERSION}_macos.dmg"

# Clean up
rm -rf dmg_temp

# Generate checksum
echo "Generating checksum..."
shasum -a 256 "mirenku_v${VERSION}_macos.dmg" > "mirenku_v${VERSION}_macos.sha256"

# Sign the app (requires Apple Developer certificate)
if [ -n "$APPLE_DEVELOPER_ID" ]; then
    echo "Signing app with Developer ID..."
    codesign --deep --force --verify --verbose \
        --sign "$APPLE_DEVELOPER_ID" \
        --options runtime \
        "dist/${APP_NAME}.app"

    # Notarize the app (requires Apple ID credentials)
    if [ -n "$APPLE_ID" ] && [ -n "$APPLE_APP_PASSWORD" ]; then
        echo "Notarizing app..."
        xcrun altool --notarize-app \
            --primary-bundle-id "${BUNDLE_ID}" \
            --username "$APPLE_ID" \
            --password "$APPLE_APP_PASSWORD" \
            --file "mirenku_v${VERSION}_macos.dmg"
    fi
else
    echo "Warning: No Apple Developer ID found. App will not be signed."
    echo "Users may see security warnings when opening the app."
fi

echo
echo "================================================"
echo "   Build Complete!"
echo "================================================"
echo
echo "Output files:"
echo "  - mirenku_v${VERSION}_macos.dmg (Installer)"
echo "  - mirenku_v${VERSION}_macos.sha256 (Checksum)"
echo
echo "To install: Open the DMG and drag Mirenku to Applications"
echo
