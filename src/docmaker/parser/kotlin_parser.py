"""Kotlin parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_kotlin as tskotlin
from tree_sitter import Language, Node, Parser

from docmaker.models import (
    Annotation,
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

KOTLIN_LANGUAGE = Language(tskotlin.language())


class KotlinParser(BaseParser):
    """Parser for Kotlin source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(KOTLIN_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.KOTLIN

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.KOTLIN

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a Kotlin file and extract all symbols."""
        content = self.read_file_content(file.path)
        tree = self._parser.parse(content.encode("utf-8"))

        symbols = FileSymbols(file=file)
        symbols.package = self._extract_package(tree.root_node, content)
        symbols.imports = self._extract_imports(tree.root_node, content)
        symbols.classes = self._extract_classes(tree.root_node, content, file.path)
        symbols.functions = self._extract_module_functions(tree.root_node, content, file.path)

        return symbols

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte : node.end_byte]

    def _extract_package(self, root: Node, content: str) -> str | None:
        """Extract the package declaration."""
        for child in root.children:
            if child.type == "package_header":
                for subchild in child.children:
                    if subchild.type == "qualified_identifier":
                        return self._get_node_text(subchild, content)
        return None

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements."""
        imports = []
        for child in root.children:
            if child.type == "import":
                module = None
                is_wildcard = False
                alias = None
                for subchild in child.children:
                    if subchild.type == "qualified_identifier":
                        module = self._get_node_text(subchild, content)
                    elif subchild.type == "import_alias":
                        for alias_child in subchild.children:
                            if alias_child.type == "identifier":
                                alias = self._get_node_text(alias_child, content)
                    elif subchild.type == "*":
                        is_wildcard = True
                if module:
                    if is_wildcard:
                        module = f"{module}.*"
                    imports.append(
                        ImportDef(
                            module=module,
                            alias=alias,
                            is_wildcard=is_wildcard,
                            line_number=child.start_point[0] + 1,
                        )
                    )
        return imports

    def _extract_annotations(self, node: Node, content: str) -> list[Annotation]:
        """Extract annotations from a node's modifiers."""
        annotations = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "annotation":
                        ann = self._parse_annotation(modifier, content)
                        if ann:
                            annotations.append(ann)
        return annotations

    def _parse_annotation(self, node: Node, content: str) -> Annotation | None:
        """Parse a single annotation."""
        name = None
        arguments = {}

        for child in node.children:
            if child.type == "user_type":
                name = self._get_node_text(child, content)
            elif child.type == "value_arguments":
                arguments = self._parse_annotation_arguments(child, content)

        if name:
            return Annotation(name=name, arguments=arguments)
        return None

    def _parse_annotation_arguments(self, node: Node, content: str) -> dict[str, str]:
        """Parse annotation arguments."""
        args = {}
        positional_index = 0

        for child in node.children:
            if child.type == "value_argument":
                key = None
                value = None
                for subchild in child.children:
                    if subchild.type == "value_argument_label":
                        for label_child in subchild.children:
                            if label_child.type == "identifier":
                                key = self._get_node_text(label_child, content)
                    elif subchild.type == "string_literal":
                        value = self._get_string_content(subchild, content)
                    elif subchild.type in ("integer_literal", "boolean_literal"):
                        value = self._get_node_text(subchild, content)

                if key and value:
                    args[key] = value
                elif value:
                    args[f"arg{positional_index}"] = value
                    positional_index += 1

        return args

    def _get_string_content(self, node: Node, content: str) -> str:
        """Extract string content, stripping quotes."""
        text = self._get_node_text(node, content)
        if text.startswith('"""') and text.endswith('"""'):
            return text[3:-3]
        return text.strip("\"'")

    def _extract_modifiers(self, node: Node, content: str) -> list[str]:
        """Extract modifiers from a node."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "visibility_modifier":
                        modifiers.append(self._get_node_text(modifier, content))
                    elif modifier.type == "class_modifier":
                        modifiers.append(self._get_node_text(modifier, content))
                    elif modifier.type == "member_modifier":
                        modifiers.append(self._get_node_text(modifier, content))
                    elif modifier.type == "function_modifier":
                        modifiers.append(self._get_node_text(modifier, content))
                    elif modifier.type == "inheritance_modifier":
                        modifiers.append(self._get_node_text(modifier, content))
        return modifiers

    def _extract_comment(self, node: Node, content: str) -> str | None:
        """Extract doc comment before a node."""
        prev = node.prev_sibling
        while prev is not None:
            if prev.type == "block_comment":
                text = self._get_node_text(prev, content)
                if text.startswith("/**"):
                    return self._clean_kdoc(text)
                break
            elif prev.type == "line_comment":
                prev = prev.prev_sibling
                continue
            else:
                break
        return None

    def _clean_kdoc(self, kdoc: str) -> str:
        """Clean up a KDoc comment."""
        lines = kdoc.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("/**"):
                line = line[3:].strip()
            if line.endswith("*/"):
                line = line[:-2].strip()
            if line.startswith("*"):
                line = line[1:].strip()
            if line and not line.startswith("@"):
                cleaned.append(line)
        return "\n".join(cleaned)

    def _extract_classes(
        self, root: Node, content: str, file_path: Path
    ) -> list[ClassDef]:
        """Extract all class, interface, and object declarations."""
        classes = []
        for child in root.children:
            if child.type == "class_declaration":
                class_def = self._parse_class(child, content, file_path)
                if class_def:
                    classes.append(class_def)
            elif child.type == "object_declaration":
                obj_def = self._parse_object(child, content, file_path)
                if obj_def:
                    classes.append(obj_def)
        return classes

    def _parse_class(
        self, node: Node, content: str, file_path: Path
    ) -> ClassDef | None:
        """Parse a class or interface declaration."""
        name = None
        superclass = None
        interfaces = []
        is_interface = False

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "interface":
                is_interface = True
            elif child.type == "delegation_specifier_list":
                superclass, interfaces = self._parse_delegation_specifiers(child, content)

        if is_interface:
            modifiers.append("interface")

        if not name:
            return None

        docstring = self._extract_comment(node, content)

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            superclass=superclass,
            interfaces=interfaces,
            annotations=annotations,
            modifiers=modifiers,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        for child in node.children:
            if child.type == "class_body":
                class_def.methods = self._extract_methods(child, content, file_path)
                class_def.fields = self._extract_properties(child, content)
            elif child.type == "primary_constructor":
                class_def.fields.extend(
                    self._extract_constructor_fields(child, content)
                )

        return class_def

    def _parse_object(
        self, node: Node, content: str, file_path: Path
    ) -> ClassDef | None:
        """Parse an object declaration."""
        name = None
        annotations = self._extract_annotations(node, content)
        modifiers = ["object"]

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)

        if not name:
            return None

        docstring = self._extract_comment(node, content)

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            annotations=annotations,
            modifiers=modifiers,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        for child in node.children:
            if child.type == "class_body":
                class_def.methods = self._extract_methods(child, content, file_path)
                class_def.fields = self._extract_properties(child, content)

        return class_def

    def _parse_delegation_specifiers(
        self, node: Node, content: str
    ) -> tuple[str | None, list[str]]:
        """Parse delegation specifiers (superclass and interfaces)."""
        superclass = None
        interfaces = []

        for child in node.children:
            if child.type == "delegation_specifier":
                for subchild in child.children:
                    if subchild.type == "constructor_invocation":
                        for ci_child in subchild.children:
                            if ci_child.type == "user_type":
                                superclass = self._get_node_text(ci_child, content)
                    elif subchild.type == "user_type":
                        interfaces.append(self._get_node_text(subchild, content))

        return superclass, interfaces

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract methods from a class body."""
        methods = []
        for child in class_body.children:
            if child.type == "function_declaration":
                method = self._parse_function(child, content, file_path)
                if method:
                    methods.append(method)
        return methods

    def _parse_function(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        parameters = []
        return_type = None

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                if name is None:
                    name = self._get_node_text(child, content)
            elif child.type == "function_value_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "user_type":
                return_type = self._get_node_text(child, content)
            elif child.type == "nullable_type":
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
            annotations=annotations,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
        )

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function parameters."""
        parameters = []
        for child in node.children:
            if child.type == "parameter":
                param = self._parse_single_parameter(child, content)
                if param:
                    parameters.append(param)
        return parameters

    def _parse_single_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a single parameter."""
        name = None
        param_type = None
        default = None

        for child in node.children:
            if child.type == "identifier":
                if name is None:
                    name = self._get_node_text(child, content)
            elif child.type == "user_type":
                param_type = self._get_node_text(child, content)
            elif child.type == "nullable_type":
                param_type = self._get_node_text(child, content)

        if name:
            return Parameter(name=name, type=param_type, default=default)
        return None

    def _extract_properties(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract property declarations from a class body."""
        fields = []
        for child in class_body.children:
            if child.type == "property_declaration":
                field = self._parse_property(child, content)
                if field:
                    fields.append(field)
        return fields

    def _parse_property(self, node: Node, content: str) -> FieldDef | None:
        """Parse a property declaration."""
        name = None
        field_type = None
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "variable_declaration":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "user_type":
                        field_type = self._get_node_text(subchild, content)
                    elif subchild.type == "nullable_type":
                        field_type = self._get_node_text(subchild, content)

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_constructor_fields(self, node: Node, content: str) -> list[FieldDef]:
        """Extract fields from primary constructor parameters."""
        fields = []
        for child in node.children:
            if child.type == "class_parameters":
                for param in child.children:
                    if param.type == "class_parameter":
                        field = self._parse_constructor_field(param, content)
                        if field:
                            fields.append(field)
        return fields

    def _parse_constructor_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a constructor parameter that is also a field (val/var)."""
        name = None
        field_type = None
        modifiers = []
        has_val_var = False

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "user_type":
                field_type = self._get_node_text(child, content)
            elif child.type == "nullable_type":
                field_type = self._get_node_text(child, content)
            elif child.type in ("val", "var"):
                has_val_var = True
            elif child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "visibility_modifier":
                        modifiers.append(self._get_node_text(modifier, content))

        if name and has_val_var:
            return FieldDef(
                name=name,
                type=field_type,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_module_functions(
        self, root: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract top-level functions."""
        functions = []
        for child in root.children:
            if child.type == "function_declaration":
                func = self._parse_function(child, content, file_path)
                if func:
                    functions.append(func)
        return functions
