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

    _type_node_types = frozenset(
        {
            "type_identifier",
            "pointer_type",
            "slice_type",
            "map_type",
            "array_type",
            "qualified_type",
            "channel_type",
            "function_type",
            "interface_type",
            "struct_type",
        }
    )

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

        structs, interfaces = self._extract_type_declarations(tree.root_node, content, file.path)
        symbols.classes = structs + interfaces

        symbols.functions = self._extract_functions(tree.root_node, content, file.path)

        self._attach_methods_to_structs(tree.root_node, content, file.path, symbols.classes)

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
        alias = None
        module = None
        is_wildcard = False

        for child in node.children:
            if child.type == "interpreted_string_literal":
                module = self._get_node_text(child, content).strip('"')
            elif child.type == "package_identifier" or child.type == "dot":
                alias_text = self._get_node_text(child, content)
                if alias_text == ".":
                    is_wildcard = True
                elif alias_text == "_":
                    alias = "_"
                else:
                    alias = alias_text
            elif child.type == "blank_identifier":
                alias = "_"

        if module:
            return ImportDef(
                module=module,
                alias=alias,
                is_wildcard=is_wildcard,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_type_declarations(
        self, root: Node, content: str, file_path: Path
    ) -> tuple[list[ClassDef], list[ClassDef]]:
        """Extract struct and interface type declarations."""
        structs = []
        interfaces = []

        for child in root.children:
            if child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        result = self._parse_type_spec(spec, child, content, file_path)
                        if result:
                            class_def, is_interface = result
                            if is_interface:
                                interfaces.append(class_def)
                            else:
                                structs.append(class_def)

        return structs, interfaces

    def _parse_type_spec(
        self, spec: Node, decl: Node, content: str, file_path: Path
    ) -> tuple[ClassDef, bool] | None:
        """Parse a type spec into a ClassDef."""
        name = None
        is_interface = False
        fields = []
        interfaces = []  # embedded interfaces/types

        for child in spec.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "struct_type":
                fields = self._extract_struct_fields(child, content)
                interfaces = self._extract_embedded_types(child, content)
            elif child.type == "interface_type":
                is_interface = True
                interfaces = self._extract_embedded_interfaces(child, content)

        if not name:
            return None

        docstring = self._extract_comment_above(decl, content)

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=decl.start_point[0] + 1,
            end_line=decl.end_point[0] + 1,
            interfaces=interfaces,
            modifiers=["interface"] if is_interface else ["struct"],
            docstring=docstring,
            fields=fields,
            source_code=self._get_node_text(decl, content),
        )

        if is_interface:
            class_def.methods = self._extract_interface_methods(spec, content, file_path)

        return class_def, is_interface

    def _extract_struct_fields(self, struct_node: Node, content: str) -> list[FieldDef]:
        """Extract fields from a struct type."""
        fields = []
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                for field_node in child.children:
                    if field_node.type == "field_declaration":
                        field = self._parse_struct_field(field_node, content)
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
            elif child.type in self._type_node_types:
                field_type = self._get_node_text(child, content)

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_embedded_types(self, struct_node: Node, content: str) -> list[str]:
        """Extract embedded type names from a struct (Go composition)."""
        embedded = []
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                for field_node in child.children:
                    if field_node.type == "field_declaration":
                        has_field_id = any(
                            c.type == "field_identifier" for c in field_node.children
                        )
                        if not has_field_id:
                            for c in field_node.children:
                                if c.type in ("type_identifier", "qualified_type", "pointer_type"):
                                    embedded.append(self._get_node_text(c, content))
        return embedded

    def _extract_embedded_interfaces(self, iface_node: Node, content: str) -> list[str]:
        """Extract embedded interface names from an interface type."""
        embedded = []
        for child in iface_node.children:
            if child.type == "type_elem":
                for sub in child.children:
                    if sub.type in ("type_identifier", "qualified_type"):
                        embedded.append(self._get_node_text(sub, content))
        return embedded

    def _extract_interface_methods(
        self, type_spec: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract method signatures from an interface type."""
        methods = []
        for child in type_spec.children:
            if child.type == "interface_type":
                for iface_child in child.children:
                    if iface_child.type in ("method_spec", "method_elem"):
                        method = self._parse_interface_method(iface_child, content, file_path)
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
        seen_params = False

        for child in node.children:
            if child.type == "field_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "parameter_list":
                if not seen_params:
                    parameters = self._parse_parameters(child, content)
                    seen_params = True
                else:
                    return_type = self._get_node_text(child, content)
            elif child.type in self._type_node_types:
                return_type = self._get_node_text(child, content)

        if not name:
            return None

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            source_code=self._get_node_text(node, content),
        )

    def _extract_functions(self, root: Node, content: str, file_path: Path) -> list[FunctionDef]:
        """Extract top-level function declarations (not methods)."""
        functions = []
        for child in root.children:
            if child.type == "function_declaration":
                func = self._parse_function(child, content, file_path)
                if func:
                    functions.append(func)
        return functions

    def _parse_function(self, node: Node, content: str, file_path: Path) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        parameters = []
        return_type = None
        seen_params = False

        for child in node.children:
            if child.type == "identifier" and name is None:
                name = self._get_node_text(child, content)
            elif child.type == "parameter_list":
                if not seen_params:
                    parameters = self._parse_parameters(child, content)
                    seen_params = True
                else:
                    return_type = self._get_node_text(child, content)
            elif child.type in self._type_node_types:
                return_type = self._get_node_text(child, content)

        if not name:
            return None

        docstring = self._extract_comment_above(node, content)

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

    def _attach_methods_to_structs(
        self,
        root: Node,
        content: str,
        file_path: Path,
        classes: list[ClassDef],
    ) -> None:
        """Find method declarations and attach them to their receiver struct."""
        struct_map = {cls.name: cls for cls in classes}

        for child in root.children:
            if child.type == "method_declaration":
                receiver_name, method = self._parse_method(child, content, file_path)
                if receiver_name and method:
                    # Strip pointer prefix
                    receiver_name = receiver_name.lstrip("*")
                    if receiver_name in struct_map:
                        struct_map[receiver_name].methods.append(method)

    def _parse_method(
        self, node: Node, content: str, file_path: Path
    ) -> tuple[str | None, FunctionDef | None]:
        """Parse a method declaration, returning (receiver_type_name, FunctionDef)."""
        name = None
        receiver_name = None
        parameters = []
        return_type = None

        param_list_index = 0
        for child in node.children:
            if child.type == "parameter_list":
                if param_list_index == 0:
                    receiver_name = self._extract_receiver_type(child, content)
                elif param_list_index == 1:
                    parameters = self._parse_parameters(child, content)
                else:
                    return_type = self._get_node_text(child, content)
                param_list_index += 1
            elif child.type == "field_identifier":
                name = self._get_node_text(child, content)
            elif child.type in self._type_node_types:
                return_type = self._get_node_text(child, content)

        if not name:
            return None, None

        docstring = self._extract_comment_above(node, content)

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

        return receiver_name, method

    def _extract_receiver_type(self, param_list: Node, content: str) -> str | None:
        """Extract the receiver type name from a method's receiver parameter list."""
        for child in param_list.children:
            if child.type == "parameter_declaration":
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        return self._get_node_text(subchild, content)
                    elif subchild.type == "pointer_type":
                        for ptr_child in subchild.children:
                            if ptr_child.type == "type_identifier":
                                return "*" + self._get_node_text(ptr_child, content)
        return None

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function/method parameters."""
        parameters = []
        for child in node.children:
            if child.type == "parameter_declaration":
                params = self._parse_parameter_declaration(child, content)
                parameters.extend(params)
        return parameters

    def _parse_parameter_declaration(self, node: Node, content: str) -> list[Parameter]:
        """Parse a single parameter declaration (may contain multiple names)."""
        names = []
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child, content))
            elif child.type in self._type_node_types:
                param_type = self._get_node_text(child, content)

        if names:
            return [Parameter(name=n, type=param_type) for n in names]
        elif param_type:
            return [Parameter(name="", type=param_type)]
        return []

    def _extract_comment_above(self, node: Node, content: str) -> str | None:
        """Extract comment immediately above a node as its docstring."""
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            return self._clean_comment(self._get_node_text(prev, content))
        return None

    def _clean_comment(self, comment: str) -> str:
        """Clean a Go comment block."""
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
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)
