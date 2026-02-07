"""Build graph data structures from SymbolTable for visualization."""

from dataclasses import dataclass, field

from docmaker.models import ClassDef, EndpointDef, FileSymbols, SymbolTable


@dataclass
class GraphNode:
    """Represents a node in the code graph."""

    id: str
    label: str
    type: str  # class, interface, file, package, endpoint
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "metadata": self.metadata,
        }


@dataclass
class GraphEdge:
    """Represents an edge in the code graph."""

    source: str
    target: str
    type: str  # extends, implements, imports, calls, contains

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
        }


@dataclass
class CodeGraph:
    """Complete code graph with nodes and edges."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)


class GraphBuilder:
    """Builds a CodeGraph from a SymbolTable."""

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self._node_ids: set[str] = set()
        self._package_nodes: set[str] = set()

    def build(self) -> CodeGraph:
        """Build the complete code graph from the symbol table."""
        graph = CodeGraph()

        # First pass: create all nodes
        for file_path, file_symbols in self.symbol_table.files.items():
            self._add_file_nodes(graph, file_symbols)

        # Second pass: create edges
        for file_path, file_symbols in self.symbol_table.files.items():
            self._add_file_edges(graph, file_symbols)

        return graph

    def _add_file_nodes(self, graph: CodeGraph, file_symbols: FileSymbols) -> None:
        """Add nodes from a single file."""
        # Add package node if not already added
        if file_symbols.package and file_symbols.package not in self._package_nodes:
            self._package_nodes.add(file_symbols.package)
            graph.add_node(
                GraphNode(
                    id=f"pkg:{file_symbols.package}",
                    label=file_symbols.package,
                    type="package",
                    metadata={"fqn": file_symbols.package},
                )
            )

        # Add file node
        file_id = f"file:{file_symbols.file.relative_path}"
        if file_id not in self._node_ids:
            self._node_ids.add(file_id)
            graph.add_node(
                GraphNode(
                    id=file_id,
                    label=file_symbols.file.relative_path.name,
                    type="file",
                    metadata={
                        "path": str(file_symbols.file.path),
                        "relativePath": str(file_symbols.file.relative_path),
                        "language": file_symbols.file.language.value,
                        "category": file_symbols.file.category.value,
                    },
                )
            )

        # Add class nodes
        for cls in file_symbols.classes:
            self._add_class_node(graph, cls, file_symbols)

        # Add endpoint nodes
        for endpoint in file_symbols.endpoints:
            self._add_endpoint_node(graph, endpoint, file_symbols)

    def _add_class_node(self, graph: CodeGraph, cls: ClassDef, file_symbols: FileSymbols) -> None:
        """Add a class or interface node."""
        fqn = f"{file_symbols.package}.{cls.name}" if file_symbols.package else cls.name
        node_id = f"class:{fqn}"

        if node_id in self._node_ids:
            return

        self._node_ids.add(node_id)

        # Determine if this is an interface
        is_interface = "interface" in cls.modifiers

        graph.add_node(
            GraphNode(
                id=node_id,
                label=cls.name,
                type="interface" if is_interface else "class",
                metadata={
                    "fqn": fqn,
                    "path": str(cls.file_path),
                    "line": cls.line_number,
                    "endLine": cls.end_line,
                    "package": file_symbols.package or "",
                    "modifiers": cls.modifiers,
                    "superclass": cls.superclass,
                    "interfaces": cls.interfaces,
                    "methodCount": len(cls.methods),
                    "fieldCount": len(cls.fields),
                    "category": file_symbols.file.category.value,
                },
            )
        )

    def _add_endpoint_node(
        self, graph: CodeGraph, endpoint: EndpointDef, file_symbols: FileSymbols
    ) -> None:
        """Add an endpoint node."""
        node_id = f"endpoint:{endpoint.http_method}:{endpoint.path}"

        if node_id in self._node_ids:
            return

        self._node_ids.add(node_id)

        graph.add_node(
            GraphNode(
                id=node_id,
                label=f"{endpoint.http_method} {endpoint.path}",
                type="endpoint",
                metadata={
                    "method": endpoint.http_method,
                    "path": endpoint.path,
                    "handler": f"{endpoint.handler_class}.{endpoint.handler_method}",
                    "filePath": str(endpoint.file_path),
                    "line": endpoint.line_number,
                    "category": file_symbols.file.category.value,
                },
            )
        )

    def _add_file_edges(self, graph: CodeGraph, file_symbols: FileSymbols) -> None:
        """Add edges for relationships in a file."""
        file_id = f"file:{file_symbols.file.relative_path}"

        # File contains classes
        for cls in file_symbols.classes:
            fqn = f"{file_symbols.package}.{cls.name}" if file_symbols.package else cls.name
            class_id = f"class:{fqn}"
            graph.add_edge(GraphEdge(source=file_id, target=class_id, type="contains"))

            # Package contains class
            if file_symbols.package:
                pkg_id = f"pkg:{file_symbols.package}"
                graph.add_edge(GraphEdge(source=pkg_id, target=class_id, type="contains"))

            # Class extends superclass
            if cls.superclass:
                superclass_id = self._resolve_class_id(cls.superclass, file_symbols)
                if superclass_id:
                    graph.add_edge(GraphEdge(source=class_id, target=superclass_id, type="extends"))

            # Class implements interfaces
            for interface in cls.interfaces:
                interface_id = self._resolve_class_id(interface, file_symbols)
                if interface_id:
                    graph.add_edge(
                        GraphEdge(source=class_id, target=interface_id, type="implements")
                    )

        # Add calls edges from constructor instantiations
        for cls in file_symbols.classes:
            fqn = f"{file_symbols.package}.{cls.name}" if file_symbols.package else cls.name
            class_id = f"class:{fqn}"
            for method in cls.methods:
                for callee in method.calls:
                    target_id = self._resolve_class_id(callee, file_symbols)
                    if target_id:
                        graph.add_edge(
                            GraphEdge(source=class_id, target=target_id, type="calls")
                        )

        # Add import edges
        for imp in file_symbols.imports:
            if not imp.is_wildcard:
                target_id = f"class:{imp.module}"
                if target_id in self._node_ids or self._class_exists(imp.module):
                    for cls in file_symbols.classes:
                        fqn = (
                            f"{file_symbols.package}.{cls.name}"
                            if file_symbols.package
                            else cls.name
                        )
                        class_id = f"class:{fqn}"
                        graph.add_edge(GraphEdge(source=class_id, target=target_id, type="imports"))

        # Endpoint handled by class
        for endpoint in file_symbols.endpoints:
            endpoint_id = f"endpoint:{endpoint.http_method}:{endpoint.path}"
            handler_fqn = (
                f"{file_symbols.package}.{endpoint.handler_class}"
                if file_symbols.package
                else endpoint.handler_class
            )
            handler_id = f"class:{handler_fqn}"
            if handler_id in self._node_ids:
                graph.add_edge(GraphEdge(source=handler_id, target=endpoint_id, type="contains"))

    def _resolve_class_id(self, class_name: str, file_symbols: FileSymbols) -> str | None:
        """Resolve a class name to its node ID using imports."""
        # Check if it's already a fully qualified name
        if f"class:{class_name}" in self._node_ids:
            return f"class:{class_name}"

        # Check imports for the class
        for imp in file_symbols.imports:
            if imp.module.endswith(f".{class_name}"):
                if f"class:{imp.module}" in self._node_ids:
                    return f"class:{imp.module}"

        # Check same package
        if file_symbols.package:
            same_pkg_fqn = f"{file_symbols.package}.{class_name}"
            if f"class:{same_pkg_fqn}" in self._node_ids:
                return f"class:{same_pkg_fqn}"

        # Return unresolved ID (will create edge even if target doesn't exist in our graph)
        return f"class:{class_name}"

    def _class_exists(self, fqn: str) -> bool:
        """Check if a class exists in the symbol table."""
        return fqn in self.symbol_table.class_index
