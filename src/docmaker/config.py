"""Configuration management for docmaker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    """Configuration for the LLM provider."""

    provider: str = "ollama"
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    timeout: int = 30
    enabled: bool = True


@dataclass
class CrawlerConfig:
    """Configuration for the file crawler."""

    respect_gitignore: bool = True
    custom_ignore_patterns: list[str] = field(default_factory=list)
    include_extensions: list[str] = field(
        default_factory=lambda: [".java", ".py", ".go", ".ts", ".js", ".kt"]
    )
    max_file_size_kb: int = 500
    header_lines_for_classification: int = 50


@dataclass
class OutputConfig:
    """Configuration for the output generation."""

    output_dir: Path = field(default_factory=lambda: Path("./docs"))
    mirror_source_structure: bool = True
    include_source_snippets: bool = True
    max_snippet_lines: int = 50
    generate_index: bool = True


@dataclass
class DocmakerConfig:
    """Main configuration for docmaker."""

    source_dir: Path = field(default_factory=lambda: Path("."))
    llm: LLMConfig = field(default_factory=LLMConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    cache_file: Path = field(default_factory=lambda: Path(".docmaker_cache.json"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocmakerConfig":
        """Create configuration from a dictionary."""
        llm_data = data.get("llm", {})
        crawler_data = data.get("crawler", {})
        output_data = data.get("output", {})

        llm_config = LLMConfig(
            provider=llm_data.get("provider", "ollama"),
            model=llm_data.get("model", "llama3.2"),
            base_url=llm_data.get("base_url", "http://localhost:11434"),
            api_key=llm_data.get("api_key"),
            timeout=llm_data.get("timeout", 30),
            enabled=llm_data.get("enabled", True),
        )

        crawler_config = CrawlerConfig(
            respect_gitignore=crawler_data.get("respect_gitignore", True),
            custom_ignore_patterns=crawler_data.get("custom_ignore_patterns", []),
            include_extensions=crawler_data.get(
                "include_extensions", [".java", ".py", ".go", ".ts", ".js", ".kt"]
            ),
            max_file_size_kb=crawler_data.get("max_file_size_kb", 500),
            header_lines_for_classification=crawler_data.get("header_lines_for_classification", 50),
        )

        output_config = OutputConfig(
            output_dir=Path(output_data.get("output_dir", "./docs")),
            mirror_source_structure=output_data.get("mirror_source_structure", True),
            include_source_snippets=output_data.get("include_source_snippets", True),
            max_snippet_lines=output_data.get("max_snippet_lines", 50),
            generate_index=output_data.get("generate_index", True),
        )

        return cls(
            source_dir=Path(data.get("source_dir", ".")),
            llm=llm_config,
            crawler=crawler_config,
            output=output_config,
            cache_file=Path(data.get("cache_file", ".docmaker_cache.json")),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "DocmakerConfig":
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "DocmakerConfig":
        """Load configuration from file or return defaults."""
        if config_path and config_path.exists():
            return cls.from_yaml(config_path)

        default_paths = [
            Path("docmaker.yaml"),
            Path("docmaker.yml"),
            Path(".docmaker.yaml"),
            Path(".docmaker.yml"),
        ]

        for path in default_paths:
            if path.exists():
                return cls.from_yaml(path)

        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to a dictionary."""
        return {
            "source_dir": str(self.source_dir),
            "cache_file": str(self.cache_file),
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "base_url": self.llm.base_url,
                "api_key": self.llm.api_key,
                "timeout": self.llm.timeout,
                "enabled": self.llm.enabled,
            },
            "crawler": {
                "respect_gitignore": self.crawler.respect_gitignore,
                "custom_ignore_patterns": self.crawler.custom_ignore_patterns,
                "include_extensions": self.crawler.include_extensions,
                "max_file_size_kb": self.crawler.max_file_size_kb,
                "header_lines_for_classification": self.crawler.header_lines_for_classification,
            },
            "output": {
                "output_dir": str(self.output.output_dir),
                "mirror_source_structure": self.output.mirror_source_structure,
                "include_source_snippets": self.output.include_source_snippets,
                "max_snippet_lines": self.output.max_snippet_lines,
                "generate_index": self.output.generate_index,
            },
        }

    def save(self, path: Path) -> None:
        """Save configuration to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
