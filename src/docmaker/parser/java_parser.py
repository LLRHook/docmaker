"""Java parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_java as tsjava
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

logger = logging.getLogger(__name__)

JAVA_LANGUAGE = Language(tsjava.language())

HTTP_METHOD_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": None,
}

REQUEST_PARAM_ANNOTATIONS = {
    "PathVariable",
    "RequestParam",
    "RequestBody",
    "RequestHeader",
    "MatrixVariable",
}


class JavaParser(BaseParser):
    """Parser for Java source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(JAVA_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.JAVA

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.JAVA

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a Java file and extract all symbols."""
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
            if child.type == "package_declaration":
                for subchild in child.children:
                    if subchild.type == "scoped_identifier" or subchild.type == "identifier":
                        return self._get_node_text(subchild, content)
        return None

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements."""
        imports = []
        for child in root.children:
            if child.type == "import_declaration":
                is_wildcard = False
                module = ""

                for subchild in child.children:
                    if subchild.type == "scoped_identifier" or subchild.type == "identifier":
                        module = self._get_node_text(subchild, content)
                    elif subchild.type == "asterisk":
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

    def _extract_annotations(self, node: Node, content: str) -> list[Annotation]:
        """Extract annotations from a node's modifiers."""
        annotations = []

        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type == "annotation" or modifier.type == "marker_annotation":
                        ann = self._parse_annotation(modifier, content)
                        if ann:
                            annotations.append(ann)

        return annotations

    def _parse_annotation(self, node: Node, content: str) -> Annotation | None:
        """Parse a single annotation node."""
        name = None
        arguments = {}

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "annotation_argument_list":
                arguments = self._parse_annotation_arguments(child, content)

        if name:
            return Annotation(name=name, arguments=arguments)
        return None

    def _parse_annotation_arguments(self, node: Node, content: str) -> dict[str, str]:
        """Parse annotation arguments."""
        args = {}

        for child in node.children:
            if child.type == "element_value_pair":
                key = None
                value = None
                for subchild in child.children:
                    if subchild.type == "identifier":
                        key = self._get_node_text(subchild, content)
                    elif subchild.type in ("string_literal", "number_literal", "true", "false"):
                        value = self._get_node_text(subchild, content).strip("\"'")
                    elif subchild.type == "element_value_array_initializer":
                        values = []
                        for elem in subchild.children:
                            if elem.type == "string_literal":
                                values.append(self._get_node_text(elem, content).strip("\"'"))
                        value = ",".join(values)
                if key and value:
                    args[key] = value
            elif child.type == "string_literal":
                args["value"] = self._get_node_text(child, content).strip("\"'")

        return args

    def _extract_modifiers(self, node: Node, content: str) -> list[str]:
        """Extract modifiers (public, private, static, etc.)."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type in (
                        "public",
                        "private",
                        "protected",
                        "static",
                        "final",
                        "abstract",
                        "synchronized",
                        "native",
                    ):
                        modifiers.append(modifier.type)
        return modifiers

    def _extract_classes(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract all class definitions."""
        classes = []
        self._find_classes(root, content, file_path, classes)
        return classes

    def _find_classes(
        self, node: Node, content: str, file_path: Path, classes: list[ClassDef]
    ) -> None:
        """Recursively find class definitions."""
        if node.type == "class_declaration":
            class_def = self._parse_class(node, content, file_path)
            if class_def:
                classes.append(class_def)

        for child in node.children:
            self._find_classes(child, content, file_path, classes)

    def _parse_class(self, node: Node, content: str, file_path: Path) -> ClassDef | None:
        """Parse a class declaration node."""
        name = None
        superclass = None
        interfaces = []
        docstring = None

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "superclass":
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        superclass = self._get_node_text(subchild, content)
            elif child.type == "super_interfaces":
                for subchild in child.children:
                    if subchild.type == "type_list":
                        for type_node in subchild.children:
                            if type_node.type == "type_identifier":
                                interfaces.append(self._get_node_text(type_node, content))

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("block_comment", "line_comment"):
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

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract methods from a class body."""
        methods = []

        for child in class_body.children:
            if child.type == "method_declaration":
                method = self._parse_method(child, content, file_path)
                if method:
                    methods.append(method)
            elif child.type == "constructor_declaration":
                method = self._parse_constructor(child, content, file_path)
                if method:
                    methods.append(method)

        return methods

    def _parse_method(self, node: Node, content: str, file_path: Path) -> FunctionDef | None:
        """Parse a method declaration."""
        name = None
        return_type = None
        parameters = []
        docstring = None

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in ("type_identifier", "void_type", "generic_type"):
                if return_type is None:
                    return_type = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("block_comment", "line_comment"):
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

    def _parse_constructor(self, node: Node, content: str, file_path: Path) -> FunctionDef | None:
        """Parse a constructor declaration."""
        name = None
        parameters = []
        docstring = None

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)

        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ("block_comment", "line_comment"):
            docstring = self._clean_docstring(self._get_node_text(prev_sibling, content))

        if not name:
            return None

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=None,
            docstring=docstring,
            annotations=annotations,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
        )

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse method parameters."""
        parameters = []

        for child in node.children:
            if child.type == "formal_parameter" or child.type == "spread_parameter":
                param = self._parse_single_parameter(child, content)
                if param:
                    parameters.append(param)

        return parameters

    def _parse_single_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a single parameter."""
        name = None
        param_type = None
        annotations = []

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type in ("type_identifier", "generic_type", "array_type", "integral_type"):
                param_type = self._get_node_text(child, content)
            elif child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type in ("annotation", "marker_annotation"):
                        ann = self._parse_annotation(modifier, content)
                        if ann:
                            annotations.append(ann)

        if name:
            description = None
            for ann in annotations:
                if ann.name in REQUEST_PARAM_ANNOTATIONS:
                    description = f"@{ann.name}"
                    if ann.arguments:
                        args_str = ", ".join(f"{k}={v}" for k, v in ann.arguments.items())
                        description += f"({args_str})"
            return Parameter(name=name, type=param_type, description=description)
        return None

    def _extract_fields(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract fields from a class body."""
        fields = []

        for child in class_body.children:
            if child.type == "field_declaration":
                field = self._parse_field(child, content)
                if field:
                    fields.append(field)

        return fields

    def _parse_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a field declaration."""
        name = None
        field_type = None

        annotations = self._extract_annotations(node, content)
        modifiers = self._extract_modifiers(node, content)

        for child in node.children:
            if child.type in ("type_identifier", "generic_type", "array_type", "integral_type"):
                field_type = self._get_node_text(child, content)
            elif child.type == "variable_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                        break

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                annotations=annotations,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _clean_docstring(self, comment: str) -> str:
        """Clean up a Javadoc comment."""
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
