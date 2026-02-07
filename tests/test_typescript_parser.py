"""Tests for the TypeScript parser."""

import tempfile
from pathlib import Path

import pytest

from docmaker.models import FileCategory, Language, SourceFile
from docmaker.parser.typescript_parser import TypeScriptParser


@pytest.fixture
def typescript_parser():
    """Create a TypeScript parser instance."""
    return TypeScriptParser()


@pytest.fixture
def sample_typescript_class():
    """Create a sample TypeScript class file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write('''import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { User, UserDTO } from "./models";

/**
 * Service for managing users.
 */
@Injectable({
  providedIn: "root"
})
export class UserService {
  private readonly apiUrl = "/api/users";

  constructor(private http: HttpClient) {}

  /**
   * Get all users from the API.
   */
  async getUsers(): Promise<User[]> {
    return this.http.get<User[]>(this.apiUrl).toPromise();
  }

  getUser(id: number): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`);
  }

  createUser(user: UserDTO): Observable<User> {
    return this.http.post<User>(this.apiUrl, user);
  }

  static formatUser(user: User): string {
    return `${user.firstName} ${user.lastName}`;
  }
}
''')
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_typescript_interface():
    """Create a sample TypeScript interface file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write('''/**
 * Represents a user in the system.
 */
export interface User {
  id: number;
  firstName: string;
  lastName: string;
  email?: string;
  createdAt: Date;
}

export interface UserDTO extends Partial<User> {
  password: string;
}

interface InternalConfig {
  debug: boolean;
  timeout: number;
}
''')
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_typescript_functions():
    """Create a sample TypeScript file with various function styles."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write('''import { User } from "./models";

/**
 * Validates a user object.
 */
export function validateUser(user: User): boolean {
  return user.id > 0 && user.firstName.length > 0;
}

export async function fetchUsers(limit: number = 10): Promise<User[]> {
  const response = await fetch(`/api/users?limit=${limit}`);
  return response.json();
}

const formatName = (first: string, last: string): string => {
  return `${first} ${last}`;
};

export const processUser = async (user: User): Promise<void> => {
  console.log(user);
};
''')
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_typescript_imports():
    """Create a sample TypeScript file with various import styles."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write('''import React from "react";
