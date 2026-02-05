"""Tests for the desktop app settings management."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from docmaker.app.settings import (
    DEFAULT_SETTINGS,
    get_settings_dir,
    get_settings_path,
    load_settings,
    save_settings,
    reset_settings,
    get_editor_command,
)


# --- Path/Directory Tests ---


def test_get_settings_dir_returns_platform_appropriate_path():
    """Test that get_settings_dir returns a platform-appropriate directory."""
    settings_dir = get_settings_dir()

    assert isinstance(settings_dir, Path)
    assert "docmaker" in str(settings_dir)

    if sys.platform == "win32":
        # Windows: should be in APPDATA
        assert "AppData" in str(settings_dir) or "Roaming" in str(settings_dir)
    elif sys.platform == "darwin":
        # macOS: should be in Library/Application Support
        assert "Library" in str(settings_dir)
        assert "Application Support" in str(settings_dir)
    else:
        # Linux: should be in .config
        assert ".config" in str(settings_dir)


def test_get_settings_path_returns_json_file():
    """Test that get_settings_path returns a path to settings.json."""
    settings_path = get_settings_path()

    assert isinstance(settings_path, Path)
    assert settings_path.name == "settings.json"
    assert settings_path.parent == get_settings_dir()


# --- Load Settings Tests ---


def test_load_settings_returns_defaults_when_no_file(tmp_path, monkeypatch):
    """Test that load_settings returns defaults when no settings file exists."""
    # Point to a non-existent settings file
    monkeypatch.setattr(
        "docmaker.app.settings.get_settings_path",
        lambda: tmp_path / "nonexistent" / "settings.json"
    )

    settings = load_settings()

    assert settings == DEFAULT_SETTINGS


def test_load_settings_merges_saved_with_defaults(tmp_path, monkeypatch):
    """Test that saved settings are merged with defaults (partial settings file)."""
    settings_path = tmp_path / "settings.json"

    # Write partial settings (missing some keys)
    partial_settings = {
        "graphView": {
            "scrollSpeed": 0.5,
            # Missing other graphView keys
        },
        # Missing appearance, editor, general
    }
    settings_path.write_text(json.dumps(partial_settings))

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    settings = load_settings()

    # Custom value should be preserved
    assert settings["graphView"]["scrollSpeed"] == 0.5
    # Default values should be filled in
    assert settings["graphView"]["zoomSensitivity"] == DEFAULT_SETTINGS["graphView"]["zoomSensitivity"]
    assert settings["appearance"] == DEFAULT_SETTINGS["appearance"]
    assert settings["editor"] == DEFAULT_SETTINGS["editor"]
    assert settings["general"] == DEFAULT_SETTINGS["general"]


def test_load_settings_handles_corrupt_json_gracefully(tmp_path, monkeypatch):
    """Test that corrupted JSON returns defaults instead of crashing."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{ invalid json }")

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    settings = load_settings()

    assert settings == DEFAULT_SETTINGS


def test_load_settings_handles_missing_keys(tmp_path, monkeypatch):
    """Test that settings with missing category keys get defaults filled in."""
    settings_path = tmp_path / "settings.json"

    # Write settings with only one category
    partial_settings = {
        "editor": {
            "preferredEditor": "vscode",
            "customEditorCommand": "code {file}:{line}",
            "alwaysAsk": True,
        }
    }
    settings_path.write_text(json.dumps(partial_settings))

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    settings = load_settings()

    # Custom editor values preserved
    assert settings["editor"]["preferredEditor"] == "vscode"
    assert settings["editor"]["customEditorCommand"] == "code {file}:{line}"
    assert settings["editor"]["alwaysAsk"] is True
    # Other categories get defaults
    assert settings["graphView"] == DEFAULT_SETTINGS["graphView"]
    assert settings["appearance"] == DEFAULT_SETTINGS["appearance"]
    assert settings["general"] == DEFAULT_SETTINGS["general"]


# --- Save Settings Tests ---


def test_save_settings_creates_directory_if_missing(tmp_path, monkeypatch):
    """Test that save_settings creates the settings directory if it doesn't exist."""
    settings_dir = tmp_path / "new_dir" / "nested"
    settings_path = settings_dir / "settings.json"

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    save_settings(DEFAULT_SETTINGS)

    assert settings_dir.exists()
    assert settings_path.exists()


