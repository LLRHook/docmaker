# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Docmaker desktop application.

Build with:
    pyinstaller packaging/docmaker.spec

Or use the build script:
    python packaging/scripts/build.py
"""

import platform
from pathlib import Path

# Determine paths
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent
PACKAGING_DIR = PROJECT_ROOT / "packaging"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ICONS_DIR = PACKAGING_DIR / "icons"

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Icon paths
if IS_WINDOWS:
    ICON_FILE = ICONS_DIR / "docmaker.ico"
elif IS_MACOS:
    ICON_FILE = ICONS_DIR / "docmaker.icns"
else:
    ICON_FILE = ICONS_DIR / "docmaker.png"

# Convert to string and check existence
ICON_PATH = str(ICON_FILE) if ICON_FILE.exists() else None

# Hidden imports for all docmaker modules and dependencies
hidden_imports = [
    # Docmaker modules
    "docmaker",
    "docmaker.app",
    "docmaker.app.main",
    "docmaker.app.ipc",
    "docmaker.cli",
    "docmaker.config",
    "docmaker.models",
    "docmaker.crawler",
    "docmaker.cache",
    "docmaker.llm",
    "docmaker.pipeline",
    "docmaker.parser",
    "docmaker.parser.registry",
    "docmaker.parser.base_parser",
    "docmaker.parser.go_parser",
    "docmaker.parser.java_parser",
    "docmaker.parser.javascript_parser",
    "docmaker.parser.kotlin_parser",
    "docmaker.parser.python_parser",
    "docmaker.parser.typescript_parser",
    "docmaker.generator",
    "docmaker.generator.linker",
    "docmaker.generator.markdown",
    # Tree-sitter grammars
    "tree_sitter",
    "tree_sitter_go",
    "tree_sitter_java",
    "tree_sitter_javascript",
    "tree_sitter_kotlin",
    "tree_sitter_python",
    "tree_sitter_typescript",
    # Pyloid and PySide6
    "pyloid",
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "PySide6.QtNetwork",
    # Other dependencies
    "yaml",
    "click",
    "httpx",
    "pathspec",
    "rich",
    "rich.console",
    "rich.progress",
    "rich.table",
]

# Data files to bundle
datas = []

# Add frontend dist if it exists
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend"))

# Add icon PNG for runtime icon (Qt uses PNG, not ICO for runtime)
ICON_PNG = ICONS_DIR / "docmaker.png"
if ICON_PNG.exists():
    datas.append((str(ICON_PNG), "icons"))

# Analysis
a = Analysis(
    [str(PACKAGING_DIR / "launcher.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",  # Only needed for icon conversion, not runtime
        "cairosvg",
    ],
    noarchive=False,
    optimize=0,
)

# Remove duplicate entries
pyz = PYZ(a.pure)

# Platform-specific executable settings
exe_kwargs = {
    "name": "Docmaker",
    "debug": False,
    "bootloader_ignore_signals": False,
    "strip": False,
    "upx": True,
    "console": False,  # GUI application, no console window
    "disable_windowed_traceback": False,
    "argv_emulation": False,
    "target_arch": None,
    "codesign_identity": None,
    "entitlements_file": None,
}

if ICON_PATH:
    exe_kwargs["icon"] = ICON_PATH

# Windows-specific: version info
if IS_WINDOWS:
    version_file = PACKAGING_DIR / "version_info.txt"
    if version_file.exists():
        exe_kwargs["version"] = str(version_file)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    **exe_kwargs,
)

# Collect all files for distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Docmaker",
)

# macOS: Create app bundle
if IS_MACOS:
    app = BUNDLE(
        coll,
        name="Docmaker.app",
        icon=ICON_PATH,
        bundle_identifier="com.docmaker.app",
        info_plist={
            "CFBundleName": "Docmaker",
            "CFBundleDisplayName": "Docmaker",
            "CFBundleGetInfoString": "Code-to-Knowledge Pipeline",
            "CFBundleIdentifier": "com.docmaker.app",
            "CFBundleVersion": "0.1.0",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # Support dark mode
            "LSMinimumSystemVersion": "10.15",
        },
    )
