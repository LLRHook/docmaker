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
def sample_java_class():
    """Create a sample Java class with inheritance, fields, methods, and Javadoc."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.service;

import java.util.List;
import java.util.Optional;
import com.example.model.User;
import com.example.repository.*;

/** Service for managing users. */
public class UserService extends BaseService implements Serializable {

    private final UserRepository repository;
    protected int maxRetries;
    public static final String DEFAULT_ROLE = "USER";

    /** Create a new UserService. */
    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    /**
     * Find a user by their unique ID.
     */
    public Optional<User> findById(long id) {
        return repository.findById(id);
    }

    public List<User> findAll(int limit, int offset) {
        return repository.findAll(limit, offset);
    }

    private void validateUser(User user) {
        // validation logic
    }

    public static UserService create() {
        return new UserService(null);
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_spring_controller():
    """Create a sample Spring REST controller with various endpoint mappings."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.controller;

import org.springframework.web.bind.annotation.*;
import com.example.model.User;
import com.example.service.UserService;

@RestController
@RequestMapping(value = "/api/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public List<User> getAll() {
        return userService.findAll();
    }

    @GetMapping(value = "/{id}")
    public User getById(@PathVariable long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User create(@RequestBody User user) {
        return userService.create(user);
    }

    @PutMapping(value = "/{id}")
    public User update(@PathVariable long id, @RequestBody User user) {
        return userService.update(id, user);
    }

    @DeleteMapping(value = "/{id}")
    public void delete(@PathVariable long id) {
        userService.delete(id);
    }

    @PatchMapping(value = "/{id}/status")
    public User updateStatus(@PathVariable long id, @RequestParam String status) {
        return userService.updateStatus(id, status);
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_spring_service():
    """Create a sample Spring service with @Service annotation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

@Service
public class OrderService {

    @Autowired
    private OrderRepository orderRepository;

    public void processOrder(Order order) {
        orderRepository.save(order);
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_spring_repository():
    """Create a sample Spring repository with @Repository annotation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.repository;

import org.springframework.stereotype.Repository;

@Repository
public class UserRepository extends BaseRepository implements CrudRepository {

    public User findById(long id) {
        return null;
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_java_interfaces():
    """Create a sample Java file with multiple interface implementations."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.model;

public class PaymentProcessor extends AbstractProcessor implements Runnable, Closeable {

    private String apiKey;

    public void run() {
        // process
    }

    public void close() {
        // cleanup
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_java_request_mapping():
    """Create a controller using @RequestMapping with method attribute for endpoints."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.controller;

import org.springframework.web.bind.annotation.*;

@Controller
@RequestMapping(value = "/legacy")
public class LegacyController {

    @RequestMapping(value = "/items", method = "GET")
    public List<Item> listItems() {
        return null;
    }

    @RequestMapping(value = "/items", method = "POST")
    public Item createItem(@RequestBody Item item) {
        return null;
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_java_method_params():
    """Create a controller with various parameter annotation styles."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
        f.write("""package com.example.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping(value = "/api/search")
public class SearchController {

    @GetMapping
    public List<Result> search(
            @RequestParam String query,
            @RequestParam int page,
            @RequestHeader String authorization,
            @PathVariable String category) {
        return null;
    }

    @PostMapping(value = "/bulk")
    public void bulkSearch(@RequestBody SearchRequest request) {
        // bulk search
    }
}
""")
        f.flush()
        yield Path(f.name)


# --- Package extraction ---


def test_parser_extracts_package(java_parser, sample_java_class):
    """Test that the parser extracts the package declaration."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    assert symbols.package == "com.example.service"


# --- Import extraction ---


def test_parser_extracts_imports(java_parser, sample_java_class):
    """Test that the parser extracts import statements."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    import_modules = [i.module for i in symbols.imports]
    assert "java.util.List" in import_modules
    assert "java.util.Optional" in import_modules
    assert "com.example.model.User" in import_modules


def test_parser_extracts_wildcard_imports(java_parser, sample_java_class):
    """Test that the parser identifies wildcard imports."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    wildcards = [i for i in symbols.imports if i.is_wildcard]
    assert len(wildcards) == 1
    assert "com.example.repository.*" in wildcards[0].module


# --- Class extraction ---


def test_parser_extracts_classes(java_parser, sample_java_class):
    """Test that the parser extracts class definitions."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    class_names = [c.name for c in symbols.classes]
    assert "UserService" in class_names


def test_parser_extracts_class_docstring(java_parser, sample_java_class):
    """Test that the parser extracts Javadoc comments from classes."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert user_service.docstring is not None
    assert "managing users" in user_service.docstring


def test_parser_extracts_class_modifiers(java_parser, sample_java_class):
    """Test that the parser extracts class modifiers (public, abstract, etc.)."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert "public" in user_service.modifiers


# --- Inheritance ---


def test_parser_extracts_superclass(java_parser, sample_java_class):
    """Test that the parser extracts the superclass (extends)."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert user_service.superclass == "BaseService"


def test_parser_extracts_interfaces(java_parser, sample_java_class):
    """Test that the parser extracts implemented interfaces."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert "Serializable" in user_service.interfaces


def test_parser_extracts_multiple_interfaces(java_parser, sample_java_interfaces):
    """Test that the parser extracts multiple implemented interfaces."""
    source_file = SourceFile(
        path=sample_java_interfaces,
        relative_path=Path("PaymentProcessor.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    processor = next(c for c in symbols.classes if c.name == "PaymentProcessor")
    assert processor.superclass == "AbstractProcessor"
    assert "Runnable" in processor.interfaces
    assert "Closeable" in processor.interfaces
    assert len(processor.interfaces) == 2


# --- Field extraction ---


def test_parser_extracts_fields(java_parser, sample_java_class):
    """Test that the parser extracts field definitions."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    field_names = [f.name for f in user_service.fields]
    assert "repository" in field_names
    assert "maxRetries" in field_names
    assert "DEFAULT_ROLE" in field_names


def test_parser_extracts_field_types(java_parser, sample_java_class):
    """Test that the parser extracts field types."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    repo_field = next(f for f in user_service.fields if f.name == "repository")
    assert repo_field.type == "UserRepository"


def test_parser_extracts_field_modifiers(java_parser, sample_java_class):
    """Test that the parser extracts field modifiers."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    repo_field = next(f for f in user_service.fields if f.name == "repository")
    assert "private" in repo_field.modifiers
    assert "final" in repo_field.modifiers


# --- Method extraction ---


def test_parser_extracts_methods(java_parser, sample_java_class):
    """Test that the parser extracts method definitions."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    method_names = [m.name for m in user_service.methods]
    assert "findById" in method_names
    assert "findAll" in method_names
    assert "validateUser" in method_names
    assert "create" in method_names


def test_parser_extracts_constructor(java_parser, sample_java_class):
    """Test that the parser extracts constructors."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    constructor = next((m for m in user_service.methods if m.name == "UserService"), None)
    assert constructor is not None
    assert constructor.return_type is None


def test_parser_extracts_method_docstring(java_parser, sample_java_class):
    """Test that the parser extracts method Javadoc comments."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    find_by_id = next(m for m in user_service.methods if m.name == "findById")
    assert find_by_id.docstring is not None
    assert "Find a user" in find_by_id.docstring


def test_parser_extracts_method_return_type(java_parser, sample_java_class):
    """Test that the parser extracts method return types."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    find_by_id = next(m for m in user_service.methods if m.name == "findById")
    assert find_by_id.return_type is not None
    assert "Optional" in find_by_id.return_type


def test_parser_extracts_method_modifiers(java_parser, sample_java_class):
    """Test that the parser extracts method modifiers."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")

    validate = next(m for m in user_service.methods if m.name == "validateUser")
    assert "private" in validate.modifiers

    create = next(m for m in user_service.methods if m.name == "create")
    assert "public" in create.modifiers
    assert "static" in create.modifiers


# --- Method parameters ---


def test_parser_extracts_method_parameters(java_parser, sample_java_class):
    """Test that the parser extracts method parameters."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    find_all = next(m for m in user_service.methods if m.name == "findAll")

    param_names = [p.name for p in find_all.parameters]
    assert "limit" in param_names
    assert "offset" in param_names


def test_parser_extracts_parameter_types(java_parser, sample_java_class):
    """Test that the parser extracts parameter types."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    find_by_id = next(m for m in user_service.methods if m.name == "findById")

    id_param = next(p for p in find_by_id.parameters if p.name == "id")
    assert id_param.type is not None


def test_parser_extracts_annotated_parameters(java_parser, sample_java_method_params):
    """Test that the parser extracts parameter annotations like @RequestParam."""
    source_file = SourceFile(
        path=sample_java_method_params,
        relative_path=Path("SearchController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    controller = next(c for c in symbols.classes if c.name == "SearchController")
    search = next(m for m in controller.methods if m.name == "search")

    query_param = next(p for p in search.parameters if p.name == "query")
    assert query_param.description is not None
    assert "@RequestParam" in query_param.description

    auth_param = next(p for p in search.parameters if p.name == "authorization")
    assert auth_param.description is not None
    assert "@RequestHeader" in auth_param.description

    cat_param = next(p for p in search.parameters if p.name == "category")
    assert cat_param.description is not None
    assert "@PathVariable" in cat_param.description


# --- Spring annotations ---


def test_parser_extracts_rest_controller_annotation(java_parser, sample_spring_controller):
    """Test that the parser extracts @RestController annotation."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    controller = next(c for c in symbols.classes if c.name == "UserController")
    annotation_names = [a.name for a in controller.annotations]
    assert "RestController" in annotation_names
    assert "RequestMapping" in annotation_names


def test_parser_extracts_request_mapping_value(java_parser, sample_spring_controller):
    """Test that the parser extracts @RequestMapping value argument."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    controller = next(c for c in symbols.classes if c.name == "UserController")
    req_mapping = next(a for a in controller.annotations if a.name == "RequestMapping")
    assert req_mapping.arguments.get("value") == "/api/users"


def test_parser_extracts_service_annotation(java_parser, sample_spring_service):
    """Test that the parser extracts @Service annotation."""
    source_file = SourceFile(
        path=sample_spring_service,
        relative_path=Path("OrderService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    service = next(c for c in symbols.classes if c.name == "OrderService")
    annotation_names = [a.name for a in service.annotations]
    assert "Service" in annotation_names


def test_parser_extracts_repository_annotation(java_parser, sample_spring_repository):
    """Test that the parser extracts @Repository annotation."""
    source_file = SourceFile(
        path=sample_spring_repository,
        relative_path=Path("UserRepository.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    repo = next(c for c in symbols.classes if c.name == "UserRepository")
    annotation_names = [a.name for a in repo.annotations]
    assert "Repository" in annotation_names


def test_parser_extracts_autowired_annotation(java_parser, sample_spring_service):
    """Test that the parser extracts @Autowired field annotation."""
    source_file = SourceFile(
        path=sample_spring_service,
        relative_path=Path("OrderService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    service = next(c for c in symbols.classes if c.name == "OrderService")
    repo_field = next(f for f in service.fields if f.name == "orderRepository")
    annotation_names = [a.name for a in repo_field.annotations]
    assert "Autowired" in annotation_names


def test_parser_extracts_method_annotations(java_parser, sample_spring_controller):
    """Test that the parser extracts method-level annotations like @GetMapping."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    controller = next(c for c in symbols.classes if c.name == "UserController")
    get_all = next(m for m in controller.methods if m.name == "getAll")
    annotation_names = [a.name for a in get_all.annotations]
    assert "GetMapping" in annotation_names


# --- REST endpoint parsing ---


def test_parser_extracts_get_endpoint(java_parser, sample_spring_controller):
    """Test that the parser extracts GET endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    get_endpoints = [e for e in symbols.endpoints if e.http_method == "GET"]
    assert len(get_endpoints) == 2

    paths = [e.path for e in get_endpoints]
    assert "/api/users" in paths
    assert "/api/users/{id}" in paths


def test_parser_extracts_post_endpoint(java_parser, sample_spring_controller):
    """Test that the parser extracts POST endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    post_endpoints = [e for e in symbols.endpoints if e.http_method == "POST"]
    assert len(post_endpoints) == 1
    assert post_endpoints[0].path == "/api/users"
    assert post_endpoints[0].handler_method == "create"


def test_parser_extracts_put_endpoint(java_parser, sample_spring_controller):
    """Test that the parser extracts PUT endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    put_endpoints = [e for e in symbols.endpoints if e.http_method == "PUT"]
    assert len(put_endpoints) == 1
    assert put_endpoints[0].path == "/api/users/{id}"


def test_parser_extracts_delete_endpoint(java_parser, sample_spring_controller):
    """Test that the parser extracts DELETE endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    delete_endpoints = [e for e in symbols.endpoints if e.http_method == "DELETE"]
    assert len(delete_endpoints) == 1
    assert delete_endpoints[0].path == "/api/users/{id}"


def test_parser_extracts_patch_endpoint(java_parser, sample_spring_controller):
    """Test that the parser extracts PATCH endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    patch_endpoints = [e for e in symbols.endpoints if e.http_method == "PATCH"]
    assert len(patch_endpoints) == 1
    assert patch_endpoints[0].path == "/api/users/{id}/status"


def test_parser_extracts_endpoint_handler_class(java_parser, sample_spring_controller):
    """Test that endpoints reference their handler class."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    for endpoint in symbols.endpoints:
        assert endpoint.handler_class == "UserController"


def test_parser_extracts_endpoint_request_body(java_parser, sample_spring_controller):
    """Test that the parser identifies @RequestBody parameters on endpoints."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    post_endpoint = next(e for e in symbols.endpoints if e.http_method == "POST")
    assert post_endpoint.request_body == "User"


def test_parser_extracts_request_mapping_endpoints(java_parser, sample_java_request_mapping):
    """Test that the parser handles @RequestMapping with method attribute."""
    source_file = SourceFile(
        path=sample_java_request_mapping,
        relative_path=Path("LegacyController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    # @Controller (not @RestController) should still extract endpoints
    # since the code checks for both "Controller" and "RestController"
    get_endpoints = [e for e in symbols.endpoints if e.http_method == "GET"]
    post_endpoints = [e for e in symbols.endpoints if e.http_method == "POST"]
    assert len(get_endpoints) == 1
    assert len(post_endpoints) == 1
    assert get_endpoints[0].path == "/legacy/items"


def test_parser_no_endpoints_for_non_controller(java_parser, sample_java_class):
    """Test that the parser does not extract endpoints from non-controller classes."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    assert len(symbols.endpoints) == 0


def test_parser_extracts_all_endpoint_methods(java_parser, sample_spring_controller):
    """Test that the parser extracts all HTTP methods from a controller."""
    source_file = SourceFile(
        path=sample_spring_controller,
        relative_path=Path("UserController.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    methods = {e.http_method for e in symbols.endpoints}
    assert methods == {"GET", "POST", "PUT", "DELETE", "PATCH"}


# --- Line numbers ---


def test_parser_extracts_line_numbers(java_parser, sample_java_class):
    """Test that the parser records line numbers for classes and methods."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert user_service.line_number > 0
    assert user_service.end_line > user_service.line_number

    for method in user_service.methods:
        assert method.line_number > 0
        assert method.end_line >= method.line_number


def test_parser_extracts_import_line_numbers(java_parser, sample_java_class):
    """Test that the parser records line numbers for imports."""
    source_file = SourceFile(
        path=sample_java_class,
        relative_path=Path("UserService.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    symbols = java_parser.parse(source_file)

    for imp in symbols.imports:
        assert imp.line_number > 0
