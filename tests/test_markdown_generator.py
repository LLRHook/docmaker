"""Tests for Obsidian vault markdown generation."""

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
def output_dir(tmp_path):
    return tmp_path / "docs"


@pytest.fixture
def output_config(output_dir):
    return OutputConfig(
        output_dir=output_dir,
        mirror_source_structure=True,
        include_source_snippets=False,
        generate_index=True,
        generate_moc=True,
    )


def _make_source_file(relative_path: str, language=Language.JAVA, category=FileCategory.BACKEND):
    rel = Path(relative_path)
    return SourceFile(
        path=Path("/project") / rel,
        relative_path=rel,
        language=language,
        category=category,
    )


def _make_symbol_table(*file_symbols_list: FileSymbols) -> SymbolTable:
    st = SymbolTable()
    for fs in file_symbols_list:
        st.add_file_symbols(fs)
    return st


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


# ---------------------------------------------------------------------------
# Obsidian frontmatter tests
# ---------------------------------------------------------------------------


class TestFrontmatter:
    """Test YAML frontmatter generation for Obsidian compatibility."""

    def test_tags_use_yaml_list_format(self, output_config):
        """Obsidian requires tags as a YAML list, not inline array."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="Service")],
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        assert "tags:" in content
        assert "  - java" in content
        assert "  - backend" in content
        assert "  - service" in content
        # Should NOT use inline array format
        assert "tags: [" not in content

    def test_aliases_include_class_names(self, output_config):
        """Class names should appear as aliases for WikiLink resolution."""
        fs = FileSymbols(
            file=_make_source_file("src/UserController.java"),
            package="com.example.controller",
            classes=[
                ClassDef(
                    name="UserController",
                    file_path=Path("/project/src/UserController.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="RestController")],
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        assert "aliases:" in content
        assert "  - UserController" in content

    def test_multiple_classes_all_aliased(self, output_config):
        """Files with multiple classes should alias all of them."""
        fs = FileSymbols(
            file=_make_source_file("src/Models.java"),
            package="com.example.model",
            classes=[
                ClassDef(
                    name="User",
                    file_path=Path("/project/src/Models.java"),
                    line_number=1,
                    end_line=20,
                ),
                ClassDef(
                    name="Address",
                    file_path=Path("/project/src/Models.java"),
                    line_number=22,
                    end_line=40,
                ),
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        assert "  - User" in content
        assert "  - Address" in content

    def test_no_aliases_when_no_classes(self, output_config):
        """Files without classes should not have an aliases section."""
        fs = FileSymbols(
            file=_make_source_file("src/utils.py", language=Language.PYTHON),
            functions=[
                FunctionDef(
                    name="helper",
                    file_path=Path("/project/src/utils.py"),
                    line_number=1,
                    end_line=5,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        assert "aliases:" not in content

    def test_package_in_frontmatter(self, output_config):
        """Package should appear in frontmatter when available."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        assert "package: com.example.service" in content

    def test_frontmatter_has_valid_yaml_delimiters(self, output_config):
        """Frontmatter must start with --- and end with ---."""
        fs = FileSymbols(
            file=_make_source_file("src/App.java"),
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_frontmatter(fs)

        lines = content.strip().split("\n")
        assert lines[0] == "---"
        assert lines[-1] == "---"


# ---------------------------------------------------------------------------
# MOC generation tests
# ---------------------------------------------------------------------------


class TestMOCGeneration:
    """Test Map of Content (MOC) index page generation."""

    def test_moc_generated_per_package(self, output_config, output_dir):
        """Each package should get its own MOC page."""
        fs1 = FileSymbols(
            file=_make_source_file("src/main/java/com/example/service/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/main/java/com/example/service/UserService.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="Service")],
                )
            ],
        )
        fs2 = FileSymbols(
            file=_make_source_file("src/main/java/com/example/model/User.java"),
            package="com.example.model",
            classes=[
                ClassDef(
                    name="User",
                    file_path=Path("/project/src/main/java/com/example/model/User.java"),
                    line_number=1,
                    end_line=30,
                    annotations=[Annotation(name="Entity")],
                )
            ],
        )

        st = _make_symbol_table(fs1, fs2)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        # Should have MOC files
        moc_files = [f for f in generated if "MOC" in f.name]
        assert len(moc_files) >= 2

    def test_moc_contains_class_wikilinks(self, output_config, output_dir):
        """MOC pages should contain WikiLinks to classes in the package."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="Service")],
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        moc_files = [f for f in generated if "MOC" in f.name]
        assert moc_files, "Expected at least one MOC file"

        # Find the MOC for the service package specifically
        service_moc = None
        for moc in moc_files:
            if "service" in moc.name:
                service_moc = moc.read_text()
                break

        assert service_moc is not None
        assert "[[UserService]]" in service_moc

    def test_moc_has_frontmatter_tags(self, output_config, output_dir):
        """MOC pages should have MOC and package tags in frontmatter."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        moc_files = [f for f in generated if "MOC" in f.name]
        assert moc_files

        for moc_path in moc_files:
            content = moc_path.read_text()
            assert "  - MOC" in content
            assert "  - package" in content

    def test_moc_shows_sub_packages(self, output_config, output_dir):
        """MOC pages should link to child packages."""
        fs1 = FileSymbols(
            file=_make_source_file("src/service/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/service/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        fs2 = FileSymbols(
            file=_make_source_file("src/model/User.java"),
            package="com.example.model",
            classes=[
                ClassDef(
                    name="User",
                    file_path=Path("/project/src/model/User.java"),
                    line_number=1,
                    end_line=30,
                )
            ],
        )
        st = _make_symbol_table(fs1, fs2)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        # Find the parent package MOC (com.example)
        moc_files = [f for f in generated if "MOC" in f.name]
        example_moc = None
        for moc in moc_files:
            if "MOC - example" in moc.name:
                example_moc = moc.read_text()
                break

        assert example_moc is not None
        assert "## Sub-packages" in example_moc
        assert "[[MOC - service]]" in example_moc
        assert "[[MOC - model]]" in example_moc

    def test_moc_shows_parent_link(self, output_config, output_dir):
        """MOC pages should link back to parent package."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        moc_files = [f for f in generated if "MOC" in f.name]
        service_moc = None
        for moc in moc_files:
            if "service" in moc.name:
                service_moc = moc.read_text()
                break

        assert service_moc is not None
        assert "**Parent:** [[MOC - example]]" in service_moc

    def test_moc_not_generated_when_disabled(self, output_dir):
        """MOC pages should not be generated when generate_moc is False."""
        config = OutputConfig(
            output_dir=output_dir,
            generate_moc=False,
            generate_index=False,
        )
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(config, st)
        generated = gen.generate_all()

        moc_files = [f for f in generated if "MOC" in f.name]
        assert len(moc_files) == 0

    def test_moc_shows_class_roles(self, output_config, output_dir):
        """MOC pages should annotate classes with their architectural role."""
        fs = FileSymbols(
            file=_make_source_file("src/UserController.java"),
            package="com.example.controller",
            classes=[
                ClassDef(
                    name="UserController",
                    file_path=Path("/project/src/UserController.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="RestController")],
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        moc_files = [f for f in generated if "MOC" in f.name]
        controller_moc = None
        for moc in moc_files:
            if "controller" in moc.name:
                controller_moc = moc.read_text()
                break

        assert controller_moc is not None
        assert "[[UserController]] `controller`" in controller_moc


# ---------------------------------------------------------------------------
# WikiLink tests
# ---------------------------------------------------------------------------


class TestWikiLinks:
    """Test WikiLink generation for Obsidian graph view compatibility."""

    def test_class_wikilinks_in_extends(self, output_config):
        """Superclass references should use WikiLinks."""
        parent_fs = FileSymbols(
            file=_make_source_file("src/BaseService.java"),
            package="com.example",
            classes=[
                ClassDef(
                    name="BaseService",
                    file_path=Path("/project/src/BaseService.java"),
                    line_number=1,
                    end_line=20,
                )
            ],
        )
        child_fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example",
            imports=[ImportDef(module="com.example.BaseService")],
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                    superclass="BaseService",
                )
            ],
        )
        st = _make_symbol_table(parent_fs, child_fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_class_doc(child_fs.classes[0], child_fs)

        assert "[[BaseService]]" in content

    def test_wikilinks_in_used_by(self, output_config):
        """Used-by section should contain WikiLinks."""
        service_fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        controller_fs = FileSymbols(
            file=_make_source_file("src/UserController.java"),
            package="com.example.controller",
            imports=[ImportDef(module="com.example.service.UserService")],
            classes=[
                ClassDef(
                    name="UserController",
                    file_path=Path("/project/src/UserController.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(service_fs, controller_fs)
        gen = MarkdownGenerator(output_config, st)
        content = gen._generate_class_doc(service_fs.classes[0], service_fs)

        assert "[[UserController]]" in content

    def test_index_uses_wikilinks(self, output_config, output_dir):
        """Main index should use WikiLinks for all classes."""
        fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="Service")],
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        gen.generate_all()

        index = (output_dir / "index.md").read_text()
        assert "[[UserService]]" in index


# ---------------------------------------------------------------------------
# Vault structure tests
# ---------------------------------------------------------------------------


class TestVaultStructure:
    """Test overall vault structure for Obsidian compatibility."""

    def test_mirrored_directory_structure(self, output_config, output_dir):
        """Files should mirror source directory structure."""
        fs = FileSymbols(
            file=_make_source_file("src/main/java/com/example/UserService.java"),
            package="com.example",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/main/java/com/example/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        md_files = [f for f in generated if "MOC" not in f.name and f.name != "index.md"]
        assert len(md_files) == 1
        assert "src/main/java/com/example" in str(md_files[0])

    def test_flat_structure_when_mirror_disabled(self, output_dir):
        """Without mirroring, files should be flat in output directory."""
        config = OutputConfig(
            output_dir=output_dir,
            mirror_source_structure=False,
            generate_index=False,
            generate_moc=False,
        )
        fs = FileSymbols(
            file=_make_source_file("src/main/java/com/example/UserService.java"),
            package="com.example",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/main/java/com/example/UserService.java"),
                    line_number=1,
                    end_line=50,
                )
            ],
        )
        st = _make_symbol_table(fs)
        gen = MarkdownGenerator(config, st)
        generated = gen.generate_all()

        assert len(generated) == 1
        assert generated[0].parent == output_dir

    def test_generate_all_creates_complete_vault(self, output_config, output_dir):
        """generate_all should produce file docs, index, endpoints index, and MOC pages."""
        service_fs = FileSymbols(
            file=_make_source_file("src/UserService.java"),
            package="com.example.service",
            classes=[
                ClassDef(
                    name="UserService",
                    file_path=Path("/project/src/UserService.java"),
                    line_number=1,
                    end_line=50,
                    annotations=[Annotation(name="Service")],
                )
            ],
        )
        controller_fs = FileSymbols(
            file=_make_source_file("src/UserController.java"),
            package="com.example.controller",
            classes=[
                ClassDef(
                    name="UserController",
                    file_path=Path("/project/src/UserController.java"),
                    line_number=1,
                    end_line=80,
                    annotations=[Annotation(name="RestController")],
                )
            ],
            endpoints=[
                EndpointDef(
                    http_method="GET",
                    path="/api/users",
                    handler_method="getUsers",
                    handler_class="UserController",
                    file_path=Path("/project/src/UserController.java"),
                    line_number=20,
                    source_code="public List<User> getUsers() {}",
                )
            ],
        )

        st = _make_symbol_table(service_fs, controller_fs)
        gen = MarkdownGenerator(output_config, st)
        generated = gen.generate_all()

        names = {f.name for f in generated}
        # File docs
        assert "UserService.md" in names
        assert "UserController.md" in names
        # Index
        assert "index.md" in names
        # Endpoints index
        assert "endpoints.md" in names
        # MOC pages
        moc_names = {f.name for f in generated if "MOC" in f.name}
        assert len(moc_names) >= 2  # At least service and controller packages


# ---------------------------------------------------------------------------
# Config integration tests
# ---------------------------------------------------------------------------


class TestConfigIntegration:
    """Test configuration options for Obsidian vault generation."""

    def test_generate_moc_default_true(self):
        """generate_moc should default to True."""
        config = OutputConfig()
        assert config.generate_moc is True

    def test_generate_moc_from_dict(self):
        """generate_moc should be loadable from config dict."""
        from docmaker.config import DocmakerConfig

        data = {"output": {"generate_moc": False}}
        config = DocmakerConfig.from_dict(data)
        assert config.output.generate_moc is False

    def test_generate_moc_in_to_dict(self):
        """generate_moc should be present in serialized config."""
        from docmaker.config import DocmakerConfig

        config = DocmakerConfig()
        d = config.to_dict()
        assert "generate_moc" in d["output"]
        assert d["output"]["generate_moc"] is True


# ---------------------------------------------------------------------------
# General markdown generator tests (using symbol_table fixture)
# ---------------------------------------------------------------------------


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
