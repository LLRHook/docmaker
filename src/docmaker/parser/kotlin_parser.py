"""Kotlin parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_kotlin as tskotlin
from tree_sitter import Language, Node, Parser

from docmaker.models import (
    Annotation,
    ClassDef,
    EndpointDef,
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
from docmaker.parser.java_parser import HTTP_METHOD_ANNOTATIONS, REQUEST_PARAM_ANNOTATIONS

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
        symbols.endpoints = self._extract_endpoints_from_classes(symbols.classes, symbols.package)

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
                module = ""
                is_wildcard = False

                for subchild in child.children:
                    if subchild.type == "qualified_identifier":
                        module = self._get_node_text(subchild, content)
                    elif subchild.type == "*":
                        is_wildcard = True
                        module = module.rstrip(".") + ".*"

                if module:
                    imports.append(
                        ImportDef(
                            module=module,
                            is_wildcard=is_wildcard,
                            line_number=child.start_point[0] + 1,
                        )
                    )
        return imports

    # ── Annotation extraction ──────────────────────────────────────────

    def _extract_annotations_from_modifiers(self, node: Node, content: str) -> list[Annotation]:
        """Extract annotations from a node's modifiers child."""
        annotations = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "annotation":
                        ann = self._parse_annotation(modifier, content)
                        if ann:
                            annotations.append(ann)
        return annotations

    def _extract_annotations_from_annotated_expression(
        self, node: Node, content: str
    ) -> list[Annotation]:
        """Extract annotations from an annotated_expression tree.

        Kotlin's tree-sitter grammar wraps top-level annotations (before a class)
        in nested annotated_expression nodes.
        """
        annotations = []
        self._collect_annotations_recursive(node, content, annotations)
        return annotations

    def _collect_annotations_recursive(
        self, node: Node, content: str, annotations: list[Annotation]
    ) -> None:
        """Recursively collect annotations from annotated_expression nodes."""
        if node.type != "annotated_expression":
            return

        # An annotated_expression contains: annotation, then either another
        # annotated_expression or a parenthesized_expression (annotation args)
        ann_node = None
        args_node = None

        for child in node.children:
            if child.type == "annotation":
                ann_node = child
            elif child.type == "parenthesized_expression":
                args_node = child
            elif child.type == "annotated_expression":
                self._collect_annotations_recursive(child, content, annotations)

        if ann_node:
            ann = self._parse_annotation(ann_node, content, args_node)
            if ann:
                annotations.append(ann)

    def _parse_annotation(
        self, node: Node, content: str, external_args: Node | None = None
    ) -> Annotation | None:
        """Parse a single annotation node.

        Kotlin annotations come in two AST shapes:
        1. In modifiers: annotation > @ + constructor_invocation(user_type + value_arguments)
        2. In annotated_expression: annotation > @ + user_type, with args in a sibling
           parenthesized_expression.
        """
        name = None
        arguments: dict[str, str] = {}

        for child in node.children:
            if child.type == "user_type":
                name = self._extract_type_name(child, content)
            elif child.type == "constructor_invocation":
                for sub in child.children:
                    if sub.type == "user_type":
                        name = self._extract_type_name(sub, content)
                    elif sub.type == "value_arguments":
                        arguments = self._parse_value_arguments(sub, content)

        # Handle args from a sibling parenthesized_expression (annotated_expression case)
        if external_args and external_args.type == "parenthesized_expression":
            arguments = self._parse_parenthesized_args(external_args, content)

        if name:
            return Annotation(name=name, arguments=arguments)
        return None

    def _extract_type_name(self, user_type_node: Node, content: str) -> str:
        """Extract the type name from a user_type node."""
        for child in user_type_node.children:
            if child.type == "identifier":
                return self._get_node_text(child, content)
        return self._get_node_text(user_type_node, content)

    def _parse_value_arguments(self, node: Node, content: str) -> dict[str, str]:
        """Parse value_arguments (used in constructor_invocation style annotations)."""
        args = {}
        for child in node.children:
            if child.type == "value_argument":
                key, value = self._parse_value_argument(child, content)
                if key and value:
                    args[key] = value
                elif value:
                    args["value"] = value
        return args

    def _parse_value_argument(self, node: Node, content: str) -> tuple[str | None, str | None]:
        """Parse a single value_argument, returning (key, value)."""
        key = None
        value = None

        has_equals = any(c.type == "=" for c in node.children)

        for child in node.children:
            if child.type == "identifier" and has_equals and key is None:
                key = self._get_node_text(child, content)
            elif child.type == "string_literal":
                value = self._extract_string_content(child, content)
            elif child.type == "number_literal":
                value = self._get_node_text(child, content)
            elif child.type in ("true", "false"):
                value = self._get_node_text(child, content)
            elif child.type == "collection_literal":
                values = []
                for elem in child.children:
                    if elem.type == "string_literal":
                        values.append(self._extract_string_content(elem, content))
                    elif elem.type == "navigation_expression":
                        values.append(self._get_node_text(elem, content))
                value = ",".join(values)
            elif child.type == "navigation_expression":
                value = self._get_node_text(child, content)

        return key, value

    def _parse_parenthesized_args(self, node: Node, content: str) -> dict[str, str]:
        """Parse annotation args from a parenthesized_expression."""
        args = {}
        for child in node.children:
            if child.type == "string_literal":
                args["value"] = self._extract_string_content(child, content)
        return args

    def _extract_string_content(self, node: Node, content: str) -> str:
        """Extract text content from a string_literal node, stripping quotes."""
        for child in node.children:
            if child.type == "string_content":
                return self._get_node_text(child, content)
        # Fallback: strip quotes manually
        text = self._get_node_text(node, content)
        return text.strip("\"'")

    # ── Modifier extraction ────────────────────────────────────────────

    def _extract_modifiers(self, node: Node, content: str) -> list[str]:
        """Extract modifiers (public, private, open, data, suspend, etc.)."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "visibility_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
                    elif modifier.type == "inheritance_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
                    elif modifier.type == "class_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
                    elif modifier.type == "member_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
                    elif modifier.type == "function_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
                    elif modifier.type == "property_modifier":
                        for m in modifier.children:
                            modifiers.append(m.type)
        return modifiers

    def _is_suspend(self, node: Node) -> bool:
        """Check if a function declaration has the suspend modifier."""
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "function_modifier":
                        for m in modifier.children:
                            if m.type == "suspend":
                                return True
        return False

    # ── Class extraction ───────────────────────────────────────────────

    def _extract_classes(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract all class, object, and interface definitions."""
        classes = []
        children = root.children if root.children else []

        i = 0
        while i < len(children):
            child = children[i]

            if child.type == "class_declaration":
                class_def = self._parse_class(child, content, file_path)
                if class_def:
                    classes.append(class_def)
            elif child.type == "object_declaration":
                class_def = self._parse_object(child, content, file_path)
                if class_def:
                    classes.append(class_def)
            elif child.type == "annotated_expression":
                # Top-level annotations precede the next class/object declaration
                annotations = self._extract_annotations_from_annotated_expression(child, content)
                if i + 1 < len(children):
                    next_child = children[i + 1]
                    if next_child.type == "class_declaration":
                        class_def = self._parse_class(
                            next_child, content, file_path, extra_annotations=annotations
                        )
                        if class_def:
                            classes.append(class_def)
                        i += 1
                    elif next_child.type == "object_declaration":
                        class_def = self._parse_object(
                            next_child, content, file_path, extra_annotations=annotations
                        )
                        if class_def:
                            classes.append(class_def)
                        i += 1

            # Recurse into class bodies for nested classes
            if child.type == "class_declaration":
                for body_child in child.children:
                    if body_child.type == "class_body":
                        self._find_nested_classes(body_child, content, file_path, classes)

            i += 1

        return classes

    def _find_nested_classes(
        self, node: Node, content: str, file_path: Path, classes: list[ClassDef]
    ) -> None:
        """Recursively find nested class definitions."""
        for child in node.children:
            if child.type == "class_declaration":
                class_def = self._parse_class(child, content, file_path)
                if class_def:
                    classes.append(class_def)
                for body_child in child.children:
                    if body_child.type == "class_body":
                        self._find_nested_classes(body_child, content, file_path, classes)
            elif child.type == "object_declaration":
                class_def = self._parse_object(child, content, file_path)
                if class_def:
                    classes.append(class_def)

    def _parse_class(
        self,
        node: Node,
        content: str,
        file_path: Path,
        extra_annotations: list[Annotation] | None = None,
    ) -> ClassDef | None:
        """Parse a class or interface declaration."""
        name = None
        superclass = None
        interfaces: list[str] = []
        docstring = None
        is_interface = False

        annotations = list(extra_annotations) if extra_annotations else []
        annotations.extend(self._extract_annotations_from_modifiers(node, content))
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "interface":
                is_interface = True
            elif child.type == "delegation_specifiers":
                superclass, interfaces = self._parse_delegation_specifiers(child, content)

        if is_interface and "interface" not in modifiers:
            modifiers.insert(0, "interface")

        # Check for data modifier
        is_data = "data" in modifiers

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("multiline_comment", "line_comment"):
            docstring = self._clean_docstring(self._get_node_text(prev_sibling, content))

        if not name:
            return None

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

        # Extract methods and fields from class body
        for child in node.children:
            if child.type == "class_body":
                class_def.methods = self._extract_methods(child, content, file_path)
                class_def.fields = self._extract_fields(child, content)

        # Extract constructor parameters as fields for data classes
        if is_data:
            class_def.fields.extend(self._extract_constructor_fields(node, content))

        return class_def

    def _parse_object(
        self,
        node: Node,
        content: str,
        file_path: Path,
        extra_annotations: list[Annotation] | None = None,
    ) -> ClassDef | None:
        """Parse an object declaration (Kotlin singleton)."""
        name = None
        superclass = None
        interfaces: list[str] = []
        docstring = None

        annotations = list(extra_annotations) if extra_annotations else []
        annotations.extend(self._extract_annotations_from_modifiers(node, content))
        modifiers = self._extract_modifiers(node, content)
        modifiers.insert(0, "object")

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "delegation_specifiers":
                superclass, interfaces = self._parse_delegation_specifiers(child, content)

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("multiline_comment", "line_comment"):
            docstring = self._clean_docstring(self._get_node_text(prev_sibling, content))

        if not name:
            return None

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
                class_def.fields = self._extract_fields(child, content)

        return class_def

    def _parse_delegation_specifiers(
        self, node: Node, content: str
    ) -> tuple[str | None, list[str]]:
        """Parse delegation_specifiers to extract superclass and interfaces."""
        superclass = None
        interfaces = []

        for child in node.children:
            if child.type == "delegation_specifier":
                for sub in child.children:
                    if sub.type == "constructor_invocation":
                        # Superclass (has parentheses)
                        for s in sub.children:
                            if s.type == "user_type":
                                superclass = self._extract_type_name(s, content)
                    elif sub.type == "user_type":
                        # Interface (no parentheses)
                        interfaces.append(self._extract_type_name(sub, content))

        return superclass, interfaces

    # ── Method extraction ──────────────────────────────────────────────

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract functions from a class body."""
        methods = []
        for child in class_body.children:
            if child.type == "function_declaration":
                method = self._parse_method(child, content, file_path)
                if method:
                    methods.append(method)
        return methods

    def _parse_method(self, node: Node, content: str, file_path: Path) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        return_type = None
        parameters = []
        docstring = None

        annotations = self._extract_annotations_from_modifiers(node, content)
        modifiers = self._extract_modifiers(node, content)
        is_suspend = self._is_suspend(node)
        if is_suspend and "suspend" not in modifiers:
            modifiers.insert(0, "suspend")

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in ("user_type", "nullable_type"):
                # Return type appears after ":"
                if return_type is None:
                    return_type = self._get_node_text(child, content)
            elif child.type == "function_value_parameters":
                parameters = self._parse_parameters(child, content)

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("multiline_comment", "line_comment"):
            docstring = self._clean_docstring(self._get_node_text(prev_sibling, content))

        if not name:
            return None

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
        pending_annotations: list[Annotation] = []

        for child in node.children:
            if child.type == "parameter_modifiers":
                # Annotations on parameters appear as parameter_modifiers
                for mod in child.children:
                    if mod.type == "annotation":
                        ann = self._parse_annotation(mod, content)
                        if ann:
                            pending_annotations.append(ann)
            elif child.type == "parameter":
                param = self._parse_single_parameter(child, content, pending_annotations)
                if param:
                    parameters.append(param)
                pending_annotations = []

        return parameters

    def _parse_single_parameter(
        self, node: Node, content: str, annotations: list[Annotation] | None = None
    ) -> Parameter | None:
        """Parse a single parameter."""
        name = None
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in ("user_type", "nullable_type"):
                param_type = self._get_node_text(child, content)

        if name:
            description = None
            if annotations:
                for ann in annotations:
                    if ann.name in REQUEST_PARAM_ANNOTATIONS:
                        description = f"@{ann.name}"
                        if ann.arguments:
                            args_str = ", ".join(f"{k}={v}" for k, v in ann.arguments.items())
                            description += f"({args_str})"
            return Parameter(name=name, type=param_type, description=description)
        return None

    # ── Field extraction ───────────────────────────────────────────────

    def _extract_fields(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract property declarations from a class body."""
        fields = []
        for child in class_body.children:
            if child.type == "property_declaration":
                field = self._parse_field(child, content)
                if field:
                    fields.append(field)
        return fields

    def _parse_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a property declaration."""
        name = None
        field_type = None

        annotations = self._extract_annotations_from_modifiers(node, content)
        modifiers = self._extract_modifiers(node, content)

        # Check val/var
        for child in node.children:
            if child.type == "val":
                if "val" not in modifiers:
                    modifiers.append("val")
            elif child.type == "var":
                if "var" not in modifiers:
                    modifiers.append("var")
            elif child.type == "variable_declaration":
                for sub in child.children:
                    if sub.type == "identifier":
                        name = self._get_node_text(sub, content)
                    elif sub.type in ("user_type", "nullable_type"):
                        field_type = self._get_node_text(sub, content)

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                annotations=annotations,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_constructor_fields(self, class_node: Node, content: str) -> list[FieldDef]:
        """Extract fields from primary constructor parameters (for data classes)."""
        fields = []
        for child in class_node.children:
            if child.type == "primary_constructor":
                for sub in child.children:
                    if sub.type == "class_parameters":
                        for param in sub.children:
                            if param.type == "class_parameter":
                                field = self._parse_constructor_param_as_field(param, content)
                                if field:
                                    fields.append(field)
        return fields

    def _parse_constructor_param_as_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a class_parameter as a FieldDef."""
        name = None
        field_type = None
        modifiers = []

        for child in node.children:
            if child.type == "val":
                modifiers.append("val")
            elif child.type == "var":
                modifiers.append("var")
            elif child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in ("user_type", "nullable_type"):
                field_type = self._get_node_text(child, content)
            elif child.type == "modifiers":
                for mod in child.children:
                    if mod.type == "visibility_modifier":
                        for m in mod.children:
                            modifiers.append(m.type)

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                annotations=[],
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    # ── Docstring cleaning ─────────────────────────────────────────────

    def _clean_docstring(self, comment: str) -> str:
        """Clean up a KDoc comment."""
        lines = comment.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("/**") or line.startswith("/*"):
                line = line[3:].strip() if line.startswith("/**") else line[2:].strip()
            if line.endswith("*/"):
                line = line[:-2].strip()
            if line.startswith("*"):
                line = line[1:].strip()
            if line.startswith("//"):
                line = line[2:].strip()
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)

    # ── Endpoint extraction (shared logic with Java parser) ────────────

    def _extract_endpoints_from_classes(
        self, classes: list[ClassDef], package: str | None
    ) -> list[EndpointDef]:
        """Extract REST endpoints from controller classes."""
        endpoints = []

        for cls in classes:
            class_path = self._get_class_base_path(cls)
            is_controller = any(
                ann.name in ("RestController", "Controller") for ann in cls.annotations
            )

            if not is_controller:
                continue

            for method in cls.methods:
                endpoint = self._extract_endpoint_from_method(method, cls, class_path, package)
                if endpoint:
                    endpoints.append(endpoint)

        return endpoints

    def _get_class_base_path(self, cls: ClassDef) -> str:
        """Get the base path from @RequestMapping on the class."""
        for ann in cls.annotations:
            if ann.name == "RequestMapping":
                return ann.arguments.get("value", ann.arguments.get("path", ""))
        return ""

    def _extract_endpoint_from_method(
        self,
        method: FunctionDef,
        cls: ClassDef,
        class_path: str,
        package: str | None,
    ) -> EndpointDef | None:
        """Extract endpoint info from a controller method."""
        http_method = None
        method_path = ""

        for ann in method.annotations:
            if ann.name in HTTP_METHOD_ANNOTATIONS:
                if ann.name == "RequestMapping":
                    method_val = ann.arguments.get("method", "GET")
                    if "GET" in method_val:
                        http_method = "GET"
                    elif "POST" in method_val:
                        http_method = "POST"
                    elif "PUT" in method_val:
                        http_method = "PUT"
                    elif "DELETE" in method_val:
                        http_method = "DELETE"
                    elif "PATCH" in method_val:
                        http_method = "PATCH"
                    else:
                        http_method = "GET"
                else:
                    http_method = HTTP_METHOD_ANNOTATIONS[ann.name]

                method_path = ann.arguments.get("value", ann.arguments.get("path", ""))
                break

        if not http_method:
            return None

        full_path = self._combine_paths(class_path, method_path)

        request_body = None
        for param in method.parameters:
            if param.description and "@RequestBody" in param.description:
                request_body = param.type

        return EndpointDef(
            http_method=http_method,
            path=full_path,
            handler_method=method.name,
            handler_class=cls.name,
            file_path=method.file_path,
            line_number=method.line_number,
            parameters=method.parameters,
            request_body=request_body,
            response_type=method.return_type,
            description=method.docstring,
            annotations=method.annotations,
            source_code=method.source_code,
        )

    def _combine_paths(self, base: str, path: str) -> str:
        """Combine base path and method path."""
        base = base.strip("/") if base else ""
        path = path.strip("/") if path else ""

        if base and path:
            return f"/{base}/{path}"
        elif base:
            return f"/{base}"
        elif path:
            return f"/{path}"
        else:
            return "/"
