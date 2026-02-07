"""Parser module for extracting symbols from source code."""

from docmaker.parser.base import BaseParser
from docmaker.parser.go_parser import GoParser
from docmaker.parser.java_parser import JavaParser
from docmaker.parser.python_parser import PythonParser
from docmaker.parser.registry import ParserRegistry, get_parser
from docmaker.parser.typescript_parser import TypeScriptParser

__all__ = [
    "BaseParser",
    "GoParser",
    "JavaParser",
    "PythonParser",
    "TypeScriptParser",
    "ParserRegistry",
    "get_parser",
]
