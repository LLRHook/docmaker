"""Base parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from docmaker.models import FileSymbols, Language, SourceFile


class BaseParser(ABC):
    """Abstract base class for language-specific parsers."""

    @property
    @abstractmethod
    def language(self) -> Language:
        """The language this parser handles."""
        pass

    @abstractmethod
    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a source file and extract symbols."""
        pass

    @abstractmethod
    def can_parse(self, file: SourceFile) -> bool:
        """Check if this parser can handle the given file."""
        pass

    def read_file_content(self, path: Path) -> str:
        """Read the content of a file."""
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()

    def get_line_content(self, content: str, start_line: int, end_line: int) -> str:
        """Extract lines from content."""
        lines = content.splitlines()
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        return "\n".join(lines[start_idx:end_idx])
