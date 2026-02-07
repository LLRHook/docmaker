"""Parser registry for managing language-specific parsers."""

import logging

from docmaker.models import FileSymbols, Language, SourceFile
from docmaker.parser.base import BaseParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for language-specific parsers."""

    def __init__(self):
        self._parsers: dict[Language, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser for a language."""
        self._parsers[parser.language] = parser
        logger.debug(f"Registered parser for {parser.language.value}")

    def get_parser(self, language: Language) -> BaseParser | None:
        """Get the parser for a specific language."""
        return self._parsers.get(language)

    def can_parse(self, file: SourceFile) -> bool:
        """Check if any registered parser can handle the file."""
        parser = self._parsers.get(file.language)
        return parser is not None and parser.can_parse(file)

    def parse(self, file: SourceFile) -> FileSymbols | None:
        """Parse a file using the appropriate parser."""
        parser = self._parsers.get(file.language)
        if parser and parser.can_parse(file):
            try:
                return parser.parse(file)
            except Exception as e:
                logger.error(f"Failed to parse {file.path}: {e}")
                return None
        return None

    @property
    def supported_languages(self) -> list[Language]:
        """Get list of supported languages."""
        return list(self._parsers.keys())


_default_registry: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    """Get the default parser registry with all parsers registered."""
    global _default_registry

    if _default_registry is None:
        _default_registry = ParserRegistry()

        from docmaker.parser.go_parser import GoParser
        from docmaker.parser.java_parser import JavaParser
        from docmaker.parser.python_parser import PythonParser
        from docmaker.parser.typescript_parser import TypeScriptParser

        _default_registry.register(GoParser())
        _default_registry.register(JavaParser())
        _default_registry.register(PythonParser())
        _default_registry.register(TypeScriptParser())

    return _default_registry


def get_parser(language: Language) -> BaseParser | None:
    """Convenience function to get a parser for a language."""
    return get_parser_registry().get_parser(language)
