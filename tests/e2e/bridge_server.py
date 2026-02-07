"""Lightweight HTTP bridge server that exposes docmaker IPC methods without Qt/PySide6.

Playwright tests inject a fake window.ipc that fetches from this server,
so the frontend runs unmodified against real parsing logic.

Usage:
    python tests/e2e/bridge_server.py [port]
"""

import json
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from docmaker.app.graph_builder import GraphBuilder
from docmaker.app.settings import (
    load_settings,
    reset_settings,
    save_settings,
)
from docmaker.config import DocmakerConfig
from docmaker.crawler import FileCrawler
from docmaker.models import FileCategory, SourceFile, SymbolTable
from docmaker.parser.registry import get_parser_registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class BridgeState:
    """Shared mutable state across requests (mirrors DocmakerAPI instance vars)."""

    def __init__(self) -> None:
        self.current_project: Path | None = None
        self.symbol_table: SymbolTable | None = None
        self.config: DocmakerConfig | None = None
        self.files: list[SourceFile] = []
        self.graph_dict: dict[str, Any] | None = None


state = BridgeState()


# ---------- IPC method implementations ----------


def ipc_parse_only(path: str) -> str:
    project_path = Path(path).resolve()
    if not project_path.exists():
        return json.dumps({"error": f"Path does not exist: {path}"})

    state.current_project = project_path
    state.config = DocmakerConfig.load(None)
    state.config.source_dir = project_path
    state.config.llm.enabled = False

    crawler = FileCrawler(state.config)
    state.files = crawler.crawl()

    relevant_files = [
        f for f in state.files if f.category not in (FileCategory.IGNORE, FileCategory.TEST)
    ]

    parser_registry = get_parser_registry()
    state.symbol_table = SymbolTable()

    for file in relevant_files:
        if parser_registry.can_parse(file):
            symbols = parser_registry.parse(file)
            if symbols:
                state.symbol_table.add_file_symbols(symbols)

    builder = GraphBuilder(state.symbol_table)
    graph = builder.build()
    state.graph_dict = graph.to_dict()

    logger.info(
        "Parse complete: %d scanned, %d parsed, %d classes, %d endpoints",
        len(state.files),
        len(state.symbol_table.files),
        len(state.symbol_table.class_index),
        len(state.symbol_table.endpoint_index),
    )

    return json.dumps({
        "success": True,
        "stats": {
            "filesScanned": len(state.files),
            "filesParsed": len(state.symbol_table.files),
            "classesFound": len(state.symbol_table.class_index),
            "endpointsFound": len(state.symbol_table.endpoint_index),
        },
        "graph": state.graph_dict,
    })


def ipc_get_graph_data() -> str:
    if not state.symbol_table:
        return json.dumps({"error": "No symbol table available. Run parse_only first."})

    if state.graph_dict:
        return json.dumps(state.graph_dict)

    builder = GraphBuilder(state.symbol_table)
    graph = builder.build()
    state.graph_dict = graph.to_dict()
    return json.dumps(state.graph_dict)


def ipc_get_class_details(class_fqn: str) -> str:
    if not state.symbol_table:
        return json.dumps({"error": "No symbol table available"})

    cls = state.symbol_table.class_index.get(class_fqn)
    if not cls:
        for fqn, class_def in state.symbol_table.class_index.items():
            if class_def.name == class_fqn or fqn.endswith(f".{class_fqn}"):
                cls = class_def
                class_fqn = fqn
                break
    if not cls:
        return json.dumps({"error": f"Class not found: {class_fqn}"})

    return json.dumps({
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
    })


def ipc_get_endpoint_details(endpoint_key: str) -> str:
    if not state.symbol_table:
        return json.dumps({"error": "No symbol table available"})

    endpoint = state.symbol_table.endpoint_index.get(endpoint_key)
    if not endpoint:
        return json.dumps({"error": f"Endpoint not found: {endpoint_key}"})

    return json.dumps({
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
    })


def ipc_get_project_info() -> str:
    if not state.current_project:
        return json.dumps({"loaded": False})

    return json.dumps({
        "loaded": True,
        "path": str(state.current_project),
        "name": state.current_project.name,
        "hasSymbolTable": state.symbol_table is not None,
        "stats": {
            "files": len(state.files),
            "classes": len(state.symbol_table.class_index) if state.symbol_table else 0,
            "endpoints": len(state.symbol_table.endpoint_index) if state.symbol_table else 0,
        }
        if state.symbol_table
        else None,
    })


def ipc_get_settings() -> str:
    try:
        settings = load_settings()
        return json.dumps(settings)
    except Exception as e:
        return json.dumps({"error": str(e)})


def ipc_save_settings_ipc(settings_json: str) -> str:
    try:
        settings = json.loads(settings_json)
        save_settings(settings)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


def ipc_reset_settings_ipc() -> str:
    try:
        defaults = reset_settings()
        return json.dumps(defaults)
    except Exception as e:
        return json.dumps({"error": str(e)})


# No-op stubs for GUI-only methods
def ipc_select_folder() -> str:
    return json.dumps({"path": None})


def ipc_open_file(path: str, line: int = 0) -> str:
    return json.dumps({"success": True, "editor": "stub"})


def ipc_resize_window(width: int = 1280, height: int = 720) -> str:
    return json.dumps({"success": True, "width": width, "height": height})


def ipc_get_window_size() -> str:
    return json.dumps({"width": 1280, "height": 720})


# ---------- Dispatch table ----------

METHODS: dict[str, Any] = {
    "parse_only": ipc_parse_only,
    "get_graph_data": ipc_get_graph_data,
    "get_class_details": ipc_get_class_details,
    "get_endpoint_details": ipc_get_endpoint_details,
    "get_project_info": ipc_get_project_info,
    "get_settings": ipc_get_settings,
    "save_settings_ipc": ipc_save_settings_ipc,
    "reset_settings_ipc": ipc_reset_settings_ipc,
    "select_folder": ipc_select_folder,
    "open_file": ipc_open_file,
    "resize_window": ipc_resize_window,
    "get_window_size": ipc_get_window_size,
}


# ---------- HTTP handler ----------


class BridgeHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_POST(self) -> None:
        # Expected path: /ipc/<method_name>
        parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "ipc":
            self.send_response(404)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')
            return

        method_name = parts[1]
        handler = METHODS.get(method_name)
        if not handler:
            self.send_response(404)
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Unknown method: {method_name}"}).encode())
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        args = payload.get("args", [])

        try:
            result = handler(*args)
        except Exception as e:
            logger.exception("Error in %s", method_name)
            result = json.dumps({"error": str(e)})

        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(result.encode("utf-8"))

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(format, *args)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"Bridge server ready on port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
