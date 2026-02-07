"""TypeScript parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_typescript as tstypescript
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

TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())


class TypeScriptParser(BaseParser):
    """Parser for TypeScript source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(TYPESCRIPT_LANGUAGE)
        self._tsx_parser = Parser(TSX_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.TYPESCRIPT

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.TYPESCRIPT

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a TypeScript file and extract all symbols."""
        content = self.read_file_content(file.path)

        if file.path.suffix == ".tsx":
            tree = self._tsx_parser.parse(content.encode("utf-8"))
        else:
            tree = self._parser.parse(content.encode("utf-8"))

        symbols = FileSymbols(file=file)
        symbols.package = self._extract_module_name(file.path)
        symbols.imports = self._extract_imports(tree.root_node, content)
        symbols.classes = self._extract_classes(tree.root_node, content, file.path)
        symbols.functions = self._extract_module_functions(tree.root_node, content, file.path)

        interfaces = self._extract_interfaces(tree.root_node, content, file.path)
        symbols.classes.extend(interfaces)

        return symbols

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte : node.end_byte]

    def _extract_module_name(self, file_path: Path) -> str | None:
        """Extract module name from file path."""
        return file_path.stem

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements."""
        imports = []
        for child in root.children:
            if child.type == "import_statement":
                imports.extend(self._parse_import_statement(child, content))
        return imports

    def _parse_import_statement(self, node: Node, content: str) -> list[ImportDef]:
        """Parse an import statement."""
        imports = []
        module_path = None
        is_wildcard = False

        for child in node.children:
            if child.type == "string":
                module_path = self._get_node_text(child, content).strip("\"'")
            elif child.type == "import_clause":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                        imports.append(
                            ImportDef(
                                module=f"{module_path}.default" if module_path else name,
                                alias=name,
                                line_number=node.start_point[0] + 1,
                            )
                        )
                    elif subchild.type == "named_imports":
                        for import_node in subchild.children:
                            if import_node.type == "import_specifier":
                                name = None
                                alias = None
                                for spec_child in import_node.children:
                                    if spec_child.type == "identifier":
                                        if name is None:
                                            name = self._get_node_text(spec_child, content)
                                        else:
                                            alias = self._get_node_text(spec_child, content)
                                if name:
                                    full_module = f"{module_path}.{name}" if module_path else name
                                    imports.append(
                                        ImportDef(
                                            module=full_module,
                                            alias=alias,
                                            line_number=node.start_point[0] + 1,
                                        )
                                    )
                    elif subchild.type == "namespace_import":
                        is_wildcard = True
                        for ns_child in subchild.children:
                            if ns_child.type == "identifier":
                                alias = self._get_node_text(ns_child, content)
                                imports.append(
                                    ImportDef(
                                        module=f"{module_path}.*" if module_path else "*",
                                        alias=alias,
                                        is_wildcard=True,
                                        line_number=node.start_point[0] + 1,
                                    )
                                )

        if not imports and module_path:
            imports.append(
                ImportDef(
                    module=module_path,
                    is_wildcard=is_wildcard,
                    line_number=node.start_point[0] + 1,
                )
            )

        return imports

    def _extract_classes(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract all class definitions."""
        classes = []
        self._find_classes(root, content, file_path, classes, decorators=[])
        return classes

    def _find_classes(
        self,
        node: Node,
        content: str,
        file_path: Path,
        classes: list[ClassDef],
        decorators: list[Annotation],
    ) -> None:
        """Recursively find class definitions."""
        current_decorators = list(decorators)
        for child in node.children:
            if child.type == "class_declaration":
                class_def = self._parse_class(child, content, file_path, current_decorators)
                if class_def:
                    classes.append(class_def)
                current_decorators = []
            elif child.type == "decorator":
                dec = self._parse_decorator(child, content)
                if dec:
                    current_decorators.append(dec)
            elif child.type == "export_statement":
                export_decorators = []
                export_jsdoc = self._extract_jsdoc(child, content)
                for subchild in child.children:
                    if subchild.type == "decorator":
                        dec = self._parse_decorator(subchild, content)
                        if dec:
                            export_decorators.append(dec)
                    elif subchild.type == "class_declaration":
                        all_decorators = current_decorators + export_decorators
                        class_def = self._parse_class(subchild, content, file_path, all_decorators)
                        if class_def:
                            class_def.modifiers.append("export")
                            if class_def.docstring is None and export_jsdoc:
                                class_def.docstring = export_jsdoc
                            classes.append(class_def)
                        current_decorators = []
            else:
                if child.type != "comment":
                    current_decorators = []

    def _parse_class(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> ClassDef | None:
        """Parse a class declaration node."""
        name = None
        superclass = None
        interfaces = []
        docstring = None
        modifiers = []

        for child in node.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "class_heritage":
                superclass, interfaces = self._parse_class_heritage(child, content)
            elif child.type in ("abstract", "export", "declare"):
                modifiers.append(child.type)

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            superclass=superclass,
            interfaces=interfaces,
            annotations=decorators,
            modifiers=modifiers,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        for child in node.children:
            if child.type == "class_body":
                class_def.methods = self._extract_methods(child, content, file_path)
                class_def.fields = self._extract_class_fields(child, content)

        return class_def

    def _parse_class_heritage(self, node: Node, content: str) -> tuple[str | None, list[str]]:
        """Parse class heritage (extends and implements)."""
        superclass = None
        interfaces = []

        for child in node.children:
            if child.type == "extends_clause":
                for subchild in child.children:
                    if subchild.type in ("type_identifier", "generic_type"):
                        superclass = self._get_node_text(subchild, content)
                        break
            elif child.type == "implements_clause":
                for subchild in child.children:
                    if subchild.type in ("type_identifier", "generic_type"):
                        interfaces.append(self._get_node_text(subchild, content))

        return superclass, interfaces

    def _extract_jsdoc(self, node: Node, content: str) -> str | None:
        """Extract JSDoc comment before a node."""
        prev = node.prev_sibling
        while prev is not None:
            if prev.type == "comment":
                text = self._get_node_text(prev, content)
                if text.startswith("/**"):
                    return self._clean_jsdoc(text)
                elif text.startswith("//"):
                    prev = prev.prev_sibling
                    continue
                break
            elif prev.type == "decorator":
                prev = prev.prev_sibling
                continue
            else:
                break
            prev = prev.prev_sibling
        return None

    def _clean_jsdoc(self, jsdoc: str) -> str:
        """Clean up a JSDoc comment."""
        lines = jsdoc.split("\n")
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

    def _parse_decorator(self, node: Node, content: str) -> Annotation | None:
        """Parse a decorator."""
        name = None
        arguments = {}

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "call_expression":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "member_expression":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "arguments":
                        arguments = self._parse_decorator_arguments(subchild, content)

        if name:
            return Annotation(name=name, arguments=arguments)
        return None

    def _parse_decorator_arguments(self, node: Node, content: str) -> dict[str, str]:
        """Parse decorator arguments."""
        args = {}
        positional_index = 0

        for child in node.children:
            if child.type == "string":
                args[f"arg{positional_index}"] = self._get_node_text(child, content).strip("\"'`")
                positional_index += 1
            elif child.type == "object":
                for prop in child.children:
                    if prop.type == "pair":
                        key = None
                        value = None
                        for subchild in prop.children:
                            if subchild.type == "property_identifier":
                                key = self._get_node_text(subchild, content)
                            elif subchild.type in ("string", "number", "true", "false"):
                                value = self._get_node_text(subchild, content).strip("\"'`")
                        if key and value:
                            args[key] = value

        return args

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract methods from a class body."""
        methods = []
        decorators = []

        for child in class_body.children:
            if child.type == "decorator":
                dec = self._parse_decorator(child, content)
                if dec:
                    decorators.append(dec)
            elif child.type == "method_definition":
                method = self._parse_method(child, content, file_path, decorators)
                if method:
                    methods.append(method)
                decorators = []
            elif child.type == "public_field_definition":
                decorators = []
            else:
                decorators = []

        return methods

    def _parse_method(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> FunctionDef | None:
        """Parse a method definition."""
        name = None
        parameters = []
        return_type = None
        docstring = None
        modifiers = []

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        return_type = self._get_node_text(subchild, content)
            elif child.type in ("public", "private", "protected", "static", "async", "readonly"):
                modifiers.append(child.type)
            elif child.type == "accessibility_modifier":
                modifiers.append(self._get_node_text(child, content))

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        # Extract calls from the method body
        calls = []
        for child in node.children:
            if child.type == "statement_block":
                calls = self._extract_calls(child, content)
                break

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            annotations=decorators,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
            calls=calls,
        )

    def _extract_module_functions(
        self, root: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract module-level functions."""
        functions = []
        decorators = []

        for child in root.children:
            if child.type == "decorator":
                dec = self._parse_decorator(child, content)
                if dec:
                    decorators.append(dec)
            elif child.type == "function_declaration":
                func = self._parse_function(child, content, file_path, decorators)
                if func:
                    functions.append(func)
                decorators = []
            elif child.type == "export_statement":
                export_jsdoc = self._extract_jsdoc(child, content)
                for subchild in child.children:
                    if subchild.type == "function_declaration":
                        func = self._parse_function(subchild, content, file_path, decorators)
                        if func:
                            func.modifiers.append("export")
                            if func.docstring is None and export_jsdoc:
                                func.docstring = export_jsdoc
                            functions.append(func)
                decorators = []
            elif child.type == "lexical_declaration":
                funcs = self._extract_arrow_functions(child, content, file_path, decorators)
                functions.extend(funcs)
                decorators = []
            else:
                decorators = []

        return functions

    def _parse_function(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        parameters = []
        return_type = None
        docstring = None
        modifiers = []

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        return_type = self._get_node_text(subchild, content)
            elif child.type == "async":
                modifiers.append("async")

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        # Extract calls from the function body
        calls = []
        for child in node.children:
            if child.type == "statement_block":
                calls = self._extract_calls(child, content)
                break

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            annotations=decorators,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
            calls=calls,
        )

    def _extract_arrow_functions(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> list[FunctionDef]:
        """Extract arrow function declarations."""
        functions = []

        for child in node.children:
            if child.type == "variable_declarator":
                name = None
                arrow_func = None
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "arrow_function":
                        arrow_func = subchild

                if name and arrow_func:
                    func = self._parse_arrow_function(
                        arrow_func, name, content, file_path, decorators
                    )
                    if func:
                        functions.append(func)

        return functions

    def _parse_arrow_function(
        self,
        node: Node,
        name: str,
        content: str,
        file_path: Path,
        decorators: list[Annotation],
    ) -> FunctionDef | None:
        """Parse an arrow function."""
        parameters = []
        return_type = None
        modifiers = []

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "identifier":
                parameters.append(Parameter(name=self._get_node_text(child, content)))
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        return_type = self._get_node_text(subchild, content)
            elif child.type == "async":
                modifiers.append("async")

        # Extract calls from the arrow function body
        calls = []
        for child in node.children:
            if child.type == "statement_block":
                calls = self._extract_calls(child, content)
                break

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            annotations=decorators,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
            calls=calls,
        )

    def _extract_calls(self, node: Node, content: str) -> list[str]:
        """Extract function/method call targets from a syntax tree node.

        Recursively walks the node to find all `call_expression` nodes and
        extracts the callee name. Handles simple calls (func()), member calls
        (obj.method()), and chained calls (a.b.c()).
        """
        calls: list[str] = []
        self._find_calls(node, content, calls)
        seen: set[str] = set()
        unique: list[str] = []
        for c in calls:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    def _find_calls(self, node: Node, content: str, calls: list[str]) -> None:
        """Recursively find call expressions in a node."""
        if node.type == "call_expression":
            callee = self._resolve_callee(node, content)
            if callee:
                calls.append(callee)
        for child in node.children:
            self._find_calls(child, content, calls)

    def _resolve_callee(self, call_node: Node, content: str) -> str | None:
        """Resolve the callee of a call expression.

        For TypeScript call_expression nodes, the first child is the callee:
        - identifier: simple function call
        - member_expression: obj.method() or a.b.c()
        """
        for child in call_node.children:
            if child.type == "identifier":
                return self._get_node_text(child, content)
            elif child.type == "member_expression":
                return self._get_node_text(child, content)
            elif child.type == "arguments":
                break
        return None

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function parameters."""
        parameters = []

        for child in node.children:
            if child.type in ("required_parameter", "optional_parameter"):
                param = self._parse_typed_parameter(child, content)
                if param:
                    parameters.append(param)
            elif child.type == "rest_pattern":
                param = self._parse_rest_parameter(child, content)
                if param:
                    parameters.append(param)

        return parameters

    def _parse_typed_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a typed parameter."""
        name = None
        param_type = None
        default = None
        is_optional = node.type == "optional_parameter"

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        param_type = self._get_node_text(subchild, content)
            elif child.type not in (":", "=", "?"):
                if name is not None and child.type not in ("type_annotation",):
                    default = self._get_node_text(child, content)

        if name:
            if is_optional and param_type:
                param_type = f"{param_type}?"
            return Parameter(name=name, type=param_type, default=default)
        return None

    def _parse_rest_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a rest parameter (...args)."""
        name = None
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                name = f"...{self._get_node_text(child, content)}"
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        param_type = self._get_node_text(subchild, content)

        if name:
            return Parameter(name=name, type=param_type)
        return None

    def _extract_interfaces(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract interface definitions as ClassDef objects."""
        interfaces = []
        self._find_interfaces(root, content, file_path, interfaces)
        return interfaces

    def _find_interfaces(
        self, node: Node, content: str, file_path: Path, interfaces: list[ClassDef]
    ) -> None:
        """Recursively find interface definitions."""
        for child in node.children:
            if child.type == "interface_declaration":
                interface = self._parse_interface(child, content, file_path)
                if interface:
                    interfaces.append(interface)
            elif child.type == "export_statement":
                export_jsdoc = self._extract_jsdoc(child, content)
                for subchild in child.children:
                    if subchild.type == "interface_declaration":
                        interface = self._parse_interface(subchild, content, file_path)
                        if interface:
                            interface.modifiers.append("export")
                            if interface.docstring is None and export_jsdoc:
                                interface.docstring = export_jsdoc
                            interfaces.append(interface)

    def _parse_interface(self, node: Node, content: str, file_path: Path) -> ClassDef | None:
        """Parse an interface declaration as a ClassDef."""
        name = None
        interfaces = []
        docstring = None

        for child in node.children:
            if child.type == "type_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "extends_type_clause":
                for subchild in child.children:
                    if subchild.type in ("type_identifier", "generic_type"):
                        interfaces.append(self._get_node_text(subchild, content))

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        interface_annotation = Annotation(name="interface")

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            interfaces=interfaces,
            annotations=[interface_annotation],
            modifiers=["interface"],
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        for child in node.children:
            if child.type in ("object_type", "interface_body"):
                class_def.methods = self._extract_interface_methods(child, content, file_path)
                class_def.fields = self._extract_interface_fields(child, content)

        return class_def

    def _extract_interface_methods(
        self, object_type: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract method signatures from an interface."""
        methods = []

        for child in object_type.children:
            if child.type == "method_signature":
                method = self._parse_method_signature(child, content, file_path)
                if method:
                    methods.append(method)

        return methods

    def _parse_method_signature(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse a method signature."""
        name = None
        parameters = []
        return_type = None

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        return_type = self._get_node_text(subchild, content)

        docstring = self._extract_jsdoc(node, content)

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
            modifiers=["abstract"],
            source_code=self._get_node_text(node, content),
        )

    def _extract_interface_fields(self, object_type: Node, content: str) -> list[FieldDef]:
        """Extract property signatures from an interface."""
        fields = []

        for child in object_type.children:
            if child.type == "property_signature":
                field = self._parse_property_signature(child, content)
                if field:
                    fields.append(field)

        return fields

    def _parse_property_signature(self, node: Node, content: str) -> FieldDef | None:
        """Parse a property signature."""
        name = None
        field_type = None
        is_optional = False

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        field_type = self._get_node_text(subchild, content)
            elif child.type == "?":
                is_optional = True

        if name:
            if is_optional and field_type:
                field_type = f"{field_type}?"
            return FieldDef(
                name=name,
                type=field_type,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_class_fields(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract class field definitions."""
        fields = []

        for child in class_body.children:
            if child.type == "public_field_definition":
                field = self._parse_class_field(child, content)
                if field:
                    fields.append(field)

        return fields

    def _parse_class_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a class field definition."""
        name = None
        field_type = None
        modifiers = []

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "type_annotation":
                for subchild in child.children:
                    if subchild.type != ":":
                        field_type = self._get_node_text(subchild, content)
            elif child.type in ("public", "private", "protected", "readonly", "static"):
                modifiers.append(child.type)
            elif child.type == "accessibility_modifier":
                modifiers.append(self._get_node_text(child, content))

        if name:
            return FieldDef(
                name=name,
                type=field_type,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None
