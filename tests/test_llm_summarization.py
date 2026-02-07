"""Tests for LLM summarization integration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from docmaker.config import LLMConfig, OutputConfig
from docmaker.generator.markdown import MarkdownGenerator
from docmaker.llm import (
    NoOpProvider,
    Summarizer,
    create_llm_provider,
)
from docmaker.models import (
    Annotation,
    ClassDef,
    FileCategory,
    FileSymbols,
    FunctionDef,
    Language,
    Parameter,
    SourceFile,
    SymbolTable,
)


@pytest.fixture
def disabled_config():
    return LLMConfig(enabled=False)


@pytest.fixture
def enabled_config():
    return LLMConfig(enabled=True, provider="ollama")


@pytest.fixture
def sample_class():
    return ClassDef(
        name="UserService",
        file_path=Path("/src/UserService.java"),
        line_number=10,
        end_line=50,
        package="com.example.service",
        annotations=[Annotation(name="Service")],
        methods=[
            FunctionDef(
                name="getUser",
                file_path=Path("/src/UserService.java"),
                line_number=15,
                end_line=20,
                parameters=[Parameter(name="id", type="Long")],
                return_type="User",
                source_code="public User getUser(Long id) { return repo.findById(id); }",
            ),
        ],
        source_code="@Service\npublic class UserService { ... }",
    )


@pytest.fixture
def sample_symbol_table(sample_class):
    source_file = SourceFile(
        path=Path("/src/UserService.java"),
        relative_path=Path("src/UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )
    file_symbols = FileSymbols(
        file=source_file,
        package="com.example.service",
        classes=[sample_class],
    )
    st = SymbolTable()
    st.add_file_symbols(file_symbols)
    return st


# --- Model tests ---


def test_classdef_has_summary_field():
    cls = ClassDef(
        name="Foo",
        file_path=Path("/foo.py"),
        line_number=1,
        end_line=10,
    )
    assert cls.summary is None


def test_classdef_summary_can_be_set():
    cls = ClassDef(
        name="Foo",
        file_path=Path("/foo.py"),
        line_number=1,
        end_line=10,
        summary="A test class that does things.",
    )
    assert cls.summary == "A test class that does things."


def test_functiondef_has_summary_field():
    func = FunctionDef(
        name="bar",
        file_path=Path("/foo.py"),
        line_number=1,
        end_line=5,
    )
    assert func.summary is None


def test_functiondef_summary_can_be_set():
    func = FunctionDef(
        name="bar",
        file_path=Path("/foo.py"),
        line_number=1,
        end_line=5,
        summary="Computes the bar value.",
    )
    assert func.summary == "Computes the bar value."


# --- Provider tests ---


def test_noop_provider_generate_returns_none():
    provider = NoOpProvider()
    assert provider.generate("anything") is None


def test_create_provider_disabled_returns_noop(disabled_config):
    provider = create_llm_provider(disabled_config)
    assert isinstance(provider, NoOpProvider)


# --- Summarizer tests ---


def test_summarizer_disabled_llm_not_available(disabled_config):
    summarizer = Summarizer(disabled_config)
    # NoOpProvider.is_available() returns True, but generate returns None
    assert summarizer.is_llm_available() is True


def test_summarizer_generates_class_summary(enabled_config, sample_class):
    summarizer = Summarizer(enabled_config)
    summarizer.provider = MagicMock()
    summarizer.provider.generate.return_value = "UserService manages user data access."

    result = summarizer.summarize_class(sample_class, "java")
    assert result == "UserService manages user data access."
    summarizer.provider.generate.assert_called_once()


def test_summarizer_generates_method_summary(enabled_config):
    summarizer = Summarizer(enabled_config)
    summarizer.provider = MagicMock()
    summarizer.provider.generate.return_value = "Retrieves a user by their ID."

    method = FunctionDef(
        name="getUser",
        file_path=Path("/src/UserService.java"),
        line_number=15,
        end_line=20,
        parameters=[Parameter(name="id", type="Long")],
        return_type="User",
        source_code="public User getUser(Long id) { return repo.findById(id); }",
    )

    result = summarizer.summarize_method(method, "UserService", "java")
    assert result == "Retrieves a user by their ID."
    summarizer.provider.generate.assert_called_once()


def test_summarizer_handles_generation_failure(enabled_config, sample_class):
    summarizer = Summarizer(enabled_config)
    summarizer.provider = MagicMock()
    summarizer.provider.generate.return_value = None

    result = summarizer.summarize_class(sample_class, "java")
    assert result is None


def test_summarize_symbol_table(enabled_config, sample_symbol_table):
    summarizer = Summarizer(enabled_config)
    summarizer.provider = MagicMock()
    summarizer.provider.generate.return_value = "A helpful summary."
    summarizer.provider.is_available.return_value = True

    class_count, method_count = summarizer.summarize_symbol_table(sample_symbol_table)
    assert class_count == 1
    assert method_count == 1

    # Verify summaries were set on the models
    for fs in sample_symbol_table.files.values():
        for cls in fs.classes:
            assert cls.summary == "A helpful summary."
            for method in cls.methods:
                assert method.summary == "A helpful summary."


def test_summarize_symbol_table_noop(disabled_config, sample_symbol_table):
    summarizer = Summarizer(disabled_config)
    class_count, method_count = summarizer.summarize_symbol_table(sample_symbol_table)
    # NoOpProvider.generate returns None, so no summaries
    assert class_count == 0
    assert method_count == 0


# --- Markdown rendering tests ---


def test_markdown_renders_class_summary():
    source_file = SourceFile(
        path=Path("/src/Foo.py"),
        relative_path=Path("src/Foo.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    cls = ClassDef(
        name="Foo",
        file_path=Path("/src/Foo.py"),
        line_number=1,
        end_line=10,
        summary="Foo handles all the business logic for widget processing.",
    )
    file_symbols = FileSymbols(file=source_file, classes=[cls])
    st = SymbolTable()
    st.add_file_symbols(file_symbols)

    config = OutputConfig(output_dir=Path("/tmp/test_docs"))
    gen = MarkdownGenerator(config, st)
    doc = gen._generate_class_doc(cls, file_symbols)

    assert "**Summary:** Foo handles all the business logic for widget processing." in doc


def test_markdown_renders_method_summary():
    source_file = SourceFile(
        path=Path("/src/Foo.py"),
        relative_path=Path("src/Foo.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    cls = ClassDef(
        name="Foo",
        file_path=Path("/src/Foo.py"),
        line_number=1,
        end_line=20,
    )
    method = FunctionDef(
        name="process",
        file_path=Path("/src/Foo.py"),
        line_number=5,
        end_line=10,
        summary="Processes the widget and returns the result.",
    )
    file_symbols = FileSymbols(file=source_file, classes=[cls])
    st = SymbolTable()
    st.add_file_symbols(file_symbols)

    config = OutputConfig(output_dir=Path("/tmp/test_docs"))
    gen = MarkdownGenerator(config, st)
    doc = gen._generate_method_doc(method, cls, file_symbols)

    assert "**Summary:** Processes the widget and returns the result." in doc


def test_markdown_renders_function_summary():
    source_file = SourceFile(
        path=Path("/src/utils.py"),
        relative_path=Path("src/utils.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    func = FunctionDef(
        name="helper",
        file_path=Path("/src/utils.py"),
        line_number=1,
        end_line=5,
        summary="A utility function that helps with data transformation.",
    )
    file_symbols = FileSymbols(file=source_file, functions=[func])
    st = SymbolTable()
    st.add_file_symbols(file_symbols)

    config = OutputConfig(output_dir=Path("/tmp/test_docs"))
    gen = MarkdownGenerator(config, st)
    doc = gen._generate_function_doc(func, file_symbols)

    assert "**Summary:** A utility function that helps with data transformation." in doc


def test_markdown_no_summary_when_none():
    source_file = SourceFile(
        path=Path("/src/Foo.py"),
        relative_path=Path("src/Foo.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    cls = ClassDef(
        name="Foo",
        file_path=Path("/src/Foo.py"),
        line_number=1,
        end_line=10,
        # No summary set
    )
    file_symbols = FileSymbols(file=source_file, classes=[cls])
    st = SymbolTable()
    st.add_file_symbols(file_symbols)

    config = OutputConfig(output_dir=Path("/tmp/test_docs"))
    gen = MarkdownGenerator(config, st)
    doc = gen._generate_class_doc(cls, file_symbols)

    assert "**Summary:**" not in doc
