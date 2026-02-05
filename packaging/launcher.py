#!/usr/bin/env python3
"""PyInstaller entry point for Docmaker desktop application.

This launcher bypasses the Click CLI and directly launches the desktop app.
"""

import sys


def main():
    """Launch the Docmaker desktop application."""
    # Optional: accept project path as command line argument
    project_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Import here to avoid issues with PyInstaller hooks
    from docmaker.app.main import run_app

    sys.exit(run_app(dev_mode=False, project_path=project_path))


if __name__ == "__main__":
    main()
