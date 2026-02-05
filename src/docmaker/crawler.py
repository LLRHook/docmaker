"""File crawler for traversing repositories and identifying source files."""

import hashlib
import os
from pathlib import Path

import pathspec

from docmaker.config import DocmakerConfig
from docmaker.models import FileCategory, Language, SourceFile


class FileCrawler:
    """Crawls a repository and identifies relevant source files."""

    def __init__(self, config: DocmakerConfig):
        self.config = config
        self.source_dir = config.source_dir.resolve()
        self._gitignore_spec: pathspec.PathSpec | None = None
        self._custom_spec: pathspec.PathSpec | None = None
        self._load_ignore_patterns()

    def _load_ignore_patterns(self) -> None:
        """Load .gitignore and custom ignore patterns."""
        patterns: list[str] = []

        if self.config.crawler.respect_gitignore:
            gitignore_path = self.source_dir / ".gitignore"
            if gitignore_path.exists():
                with open(gitignore_path) as f:
                    patterns.extend(
                        line.strip() for line in f if line.strip() and not line.startswith("#")
                    )

        always_ignore = [
            ".git",
            ".git/**",
            "node_modules",
            "node_modules/**",
            "__pycache__",
            "__pycache__/**",
            "*.pyc",
            ".idea",
            ".idea/**",
            ".vscode",
            ".vscode/**",
            "target",
            "target/**",
            "build",
            "build/**",
            "dist",
            "dist/**",
            ".gradle",
            ".gradle/**",
            "*.class",
            "*.jar",
            "*.war",
        ]
        patterns.extend(always_ignore)

        if patterns:
            self._gitignore_spec = pathspec.PathSpec.from_lines("gitignore", patterns)

        if self.config.crawler.custom_ignore_patterns:
            self._custom_spec = pathspec.PathSpec.from_lines(
                "gitignore", self.config.crawler.custom_ignore_patterns
            )

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        try:
            relative = path.relative_to(self.source_dir)
            relative_str = str(relative).replace("\\", "/")
        except ValueError:
            return True

        if self._gitignore_spec and self._gitignore_spec.match_file(relative_str):
            return True

        if self._custom_spec and self._custom_spec.match_file(relative_str):
            return True

        return False

    def _is_relevant_extension(self, path: Path) -> bool:
        """Check if the file has a relevant extension."""
        return path.suffix.lower() in self.config.crawler.include_extensions

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of file contents."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _read_header(self, path: Path, num_lines: int) -> str:
        """Read the first N lines of a file for classification."""
        lines = []
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i >= num_lines:
                        break
                    lines.append(line)
        except Exception:
            pass
        return "".join(lines)

    def _categorize_by_path(self, path: Path) -> FileCategory:
        """Quick categorization based on file path patterns."""
        path_str = str(path).lower().replace("\\", "/")

        test_patterns = [
            "/test/",
            "/tests/",
            "/__tests__/",
            "/spec/",
            ".test.",
            ".spec.",
            "_test.",
            "_spec.",
            "test_",
        ]
        if any(pattern in path_str for pattern in test_patterns):
            return FileCategory.TEST

        config_patterns = [
            "config",
            "configuration",
            "settings",
            "properties",
            "application.yml",
            "application.yaml",
            "application.properties",
            ".env",
            "pom.xml",
            "build.gradle",
            "package.json",
            "tsconfig.json",
        ]
        if any(pattern in path_str for pattern in config_patterns):
            return FileCategory.CONFIG

        frontend_patterns = [
            "/frontend/",
            "/web/",
            "/ui/",
            "/client/",
            "/components/",
            "/pages/",
            "/views/",
            ".tsx",
            ".jsx",
            ".vue",
            ".svelte",
        ]
        if any(pattern in path_str for pattern in frontend_patterns):
            return FileCategory.FRONTEND

        backend_patterns = [
            "/backend/",
            "/server/",
            "/api/",
            "/service/",
            "/controller/",
            "/repository/",
            "/domain/",
            "/entity/",
            "/model/",
            "controller.java",
            "service.java",
            "repository.java",
        ]
        if any(pattern in path_str for pattern in backend_patterns):
            return FileCategory.BACKEND

        return FileCategory.UNKNOWN

    def crawl(self) -> list[SourceFile]:
        """Crawl the source directory and return a list of relevant files."""
        files: list[SourceFile] = []
        max_size = self.config.crawler.max_file_size_kb * 1024

        for root, dirs, filenames in os.walk(self.source_dir):
            root_path = Path(root)

            dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d)]

            for filename in filenames:
                file_path = root_path / filename

                if self._should_ignore(file_path):
                    continue

                if not self._is_relevant_extension(file_path):
                    continue

                try:
                    stat = file_path.stat()
                    if stat.st_size > max_size:
                        continue
                    size_bytes = stat.st_size
                except OSError:
                    continue

                relative_path = file_path.relative_to(self.source_dir)
                language = Language.from_extension(file_path.suffix)
                category = self._categorize_by_path(file_path)

                header_content = ""
                if self.config.llm.enabled:
                    header_content = self._read_header(
                        file_path, self.config.crawler.header_lines_for_classification
                    )

                file_hash = self._compute_hash(file_path)

                source_file = SourceFile(
                    path=file_path,
                    relative_path=relative_path,
                    language=language,
                    category=category,
                    size_bytes=size_bytes,
                    hash=file_hash,
                    header_content=header_content,
                )
                files.append(source_file)

        return files
