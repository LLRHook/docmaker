"""Tests for data models."""

from pathlib import Path

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


class TestFileCategory:
    def test_values(self):
        assert FileCategory.BACKEND == "backend"
        assert FileCategory.FRONTEND == "frontend"
        assert FileCategory.CONFIG == "config"
        assert FileCategory.TEST == "test"
        assert FileCategory.IGNORE == "ignore"
        assert FileCategory.UNKNOWN == "unknown"

    def test_is_str(self):
        assert isinstance(FileCategory.BACKEND, str)


class TestLanguage:
    def test_from_extension_java(self):
        assert Language.from_extension(".java") == Language.JAVA

    def test_from_extension_python(self):
        assert Language.from_extension(".py") == Language.PYTHON

    def test_from_extension_go(self):
        assert Language.from_extension(".go") == Language.GO

    def test_from_extension_typescript(self):
        assert Language.from_extension(".ts") == Language.TYPESCRIPT
        assert Language.from_extension(".tsx") == Language.TYPESCRIPT

    def test_from_extension_javascript(self):
        assert Language.from_extension(".js") == Language.JAVASCRIPT
        assert Language.from_extension(".jsx") == Language.JAVASCRIPT

    def test_from_extension_kotlin(self):
        assert Language.from_extension(".kt") == Language.KOTLIN
        assert Language.from_extension(".kts") == Language.KOTLIN

    def test_from_extension_unknown(self):
        assert Language.from_extension(".rs") == Language.UNKNOWN
        assert Language.from_extension(".cpp") == Language.UNKNOWN

    def test_from_extension_case_insensitive(self):
        assert Language.from_extension(".JAVA") == Language.JAVA
        assert Language.from_extension(".Py") == Language.PYTHON


class TestSourceFile:
    def test_defaults(self):
        sf = SourceFile(
            path=Path("/tmp/test.py"),
            relative_path=Path("test.py"),
            language=Language.PYTHON,
        )
        assert sf.category == FileCategory.UNKNOWN
        assert sf.size_bytes == 0
        assert sf.hash == ""
        assert sf.header_content == ""


class TestParameter:
    def test_defaults(self):
        p = Parameter(name="x")
        assert p.name == "x"
        assert p.type is None
        assert p.default is None
        assert p.description is None

    def test_full(self):
        p = Parameter(name="count", type="int", default="0", description="The count")
        assert p.type == "int"
        assert p.default == "0"


class TestAnnotation:
    def test_defaults(self):
        a = Annotation(name="Override")
        assert a.name == "Override"
        assert a.arguments == {}

    def test_with_arguments(self):
        a = Annotation(name="RequestMapping", arguments={"value": "/api"})
        assert a.arguments["value"] == "/api"


class TestSymbolTable:
    @pytest.fixture
    def symbol_table(self):
        return SymbolTable()

    @pytest.fixture
    def sample_file_symbols(self):
        sf = SourceFile(
            path=Path("/test/MyClass.java"),
            relative_path=Path("MyClass.java"),
            language=Language.JAVA,
        )
        cls = ClassDef(
            name="MyClass",
            file_path=Path("/test/MyClass.java"),
            line_number=1,
            end_line=50,
            methods=[
                FunctionDef(
                    name="doWork",
                    file_path=Path("/test/MyClass.java"),
                    line_number=10,
                    end_line=20,
                )
            ],
        )
        func = FunctionDef(
            name="helperFunc",
            file_path=Path("/test/MyClass.java"),
            line_number=55,
            end_line=60,
        )
        endpoint = EndpointDef(
            http_method="GET",
            path="/api/items",
            handler_method="getItems",
            handler_class="MyClass",
            file_path=Path("/test/MyClass.java"),
            line_number=10,
        )
        return FileSymbols(
            file=sf,
            package="com.example",
            imports=[ImportDef(module="com.example.Other")],
            classes=[cls],
            functions=[func],
            endpoints=[endpoint],
        )

    def test_add_file_symbols_stores_file(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        assert Path("/test/MyClass.java") in symbol_table.files

    def test_add_file_symbols_indexes_class(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        assert "com.example.MyClass" in symbol_table.class_index

    def test_add_file_symbols_indexes_method(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        assert "com.example.MyClass.doWork" in symbol_table.function_index

    def test_add_file_symbols_indexes_function(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        assert "com.example.helperFunc" in symbol_table.function_index

    def test_add_file_symbols_indexes_endpoint(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        assert "GET:/api/items" in symbol_table.endpoint_index

    def test_add_file_symbols_no_package(self, symbol_table):
        sf = SourceFile(
            path=Path("/test/util.py"),
            relative_path=Path("util.py"),
            language=Language.PYTHON,
        )
        cls = ClassDef(
            name="Util",
            file_path=Path("/test/util.py"),
            line_number=1,
            end_line=10,
        )
        symbols = FileSymbols(file=sf, classes=[cls])
        symbol_table.add_file_symbols(symbols)
        assert "Util" in symbol_table.class_index

    def test_resolve_import_found(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        result = symbol_table.resolve_import("com.example.MyClass")
        assert result is not None
        assert result.name == "MyClass"

    def test_resolve_import_not_found(self, symbol_table):
        result = symbol_table.resolve_import("com.nonexistent.Foo")
        assert result is None

    def test_get_endpoints_by_class(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        endpoints = symbol_table.get_endpoints_by_class("MyClass")
        assert len(endpoints) == 1
        assert endpoints[0].path == "/api/items"

    def test_get_endpoints_by_class_none(self, symbol_table, sample_file_symbols):
        symbol_table.add_file_symbols(sample_file_symbols)
        endpoints = symbol_table.get_endpoints_by_class("NonExistent")
        assert endpoints == []
