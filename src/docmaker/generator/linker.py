"""Import resolver and linker for creating WikiLinks."""

import logging
from pathlib import Path

from docmaker.models import FileSymbols, ImportDef, SymbolTable

logger = logging.getLogger(__name__)


class ImportLinker:
    """Resolves imports and creates links between symbols."""

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self._import_cache: dict[str, Path | None] = {}

    def resolve_import(self, import_def: ImportDef) -> Path | None:
        """Resolve an import to a file path."""
        if import_def.module in self._import_cache:
            return self._import_cache[import_def.module]

        cls = self.symbol_table.class_index.get(import_def.module)
        if cls:
            self._import_cache[import_def.module] = cls.file_path
            return cls.file_path

        self._import_cache[import_def.module] = None
        return None

    def resolve_type(self, type_name: str, file_symbols: FileSymbols) -> str | None:
        """Resolve a type name to a fully qualified name using file imports."""
        if not type_name:
            return None

        base_type = type_name.split("<")[0].split("[")[0].strip()

        if base_type in self.symbol_table.class_index:
            return base_type

        for imp in file_symbols.imports:
            if imp.module.endswith(f".{base_type}"):
                return imp.module
            if imp.is_wildcard:
                potential_fqn = imp.module.replace(".*", f".{base_type}")
                if potential_fqn in self.symbol_table.class_index:
                    return potential_fqn

        if file_symbols.package:
            local_fqn = f"{file_symbols.package}.{base_type}"
            if local_fqn in self.symbol_table.class_index:
                return local_fqn

        return None

    def get_wikilink(self, type_name: str, file_symbols: FileSymbols) -> str:
        """Get a WikiLink for a type if it exists in the codebase."""
        fqn = self.resolve_type(type_name, file_symbols)
        if fqn:
            cls = self.symbol_table.class_index.get(fqn)
            if cls:
                return f"[[{cls.name}]]"

        return f"`{type_name}`"

    def get_class_link(self, class_name: str) -> str:
        """Get a WikiLink for a class by name."""
        for fqn, cls in self.symbol_table.class_index.items():
            if cls.name == class_name:
                return f"[[{class_name}]]"

        return f"`{class_name}`"

    def get_method_link(self, class_name: str, method_name: str) -> str:
        """Get a WikiLink to a specific method."""
        for fqn, cls in self.symbol_table.class_index.items():
            if cls.name == class_name:
                return f"[[{class_name}#{method_name}]]"

        return f"`{class_name}.{method_name}()`"

    def find_callers(self, class_name: str, method_name: str) -> list[tuple[str, str]]:
        """Find all methods that call the given method (basic text search)."""
        callers = []
        target = f"{method_name}("

        for file_symbols in self.symbol_table.files.values():
            for cls in file_symbols.classes:
                for method in cls.methods:
                    if target in method.source_code and not (
                        cls.name == class_name and method.name == method_name
                    ):
                        callers.append((cls.name, method.name))

        return callers

    def find_usages(self, class_name: str) -> list[tuple[str, str]]:
        """Find all places where a class is used."""
        usages = []

        for file_symbols in self.symbol_table.files.values():
            for imp in file_symbols.imports:
                if imp.module.endswith(f".{class_name}"):
                    for cls in file_symbols.classes:
                        usages.append((cls.name, "imports"))
                        break

        return usages
