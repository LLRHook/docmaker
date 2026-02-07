"""Tests for the Java parser."""

import tempfile
from pathlib import Path

import pytest

from docmaker.models import FileCategory, Language, SourceFile
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


@pytest.fixture
def sample_service():
    """Create a sample Java service with inheritance and fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example.service;

import java.util.*;
import com.example.model.User;

/**
 * Service for user operations.
 */
public abstract class UserService extends BaseService implements Serializable {

    private final UserRepository repository;
    protected static int instanceCount;

    /**
     * Constructor for UserService.
     */
    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    /**
     * Find user by ID.
     */
    public abstract User findById(Long id);

    public List<User> findAll() {
        return repository.findAll();
    }

    private void logAction(String action) {
        System.out.println(action);
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_pojo():
    """Create a sample POJO class with multiple annotations."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example.model;

import javax.persistence.*;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = "IDENTITY")
    private Long id;

    @Column(name = "full_name", nullable = "false")
    private String name;

    private String email;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
""")
        f.flush()
        yield Path(f.name)


def _make_source(path, name="Test.java"):
    return SourceFile(
        path=path,
        relative_path=Path(name),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )


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


def test_parser_extracts_class_docstring(java_parser, sample_controller):
    """Test that the parser extracts Javadoc from classes."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    assert cls.docstring is not None
    assert "Controller for user operations" in cls.docstring


def test_parser_extracts_method_docstring(java_parser, sample_controller):
    """Test that the parser extracts Javadoc from methods."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert get_user.docstring is not None
    assert "Get a user by ID" in get_user.docstring


def test_parser_extracts_constructor(java_parser, sample_controller):
    """Test that the parser extracts constructor declarations."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    method_names = [m.name for m in cls.methods]
    assert "UserController" in method_names


def test_parser_extracts_constructor_parameters(java_parser, sample_controller):
    """Test that constructor parameters are extracted."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    ctor = next(m for m in cls.methods if m.name == "UserController")
    assert len(ctor.parameters) == 1
    assert ctor.parameters[0].name == "userService"
    assert ctor.parameters[0].type == "UserService"


def test_parser_extracts_method_return_type(java_parser, sample_controller):
    """Test that method return types are extracted."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert get_user.return_type == "User"
    delete_user = next(m for m in cls.methods if m.name == "deleteUser")
    assert delete_user.return_type == "void"


def test_parser_extracts_method_parameters(java_parser, sample_controller):
    """Test that method parameters are extracted with types and annotations."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert len(get_user.parameters) == 1
    assert get_user.parameters[0].name == "id"
    assert get_user.parameters[0].type == "Long"
    assert "@PathVariable" in (get_user.parameters[0].description or "")


def test_parser_extracts_method_annotations(java_parser, sample_controller):
    """Test that method-level annotations are extracted."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    ann_names = [a.name for a in get_user.annotations]
    assert "GetMapping" in ann_names


def test_parser_extracts_fields(java_parser, sample_controller):
    """Test that the parser extracts field declarations."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    assert len(cls.fields) >= 1
    field_names = [f.name for f in cls.fields]
    assert "userService" in field_names


def test_parser_extracts_field_types(java_parser, sample_controller):
    """Test that field types are extracted."""
    symbols = java_parser.parse(_make_source(sample_controller))
    cls = symbols.classes[0]
    field = next(f for f in cls.fields if f.name == "userService")
    assert field.type == "UserService"


def test_parser_extracts_field_modifiers(java_parser, sample_service):
    """Test that field modifiers are extracted."""
    symbols = java_parser.parse(_make_source(sample_service))
    cls = symbols.classes[0]
    repo_field = next(f for f in cls.fields if f.name == "repository")
    assert "private" in repo_field.modifiers
    assert "final" in repo_field.modifiers
    count_field = next(f for f in cls.fields if f.name == "instanceCount")
    assert "protected" in count_field.modifiers
    assert "static" in count_field.modifiers


def test_parser_extracts_inheritance(java_parser, sample_service):
    """Test that superclass and interfaces are extracted."""
    symbols = java_parser.parse(_make_source(sample_service))
    cls = symbols.classes[0]
    assert cls.superclass == "BaseService"
    assert "Serializable" in cls.interfaces


def test_parser_extracts_class_modifiers(java_parser, sample_service):
    """Test that class modifiers are extracted."""
    symbols = java_parser.parse(_make_source(sample_service))
    cls = symbols.classes[0]
    assert "public" in cls.modifiers
    assert "abstract" in cls.modifiers


def test_parser_extracts_method_modifiers(java_parser, sample_service):
    """Test that method modifiers (public, private, abstract) are extracted."""
    symbols = java_parser.parse(_make_source(sample_service))
    cls = symbols.classes[0]
    find_by_id = next(m for m in cls.methods if m.name == "findById")
    assert "public" in find_by_id.modifiers
    assert "abstract" in find_by_id.modifiers
    log_action = next(m for m in cls.methods if m.name == "logAction")
    assert "private" in log_action.modifiers


def test_parser_extracts_wildcard_imports(java_parser, sample_service):
    """Test that wildcard imports are detected."""
    symbols = java_parser.parse(_make_source(sample_service))
    wildcard_imports = [i for i in symbols.imports if i.is_wildcard]
    assert len(wildcard_imports) >= 1
    assert any("java.util" in i.module for i in wildcard_imports)


def test_parser_extracts_annotation_arguments(java_parser, sample_pojo):
    """Test that annotation arguments are extracted."""
    symbols = java_parser.parse(_make_source(sample_pojo))
    cls = symbols.classes[0]
    table_ann = next(a for a in cls.annotations if a.name == "Table")
    assert table_ann.arguments.get("name") == "users"


def test_parser_extracts_field_annotations(java_parser, sample_pojo):
    """Test that field-level annotations are extracted."""
    symbols = java_parser.parse(_make_source(sample_pojo))
    cls = symbols.classes[0]
    id_field = next(f for f in cls.fields if f.name == "id")
    ann_names = [a.name for a in id_field.annotations]
    assert "Id" in ann_names
    assert "GeneratedValue" in ann_names


def test_parser_extracts_request_body_on_endpoint(java_parser, sample_controller):
    """Test that @RequestBody parameter is detected on endpoints."""
    symbols = java_parser.parse(_make_source(sample_controller))
    post_endpoint = next(ep for ep in symbols.endpoints if ep.http_method == "POST")
    assert post_endpoint.request_body == "User"


def test_parser_extracts_generic_return_type(java_parser, sample_service):
    """Test that generic return types like List<User> are extracted."""
    symbols = java_parser.parse(_make_source(sample_service))
    cls = symbols.classes[0]
    find_all = next(m for m in cls.methods if m.name == "findAll")
    assert find_all.return_type is not None
    assert "List" in find_all.return_type


def test_parser_handles_no_package(java_parser):
    """Test that files without a package declaration work correctly."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
public class Simple {
    public void doSomething() {}
}
""")
        f.flush()
        symbols = java_parser.parse(_make_source(Path(f.name)))
    assert symbols.package is None
    assert len(symbols.classes) == 1
    assert symbols.classes[0].name == "Simple"


def test_parser_extracts_multiple_classes(java_parser):
    """Test extraction of multiple classes from one file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""
package com.example;

public class Outer {
    public void outerMethod() {}
}

class Inner {
    public void innerMethod() {}
}
""")
        f.flush()
        symbols = java_parser.parse(_make_source(Path(f.name)))
    assert len(symbols.classes) >= 2
    names = {c.name for c in symbols.classes}
    assert "Outer" in names
    assert "Inner" in names
