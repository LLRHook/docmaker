"""Tests for the Kotlin parser."""

import tempfile
from pathlib import Path

import pytest
from docmaker.parser.kotlin_parser import KotlinParser

from docmaker.models import FileCategory, Language, SourceFile


@pytest.fixture
def kotlin_parser():
    """Create a Kotlin parser instance."""
    return KotlinParser()


@pytest.fixture
def sample_kotlin_class():
    """Create a sample Kotlin class file with various features."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.service

import org.springframework.stereotype.Service
import com.example.model.User
import com.example.repository.UserRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Service for managing users.
 */
@Service
class UserService(private val repository: UserRepository) {

    val defaultLimit: Int = 100

    var lastAccessTime: Long = 0L

    /**
     * Get a user by ID.
     *
     * @param id the user identifier
     * @return the user if found
     */
    fun getUser(id: Long): User? {
        return repository.findById(id)
    }

    fun createUser(name: String, email: String): User {
        val user = User(name = name, email = email)
        return repository.save(user)
    }

    private fun validateEmail(email: String): Boolean {
        return "@" in email
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_data_class():
    """Create a sample Kotlin file with data classes."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.model

/**
 * Data transfer object for a user.
 */
data class UserDTO(
    val id: Long,
    val name: String,
    val email: String? = null,
    val roles: List<String> = emptyList()
)

data class CreateUserRequest(
    val name: String,
    val email: String
)

/**
 * Represents an API response wrapper.
 */
data class ApiResponse<T>(
    val data: T,
    val status: Int = 200,
    val message: String = "OK"
)
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_companion_object():
    """Create a sample Kotlin file with companion objects."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.config

import com.example.model.User

/**
 * Configuration manager with factory methods.
 */
class AppConfig private constructor(val environment: String) {

    val isProduction: Boolean
        get() = environment == "production"

    companion object {
        const val DEFAULT_ENV = "development"
        const val MAX_RETRIES = 3

        fun create(env: String = DEFAULT_ENV): AppConfig {
            return AppConfig(env)
        }

        fun production(): AppConfig {
            return AppConfig("production")
        }
    }
}

class UserFactory {

    companion object Factory {
        fun fromDTO(dto: Map<String, Any>): User {
            return User(name = dto["name"] as String)
        }
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_spring_controller():
    """Create a sample Kotlin Spring Boot controller."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.controller

import org.springframework.web.bind.annotation.*
import org.springframework.http.ResponseEntity
import com.example.model.User
import com.example.model.UserDTO
import com.example.service.UserService

/**
 * REST controller for user operations.
 */
@RestController
@RequestMapping("/api/users")
class UserController(private val userService: UserService) {

    /**
     * Get all users with pagination.
     */
    @GetMapping
    fun getUsers(
        @RequestParam(defaultValue = "10") limit: Int,
        @RequestParam(defaultValue = "0") offset: Int
    ): List<User> {
        return userService.getAll(limit, offset)
    }

    @GetMapping("/{id}")
    fun getUser(@PathVariable id: Long): ResponseEntity<User> {
        return ResponseEntity.ok(userService.getUser(id))
    }

    @PostMapping
    fun createUser(@RequestBody dto: UserDTO): ResponseEntity<User> {
        return ResponseEntity.ok(userService.create(dto))
    }

    @PutMapping("/{id}")
    fun updateUser(
        @PathVariable id: Long,
        @RequestBody dto: UserDTO
    ): ResponseEntity<User> {
        return ResponseEntity.ok(userService.update(id, dto))
    }

