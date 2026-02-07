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


@pytest.fixture
def sample_java_with_constructors():
    """Create a sample Java file with constructor instantiation calls."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example.service;

import com.example.model.User;
import com.example.model.Address;
import java.util.ArrayList;

public class UserService {

    public User createUser(String name) {
        Address address = new Address();
        ArrayList<String> tags = new ArrayList<>();
        return new User(name, address);
    }

    public UserService() {
        ArrayList<User> users = new ArrayList<>();
    }
}
""")
        f.flush()
        yield Path(f.name)


def test_parser_extracts_constructor_calls(java_parser, sample_java_with_constructors):
    """Test that the parser extracts constructor instantiation calls."""
    source_file = SourceFile(
        path=sample_java_with_constructors,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    create_user = next(m for m in cls.methods if m.name == "createUser")
    assert "Address" in create_user.calls
    assert "ArrayList" in create_user.calls
    assert "User" in create_user.calls


def test_parser_extracts_constructor_calls_in_constructor(
    java_parser, sample_java_with_constructors
):
    """Test that constructor calls are extracted from constructor bodies."""
    source_file = SourceFile(
        path=sample_java_with_constructors,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    cls = symbols.classes[0]
    constructor = next(m for m in cls.methods if m.name == "UserService")
    assert "ArrayList" in constructor.calls
