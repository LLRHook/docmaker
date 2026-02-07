"""Tests for the linker module (cross-reference resolution, WikiLinks, usage tracking)."""

from pathlib import Path

import pytest

from docmaker.generator.linker import ImportLinker
from docmaker.models import (
    ClassDef,
    FileCategory,
    FileSymbols,
    FunctionDef,
    ImportDef,
    Language,
    SourceFile,
    SymbolTable,
)


def _source_file(name: str = "Test.java") -> SourceFile:
    return SourceFile(
        path=Path(f"/src/{name}"),
        relative_path=Path(name),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )


def _class_def(name: str, fpath: str = "/src/Test.java", **kwargs) -> ClassDef:
    return ClassDef(
        name=name, file_path=Path(fpath), line_number=1, end_line=50, **kwargs
    )


def _method_def(name: str, source_code: str = "") -> FunctionDef:
    return FunctionDef(
        name=name,
        file_path=Path("/src/Test.java"),
        line_number=1,
        end_line=10,
        source_code=source_code,
    )


@pytest.fixture
def symbol_table():
    """Build a SymbolTable with several interconnected classes."""
    st = SymbolTable()

    # --- User class in model package ---
    user_cls = _class_def("User", "/src/User.java")
    user_file = FileSymbols(
        file=_source_file("User.java"),
        package="com.example.model",
        classes=[user_cls],
    )
    st.add_file_symbols(user_file)

    # --- UserService with a method that calls userRepo.findById ---
    svc_method = _method_def(
        "findUser", source_code="return userRepo.findById(id);"
    )
    save_method = _method_def(
        "saveUser", source_code="return userRepo.save(user);"
    )
    svc_cls = _class_def("UserService", "/src/UserService.java", methods=[svc_method, save_method])
    svc_file = FileSymbols(
        file=_source_file("UserService.java"),
        package="com.example.service",
        imports=[ImportDef(module="com.example.model.User")],
        classes=[svc_cls],
    )
    st.add_file_symbols(svc_file)

    # --- UserController with a method that calls findUser ---
    ctrl_method = _method_def(
        "getUser", source_code="return userService.findUser(id);"
    )
    ctrl_cls = _class_def("UserController", "/src/UserController.java", methods=[ctrl_method])
    ctrl_file = FileSymbols(
        file=_source_file("UserController.java"),
        package="com.example.controller",
        imports=[
            ImportDef(module="com.example.model.User"),
            ImportDef(module="com.example.service.UserService"),
        ],
        classes=[ctrl_cls],
    )
    st.add_file_symbols(ctrl_file)

    return st


@pytest.fixture
def linker(symbol_table):
    return ImportLinker(symbol_table)


# ── resolve_import ───────────────────────────────────────────────


class TestResolveImport:
    def test_resolves_known_import(self, linker):
        imp = ImportDef(module="com.example.model.User")
        result = linker.resolve_import(imp)
        assert result == Path("/src/User.java")

    def test_returns_none_for_unknown_import(self, linker):
        imp = ImportDef(module="com.example.missing.Nope")
        assert linker.resolve_import(imp) is None

    def test_caches_resolved_path(self, linker):
        imp = ImportDef(module="com.example.model.User")
        linker.resolve_import(imp)
        assert "com.example.model.User" in linker._import_cache
        assert linker._import_cache["com.example.model.User"] == Path("/src/User.java")

    def test_caches_none_for_unknown(self, linker):
        imp = ImportDef(module="com.example.missing.Nope")
        linker.resolve_import(imp)
        assert "com.example.missing.Nope" in linker._import_cache
        assert linker._import_cache["com.example.missing.Nope"] is None

    def test_cache_hit_returns_same_result(self, linker):
        imp = ImportDef(module="com.example.model.User")
        first = linker.resolve_import(imp)
        second = linker.resolve_import(imp)
        assert first == second == Path("/src/User.java")


# ── resolve_type ─────────────────────────────────────────────────


