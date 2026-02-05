"""IPC bridges for communication between Python backend and frontend."""

import json
import logging
import subprocess
import sys
from pathlib import Path

from pyloid.ipc import Bridge, PyloidIPC
from PySide6.QtWidgets import QFileDialog

from docmaker.app.graph_builder import GraphBuilder
from docmaker.app.settings import (
    get_editor_command,
    load_settings,
    reset_settings,
    save_settings,
)
from docmaker.config import DocmakerConfig
from docmaker.crawler import FileCrawler
from docmaker.models import FileCategory, SourceFile, SymbolTable
from docmaker.parser.registry import get_parser_registry
from docmaker.pipeline import Pipeline

logger = logging.getLogger(__name__)


class DocmakerAPI(PyloidIPC):
    """API exposed to the frontend via IPC bridges."""

    def __init__(self):
        super().__init__()
        self._current_project: Path | None = None
        self._symbol_table: SymbolTable | None = None
        self._config: DocmakerConfig | None = None
        self._files: list[SourceFile] = []

    @Bridge(result=str)
    def select_folder(self) -> str:
        """Open a native folder picker dialog.

        Returns:
            JSON string with selected path or null if cancelled
        """
        logger.debug("select_folder called")
        try:
            selected = QFileDialog.getExistingDirectory(
                None,
                "Select Project Folder",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
            if selected:
                logger.info("Folder selected: %s", selected)
                return json.dumps({"path": selected})
            logger.debug("Folder selection cancelled")
            return json.dumps({"path": None})
        except Exception as e:
            logger.exception("Error opening folder dialog")
            return json.dumps({"error": str(e)})

    @Bridge(str, result=str)
    def scan_project(self, path: str) -> str:
        """Scan a project directory and return file statistics.

        Args:
            path: Path to the project directory

        Returns:
            JSON string with file list and statistics
        """
        logger.info("scan_project called with path: %s", path)
        try:
            project_path = Path(path).resolve()
            if not project_path.exists():
                logger.error("Path does not exist: %s", path)
                return json.dumps({"error": f"Path does not exist: {path}"})

            if not project_path.is_dir():
                logger.error("Path is not a directory: %s", path)
                return json.dumps({"error": f"Path is not a directory: {path}"})

            self._current_project = project_path
            self._config = DocmakerConfig.load(None)
            self._config.source_dir = project_path
            self._config.llm.enabled = False

            crawler = FileCrawler(self._config)
            self._files = crawler.crawl()

            # Build statistics
            by_language: dict[str, int] = {}
            by_category: dict[str, int] = {}

            file_list = []
            for f in self._files:
                lang = f.language.value
                cat = f.category.value
                by_language[lang] = by_language.get(lang, 0) + 1
                by_category[cat] = by_category.get(cat, 0) + 1

                file_list.append(
                    {
                        "path": str(f.relative_path),
                        "language": lang,
                        "category": cat,
                        "size": f.size_bytes,
                    }
                )

            logger.info(
                "Scan complete: %d files found (%s)",
                len(self._files),
                ", ".join(f"{k}:{v}" for k, v in by_language.items()),
            )

            return json.dumps(
                {
                    "projectPath": str(project_path),
                    "files": file_list,
                    "stats": {
                        "totalFiles": len(self._files),
                        "byLanguage": by_language,
                        "byCategory": by_category,
                    },
                }
            )

        except Exception as e:
            logger.exception("Error scanning project")
            return json.dumps({"error": str(e)})

    @Bridge(str, result=str)
    def generate_docs(self, options_json: str) -> str:
        """Run the documentation generation pipeline.

        Args:
            options_json: JSON string with generation options
                - incremental: bool (default False)
                - useLlm: bool (default False)

        Returns:
            JSON string with generation results
        """
        logger.info("generate_docs called with options: %s", options_json)
        try:
            options = json.loads(options_json)
            incremental = options.get("incremental", False)
            use_llm = options.get("useLlm", False)

            if not self._current_project or not self._config:
                logger.error("No project loaded")
                return json.dumps({"error": "No project loaded. Call scan_project first."})

            self._config.llm.enabled = use_llm

            # Create a simple console that doesn't print anything
            from io import StringIO

            from rich.console import Console

            console = Console(file=StringIO(), force_terminal=False)

            pipeline = Pipeline(self._config, console)
            generated = pipeline.run(incremental=incremental)

            # Store the symbol table for graph building
            self._symbol_table = pipeline.symbol_table

            logger.info(
                "Documentation generated: %d files, %d classes, %d endpoints",
                len(pipeline.symbol_table.files),
                len(pipeline.symbol_table.class_index),
                len(pipeline.symbol_table.endpoint_index),
            )

            return json.dumps(
                {
                    "success": True,
                    "generatedFiles": [str(p) for p in generated],
                    "stats": {
                        "filesProcessed": len(pipeline.symbol_table.files),
                        "classesFound": len(pipeline.symbol_table.class_index),
                        "endpointsFound": len(pipeline.symbol_table.endpoint_index),
                    },
                }
            )

        except Exception as e:
            logger.exception("Error generating docs")
            return json.dumps({"error": str(e)})

    @Bridge(result=str)
    def get_graph_data(self) -> str:
        """Get the code graph data for visualization.

        Returns:
            JSON string with nodes and edges for the graph
        """
        try:
            if not self._symbol_table:
                return json.dumps({"error": "No symbol table available. Run generate_docs first."})

            builder = GraphBuilder(self._symbol_table)
            graph = builder.build()

            return json.dumps(graph.to_dict())

        except Exception as e:
            logger.exception("Error building graph")
            return json.dumps({"error": str(e)})

    @Bridge(str, result=str)
    def parse_only(self, path: str) -> str:
        """Parse files without generating docs, for quick graph preview.

        Args:
            path: Path to the project directory

        Returns:
            JSON string with parsing results and graph data
        """
        logger.info("parse_only called with path: %s", path)
        try:
            project_path = Path(path).resolve()
            if not project_path.exists():
                logger.error("Path does not exist: %s", path)
                return json.dumps({"error": f"Path does not exist: {path}"})

            self._current_project = project_path
            self._config = DocmakerConfig.load(None)
            self._config.source_dir = project_path
            self._config.llm.enabled = False

            # Crawl files
            crawler = FileCrawler(self._config)
            self._files = crawler.crawl()

            # Filter to parseable files
            relevant_files = [
                f for f in self._files if f.category not in (FileCategory.IGNORE, FileCategory.TEST)
            ]

            # Parse files
            logger.debug("Parsing %d relevant files", len(relevant_files))
            parser_registry = get_parser_registry()
            self._symbol_table = SymbolTable()

            for file in relevant_files:
                if parser_registry.can_parse(file):
                    logger.debug("Parsing file: %s", file.relative_path)
                    symbols = parser_registry.parse(file)
                    if symbols:
                        self._symbol_table.add_file_symbols(symbols)

            # Build graph
            logger.debug("Building graph from symbol table")
            builder = GraphBuilder(self._symbol_table)
            graph = builder.build()

            logger.info(
                "Parse complete: %d files scanned, %d parsed, %d classes, %d endpoints",
                len(self._files),
                len(self._symbol_table.files),
                len(self._symbol_table.class_index),
                len(self._symbol_table.endpoint_index),
            )

            return json.dumps(
                {
                    "success": True,
                    "stats": {
                        "filesScanned": len(self._files),
                        "filesParsed": len(self._symbol_table.files),
                        "classesFound": len(self._symbol_table.class_index),
                        "endpointsFound": len(self._symbol_table.endpoint_index),
                    },
                    "graph": graph.to_dict(),
                }
            )

        except Exception as e:
            logger.exception("Error parsing project")
            return json.dumps({"error": str(e)})

    @Bridge(str, int, result=str)
    def open_file(self, path: str, line: int) -> str:
        """Open a file in the configured editor.

        Args:
            path: Path to the file
            line: Line number to jump to (0 for beginning)

        Returns:
            JSON string with success status and editor used
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                return json.dumps({"error": f"File does not exist: {path}"})

            settings = load_settings()
            cmd_template, editor_type = get_editor_command(settings)

            # If alwaysAsk is true, signal frontend to show picker
            if editor_type == "ask":
                return json.dumps({"success": False, "askUser": True})

            # Handle auto-detect: try VS Code first, then system default
            if editor_type == "auto":
                try:
                    if line > 0:
                        subprocess.Popen(["code", "--goto", f"{path}:{line}"])
                    else:
                        subprocess.Popen(["code", path])
                    return json.dumps({"success": True, "editor": "vscode"})
                except FileNotFoundError:
                    # Fall through to system default
                    editor_type = "system"

            # Handle custom command with placeholders
            if cmd_template and editor_type == "custom":
                cmd = []
                for part in cmd_template:
                    part = part.replace("{file}", path)
                    part = part.replace("{line}", str(line if line > 0 else 1))
                    cmd.append(part)
                try:
                    subprocess.Popen(cmd)
                    return json.dumps({"success": True, "editor": "custom"})
                except FileNotFoundError:
                    logger.warning("Custom editor command not found: %s", cmd[0])
                    editor_type = "system"

            # Handle specific editors
            if editor_type == "vscode":
                try:
                    if line > 0:
                        subprocess.Popen(["code", "--goto", f"{path}:{line}"])
                    else:
                        subprocess.Popen(["code", path])
                    return json.dumps({"success": True, "editor": "vscode"})
                except FileNotFoundError:
                    logger.warning("VS Code not found, falling back to system")
                    editor_type = "system"

            elif editor_type == "idea":
                try:
                    if line > 0:
                        subprocess.Popen(["idea", "--line", str(line), path])
                    else:
                        subprocess.Popen(["idea", path])
                    return json.dumps({"success": True, "editor": "idea"})
                except FileNotFoundError:
                    logger.warning("IntelliJ IDEA not found, falling back to system")
                    editor_type = "system"

            elif editor_type == "sublime":
                try:
                    if line > 0:
                        subprocess.Popen(["subl", f"{path}:{line}"])
                    else:
                        subprocess.Popen(["subl", path])
                    return json.dumps({"success": True, "editor": "sublime"})
                except FileNotFoundError:
                    logger.warning("Sublime Text not found, falling back to system")
                    editor_type = "system"

            # System default fallback
            if sys.platform == "win32":
                import os

                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

            return json.dumps({"success": True, "editor": "system"})

        except Exception as e:
            logger.exception("Error opening file")
            return json.dumps({"error": str(e)})

    @Bridge(result=str)
    def get_project_info(self) -> str:
        """Get information about the currently loaded project.

        Returns:
            JSON string with project information
        """
        if not self._current_project:
            return json.dumps({"loaded": False})

        return json.dumps(
            {
                "loaded": True,
                "path": str(self._current_project),
                "name": self._current_project.name,
                "hasSymbolTable": self._symbol_table is not None,
                "stats": {
                    "files": len(self._files),
                    "classes": len(self._symbol_table.class_index) if self._symbol_table else 0,
                    "endpoints": len(self._symbol_table.endpoint_index)
                    if self._symbol_table
                    else 0,
                }
                if self._symbol_table
                else None,
            }
        )

    @Bridge(str, result=str)
    def get_class_details(self, class_fqn: str) -> str:
        """Get detailed information about a class.

        Args:
            class_fqn: Fully qualified name of the class

        Returns:
            JSON string with class details
        """
        try:
            if not self._symbol_table:
                return json.dumps({"error": "No symbol table available"})

            cls = self._symbol_table.class_index.get(class_fqn)
            if not cls:
                for fqn, class_def in self._symbol_table.class_index.items():
                    if class_def.name == class_fqn or fqn.endswith(f".{class_fqn}"):
                        cls = class_def
                        class_fqn = fqn
                        break
            if not cls:
                return json.dumps({"error": f"Class not found: {class_fqn}"})

            return json.dumps(
                {
                    "name": cls.name,
                    "fqn": class_fqn,
                    "path": str(cls.file_path),
                    "line": cls.line_number,
                    "endLine": cls.end_line,
                    "superclass": cls.superclass,
                    "interfaces": cls.interfaces,
                    "modifiers": cls.modifiers,
                    "docstring": cls.docstring,
                    "methods": [
                        {
                            "name": m.name,
                            "returnType": m.return_type,
                            "parameters": [{"name": p.name, "type": p.type} for p in m.parameters],
                            "modifiers": m.modifiers,
                            "line": m.line_number,
                        }
                        for m in cls.methods
                    ],
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.type,
                            "modifiers": f.modifiers,
                            "line": f.line_number,
                        }
                        for f in cls.fields
                    ],
                }
            )

        except Exception as e:
            logger.exception("Error getting class details")
            return json.dumps({"error": str(e)})

    @Bridge(str, result=str)
    def get_endpoint_details(self, endpoint_key: str) -> str:
        """Get detailed information about an endpoint.

        Args:
            endpoint_key: Endpoint key in format "METHOD:path"

        Returns:
            JSON string with endpoint details
        """
        try:
            if not self._symbol_table:
                return json.dumps({"error": "No symbol table available"})

            endpoint = self._symbol_table.endpoint_index.get(endpoint_key)
            if not endpoint:
                return json.dumps({"error": f"Endpoint not found: {endpoint_key}"})

            return json.dumps(
                {
                    "httpMethod": endpoint.http_method,
                    "path": endpoint.path,
                    "handlerClass": endpoint.handler_class,
                    "handlerMethod": endpoint.handler_method,
                    "filePath": str(endpoint.file_path),
                    "line": endpoint.line_number,
                    "parameters": [
                        {"name": p.name, "type": p.type, "description": p.description}
                        for p in endpoint.parameters
                    ],
                    "requestBody": endpoint.request_body,
                    "responseType": endpoint.response_type,
                    "description": endpoint.description,
                }
            )

        except Exception as e:
            logger.exception("Error getting endpoint details")
            return json.dumps({"error": str(e)})

    @Bridge(result=str)
    def get_settings(self) -> str:
        """Load and return all settings as JSON.

        Returns:
            JSON string with current settings
        """
        try:
            settings = load_settings()
            return json.dumps(settings)
        except Exception as e:
            logger.exception("Error loading settings")
            return json.dumps({"error": str(e)})

    @Bridge(str, result=str)
    def save_settings_ipc(self, settings_json: str) -> str:
        """Save settings from JSON string.

        Args:
            settings_json: JSON string with settings to save

        Returns:
            JSON string with success status
        """
        try:
            settings = json.loads(settings_json)
            save_settings(settings)
            return json.dumps({"success": True})
        except Exception as e:
            logger.exception("Error saving settings")
            return json.dumps({"error": str(e)})

    @Bridge(result=str)
    def reset_settings_ipc(self) -> str:
        """Reset all settings to defaults.

        Returns:
            JSON string with default settings
        """
        try:
            defaults = reset_settings()
            return json.dumps(defaults)
        except Exception as e:
            logger.exception("Error resetting settings")
            return json.dumps({"error": str(e)})

    @Bridge(int, int, result=str)
    def resize_window(self, width: int, height: int) -> str:
        """Resize the application window.

        Args:
            width: New window width in pixels
            height: New window height in pixels

        Returns:
            JSON string with success status
        """
        try:
            # Access the window through the app singleton
            from docmaker.app.main import get_app_window

            window = get_app_window()
            if window:
                window.resize(width, height)
                logger.info("Window resized to %dx%d", width, height)
                return json.dumps({"success": True, "width": width, "height": height})
            else:
                return json.dumps({"error": "Window not available"})
        except Exception as e:
            logger.exception("Error resizing window")
            return json.dumps({"error": str(e)})

    @Bridge(result=str)
    def get_window_size(self) -> str:
        """Get the current window size.

        Returns:
            JSON string with width and height
        """
        try:
            from docmaker.app.main import get_app_window

            window = get_app_window()
            if window:
                size = window.size()
                return json.dumps({"width": size.width(), "height": size.height()})
            else:
                return json.dumps({"error": "Window not available"})
        except Exception as e:
            logger.exception("Error getting window size")
            return json.dumps({"error": str(e)})
