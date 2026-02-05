# Docmaker

Generate Obsidian-compatible documentation from your codebase.

## Features

- **Desktop Application**: Interactive knowledge graph visualization of your codebase
- **Graph Exploration**: Zoom, pan, filter, and click-to-navigate to source files
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

# Build the frontend (required for desktop app)
cd frontend
npm install
npm run build
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

## Desktop Application

Launch the interactive knowledge graph viewer:

```bash
docmaker app
```

The desktop app provides a visual representation of your codebase as an interactive graph. You can explore relationships between classes, interfaces, packages, and REST endpoints.

### Key Features

- **Interactive Graph**: Zoom, pan, and drag nodes to explore your codebase structure
- **Multiple Layouts**: Force-directed (default), circular, and grid layouts
- **Filtering**: Filter by node type (class, interface, endpoint, package, file)
- **Node Details**: Click any node to view detailed information
- **Source Navigation**: Jump directly to source files from the graph

### Node Types

- **Class**: Java classes with their methods and fields
- **Interface**: Java interfaces
- **Endpoint**: REST API endpoints (Spring Boot)
- **Package**: Java packages
- **File**: Source files

### Edge Types

- **extends**: Class inheritance
- **implements**: Interface implementation
- **imports**: Import dependencies
- **contains**: Package/file containment

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

### Desktop App

```bash
# Launch desktop app
docmaker app

# Launch with project pre-loaded
docmaker app --project /path/to/source

# Development mode (connects to Vite dev server)
docmaker app --dev
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
