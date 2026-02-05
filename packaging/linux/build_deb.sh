#!/bin/bash
# Build Debian package from PyInstaller output
# Run this AFTER running the main build script
#
# Usage: ./packaging/linux/build_deb.sh [version]
#   version: Package version (default: 0.1.0)

set -e

VERSION="${1:-0.1.0}"
ARCH="amd64"
PACKAGE_NAME="docmaker"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
PYINSTALLER_OUTPUT="$DIST_DIR/Docmaker"
DEB_ROOT="$DIST_DIR/deb_build"
PACKAGE_DIR="$DEB_ROOT/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "============================================================"

# Check PyInstaller output exists
if [ ! -d "$PYINSTALLER_OUTPUT" ]; then
    echo "Error: PyInstaller output not found at $PYINSTALLER_OUTPUT"
    echo "Run the build script first: python packaging/scripts/build.py"
    exit 1
fi

# Clean previous build
rm -rf "$DEB_ROOT"
mkdir -p "$DEB_ROOT"

# Create package directory structure
mkdir -p "$PACKAGE_DIR/DEBIAN"
mkdir -p "$PACKAGE_DIR/opt/docmaker"
mkdir -p "$PACKAGE_DIR/usr/share/applications"
mkdir -p "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PACKAGE_DIR/usr/bin"

# Copy PyInstaller output
echo "Copying application files..."
cp -r "$PYINSTALLER_OUTPUT"/* "$PACKAGE_DIR/opt/docmaker/"

# Copy desktop file
cp "$SCRIPT_DIR/docmaker.desktop" "$PACKAGE_DIR/usr/share/applications/"

# Copy icon
ICON_SOURCE="$PROJECT_ROOT/packaging/icons/docmaker.png"
if [ -f "$ICON_SOURCE" ]; then
    cp "$ICON_SOURCE" "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps/docmaker.png"
else
    echo "Warning: Icon not found at $ICON_SOURCE"
fi

# Create symlink in /usr/bin
ln -sf /opt/docmaker/Docmaker "$PACKAGE_DIR/usr/bin/docmaker"

# Calculate installed size (in KB)
INSTALLED_SIZE=$(du -sk "$PACKAGE_DIR" | cut -f1)

# Create control file
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: devel
Priority: optional
Architecture: $ARCH
Installed-Size: $INSTALLED_SIZE
Maintainer: Victor <victor.n.ivanov@gmail.com>
Homepage: https://github.com/LLRHook/docmaker
Description: Code-to-Knowledge Pipeline
 Docmaker crawls codebases, parses source files using Tree-sitter,
 and generates interlinked Obsidian-compatible markdown documentation.
 It supports optional LLM-based file classification.
EOF

# Create postinst script (update icon cache)
cat > "$PACKAGE_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/postinst"

# Create postrm script
cat > "$PACKAGE_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/postrm"

# Set permissions
chmod 755 "$PACKAGE_DIR/opt/docmaker/Docmaker"

# Build the package
echo "Building .deb package..."
dpkg-deb --build --root-owner-group "$PACKAGE_DIR"

# Move to dist directory
mv "$DEB_ROOT/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" "$DIST_DIR/"

# Clean up
rm -rf "$DEB_ROOT"

echo ""
echo "============================================================"
echo "Package created: $DIST_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "Install with:"
echo "  sudo dpkg -i $DIST_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "Uninstall with:"
echo "  sudo dpkg -r $PACKAGE_NAME"
