"""Tests for the JavaScript parser."""

import tempfile
from pathlib import Path

import pytest
from docmaker.parser.javascript_parser import JavaScriptParser

from docmaker.models import FileCategory, Language, SourceFile


@pytest.fixture
def js_parser():
    """Create a JavaScript parser instance."""
    return JavaScriptParser()


# --- Fixtures: sample JS source files ---


@pytest.fixture
def sample_js_class():
    """Create a sample JavaScript file with a class definition."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""/**
 * Manages user data and operations.
 */
class UserManager {
  constructor(db) {
    this.db = db;
    this.cache = {};
  }

  /**
   * Find a user by their ID.
   */
  async findById(id) {
    if (this.cache[id]) return this.cache[id];
    const user = await this.db.query("SELECT * FROM users WHERE id = ?", [id]);
    this.cache[id] = user;
    return user;
  }

  static create(name, email) {
    return { name, email, createdAt: new Date() };
  }

  get count() {
    return Object.keys(this.cache).length;
  }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_class_extends():
    """Create a sample JavaScript file with class inheritance."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""class Animal {
  constructor(name) {
    this.name = name;
  }

  speak() {
    return this.name + " makes a noise.";
  }
}

class Dog extends Animal {
  constructor(name, breed) {
    super(name);
    this.breed = breed;
  }

  speak() {
    return this.name + " barks.";
  }

  fetch(item) {
    return this.name + " fetches " + item;
  }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_functions():
    """Create a sample JavaScript file with function declarations."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""/**
 * Calculate the sum of two numbers.
 */
function add(a, b) {
  return a + b;
}

async function fetchData(url, options) {
  const response = await fetch(url, options);
  return response.json();
}

function* generateIds(start) {
  let id = start;
  while (true) {
    yield id++;
  }
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_arrow_functions():
    """Create a sample JavaScript file with arrow function expressions."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""const multiply = (a, b) => {
  return a * b;
};

const square = (x) => x * x;

const greet = (name) => {
  const greeting = "Hello, " + name;
  return greeting;
};

const identity = x => x;
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_es_imports():
    """Create a sample JavaScript file with ES module imports."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""import React from "react";
import { useState, useEffect } from "react";
import * as Utils from "./utils";
import "./styles.css";

function App() {
  return null;
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_es_exports():
    """Create a sample JavaScript file with ES module exports."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""/**
 * Format a name for display.
 */
export function formatName(first, last) {
  return first + " " + last;
}

export class Logger {
  constructor(prefix) {
    this.prefix = prefix;
  }

  log(message) {
    console.log(this.prefix + ": " + message);
  }
}

export default function main() {
  return "main";
}

export const VERSION = "1.0.0";
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_commonjs_require():
    """Create a sample JavaScript file with CommonJS require patterns."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""const fs = require("fs");
const path = require("path");
const { readFile, writeFile } = require("fs/promises");
const { join, resolve } = require("path");

function readConfig(configPath) {
  const content = fs.readFileSync(configPath, "utf-8");
  return JSON.parse(content);
}

module.exports = { readConfig };
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_destructuring_imports():
    """Create a sample JavaScript file with destructuring import patterns."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""import { useState, useEffect, useCallback } from "react";
import { connect, useSelector, useDispatch } from "react-redux";
import {
  Button,
  TextField,
  Dialog,
} from "@mui/material";
const { EventEmitter } = require("events");
const { createServer, createConnection } = require("net");

function Component() {
  return null;
}
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_js_jsx():
    """Create a sample JSX file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsx", delete=False) as f:
        f.write("""import React from "react";

/**
 * A greeting component.
 */
function Greeting({ name }) {
  return <h1>Hello, {name}!</h1>;
}

export default Greeting;
""")
        f.flush()
        yield Path(f.name)


def _make_source_file(path, relative_name="test.js"):
    """Helper to create a SourceFile from a path."""
    return SourceFile(
        path=path,
        relative_path=Path(relative_name),
        language=Language.JAVASCRIPT,
        category=FileCategory.FRONTEND,
    )


# --- Tests: parser basics ---


def test_parser_language(js_parser):
    """Test that the parser reports JavaScript as its language."""
    assert js_parser.language == Language.JAVASCRIPT


def test_parser_can_parse_js(js_parser):
    """Test that the parser accepts JavaScript source files."""
    sf = SourceFile(
        path=Path("/tmp/test.js"),
        relative_path=Path("test.js"),
        language=Language.JAVASCRIPT,
        category=FileCategory.FRONTEND,
    )
    assert js_parser.can_parse(sf) is True


def test_parser_rejects_non_js(js_parser):
    """Test that the parser rejects non-JavaScript source files."""
    sf = SourceFile(
        path=Path("/tmp/test.py"),
        relative_path=Path("test.py"),
        language=Language.PYTHON,
        category=FileCategory.BACKEND,
    )
    assert js_parser.can_parse(sf) is False


# --- Tests: class extraction ---


def test_parser_extracts_class(js_parser, sample_js_class):
    """Test that the parser extracts class definitions."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    class_names = [c.name for c in symbols.classes]
    assert "UserManager" in class_names


