"""Main pipeline orchestrator for docmaker."""

import logging
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from docmaker.cache import CacheManager
from docmaker.config import DocmakerConfig
from docmaker.crawler import FileCrawler
from docmaker.generator.markdown import MarkdownGenerator
from docmaker.llm import FileClassifier, SymbolSummarizer
from docmaker.models import FileCategory, SourceFile, SymbolTable
from docmaker.parser.registry import get_parser_registry

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the complete code-to-documentation pipeline."""

    def __init__(self, config: DocmakerConfig, console: Console | None = None):
        self.config = config
        self.console = console or Console()
        self.crawler = FileCrawler(config)
        self.classifier = FileClassifier(config.llm)
        self.summarizer = SymbolSummarizer(config.llm)
        self.cache = CacheManager(config.source_dir / config.cache_file)
        self.parser_registry = get_parser_registry()
        self.symbol_table = SymbolTable()

    def run(self, incremental: bool = False) -> list[Path]:
        """Run the complete pipeline."""
        self.console.print("\n[bold blue]Docmaker - Code to Knowledge Pipeline[/bold blue]\n")

        files = self._crawl_files()
        if not files:
            self.console.print("[yellow]No source files found.[/yellow]")
            return []

        if incremental:
            files = self._filter_changed_files(files)
            if not files:
                self.console.print("[green]All files are up to date.[/green]")
                return []

        files = self._classify_files(files)

        relevant_files = [
            f for f in files if f.category not in (FileCategory.IGNORE, FileCategory.TEST)
        ]

        self._parse_files(relevant_files)

        self._summarize_symbols()

        generated = self._generate_docs()

        self._update_cache(files)

        self._print_summary(files, generated)

        return generated

    def _crawl_files(self) -> list[SourceFile]:
        """Crawl the source directory for files."""
        with self.console.status("[bold green]Scanning repository..."):
            files = self.crawler.crawl()
            self.console.print(f"[green]OK[/green] Found {len(files)} source files")
        return files

    def _filter_changed_files(self, files: list[SourceFile]) -> list[SourceFile]:
        """Filter to only changed files (incremental mode)."""
        changed = self.cache.get_changed_files(files)
        deleted = self.cache.get_deleted_files(files)

        if deleted:
            self.console.print(f"[yellow]Detected {len(deleted)} deleted files[/yellow]")
            for path in deleted:
                self.cache.remove_file(Path(path))

        self.console.print(
            f"[cyan]Incremental mode: {len(changed)}/{len(files)} files changed[/cyan]"
        )
        return changed

    def _classify_files(self, files: list[SourceFile]) -> list[SourceFile]:
        """Classify files using heuristics and optionally LLM."""
        if not self.config.llm.enabled:
            self.console.print("[dim]LLM classification disabled, using heuristics only[/dim]")
            return files

        if not self.classifier.is_llm_available():
            self.console.print("[yellow]Warning: LLM not available, using heuristics only[/yellow]")
            return files

        unknown_files = [f for f in files if f.category == FileCategory.UNKNOWN]
        if not unknown_files:
            return files

        self.console.print(f"[cyan]Classifying {len(unknown_files)} files with LLM...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Classifying...", total=len(unknown_files))

            for file in unknown_files:
                file.category = self.classifier.classify(file)
                progress.advance(task)

        return files

    def _parse_files(self, files: list[SourceFile]) -> None:
        """Parse files and extract symbols."""
        parseable = [f for f in files if self.parser_registry.can_parse(f)]

        if not parseable:
            self.console.print("[yellow]No parseable files found[/yellow]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Parsing files...", total=len(parseable))

            for file in parseable:
                symbols = self.parser_registry.parse(file)
                if symbols:
                    self.symbol_table.add_file_symbols(symbols)
                progress.advance(task)

        self.console.print(
            f"[green]OK[/green] Parsed {len(self.symbol_table.files)} files, "
            f"found {len(self.symbol_table.class_index)} classes, "
            f"{len(self.symbol_table.endpoint_index)} endpoints"
        )

    def _summarize_symbols(self) -> None:
        """Generate LLM summaries for classes and functions."""
        if not self.config.llm.enabled:
            self.console.print("[dim]LLM summarization disabled[/dim]")
            return

        if not self.summarizer.is_available():
            self.console.print("[yellow]Warning: LLM not available for summarization[/yellow]")
            return

        classes = list(self.symbol_table.class_index.values())
        functions = [
            (func, None)
            for func in self.symbol_table.function_index.values()
            if not any(
                func in cls.methods for cls in self.symbol_table.class_index.values()
            )
        ]
        for cls in classes:
            for method in cls.methods:
                functions.append((method, cls.name))

        total = len(classes) + len(functions)
        if total == 0:
            return

        self.console.print(
            f"[cyan]Summarizing {len(classes)} classes "
            f"and {len(functions)} functions with LLM...[/cyan]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Summarizing...", total=total)

            for cls in classes:
                summary = self.summarizer.summarize_class(cls)
                if summary:
                    cls.summary = summary
                progress.advance(task)

            for func, class_name in functions:
                summary = self.summarizer.summarize_function(func, class_name)
                if summary:
                    func.summary = summary
                progress.advance(task)

        summarized_classes = sum(1 for c in classes if c.summary)
        summarized_funcs = sum(1 for f, _ in functions if f.summary)
        self.console.print(
            f"[green]OK[/green] Summarized {summarized_classes} classes, "
            f"{summarized_funcs} functions"
        )

    def _generate_docs(self) -> list[Path]:
        """Generate markdown documentation."""
        if not self.symbol_table.files:
            self.console.print("[yellow]No symbols to document[/yellow]")
            return []

        generator = MarkdownGenerator(self.config.output, self.symbol_table)

        with self.console.status("[bold green]Generating documentation..."):
            generated = generator.generate_all()

        self.console.print(f"[green]OK[/green] Generated {len(generated)} documentation files")
        return generated

    def _update_cache(self, files: list[SourceFile]) -> None:
        """Update the cache with processed files."""
        for file in files:
            self.cache.update_file(file)
        self.cache.save()

    def _print_summary(self, files: list[SourceFile], generated: list[Path]) -> None:
        """Print a summary of the pipeline run."""
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"  • Source files processed: {len(files)}")
        self.console.print(f"  • Classes documented: {len(self.symbol_table.class_index)}")
        self.console.print(f"  • Endpoints documented: {len(self.symbol_table.endpoint_index)}")
        self.console.print(f"  • Markdown files generated: {len(generated)}")
        self.console.print(f"  • Output directory: {self.config.output.output_dir.resolve()}")
        self.console.print("\n[bold green]Documentation generated successfully![/bold green]\n")
