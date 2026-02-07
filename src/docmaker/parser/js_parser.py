"""JavaScript parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_javascript as tsjavascript
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

JS_LANGUAGE = Language(tsjavascript.language())


class JavaScriptParser(BaseParser):
    """Parser for JavaScript source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(JS_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.JAVASCRIPT

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.JAVASCRIPT

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a JavaScript file and extract all symbols."""
        content = self.read_file_content(file.path)
        tree = self._parser.parse(content.encode("utf-8"))

        symbols = FileSymbols(file=file)
        symbols.package = self._extract_module_name(file.path)
        symbols.imports = self._extract_imports(tree.root_node, content)
        symbols.classes = self._extract_classes(tree.root_node, content, file.path)
        symbols.functions = self._extract_module_functions(tree.root_node, content, file.path)

        return symbols

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte : node.end_byte]

    def _extract_module_name(self, file_path: Path) -> str | None:
        """Extract module name from file path."""
        return file_path.stem

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements and require calls."""
        imports = []
        for child in root.children:
            if child.type == "import_statement":
                imports.extend(self._parse_import_statement(child, content))
            elif child.type == "lexical_declaration" or child.type == "variable_declaration":
                imp = self._parse_require(child, content)
                if imp:
                    imports.append(imp)
        return imports

    def _parse_import_statement(self, node: Node, content: str) -> list[ImportDef]:
        """Parse an ES module import statement."""
        imports = []
        module_path = None

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
                                    full_module = (
                                        f"{module_path}.{name}" if module_path else name
                                    )
                                    imports.append(
                                        ImportDef(
                                            module=full_module,
                                            alias=alias,
                                            line_number=node.start_point[0] + 1,
                                        )
                                    )
                    elif subchild.type == "namespace_import":
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
                    line_number=node.start_point[0] + 1,
                )
            )

        return imports

    def _parse_require(self, node: Node, content: str) -> ImportDef | None:
        """Parse a CommonJS require() call."""
        for child in node.children:
            if child.type == "variable_declarator":
                name = None
                module = None
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "call_expression":
                        func_name = None
                        for call_child in subchild.children:
                            if call_child.type == "identifier":
                                func_name = self._get_node_text(call_child, content)
                            elif call_child.type == "arguments":
                                for arg in call_child.children:
                                    if arg.type == "string":
                                        module = self._get_node_text(arg, content).strip(
                                            "\"'"
                                        )
                        if func_name != "require":
                            module = None
                if name and module:
                    return ImportDef(
                        module=module,
                        alias=name,
                        line_number=node.start_point[0] + 1,
                    )
        return None

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
            else:
                break
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

    def _extract_classes(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract all class definitions."""
        classes = []
        for child in root.children:
            if child.type == "class_declaration":
                class_def = self._parse_class(child, content, file_path)
                if class_def:
                    classes.append(class_def)
            elif child.type == "export_statement":
                for subchild in child.children:
                    if subchild.type == "class_declaration":
                        export_jsdoc = self._extract_jsdoc(child, content)
                        class_def = self._parse_class(subchild, content, file_path)
                        if class_def:
                            class_def.modifiers.append("export")
                            if class_def.docstring is None and export_jsdoc:
                                class_def.docstring = export_jsdoc
                            classes.append(class_def)
        return classes

    def _parse_class(
        self, node: Node, content: str, file_path: Path
    ) -> ClassDef | None:
        """Parse a class declaration."""
        name = None
        superclass = None
        modifiers = []

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "class_heritage":
                for subchild in child.children:
                    if subchild.type == "extends_clause":
                        for ext_child in subchild.children:
                            if ext_child.type == "identifier":
                                superclass = self._get_node_text(ext_child, content)

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            superclass=superclass,
            modifiers=modifiers,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        for child in node.children:
            if child.type == "class_body":
                class_def.methods = self._extract_methods(child, content, file_path)
                class_def.fields = self._extract_class_fields(child, content)

        return class_def

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract methods from a class body."""
        methods = []
        for child in class_body.children:
            if child.type == "method_definition":
                method = self._parse_method(child, content, file_path)
                if method:
                    methods.append(method)
        return methods

    def _parse_method(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse a method definition."""
        name = None
        parameters = []
        modifiers = []

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "async":
                modifiers.append("async")
            elif child.type == "static":
                modifiers.append("static")
            elif child.type == "get":
                modifiers.append("get")
            elif child.type == "set":
                modifiers.append("set")

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            docstring=docstring,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
        )

    def _extract_class_fields(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract class field definitions."""
        fields = []
        for child in class_body.children:
            if child.type == "field_definition":
                field = self._parse_class_field(child, content)
                if field:
                    fields.append(field)
        return fields

    def _parse_class_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a class field definition."""
        name = None
        modifiers = []

        for child in node.children:
            if child.type == "property_identifier":
                name = self._get_node_text(child, content)
            elif child.type == "static":
                modifiers.append("static")

        if name:
            return FieldDef(
                name=name,
                modifiers=modifiers,
                line_number=node.start_point[0] + 1,
            )
        return None

    def _extract_module_functions(
        self, root: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract module-level functions."""
        functions = []

        for child in root.children:
            if child.type == "function_declaration":
                func = self._parse_function(child, content, file_path)
                if func:
                    functions.append(func)
            elif child.type == "export_statement":
                export_jsdoc = self._extract_jsdoc(child, content)
                for subchild in child.children:
                    if subchild.type == "function_declaration":
                        func = self._parse_function(subchild, content, file_path)
                        if func:
                            func.modifiers.append("export")
                            if func.docstring is None and export_jsdoc:
                                func.docstring = export_jsdoc
                            functions.append(func)
            elif child.type == "lexical_declaration" or child.type == "variable_declaration":
                funcs = self._extract_arrow_functions(child, content, file_path)
                functions.extend(funcs)

        return functions

    def _parse_function(
        self, node: Node, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse a function declaration."""
        name = None
        parameters = []
        modifiers = []

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "async":
                modifiers.append("async")

        docstring = self._extract_jsdoc(node, content)

        if not name:
            return None

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            docstring=docstring,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
        )

    def _extract_arrow_functions(
        self, node: Node, content: str, file_path: Path
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
                    func = self._parse_arrow_function(arrow_func, name, content, file_path)
                    if func:
                        functions.append(func)

        return functions

    def _parse_arrow_function(
        self, node: Node, name: str, content: str, file_path: Path
    ) -> FunctionDef | None:
        """Parse an arrow function."""
        parameters = []
        modifiers = []

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "identifier":
                parameters.append(Parameter(name=self._get_node_text(child, content)))
            elif child.type == "async":
                modifiers.append("async")

        return FunctionDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            modifiers=modifiers,
            source_code=self._get_node_text(node, content),
        )

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function parameters."""
        parameters = []
        for child in node.children:
            if child.type == "identifier":
                parameters.append(
                    Parameter(name=self._get_node_text(child, content))
                )
            elif child.type == "assignment_pattern":
                param = self._parse_default_parameter(child, content)
                if param:
                    parameters.append(param)
            elif child.type == "rest_pattern":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = f"...{self._get_node_text(subchild, content)}"
                        parameters.append(Parameter(name=name))
            elif child.type == "object_pattern" or child.type == "array_pattern":
                parameters.append(
                    Parameter(name=self._get_node_text(child, content))
                )
        return parameters

    def _parse_default_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a parameter with a default value."""
        name = None
        default = None

        for child in node.children:
            if child.type == "identifier" and name is None:
                name = self._get_node_text(child, content)
            elif child.type != "=" and name is not None:
                default = self._get_node_text(child, content)

        if name:
            return Parameter(name=name, default=default)
        return None
