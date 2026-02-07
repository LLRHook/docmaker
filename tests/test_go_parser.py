"""Tests for the Go parser."""

import tempfile
from pathlib import Path

import pytest

# The Go parser is expected to be implemented at this path.
# Tests are written TDD-style; they will pass once go_parser.py exists.
from docmaker.parser.go_parser import GoParser

from docmaker.models import FileCategory, Language, SourceFile


@pytest.fixture
def go_parser():
    """Create a Go parser instance."""
    return GoParser()


# ---------------------------------------------------------------------------
# Sample Go source fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_go_struct():
    """Create a sample Go file with a struct, methods, and fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package user

import (
	"fmt"
	"time"
)

// User represents a user in the system.
type User struct {
	ID        int
	FirstName string
	LastName  string
	Email     string
	CreatedAt time.Time
}

// FullName returns the user's full name.
func (u *User) FullName() string {
	return fmt.Sprintf("%s %s", u.FirstName, u.LastName)
}

// SetEmail sets the user's email address.
func (u *User) SetEmail(email string) error {
	u.Email = email
	return nil
}

// String implements the Stringer interface.
func (u User) String() string {
	return u.FullName()
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_interface():
    """Create a sample Go file with interfaces."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package repository

// Repository defines the interface for data access.
type Repository interface {
	FindByID(id int) (interface{}, error)
	FindAll() ([]interface{}, error)
	Save(entity interface{}) error
	Delete(id int) error
}

// ReadOnlyRepository defines a read-only data access interface.
type ReadOnlyRepository interface {
	FindByID(id int) (interface{}, error)
	FindAll() ([]interface{}, error)
}

