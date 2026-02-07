"""Tests for the Java parser."""

import tempfile
from pathlib import Path

import pytest

from docmaker.models import Language, SourceFile, FileCategory
from docmaker.parser.java_parser import JavaParser


@pytest.fixture
def java_parser():
    """Create a Java parser instance."""
    return JavaParser()


@pytest.fixture
def sample_controller():
    """Create a sample Spring controller file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example.controller;

import org.springframework.web.bind.annotation.*;
import com.example.model.User;
import com.example.service.UserService;

/**
 * Controller for user operations.
 */
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * Get a user by ID.
     */
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
""")
        f.flush()
        yield Path(f.name)


def test_parser_extracts_package(java_parser, sample_controller):
    """Test that the parser extracts the package declaration."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    assert symbols.package == "com.example.controller"


def test_parser_extracts_imports(java_parser, sample_controller):
    """Test that the parser extracts import statements."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    import_modules = [i.module for i in symbols.imports]
    assert any("springframework" in m for m in import_modules)


def test_parser_extracts_class(java_parser, sample_controller):
    """Test that the parser extracts class definitions."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    assert len(symbols.classes) == 1
    cls = symbols.classes[0]
    assert cls.name == "UserController"


def test_parser_extracts_annotations(java_parser, sample_controller):
    """Test that the parser extracts class annotations."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    ann_names = [a.name for a in cls.annotations]
    assert "RestController" in ann_names
    assert "RequestMapping" in ann_names


def test_parser_extracts_methods(java_parser, sample_controller):
    """Test that the parser extracts method definitions."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    method_names = [m.name for m in cls.methods]
    assert "getUser" in method_names
    assert "createUser" in method_names
    assert "deleteUser" in method_names


def test_parser_extracts_endpoints(java_parser, sample_controller):
    """Test that the parser extracts REST endpoints."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    assert len(symbols.endpoints) == 3

    methods = {ep.http_method for ep in symbols.endpoints}
    assert "GET" in methods
    assert "POST" in methods
    assert "DELETE" in methods


def test_parser_extracts_endpoint_paths(java_parser, sample_controller):
    """Test that endpoint paths are correctly combined."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    paths = {ep.path for ep in symbols.endpoints}
    assert "/api/users/{id}" in paths
    assert "/api/users" in paths


def test_parser_extracts_method_calls(java_parser, sample_controller):
    """Test that the parser extracts method call targets."""
    source_file = SourceFile(
        path=sample_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]

    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert "userService.findById" in get_user.calls

    create_user = next(m for m in cls.methods if m.name == "createUser")
    assert "userService.save" in create_user.calls

    delete_user = next(m for m in cls.methods if m.name == "deleteUser")
    assert "userService.delete" in delete_user.calls


def test_parser_extracts_simple_calls(java_parser):
    """Test that the parser extracts simple (unqualified) method calls."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example;

public class Service {
    public void process() {
        validate();
        transform();
    }

    private void validate() {}
    private void transform() {}
}
""")
        f.flush()
        path = Path(f.name)

    source_file = SourceFile(
        path=path,
        relative_path=Path("Service.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    process = next(m for m in cls.methods if m.name == "process")
    assert "validate" in process.calls
    assert "transform" in process.calls


def test_parser_extracts_no_calls_from_empty_method(java_parser):
    """Test that methods with no calls have empty calls list."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example;

public class Simple {
    public int getValue() {
        return 42;
    }
}
""")
        f.flush()
        path = Path(f.name)

    source_file = SourceFile(
        path=path,
        relative_path=Path("Simple.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    get_value = next(m for m in cls.methods if m.name == "getValue")
    assert get_value.calls == []