class TestResolveType:
    def test_returns_none_for_empty_type(self, linker, symbol_table):
        fs = FileSymbols(file=_source_file())
        assert linker.resolve_type("", fs) is None

    def test_returns_none_for_none_type(self, linker):
        fs = FileSymbols(file=_source_file())
        assert linker.resolve_type(None, fs) is None

    def test_resolves_fqn_already_in_index(self, linker):
        fs = FileSymbols(file=_source_file())
        result = linker.resolve_type("com.example.model.User", fs)
        assert result == "com.example.model.User"

    def test_resolves_simple_name_via_import(self, linker, symbol_table):
        fs = symbol_table.files[Path("/src/UserController.java")]
        result = linker.resolve_type("User", fs)
        assert result == "com.example.model.User"

    def test_resolves_generic_extracts_base_type(self, linker, symbol_table):
        """resolve_type strips generic params: List<User> resolves 'List', not 'User'."""
        fs = symbol_table.files[Path("/src/UserController.java")]
        # List is not in the class index, so this returns None
        assert linker.resolve_type("List<User>", fs) is None
        # But if the base type itself is known, it resolves
        assert linker.resolve_type("User<T>", fs) == "com.example.model.User"

    def test_resolves_array_type(self, linker, symbol_table):
        fs = symbol_table.files[Path("/src/UserController.java")]
        result = linker.resolve_type("User[]", fs)
        assert result == "com.example.model.User"

    def test_resolves_wildcard_import(self, linker, symbol_table):
        """Wildcard import like com.example.model.* resolves User."""
        wildcard_file = FileSymbols(
            file=_source_file("Other.java"),
            package="com.example.other",
            imports=[ImportDef(module="com.example.model.*", is_wildcard=True)],
            classes=[_class_def("Other", "/src/Other.java")],
        )
        symbol_table.add_file_symbols(wildcard_file)

        result = linker.resolve_type("User", wildcard_file)
        assert result == "com.example.model.User"

    def test_resolves_local_package_type(self, linker, symbol_table):
        """A class in the same package resolves without explicit import."""
        # Add a second class in com.example.model
        addr_cls = _class_def("Address", "/src/Address.java")
        addr_file = FileSymbols(
            file=_source_file("Address.java"),
            package="com.example.model",
            classes=[addr_cls],
        )
        symbol_table.add_file_symbols(addr_file)

        # Resolve from User's file (same package, no import needed)
        user_fs = symbol_table.files[Path("/src/User.java")]
        result = linker.resolve_type("Address", user_fs)
        assert result == "com.example.model.Address"

    def test_returns_none_for_unresolvable(self, linker):
        fs = FileSymbols(file=_source_file())
        assert linker.resolve_type("NoSuchType", fs) is None


# ── get_wikilink ─────────────────────────────────────────────────


class TestGetWikilink:
    def test_resolvable_type_returns_wikilink(self, linker, symbol_table):
        fs = symbol_table.files[Path("/src/UserController.java")]
        assert linker.get_wikilink("User", fs) == "[[User]]"

    def test_unresolvable_type_returns_code_span(self, linker):
        fs = FileSymbols(file=_source_file())
        assert linker.get_wikilink("Unknown", fs) == "`Unknown`"

    def test_fqn_type_returns_wikilink(self, linker):
        fs = FileSymbols(file=_source_file())
        assert linker.get_wikilink("com.example.model.User", fs) == "[[User]]"

    def test_generic_type_wikilink_uses_base(self, linker, symbol_table):
        """WikiLink for generic resolves the base type, not the type parameter."""
        fs = symbol_table.files[Path("/src/UserController.java")]
        # List isn't a known class, so falls back to code span
        assert linker.get_wikilink("List<User>", fs) == "`List<User>`"
        # But User<T> resolves User
        assert linker.get_wikilink("User<T>", fs) == "[[User]]"


# ── get_class_link ───────────────────────────────────────────────


class TestGetClassLink:
    def test_known_class(self, linker):
        assert linker.get_class_link("User") == "[[User]]"

    def test_unknown_class(self, linker):
        assert linker.get_class_link("Ghost") == "`Ghost`"

    def test_finds_by_simple_name(self, linker):
        assert linker.get_class_link("UserService") == "[[UserService]]"


# ── get_method_link ──────────────────────────────────────────────


class TestGetMethodLink:
    def test_known_class_method(self, linker):
        assert linker.get_method_link("UserService", "findUser") == "[[UserService#findUser]]"

    def test_unknown_class_method(self, linker):
        assert linker.get_method_link("Ghost", "doStuff") == "`Ghost.doStuff()`"


# ── find_callers ─────────────────────────────────────────────────


class TestFindCallers:
    def test_finds_callers(self, linker):
        callers = linker.find_callers("UserService", "findUser")
        assert ("UserController", "getUser") in callers

    def test_excludes_self(self, linker):
        """A method should not list itself as a caller."""
        callers = linker.find_callers("UserController", "getUser")
        assert ("UserController", "getUser") not in callers

    def test_no_callers(self, linker):
        callers = linker.find_callers("UserController", "getUser")
        # getUser is the leaf; nobody calls it
        assert len(callers) == 0

    def test_method_not_found(self, linker):
        callers = linker.find_callers("User", "nonexistent")
        assert callers == []


# ── find_usages ──────────────────────────────────────────────────


class TestFindUsages:
    def test_finds_import_usages(self, linker):
        usages = linker.find_usages("User")
        class_names = [u[0] for u in usages]
        assert "UserService" in class_names
        assert "UserController" in class_names

    def test_usage_type_is_imports(self, linker):
        usages = linker.find_usages("User")
        for _, usage_type in usages:
            assert usage_type == "imports"

    def test_no_usages(self, linker):
        usages = linker.find_usages("UserController")
        assert usages == []

    def test_does_not_match_partial_names(self, linker):
        """find_usages('Use') should not match 'com.example.model.User'."""
        usages = linker.find_usages("Use")
        assert usages == []