def test_parser_extracts_class_docstring(js_parser, sample_js_class):
    """Test that the parser extracts JSDoc comments on classes."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    assert user_manager.docstring is not None
    assert "user data" in user_manager.docstring.lower()


def test_parser_extracts_class_methods(js_parser, sample_js_class):
    """Test that the parser extracts methods from a class."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    method_names = [m.name for m in user_manager.methods]
    assert "constructor" in method_names
    assert "findById" in method_names
    assert "create" in method_names


def test_parser_extracts_static_method(js_parser, sample_js_class):
    """Test that the parser identifies static methods."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    create_method = next(m for m in user_manager.methods if m.name == "create")
    assert "static" in create_method.modifiers


def test_parser_extracts_async_method(js_parser, sample_js_class):
    """Test that the parser identifies async methods."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    find_by_id = next(m for m in user_manager.methods if m.name == "findById")
    assert "async" in find_by_id.modifiers


def test_parser_extracts_method_docstring(js_parser, sample_js_class):
    """Test that the parser extracts JSDoc comments on methods."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    find_by_id = next(m for m in user_manager.methods if m.name == "findById")
    assert find_by_id.docstring is not None
    assert "Find a user" in find_by_id.docstring


def test_parser_extracts_method_parameters(js_parser, sample_js_class):
    """Test that the parser extracts method parameters."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    create = next(m for m in user_manager.methods if m.name == "create")
    param_names = [p.name for p in create.parameters]
    assert "name" in param_names
    assert "email" in param_names


def test_parser_extracts_class_inheritance(js_parser, sample_js_class_extends):
    """Test that the parser extracts class extends clauses."""
    symbols = js_parser.parse(_make_source_file(sample_js_class_extends))

    dog = next(c for c in symbols.classes if c.name == "Dog")
    assert dog.superclass == "Animal"


def test_parser_extracts_multiple_classes(js_parser, sample_js_class_extends):
    """Test that the parser extracts multiple classes from one file."""
    symbols = js_parser.parse(_make_source_file(sample_js_class_extends))

    class_names = [c.name for c in symbols.classes]
    assert "Animal" in class_names
    assert "Dog" in class_names


# --- Tests: function declarations ---


def test_parser_extracts_function_declarations(js_parser, sample_js_functions):
    """Test that the parser extracts function declarations."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    function_names = [f.name for f in symbols.functions]
    assert "add" in function_names
    assert "fetchData" in function_names


def test_parser_extracts_function_docstring(js_parser, sample_js_functions):
    """Test that the parser extracts JSDoc on function declarations."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    add_func = next(f for f in symbols.functions if f.name == "add")
    assert add_func.docstring is not None
    assert "sum" in add_func.docstring.lower()


def test_parser_extracts_function_parameters(js_parser, sample_js_functions):
    """Test that the parser extracts function parameters."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    add_func = next(f for f in symbols.functions if f.name == "add")
    param_names = [p.name for p in add_func.parameters]
    assert "a" in param_names
    assert "b" in param_names


def test_parser_extracts_async_function(js_parser, sample_js_functions):
    """Test that the parser identifies async function declarations."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    fetch_data = next(f for f in symbols.functions if f.name == "fetchData")
    assert "async" in fetch_data.modifiers


def test_parser_extracts_async_function_parameters(js_parser, sample_js_functions):
    """Test that async function parameters are extracted."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    fetch_data = next(f for f in symbols.functions if f.name == "fetchData")
    param_names = [p.name for p in fetch_data.parameters]
    assert "url" in param_names
    assert "options" in param_names


def test_parser_extracts_generator_function(js_parser, sample_js_functions):
    """Test that the parser extracts generator function declarations."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    function_names = [f.name for f in symbols.functions]
    assert "generateIds" in function_names