def test_save_settings_writes_valid_json(tmp_path, monkeypatch):
    """Test that save_settings writes valid JSON that can be parsed back."""
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    custom_settings = {
        **DEFAULT_SETTINGS,
        "graphView": {
            **DEFAULT_SETTINGS["graphView"],
            "scrollSpeed": 0.8,
        }
    }

    save_settings(custom_settings)

    # Read back and verify
    with open(settings_path) as f:
        loaded = json.load(f)

    assert loaded["graphView"]["scrollSpeed"] == 0.8
    assert loaded["appearance"] == DEFAULT_SETTINGS["appearance"]


def test_save_settings_overwrites_existing(tmp_path, monkeypatch):
    """Test that save_settings overwrites existing settings file."""
    settings_path = tmp_path / "settings.json"

    # Write initial settings
    initial_settings = {"old": "data"}
    settings_path.write_text(json.dumps(initial_settings))

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    save_settings(DEFAULT_SETTINGS)

    # Verify old data is gone
    with open(settings_path) as f:
        loaded = json.load(f)

    assert "old" not in loaded
    assert "graphView" in loaded


# --- Reset Settings Tests ---


def test_reset_settings_deletes_file(tmp_path, monkeypatch):
    """Test that reset_settings deletes the settings file."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(DEFAULT_SETTINGS))

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    result = reset_settings()

    assert not settings_path.exists()
    assert result == DEFAULT_SETTINGS


def test_reset_settings_returns_defaults(tmp_path, monkeypatch):
    """Test that reset_settings returns default settings even if file didn't exist."""
    settings_path = tmp_path / "nonexistent" / "settings.json"

    monkeypatch.setattr("docmaker.app.settings.get_settings_path", lambda: settings_path)

    result = reset_settings()

    assert result == DEFAULT_SETTINGS


# --- Editor Command Tests ---


def test_get_editor_command_auto_mode():
    """Test that 'auto' mode returns auto for system detection."""
    settings = {"editor": {"preferredEditor": "auto", "alwaysAsk": False}}

    command, name = get_editor_command(settings)

    assert command is None
    assert name == "auto"


def test_get_editor_command_specific_editor_vscode():
    """Test that 'vscode' returns the correct command template."""
    settings = {"editor": {"preferredEditor": "vscode", "alwaysAsk": False}}

    command, name = get_editor_command(settings)

    assert command == ["code", "--goto", "{file}:{line}"]
    assert name == "vscode"


def test_get_editor_command_specific_editor_idea():
    """Test that 'idea' returns the correct command template."""
    settings = {"editor": {"preferredEditor": "idea", "alwaysAsk": False}}

    command, name = get_editor_command(settings)

    assert command == ["idea", "--line", "{line}", "{file}"]
    assert name == "idea"


def test_get_editor_command_specific_editor_sublime():
    """Test that 'sublime' returns the correct command template."""
    settings = {"editor": {"preferredEditor": "sublime", "alwaysAsk": False}}

    command, name = get_editor_command(settings)

    assert command == ["subl", "{file}:{line}"]
    assert name == "sublime"


def test_get_editor_command_custom_command():
    """Test that 'custom' mode uses the custom command."""
    settings = {
        "editor": {
            "preferredEditor": "custom",
            "customEditorCommand": "nvim +{line} {file}",
            "alwaysAsk": False,
        }
    }

    command, name = get_editor_command(settings)

    assert command == ["nvim", "+{line}", "{file}"]
    assert name == "custom"


def test_get_editor_command_custom_empty_falls_back_to_ask():
    """Test that empty custom command falls back to ask mode."""
    settings = {
        "editor": {
            "preferredEditor": "custom",
            "customEditorCommand": "",
            "alwaysAsk": False,
        }
    }

    command, name = get_editor_command(settings)

    assert command is None
    assert name == "ask"


def test_get_editor_command_always_ask_returns_ask():
    """Test that alwaysAsk=True returns ask mode regardless of other settings."""
    settings = {
        "editor": {
            "preferredEditor": "vscode",
            "alwaysAsk": True,
        }
    }

    command, name = get_editor_command(settings)

    assert command is None
    assert name == "ask"


def test_get_editor_command_system_mode():
    """Test that 'system' mode returns system for OS default handling."""
    settings = {"editor": {"preferredEditor": "system", "alwaysAsk": False}}

    command, name = get_editor_command(settings)

    assert command is None
    assert name == "system"


def test_get_editor_command_missing_editor_settings():
    """Test that missing editor settings fall back gracefully."""
    settings = {}  # No editor key

    command, name = get_editor_command(settings)

    # Should default to auto mode
    assert name == "auto"
