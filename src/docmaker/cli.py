"""Command-line interface for docmaker."""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from docmaker import __version__
from docmaker.config import DocmakerConfig
from docmaker.pipeline import Pipeline

console = Console()


def setup_logging(verbose: bool) -> None:
    """Configure logging with rich output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.version_option(version=__version__)
def main():
    """Docmaker - Generate Obsidian documentation from your codebase."""
    pass


@main.command()
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory for documentation (default: ./docs)",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--incremental/--full",
    default=False,
    help="Only process changed files (default: full regeneration)",
)
@click.option(
    "--no-llm",
    is_flag=True,
    default=False,
    help="Disable LLM classification",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output",
)
def generate(
    source_dir: Path,
    output: Path | None,
    config: Path | None,
    incremental: bool,
    no_llm: bool,
    verbose: bool,
) -> None:
    """Generate documentation for a codebase.

    SOURCE_DIR is the path to the source code repository.
    """
    setup_logging(verbose)

    try:
        cfg = DocmakerConfig.load(config)

        cfg.source_dir = source_dir.resolve()

        if output:
            cfg.output.output_dir = output.resolve()

        if no_llm:
            cfg.llm.enabled = False

        pipeline = Pipeline(cfg, console)
        generated = pipeline.run(incremental=incremental)

        if generated:
            sys.exit(0)
        else:
            sys.exit(0)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("docmaker.yaml"),
    help="Output path for configuration file",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing configuration file",
)
def init(output: Path, force: bool) -> None:
    """Initialize a new docmaker configuration file."""
    if output.exists() and not force:
        console.print(f"[yellow]Configuration file already exists: {output}[/yellow]")
        console.print("Use --force to overwrite")
        sys.exit(1)

    config = DocmakerConfig()
    config.save(output)

    console.print(f"[green]OK[/green] Created configuration file: {output}")
    console.print("\nEdit this file to customize your settings, then run:")
    console.print("  [cyan]docmaker generate <source_dir>[/cyan]")


@main.command()
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to configuration file",
)
def scan(source_dir: Path, config: Path | None) -> None:
    """Scan a codebase and show statistics without generating docs."""
    setup_logging(False)

    try:
        cfg = DocmakerConfig.load(config)
        cfg.source_dir = source_dir.resolve()
        cfg.llm.enabled = False

        from docmaker.crawler import FileCrawler

        crawler = FileCrawler(cfg)
        files = crawler.crawl()

        console.print(f"\n[bold]Scan Results for:[/bold] {source_dir}\n")

        by_language: dict[str, int] = {}
        by_category: dict[str, int] = {}

        for f in files:
            lang = f.language.value
            cat = f.category.value
            by_language[lang] = by_language.get(lang, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1

        console.print("[bold]By Language:[/bold]")
        for lang, count in sorted(by_language.items(), key=lambda x: -x[1]):
            console.print(f"  {lang}: {count}")

        console.print("\n[bold]By Category:[/bold]")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            console.print(f"  {cat}: {count}")

        console.print(f"\n[bold]Total Files:[/bold] {len(files)}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.option(
    "-p",
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to project to load on startup",
)
@click.option(
    "--dev",
    is_flag=True,
    default=False,
    help="Run in development mode (connect to Vite dev server)",
)
def app(project: Path | None, dev: bool) -> None:
    """Launch the Docmaker desktop application with knowledge graph visualization."""
    from docmaker.app.main import run_app

    project_path = str(project.resolve()) if project else None
    sys.exit(run_app(dev_mode=dev, project_path=project_path))


@main.command()
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to configuration file",
)
def clear_cache(source_dir: Path, config: Path | None) -> None:
    """Clear the incremental update cache."""
    try:
        cfg = DocmakerConfig.load(config)
        cfg.source_dir = source_dir.resolve()

        from docmaker.cache import CacheManager

        cache = CacheManager(cfg.source_dir / cfg.cache_file)
        cache.clear()

        console.print("[green]OK[/green] Cache cleared")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
