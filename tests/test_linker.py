"""Tests for the import linker."""

from pathlib import Path

import pytest

from docmaker.generator.linker import ImportLinker
from docmaker.models import (
    ClassDef,
    EndpointDef,
    FileCategory,
    FileSymbols,
    FunctionDef,
    ImportDef,
    Language,
    SourceFile,
    SymbolTable,
)


@pytest.fixture
def symbol_table():
    """Create a symbol table with sample data."""
    st = SymbolTable()

    # Controller file
    controller_file = SourceFile(
        path=Path("/src/UserController.java"),
        relative_path=Path("src/UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )
    controller_cls = ClassDef(
        name="UserController",
        file_path=Path("/src/UserController.java"),
        line_number=10,
        end_line=50,
        package="com.example",
        methods=[
            FunctionDef(
                name="getUser",
                file_path=Path("/src/UserController.java"),
                line_number=15,
                end_line=25,
                source_code="public User getUser(Long id) { return userService.findById(id); }",
            )
        ],
    )
    controller_symbols = FileSymbols(
        file=controller_file,
        package="com.example",
        imports=[ImportDef(module="com.example.service.UserService")],
        classes=[controller_cls],
    )

    # Service file
    service_file = SourceFile(
        path=Path("/src/UserService.java"),
        relative_path=Path("src/UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )
    service_cls = ClassDef(
        name="UserService",
        file_path=Path("/src/UserService.java"),
        line_number=5,
        end_line=30,
        package="com.example.service",
        methods=[
            FunctionDef(
                name="findById",
                file_path=Path("/src/UserService.java"),
                line_number=10,
                end_line=15,
                source_code="public User findById(Long id) { return repo.findById(id); }",
            )
        ],
    )
    service_symbols = FileSymbols(
        file=service_file,
        package="com.example.service",
        classes=[service_cls],
    )

    st.add_file_symbols(controller_symbols)
    st.add_file_symbols(service_symbols)
    return st


@pytest.fixture
def linker(symbol_table):
    return ImportLinker(symbol_table)


@pytest.fixture
def controller_file_symbols(symbol_table):
    return symbol_table.files[Path("/src/UserController.java")]


class TestResolveImport:
    def test_resolve_known_import(self, linker, symbol_table):
        imp = ImportDef(module="com.example.service.UserService")
        result = linker.resolve_import(imp)
        assert result == Path("/src/UserService.java")

    def test_resolve_unknown_import(self, linker):
        imp = ImportDef(module="com.nonexistent.Foo")
        result = linker.resolve_import(imp)
        assert result is None

    def test_resolve_caches_result(self, linker):
        imp = ImportDef(module="com.example.service.UserService")
        linker.resolve_import(imp)
        assert "com.example.service.UserService" in linker._import_cache

    def test_resolve_caches_none(self, linker):
        imp = ImportDef(module="com.nonexistent.Foo")
        linker.resolve_import(imp)
        assert linker._import_cache["com.nonexistent.Foo"] is None


class TestResolveType:
    def test_resolve_fqn(self, linker, controller_file_symbols):
        result = linker.resolve_type("com.example.UserController", controller_file_symbols)
        assert result == "com.example.UserController"

    def test_resolve_via_import(self, linker, controller_file_symbols):
        result = linker.resolve_type("UserService", controller_file_symbols)
        assert result == "com.example.service.UserService"

    def test_resolve_local_package(self, linker, controller_file_symbols):
        result = linker.resolve_type("UserController", controller_file_symbols)
        assert result == "com.example.UserController"

    def test_resolve_unknown(self, linker, controller_file_symbols):
        result = linker.resolve_type("NonExistent", controller_file_symbols)
        assert result is None

    def test_resolve_empty_type(self, linker, controller_file_symbols):
        result = linker.resolve_type("", controller_file_symbols)
        assert result is None

    def test_resolve_none_type(self, linker, controller_file_symbols):
        result = linker.resolve_type(None, controller_file_symbols)
        assert result is None

    def test_resolve_generic_type(self, linker, controller_file_symbols):
        """Test that generic types strip type parameters."""
        result = linker.resolve_type("UserController<String>", controller_file_symbols)
        assert result == "com.example.UserController"

    def test_resolve_wildcard_import(self, linker, symbol_table):
        """Test resolving via wildcard import."""
        sf = SourceFile(
            path=Path("/test/Test.java"),
            relative_path=Path("Test.java"),
            language=Language.JAVA,
        )
        file_symbols = FileSymbols(
            file=sf,
            imports=[ImportDef(module="com.example.service.*", is_wildcard=True)],
        )
        result = linker.resolve_type("UserService", file_symbols)
        assert result == "com.example.service.UserService"


class TestGetWikilink:
    def test_known_class(self, linker, controller_file_symbols):
        result = linker.get_wikilink("UserService", controller_file_symbols)
        assert result == "[[UserService]]"

    def test_unknown_class(self, linker, controller_file_symbols):
        result = linker.get_wikilink("UnknownType", controller_file_symbols)
        assert result == "`UnknownType`"


class TestGetClassLink:
    def test_known_class(self, linker):
        result = linker.get_class_link("UserController")
        assert result == "[[UserController]]"

    def test_unknown_class(self, linker):
        result = linker.get_class_link("NonExistent")
        assert result == "`NonExistent`"


class TestGetMethodLink:
    def test_known_class_method(self, linker):
        result = linker.get_method_link("UserController", "getUser")
        assert result == "[[UserController#getUser]]"

    def test_unknown_class_method(self, linker):
        result = linker.get_method_link("NonExistent", "doThing")
        assert result == "`NonExistent.doThing()`"


class TestFindCallers:
    def test_find_callers(self, linker):
        callers = linker.find_callers("UserService", "findById")
        assert len(callers) == 1
        assert callers[0] == ("UserController", "getUser")

    def test_find_callers_excludes_self(self, linker):
        callers = linker.find_callers("UserController", "getUser")
        assert all(c[0] != "UserController" or c[1] != "getUser" for c in callers)


class TestFindUsages:
    def test_find_usages(self, linker):
        usages = linker.find_usages("UserService")
        assert len(usages) == 1
        assert usages[0] == ("UserController", "imports")

    def test_find_usages_none(self, linker):
        usages = linker.find_usages("NonExistent")
        assert usages == []
