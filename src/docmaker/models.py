"""Data models for docmaker."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FileCategory(str, Enum):
    """Category of a source file."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    CONFIG = "config"
    TEST = "test"
    IGNORE = "ignore"
    UNKNOWN = "unknown"


class Language(str, Enum):
    """Supported programming languages."""

    JAVA = "java"
    PYTHON = "python"
    GO = "go"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    KOTLIN = "kotlin"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> "Language":
        """Determine language from file extension."""
        mapping = {
            ".java": cls.JAVA,
            ".py": cls.PYTHON,
            ".go": cls.GO,
            ".ts": cls.TYPESCRIPT,
            ".tsx": cls.TYPESCRIPT,
            ".js": cls.JAVASCRIPT,
            ".jsx": cls.JAVASCRIPT,
            ".kt": cls.KOTLIN,
            ".kts": cls.KOTLIN,
        }
        return mapping.get(ext.lower(), cls.UNKNOWN)


@dataclass
class SourceFile:
    """Represents a source file in the repository."""

    path: Path
    relative_path: Path
    language: Language
    category: FileCategory = FileCategory.UNKNOWN
    size_bytes: int = 0
    hash: str = ""
    header_content: str = ""


@dataclass
class Parameter:
    """Represents a function/method parameter."""

    name: str
    type: str | None = None
    default: str | None = None
    description: str | None = None


@dataclass
class Annotation:
    """Represents a Java/Kotlin annotation."""

    name: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass
class FunctionDef:
    """Represents a function or method definition."""

    name: str
    file_path: Path
    line_number: int
    end_line: int
    parameters: list[Parameter] = field(default_factory=list)
    return_type: str | None = None
    docstring: str | None = None
    annotations: list[Annotation] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    source_code: str = ""
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassDef:
    """Represents a class definition."""

    name: str
    file_path: Path
    line_number: int
    end_line: int
    package: str | None = None
    superclass: str | None = None
    interfaces: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    docstring: str | None = None
    methods: list[FunctionDef] = field(default_factory=list)
    fields: list["FieldDef"] = field(default_factory=list)
    source_code: str = ""


@dataclass
class FieldDef:
    """Represents a field/property definition."""

    name: str
    type: str | None = None
    annotations: list[Annotation] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class EndpointDef:
    """Represents a REST API endpoint."""

    http_method: str
    path: str
    handler_method: str
    handler_class: str
    file_path: Path
    line_number: int
    parameters: list[Parameter] = field(default_factory=list)
    request_body: str | None = None
    response_type: str | None = None
    description: str | None = None
    authentication: str | None = None
    annotations: list[Annotation] = field(default_factory=list)
    source_code: str = ""


@dataclass
class ImportDef:
    """Represents an import statement."""

    module: str
    alias: str | None = None
    is_wildcard: bool = False
    line_number: int = 0


@dataclass
class FileSymbols:
    """All symbols extracted from a single file."""

    file: SourceFile
    package: str | None = None
    imports: list[ImportDef] = field(default_factory=list)
    classes: list[ClassDef] = field(default_factory=list)
    functions: list[FunctionDef] = field(default_factory=list)
    endpoints: list[EndpointDef] = field(default_factory=list)


@dataclass
class SymbolTable:
    """Global symbol table containing all extracted symbols."""

    files: dict[Path, FileSymbols] = field(default_factory=dict)
    class_index: dict[str, ClassDef] = field(default_factory=dict)
    endpoint_index: dict[str, EndpointDef] = field(default_factory=dict)
    function_index: dict[str, FunctionDef] = field(default_factory=dict)

    def add_file_symbols(self, symbols: FileSymbols) -> None:
        """Add symbols from a file to the table."""
        self.files[symbols.file.path] = symbols

        for cls in symbols.classes:
            fqn = f"{symbols.package}.{cls.name}" if symbols.package else cls.name
            self.class_index[fqn] = cls

            for method in cls.methods:
                method_fqn = f"{fqn}.{method.name}"
                self.function_index[method_fqn] = method

        for func in symbols.functions:
            fqn = f"{symbols.package}.{func.name}" if symbols.package else func.name
            self.function_index[fqn] = func

        for endpoint in symbols.endpoints:
            key = f"{endpoint.http_method}:{endpoint.path}"
            self.endpoint_index[key] = endpoint

    def resolve_import(self, import_path: str) -> ClassDef | None:
        """Resolve an import to a class definition."""
        return self.class_index.get(import_path)

    def get_endpoints_by_class(self, class_name: str) -> list[EndpointDef]:
        """Get all endpoints handled by a specific class."""
        return [ep for ep in self.endpoint_index.values() if ep.handler_class == class_name]