# --- Tests: arrow functions ---


def test_parser_extracts_arrow_functions(js_parser, sample_js_arrow_functions):
    """Test that the parser extracts arrow function expressions assigned to const."""
    symbols = js_parser.parse(_make_source_file(sample_js_arrow_functions))

    function_names = [f.name for f in symbols.functions]
    assert "multiply" in function_names
    assert "square" in function_names
    assert "greet" in function_names


def test_parser_extracts_arrow_function_parameters(js_parser, sample_js_arrow_functions):
    """Test that the parser extracts arrow function parameters."""
    symbols = js_parser.parse(_make_source_file(sample_js_arrow_functions))

    multiply = next(f for f in symbols.functions if f.name == "multiply")
    param_names = [p.name for p in multiply.parameters]
    assert "a" in param_names
    assert "b" in param_names


def test_parser_extracts_single_param_arrow(js_parser, sample_js_arrow_functions):
    """Test that the parser handles arrow functions with a single non-parenthesized param."""
    symbols = js_parser.parse(_make_source_file(sample_js_arrow_functions))

    function_names = [f.name for f in symbols.functions]
    assert "identity" in function_names

    identity = next(f for f in symbols.functions if f.name == "identity")
    param_names = [p.name for p in identity.parameters]
    assert "x" in param_names


# --- Tests: ES module imports ---


def test_parser_extracts_es_default_import(js_parser, sample_js_es_imports):
    """Test that the parser extracts default imports."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_imports))

    assert len(symbols.imports) > 0
    import_modules = [i.module for i in symbols.imports]
    assert any("react" in m.lower() for m in import_modules)


def test_parser_extracts_es_named_imports(js_parser, sample_js_es_imports):
    """Test that the parser extracts named imports."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_imports))

    import_modules = [i.module for i in symbols.imports]
    assert any("useState" in m for m in import_modules)
    assert any("useEffect" in m for m in import_modules)


def test_parser_extracts_es_namespace_import(js_parser, sample_js_es_imports):
    """Test that the parser extracts namespace (wildcard) imports."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_imports))

    wildcard_imports = [i for i in symbols.imports if i.is_wildcard]
    assert len(wildcard_imports) >= 1
    assert any(i.alias == "Utils" for i in wildcard_imports)


def test_parser_extracts_es_side_effect_import(js_parser, sample_js_es_imports):
    """Test that the parser extracts side-effect-only imports."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_imports))

    import_modules = [i.module for i in symbols.imports]
    assert any("styles.css" in m for m in import_modules)


# --- Tests: ES module exports ---


def test_parser_extracts_exported_function(js_parser, sample_js_es_exports):
    """Test that the parser identifies exported function declarations."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_exports))

    format_name = next(f for f in symbols.functions if f.name == "formatName")
    assert "export" in format_name.modifiers


def test_parser_extracts_exported_function_docstring(js_parser, sample_js_es_exports):
    """Test that JSDoc on exported functions is extracted."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_exports))

    format_name = next(f for f in symbols.functions if f.name == "formatName")
    assert format_name.docstring is not None
    assert "Format" in format_name.docstring


def test_parser_extracts_exported_class(js_parser, sample_js_es_exports):
    """Test that the parser identifies exported classes."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_exports))

    logger_class = next(c for c in symbols.classes if c.name == "Logger")
    assert "export" in logger_class.modifiers


def test_parser_extracts_exported_class_methods(js_parser, sample_js_es_exports):
    """Test that methods of exported classes are extracted."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_exports))

    logger_class = next(c for c in symbols.classes if c.name == "Logger")
    method_names = [m.name for m in logger_class.methods]
    assert "log" in method_names


def test_parser_extracts_default_export_function(js_parser, sample_js_es_exports):
    """Test that the parser extracts default-exported functions."""
    symbols = js_parser.parse(_make_source_file(sample_js_es_exports))

    function_names = [f.name for f in symbols.functions]
    assert "main" in function_names


# --- Tests: CommonJS require ---


def test_parser_extracts_commonjs_require(js_parser, sample_js_commonjs_require):
    """Test that the parser extracts CommonJS require() calls."""
    symbols = js_parser.parse(_make_source_file(sample_js_commonjs_require))

    assert len(symbols.imports) > 0
    import_modules = [i.module for i in symbols.imports]
    assert any("fs" in m for m in import_modules)
    assert any("path" in m for m in import_modules)


