"""Tests for the IPC bridge (DocmakerAPI)."""

import json
from pathlib import Path
from unittest import mock

import pytest

from docmaker.models import (
    Annotation,
    ClassDef,
    EndpointDef,
    FieldDef,
    FileCategory,
    FileSymbols,
    FunctionDef,
    ImportDef,
    Language,
    Parameter,
    SourceFile,
    SymbolTable,
)


@pytest.fixture
def api():
    """Create a fresh DocmakerAPI instance with Qt/PySide6 mocked out."""
    from docmaker.app.ipc import DocmakerAPI

    obj = DocmakerAPI()
    return obj


@pytest.fixture
def symbol_table():
    """Build a SymbolTable with one class and one endpoint for detail tests."""
    st = SymbolTable()

    src_file = SourceFile(
        path=Path("/proj/UserController.java"),
        relative_path=Path("src/UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
        size_bytes=1024,
    )

    cls = ClassDef(
        name="UserController",
        file_path=Path("/proj/UserController.java"),
        line_number=10,
        end_line=80,
        package="com.example",
        superclass="BaseController",
        interfaces=["Serializable"],
        modifiers=["public"],
        docstring="Handles user requests.",
        annotations=[Annotation(name="RestController", arguments={"value": "/api"})],
        methods=[
            FunctionDef(
                name="getUsers",
                file_path=Path("/proj/UserController.java"),
                line_number=20,
                end_line=30,
                return_type="List<User>",
                parameters=[Parameter(name="page", type="int")],
                modifiers=["public"],
                docstring="List users.",
                annotations=[Annotation(name="GetMapping", arguments={"value": "/users"})],
            ),
        ],
        fields=[
            FieldDef(
                name="userService",
                line_number=12,
                type="UserService",
                modifiers=["private"],
                annotations=[Annotation(name="Autowired")],
            ),
        ],
    )

    endpoint = EndpointDef(
        http_method="GET",
        path="/users",
        handler_method="getUsers",
        handler_class="UserController",
        file_path=Path("/proj/UserController.java"),
        line_number=20,
        parameters=[Parameter(name="page", type="int", description="Page number")],
        request_body=None,
        response_type="List<User>",
        description="List all users",
    )

    symbols = FileSymbols(
        file=src_file,
        package="com.example",
        imports=[ImportDef(module="com.example.service.UserService")],
        classes=[cls],
        endpoints=[endpoint],
    )
    st.add_file_symbols(symbols)
    return st


# ---------------------------------------------------------------------------
# scan_project
# ---------------------------------------------------------------------------


class TestScanProject:
    def test_nonexistent_path_returns_error(self, api):
        result = json.loads(api.scan_project("/nonexistent/path/xyz"))
        assert "error" in result
        assert "does not exist" in result["error"]

    def test_file_path_returns_error(self, api, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hi")
        result = json.loads(api.scan_project(str(f)))
        assert "error" in result
        assert "not a directory" in result["error"]

    @mock.patch("docmaker.app.ipc.FileCrawler")
    @mock.patch("docmaker.app.ipc.DocmakerConfig.load")
    def test_successful_scan(self, mock_config_load, mock_crawler_cls, api, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()

        mock_config = mock.MagicMock()
        mock_config_load.return_value = mock_config

        fake_file = SourceFile(
            path=project / "Main.java",
            relative_path=Path("Main.java"),
            language=Language.JAVA,
            category=FileCategory.BACKEND,
            size_bytes=512,
        )
        mock_crawler_cls.return_value.crawl.return_value = [fake_file]

        result = json.loads(api.scan_project(str(project)))

        assert "error" not in result
        assert result["stats"]["totalFiles"] == 1
        assert result["stats"]["byLanguage"]["java"] == 1
        assert result["stats"]["byCategory"]["backend"] == 1
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "Main.java"
        assert result["files"][0]["size"] == 512
        assert result["projectPath"] == str(project.resolve())


# ---------------------------------------------------------------------------
# parse_only
# ---------------------------------------------------------------------------


class TestParseOnly:
    def test_nonexistent_path_returns_error(self, api):
        result = json.loads(api.parse_only("/nonexistent/path/xyz"))
        assert "error" in result
        assert "does not exist" in result["error"]

    @mock.patch("docmaker.app.ipc.GraphBuilder")
    @mock.patch("docmaker.app.ipc.get_parser_registry")
    @mock.patch("docmaker.app.ipc.FileCrawler")
    @mock.patch("docmaker.app.ipc.DocmakerConfig.load")
    def test_successful_parse(
        self, mock_config_load, mock_crawler_cls, mock_registry_fn, mock_graph_cls, api, tmp_path
    ):
        project = tmp_path / "proj"
        project.mkdir()

        mock_config = mock.MagicMock()
        mock_config_load.return_value = mock_config

        backend_file = SourceFile(
            path=project / "App.java",
            relative_path=Path("App.java"),
            language=Language.JAVA,
            category=FileCategory.BACKEND,
            size_bytes=256,
        )
        ignored_file = SourceFile(
            path=project / ".gitignore",
            relative_path=Path(".gitignore"),
            language=Language.UNKNOWN,
            category=FileCategory.IGNORE,
            size_bytes=32,
        )
        mock_crawler_cls.return_value.crawl.return_value = [backend_file, ignored_file]

        registry = mock.MagicMock()
        registry.can_parse.return_value = True
        mock_file_symbols = mock.MagicMock()
        registry.parse.return_value = mock_file_symbols
        mock_registry_fn.return_value = registry

        mock_graph = mock.MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [], "edges": []}
        mock_graph_cls.return_value.build.return_value = mock_graph

        result = json.loads(api.parse_only(str(project)))

        assert result["success"] is True
        assert "stats" in result
        assert "graph" in result
        # Ignored files should be filtered out
        registry.can_parse.assert_called_once_with(backend_file)

    @mock.patch("docmaker.app.ipc.GraphBuilder")
    @mock.patch("docmaker.app.ipc.get_parser_registry")
    @mock.patch("docmaker.app.ipc.FileCrawler")
    @mock.patch("docmaker.app.ipc.DocmakerConfig.load")
    def test_test_files_filtered_out(
        self, mock_config_load, mock_crawler_cls, mock_registry_fn, mock_graph_cls, api, tmp_path
    ):
        project = tmp_path / "proj"
        project.mkdir()
        mock_config_load.return_value = mock.MagicMock()

        test_file = SourceFile(
            path=project / "TestApp.java",
            relative_path=Path("TestApp.java"),
            language=Language.JAVA,
            category=FileCategory.TEST,
            size_bytes=128,
        )
        mock_crawler_cls.return_value.crawl.return_value = [test_file]

        registry = mock.MagicMock()
        mock_registry_fn.return_value = registry

        mock_graph = mock.MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [], "edges": []}
        mock_graph_cls.return_value.build.return_value = mock_graph

        result = json.loads(api.parse_only(str(project)))
        assert result["success"] is True
        # TEST category should be filtered, so parser never called
        registry.can_parse.assert_not_called()


# ---------------------------------------------------------------------------
# get_class_details
# ---------------------------------------------------------------------------


class TestGetClassDetails:
    def test_no_symbol_table_returns_error(self, api):
        result = json.loads(api.get_class_details("Foo"))
        assert "error" in result
        assert "No symbol table" in result["error"]

    def test_class_not_found_returns_error(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_class_details("NonExistentClass"))
        assert "error" in result
        assert "Class not found" in result["error"]

    def test_lookup_by_fqn(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_class_details("com.example.UserController"))
        assert result["name"] == "UserController"
        assert result["fqn"] == "com.example.UserController"
        assert result["superclass"] == "BaseController"
        assert result["interfaces"] == ["Serializable"]
        assert result["line"] == 10
        assert result["endLine"] == 80
        assert result["modifiers"] == ["public"]
        assert result["docstring"] == "Handles user requests."

    def test_lookup_by_short_name(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_class_details("UserController"))
        assert result["name"] == "UserController"
        assert result["fqn"] == "com.example.UserController"

    def test_methods_serialized(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_class_details("com.example.UserController"))
        assert len(result["methods"]) == 1
        m = result["methods"][0]
        assert m["name"] == "getUsers"
        assert m["returnType"] == "List<User>"
        assert m["line"] == 20
        assert m["modifiers"] == ["public"]
        assert m["docstring"] == "List users."
        assert len(m["parameters"]) == 1
        assert m["parameters"][0] == {"name": "page", "type": "int"}
        assert len(m["annotations"]) == 1
        assert m["annotations"][0]["name"] == "GetMapping"

    def test_fields_serialized(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_class_details("com.example.UserController"))
        assert len(result["fields"]) == 1
        f = result["fields"][0]
        assert f["name"] == "userService"
        assert f["type"] == "UserService"
        assert f["modifiers"] == ["private"]
        assert f["line"] == 12
        assert len(f["annotations"]) == 1
        assert f["annotations"][0]["name"] == "Autowired"


# ---------------------------------------------------------------------------
# get_endpoint_details
# ---------------------------------------------------------------------------


class TestGetEndpointDetails:
    def test_no_symbol_table_returns_error(self, api):
        result = json.loads(api.get_endpoint_details("GET:/users"))
        assert "error" in result
        assert "No symbol table" in result["error"]

    def test_endpoint_not_found_returns_error(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_endpoint_details("DELETE:/users"))
        assert "error" in result
        assert "Endpoint not found" in result["error"]

    def test_successful_lookup(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_endpoint_details("GET:/users"))
        assert result["httpMethod"] == "GET"
        assert result["path"] == "/users"
        assert result["handlerClass"] == "UserController"
        assert result["handlerMethod"] == "getUsers"
        assert result["line"] == 20
        assert result["responseType"] == "List<User>"
        assert result["description"] == "List all users"
        assert result["requestBody"] is None

    def test_parameters_serialized(self, api, symbol_table):
        api._symbol_table = symbol_table
        result = json.loads(api.get_endpoint_details("GET:/users"))
        assert len(result["parameters"]) == 1
        p = result["parameters"][0]
        assert p["name"] == "page"
        assert p["type"] == "int"
        assert p["description"] == "Page number"


# ---------------------------------------------------------------------------
# open_file
# ---------------------------------------------------------------------------


class TestOpenFile:
    def test_nonexistent_file_returns_error(self, api):
        result = json.loads(api.open_file("/no/such/file.txt", 0))
        assert "error" in result
        assert "does not exist" in result["error"]

    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_always_ask_returns_ask_user(self, mock_get_cmd, mock_load, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (None, "ask")

        result = json.loads(api.open_file(str(f), 1))
        assert result["askUser"] is True
        assert result["success"] is False

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_auto_detect_vscode(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (None, "auto")

        result = json.loads(api.open_file(str(f), 5))
        assert result["success"] is True
        assert result["editor"] == "vscode"
        mock_popen.assert_called_once_with(["code", "--goto", f"{f}:5"])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_auto_detect_vscode_no_line(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (None, "auto")

        result = json.loads(api.open_file(str(f), 0))
        assert result["success"] is True
        assert result["editor"] == "vscode"
        mock_popen.assert_called_once_with(["code", str(f)])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_auto_detect_falls_back_to_system(
        self, mock_get_cmd, mock_load, mock_popen, api, tmp_path
    ):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (None, "auto")

        # First Popen (vscode) raises FileNotFoundError, second (xdg-open) succeeds
        mock_popen.side_effect = [FileNotFoundError("code not found"), mock.MagicMock()]

        result = json.loads(api.open_file(str(f), 0))
        assert result["success"] is True
        assert result["editor"] == "system"

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_custom_editor_command(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (["nvim", "+{line}", "{file}"], "custom")

        result = json.loads(api.open_file(str(f), 42))
        assert result["success"] is True
        assert result["editor"] == "custom"
        mock_popen.assert_called_once_with(["nvim", "+42", str(f)])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_vscode_editor(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (["code", "--goto", "{file}:{line}"], "vscode")

        result = json.loads(api.open_file(str(f), 10))
        assert result["success"] is True
        assert result["editor"] == "vscode"
        mock_popen.assert_called_once_with(["code", "--goto", f"{f}:10"])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_idea_editor(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (["idea", "--line", "{line}", "{file}"], "idea")

        result = json.loads(api.open_file(str(f), 7))
        assert result["success"] is True
        assert result["editor"] == "idea"
        mock_popen.assert_called_once_with(["idea", "--line", "7", str(f)])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_sublime_editor(self, mock_get_cmd, mock_load, mock_popen, api, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (["subl", "{file}:{line}"], "sublime")

        result = json.loads(api.open_file(str(f), 3))
        assert result["success"] is True
        assert result["editor"] == "sublime"
        mock_popen.assert_called_once_with(["subl", f"{f}:3"])

    @mock.patch("docmaker.app.ipc.subprocess.Popen")
    @mock.patch("docmaker.app.ipc.load_settings")
    @mock.patch("docmaker.app.ipc.get_editor_command")
    def test_custom_editor_not_found_falls_back(
        self, mock_get_cmd, mock_load, mock_popen, api, tmp_path
    ):
        f = tmp_path / "test.py"
        f.write_text("pass")
        mock_load.return_value = {}
        mock_get_cmd.return_value = (["myeditor", "{file}"], "custom")

        # First call (custom) fails, second (system fallback) succeeds
        mock_popen.side_effect = [FileNotFoundError("myeditor not found"), mock.MagicMock()]

        result = json.loads(api.open_file(str(f), 0))
        assert result["success"] is True
        assert result["editor"] == "system"


# ---------------------------------------------------------------------------
# Settings operations
# ---------------------------------------------------------------------------


class TestSettingsOperations:
    @mock.patch("docmaker.app.ipc.load_settings")
    def test_get_settings(self, mock_load, api):
        mock_load.return_value = {"editor": {"preferredEditor": "vscode"}}
        result = json.loads(api.get_settings())
        assert result["editor"]["preferredEditor"] == "vscode"

    @mock.patch("docmaker.app.ipc.load_settings")
    def test_get_settings_error(self, mock_load, api):
        mock_load.side_effect = RuntimeError("disk error")
        result = json.loads(api.get_settings())
        assert "error" in result

    @mock.patch("docmaker.app.ipc.save_settings")
    def test_save_settings_ipc(self, mock_save, api):
        settings = {"editor": {"preferredEditor": "idea"}}
        result = json.loads(api.save_settings_ipc(json.dumps(settings)))
        assert result["success"] is True
        mock_save.assert_called_once_with(settings)

    @mock.patch("docmaker.app.ipc.save_settings")
    def test_save_settings_ipc_error(self, mock_save, api):
        mock_save.side_effect = OSError("write failed")
        result = json.loads(api.save_settings_ipc('{"bad": true}'))
        assert "error" in result

    def test_save_settings_ipc_invalid_json(self, api):
        result = json.loads(api.save_settings_ipc("not json"))
        assert "error" in result

    @mock.patch("docmaker.app.ipc.reset_settings")
    def test_reset_settings_ipc(self, mock_reset, api):
        mock_reset.return_value = {"editor": {"preferredEditor": "auto"}}
        result = json.loads(api.reset_settings_ipc())
        assert result["editor"]["preferredEditor"] == "auto"
        mock_reset.assert_called_once()

    @mock.patch("docmaker.app.ipc.reset_settings")
    def test_reset_settings_ipc_error(self, mock_reset, api):
        mock_reset.side_effect = RuntimeError("reset failed")
        result = json.loads(api.reset_settings_ipc())
        assert "error" in result


# ---------------------------------------------------------------------------
# get_project_info
# ---------------------------------------------------------------------------


class TestGetProjectInfo:
    def test_no_project_loaded(self, api):
        result = json.loads(api.get_project_info())
        assert result["loaded"] is False

    def test_project_loaded_no_symbol_table(self, api, tmp_path):
        api._current_project = tmp_path
        api._files = [mock.MagicMock(), mock.MagicMock()]
        result = json.loads(api.get_project_info())
        assert result["loaded"] is True
        assert result["path"] == str(tmp_path)
        assert result["name"] == tmp_path.name
        assert result["hasSymbolTable"] is False

    def test_project_loaded_with_symbol_table(self, api, symbol_table, tmp_path):
        api._current_project = tmp_path
        api._symbol_table = symbol_table
        api._files = []
        result = json.loads(api.get_project_info())
        assert result["loaded"] is True
        assert result["hasSymbolTable"] is True
        assert result["stats"]["classes"] == 1
        assert result["stats"]["endpoints"] == 1


# ---------------------------------------------------------------------------
# get_graph_data
# ---------------------------------------------------------------------------


class TestGetGraphData:
    def test_no_symbol_table_returns_error(self, api):
        result = json.loads(api.get_graph_data())
        assert "error" in result

    @mock.patch("docmaker.app.ipc.GraphBuilder")
    def test_returns_graph_dict(self, mock_builder_cls, api, symbol_table):
        api._symbol_table = symbol_table
        mock_graph = mock.MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [{"id": "a"}], "edges": []}
        mock_builder_cls.return_value.build.return_value = mock_graph

        result = json.loads(api.get_graph_data())
        assert result["nodes"] == [{"id": "a"}]
        assert result["edges"] == []
