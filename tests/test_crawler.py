"""Tests for the file crawler."""

import builtins
import os
import tempfile
from pathlib import Path

import pytest

from docmaker.config import DocmakerConfig
from docmaker.crawler import FileCrawler
from docmaker.models import FileCategory, Language


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        (root / "src" / "main" / "java" / "com" / "example").mkdir(parents=True)
        (root / "src" / "test" / "java" / "com" / "example").mkdir(parents=True)
        (root / "node_modules" / "package").mkdir(parents=True)

        controller = root / "src" / "main" / "java" / "com" / "example" / "UserController.java"
        controller.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return null;
    }
}
""")

        service = root / "src" / "main" / "java" / "com" / "example" / "UserService.java"
        service.write_text("""
package com.example;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    public User findById(Long id) {
        return null;
    }
}
""")

        test_file = root / "src" / "test" / "java" / "com" / "example" / "UserControllerTest.java"
        test_file.write_text("""
package com.example;

import org.junit.jupiter.api.Test;

public class UserControllerTest {
    @Test
    void testGetUser() {}
}
""")

        node_file = root / "node_modules" / "package" / "index.js"
        node_file.write_text("module.exports = {};")

        gitignore = root / ".gitignore"
        gitignore.write_text("*.log\ntarget/\n")

        yield root


def test_crawler_finds_java_files(temp_repo):
    """Test that the crawler finds Java files."""
    config = DocmakerConfig()
    config.source_dir = temp_repo
    config.llm.enabled = False

    crawler = FileCrawler(config)
    files = crawler.crawl()

    java_files = [f for f in files if f.language == Language.JAVA]
    assert len(java_files) == 3


def test_crawler_ignores_node_modules(temp_repo):
    """Test that node_modules is ignored."""
    config = DocmakerConfig()
    config.source_dir = temp_repo
    config.llm.enabled = False

    crawler = FileCrawler(config)
    files = crawler.crawl()

    paths = [str(f.relative_path) for f in files]
    assert not any("node_modules" in p for p in paths)


def test_crawler_categorizes_test_files(temp_repo):
    """Test that test files are categorized correctly."""
    config = DocmakerConfig()
    config.source_dir = temp_repo
    config.llm.enabled = False

    crawler = FileCrawler(config)
    files = crawler.crawl()

    test_files = [f for f in files if f.category == FileCategory.TEST]
    assert len(test_files) >= 1


def test_crawler_categorizes_backend_files(temp_repo):
    """Test that backend files are categorized correctly."""
    config = DocmakerConfig()
    config.source_dir = temp_repo
    config.llm.enabled = False

    crawler = FileCrawler(config)
    files = crawler.crawl()

    backend_files = [f for f in files if f.category == FileCategory.BACKEND]
    assert len(backend_files) >= 1


@pytest.mark.parametrize("ancestor", ["test_checkout", "configuration", "frontend", "backend"])
def test_crawler_categories_do_not_depend_on_checkout_location(temp_repo, ancestor):
    root = temp_repo / ancestor / "project"
    root.mkdir(parents=True)
    (root / "App.java").write_text("class App {}")
    (root / "tests").mkdir()
    (root / "tests" / "AppTest.java").write_text("class AppTest {}")
    config = DocmakerConfig(source_dir=root)
    config.llm.enabled = False

    files = {file.relative_path: file for file in FileCrawler(config).crawl()}

    assert files[Path("App.java")].category == FileCategory.UNKNOWN
    assert files[Path("tests/AppTest.java")].category == FileCategory.TEST


def test_crawler_does_not_ingest_symlinks_outside_source_directory(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    external = tmp_path / "private.java"
    external.write_text("class Private {}")
    (root / "External.java").symlink_to(external)
    (root / "App.java").write_text("class App {}")
    (root / "Alias.java").symlink_to(root / "App.java")
    config = DocmakerConfig(source_dir=root)

    files = FileCrawler(config).crawl()

    assert {file.relative_path for file in files} == {Path("App.java"), Path("Alias.java")}


def test_crawler_does_not_follow_symlinks_to_ignored_files(tmp_path):
    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    ignored = ignored_dir / "Private.java"
    ignored.write_text("class Private {}")
    (tmp_path / "Alias.java").symlink_to(ignored)
    (tmp_path / "App.java").write_text("class App {}")

    files = FileCrawler(DocmakerConfig(source_dir=tmp_path)).crawl()

    assert [file.relative_path for file in files] == [Path("App.java")]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes require POSIX")
def test_crawler_does_not_read_named_pipes(tmp_path, monkeypatch):
    pipe = tmp_path / "stream.java"
    os.mkfifo(pipe)
    (tmp_path / "App.java").write_text("class App {}")
    crawler = FileCrawler(DocmakerConfig(source_dir=tmp_path))
    read_header = crawler._read_header
    compute_hash = crawler._compute_hash

    def checked_header(path, num_lines):
        assert path != pipe, "Reading a named pipe would hang the scan"
        return read_header(path, num_lines)

    def checked_hash(path):
        assert path != pipe, "Hashing a named pipe would hang the scan"
        return compute_hash(path)

    monkeypatch.setattr(crawler, "_read_header", checked_header)
    monkeypatch.setattr(crawler, "_compute_hash", checked_hash)

    assert [file.relative_path for file in crawler.crawl()] == [Path("App.java")]


@pytest.mark.parametrize("error", [PermissionError, FileNotFoundError])
def test_crawler_continues_after_file_becomes_unreadable(tmp_path, monkeypatch, caplog, error):
    (tmp_path / "Unavailable.java").write_text("class Unavailable {}")
    (tmp_path / "App.java").write_text("class App {}")
    config = DocmakerConfig(source_dir=tmp_path)
    config.llm.enabled = False
    crawler = FileCrawler(config)
    real_open = builtins.open

    def failing_open(path, *args, **kwargs):
        if path == tmp_path / "Unavailable.java":
            raise error("File became unavailable after stat")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)

    assert [file.relative_path for file in crawler.crawl()] == [Path("App.java")]
    assert "Skipping unavailable source file" in caplog.text
    assert "Unavailable.java" in caplog.text
