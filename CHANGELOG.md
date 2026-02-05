# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-02-05

### Added

- fCoSE force-directed graph layout with quality and node sizing settings
- Collapsible sidebar node groups with localStorage persistence
- Swagger-style endpoint details panel with parameter tables, sample JSON, and example requests
- Fallback class lookup by simple name in backend IPC

### Changed

- Default graph layout switched from CoSE to fCoSE

## [0.1.0] - 2025-02-05

### Added

- Initial release
- File crawler with `.gitignore` support and custom ignore patterns
- LLM-based file classification (Ollama, LM Studio, OpenAI, Anthropic)
- Java parser using Tree-sitter with Spring Boot endpoint extraction
- Markdown generator with Obsidian WikiLinks
- Import linker for type resolution across files
- Incremental update support with file hash caching
- CLI with `generate`, `scan`, and `clear-cache` commands
