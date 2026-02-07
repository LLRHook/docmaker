"""Go parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_go as tsgo
from tree_sitter import Language, Node, Parser

from docmaker.models import (
    ClassDef,
    FieldDef,
    FileSymbols,
    FunctionDef,
    ImportDef,
    Parameter,
    SourceFile,
)
from docmaker.models import (
    Language as LangEnum,
)
from docmaker.parser.base import BaseParser

logger = logging.getLogger(__name__)

GO_LANGUAGE = Language(tsgo.language())


class GoParser(BaseParser):
    """Parser for Go source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(GO_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.GO

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.GO

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a Go file and extract all symbols."""
        content = self.read_file_content(file.path)
        tree = self._parser.parse(content.encode("utf-8"))

        symbols = FileSymbols(file=file)
        symbols.package = self._extract_package(tree.root_node, content)
        symbols.imports = self._extract_imports(tree.root_node, content)
        symbols.classes = self._extract_types(tree.root_node, content, file.path)
        symbols.functions = self._extract_functions(tree.root_node, content, file.path)

        self._attach_methods_to_types(tree.root_node, content, file.path, symbols.classes)

        return symbols

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte : node.end_byte]

    def _extract_package(self, root: Node, content: str) -> str | None:
        """Extract the package declaration."""
        for child in root.children:
            if child.type == "package_clause":
                for subchild in child.children:
                    if subchild.type == "package_identifier":
                        return self._get_node_text(subchild, content)
        return None

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements."""
        imports = []
        for child in root.children:
            if child.type == "import_declaration":
                for subchild in child.children:
                    if subchild.type == "import_spec":
                        imp = self._parse_import_spec(subchild, content)
                        if imp:
                            imports.append(imp)
                    elif subchild.type == "import_spec_list":
                        for spec in subchild.children:
                            if spec.type == "import_spec":
                                imp = self._parse_import_spec(spec, content)
                                if imp:
                                    imports.append(imp)
        return imports

    def _parse_import_spec(self, node: Node, content: str) -> ImportDef | None:
        """Parse a single import spec."""
        module = None
        alias = None

        for child in node.children:
            if child.type == "interpreted_string_literal":
                module = self._get_node_text(child, content).strip('"')
            elif child.type == "package_identifier" or child.type == "dot":
                alias = self._get_node_text(child, content)
            elif child.type == "blank_identifier":
                alias = "_"

        if module:
            return ImportDef(
                module=module,
                alias=alias,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_comment(self, node: Node, content: str) -> str | None:
        """Extract comment before a node."""
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            return self._clean_comment(self._get_node_text(prev, content))
        return None

    def _clean_comment(self, comment: str) -> str:
        """Clean up a Go comment."""
        lines = comment.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("//"):
                line = line[2:].strip()
            elif line.startswith("/*"):
                line = line[2:].strip()
            if line.endswith("*/"):
                line = line[:-2].strip()
            if line.startswith("*"):
                line = line[1:].strip()
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)

    def _extract_types(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract struct and interface type declarations."""
        types = []
        for child in root.children:
            if child.type == "type_declaration":
                for subchild in child.children:
                    if subchild.type == "type_spec":
                        type_def = self._parse_type_spec(subchild, child, content, file_path)
                        if type_def:
                            types.append(type_def)
        return types

    def _parse_type_spec(
        self, node: Node, decl_node: Node, content: str, file_path: Path
    ) -> ClassDef | None:
        """Parse a type spec (struct or interface)."""
        name = None
        is_interface = False
        fields = []
        methods = []

        for child in node.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "struct_type":
                for struct_child in child.children:
                    if struct_child.type == "field_declaration_list":
                        fields = self._extract_struct_fields(struct_child, content)
            elif child.type == "interface_type":
                is_interface = True
                methods = self._extract_interface_methods(child, content, file_path)

        if not name:
            return None

        docstring = self._extract_comment(decl_node, content)
        modifiers = ["interface"] if is_interface else []

        return ClassDef(
            name=name,
            file_path=file_path,
            line_number=decl_node.start_point[0] + 1,
            end_line=decl_node.end_point[0] + 1,
            modifiers=modifiers,
            docstring=docstring,
            fields=fields,
            methods=methods,
            source_code=self._get_node_text(decl_node, content),
        )

    def _extract_struct_fields(self, node: Node, content: str) -> list[FieldDef]:
        """Extract fields from a struct field declaration list."""
        fields = []
        for child in node.children:
            if child.type == "field_declaration":
                field = self._parse_struct_field(child, content)
                if field:
                    fields.append(field)
        return fields

    def _parse_struct_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a single struct field."""
        name = None
        field_type = None

        for child in node.children:
            if child.type == "field_identifier":
                name = self._get_node_text(child, content)
            elif child.type in (
                "type_identifier",
                "pointer_type",
                "slice_type",
                "map_type",
                "array_type",
                "qualified_type",
                "interface_type",
                "struct_type",
                "channel_type",
                "function_type",
            ):
                field_type = self._get_node_text(child, content)

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_interface_methods(
        self, node: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract method signatures from an interface."""
        methods = []
        for child in node.children:
            if child.type == "method_elem":
                method = self._parse_interface_method(child, content, file_path)
                if method:
                    methods.append(method)
        return methods

    def _parse_interface_method(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse an interface method signature."""
        name = None
        parameters = []
        return_type = None

        for child in node.children:
            if child.type == "field_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "parameter_list":
                if name is None:
                    continue
                if parameters:
                    return_type = self._format_return_type(child, content)
                else:
                    parameters = self._parse_parameters(child, content)

        if not name:
            return None

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            modifiers=["abstract"],
            source_code=self._get_node_text(node, content),
        )

    def _extract_functions(
        self, root: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract package-level functions (not methods)."""
        functions = []
        for child in root.children:
            if child.type == "function_declaration":
                func = self._parse_function(child, content, file_path)
                if func:
                    functions.append(func)
        return functions

    def _parse_function(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        parameters = []
        return_type = None
        found_params = False

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "parameter_list":
                if not found_params:
                    parameters = self._parse_parameters(child, content)
                    found_params = True
                else:
                    return_type = self._format_return_type(child, content)
            elif child.type in (
                "type_identifier",
                "pointer_type",
                "slice_type",
                "map_type",
                "array_type",
                "qualified_type",
                "interface_type",
                "struct_type",
            ):
                return_type = self._get_node_text(child, content)

        if not name:
            return None

        docstring = self._extract_comment(node, content)

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

    def _attach_methods_to_types(
        self,
        root: Node,
        content: str,
        file_path: Path,
        types: list[ClassDef],
    ) -> None:
        """Find method declarations and attach them to their receiver types."""
        type_map = {t.name: t for t in types}

        for child in root.children:
            if child.type == "method_declaration":
                receiver_type, method = self._parse_method(child, content, file_path)
                if receiver_type and method and receiver_type in type_map:
                    type_map[receiver_type].methods.append(method)

    def _parse_method(
        self, node: Node, content: str, file_path: Path
    ) -> tuple[str | None, FunctionDef | None]:
        """Parse a method declaration and return (receiver_type, method)."""
        name = None
        receiver_type = None
        parameters = []
        return_type = None
        param_lists_seen = 0

        for child in node.children:
            if child.type == "field_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "parameter_list":
                if param_lists_seen == 0:
                    receiver_type = self._extract_receiver_type(child, content)
                elif param_lists_seen == 1:
                    parameters = self._parse_parameters(child, content)
                else:
                    return_type = self._format_return_type(child, content)
                param_lists_seen += 1
            elif child.type in (
                "type_identifier",
                "pointer_type",
                "slice_type",
                "map_type",
                "array_type",
                "qualified_type",
            ):
                if param_lists_seen >= 2:
                    return_type = self._get_node_text(child, content)

        if not name:
            return None, None

        docstring = self._extract_comment(node, content)

        method = FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        return receiver_type, method

    def _extract_receiver_type(self, node: Node, content: str) -> str | None:
        """Extract the receiver type name from a method's first parameter list."""
        for child in node.children:
            if child.type == "parameter_declaration":
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        return self._get_node_text(subchild, content)
                    elif subchild.type == "pointer_type":
                        for ptr_child in subchild.children:
                            if ptr_child.type == "type_identifier":
                                return self._get_node_text(ptr_child, content)
        return None

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function parameters."""
        parameters = []
        for child in node.children:
            if child.type == "parameter_declaration":
                params = self._parse_parameter_declaration(child, content)
                parameters.extend(params)
            elif child.type == "variadic_parameter_declaration":
                param = self._parse_variadic_parameter(child, content)
                if param:
                    parameters.append(param)
        return parameters

    def _parse_parameter_declaration(self, node: Node, content: str) -> list[Parameter]:
        """Parse a parameter declaration (may have multiple names for one type)."""
        names = []
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child, content))
            elif child.type in (
                "type_identifier",
                "pointer_type",
                "slice_type",
                "map_type",
                "array_type",
                "qualified_type",
                "interface_type",
                "struct_type",
                "channel_type",
                "function_type",
            ):
                param_type = self._get_node_text(child, content)

        if names:
            return [Parameter(name=n, type=param_type) for n in names]
        elif param_type:
            return [Parameter(name="", type=param_type)]
        return []

    def _parse_variadic_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a variadic parameter (...type)."""
        name = None
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in (
                "type_identifier",
                "pointer_type",
                "slice_type",
                "map_type",
                "qualified_type",
                "interface_type",
            ):
                param_type = f"...{self._get_node_text(child, content)}"

        if name:
            return Parameter(name=name, type=param_type)
        return None

    def _format_return_type(self, node: Node, content: str) -> str:
        """Format a return type from a parameter list (multi-return)."""
        types = []
        for child in node.children:
            if child.type == "parameter_declaration":
                type_text = None
                for subchild in child.children:
                    if subchild.type in (
                        "type_identifier",
                        "pointer_type",
                        "slice_type",
                        "map_type",
                        "array_type",
                        "qualified_type",
                        "interface_type",
                    ):
                        type_text = self._get_node_text(subchild, content)
                if type_text:
                    types.append(type_text)
        if len(types) == 1:
            return types[0]
        elif types:
            return f"({', '.join(types)})"
        return ""
