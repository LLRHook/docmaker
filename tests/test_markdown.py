"""Tests for the markdown generator."""

from pathlib import Path

import pytest

from docmaker.config import OutputConfig
from docmaker.generator.markdown import MarkdownGenerator
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def output_config(tmp_path):
    return OutputConfig(
        output_dir=tmp_path / "docs",
        mirror_source_structure=True,
        include_source_snippets=True,
        max_snippet_lines=50,
        generate_index=True,
    )


@pytest.fixture
def source_file():
    return SourceFile(
        path=Path("/project/src/main/java/com/example/UserController.java"),
        relative_path=Path("src/main/java/com/example/UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )


@pytest.fixture
def method_def():
    return FunctionDef(
        name="getUsers",
        file_path=Path("/project/src/main/java/com/example/UserController.java"),
        line_number=20,
        end_line=30,
        parameters=[
            Parameter(name="page", type="int", description="Page number"),
            Parameter(name="size", type="int"),
        ],
        return_type="List<User>",
        docstring="Returns a paginated list of users.",
        annotations=[Annotation(name="GetMapping", arguments={"value": "/users"})],
        modifiers=["public"],
        source_code=(
            "public List<User> getUsers(int page, int size) {\n"
            "    return userService.findAll(page, size);\n}"
        ),
    )


@pytest.fixture
def class_def(method_def):
    return ClassDef(
        name="UserController",
        file_path=Path("/project/src/main/java/com/example/UserController.java"),
        line_number=10,
        end_line=50,
        package="com.example",
        superclass="BaseController",
        interfaces=["Controller"],
        annotations=[
            Annotation(name="RestController"),
            Annotation(name="RequestMapping", arguments={"value": "/api"}),
        ],
        modifiers=["public"],
        docstring="Handles user-related REST endpoints.",
        methods=[method_def],
        fields=[
            FieldDef(
                name="userService",
                type="UserService",
                annotations=[Annotation(name="Autowired")],
                modifiers=["private"],
                line_number=12,
            ),
        ],
    )


@pytest.fixture
def endpoint_def():
    return EndpointDef(
        http_method="GET",
        path="/api/users/{id}",
        handler_method="getUserById",
        handler_class="UserController",
        file_path=Path("/project/src/main/java/com/example/UserController.java"),
        line_number=35,
        parameters=[
            Parameter(name="id", type="Long", description="@PathVariable user id"),
        ],
        response_type="User",
        description="Get a single user by ID.",
        source_code=(
            "public User getUserById(@PathVariable Long id) {\n"
            "    return userService.findById(id);\n}"
        ),
    )


@pytest.fixture
def file_symbols(source_file, class_def, endpoint_def):
    return FileSymbols(
        file=source_file,
        package="com.example",
        imports=[
            ImportDef(module="com.example.service.UserService"),
            ImportDef(module="org.springframework.web.bind.annotation.RestController"),
        ],
        classes=[class_def],
        endpoints=[endpoint_def],
    )


@pytest.fixture
def symbol_table(file_symbols, class_def, endpoint_def):
    st = SymbolTable()
    st.add_file_symbols(file_symbols)
    return st


@pytest.fixture
def generator(output_config, symbol_table):
    return MarkdownGenerator(output_config, symbol_table)


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_frontmatter_has_yaml_delimiters(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert fm.startswith("---\n")
        assert "\n---\n" in fm

    def test_frontmatter_includes_title(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "title: UserController" in fm

    def test_frontmatter_includes_path(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "path: src/main/java/com/example/UserController.java" in fm

    def test_frontmatter_includes_language(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "language: java" in fm

    def test_frontmatter_includes_category(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "category: backend" in fm

    def test_frontmatter_includes_generated_timestamp(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "generated:" in fm

    def test_frontmatter_tags_include_controller(self, generator, file_symbols):
        fm = generator._generate_frontmatter(file_symbols)
        assert "controller" in fm

    def test_frontmatter_tags_for_service_annotation(self, generator, source_file):
        cls = ClassDef(
            name="UserService",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Service")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "service" in fm

    def test_frontmatter_tags_for_repository_annotation(self, generator, source_file):
        cls = ClassDef(
            name="UserRepo",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Repository")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "repository" in fm

    def test_frontmatter_tags_for_entity_annotation(self, generator, source_file):
        cls = ClassDef(
            name="User",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Entity")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "entity" in fm

    def test_frontmatter_tags_for_configuration_annotation(self, generator, source_file):
        cls = ClassDef(
            name="AppConfig",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Configuration")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "configuration" in fm

    def test_frontmatter_tags_for_dataclass_annotation(self, generator, source_file):
        cls = ClassDef(
            name="DataObj",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="dataclass")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "dataclass" in fm

    def test_frontmatter_tags_for_interface_annotation(self, generator, source_file):
        cls = ClassDef(
            name="IService",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="interface")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "interface" in fm

    def test_frontmatter_tags_for_component_annotation(self, generator, source_file):
        cls = ClassDef(
            name="MyComponent",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Component")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "component" in fm

    def test_frontmatter_tags_for_injectable_annotation(self, generator, source_file):
        cls = ClassDef(
            name="MyInjectable",
            file_path=source_file.path,
            line_number=1,
            end_line=10,
            annotations=[Annotation(name="Injectable")],
        )
        fs = FileSymbols(file=source_file, classes=[cls])
        fm = generator._generate_frontmatter(fs)
        assert "injectable" in fm


# ---------------------------------------------------------------------------
# File documentation
# ---------------------------------------------------------------------------


class TestFileDoc:
    def test_file_doc_has_title(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "# UserController" in doc

    def test_file_doc_has_file_info_callout(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "> [!info] File Info" in doc
        assert "**Path:**" in doc
        assert "**Language:** java" in doc
        assert "**Category:** backend" in doc

    def test_file_doc_shows_package(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "**Package:** `com.example`" in doc

    def test_file_doc_no_package_when_none(self, generator, source_file):
        fs = FileSymbols(file=source_file)
        doc = generator._generate_file_doc(fs)
        assert "**Package:**" not in doc

    def test_file_doc_includes_imports_section(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "## Imports" in doc
        assert "UserService" in doc

    def test_file_doc_no_imports_section_when_empty(self, generator, source_file):
        fs = FileSymbols(file=source_file)
        doc = generator._generate_file_doc(fs)
        assert "## Imports" not in doc

    def test_file_doc_truncates_imports_over_20(self, generator, source_file):
        imports = [ImportDef(module=f"com.example.pkg{i}.Class{i}") for i in range(25)]
        fs = FileSymbols(file=source_file, imports=imports)
        doc = generator._generate_file_doc(fs)
        assert "... and 5 more" in doc

    def test_file_doc_includes_class_section(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "## Class: `UserController`" in doc

    def test_file_doc_includes_endpoints_section(self, generator, file_symbols):
        doc = generator._generate_file_doc(file_symbols)
        assert "## REST Endpoints" in doc

    def test_file_doc_includes_function_section(self, generator, source_file):
        func = FunctionDef(
            name="helper_func",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            docstring="A helper function.",
        )
        fs = FileSymbols(file=source_file, functions=[func])
        doc = generator._generate_file_doc(fs)
        assert "## Function: `helper_func()`" in doc

    def test_file_doc_no_endpoints_section_when_empty(self, generator, source_file):
        fs = FileSymbols(file=source_file)
        doc = generator._generate_file_doc(fs)
        assert "## REST Endpoints" not in doc


# ---------------------------------------------------------------------------
# Class documentation
# ---------------------------------------------------------------------------


class TestClassDoc:
    def test_class_heading(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "## Class: `UserController`" in doc

    def test_class_annotations(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "**Annotations:**" in doc
        assert "`@RestController`" in doc
        assert '`@RequestMapping(value="/api")`' in doc

    def test_class_modifiers(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "**Modifiers:** `public`" in doc

    def test_class_extends(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "**Extends:**" in doc
        assert "BaseController" in doc

    def test_class_implements(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "**Implements:**" in doc

    def test_class_docstring(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "> Handles user-related REST endpoints." in doc

    def test_class_fields_table(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "### Fields" in doc
        assert "| Name | Type | Modifiers | Annotations |" in doc
        assert "`userService`" in doc
        assert "`@Autowired`" in doc

    def test_class_methods_section(self, generator, class_def, file_symbols):
        doc = generator._generate_class_doc(class_def, file_symbols)
        assert "### Methods" in doc
        assert "`getUsers()`" in doc

    def test_class_no_annotations_section_when_empty(self, generator, source_file, file_symbols):
        cls = ClassDef(
            name="Plain",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_class_doc(cls, file_symbols)
        assert "**Annotations:**" not in doc

    def test_class_no_modifiers_section_when_empty(self, generator, source_file, file_symbols):
        cls = ClassDef(
            name="Plain",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_class_doc(cls, file_symbols)
        assert "**Modifiers:**" not in doc

    def test_class_no_superclass_section_when_none(self, generator, source_file, file_symbols):
        cls = ClassDef(
            name="Plain",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_class_doc(cls, file_symbols)
        assert "**Extends:**" not in doc

    def test_class_no_interfaces_section_when_empty(self, generator, source_file, file_symbols):
        cls = ClassDef(
            name="Plain",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_class_doc(cls, file_symbols)
        assert "**Implements:**" not in doc

    def test_class_no_docstring_when_none(self, generator, source_file, file_symbols):
        cls = ClassDef(
            name="Plain",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_class_doc(cls, file_symbols)
        # Should not have a blockquote for docstring
        lines = doc.strip().split("\n")
        # The only line starting with > should not exist (no docstring)
        assert not any(line.startswith("> ") and "info" not in line for line in lines)


# ---------------------------------------------------------------------------
# Method documentation
# ---------------------------------------------------------------------------


class TestMethodDoc:
    def test_method_heading(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "#### `getUsers()`" in doc

    def test_method_annotations(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "**Annotations:**" in doc
        assert '`@GetMapping(value="/users")`' in doc

    def test_method_modifiers(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "**Modifiers:** `public`" in doc

    def test_method_return_type(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "**Returns:**" in doc

    def test_method_docstring(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "> Returns a paginated list of users." in doc

    def test_method_parameters_table(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "**Parameters:**" in doc
        assert "| Name | Type | Description |" in doc
        assert "`page`" in doc
        assert "Page number" in doc
        assert "`size`" in doc

    def test_method_line_number(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "Line 20" in doc

    def test_method_source_snippet_included(self, generator, method_def, class_def, file_symbols):
        doc = generator._generate_method_doc(method_def, class_def, file_symbols)
        assert "<details>" in doc
        assert "<summary>Source Code</summary>" in doc
        assert "```java" in doc
        assert "userService.findAll" in doc

    def test_method_no_source_snippet_when_disabled(
        self, tmp_path, symbol_table, method_def, class_def, file_symbols
    ):
        config = OutputConfig(
            output_dir=tmp_path / "docs",
            include_source_snippets=False,
        )
        gen = MarkdownGenerator(config, symbol_table)
        doc = gen._generate_method_doc(method_def, class_def, file_symbols)
        assert "<details>" not in doc

    def test_method_no_annotations_when_empty(self, generator, class_def, file_symbols):
        method = FunctionDef(
            name="simple",
            file_path=class_def.file_path,
            line_number=1,
            end_line=3,
        )
        doc = generator._generate_method_doc(method, class_def, file_symbols)
        assert "**Annotations:**" not in doc

    def test_method_param_with_no_description(self, generator, class_def, file_symbols):
        method = FunctionDef(
            name="noDesc",
            file_path=class_def.file_path,
            line_number=1,
            end_line=3,
            parameters=[Parameter(name="x", type="int")],
        )
        doc = generator._generate_method_doc(method, class_def, file_symbols)
        assert "| `x` |" in doc
        assert "| - |" in doc


# ---------------------------------------------------------------------------
# Function documentation
# ---------------------------------------------------------------------------


class TestFunctionDoc:
    def test_function_heading(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calculate",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "## Function: `calculate()`" in doc

    def test_function_annotations(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calc",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            annotations=[Annotation(name="staticmethod")],
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "`@staticmethod`" in doc

    def test_function_return_type(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calc",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            return_type="int",
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "**Returns:**" in doc

    def test_function_docstring(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calc",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            docstring="Computes a value.",
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "> Computes a value." in doc

    def test_function_parameters(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calc",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            parameters=[
                Parameter(name="a", type="int", description="First operand"),
                Parameter(name="b", type="int", description="Second operand"),
            ],
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "`a`" in doc
        assert "`b`" in doc
        assert "First operand" in doc

    def test_function_source_snippet(self, generator, source_file, file_symbols):
        func = FunctionDef(
            name="calc",
            file_path=source_file.path,
            line_number=1,
            end_line=5,
            source_code="def calc():\n    return 42",
        )
        doc = generator._generate_function_doc(func, file_symbols)
        assert "```java" in doc
        assert "return 42" in doc


# ---------------------------------------------------------------------------
# Endpoint documentation
# ---------------------------------------------------------------------------


class TestEndpointDoc:
    def test_endpoint_heading_with_badge(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "🟢 `GET`" in doc
        assert "`/api/users/{id}`" in doc

    def test_endpoint_description(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "> Get a single user by ID." in doc

    def test_endpoint_handler_table(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "| Property | Value |" in doc
        assert "**Handler**" in doc

    def test_endpoint_response_type(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "**Response**" in doc

    def test_endpoint_path_parameters(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "#### Path Parameters" in doc
        assert "`id`" in doc

    def test_endpoint_request_example(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "#### Request Example" in doc
        assert "```http" in doc
        assert "GET /api/users/<id>" in doc

    def test_endpoint_response_example(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "#### Response Example" in doc
        assert "**200 OK**" in doc

    def test_endpoint_source_snippet(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "<summary>Handler Source Code</summary>" in doc
        assert "userService.findById" in doc

    def test_endpoint_line_reference(self, generator, endpoint_def, file_symbols):
        doc = generator._generate_endpoint_doc(endpoint_def, file_symbols)
        assert "UserController.java:35" in doc

    def test_endpoint_no_description_when_none(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="DELETE",
            path="/api/users/{id}",
            handler_method="deleteUser",
            handler_class="UserController",
            file_path=Path("/test.java"),
            line_number=1,
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "🔴 `DELETE`" in doc
        # No blockquote for description
        lines = [line for line in doc.split("\n") if line.startswith("> ")]
        assert len(lines) == 0

    def test_endpoint_query_parameters(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="GET",
            path="/api/users",
            handler_method="search",
            handler_class="UserController",
            file_path=Path("/test.java"),
            line_number=1,
            parameters=[
                Parameter(name="q", type="String", description="@RequestParam search query"),
                Parameter(
                    name="limit",
                    type="int",
                    description="@RequestParam required=true max results",
                ),
            ],
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "#### Query Parameters" in doc
        assert "`q`" in doc
        assert "`limit`" in doc

    def test_endpoint_request_body(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="POST",
            path="/api/users",
            handler_method="createUser",
            handler_class="UserController",
            file_path=Path("/test.java"),
            line_number=1,
            request_body="UserDTO",
            parameters=[
                Parameter(name="body", type="UserDTO", description="@RequestBody user data"),
            ],
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "**Request Body**" in doc
        assert "Content-Type: application/json" in doc

    def test_endpoint_post_badge(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="POST",
            path="/test",
            handler_method="create",
            handler_class="X",
            file_path=Path("/t.java"),
            line_number=1,
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "🟡 `POST`" in doc

    def test_endpoint_put_badge(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="PUT",
            path="/test",
            handler_method="update",
            handler_class="X",
            file_path=Path("/t.java"),
            line_number=1,
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "🔵 `PUT`" in doc

    def test_endpoint_patch_badge(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="PATCH",
            path="/test",
            handler_method="patch",
            handler_class="X",
            file_path=Path("/t.java"),
            line_number=1,
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "🟣 `PATCH`" in doc

    def test_endpoint_unknown_method_badge(self, generator, file_symbols):
        ep = EndpointDef(
            http_method="OPTIONS",
            path="/test",
            handler_method="options",
            handler_class="X",
            file_path=Path("/t.java"),
            line_number=1,
        )
        doc = generator._generate_endpoint_doc(ep, file_symbols)
        assert "`OPTIONS`" in doc


# ---------------------------------------------------------------------------
# WikiLinks
# ---------------------------------------------------------------------------


class TestWikiLinks:
    def test_import_link_for_known_class(self, generator):
        # UserController is in the symbol table via class_index
        link = generator._get_import_link("com.example.UserController")
        assert "[[UserController]]" in link

    def test_import_link_for_unknown_class(self, generator):
        link = generator._get_import_link("com.external.Unknown")
        assert link == "`com.external.Unknown`"

    def test_import_link_for_wildcard(self, generator):
        link = generator._get_import_link("com.example.*")
        assert link == "`com.example.*`"


# ---------------------------------------------------------------------------
# Source snippets
# ---------------------------------------------------------------------------


class TestSourceSnippets:
    def test_truncate_short_source(self, generator):
        source = "line1\nline2\nline3"
        result = generator._truncate_source(source)
        assert result == source

    def test_truncate_long_source(self, tmp_path, symbol_table):
        config = OutputConfig(output_dir=tmp_path, max_snippet_lines=3)
        gen = MarkdownGenerator(config, symbol_table)
        source = "\n".join(f"line {i}" for i in range(10))
        result = gen._truncate_source(source)
        assert result.endswith("// ... truncated")
        assert "line 0" in result
        assert "line 2" in result
        assert "line 3" not in result


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------


class TestIndexGeneration:
    @pytest.fixture(autouse=True)
    def _ensure_output_dir(self, generator):
        generator.output_dir.mkdir(parents=True, exist_ok=True)

    def test_generate_index_creates_file(self, generator):
        index_path = generator._generate_index()
        assert index_path.exists()
        assert index_path.name == "index.md"

    def test_generate_index_has_frontmatter(self, generator):
        index_path = generator._generate_index()
        content = index_path.read_text()
        assert content.startswith("---\n")
        assert "title: Documentation Index" in content

    def test_generate_index_has_statistics(self, generator):
        index_path = generator._generate_index()
        content = index_path.read_text()
        assert "## Statistics" in content
        assert "**Total Files:**" in content
        assert "**Total Classes:**" in content
        assert "**Total Endpoints:**" in content

    def test_generate_index_categorizes_controllers(self, generator):
        index_path = generator._generate_index()
        content = index_path.read_text()
        assert "## Controllers" in content
        assert "[[UserController]]" in content

    def test_generate_endpoints_index_creates_file(self, generator):
        ep_path = generator._generate_endpoints_index()
        assert ep_path is not None
        assert ep_path.exists()
        assert ep_path.name == "endpoints.md"

    def test_generate_endpoints_index_has_frontmatter(self, generator):
        ep_path = generator._generate_endpoints_index()
        content = ep_path.read_text()
        assert "title: API Endpoints" in content

    def test_generate_endpoints_index_has_table(self, generator):
        ep_path = generator._generate_endpoints_index()
        content = ep_path.read_text()
        assert "| Method | Path | Handler |" in content
        assert "`/api/users/{id}`" in content

    def test_generate_endpoints_index_returns_none_when_no_endpoints(self, tmp_path):
        config = OutputConfig(output_dir=tmp_path / "docs")
        st = SymbolTable()
        gen = MarkdownGenerator(config, st)
        result = gen._generate_endpoints_index()
        assert result is None


# ---------------------------------------------------------------------------
# generate_all integration
# ---------------------------------------------------------------------------


class TestGenerateAll:
    def test_generate_all_creates_files(self, generator):
        paths = generator.generate_all()
        assert len(paths) > 0
        assert all(p.exists() for p in paths)
        assert all(p.suffix == ".md" for p in paths)

    def test_generate_all_includes_index(self, generator):
        paths = generator.generate_all()
        names = [p.name for p in paths]
        assert "index.md" in names
        assert "endpoints.md" in names

    def test_generate_all_mirrors_source_structure(self, generator):
        paths = generator.generate_all()
        doc_paths = [p for p in paths if p.name == "UserController.md"]
        assert len(doc_paths) == 1
        # Should mirror source structure: src/main/java/com/example/UserController.md
        assert "src" in str(doc_paths[0])

    def test_generate_all_flat_structure(self, tmp_path, symbol_table):
        config = OutputConfig(
            output_dir=tmp_path / "docs",
            mirror_source_structure=False,
            generate_index=False,
        )
        gen = MarkdownGenerator(config, symbol_table)
        paths = gen.generate_all()
        doc_paths = [p for p in paths if p.name == "UserController.md"]
        assert len(doc_paths) == 1
        # Should be directly under output_dir
        assert doc_paths[0].parent == tmp_path / "docs"

    def test_generate_all_no_index_when_disabled(self, tmp_path, symbol_table):
        config = OutputConfig(
            output_dir=tmp_path / "docs",
            generate_index=False,
        )
        gen = MarkdownGenerator(config, symbol_table)
        paths = gen.generate_all()
        names = [p.name for p in paths]
        assert "index.md" not in names
        assert "endpoints.md" not in names

    def test_generate_all_creates_output_dir(self, generator, output_config):
        assert not output_config.output_dir.exists()
        generator.generate_all()
        assert output_config.output_dir.exists()


# ---------------------------------------------------------------------------
# Annotation formatting
# ---------------------------------------------------------------------------


class TestFormatAnnotation:
    def test_simple_annotation(self, generator):
        ann = Annotation(name="Override")
        assert generator._format_annotation(ann) == "`@Override`"

    def test_annotation_with_arguments(self, generator):
        ann = Annotation(name="GetMapping", arguments={"value": "/users"})
        result = generator._format_annotation(ann)
        assert result == '`@GetMapping(value="/users")`'


# ---------------------------------------------------------------------------
# HTTP method badges
# ---------------------------------------------------------------------------


class TestMethodBadges:
    def test_get_badge(self, generator):
        assert generator._get_method_badge("GET") == "🟢 `GET`"

    def test_post_badge(self, generator):
        assert generator._get_method_badge("POST") == "🟡 `POST`"

    def test_put_badge(self, generator):
        assert generator._get_method_badge("PUT") == "🔵 `PUT`"

    def test_delete_badge(self, generator):
        assert generator._get_method_badge("DELETE") == "🔴 `DELETE`"

    def test_patch_badge(self, generator):
        assert generator._get_method_badge("PATCH") == "🟣 `PATCH`"

    def test_unknown_badge(self, generator):
        assert generator._get_method_badge("HEAD") == "`HEAD`"


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------


class TestOutputPath:
    def test_output_path_mirrors_structure(self, generator, file_symbols):
        path = generator._get_output_path(file_symbols)
        assert path.name == "UserController.md"
        assert "src/main/java/com/example" in str(path)

    def test_output_path_flat(self, tmp_path, symbol_table, file_symbols):
        config = OutputConfig(
            output_dir=tmp_path / "docs",
            mirror_source_structure=False,
        )
        gen = MarkdownGenerator(config, symbol_table)
        path = gen._get_output_path(file_symbols)
        assert path == tmp_path / "docs" / "UserController.md"
