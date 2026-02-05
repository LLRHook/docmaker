"""Settings management for the Docmaker desktop app."""

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default settings structure
DEFAULT_SETTINGS: dict[str, Any] = {
    "graphView": {
        "scrollSpeed": 0.3,
        "zoomSensitivity": 0.2,
        "animationSpeed": "normal",
        "defaultLayout": "fcose",
        "showLabels": True,
        "layoutQuality": "default",
        "nodeSizing": "byDegree",
        "largeGraphThreshold": 200,
    },
    "appearance": {
        "fontSize": "medium",
        "uiScale": 100,
    },
    "editor": {
        "preferredEditor": "auto",
        "customEditorCommand": "",
        "alwaysAsk": False,
    },
    "general": {
        "openLastProjectOnStartup": False,
        "lastProjectPath": None,
    },
    "layout": {
        "windowWidth": 1280,
        "windowHeight": 720,
        "sidebarWidth": 288,
        "detailsPanelWidth": 320,
    },
}


def get_settings_dir() -> Path:
    """Get the platform-appropriate settings directory.

    Returns:
        Path to the settings directory:
        - Windows: %APPDATA%/docmaker
        - macOS: ~/Library/Application Support/docmaker
        - Linux: ~/.config/docmaker
    """
    if sys.platform == "win32":
        import os

        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "docmaker"
        return Path.home() / "AppData" / "Roaming" / "docmaker"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "docmaker"
    else:
        # Linux and other Unix-like systems
        xdg_config = Path.home() / ".config"
        return xdg_config / "docmaker"


def get_settings_path() -> Path:
    """Get the path to the settings JSON file.

    Returns:
        Path to settings.json
    """
    return get_settings_dir() / "settings.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary with default values
        override: Dictionary with values to override

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> dict[str, Any]:
    """Load settings from disk, merging with defaults.

    Missing keys in the saved settings will be filled with defaults.
    This ensures forward compatibility when new settings are added.

    Returns:
        Settings dictionary with all keys guaranteed to exist
    """
    settings_path = get_settings_path()

    if not settings_path.exists():
        logger.info("No settings file found, using defaults")
        return DEFAULT_SETTINGS.copy()

    try:
        with open(settings_path, encoding="utf-8") as f:
            saved_settings = json.load(f)

        # Deep merge with defaults to handle missing keys
        merged = _deep_merge(DEFAULT_SETTINGS, saved_settings)
        logger.debug("Settings loaded from %s", settings_path)
        return merged

    except json.JSONDecodeError as e:
        logger.warning("Invalid settings file, using defaults: %s", e)
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logger.warning("Error loading settings, using defaults: %s", e)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings to disk.

    Args:
        settings: Settings dictionary to save

    Raises:
        OSError: If unable to create directory or write file
    """
    settings_path = get_settings_path()
    settings_dir = settings_path.parent

    # Create directory if it doesn't exist
    settings_dir.mkdir(parents=True, exist_ok=True)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    logger.info("Settings saved to %s", settings_path)


def reset_settings() -> dict[str, Any]:
    """Reset settings to defaults.

    Deletes the settings file and returns the default settings.

    Returns:
        Default settings dictionary
    """
    settings_path = get_settings_path()

    if settings_path.exists():
        settings_path.unlink()
        logger.info("Settings file deleted: %s", settings_path)

    return DEFAULT_SETTINGS.copy()


def get_editor_command(settings: dict[str, Any]) -> tuple[list[str] | None, str]:
    """Get the editor command based on settings.

    Args:
        settings: Current settings dictionary

    Returns:
        Tuple of (command_list, editor_name) or (None, "ask") if should ask user
    """
    editor_settings = settings.get("editor", {})
    preferred = editor_settings.get("preferredEditor", "auto")
    always_ask = editor_settings.get("alwaysAsk", False)

    if always_ask:
        return None, "ask"

    # Editor command templates: {file} and {line} are placeholders
    editor_commands: dict[str, tuple[list[str], str]] = {
        "vscode": (["code", "--goto", "{file}:{line}"], "vscode"),
        "idea": (["idea", "--line", "{line}", "{file}"], "idea"),
        "sublime": (["subl", "{file}:{line}"], "sublime"),
    }

    if preferred == "custom":
        custom_cmd = editor_settings.get("customEditorCommand", "")
        if custom_cmd:
            # Parse the custom command, preserving placeholders
            return custom_cmd.split(), "custom"
        return None, "ask"

    if preferred == "system":
        return None, "system"

    if preferred in editor_commands:
        return editor_commands[preferred]

    # Auto-detect: try VS Code first, then fall back to system
    return None, "auto"
