#!/usr/bin/env python3
"""Cross-platform build script for Docmaker desktop application.

This script handles the complete build process:
1. Validates prerequisites (frontend built, dependencies installed)
2. Runs PyInstaller with the appropriate spec file
3. Reports build output location
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
PACKAGING_DIR = PROJECT_ROOT / "packaging"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
SPEC_FILE = PACKAGING_DIR / "docmaker.spec"


def get_platform():
    """Get normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def check_frontend():
    """Verify frontend is built."""
    if not FRONTEND_DIST.exists():
        print("Error: Frontend not built.")
        print("Run: cd frontend && npm install && npm run build")
        return False

    index_html = FRONTEND_DIST / "index.html"
    if not index_html.exists():
        print("Error: Frontend build incomplete (index.html missing).")
        return False

    print(f"Frontend found at: {FRONTEND_DIST}")
    return True


def check_pyinstaller():
    """Verify PyInstaller is installed."""
    try:
        import PyInstaller

        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("Error: PyInstaller not installed.")
        print("Run: pip install pyinstaller")
        return False


def check_icons():
    """Check if platform-specific icons exist."""
    plat = get_platform()
    icons_dir = PACKAGING_DIR / "icons"

    if plat == "windows":
        icon_file = icons_dir / "docmaker.ico"
    elif plat == "macos":
        icon_file = icons_dir / "docmaker.icns"
    else:
        icon_file = icons_dir / "docmaker.png"

    if not icon_file.exists():
        print(f"Warning: Icon not found at {icon_file}")
        print("Run: python packaging/scripts/convert_icons.py packaging/icons/docmaker.svg")
        return False

    print(f"Icon found: {icon_file}")
    return True


def clean_build():
    """Clean previous build artifacts."""
    build_dir = PROJECT_ROOT / "build"
    dist_dir = PROJECT_ROOT / "dist"

    for d in [build_dir, dist_dir]:
        if d.exists():
            print(f"Cleaning: {d}")
            shutil.rmtree(d)


def run_pyinstaller(clean: bool = False, debug: bool = False):
    """Run PyInstaller with the spec file."""
    if not SPEC_FILE.exists():
        print(f"Error: Spec file not found at {SPEC_FILE}")
        return False

    cmd = [sys.executable, "-m", "PyInstaller"]

    if clean:
        cmd.append("--clean")

    if debug:
        cmd.append("--log-level=DEBUG")

    cmd.append(str(SPEC_FILE))

    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    return result.returncode == 0


def report_output():
    """Report build output location."""
    dist_dir = PROJECT_ROOT / "dist"
    plat = get_platform()

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)

    if plat == "windows":
        exe_path = dist_dir / "Docmaker" / "Docmaker.exe"
        if exe_path.exists():
            print(f"Executable: {exe_path}")
            print(f"Folder size: {get_dir_size(dist_dir / 'Docmaker'):.1f} MB")
    elif plat == "macos":
        app_path = dist_dir / "Docmaker.app"
        if app_path.exists():
            print(f"App bundle: {app_path}")
            print(f"Bundle size: {get_dir_size(app_path):.1f} MB")
    else:
        exe_path = dist_dir / "Docmaker" / "Docmaker"
        if exe_path.exists():
            print(f"Executable: {exe_path}")
            print(f"Folder size: {get_dir_size(dist_dir / 'Docmaker'):.1f} MB")

    print("\nTo run:")
    if plat == "windows":
        print(f'  .\\dist\\Docmaker\\Docmaker.exe')
    elif plat == "macos":
        print(f"  open dist/Docmaker.app")
    else:
        print(f"  ./dist/Docmaker/Docmaker")


def get_dir_size(path: Path) -> float:
    """Get directory size in MB."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total / (1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description="Build Docmaker desktop application")
    parser.add_argument("--clean", action="store_true", help="Clean build directories first")
    parser.add_argument("--debug", action="store_true", help="Enable PyInstaller debug logging")
    parser.add_argument("--skip-checks", action="store_true", help="Skip prerequisite checks")
    args = parser.parse_args()

    print(f"Building Docmaker for {get_platform()}")
    print(f"Project root: {PROJECT_ROOT}")
    print("-" * 60)

    if not args.skip_checks:
        # Check prerequisites
        checks = [
            ("Frontend", check_frontend),
            ("PyInstaller", check_pyinstaller),
            ("Icons", check_icons),
        ]

        all_passed = True
        for name, check_fn in checks:
            print(f"\nChecking {name}...")
            if not check_fn():
                all_passed = False

        if not all_passed:
            print("\nSome checks failed. Fix issues above or use --skip-checks to proceed anyway.")
            sys.exit(1)

    # Clean if requested
    if args.clean:
        print("\nCleaning previous builds...")
        clean_build()

    # Run PyInstaller
    print("\nRunning PyInstaller...")
    if not run_pyinstaller(clean=args.clean, debug=args.debug):
        print("\nBuild failed!")
        sys.exit(1)

    # Report output
    report_output()


if __name__ == "__main__":
    main()
