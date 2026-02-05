"""Tests for the file crawler."""

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