import { useState, useEffect } from "react";
import * as Utils from "./utils";
import type { User } from "./models";
import "./styles.css";
''')
        f.flush()
        yield Path(f.name)


def test_parser_extracts_module_name(typescript_parser, sample_typescript_class):
    """Test that the parser extracts the module name."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    assert symbols.package is not None


def test_parser_extracts_imports(typescript_parser, sample_typescript_imports):
    """Test that the parser extracts import statements."""
    source_file = SourceFile(
        path=sample_typescript_imports,
        relative_path=Path("imports.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.FRONTEND,
    )

    symbols = typescript_parser.parse(source_file)

    assert len(symbols.imports) > 0

    import_modules = [i.module for i in symbols.imports]
    assert any("react" in m.lower() for m in import_modules)

    namespace_imports = [i for i in symbols.imports if i.is_wildcard]
    assert len(namespace_imports) == 1
    assert namespace_imports[0].alias == "Utils"


def test_parser_extracts_named_imports(typescript_parser, sample_typescript_class):
    """Test that the parser extracts named imports."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    import_modules = [i.module for i in symbols.imports]
    assert any("Injectable" in m for m in import_modules)
    assert any("HttpClient" in m for m in import_modules)


def test_parser_extracts_classes(typescript_parser, sample_typescript_class):
    """Test that the parser extracts class definitions."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    class_names = [c.name for c in symbols.classes]
    assert "UserService" in class_names


def test_parser_extracts_class_docstring(typescript_parser, sample_typescript_class):
    """Test that the parser extracts JSDoc comments."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    assert user_service.docstring is not None
    assert "managing users" in user_service.docstring


def test_parser_extracts_decorators(typescript_parser, sample_typescript_class):
    """Test that the parser extracts decorators."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    decorator_names = [a.name for a in user_service.annotations]
    assert "Injectable" in decorator_names


def test_parser_extracts_decorator_arguments(typescript_parser, sample_typescript_class):
    """Test that the parser extracts decorator arguments."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    injectable = next(a for a in user_service.annotations if a.name == "Injectable")
    assert "providedIn" in injectable.arguments


def test_parser_extracts_methods(typescript_parser, sample_typescript_class):
    """Test that the parser extracts method definitions."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    method_names = [m.name for m in user_service.methods]
    assert "getUsers" in method_names
    assert "getUser" in method_names
    assert "createUser" in method_names
    assert "formatUser" in method_names


def test_parser_extracts_method_parameters(typescript_parser, sample_typescript_class):
    """Test that the parser extracts method parameters."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_user = next(m for m in user_service.methods if m.name == "getUser")

    param_names = [p.name for p in get_user.parameters]
    assert "id" in param_names

    id_param = next(p for p in get_user.parameters if p.name == "id")
    assert id_param.type == "number"


def test_parser_extracts_return_types(typescript_parser, sample_typescript_class):
    """Test that the parser extracts return types."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_user = next(m for m in user_service.methods if m.name == "getUser")

    assert get_user.return_type is not None
    assert "Observable" in get_user.return_type


def test_parser_extracts_async_methods(typescript_parser, sample_typescript_class):
    """Test that the parser identifies async methods."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    get_users = next(m for m in user_service.methods if m.name == "getUsers")

    assert "async" in get_users.modifiers


def test_parser_extracts_interfaces(typescript_parser, sample_typescript_interface):
    """Test that the parser extracts interface definitions."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    interface_names = [c.name for c in symbols.classes]
    assert "User" in interface_names
    assert "UserDTO" in interface_names
    assert "InternalConfig" in interface_names


def test_parser_marks_interfaces(typescript_parser, sample_typescript_interface):
    """Test that interfaces are marked with the interface annotation."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_interface = next(c for c in symbols.classes if c.name == "User")
    assert "interface" in user_interface.modifiers


def test_parser_extracts_interface_docstring(typescript_parser, sample_typescript_interface):
    """Test that the parser extracts interface JSDoc comments."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_interface = next(c for c in symbols.classes if c.name == "User")
    assert user_interface.docstring is not None
    assert "user in the system" in user_interface.docstring


def test_parser_extracts_interface_extends(typescript_parser, sample_typescript_interface):
    """Test that the parser extracts interface inheritance."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_dto = next(c for c in symbols.classes if c.name == "UserDTO")
    assert len(user_dto.interfaces) > 0
    assert any("User" in i for i in user_dto.interfaces)


def test_parser_extracts_interface_fields(typescript_parser, sample_typescript_interface):
    """Test that the parser extracts interface properties."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_interface = next(c for c in symbols.classes if c.name == "User")
    field_names = [f.name for f in user_interface.fields]
    assert "id" in field_names
    assert "firstName" in field_names
    assert "email" in field_names


def test_parser_extracts_optional_fields(typescript_parser, sample_typescript_interface):
    """Test that the parser identifies optional fields."""
    source_file = SourceFile(
        path=sample_typescript_interface,
        relative_path=Path("models.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_interface = next(c for c in symbols.classes if c.name == "User")
    email_field = next(f for f in user_interface.fields if f.name == "email")
    assert email_field.type is not None
    assert "?" in email_field.type


def test_parser_extracts_module_functions(typescript_parser, sample_typescript_functions):
    """Test that the parser extracts module-level functions."""
    source_file = SourceFile(
        path=sample_typescript_functions,
        relative_path=Path("utils.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "validateUser" in function_names
    assert "fetchUsers" in function_names


def test_parser_extracts_exported_functions(typescript_parser, sample_typescript_functions):
    """Test that the parser identifies exported functions."""
    source_file = SourceFile(
        path=sample_typescript_functions,
        relative_path=Path("utils.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    validate_user = next(f for f in symbols.functions if f.name == "validateUser")
    assert "export" in validate_user.modifiers


def test_parser_extracts_function_docstring(typescript_parser, sample_typescript_functions):
    """Test that the parser extracts function JSDoc comments."""
    source_file = SourceFile(
        path=sample_typescript_functions,
        relative_path=Path("utils.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    validate_user = next(f for f in symbols.functions if f.name == "validateUser")
    assert validate_user.docstring is not None
    assert "Validates" in validate_user.docstring


def test_parser_extracts_arrow_functions(typescript_parser, sample_typescript_functions):
    """Test that the parser extracts arrow function declarations."""
    source_file = SourceFile(
        path=sample_typescript_functions,
        relative_path=Path("utils.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "formatName" in function_names or "processUser" in function_names


def test_parser_extracts_async_functions(typescript_parser, sample_typescript_functions):
    """Test that the parser identifies async functions."""
    source_file = SourceFile(
        path=sample_typescript_functions,
        relative_path=Path("utils.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    fetch_users = next(f for f in symbols.functions if f.name == "fetchUsers")
    assert "async" in fetch_users.modifiers


def test_parser_extracts_class_fields(typescript_parser, sample_typescript_class):
    """Test that the parser extracts class fields."""
    source_file = SourceFile(
        path=sample_typescript_class,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    field_names = [f.name for f in user_service.fields]
    assert "apiUrl" in field_names


@pytest.fixture
def sample_typescript_with_constructors():
    """Create a sample TypeScript file with constructor instantiation calls."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write('''import { User } from "./models";
