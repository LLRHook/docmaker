"""Python parser using Tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_python as tspython
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

PYTHON_LANGUAGE = Language(tspython.language())


class PythonParser(BaseParser):
    """Parser for Python source files using Tree-sitter."""

    def __init__(self):
        self._parser = Parser(PYTHON_LANGUAGE)

    @property
    def language(self) -> LangEnum:
        return LangEnum.PYTHON

    def can_parse(self, file: SourceFile) -> bool:
        return file.language == LangEnum.PYTHON

    def parse(self, file: SourceFile) -> FileSymbols:
        """Parse a Python file and extract all symbols."""
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
        return file_path.stem if file_path.stem != "__init__" else file_path.parent.name

    def _extract_imports(self, root: Node, content: str) -> list[ImportDef]:
        """Extract all import statements."""
        imports = []
        for child in root.children:
            if child.type == "import_statement":
                imports.extend(self._parse_import_statement(child, content))
            elif child.type == "import_from_statement":
                imports.extend(self._parse_import_from_statement(child, content))
        return imports

    def _parse_import_statement(self, node: Node, content: str) -> list[ImportDef]:
        """Parse 'import x, y as z' statements."""
        imports = []
        for child in node.children:
            if child.type == "dotted_name":
                module = self._get_node_text(child, content)
                imports.append(
                    ImportDef(
                        module=module,
                        line_number=node.start_point[0] + 1,
                    )
                )
            elif child.type == "aliased_import":
                module = None
                alias = None
                for subchild in child.children:
                    if subchild.type == "dotted_name":
                        module = self._get_node_text(subchild, content)
                    elif subchild.type == "identifier":
                        alias = self._get_node_text(subchild, content)
                if module:
                    imports.append(
                        ImportDef(
                            module=module,
                            alias=alias,
                            line_number=node.start_point[0] + 1,
                        )
                    )
        return imports

    def _parse_import_from_statement(self, node: Node, content: str) -> list[ImportDef]:
        """Parse 'from x import y, z' statements."""
        imports = []
        module_name = None
        is_wildcard = False
        found_import_keyword = False

        for child in node.children:
            if child.type == "import":
                found_import_keyword = True
            elif child.type == "dotted_name":
                name = self._get_node_text(child, content)
                if not found_import_keyword:
                    module_name = name
                else:
                    full_module = f"{module_name}.{name}" if module_name else name
                    imports.append(
                        ImportDef(
                            module=full_module,
                            line_number=node.start_point[0] + 1,
                        )
                    )
            elif child.type == "relative_import":
                module_name = self._get_node_text(child, content)
            elif child.type == "wildcard_import":
                is_wildcard = True
            elif child.type == "identifier" and found_import_keyword:
                name = self._get_node_text(child, content)
                full_module = f"{module_name}.{name}" if module_name else name
                imports.append(
                    ImportDef(
                        module=full_module,
                        line_number=node.start_point[0] + 1,
                    )
                )
            elif child.type == "aliased_import":
                name = None
                alias = None
                for subchild in child.children:
                    if subchild.type == "identifier":
                        if name is None:
                            name = self._get_node_text(subchild, content)
                        else:
                            alias = self._get_node_text(subchild, content)
                    elif subchild.type == "dotted_name":
                        if name is None:
                            name = self._get_node_text(subchild, content)
                if name:
                    full_module = f"{module_name}.{name}" if module_name else name
                    imports.append(
                        ImportDef(
                            module=full_module,
                            alias=alias,
                            line_number=node.start_point[0] + 1,
                        )
                    )

        if is_wildcard and module_name:
            imports.append(
                ImportDef(
                    module=f"{module_name}.*",
                    is_wildcard=True,
                    line_number=node.start_point[0] + 1,
                )
            )

        return imports

    def _extract_classes(self, root: Node, content: str, file_path: Path) -> list[ClassDef]:
        """Extract all class definitions from the module level."""
        classes = []
        for child in root.children:
            if child.type == "class_definition":
                class_def = self._parse_class(child, content, file_path, decorators=[])
                if class_def:
                    classes.append(class_def)
            elif child.type == "decorated_definition":
                decorators = self._extract_decorators(child, content)
                for subchild in child.children:
                    if subchild.type == "class_definition":
                        class_def = self._parse_class(
                            subchild, content, file_path, decorators=decorators
                        )
                        if class_def:
                            classes.append(class_def)
        return classes

    def _parse_class(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> ClassDef | None:
        """Parse a class definition node."""
        name = None
        superclass = None
        interfaces = []
        docstring = None

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "argument_list":
                bases = self._extract_base_classes(child, content)
                if bases:
                    superclass = bases[0]
                    interfaces = bases[1:]

        if not name:
            return None

        block = None
        for child in node.children:
            if child.type == "block":
                block = child
                docstring = self._extract_docstring(block, content)
                break

        class_def = ClassDef(
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            superclass=superclass,
            interfaces=interfaces,
            annotations=decorators,
            docstring=docstring,
            source_code=self._get_node_text(node, content),
        )

        if block:
            class_def.methods = self._extract_methods(block, content, file_path)
            class_def.fields = self._extract_class_fields(block, content)

        return class_def

    def _extract_base_classes(self, argument_list: Node, content: str) -> list[str]:
        """Extract base class names from argument list."""
        bases = []
        for child in argument_list.children:
            if child.type == "identifier":
                bases.append(self._get_node_text(child, content))
            elif child.type == "attribute":
                bases.append(self._get_node_text(child, content))
        return bases

    def _extract_docstring(self, block: Node, content: str) -> str | None:
        """Extract docstring from the first statement in a block."""
        for child in block.children:
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "string":
                        text = self._get_node_text(subchild, content)
                        return self._clean_docstring(text)
                break
        return None

    def _clean_docstring(self, docstring: str) -> str:
        """Clean up a Python docstring."""
        text = docstring.strip()
        if text.startswith('"""') and text.endswith('"""'):
            text = text[3:-3]
        elif text.startswith("'''") and text.endswith("'''"):
            text = text[3:-3]
        elif text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]

        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned.append(stripped)
        return "\n".join(cleaned)

    def _extract_decorators(self, decorated_def: Node, content: str) -> list[Annotation]:
        """Extract decorators from a decorated definition."""
        decorators = []
        for child in decorated_def.children:
            if child.type == "decorator":
                decorator = self._parse_decorator(child, content)
                if decorator:
                    decorators.append(decorator)
        return decorators

    def _parse_decorator(self, node: Node, content: str) -> Annotation | None:
        """Parse a single decorator."""
        name = None
        arguments = {}

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "attribute":
                name = self._get_node_text(child, content)
            elif child.type == "call":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "attribute":
                        name = self._get_node_text(subchild, content)
                    elif subchild.type == "argument_list":
                        arguments = self._parse_decorator_arguments(subchild, content)

        if name:
            return Annotation(name=name, arguments=arguments)
        return None

    def _parse_decorator_arguments(self, node: Node, content: str) -> dict[str, str]:
        """Parse decorator arguments."""
        args = {}
        positional_index = 0

        for child in node.children:
            if child.type == "keyword_argument":
                key = None
                value = None
                for subchild in child.children:
                    if subchild.type == "identifier":
                        key = self._get_node_text(subchild, content)
                    elif subchild.type in ("string", "integer", "float", "true", "false"):
                        value = self._get_node_text(subchild, content).strip("\"'")
                if key and value:
                    args[key] = value
            elif child.type == "string":
                args[f"arg{positional_index}"] = self._get_node_text(child, content).strip("\"'")
                positional_index += 1

        return args

    def _extract_methods(
        self, class_body: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract methods from a class body."""
        methods = []

        for child in class_body.children:
            if child.type == "function_definition":
                method = self._parse_function(child, content, file_path, decorators=[])
                if method:
                    methods.append(method)
            elif child.type == "decorated_definition":
                decorators = self._extract_decorators(child, content)
                for subchild in child.children:
                    if subchild.type == "function_definition":
                        method = self._parse_function(
                            subchild, content, file_path, decorators=decorators
                        )
                        if method:
                            methods.append(method)

        return methods

    def _extract_module_functions(
        self, root: Node, content: str, file_path: Path
    ) -> list[FunctionDef]:
        """Extract module-level functions."""
        functions = []

        for child in root.children:
            if child.type == "function_definition":
                func = self._parse_function(child, content, file_path, decorators=[])
                if func:
                    functions.append(func)
            elif child.type == "decorated_definition":
                decorators = self._extract_decorators(child, content)
                for subchild in child.children:
                    if subchild.type == "function_definition":
                        func = self._parse_function(
                            subchild, content, file_path, decorators=decorators
                        )
                        if func:
                            functions.append(func)

        return functions

    def _parse_function(
        self, node: Node, content: str, file_path: Path, decorators: list[Annotation]
    ) -> FunctionDef | None:
        """Parse a function definition."""
        name = None
        parameters = []
        return_type = None
        docstring = None
        modifiers = []

        is_async = False
        for child in node.children:
            if child.type == "async":
                is_async = True
                break

        if is_async:
            modifiers.append("async")

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "parameters":
                parameters = self._parse_parameters(child, content)
            elif child.type == "type":
                return_type = self._get_node_text(child, content)
            elif child.type == "block":
                docstring = self._extract_docstring(child, content)

        if not name:
            return None

        for decorator in decorators:
            if decorator.name in ("staticmethod", "classmethod", "property", "abstractmethod"):
                modifiers.append(decorator.name)

        body = None
        for child in node.children:
            if child.type == "block":
                body = child
                break

        calls = self._extract_constructor_calls(body, content) if body else []

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

    def _extract_constructor_calls(self, node: Node, content: str) -> list[str]:
        """Extract constructor instantiation calls (ClassName()) from a function body.

        Uses the convention that class names start with an uppercase letter.
        """
        calls: list[str] = []
        self._find_constructor_calls(node, content, calls)
        return calls

    def _find_constructor_calls(self, node: Node, content: str, calls: list[str]) -> None:
        """Recursively find call expressions that look like constructor calls."""
        if node.type == "call":
            func_node = node.children[0] if node.children else None
            if func_node:
                if func_node.type == "identifier":
                    name = self._get_node_text(func_node, content)
                    if name and name[0].isupper():
                        if name not in calls:
                            calls.append(name)
                elif func_node.type == "attribute":
                    # e.g., module.ClassName()
                    text = self._get_node_text(func_node, content)
                    parts = text.rsplit(".", 1)
                    if len(parts) == 2 and parts[1] and parts[1][0].isupper():
                        if text not in calls:
                            calls.append(text)

        for child in node.children:
            self._find_constructor_calls(child, content, calls)

    def _parse_parameters(self, node: Node, content: str) -> list[Parameter]:
        """Parse function parameters."""
        parameters = []

        for child in node.children:
            if child.type in (
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
                "list_splat_pattern",
                "dictionary_splat_pattern",
            ):
                param = self._parse_single_parameter(child, content)
                if param:
                    parameters.append(param)

        return parameters

    def _parse_single_parameter(self, node: Node, content: str) -> Parameter | None:
        """Parse a single parameter."""
        name = None
        param_type = None
        default = None

        if node.type == "identifier":
            name = self._get_node_text(node, content)
        elif node.type == "typed_parameter":
            for child in node.children:
                if child.type == "identifier":
                    name = self._get_node_text(child, content)
                elif child.type == "type":
                    param_type = self._get_node_text(child, content)
        elif node.type == "default_parameter":
            for child in node.children:
                if child.type == "identifier":
                    name = self._get_node_text(child, content)
                elif child.type not in ("=",):
                    if name is not None:
                        default = self._get_node_text(child, content)
        elif node.type == "typed_default_parameter":
            for child in node.children:
                if child.type == "identifier":
                    name = self._get_node_text(child, content)
                elif child.type == "type":
                    param_type = self._get_node_text(child, content)
                elif child.type not in ("=", ":", "identifier", "type"):
                    default = self._get_node_text(child, content)
        elif node.type == "list_splat_pattern":
            for child in node.children:
                if child.type == "identifier":
                    name = f"*{self._get_node_text(child, content)}"
        elif node.type == "dictionary_splat_pattern":
            for child in node.children:
                if child.type == "identifier":
                    name = f"**{self._get_node_text(child, content)}"

        if name:
            return Parameter(name=name, type=param_type, default=default)
        return None

    def _extract_class_fields(self, class_body: Node, content: str) -> list[FieldDef]:
        """Extract class-level fields from assignment statements."""
        fields = []

        for child in class_body.children:
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "assignment":
                        field = self._parse_assignment_field(subchild, content)
                        if field:
                            fields.append(field)

        return fields

    def _parse_assignment_field(self, node: Node, content: str) -> FieldDef | None:
        """Parse a field from an assignment statement."""
        name = None
        field_type = None

        for child in node.children:
            if child.type == "identifier":
                name = self._get_node_text(child, content)
            elif child.type == "type":
                field_type = self._get_node_text(child, content)

        if name and not name.startswith("_"):
            return FieldDef(
                name=name,
                type=field_type,
                line_number=node.start_point[0] + 1,
            )
        return None
