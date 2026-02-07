"""Parser module for extracting symbols from source code."""

from docmaker.parser.base import BaseParser
from docmaker.parser.java_parser import JavaParser
from docmaker.parser.javascript_parser import JavaScriptParser
from docmaker.parser.kotlin_parser import KotlinParser
from docmaker.parser.python_parser import PythonParser
from docmaker.parser.registry import ParserRegistry, get_parser
from docmaker.parser.typescript_parser import TypeScriptParser

__all__ = [
    "BaseParser",
    "JavaParser",
    "JavaScriptParser",
    "KotlinParser",
    "PythonParser",
    "TypeScriptParser",
    "ParserRegistry",
    "get_parser",
]