import { Logger } from "./logger";

export class UserService {
  createUser(name: string): User {
    const logger = new Logger("UserService");
    const user = new User(name);
    return user;
  }
}

export function buildService(): UserService {
  const service = new UserService();
  return service;
}

const initApp = (): void => {
  const svc = new UserService();
};
''')
        f.flush()
        yield Path(f.name)


def test_parser_extracts_constructor_calls_in_methods(
    typescript_parser, sample_typescript_with_constructors
):
    """Test that the parser extracts new expressions from methods."""
    source_file = SourceFile(
        path=sample_typescript_with_constructors,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    user_service = next(c for c in symbols.classes if c.name == "UserService")
    create_user = next(m for m in user_service.methods if m.name == "createUser")
    assert "Logger" in create_user.calls
    assert "User" in create_user.calls


def test_parser_extracts_constructor_calls_in_functions(
    typescript_parser, sample_typescript_with_constructors
):
    """Test that the parser extracts new expressions from module functions."""
    source_file = SourceFile(
        path=sample_typescript_with_constructors,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    build_service = next(f for f in symbols.functions if f.name == "buildService")
    assert "UserService" in build_service.calls


def test_parser_extracts_constructor_calls_in_arrow_functions(
    typescript_parser, sample_typescript_with_constructors
):
    """Test that the parser extracts new expressions from arrow functions."""
    source_file = SourceFile(
        path=sample_typescript_with_constructors,
        relative_path=Path("user.service.ts"),
        language=Language.TYPESCRIPT,
        category=FileCategory.BACKEND,
    )

    symbols = typescript_parser.parse(source_file)

    init_app = next(f for f in symbols.functions if f.name == "initApp")
    assert "UserService" in init_app.calls


def test_parser_handles_tsx_files(typescript_parser):
    """Test that the parser can handle TSX files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsx", delete=False) as f:
        f.write('''import React from "react";

interface Props {
  name: string;
}

export function Greeting({ name }: Props): JSX.Element {
  return <h1>Hello, {name}!</h1>;
}
''')
        f.flush()
        tsx_path = Path(f.name)

    source_file = SourceFile(
        path=tsx_path,
        relative_path=Path("Greeting.tsx"),
        language=Language.TYPESCRIPT,
        category=FileCategory.FRONTEND,
    )

    symbols = typescript_parser.parse(source_file)

    function_names = [f.name for f in symbols.functions]
    assert "Greeting" in function_names


