"""Tests for parser registry."""

from pathlib import Path
from unittest.mock import MagicMock

from docmaker.models import FileSymbols, Language, SourceFile
from docmaker.parser.base import BaseParser
from docmaker.parser.registry import ParserRegistry, get_parser, get_parser_registry


class FakeParser(BaseParser):
    """Fake parser for testing."""

    @property
    def language(self) -> Language:
        return Language.GO

    def parse(self, file: SourceFile) -> FileSymbols:
        return FileSymbols(file=file)

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == Language.GO


class TestParserRegistry:
    def test_register_and_get(self):
        registry = ParserRegistry()
        parser = FakeParser()
        registry.register(parser)
        assert registry.get_parser(Language.GO) is parser

    def test_get_parser_unregistered(self):
        registry = ParserRegistry()
        assert registry.get_parser(Language.GO) is None

    def test_can_parse_true(self):
        registry = ParserRegistry()
        registry.register(FakeParser())
        sf = SourceFile(
            path=Path("/test/main.go"),
            relative_path=Path("main.go"),
            language=Language.GO,
        )
        assert registry.can_parse(sf) is True

    def test_can_parse_false_no_parser(self):
        registry = ParserRegistry()
        sf = SourceFile(
            path=Path("/test/main.go"),
            relative_path=Path("main.go"),
            language=Language.GO,
        )
        assert registry.can_parse(sf) is False

    def test_can_parse_false_wrong_language(self):
        registry = ParserRegistry()
        registry.register(FakeParser())
        sf = SourceFile(
            path=Path("/test/main.py"),
            relative_path=Path("main.py"),
            language=Language.PYTHON,
        )
        assert registry.can_parse(sf) is False

    def test_parse_returns_symbols(self):
        registry = ParserRegistry()
        registry.register(FakeParser())
        sf = SourceFile(
            path=Path("/test/main.go"),
            relative_path=Path("main.go"),
            language=Language.GO,
        )
        result = registry.parse(sf)
        assert result is not None
        assert result.file is sf

    def test_parse_returns_none_no_parser(self):
        registry = ParserRegistry()
        sf = SourceFile(
            path=Path("/test/main.go"),
            relative_path=Path("main.go"),
            language=Language.GO,
        )
        assert registry.parse(sf) is None

    def test_parse_handles_exception(self):
        registry = ParserRegistry()
        mock_parser = MagicMock(spec=BaseParser)
        mock_parser.language = Language.GO
        mock_parser.can_parse.return_value = True
        mock_parser.parse.side_effect = ValueError("parse error")
        registry.register(mock_parser)

        sf = SourceFile(
            path=Path("/test/main.go"),
            relative_path=Path("main.go"),
            language=Language.GO,
        )
        result = registry.parse(sf)
        assert result is None

    def test_supported_languages(self):
        registry = ParserRegistry()
        registry.register(FakeParser())
        assert Language.GO in registry.supported_languages


def test_get_parser_registry_returns_default():
    """Test that get_parser_registry returns a registry with parsers registered."""
    registry = get_parser_registry()
    assert Language.JAVA in registry.supported_languages
    assert Language.PYTHON in registry.supported_languages
    assert Language.TYPESCRIPT in registry.supported_languages


def test_get_parser_convenience():
    """Test the get_parser convenience function."""
    parser = get_parser(Language.PYTHON)
    assert parser is not None
    assert parser.language == Language.PYTHON


def test_get_parser_convenience_unknown():
    """Test get_parser returns None for unknown language."""
    parser = get_parser(Language.UNKNOWN)
    assert parser is None
