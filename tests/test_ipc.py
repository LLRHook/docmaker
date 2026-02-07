"""Tests for the IPC get_source_snippet endpoint."""

import json
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def api():
    """Create a DocmakerAPI instance with mocked Qt/Pyloid dependencies."""
    # Set up mock modules before importing ipc
    bridge_mock = mock.MagicMock()
    bridge_mock.Bridge = lambda *a, **kw: lambda fn: fn

    class FakePyloidIPC:
        pass

    bridge_mock.PyloidIPC = FakePyloidIPC

    mocks = {
        "pyloid": mock.MagicMock(),
        "pyloid.ipc": bridge_mock,
        "PySide6": mock.MagicMock(),
        "PySide6.QtWidgets": mock.MagicMock(),
    }

    saved = {}
    for mod_name in mocks:
        if mod_name in sys.modules:
            saved[mod_name] = sys.modules[mod_name]

    try:
        sys.modules.update(mocks)

        # Force re-import with mocks
        if "docmaker.app.ipc" in sys.modules:
            del sys.modules["docmaker.app.ipc"]

        from docmaker.app.ipc import DocmakerAPI

        yield DocmakerAPI()
    finally:
        # Restore original modules
        for mod_name in mocks:
            if mod_name in saved:
                sys.modules[mod_name] = saved[mod_name]
            else:
                sys.modules.pop(mod_name, None)
        sys.modules.pop("docmaker.app.ipc", None)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project with a sample source file."""
    src = tmp_path / "hello.py"
    src.write_text(textwrap.dedent("""\
        def hello():
            print("hello")

        def world():
            print("world")

        class Foo:
            pass
    """))
    return tmp_path


class TestGetSourceSnippet:
    """Tests for get_source_snippet IPC endpoint."""

    def test_returns_snippet(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet(str(project_dir / "hello.py"), 1, 2))
        assert "source" in result
        assert "def hello():" in result["source"]
        assert result["startLine"] == 1
        assert result["endLine"] == 2

    def test_relative_path(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("hello.py", 4, 5))
        assert "source" in result
        assert "def world():" in result["source"]

    def test_no_project_loaded(self, api):
        result = json.loads(api.get_source_snippet("/some/file.py", 1, 5))
        assert "error" in result
        assert "No project loaded" in result["error"]

    def test_file_not_found(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("nonexistent.py", 1, 5))
        assert "error" in result
        assert "File not found" in result["error"]

    def test_path_outside_project(self, api, project_dir):
        api._current_project = project_dir
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("secret")
            outside_path = f.name
        try:
            result = json.loads(api.get_source_snippet(outside_path, 1, 1))
            assert "error" in result
            assert "outside the project" in result["error"]
        finally:
            Path(outside_path).unlink(missing_ok=True)

    def test_start_beyond_file(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("hello.py", 999, 1000))
        assert "error" in result
        assert "exceeds file length" in result["error"]

    def test_clamps_end_to_file_length(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("hello.py", 1, 999))
        assert "source" in result
        assert result["endLine"] <= result["totalLines"]

    def test_returns_total_lines(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("hello.py", 1, 1))
        assert result["totalLines"] == 8

    def test_single_line(self, api, project_dir):
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("hello.py", 7, 7))
        assert "source" in result
        assert "class Foo:" in result["source"]

    def test_not_a_file(self, api, project_dir):
        subdir = project_dir / "subdir"
        subdir.mkdir()
        api._current_project = project_dir
        result = json.loads(api.get_source_snippet("subdir", 1, 1))
        assert "error" in result
        assert "Not a file" in result["error"]
