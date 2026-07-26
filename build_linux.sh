#!/bin/bash
# Mirenku v0.3.2 - Linux Build Script
# Creates AppImage and DEB/RPM packages

VERSION="0.3.2"
APP_NAME="mirenku"
DISPLAY_NAME="Mirenku"

echo "================================================"
echo "   Mirenku v${VERSION} - Linux Build"
echo "================================================"
echo

# Check for required tools
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: PyInstaller not found. Install with: pip install pyinstaller"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist "${APP_NAME}" "mirenku_v${VERSION}_linux_x64"*

# Create the executable
echo "Building Linux executable..."
pyinstaller --clean \
    --onefile \
    --name "${APP_NAME}" \
    --icon "assets/mirenku.ico" \
    --add-data "assets:assets" \
    --hidden-import "tkinter" \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "requests" \
    --hidden-import "urllib3" \
    --hidden-import "certifi" \
    --hidden-import "keyring.backends.SecretService" \
    --exclude-module "matplotlib" \
    --exclude-module "numpy" \
    --exclude-module "pandas" \
    --exclude-module "scipy" \
    src/main.py

if [ ! -f "dist/${APP_NAME}" ]; then
    echo "Error: Build failed!"
    exit 1
fi

echo "Executable created successfully!"

# Create AppImage (most universal format)
echo "Creating AppImage..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
mkdir -p AppDir/usr/share/metainfo

# Copy executable
cp "dist/${APP_NAME}" AppDir/usr/bin/

# Create desktop file
cat > "AppDir/usr/share/applications/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=${DISPLAY_NAME}
Comment=Local anime tracker with MyAnimeList sync
Exec=${APP_NAME}
Icon=${APP_NAME}
Categories=AudioVideo;Video;
Terminal=false
StartupNotify=true
EOF

# Copy icon (convert ico to png if needed)
if command -v convert &> /dev/null; then
    convert assets/mirenku.ico[0] "AppDir/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
else
    cp assets/mirenku.ico "AppDir/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.ico"
fi

# Create AppStream metadata
cat > "AppDir/usr/share/metainfo/${APP_NAME}.appdata.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>dev.aeturnis.mirenku</id>
  <name>${DISPLAY_NAME}</name>
  <summary>Local anime tracker with MyAnimeList sync</summary>
  <description>
    <p>Mirenku is a privacy-focused anime tracking application that works offline and syncs with MyAnimeList.</p>
  </description>
  <launchable type="desktop-id">${APP_NAME}.desktop</launchable>
  <url type="homepage">https://mirenku.org</url>
  <project_license>Proprietary</project_license>
  <developer_name>Aeturnis Development Labs LLC</developer_name>
  <releases>
    <release version="${VERSION}" date="$(date +%Y-%m-%d)"/>
  </releases>
</component>
EOF

# Download AppImage tool if not present
if [ ! -f appimagetool-x86_64.AppImage ]; then
    echo "Downloading AppImage tool..."
    wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Create AppImage
ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir "Mirenku-${VERSION}-x86_64.AppImage"

# Create tarball package (universal fallback)
echo "Creating tarball package..."
mkdir -p "mirenku_v${VERSION}_linux_x64"
cp "dist/${APP_NAME}" "mirenku_v${VERSION}_linux_x64/"
cp LICENSE "mirenku_v${VERSION}_linux_x64/LICENSE.txt" 2>/dev/null || echo "No LICENSE file found"
cp README.md "mirenku_v${VERSION}_linux_x64/README.md"
cp SECURITY.md "mirenku_v${VERSION}_linux_x64/SECURITY.txt" 2>/dev/null || echo "No SECURITY.md file found"

# Create simple launch script
cat > "mirenku_v${VERSION}_linux_x64/mirenku.sh" << 'EOF'
#!/bin/bash
# Mirenku launcher script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/mirenku" "$@"
EOF
chmod +x "mirenku_v${VERSION}_linux_x64/mirenku.sh"

# Create installation script
cat > "mirenku_v${VERSION}_linux_x64/install.sh" << 'EOF'
#!/bin/bash
# Mirenku installation script

INSTALL_DIR="/opt/mirenku"
DESKTOP_FILE="/usr/share/applications/mirenku.desktop"
BIN_LINK="/usr/local/bin/mirenku"

echo "Installing Mirenku..."

# Check for root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./install.sh"
    exit 1
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy files
cp mirenku "$INSTALL_DIR/"
cp LICENSE.txt "$INSTALL_DIR/" 2>/dev/null
cp README.md "$INSTALL_DIR/"
cp SECURITY.txt "$INSTALL_DIR/" 2>/dev/null

# Make executable
chmod +x "$INSTALL_DIR/mirenku"

# Create symbolic link
ln -sf "$INSTALL_DIR/mirenku" "$BIN_LINK"

# Create desktop file
cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Type=Application
Name=Mirenku
Comment=Local anime tracker with MyAnimeList sync
Exec=/opt/mirenku/mirenku
Icon=/opt/mirenku/mirenku.png
Categories=AudioVideo;Video;
Terminal=false
StartupNotify=true
DESKTOP

echo "Mirenku installed successfully!"
echo "You can now run 'mirenku' from the terminal or find it in your application menu."
EOF
chmod +x "mirenku_v${VERSION}_linux_x64/install.sh"

# Create tarball
tar -czf "mirenku_v${VERSION}_linux_x64.tar.gz" "mirenku_v${VERSION}_linux_x64"

# Generate checksums
echo "Generating checksums..."
sha256sum "Mirenku-${VERSION}-x86_64.AppImage" > "mirenku_v${VERSION}_linux_appimage.sha256"
sha256sum "mirenku_v${VERSION}_linux_x64.tar.gz" > "mirenku_v${VERSION}_linux_x64.sha256"

# Clean up
rm -rf AppDir
rm -rf "mirenku_v${VERSION}_linux_x64"

echo
echo "================================================"
echo "   Build Complete!"
echo "================================================"
echo
echo "Output files:"
echo "  - Mirenku-${VERSION}-x86_64.AppImage (Universal package)"
echo "  - mirenku_v${VERSION}_linux_x64.tar.gz (Manual installation)"
echo "  - *.sha256 (Checksums)"
echo
echo "AppImage: chmod +x and run directly"
echo "Tarball: Extract and run install.sh with sudo"
echo
