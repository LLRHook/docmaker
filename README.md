# Docmaker

Generate Obsidian-compatible documentation from your codebase.

## Features

- **Intelligent Crawling**: Traverses your repository while respecting `.gitignore` and custom ignore patterns
- **LLM Classification**: Optionally uses local LLMs (Ollama, LM Studio) or cloud APIs (OpenAI, Anthropic) to classify files
- **Java/Spring Boot Support**: Parses Java files using Tree-sitter, extracts classes, methods, and REST endpoints
- **Obsidian Integration**: Generates interlinked markdown files with WikiLinks
- **Incremental Updates**: Only process changed files for faster regeneration

## Installation

```bash
pip install docmaker
```

Or for development:

```bash
git clone <repo>
cd docmaker
pip install -e ".[dev]"
```

## Quick Start

1. Initialize a configuration file (optional):
   ```bash
   docmaker init
   ```

2. Generate documentation:
   ```bash
   docmaker generate /path/to/your/codebase
   ```

3. Open the `docs/` folder in Obsidian

## Usage

### Generate Documentation

```bash
# Full generation
docmaker generate /path/to/source

# Incremental (only changed files)
docmaker generate /path/to/source --incremental

# Custom output directory
docmaker generate /path/to/source -o /path/to/output

# Without LLM classification
docmaker generate /path/to/source --no-llm
```

### Scan Repository

```bash
docmaker scan /path/to/source
```

### Clear Cache

```bash
docmaker clear-cache /path/to/source
```

## Configuration

Create a `docmaker.yaml` file in your project:

```yaml
source_dir: "."

llm:
  provider: "ollama"  # ollama, lmstudio, openai, anthropic
  model: "llama3.2"
  base_url: "http://localhost:11434"
  enabled: true

crawler:
  respect_gitignore: true
  custom_ignore_patterns:
    - "*.test.java"
    - "**/test/**"
  include_extensions:
    - ".java"
    - ".py"

output:
  output_dir: "./docs"
  mirror_source_structure: true
  include_source_snippets: true
```

## Supported Languages

- Java (with Spring Boot endpoint extraction)
- More coming soon...

## License

MIT
