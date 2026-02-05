"""Tests for the graph builder module."""

from pathlib import Path

import pytest

from docmaker.app.graph_builder import CodeGraph, GraphBuilder, GraphEdge, GraphNode
from docmaker.models import (
    Annotation,
    ClassDef,
    EndpointDef,
    FileCategory,
    FileSymbols,
    FunctionDef,
    ImportDef,
    Language,
    SourceFile,
    SymbolTable,
)


@pytest.fixture
def sample_symbol_table() -> SymbolTable:
    """Create a sample symbol table for testing."""
    symbol_table = SymbolTable()

    # Create a controller class
    controller_file = SourceFile(
        path=Path("/test/UserController.java"),
        relative_path=Path("src/main/java/com/example/UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    controller_class = ClassDef(
        name="UserController",
        file_path=Path("/test/UserController.java"),
        line_number=10,
        end_line=50,
        package="com.example",
        superclass=None,
        interfaces=["Controller"],
        annotations=[Annotation(name="RestController")],
        methods=[
            FunctionDef(
                name="getUsers",
                file_path=Path("/test/UserController.java"),
                line_number=15,
                end_line=20,
            ),
            FunctionDef(
                name="createUser",
                file_path=Path("/test/UserController.java"),
                line_number=25,
                end_line=35,
            ),
        ],
    )

    controller_endpoint = EndpointDef(
        http_method="GET",
        path="/users",
        handler_method="getUsers",
        handler_class="UserController",
        file_path=Path("/test/UserController.java"),
        line_number=15,
    )

    controller_symbols = FileSymbols(
        file=controller_file,
        package="com.example",
        imports=[
            ImportDef(module="com.example.service.UserService"),
        ],
        classes=[controller_class],
        endpoints=[controller_endpoint],
    )

    # Create a service class
    service_file = SourceFile(
        path=Path("/test/UserService.java"),
        relative_path=Path("src/main/java/com/example/service/UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    service_class = ClassDef(
        name="UserService",
        file_path=Path("/test/UserService.java"),
        line_number=5,
        end_line=30,
        package="com.example.service",
        superclass="BaseService",
        interfaces=[],
    )

    service_symbols = FileSymbols(
        file=service_file,
        package="com.example.service",
        classes=[service_class],
    )

    symbol_table.add_file_symbols(controller_symbols)
    symbol_table.add_file_symbols(service_symbols)

    return symbol_table


def test_graph_builder_creates_nodes(sample_symbol_table: SymbolTable):
    """Test that the graph builder creates nodes for classes, files, and packages."""
    builder = GraphBuilder(sample_symbol_table)
    graph = builder.build()

    # Should have package nodes
    package_nodes = [n for n in graph.nodes if n.type == "package"]
    assert len(package_nodes) == 2  # com.example and com.example.service

    # Should have file nodes
    file_nodes = [n for n in graph.nodes if n.type == "file"]
    assert len(file_nodes) == 2

    # Should have class nodes
    class_nodes = [n for n in graph.nodes if n.type == "class"]
    assert len(class_nodes) == 2

    # Should have endpoint node
    endpoint_nodes = [n for n in graph.nodes if n.type == "endpoint"]
    assert len(endpoint_nodes) == 1


def test_graph_builder_creates_edges(sample_symbol_table: SymbolTable):
    """Test that the graph builder creates edges for relationships."""
    builder = GraphBuilder(sample_symbol_table)
    graph = builder.build()

    # Should have contains edges (file->class, package->class)
    contains_edges = [e for e in graph.edges if e.type == "contains"]
    assert len(contains_edges) >= 4  # At least file->class and package->class for each

    # Should have extends edge (UserService extends BaseService)
    extends_edges = [e for e in graph.edges if e.type == "extends"]
    assert len(extends_edges) == 1
    assert extends_edges[0].source == "class:com.example.service.UserService"
    assert extends_edges[0].target == "class:BaseService"

    # Should have implements edge (UserController implements Controller)
    implements_edges = [e for e in graph.edges if e.type == "implements"]
    assert len(implements_edges) == 1
    assert implements_edges[0].source == "class:com.example.UserController"


def test_graph_serialization(sample_symbol_table: SymbolTable):
    """Test that the graph can be serialized to dict."""
    builder = GraphBuilder(sample_symbol_table)
    graph = builder.build()

    data = graph.to_dict()

    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)

    # Check node structure
    for node in data["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "type" in node
        assert "metadata" in node


def test_graph_node_metadata(sample_symbol_table: SymbolTable):
    """Test that nodes have appropriate metadata."""
    builder = GraphBuilder(sample_symbol_table)
    graph = builder.build()

    # Find the UserController class node
    controller_node = next(
        n for n in graph.nodes if n.id == "class:com.example.UserController"
    )

    assert controller_node.metadata["fqn"] == "com.example.UserController"
    assert controller_node.metadata["line"] == 10
    assert controller_node.metadata["methodCount"] == 2


def test_empty_symbol_table():
    """Test that empty symbol table produces empty graph."""
    symbol_table = SymbolTable()
    builder = GraphBuilder(symbol_table)
    graph = builder.build()

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
