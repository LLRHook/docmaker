"""Markdown generator for Obsidian documentation."""

import logging
from datetime import datetime
from pathlib import Path

from docmaker.config import OutputConfig
from docmaker.generator.linker import ImportLinker
from docmaker.models import (
    Annotation,
    ClassDef,
    EndpointDef,
    FileSymbols,
    FunctionDef,
    SymbolTable,
)

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generates Obsidian-compatible markdown documentation."""

    def __init__(self, config: OutputConfig, symbol_table: SymbolTable):
        self.config = config
        self.symbol_table = symbol_table
        self.linker = ImportLinker(symbol_table)
        self.output_dir = config.output_dir

    def generate_all(self) -> list[Path]:
        """Generate documentation for all files in the symbol table."""
        generated_files = []

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for file_path, file_symbols in self.symbol_table.files.items():
            output_path = self._get_output_path(file_symbols)
            content = self._generate_file_doc(file_symbols)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(output_path)
            logger.debug(f"Generated: {output_path}")

        if self.config.generate_index:
            index_path = self._generate_index()
            generated_files.append(index_path)

            endpoints_index = self._generate_endpoints_index()
            if endpoints_index:
                generated_files.append(endpoints_index)

            moc_paths = self._generate_package_mocs()
            generated_files.extend(moc_paths)

        return generated_files

    def _get_output_path(self, file_symbols: FileSymbols) -> Path:
        """Get the output path for a file's documentation."""
        relative = file_symbols.file.relative_path
        md_name = relative.stem + ".md"

        if self.config.mirror_source_structure:
            return self.output_dir / relative.parent / md_name
        else:
            return self.output_dir / md_name

    def _generate_file_doc(self, file_symbols: FileSymbols) -> str:
        """Generate documentation for a single file."""
        lines = []

        lines.append(self._generate_frontmatter(file_symbols))

        lines.append(f"# {file_symbols.file.relative_path.stem}\n")

        lines.append("> [!info] File Info")
        lines.append(f"> - **Path:** `{file_symbols.file.relative_path}`")
        lines.append(f"> - **Language:** {file_symbols.file.language.value}")
        lines.append(f"> - **Category:** {file_symbols.file.category.value}")
        if file_symbols.package:
            lines.append(f"> - **Package:** `{file_symbols.package}`")
        lines.append("")

        if file_symbols.imports:
            lines.append("## Imports\n")
            for imp in file_symbols.imports[:20]:
                link = self._get_import_link(imp.module)
                lines.append(f"- {link}")
            if len(file_symbols.imports) > 20:
                lines.append(f"- *... and {len(file_symbols.imports) - 20} more*")
            lines.append("")

        for cls in file_symbols.classes:
            lines.append(self._generate_class_doc(cls, file_symbols))

        for func in file_symbols.functions:
            lines.append(self._generate_function_doc(func, file_symbols))

        endpoints = [ep for ep in file_symbols.endpoints]
        if endpoints:
            lines.append("## REST Endpoints\n")
            for endpoint in endpoints:
                lines.append(self._generate_endpoint_doc(endpoint, file_symbols))

        return "\n".join(lines)

    def _generate_frontmatter(self, file_symbols: FileSymbols) -> str:
        """Generate YAML frontmatter."""
        tags = [file_symbols.file.language.value, file_symbols.file.category.value]

        for cls in file_symbols.classes:
            for ann in cls.annotations:
                if ann.name in ("RestController", "Controller"):
                    tags.append("controller")
                elif ann.name == "Service":
                    tags.append("service")
                elif ann.name == "Repository":
                    tags.append("repository")
                elif ann.name == "Entity":
                    tags.append("entity")
                elif ann.name == "Configuration":
                    tags.append("configuration")
                elif ann.name == "interface":
                    tags.append("interface")
                elif ann.name == "dataclass":
                    tags.append("dataclass")
                elif ann.name == "Component":
                    tags.append("component")
                elif ann.name == "Injectable":
                    tags.append("injectable")

        lines = [
            "---",
            f"title: {file_symbols.file.relative_path.stem}",
            f"path: {file_symbols.file.relative_path}",
            f"language: {file_symbols.file.language.value}",
            f"category: {file_symbols.file.category.value}",
            f"tags: [{', '.join(tags)}]",
            f"generated: {datetime.now().isoformat()}",
            "---\n",
        ]
        return "\n".join(lines)

    def _generate_class_doc(self, cls: ClassDef, file_symbols: FileSymbols) -> str:
        """Generate documentation for a class."""
        lines = []

        lines.append(f"## Class: `{cls.name}`\n")

        if cls.annotations:
            ann_strs = [self._format_annotation(a) for a in cls.annotations]
            lines.append(f"**Annotations:** {', '.join(ann_strs)}\n")

        if cls.modifiers:
            lines.append(f"**Modifiers:** `{' '.join(cls.modifiers)}`\n")

        if cls.superclass:
            link = self.linker.get_wikilink(cls.superclass, file_symbols)
            lines.append(f"**Extends:** {link}\n")

        if cls.interfaces:
            iface_links = [self.linker.get_wikilink(i, file_symbols) for i in cls.interfaces]
            lines.append(f"**Implements:** {', '.join(iface_links)}\n")

        if cls.summary:
            lines.append(f"**Summary:** {cls.summary}\n")

        if cls.docstring:
            lines.append(f"> {cls.docstring}\n")

        usages = self.linker.find_usages(cls.name)
        if usages:
            lines.append("### Used By\n")
            for user_class, usage_type in usages[:10]:
                lines.append(f"- [[{user_class}]] ({usage_type})")
            lines.append("")

        if cls.fields:
            lines.append("### Fields\n")
            lines.append("| Name | Type | Modifiers | Annotations |")
            lines.append("|------|------|-----------|-------------|")
            for field in cls.fields:
                type_link = (
                    self.linker.get_wikilink(field.type, file_symbols) if field.type else "-"
                )
                mods = " ".join(field.modifiers) if field.modifiers else "-"
                anns = (
                    ", ".join(self._format_annotation(a) for a in field.annotations)
                    if field.annotations
                    else "-"
                )
                lines.append(f"| `{field.name}` | {type_link} | `{mods}` | {anns} |")
            lines.append("")

        if cls.methods:
            lines.append("### Methods\n")
            for method in cls.methods:
                lines.append(self._generate_method_doc(method, cls, file_symbols))

        return "\n".join(lines)

    def _generate_method_doc(
        self, method: FunctionDef, cls: ClassDef, file_symbols: FileSymbols
    ) -> str:
        """Generate documentation for a method."""
        lines = []

        lines.append(f"#### `{method.name}()`\n")

        if method.annotations:
            ann_strs = [self._format_annotation(a) for a in method.annotations]
            lines.append(f"**Annotations:** {', '.join(ann_strs)}\n")

        if method.modifiers:
            lines.append(f"**Modifiers:** `{' '.join(method.modifiers)}`\n")

        if method.return_type:
            ret_link = self.linker.get_wikilink(method.return_type, file_symbols)
            lines.append(f"**Returns:** {ret_link}\n")

        if method.summary:
            lines.append(f"**Summary:** {method.summary}\n")

        if method.docstring:
            lines.append(f"> {method.docstring}\n")

        if method.parameters:
            lines.append("**Parameters:**\n")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for param in method.parameters:
                type_link = (
                    self.linker.get_wikilink(param.type, file_symbols) if param.type else "-"
                )
                desc = param.description or "-"
                lines.append(f"| `{param.name}` | {type_link} | {desc} |")
            lines.append("")

        if self.config.include_source_snippets:
            snippet = self._truncate_source(method.source_code)
            lang = file_symbols.file.language.value
            lines.append("<details>")
            lines.append("<summary>Source Code</summary>\n")
            lines.append(f"```{lang}")
            lines.append(snippet)
            lines.append("```")
            lines.append("</details>\n")

        lines.append(f"📍 *Line {method.line_number}*\n")

        return "\n".join(lines)

    def _generate_function_doc(self, func: FunctionDef, file_symbols: FileSymbols) -> str:
        """Generate documentation for a standalone function."""
        lines = []

        lines.append(f"## Function: `{func.name}()`\n")

        if func.annotations:
            ann_strs = [self._format_annotation(a) for a in func.annotations]
            lines.append(f"**Annotations:** {', '.join(ann_strs)}\n")

        if func.return_type:
            ret_link = self.linker.get_wikilink(func.return_type, file_symbols)
            lines.append(f"**Returns:** {ret_link}\n")

        if func.summary:
            lines.append(f"**Summary:** {func.summary}\n")

        if func.docstring:
            lines.append(f"> {func.docstring}\n")

        if func.parameters:
            lines.append("**Parameters:**\n")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for param in func.parameters:
                type_link = (
                    self.linker.get_wikilink(param.type, file_symbols) if param.type else "-"
                )
                desc = param.description or "-"
                lines.append(f"| `{param.name}` | {type_link} | {desc} |")
            lines.append("")

        if self.config.include_source_snippets:
            snippet = self._truncate_source(func.source_code)
            lang = file_symbols.file.language.value
            lines.append("<details>")
            lines.append("<summary>Source Code</summary>\n")
            lines.append(f"```{lang}")
            lines.append(snippet)
            lines.append("```")
            lines.append("</details>\n")

        return "\n".join(lines)

    def _generate_endpoint_doc(self, endpoint: EndpointDef, file_symbols: FileSymbols) -> str:
        """Generate documentation for a REST endpoint."""
        lines = []

        method_badge = self._get_method_badge(endpoint.http_method)
        lines.append(f"### {method_badge} `{endpoint.path}`\n")

        if endpoint.description:
            lines.append(f"> {endpoint.description}\n")

        lines.append("| Property | Value |")
        lines.append("|----------|-------|")
        handler_link = self.linker.get_method_link(endpoint.handler_class, endpoint.handler_method)
        lines.append(f"| **Handler** | {handler_link} |")
        if endpoint.response_type:
            ret_link = self.linker.get_wikilink(endpoint.response_type, file_symbols)
            lines.append(f"| **Response** | {ret_link} |")
        if endpoint.request_body:
            body_link = self.linker.get_wikilink(endpoint.request_body, file_symbols)
            lines.append(f"| **Request Body** | {body_link} |")
        lines.append("")

        path_params = [
            p for p in endpoint.parameters if p.description and "@PathVariable" in p.description
        ]
        query_params = [
            p for p in endpoint.parameters if p.description and "@RequestParam" in p.description
        ]
        body_params = [
            p for p in endpoint.parameters if p.description and "@RequestBody" in p.description
        ]

        if path_params:
            lines.append("#### Path Parameters\n")
            lines.append("| Parameter | Type | Required | Description |")
            lines.append("|-----------|------|----------|-------------|")
            for param in path_params:
                type_link = (
                    self.linker.get_wikilink(param.type, file_symbols) if param.type else "-"
                )
                lines.append(f"| `{param.name}` | {type_link} | ✅ | - |")
            lines.append("")

        if query_params:
            lines.append("#### Query Parameters\n")
            lines.append("| Parameter | Type | Required | Description |")
            lines.append("|-----------|------|----------|-------------|")
            for param in query_params:
                type_link = (
                    self.linker.get_wikilink(param.type, file_symbols) if param.type else "-"
                )
                required = "✅" if "required=true" in (param.description or "") else "❌"
                lines.append(f"| `{param.name}` | {type_link} | {required} | - |")
            lines.append("")

        lines.append("#### Request Example\n")
        lines.append("```http")
        example_path = endpoint.path
        for param in path_params:
            example_path = example_path.replace(f"{{{param.name}}}", f"<{param.name}>")
        lines.append(f"{endpoint.http_method} {example_path}")
        if body_params:
            lines.append("Content-Type: application/json")
            lines.append("")
            lines.append("{")
            lines.append('  "field": "value"')
            lines.append("}")
        lines.append("```\n")

        lines.append("#### Response Example\n")
        lines.append("**200 OK**")
        lines.append("```json")
        lines.append("{")
        lines.append('  "status": "success"')
        lines.append("}")
        lines.append("```\n")

        if self.config.include_source_snippets:
            snippet = self._truncate_source(endpoint.source_code)
            lang = file_symbols.file.language.value
            lines.append("<details>")
            lines.append("<summary>Handler Source Code</summary>\n")
            lines.append(f"```{lang}")
            lines.append(snippet)
            lines.append("```")
            lines.append("</details>\n")

        lines.append(f"📍 *{endpoint.file_path.name}:{endpoint.line_number}*\n")

        return "\n".join(lines)

    def _generate_index(self) -> Path:
        """Generate the main index file."""
        lines = []

        lines.append("---")
        lines.append("title: Documentation Index")
        lines.append(f"generated: {datetime.now().isoformat()}")
        lines.append("---\n")

        lines.append("# Documentation Index\n")

        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        lines.append("## Statistics\n")
        lines.append(f"- **Total Files:** {len(self.symbol_table.files)}")
        lines.append(f"- **Total Classes:** {len(self.symbol_table.class_index)}")
        lines.append(f"- **Total Endpoints:** {len(self.symbol_table.endpoint_index)}")
        lines.append("")

        controllers = []
        services = []
        repositories = []
        entities = []
        others = []

        for fqn, cls in self.symbol_table.class_index.items():
            ann_names = {a.name for a in cls.annotations}
            if "RestController" in ann_names or "Controller" in ann_names:
                controllers.append(cls)
            elif "Service" in ann_names:
                services.append(cls)
            elif "Repository" in ann_names:
                repositories.append(cls)
            elif "Entity" in ann_names:
                entities.append(cls)
            else:
                others.append(cls)

        if controllers:
            lines.append("## Controllers\n")
            for cls in sorted(controllers, key=lambda c: c.name):
                lines.append(f"- [[{cls.name}]]")
            lines.append("")

        if services:
            lines.append("## Services\n")
            for cls in sorted(services, key=lambda c: c.name):
                lines.append(f"- [[{cls.name}]]")
            lines.append("")

        if repositories:
            lines.append("## Repositories\n")
            for cls in sorted(repositories, key=lambda c: c.name):
                lines.append(f"- [[{cls.name}]]")
            lines.append("")

        if entities:
            lines.append("## Entities\n")
            for cls in sorted(entities, key=lambda c: c.name):
                lines.append(f"- [[{cls.name}]]")
            lines.append("")

        if others:
            lines.append("## Other Classes\n")
            for cls in sorted(others, key=lambda c: c.name)[:50]:
                lines.append(f"- [[{cls.name}]]")
            if len(others) > 50:
                lines.append(f"- *... and {len(others) - 50} more*")
            lines.append("")

        index_path = self.output_dir / "index.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return index_path

    def _generate_endpoints_index(self) -> Path | None:
        """Generate an index of all REST endpoints."""
        if not self.symbol_table.endpoint_index:
            return None

        lines = []

        lines.append("---")
        lines.append("title: API Endpoints")
        lines.append(f"generated: {datetime.now().isoformat()}")
        lines.append("---\n")

        lines.append("# API Endpoints\n")

        lines.append(f"*Total Endpoints: {len(self.symbol_table.endpoint_index)}*\n")

        by_controller: dict[str, list[EndpointDef]] = {}
        for endpoint in self.symbol_table.endpoint_index.values():
            if endpoint.handler_class not in by_controller:
                by_controller[endpoint.handler_class] = []
            by_controller[endpoint.handler_class].append(endpoint)

        for controller in sorted(by_controller.keys()):
            endpoints = by_controller[controller]
            lines.append(f"## [[{controller}]]\n")

            lines.append("| Method | Path | Handler |")
            lines.append("|--------|------|---------|")
            for ep in sorted(endpoints, key=lambda e: e.path):
                badge = self._get_method_badge(ep.http_method)
                lines.append(f"| {badge} | `{ep.path}` | `{ep.handler_method}()` |")
            lines.append("")

        index_path = self.output_dir / "endpoints.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return index_path

    def _generate_package_mocs(self) -> list[Path]:
        """Generate Map of Content index pages per package."""
        packages: dict[str, list[FileSymbols]] = {}

        for file_symbols in self.symbol_table.files.values():
            pkg = file_symbols.package
            if not pkg:
                parent = str(file_symbols.file.relative_path.parent)
                pkg = parent if parent != "." else "(root)"
            if pkg not in packages:
                packages[pkg] = []
            packages[pkg].append(file_symbols)

        moc_paths = []
        for pkg, file_list in sorted(packages.items()):
            lines = []

            lines.append("---")
            lines.append(f'title: "{pkg}"')
            lines.append("type: moc")
            lines.append(f"generated: {datetime.now().isoformat()}")
            lines.append("---\n")

            lines.append(f"# {pkg}\n")
            lines.append(f"*Map of Content for package `{pkg}`*\n")

            all_classes = []
            all_functions = []
            all_endpoints = []
            for fs in file_list:
                all_classes.extend(fs.classes)
                all_functions.extend(fs.functions)
                all_endpoints.extend(fs.endpoints)

            lines.append("## Overview\n")
            lines.append(f"- **Files:** {len(file_list)}")
            lines.append(f"- **Classes:** {len(all_classes)}")
            lines.append(f"- **Functions:** {len(all_functions)}")
            if all_endpoints:
                lines.append(f"- **Endpoints:** {len(all_endpoints)}")
            lines.append("")

            if all_classes:
                lines.append("## Classes\n")
                for cls in sorted(all_classes, key=lambda c: c.name):
                    summary_text = f" - {cls.summary}" if cls.summary else ""
                    lines.append(f"- [[{cls.name}]]{summary_text}")
                lines.append("")

            if all_functions:
                lines.append("## Functions\n")
                for func in sorted(all_functions, key=lambda f: f.name):
                    lines.append(f"- `{func.name}()`")
                lines.append("")

            if all_endpoints:
                lines.append("## Endpoints\n")
                lines.append("| Method | Path | Handler |")
                lines.append("|--------|------|---------|")
                for ep in sorted(all_endpoints, key=lambda e: e.path):
                    badge = self._get_method_badge(ep.http_method)
                    lines.append(
                        f"| {badge} | `{ep.path}` | [[{ep.handler_class}#{ep.handler_method}]] |"
                    )
                lines.append("")

            lines.append("## Files\n")
            for fs in sorted(file_list, key=lambda f: str(f.file.relative_path)):
                stem = fs.file.relative_path.stem
                lines.append(f"- [[{stem}]] (`{fs.file.relative_path}`)")
            lines.append("")

            safe_name = pkg.replace(".", "/").replace(" ", "_")
            if self.config.mirror_source_structure:
                moc_dir = self.output_dir / safe_name
            else:
                moc_dir = self.output_dir
            moc_dir.mkdir(parents=True, exist_ok=True)

            moc_filename = f"_MOC_{pkg.split('.')[-1]}.md"
            moc_path = moc_dir / moc_filename

            with open(moc_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            moc_paths.append(moc_path)
            logger.debug(f"Generated MOC: {moc_path}")

        return moc_paths

    def _format_annotation(self, ann: Annotation) -> str:
        """Format an annotation for display."""
        if ann.arguments:
            args = ", ".join(f'{k}="{v}"' for k, v in ann.arguments.items())
            return f"`@{ann.name}({args})`"
        return f"`@{ann.name}`"

    def _get_import_link(self, module: str) -> str:
        """Get a link for an import statement."""
        class_name = module.split(".")[-1]
        if class_name == "*":
            return f"`{module}`"

        if module in self.symbol_table.class_index:
            return f"[[{class_name}]] (`{module}`)"

        for fqn in self.symbol_table.class_index:
            if fqn.endswith(f".{class_name}"):
                return f"[[{class_name}]] (`{module}`)"

        return f"`{module}`"

    def _get_method_badge(self, method: str) -> str:
        """Get a colored badge for HTTP method."""
        badges = {
            "GET": "🟢 `GET`",
            "POST": "🟡 `POST`",
            "PUT": "🔵 `PUT`",
            "DELETE": "🔴 `DELETE`",
            "PATCH": "🟣 `PATCH`",
        }
        return badges.get(method, f"`{method}`")

    def _truncate_source(self, source: str) -> str:
        """Truncate source code to max lines."""
        lines = source.split("\n")
        if len(lines) <= self.config.max_snippet_lines:
            return source
        return "\n".join(lines[: self.config.max_snippet_lines]) + "\n// ... truncated"
