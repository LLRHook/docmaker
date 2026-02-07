"""Tests for the pipeline orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docmaker.config import DocmakerConfig
from docmaker.models import (
    ClassDef,
    FileCategory,
    FileSymbols,
    Language,
    SourceFile,
    SymbolTable,
)
from docmaker.pipeline import Pipeline


@pytest.fixture
def temp_project():
    """Create a temporary project with a Python file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        src = root / "src"
        src.mkdir()
        (src / "example.py").write_text(
            'class MyClass:\n    """A sample class."""\n    def method(self):\n        pass\n'
        )
        yield root


@pytest.fixture
def config(temp_project):
    cfg = DocmakerConfig()
    cfg.source_dir = temp_project
    cfg.output.output_dir = temp_project / "docs"
    cfg.llm.enabled = False
    cfg.cache_file = Path(".test_cache.json")
    return cfg


def test_pipeline_init(config):
    """Test Pipeline initializes with all components."""
    pipeline = Pipeline(config)
    assert pipeline.config is config
    assert pipeline.crawler is not None
    assert pipeline.classifier is not None
    assert pipeline.cache is not None
    assert pipeline.parser_registry is not None
    assert isinstance(pipeline.symbol_table, SymbolTable)


def test_pipeline_run_returns_list(config):
    """Test that run() returns a list of generated paths."""
    pipeline = Pipeline(config)
    result = pipeline.run()
    assert isinstance(result, list)


def test_pipeline_run_generates_docs(config):
    """Test that run() generates documentation files."""
    pipeline = Pipeline(config)
    result = pipeline.run()
    assert len(result) > 0
    assert all(p.exists() for p in result)


def test_pipeline_run_no_files(config):
    """Test run() with empty source directory."""
    config.source_dir = config.output.output_dir / "empty"
    config.source_dir.mkdir(parents=True, exist_ok=True)
    pipeline = Pipeline(config)
    result = pipeline.run()
    assert result == []


def test_pipeline_run_incremental_all_cached(config, temp_project):
    """Test incremental mode when all files are cached."""
    pipeline = Pipeline(config)

    # First run to populate cache
    pipeline.run()

    # Second run in incremental mode - files haven't changed
    pipeline2 = Pipeline(config)
    result = pipeline2.run(incremental=True)
    assert result == []


def test_pipeline_crawl_files(config):
    """Test _crawl_files returns source files."""
    pipeline = Pipeline(config)
    files = pipeline._crawl_files()
    assert len(files) > 0
    assert all(isinstance(f, SourceFile) for f in files)


def test_pipeline_classify_files_llm_disabled(config):
    """Test classification when LLM is disabled."""
    pipeline = Pipeline(config)
    sf = SourceFile(
        path=Path("/test.py"),
        relative_path=Path("test.py"),
        language=Language.PYTHON,
        category=FileCategory.UNKNOWN,
    )
    result = pipeline._classify_files([sf])
    assert result == [sf]  # Returns unchanged


def test_pipeline_parse_files(config, temp_project):
    """Test _parse_files populates symbol table."""
    pipeline = Pipeline(config)

    sf = SourceFile(
        path=temp_project / "src" / "example.py",
        relative_path=Path("src/example.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    pipeline._parse_files([sf])
    assert len(pipeline.symbol_table.files) > 0


def test_pipeline_parse_files_no_parseable(config):
    """Test _parse_files with no parseable files."""
    pipeline = Pipeline(config)
    sf = SourceFile(
        path=Path("/test.unknown"),
        relative_path=Path("test.unknown"),
        language=Language.UNKNOWN,
    )
    pipeline._parse_files([sf])
    assert len(pipeline.symbol_table.files) == 0


def test_pipeline_generate_docs_empty_table(config):
    """Test _generate_docs with empty symbol table."""
    pipeline = Pipeline(config)
    result = pipeline._generate_docs()
    assert result == []


def test_pipeline_update_cache(config, temp_project):
    """Test _update_cache stores file info."""
    pipeline = Pipeline(config)
    sf = SourceFile(
        path=temp_project / "src" / "example.py",
        relative_path=Path("src/example.py"),
        language=Language.PYTHON,
        hash="abc123",
    )
    pipeline._update_cache([sf])
    # Cache file should have been saved
    cache_path = config.source_dir / config.cache_file
    assert cache_path.exists()


def test_pipeline_end_to_end(config):
    """Test the full pipeline from crawl to doc generation."""
    pipeline = Pipeline(config)
    generated = pipeline.run()

    assert isinstance(generated, list)
    for path in generated:
        assert path.exists()
        assert path.suffix == ".md"