def test_parser_extracts_commonjs_destructured_require(js_parser, sample_js_commonjs_require):
    """Test that the parser extracts destructured CommonJS require()."""
    symbols = js_parser.parse(_make_source_file(sample_js_commonjs_require))

    import_modules = [i.module for i in symbols.imports]
    assert any("readFile" in m for m in import_modules)
    assert any("writeFile" in m for m in import_modules)


def test_parser_extracts_functions_alongside_require(js_parser, sample_js_commonjs_require):
    """Test that functions in CommonJS files are still extracted."""
    symbols = js_parser.parse(_make_source_file(sample_js_commonjs_require))

    function_names = [f.name for f in symbols.functions]
    assert "readConfig" in function_names


# --- Tests: destructuring imports ---


def test_parser_extracts_multiple_destructured_es_imports(
    js_parser, sample_js_destructuring_imports
):
    """Test extraction of multiple named imports from a single module."""
    symbols = js_parser.parse(_make_source_file(sample_js_destructuring_imports))

    import_modules = [i.module for i in symbols.imports]
    assert any("useState" in m for m in import_modules)
    assert any("useEffect" in m for m in import_modules)
    assert any("useCallback" in m for m in import_modules)


def test_parser_extracts_multiline_destructured_imports(js_parser, sample_js_destructuring_imports):
    """Test extraction of multi-line destructured imports."""
    symbols = js_parser.parse(_make_source_file(sample_js_destructuring_imports))

    import_modules = [i.module for i in symbols.imports]
    assert any("Button" in m for m in import_modules)
    assert any("TextField" in m for m in import_modules)
    assert any("Dialog" in m for m in import_modules)


def test_parser_extracts_destructured_commonjs_require(js_parser, sample_js_destructuring_imports):
    """Test extraction of destructured CommonJS require() calls."""
    symbols = js_parser.parse(_make_source_file(sample_js_destructuring_imports))

    import_modules = [i.module for i in symbols.imports]
    assert any("EventEmitter" in m for m in import_modules)
    assert any("createServer" in m for m in import_modules)
    assert any("createConnection" in m for m in import_modules)


# --- Tests: module name ---


def test_parser_extracts_module_name(js_parser, sample_js_class):
    """Test that the parser extracts the module name from file path."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    assert symbols.package is not None


# --- Tests: JSX support ---


def test_parser_handles_jsx_files(js_parser, sample_js_jsx):
    """Test that the parser can handle JSX files."""
    sf = SourceFile(
        path=sample_js_jsx,
        relative_path=Path("Greeting.jsx"),
        language=Language.JAVASCRIPT,
        category=FileCategory.FRONTEND,
    )

    symbols = js_parser.parse(sf)

    function_names = [f.name for f in symbols.functions]
    assert "Greeting" in function_names


def test_parser_extracts_jsx_docstring(js_parser, sample_js_jsx):
    """Test that JSDoc is extracted from JSX component functions."""
    sf = SourceFile(
        path=sample_js_jsx,
        relative_path=Path("Greeting.jsx"),
        language=Language.JAVASCRIPT,
        category=FileCategory.FRONTEND,
    )

    symbols = js_parser.parse(sf)

    greeting = next(f for f in symbols.functions if f.name == "Greeting")
    assert greeting.docstring is not None
    assert "greeting" in greeting.docstring.lower()


# --- Tests: line numbers ---


def test_parser_records_line_numbers(js_parser, sample_js_functions):
    """Test that the parser records correct line numbers for functions."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    add_func = next(f for f in symbols.functions if f.name == "add")
    assert add_func.line_number > 0
    assert add_func.end_line >= add_func.line_number


def test_parser_records_class_line_numbers(js_parser, sample_js_class):
    """Test that the parser records correct line numbers for classes."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    assert user_manager.line_number > 0
    assert user_manager.end_line > user_manager.line_number


# --- Tests: source code capture ---


def test_parser_captures_function_source(js_parser, sample_js_functions):
    """Test that the parser captures function source code."""
    symbols = js_parser.parse(_make_source_file(sample_js_functions))

    add_func = next(f for f in symbols.functions if f.name == "add")
    assert "return a + b" in add_func.source_code


def test_parser_captures_class_source(js_parser, sample_js_class):
    """Test that the parser captures class source code."""
    symbols = js_parser.parse(_make_source_file(sample_js_class))

    user_manager = next(c for c in symbols.classes if c.name == "UserManager")
    assert "class UserManager" in user_manager.source_code
    assert "findById" in user_manager.source_code
