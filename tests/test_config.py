"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest
import yaml

from docmaker.config import CrawlerConfig, DocmakerConfig, LLMConfig, OutputConfig


def test_default_llm_config():
    """Test LLMConfig defaults."""
    cfg = LLMConfig()
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.2"
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.api_key is None
    assert cfg.timeout == 30
    assert cfg.enabled is True


def test_default_crawler_config():
    """Test CrawlerConfig defaults."""
    cfg = CrawlerConfig()
    assert cfg.respect_gitignore is True
    assert cfg.custom_ignore_patterns == []
    assert ".java" in cfg.include_extensions
    assert ".py" in cfg.include_extensions
    assert cfg.max_file_size_kb == 500
    assert cfg.header_lines_for_classification == 50


def test_default_output_config():
    """Test OutputConfig defaults."""
    cfg = OutputConfig()
    assert cfg.output_dir == Path("./docs")
    assert cfg.mirror_source_structure is True
    assert cfg.include_source_snippets is True
    assert cfg.max_snippet_lines == 50
    assert cfg.generate_index is True


def test_default_docmaker_config():
    """Test DocmakerConfig defaults."""
    cfg = DocmakerConfig()
    assert cfg.source_dir == Path(".")
    assert isinstance(cfg.llm, LLMConfig)
    assert isinstance(cfg.crawler, CrawlerConfig)
    assert isinstance(cfg.output, OutputConfig)
    assert cfg.cache_file == Path(".docmaker_cache.json")


def test_from_dict_empty():
    """Test creating config from empty dict returns defaults."""
    cfg = DocmakerConfig.from_dict({})
    assert cfg.source_dir == Path(".")
    assert cfg.llm.provider == "ollama"
    assert cfg.crawler.respect_gitignore is True
    assert cfg.output.output_dir == Path("./docs")


def test_from_dict_full():
    """Test creating config from a full dict."""
    data = {
        "source_dir": "/tmp/project",
        "cache_file": ".my_cache.json",
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com",
            "api_key": "sk-test",
            "timeout": 60,
            "enabled": False,
        },
        "crawler": {
            "respect_gitignore": False,
            "custom_ignore_patterns": ["*.generated"],
            "include_extensions": [".java", ".py"],
            "max_file_size_kb": 1000,
            "header_lines_for_classification": 100,
        },
        "output": {
            "output_dir": "/tmp/docs",
            "mirror_source_structure": False,
            "include_source_snippets": False,
            "max_snippet_lines": 25,
            "generate_index": False,
        },
    }
    cfg = DocmakerConfig.from_dict(data)

    assert cfg.source_dir == Path("/tmp/project")
    assert cfg.cache_file == Path(".my_cache.json")
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4"
    assert cfg.llm.api_key == "sk-test"
    assert cfg.llm.timeout == 60
    assert cfg.llm.enabled is False
    assert cfg.crawler.respect_gitignore is False
    assert cfg.crawler.custom_ignore_patterns == ["*.generated"]
    assert cfg.crawler.include_extensions == [".java", ".py"]
    assert cfg.crawler.max_file_size_kb == 1000
    assert cfg.output.output_dir == Path("/tmp/docs")
    assert cfg.output.mirror_source_structure is False
    assert cfg.output.include_source_snippets is False
    assert cfg.output.max_snippet_lines == 25
    assert cfg.output.generate_index is False


def test_from_dict_partial():
    """Test creating config from a partial dict uses defaults for missing keys."""
    data = {"llm": {"model": "mistral"}}
    cfg = DocmakerConfig.from_dict(data)

    assert cfg.llm.model == "mistral"
    assert cfg.llm.provider == "ollama"  # default
    assert cfg.crawler.respect_gitignore is True  # default


def test_to_dict_roundtrip():
    """Test that to_dict produces data that from_dict can reconstruct."""
    original = DocmakerConfig()
    data = original.to_dict()
    restored = DocmakerConfig.from_dict(data)

    assert restored.source_dir == original.source_dir
    assert restored.llm.provider == original.llm.provider
    assert restored.llm.model == original.llm.model
    assert restored.crawler.respect_gitignore == original.crawler.respect_gitignore
    assert restored.output.output_dir == original.output.output_dir


def test_to_dict_structure():
    """Test to_dict returns expected structure."""
    cfg = DocmakerConfig()
    data = cfg.to_dict()

    assert "source_dir" in data
    assert "cache_file" in data
    assert "llm" in data
    assert "crawler" in data
    assert "output" in data
    assert data["llm"]["provider"] == "ollama"
    assert data["crawler"]["respect_gitignore"] is True
    assert data["output"]["generate_index"] is True


def test_from_yaml():
    """Test loading config from a YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "source_dir": "/tmp/src",
                "llm": {"model": "codellama", "enabled": False},
            },
            f,
        )
        f.flush()
        cfg = DocmakerConfig.from_yaml(Path(f.name))

    assert cfg.source_dir == Path("/tmp/src")
    assert cfg.llm.model == "codellama"
    assert cfg.llm.enabled is False


def test_from_yaml_empty_file():
    """Test loading config from an empty YAML file returns defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        cfg = DocmakerConfig.from_yaml(Path(f.name))

    assert cfg.source_dir == Path(".")
    assert cfg.llm.provider == "ollama"


def test_save_and_load():
    """Test saving config to YAML and loading it back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "config.yaml"

        original = DocmakerConfig()
        original.llm.model = "test-model"
        original.crawler.max_file_size_kb = 999
        original.save(path)

        assert path.exists()

        loaded = DocmakerConfig.from_yaml(path)
        assert loaded.llm.model == "test-model"
        assert loaded.crawler.max_file_size_kb == 999


def test_load_with_explicit_path():
    """Test load() with an explicit config path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"llm": {"model": "explicit"}}, f)
        f.flush()
        cfg = DocmakerConfig.load(Path(f.name))

    assert cfg.llm.model == "explicit"


def test_load_returns_defaults_when_no_file():
    """Test load() returns defaults when no config file is found."""
    cfg = DocmakerConfig.load(Path("/nonexistent/config.yaml"))
    assert cfg.source_dir == Path(".")
    assert cfg.llm.provider == "ollama"


def test_load_finds_default_paths():
    """Test load() finds config files at default paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            config_path = Path(tmpdir) / "docmaker.yaml"
            yaml.dump({"llm": {"model": "found-it"}}, open(config_path, "w"))

            cfg = DocmakerConfig.load()
            assert cfg.llm.model == "found-it"
        finally:
            os.chdir(orig_cwd)
