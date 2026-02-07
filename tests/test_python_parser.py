"""Tests for the Python parser."""

import tempfile
from pathlib import Path

import pytest

from docmaker.models import FileCategory, Language, SourceFile
from docmaker.parser.python_parser import PythonParser


@pytest.fixture
def python_parser():
    """Create a Python parser instance."""
    return PythonParser()


@pytest.fixture
def sample_python_class():
    """Create a sample Python class file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('''"""User service module."""

from dataclasses import dataclass
from typing import Optional, List
import logging

from app.models import User
from app.repository import UserRepository


logger = logging.getLogger(__name__)


@dataclass
class UserDTO:
    """Data transfer object for User."""

    id: int
    name: str
    email: Optional[str] = None


class UserService:
    """Service for managing users."""

    default_limit = 100

    def __init__(self, repository: UserRepository):
        """Initialize the service with a repository."""
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        return self.repository.find_by_id(user_id)

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate an email address."""
        return "@" in email

    async def create_user(self, name: str, email: str) -> User:
        """Create a new user asynchronously."""
        user = User(name=name, email=email)
        return await self.repository.save(user)


def get_all_users(limit: int = 10, offset: int = 0) -> List[User]:
    """Get all users with pagination."""
    pass
''')
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_python_imports():
    """Create a sample Python file with various import styles."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('''import os
import sys as system
from pathlib import Path
from typing import List, Dict
from collections import defaultdict as dd
from . import local_module
from ..parent import parent_function
from package.module import *
''')
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_python_decorators():
    """Create a sample Python file with various decorators."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('''from flask import Flask, jsonify
from functools import wraps

app = Flask(__name__)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


@app.route("/api/users", methods=["GET"])
@require_auth
def get_users():
    """Get all users."""
    return jsonify([])


class Controller:
    @property
    def name(self) -> str:
        return "controller"

    @classmethod
    def create(cls):
        return cls()

    @staticmethod
    def version():
        return "1.0"
''')
        f.flush()
        yield Path(f.name)


def test_parser_extracts_module_name(python_parser, sample_python_class):
    """Test that the parser extracts the module name."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    assert symbols.package is not None


def test_parser_extracts_imports(python_parser, sample_python_imports):
    """Test that the parser extracts import statements."""
    source_file = SourceFile(
        path=sample_python_imports,
        relative_path=Path("imports.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    import_modules = [i.module for i in symbols.imports]
    assert "os" in import_modules
    assert "sys" in import_modules
    # from pathlib import Path should give us pathlib.Path
    assert any("pathlib" in m for m in import_modules)

    aliased = [i for i in symbols.imports if i.alias is not None]
    assert len(aliased) >= 1

    wildcards = [i for i in symbols.imports if i.is_wildcard]
    assert len(wildcards) == 1


def test_parser_extracts_classes(python_parser, sample_python_class):
    """Test that the parser extracts class definitions."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    assert len(symbols.classes) == 2
    class_names = [c.name for c in symbols.classes]
    assert "UserDTO" in class_names
    assert "UserService" in class_names


def test_parser_extracts_class_docstring(python_parser, sample_python_class):
    """Test that the parser extracts class docstrings."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert user_service.docstring is not None
    assert "managing users" in user_service.docstring


def test_parser_extracts_decorators(python_parser, sample_python_class):
    """Test that the parser extracts class decorators."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    decorator_names = [a.name for a in user_dto.annotations]
    assert "dataclass" in decorator_names


def test_parser_extracts_methods(python_parser, sample_python_class):
    """Test that the parser extracts method definitions."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    method_names = [m.name for m in user_service.methods]
    assert "__init__" in method_names
    assert "get_user" in method_names
    assert "validate_email" in method_names
    assert "create_user" in method_names


def test_parser_extracts_method_docstring(python_parser, sample_python_class):
    """Test that the parser extracts method docstrings."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_user = next(m for m in user_service.methods if m.name == "get_user")
    assert get_user.docstring is not None
    assert "Get a user by ID" in get_user.docstring


def test_parser_extracts_parameters(python_parser, sample_python_class):
    """Test that the parser extracts method parameters."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_user = next(m for m in user_service.methods if m.name == "get_user")

    param_names = [p.name for p in get_user.parameters]
    assert "self" in param_names
    assert "user_id" in param_names


def test_parser_extracts_type_hints(python_parser, sample_python_class):
    """Test that the parser extracts type hints."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_user = next(m for m in user_service.methods if m.name == "get_user")

    user_id_param = next(p for p in get_user.parameters if p.name == "user_id")
    assert user_id_param.type == "int"

    assert get_user.return_type is not None
    assert "Optional" in get_user.return_type or "User" in get_user.return_type


def test_parser_extracts_async_methods(python_parser, sample_python_class):
    """Test that the parser identifies async methods."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    create_user = next(m for m in user_service.methods if m.name == "create_user")

    assert "async" in create_user.modifiers


def test_parser_extracts_static_methods(python_parser, sample_python_class):
    """Test that the parser identifies static methods."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    validate_email = next(m for m in user_service.methods if m.name == "validate_email")

    assert "staticmethod" in validate_email.modifiers


def test_parser_extracts_module_functions(python_parser, sample_python_class):
    """Test that the parser extracts module-level functions."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "get_all_users" in function_names


def test_parser_extracts_method_decorators(python_parser, sample_python_decorators):
    """Test that the parser extracts method decorators."""
    source_file = SourceFile(
        path=sample_python_decorators,
        relative_path=Path("decorators.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    controller = next(c for c in symbols.classes if c.name == "Controller")

    name_prop = next(m for m in controller.methods if m.name == "name")
    assert "property" in name_prop.modifiers

    create_method = next(m for m in controller.methods if m.name == "create")
    assert "classmethod" in create_method.modifiers


def test_parser_extracts_function_decorators(python_parser, sample_python_decorators):
    """Test that the parser extracts function decorators."""
    source_file = SourceFile(
        path=sample_python_decorators,
        relative_path=Path("decorators.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    get_users = next((f for f in symbols.functions if f.name == "get_users"), None)
    assert get_users is not None

    decorator_names = [a.name for a in get_users.annotations]
    assert "app.route" in decorator_names or any("route" in n for n in decorator_names)


def test_parser_extracts_class_fields(python_parser, sample_python_class):
    """Test that the parser extracts class-level fields."""
    source_file = SourceFile(
        path=sample_python_class,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    field_names = [f.name for f in user_service.fields]
    assert "default_limit" in field_names


@pytest.fixture
def sample_python_with_constructors():
    """Create a sample Python file with constructor instantiation calls."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('''from models import User, Address

class UserService:
    def create_user(self, name: str):
        address = Address("123 Main St")
        user = User(name=name, address=address)
        return user

    def get_config(self):
        config = dict()
        return config
''')
        f.flush()
        yield Path(f.name)


def test_parser_extracts_constructor_calls(python_parser, sample_python_with_constructors):
    """Test that the parser extracts constructor instantiation calls."""
    source_file = SourceFile(
        path=sample_python_with_constructors,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    create_user = next(m for m in user_service.methods if m.name == "create_user")
    assert "Address" in create_user.calls
    assert "User" in create_user.calls


def test_parser_ignores_lowercase_calls(python_parser, sample_python_with_constructors):
    """Test that lowercase function calls are not treated as constructors."""
    source_file = SourceFile(
        path=sample_python_with_constructors,
        relative_path=Path("user_service.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )

    symbols = python_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_config = next(m for m in user_service.methods if m.name == "get_config")
    assert "dict" not in get_config.calls