type internalCache interface {
	Get(key string) (interface{}, bool)
	Set(key string, value interface{})
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_functions():
    """Create a sample Go file with top-level functions."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package utils

import (
	"strings"
	"unicode"
)

// FormatName formats a first and last name.
func FormatName(first, last string) string {
	return strings.TrimSpace(first + " " + last)
}

// IsValidEmail checks whether an email address is valid.
func IsValidEmail(email string) bool {
	return strings.Contains(email, "@")
}

func capitalize(s string) string {
	if len(s) == 0 {
		return s
	}
	runes := []rune(s)
	runes[0] = unicode.ToUpper(runes[0])
	return string(runes)
}

// ProcessItems processes a slice of items and returns the count.
func ProcessItems(items []string, limit int) (int, error) {
	return len(items), nil
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_imports():
    """Create a sample Go file with various import styles."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package main

import (
	"fmt"
	"os"

	"github.com/example/project/internal/config"
	"github.com/example/project/pkg/utils"

	log "github.com/sirupsen/logrus"
	. "github.com/onsi/gomega"
)

func main() {
	fmt.Println("hello")
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_single_import():
    """Create a sample Go file with a single import (no parens)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package simple

import "fmt"

func Hello() {
	fmt.Println("hello")
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_embedded_types():
    """Create a sample Go file with embedded (composed) types."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package models

import "sync"

// Base provides common fields for all models.
type Base struct {
	ID        int
	CreatedAt string
}

// Lockable adds mutex-based locking.
type Lockable struct {
	sync.Mutex
}

// Admin embeds User and adds admin-specific fields.
type Admin struct {
	Base
	Lockable
	Role       string
	Privileges []string
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_method_receivers():
    """Create a sample Go file with both pointer and value receivers."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package counter

// Counter tracks a count value.
type Counter struct {
	value int
}

// Increment adds one to the counter (pointer receiver).
func (c *Counter) Increment() {
	c.value++
}

// Value returns the current count (value receiver).
func (c Counter) Value() int {
	return c.value
}

// Reset resets the counter to zero (pointer receiver).
func (c *Counter) Reset() {
	c.value = 0
}

// NewCounter creates a new Counter.
func NewCounter() *Counter {
	return &Counter{value: 0}
}
"""
        )
        f.flush()
        yield Path(f.name)


@pytest.fixture
def sample_go_interface_embedding():
    """Create a sample Go file with embedded interfaces."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
        f.write(
            """\
package io

// Reader is the basic read interface.
type Reader interface {
	Read(p []byte) (n int, err error)
}

// Writer is the basic write interface.
type Writer interface {
	Write(p []byte) (n int, err error)
}

// ReadWriter combines Reader and Writer.
type ReadWriter interface {
	Reader
	Writer
}

// ReadWriteCloser adds Close to ReadWriter.
type ReadWriteCloser interface {
	ReadWriter
	Close() error
}
"""
        )
        f.flush()
        yield Path(f.name)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_source(path: Path, rel: str = "source.go") -> SourceFile:
    return SourceFile(
        path=path,
        relative_path=Path(rel),
        language=Language.GO,
        category=FileCategory.BACKEND,
    )


# ===================================================================
# 1. Struct extraction
# ===================================================================


class TestStructExtraction:
    """Tests for Go struct extraction."""

    def test_extracts_struct_as_class(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        class_names = [c.name for c in symbols.classes]
        assert "User" in class_names

    def test_struct_has_correct_line_numbers(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        assert user.line_number > 0
        assert user.end_line >= user.line_number

    def test_struct_has_docstring(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        assert user.docstring is not None
        assert "user in the system" in user.docstring

    def test_struct_has_fields(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        field_names = [f.name for f in user.fields]
        assert "ID" in field_names
        assert "FirstName" in field_names
        assert "LastName" in field_names
        assert "Email" in field_names
        assert "CreatedAt" in field_names

    def test_struct_fields_have_types(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        id_field = next(f for f in user.fields if f.name == "ID")
        assert id_field.type == "int"

    def test_struct_field_line_numbers(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        for field in user.fields:
            assert field.line_number > 0

    def test_struct_source_code_captured(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        assert user.source_code != ""
        assert "struct" in user.source_code


# ===================================================================
# 2. Interface extraction
# ===================================================================


class TestInterfaceExtraction:
    """Tests for Go interface extraction."""

    def test_extracts_interfaces(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        class_names = [c.name for c in symbols.classes]
        assert "Repository" in class_names
        assert "ReadOnlyRepository" in class_names
        assert "internalCache" in class_names

    def test_interface_has_interface_modifier(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        repo = next(c for c in symbols.classes if c.name == "Repository")
        assert "interface" in repo.modifiers

    def test_interface_has_docstring(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        repo = next(c for c in symbols.classes if c.name == "Repository")
        assert repo.docstring is not None
        assert "data access" in repo.docstring

    def test_interface_has_methods(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        repo = next(c for c in symbols.classes if c.name == "Repository")
        method_names = [m.name for m in repo.methods]
        assert "FindByID" in method_names
        assert "FindAll" in method_names
        assert "Save" in method_names
        assert "Delete" in method_names

    def test_interface_method_parameters(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        repo = next(c for c in symbols.classes if c.name == "Repository")
        find = next(m for m in repo.methods if m.name == "FindByID")
        param_names = [p.name for p in find.parameters]
        assert "id" in param_names

    def test_interface_method_return_types(self, go_parser, sample_go_interface):
        symbols = go_parser.parse(_make_source(sample_go_interface))
        repo = next(c for c in symbols.classes if c.name == "Repository")
        delete = next(m for m in repo.methods if m.name == "Delete")
        assert delete.return_type is not None
        assert "error" in delete.return_type


# ===================================================================
# 3. Method receivers
# ===================================================================


class TestMethodReceivers:
    """Tests for Go method receiver extraction."""

    def test_methods_attached_to_struct(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        method_names = [m.name for m in user.methods]
        assert "FullName" in method_names
        assert "SetEmail" in method_names
        assert "String" in method_names

    def test_method_has_docstring(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        full_name = next(m for m in user.methods if m.name == "FullName")
        assert full_name.docstring is not None
        assert "full name" in full_name.docstring

    def test_method_has_parameters(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        set_email = next(m for m in user.methods if m.name == "SetEmail")
        param_names = [p.name for p in set_email.parameters]
        assert "email" in param_names

    def test_method_has_return_type(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        full_name = next(m for m in user.methods if m.name == "FullName")
        assert full_name.return_type is not None
        assert "string" in full_name.return_type

    def test_pointer_and_value_receivers(self, go_parser, sample_go_method_receivers):
        """Both pointer (*Counter) and value (Counter) receivers attach to the struct."""
        symbols = go_parser.parse(_make_source(sample_go_method_receivers))
        counter = next(c for c in symbols.classes if c.name == "Counter")
        method_names = [m.name for m in counter.methods]
        assert "Increment" in method_names
        assert "Value" in method_names
        assert "Reset" in method_names

    def test_standalone_function_not_in_struct(self, go_parser, sample_go_method_receivers):
        """NewCounter is a top-level function, not a method on Counter."""
        symbols = go_parser.parse(_make_source(sample_go_method_receivers))
        counter = next(c for c in symbols.classes if c.name == "Counter")
        method_names = [m.name for m in counter.methods]
        assert "NewCounter" not in method_names
        func_names = [f.name for f in symbols.functions]
        assert "NewCounter" in func_names

    def test_method_line_numbers(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        user = next(c for c in symbols.classes if c.name == "User")
        for method in user.methods:
            assert method.line_number > 0
            assert method.end_line >= method.line_number


# ===================================================================
# 4. Function extraction
# ===================================================================


class TestFunctionExtraction:
    """Tests for Go top-level function extraction."""

    def test_extracts_top_level_functions(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        func_names = [f.name for f in symbols.functions]
        assert "FormatName" in func_names
        assert "IsValidEmail" in func_names
        assert "capitalize" in func_names
        assert "ProcessItems" in func_names

    def test_function_has_docstring(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        fmt_fn = next(f for f in symbols.functions if f.name == "FormatName")
        assert fmt_fn.docstring is not None
        assert "formats" in fmt_fn.docstring.lower()

    def test_unexported_function_no_docstring(self, go_parser, sample_go_functions):
        """capitalize has no doc comment."""
        symbols = go_parser.parse(_make_source(sample_go_functions))
        cap_fn = next(f for f in symbols.functions if f.name == "capitalize")
        assert cap_fn.docstring is None

    def test_function_parameters(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        fmt_fn = next(f for f in symbols.functions if f.name == "FormatName")
        param_names = [p.name for p in fmt_fn.parameters]
        assert "first" in param_names
        assert "last" in param_names

    def test_function_parameter_types(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        fmt_fn = next(f for f in symbols.functions if f.name == "FormatName")
        for param in fmt_fn.parameters:
            assert param.type is not None
            assert "string" in param.type

    def test_function_return_type(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        fmt_fn = next(f for f in symbols.functions if f.name == "FormatName")
        assert fmt_fn.return_type is not None
        assert "string" in fmt_fn.return_type

    def test_function_multiple_return_types(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        proc = next(f for f in symbols.functions if f.name == "ProcessItems")
        assert proc.return_type is not None
        assert "int" in proc.return_type
        assert "error" in proc.return_type

    def test_function_line_numbers(self, go_parser, sample_go_functions):
        symbols = go_parser.parse(_make_source(sample_go_functions))
        for func in symbols.functions:
            assert func.line_number > 0
            assert func.end_line >= func.line_number


# ===================================================================
# 5. Import extraction
# ===================================================================


class TestImportExtraction:
    """Tests for Go import extraction."""

    def test_extracts_grouped_imports(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        assert len(symbols.imports) > 0
        modules = [i.module for i in symbols.imports]
        assert "fmt" in modules
        assert "os" in modules

    def test_extracts_third_party_imports(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        modules = [i.module for i in symbols.imports]
        assert any("github.com/example/project" in m for m in modules)

    def test_extracts_aliased_import(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        log_import = next(
            (i for i in symbols.imports if "logrus" in i.module), None
        )
        assert log_import is not None
        assert log_import.alias == "log"

    def test_extracts_dot_import(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        dot_import = next(
            (i for i in symbols.imports if "gomega" in i.module), None
        )
        assert dot_import is not None
        assert dot_import.is_wildcard is True

    def test_extracts_single_import(self, go_parser, sample_go_single_import):
        symbols = go_parser.parse(_make_source(sample_go_single_import))
        assert len(symbols.imports) == 1
        assert symbols.imports[0].module == "fmt"

    def test_import_line_numbers(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        for imp in symbols.imports:
            assert imp.line_number > 0


# ===================================================================
# 6. Embedded types
# ===================================================================


class TestEmbeddedTypes:
    """Tests for Go embedded (composed) types."""

    def test_struct_embedded_types(self, go_parser, sample_go_embedded_types):
        symbols = go_parser.parse(_make_source(sample_go_embedded_types))
        admin = next(c for c in symbols.classes if c.name == "Admin")
        assert len(admin.interfaces) > 0
        assert "Base" in admin.interfaces
        assert "Lockable" in admin.interfaces

    def test_embedded_qualified_type(self, go_parser, sample_go_embedded_types):
        """sync.Mutex is an embedded type from an external package."""
        symbols = go_parser.parse(_make_source(sample_go_embedded_types))
        lockable = next(c for c in symbols.classes if c.name == "Lockable")
        assert len(lockable.interfaces) > 0
        embedded = lockable.interfaces
        assert any("Mutex" in e for e in embedded)

    def test_interface_embedding(self, go_parser, sample_go_interface_embedding):
        symbols = go_parser.parse(_make_source(sample_go_interface_embedding))
        rw = next(c for c in symbols.classes if c.name == "ReadWriter")
        assert "Reader" in rw.interfaces
        assert "Writer" in rw.interfaces

    def test_deep_interface_embedding(self, go_parser, sample_go_interface_embedding):
        symbols = go_parser.parse(_make_source(sample_go_interface_embedding))
        rwc = next(c for c in symbols.classes if c.name == "ReadWriteCloser")
        assert "ReadWriter" in rwc.interfaces


# ===================================================================
# 7. Package extraction
# ===================================================================


class TestPackageExtraction:
    """Tests for Go package name extraction."""

    def test_extracts_package_name(self, go_parser, sample_go_struct):
        symbols = go_parser.parse(_make_source(sample_go_struct))
        assert symbols.package == "user"

    def test_extracts_main_package(self, go_parser, sample_go_imports):
        symbols = go_parser.parse(_make_source(sample_go_imports))
        assert symbols.package == "main"


# ===================================================================
# 8. Parser metadata
# ===================================================================


class TestParserMetadata:
    """Tests for GoParser metadata and capabilities."""

    def test_language_is_go(self, go_parser):
        assert go_parser.language == Language.GO

    def test_can_parse_go_file(self, go_parser):
        source = SourceFile(
            path=Path("example.go"),
            relative_path=Path("example.go"),
            language=Language.GO,
        )
        assert go_parser.can_parse(source) is True

    def test_cannot_parse_non_go_file(self, go_parser):
        source = SourceFile(
            path=Path("example.py"),
            relative_path=Path("example.py"),
            language=Language.PYTHON,
        )
        assert go_parser.can_parse(source) is False
