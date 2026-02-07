"""Tests for the markdown generator."""

import tempfile
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


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def symbol_table():
    st = SymbolTable()
    sf = SourceFile(
        path=Path("/src/UserController.java"),
        relative_path=Path("src/main/UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )
    cls = ClassDef(
        name="UserController",
        file_path=Path("/src/UserController.java"),
        line_number=10,
        end_line=50,
        package="com.example",
        superclass="BaseController",
        interfaces=["Serializable"],
        annotations=[Annotation(name="RestController")],
        modifiers=["public"],
        docstring="Handles user operations.",
        fields=[
            FieldDef(name="userService", type="UserService", modifiers=["private"]),
        ],
        methods=[
            FunctionDef(
                name="getUser",
                file_path=Path("/src/UserController.java"),
                line_number=20,
                end_line=30,
                parameters=[Parameter(name="id", type="Long")],
                return_type="User",
                docstring="Get a user by ID.",
                annotations=[Annotation(name="GetMapping", arguments={"value": "/{id}"})],
                modifiers=["public"],
                source_code="public User getUser(Long id) {\n    return service.findById(id);\n}",
            )
        ],
    )
    endpoint = EndpointDef(
        http_method="GET",
        path="/api/users/{id}",
        handler_method="getUser",
        handler_class="UserController",
        file_path=Path("/src/UserController.java"),
        line_number=20,
        parameters=[
            Parameter(name="id", type="Long", description="@PathVariable id"),
        ],
        response_type="User",
        source_code="@GetMapping public User getUser(@PathVariable Long id) { return null; }",
    )
    func = FunctionDef(
        name="utilMethod",
        file_path=Path("/src/UserController.java"),
        line_number=55,
        end_line=60,
        return_type="void",
        docstring="A utility method.",
        source_code="void utilMethod() {}",
    )
    file_symbols = FileSymbols(
        file=sf,
        package="com.example",
        imports=[
            ImportDef(module="com.example.model.User"),
            ImportDef(module="org.springframework.web.bind.annotation.RestController"),
        ],
        classes=[cls],
        functions=[func],
        endpoints=[endpoint],
    )
    st.add_file_symbols(file_symbols)
    return st


def test_generate_all_creates_files(output_dir, symbol_table):
    """Test that generate_all creates markdown files."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    assert len(generated) >= 1
    assert all(p.exists() for p in generated)


def test_generate_all_mirrors_structure(output_dir, symbol_table):
    """Test that files mirror source structure when enabled."""
    config = OutputConfig(output_dir=output_dir, mirror_source_structure=True)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    doc_files = [p for p in generated if p.name == "UserController.md"]
    assert len(doc_files) == 1
    assert "src" in str(doc_files[0])


def test_generate_all_flat_structure(output_dir, symbol_table):
    """Test flat output when mirror_source_structure is disabled."""
    config = OutputConfig(output_dir=output_dir, mirror_source_structure=False)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    doc_files = [p for p in generated if p.name == "UserController.md"]
    assert len(doc_files) == 1
    assert doc_files[0].parent == output_dir


def test_generate_all_creates_index(output_dir, symbol_table):
    """Test that an index file is generated."""
    config = OutputConfig(output_dir=output_dir, generate_index=True)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    index_path = output_dir / "index.md"
    assert index_path in generated
    assert index_path.exists()


def test_generate_all_creates_endpoints_index(output_dir, symbol_table):
    """Test that an endpoints index is generated when endpoints exist."""
    config = OutputConfig(output_dir=output_dir, generate_index=True)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    endpoints_path = output_dir / "endpoints.md"
    assert endpoints_path in generated


def test_generate_all_no_index(output_dir, symbol_table):
    """Test no index when generate_index is disabled."""
    config = OutputConfig(output_dir=output_dir, generate_index=False)
    gen = MarkdownGenerator(config, symbol_table)
    generated = gen.generate_all()

    assert output_dir / "index.md" not in generated


def test_file_doc_contains_frontmatter(output_dir, symbol_table):
    """Test that generated docs contain YAML frontmatter."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert doc.startswith("---")
    assert "title: UserController" in doc
    assert "language: java" in doc
    assert "category: backend" in doc


def test_file_doc_contains_class(output_dir, symbol_table):
    """Test that class documentation is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "## Class: `UserController`" in doc
    assert "Handles user operations." in doc
    assert "`@RestController`" in doc


def test_file_doc_contains_method(output_dir, symbol_table):
    """Test that method documentation is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "#### `getUser()`" in doc
    assert "Get a user by ID." in doc


def test_file_doc_contains_fields(output_dir, symbol_table):
    """Test that field documentation is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "`userService`" in doc


def test_file_doc_contains_imports(output_dir, symbol_table):
    """Test that imports section is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "## Imports" in doc


def test_file_doc_contains_endpoints(output_dir, symbol_table):
    """Test that endpoint documentation is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "## REST Endpoints" in doc
    assert "`/api/users/{id}`" in doc


def test_file_doc_contains_function(output_dir, symbol_table):
    """Test that standalone function documentation is present."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "## Function: `utilMethod()`" in doc


def test_file_doc_source_snippets_enabled(output_dir, symbol_table):
    """Test that source code snippets are included when enabled."""
    config = OutputConfig(output_dir=output_dir, include_source_snippets=True)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "<details>" in doc
    assert "Source Code" in doc


def test_file_doc_source_snippets_disabled(output_dir, symbol_table):
    """Test that source snippets are excluded when disabled."""
    config = OutputConfig(output_dir=output_dir, include_source_snippets=False)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "<details>" not in doc


def test_truncate_source():
    """Test source truncation."""
    config = OutputConfig(max_snippet_lines=3)
    st = SymbolTable()
    gen = MarkdownGenerator(config, st)

    long_source = "\n".join(f"line {i}" for i in range(10))
    result = gen._truncate_source(long_source)
    assert result.endswith("// ... truncated")
    assert result.count("\n") <= 4  # 3 lines + truncated line


def test_truncate_source_short():
    """Test that short source is not truncated."""
    config = OutputConfig(max_snippet_lines=50)
    st = SymbolTable()
    gen = MarkdownGenerator(config, st)

    short_source = "line 1\nline 2"
    result = gen._truncate_source(short_source)
    assert result == short_source


def test_format_annotation():
    """Test annotation formatting."""
    config = OutputConfig()
    st = SymbolTable()
    gen = MarkdownGenerator(config, st)

    simple = Annotation(name="Override")
    assert gen._format_annotation(simple) == "`@Override`"

    with_args = Annotation(name="GetMapping", arguments={"value": "/users"})
    result = gen._format_annotation(with_args)
    assert result == '`@GetMapping(value="/users")`'


def test_get_method_badge():
    """Test HTTP method badges."""
    config = OutputConfig()
    st = SymbolTable()
    gen = MarkdownGenerator(config, st)

    assert "`GET`" in gen._get_method_badge("GET")
    assert "`POST`" in gen._get_method_badge("POST")
    assert "`DELETE`" in gen._get_method_badge("DELETE")
    assert "`UNKNOWN`" in gen._get_method_badge("UNKNOWN")


def test_generate_all_empty_symbol_table(output_dir):
    """Test generating with empty symbol table."""
    config = OutputConfig(output_dir=output_dir, generate_index=True)
    st = SymbolTable()
    gen = MarkdownGenerator(config, st)
    generated = gen.generate_all()

    # Should still generate index
    assert output_dir / "index.md" in generated


def test_endpoints_index_not_generated_without_endpoints(output_dir):
    """Test that endpoints index is not generated when there are no endpoints."""
    st = SymbolTable()
    sf = SourceFile(
        path=Path("/src/util.py"),
        relative_path=Path("util.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    cls = ClassDef(
        name="Util",
        file_path=Path("/src/util.py"),
        line_number=1,
        end_line=10,
    )
    st.add_file_symbols(FileSymbols(file=sf, classes=[cls]))

    config = OutputConfig(output_dir=output_dir, generate_index=True)
    gen = MarkdownGenerator(config, st)
    generated = gen.generate_all()

    assert output_dir / "endpoints.md" not in generated


def test_index_categorizes_classes(output_dir, symbol_table):
    """Test that the index properly categorizes classes."""
    config = OutputConfig(output_dir=output_dir, generate_index=True)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    index = (output_dir / "index.md").read_text()
    assert "## Controllers" in index
    assert "[[UserController]]" in index


def test_frontmatter_tags(output_dir, symbol_table):
    """Test that frontmatter includes correct tags."""
    config = OutputConfig(output_dir=output_dir)
    gen = MarkdownGenerator(config, symbol_table)
    gen.generate_all()

    doc = (output_dir / "src" / "main" / "UserController.md").read_text()
    assert "controller" in doc
    assert "java" in doc
    assert "backend" in doc