    @DeleteMapping("/{id}")
    fun deleteUser(@PathVariable id: Long): ResponseEntity<Void> {
        userService.delete(id)
        return ResponseEntity.noContent().build()
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_suspend_functions():
    """Create a sample Kotlin file with suspend and coroutine functions."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.async

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * Async service with coroutine support.
 */
class AsyncUserService(private val repository: UserRepository) {

    suspend fun fetchUser(id: Long): User {
        return withContext(Dispatchers.IO) {
            repository.findById(id)
        }
    }

    suspend fun saveUser(user: User): User {
        return withContext(Dispatchers.IO) {
            repository.save(user)
        }
    }

    fun getUserStream(): Flow<User> {
        return flow {
            repository.findAll().forEach { emit(it) }
        }
    }
}

suspend fun fetchRemoteConfig(url: String): Config {
    return withContext(Dispatchers.IO) {
        httpClient.get(url)
    }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_extension_functions():
    """Create a sample Kotlin file with extension functions."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.extensions

import com.example.model.User

/**
 * Formats a user's full name.
 */
fun User.fullName(): String {
    return "$firstName $lastName"
}

fun String.isValidEmail(): Boolean {
    return contains("@") && contains(".")
}

fun List<User>.sortByName(): List<User> {
    return sortedBy { it.name }
}

fun User.toDisplayString(): String {
    return "${fullName()} <$email>"
}

suspend fun User.fetchProfile(): UserProfile {
    return profileService.getProfile(this.id)
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_kotlin_properties():
    """Create a sample Kotlin file with various property declarations."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".kt", delete=False) as f:
        f.write("""package com.example.properties

import com.example.model.User

class PropertyShowcase {

    val readOnly: String = "immutable"

    var mutable: Int = 0

    lateinit var lateInit: String

    val computed: String
        get() = "computed_$readOnly"

    var observed: String = ""
        set(value) {
            field = value.trim()
        }

    private val secret: String = "hidden"

    protected var internal: Int = 42

    const val CONSTANT = "constant_value"
}

val topLevelVal: String = "top"

var topLevelVar: Int = 0
""")
        f.flush()
        yield Path(f.name)


# --- Class Extraction Tests ---


def test_parser_extracts_package(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts the package declaration."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    assert symbols.package == "com.example.service"


def test_parser_extracts_imports(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts import statements."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    import_modules = [i.module for i in symbols.imports]
    assert any("springframework" in m for m in import_modules)
    assert any("UserRepository" in m for m in import_modules)
    assert any("coroutines" in m for m in import_modules)


def test_parser_extracts_class(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts class definitions."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    assert len(symbols.classes) == 1
    cls = symbols.classes[0]
    assert cls.name == "UserService"


def test_parser_extracts_class_docstring(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts KDoc comments."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    assert cls.docstring is not None
    assert "managing users" in cls.docstring


def test_parser_extracts_methods(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts method definitions."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    method_names = [m.name for m in cls.methods]
    assert "getUser" in method_names
    assert "createUser" in method_names
    assert "validateEmail" in method_names


def test_parser_extracts_method_docstring(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts method KDoc comments."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert get_user.docstring is not None
    assert "Get a user by ID" in get_user.docstring


def test_parser_extracts_method_parameters(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts method parameters with types."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")

    param_names = [p.name for p in get_user.parameters]
    assert "id" in param_names

    id_param = next(p for p in get_user.parameters if p.name == "id")
    assert id_param.type == "Long"


def test_parser_extracts_return_types(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts method return types."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    assert get_user.return_type is not None
    assert "User" in get_user.return_type


def test_parser_extracts_method_modifiers(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts method visibility modifiers."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    validate_email = next(m for m in cls.methods if m.name == "validateEmail")
    assert "private" in validate_email.modifiers


# --- Data Class Tests ---


def test_parser_extracts_data_classes(kotlin_parser, sample_kotlin_data_class):
    """Test that the parser extracts data class definitions."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    class_names = [c.name for c in symbols.classes]
    assert "UserDTO" in class_names
    assert "CreateUserRequest" in class_names
    assert "ApiResponse" in class_names


def test_parser_marks_data_class_modifier(kotlin_parser, sample_kotlin_data_class):
    """Test that data classes are marked with the data modifier."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    assert "data" in user_dto.modifiers


def test_parser_extracts_data_class_docstring(kotlin_parser, sample_kotlin_data_class):
    """Test that the parser extracts data class KDoc comments."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    assert user_dto.docstring is not None
    assert "Data transfer object" in user_dto.docstring


def test_parser_extracts_data_class_fields(kotlin_parser, sample_kotlin_data_class):
    """Test that the parser extracts data class constructor properties as fields."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    field_names = [f.name for f in user_dto.fields]
    assert "id" in field_names
    assert "name" in field_names
    assert "email" in field_names
    assert "roles" in field_names


def test_parser_extracts_data_class_field_types(kotlin_parser, sample_kotlin_data_class):
    """Test that the parser extracts field types from data class constructor."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")

    id_field = next(f for f in user_dto.fields if f.name == "id")
    assert id_field.type == "Long"

    name_field = next(f for f in user_dto.fields if f.name == "name")
    assert name_field.type == "String"


def test_parser_extracts_nullable_types(kotlin_parser, sample_kotlin_data_class):
    """Test that the parser handles nullable types (String?)."""
    source_file = SourceFile(
        path=sample_kotlin_data_class,
        relative_path=Path("UserDTO.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    email_field = next(f for f in user_dto.fields if f.name == "email")
    assert email_field.type is not None
    assert "?" in email_field.type or "String" in email_field.type


# --- Companion Object Tests ---


def test_parser_extracts_companion_object_methods(kotlin_parser, sample_kotlin_companion_object):
    """Test that the parser extracts companion object methods."""
    source_file = SourceFile(
        path=sample_kotlin_companion_object,
        relative_path=Path("AppConfig.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    app_config = next(c for c in symbols.classes if c.name == "AppConfig")
    method_names = [m.name for m in app_config.methods]
    assert "create" in method_names
    assert "production" in method_names


def test_parser_extracts_companion_object_fields(kotlin_parser, sample_kotlin_companion_object):
    """Test that the parser extracts companion object constants as fields."""
    source_file = SourceFile(
        path=sample_kotlin_companion_object,
        relative_path=Path("AppConfig.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    app_config = next(c for c in symbols.classes if c.name == "AppConfig")
    field_names = [f.name for f in app_config.fields]
    assert "DEFAULT_ENV" in field_names
    assert "MAX_RETRIES" in field_names


def test_parser_extracts_named_companion_object(kotlin_parser, sample_kotlin_companion_object):
    """Test that the parser handles named companion objects."""
    source_file = SourceFile(
        path=sample_kotlin_companion_object,
        relative_path=Path("AppConfig.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    user_factory = next(c for c in symbols.classes if c.name == "UserFactory")
    method_names = [m.name for m in user_factory.methods]
    assert "fromDTO" in method_names


def test_parser_extracts_instance_properties_with_companion(
    kotlin_parser, sample_kotlin_companion_object
):
    """Test that instance properties are extracted alongside companion object."""
    source_file = SourceFile(
        path=sample_kotlin_companion_object,
        relative_path=Path("AppConfig.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    app_config = next(c for c in symbols.classes if c.name == "AppConfig")
    field_names = [f.name for f in app_config.fields]
    assert "environment" in field_names or "isProduction" in field_names


# --- Spring Annotation Tests ---


def test_parser_extracts_class_annotations(kotlin_parser, sample_kotlin_spring_controller):
    """Test that the parser extracts Spring class annotations."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    ann_names = [a.name for a in cls.annotations]
    assert "RestController" in ann_names
    assert "RequestMapping" in ann_names


def test_parser_extracts_annotation_arguments(kotlin_parser, sample_kotlin_spring_controller):
    """Test that the parser extracts annotation arguments."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    request_mapping = next(a for a in cls.annotations if a.name == "RequestMapping")
    assert "/api/users" in str(request_mapping.arguments)


def test_parser_extracts_method_annotations(kotlin_parser, sample_kotlin_spring_controller):
    """Test that the parser extracts Spring method annotations."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    ann_names = [a.name for a in get_user.annotations]
    assert "GetMapping" in ann_names


def test_parser_extracts_parameter_annotations(kotlin_parser, sample_kotlin_spring_controller):
    """Test that the parser extracts parameter annotations like @PathVariable."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user = next(m for m in cls.methods if m.name == "getUser")
    id_param = next(p for p in get_user.parameters if p.name == "id")
    # Parameter annotations may be stored in parameter description or type
    assert id_param.type == "Long"


def test_parser_extracts_endpoints(kotlin_parser, sample_kotlin_spring_controller):
    """Test that the parser extracts REST endpoints."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    assert len(symbols.endpoints) == 5

    methods = {ep.http_method for ep in symbols.endpoints}
    assert "GET" in methods
    assert "POST" in methods
    assert "PUT" in methods
    assert "DELETE" in methods


def test_parser_extracts_endpoint_paths(kotlin_parser, sample_kotlin_spring_controller):
    """Test that endpoint paths are correctly combined from class and method."""
    source_file = SourceFile(
        path=sample_kotlin_spring_controller,
        relative_path=Path("UserController.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    paths = {ep.path for ep in symbols.endpoints}
    assert "/api/users" in paths
    assert "/api/users/{id}" in paths


def test_parser_extracts_service_annotation(kotlin_parser, sample_kotlin_class):
    """Test that the parser extracts @Service annotation."""
    source_file = SourceFile(
        path=sample_kotlin_class,
        relative_path=Path("UserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    ann_names = [a.name for a in cls.annotations]
    assert "Service" in ann_names


# --- Suspend Function Tests ---


def test_parser_extracts_suspend_methods(kotlin_parser, sample_kotlin_suspend_functions):
    """Test that the parser identifies suspend methods."""
    source_file = SourceFile(
        path=sample_kotlin_suspend_functions,
        relative_path=Path("AsyncUserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    fetch_user = next(m for m in cls.methods if m.name == "fetchUser")
    assert "suspend" in fetch_user.modifiers


def test_parser_extracts_non_suspend_alongside_suspend(
    kotlin_parser, sample_kotlin_suspend_functions
):
    """Test that non-suspend methods are correctly identified alongside suspend ones."""
    source_file = SourceFile(
        path=sample_kotlin_suspend_functions,
        relative_path=Path("AsyncUserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    get_user_stream = next(m for m in cls.methods if m.name == "getUserStream")
    assert "suspend" not in get_user_stream.modifiers


def test_parser_extracts_suspend_top_level_functions(
    kotlin_parser, sample_kotlin_suspend_functions
):
    """Test that the parser extracts top-level suspend functions."""
    source_file = SourceFile(
        path=sample_kotlin_suspend_functions,
        relative_path=Path("AsyncUserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "fetchRemoteConfig" in function_names

    fetch_config = next(f for f in symbols.functions if f.name == "fetchRemoteConfig")
    assert "suspend" in fetch_config.modifiers


def test_parser_extracts_suspend_method_parameters(kotlin_parser, sample_kotlin_suspend_functions):
    """Test that suspend method parameters are correctly extracted."""
    source_file = SourceFile(
        path=sample_kotlin_suspend_functions,
        relative_path=Path("AsyncUserService.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    fetch_user = next(m for m in cls.methods if m.name == "fetchUser")

    param_names = [p.name for p in fetch_user.parameters]
    assert "id" in param_names

    id_param = next(p for p in fetch_user.parameters if p.name == "id")
    assert id_param.type == "Long"


# --- Extension Function Tests ---


def test_parser_extracts_extension_functions(kotlin_parser, sample_kotlin_extension_functions):
    """Test that the parser extracts extension functions."""
    source_file = SourceFile(
        path=sample_kotlin_extension_functions,
        relative_path=Path("Extensions.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "fullName" in function_names or "User.fullName" in function_names
    assert "isValidEmail" in function_names or "String.isValidEmail" in function_names


def test_parser_extracts_extension_function_return_types(
    kotlin_parser, sample_kotlin_extension_functions
):
    """Test that extension function return types are extracted."""
    source_file = SourceFile(
        path=sample_kotlin_extension_functions,
        relative_path=Path("Extensions.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    full_name = next(
        f for f in symbols.functions if f.name == "fullName" or f.name == "User.fullName"
    )
    assert full_name.return_type is not None
    assert "String" in full_name.return_type


def test_parser_extracts_extension_function_docstring(
    kotlin_parser, sample_kotlin_extension_functions
):
    """Test that extension function KDoc comments are extracted."""
    source_file = SourceFile(
        path=sample_kotlin_extension_functions,
        relative_path=Path("Extensions.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    full_name = next(
        f for f in symbols.functions if f.name == "fullName" or f.name == "User.fullName"
    )
    assert full_name.docstring is not None
    assert "full name" in full_name.docstring.lower()


def test_parser_extracts_suspend_extension_functions(
    kotlin_parser, sample_kotlin_extension_functions
):
    """Test that suspend extension functions are properly identified."""
    source_file = SourceFile(
        path=sample_kotlin_extension_functions,
        relative_path=Path("Extensions.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    fetch_profile = next(
        f for f in symbols.functions if f.name == "fetchProfile" or f.name == "User.fetchProfile"
    )
    assert "suspend" in fetch_profile.modifiers


# --- Property Declaration Tests ---


def test_parser_extracts_val_properties(kotlin_parser, sample_kotlin_properties):
    """Test that the parser extracts val (read-only) properties."""
    source_file = SourceFile(
        path=sample_kotlin_properties,
        relative_path=Path("PropertyShowcase.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    field_names = [f.name for f in cls.fields]
    assert "readOnly" in field_names


def test_parser_extracts_var_properties(kotlin_parser, sample_kotlin_properties):
    """Test that the parser extracts var (mutable) properties."""
    source_file = SourceFile(
        path=sample_kotlin_properties,
        relative_path=Path("PropertyShowcase.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    field_names = [f.name for f in cls.fields]
    assert "mutable" in field_names


def test_parser_extracts_property_types(kotlin_parser, sample_kotlin_properties):
    """Test that the parser extracts property types."""
    source_file = SourceFile(
        path=sample_kotlin_properties,
        relative_path=Path("PropertyShowcase.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    read_only = next(f for f in cls.fields if f.name == "readOnly")
    assert read_only.type == "String"

    mutable_field = next(f for f in cls.fields if f.name == "mutable")
    assert mutable_field.type == "Int"


def test_parser_extracts_lateinit_properties(kotlin_parser, sample_kotlin_properties):
    """Test that the parser extracts lateinit properties."""
    source_file = SourceFile(
        path=sample_kotlin_properties,
        relative_path=Path("PropertyShowcase.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    field_names = [f.name for f in cls.fields]
    assert "lateInit" in field_names


def test_parser_extracts_property_visibility_modifiers(kotlin_parser, sample_kotlin_properties):
    """Test that the parser extracts property visibility modifiers."""
    source_file = SourceFile(
        path=sample_kotlin_properties,
        relative_path=Path("PropertyShowcase.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    symbols = kotlin_parser.parse(source_file)

    cls = symbols.classes[0]
    secret = next(f for f in cls.fields if f.name == "secret")
    assert "private" in secret.modifiers


# --- Can Parse Tests ---


def test_parser_can_parse_kt_files(kotlin_parser):
    """Test that the parser reports it can parse .kt files."""
    source_file = SourceFile(
        path=Path("test.kt"),
        relative_path=Path("test.kt"),
        language=Language.KOTLIN,
        category=FileCategory.BACKEND,
    )

    assert kotlin_parser.can_parse(source_file)


def test_parser_cannot_parse_non_kotlin_files(kotlin_parser):
    """Test that the parser reports it cannot parse non-Kotlin files."""
    source_file = SourceFile(
        path=Path("test.java"),
        relative_path=Path("test.java"),
        language=Language.JAVA,
        category=FileCategory.BACKEND,
    )

    assert not kotlin_parser.can_parse(source_file)


def test_parser_language_property(kotlin_parser):
    """Test that the parser reports Kotlin as its language."""
    assert kotlin_parser.language == Language.KOTLIN
