"""Tests for the cache manager."""

import json
import tempfile
from pathlib import Path

import pytest

from docmaker.cache import CacheManager
from docmaker.models import FileCategory, Language, SourceFile


@pytest.fixture
def cache_dir():
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_manager(cache_dir):
    """Create a CacheManager with a temporary cache path."""
    return CacheManager(cache_dir / ".docmaker_cache.json")


def _make_source_file(
    relative_path: str = "src/main.py",
    language: Language = Language.PYTHON,
    category: FileCategory = FileCategory.BACKEND,
    size_bytes: int = 100,
    file_hash: str = "abc123",
) -> SourceFile:
    """Helper to create a SourceFile for testing."""
    return SourceFile(
        path=Path("/repo") / relative_path,
        relative_path=Path(relative_path),
        language=language,
        category=category,
        size_bytes=size_bytes,
        hash=file_hash,
    )


# --- Cache creation ---


class TestCacheCreation:
    def test_load_returns_empty_cache_when_no_file(self, cache_manager):
        """Loading from a non-existent path returns empty CacheData."""
        cache = cache_manager.load()
        assert cache.version == "1.0"
        assert cache.last_run == ""
        assert cache.entries == {}

    def test_save_creates_cache_file(self, cache_manager):
        """Saving creates the cache file on disk."""
        cache_manager.load()
        cache_manager.save()
        assert cache_manager.cache_path.exists()

    def test_save_creates_parent_directories(self, cache_dir):
        """Save creates intermediate directories if needed."""
        nested_path = cache_dir / "a" / "b" / "c" / "cache.json"
        cm = CacheManager(nested_path)
        cm.load()
        cm.save()
        assert nested_path.exists()

    def test_save_writes_valid_json(self, cache_manager):
        """Saved cache file contains valid JSON with expected keys."""
        cache_manager.load()
        cache_manager.save()
        with open(cache_manager.cache_path) as f:
            data = json.load(f)
        assert "version" in data
        assert "last_run" in data
        assert "entries" in data

    def test_save_sets_last_run_timestamp(self, cache_manager):
        """Save populates last_run with an ISO timestamp."""
        cache_manager.load()
        cache_manager.save()
        with open(cache_manager.cache_path) as f:
            data = json.load(f)
        assert data["last_run"] != ""

    def test_save_does_nothing_when_cache_not_loaded(self, cache_manager):
        """Save is a no-op if load() was never called."""
        cache_manager.save()
        assert not cache_manager.cache_path.exists()


# --- Cache loading ---


class TestCacheLoading:
    def test_load_returns_same_object_on_repeated_calls(self, cache_manager):
        """Load is lazy: repeated calls return the same in-memory object."""
        first = cache_manager.load()
        second = cache_manager.load()
        assert first is second

    def test_load_reads_existing_cache(self, cache_dir):
        """Load correctly deserializes a pre-existing cache file."""
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "last_run": "2026-01-01T00:00:00",
                    "entries": {
                        "src/app.py": {
                            "relative_path": "src/app.py",
                            "hash": "deadbeef",
                            "language": "python",
                            "category": "backend",
                            "size_bytes": 512,
                            "last_processed": "2026-01-01T00:00:00",
                        }
                    },
                }
            )
        )

        cm = CacheManager(cache_path)
        cache = cm.load()
        assert cache.last_run == "2026-01-01T00:00:00"
        assert "src/app.py" in cache.entries
        entry = cache.entries["src/app.py"]
        assert entry.hash == "deadbeef"
        assert entry.size_bytes == 512

    def test_load_handles_corrupted_json(self, cache_dir):
        """Load returns empty cache when the file contains invalid JSON."""
        cache_path = cache_dir / "cache.json"
        cache_path.write_text("not valid json {{{")

        cm = CacheManager(cache_path)
        cache = cm.load()
        assert cache.entries == {}

    def test_load_handles_missing_entry_keys(self, cache_dir):
        """Load returns empty cache when entry data is missing required keys."""
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "last_run": "",
                    "entries": {
                        "src/app.py": {
                            "relative_path": "src/app.py",
                            # missing hash, language, etc.
                        }
                    },
                }
            )
        )

        cm = CacheManager(cache_path)
        cache = cm.load()
        assert cache.entries == {}

    def test_roundtrip_preserves_data(self, cache_manager):
        """Data survives a save-then-load cycle via a fresh CacheManager."""
        sf = _make_source_file("src/foo.py", file_hash="roundtrip123")
        cache_manager.load()
        cache_manager.update_file(sf)
        cache_manager.save()

        cm2 = CacheManager(cache_manager.cache_path)
        cache = cm2.load()
        assert "src/foo.py" in cache.entries
        assert cache.entries["src/foo.py"].hash == "roundtrip123"


# --- Cache invalidation on file change ---


class TestFileChangeDetection:
    def test_new_file_is_always_changed(self, cache_manager):
        """A file not in the cache is considered changed."""
        sf = _make_source_file("src/new.py", file_hash="new123")
        assert cache_manager.is_file_changed(sf) is True

    def test_unchanged_file_is_not_changed(self, cache_manager):
        """A file whose hash matches the cache is not changed."""
        sf = _make_source_file("src/stable.py", file_hash="stable_hash")
        cache_manager.update_file(sf)
        assert cache_manager.is_file_changed(sf) is False

    def test_modified_file_is_changed(self, cache_manager):
        """A file whose hash differs from the cache is changed."""
        sf = _make_source_file("src/mod.py", file_hash="original")
        cache_manager.update_file(sf)

        sf_modified = _make_source_file("src/mod.py", file_hash="modified")
        assert cache_manager.is_file_changed(sf_modified) is True

    def test_update_file_stores_entry(self, cache_manager):
        """update_file adds a CacheEntry with correct metadata."""
        sf = _make_source_file(
            "src/service.java",
            language=Language.JAVA,
            category=FileCategory.BACKEND,
            size_bytes=2048,
            file_hash="java_hash",
        )
        cache_manager.update_file(sf)

        cache = cache_manager.load()
        entry = cache.entries["src/service.java"]
        assert entry.hash == "java_hash"
        assert entry.language == "java"
        assert entry.category == "backend"
        assert entry.size_bytes == 2048
        assert entry.last_processed != ""

    def test_update_file_overwrites_previous_entry(self, cache_manager):
        """Updating the same file replaces the old entry."""
        sf_v1 = _make_source_file("src/x.py", file_hash="v1")
        cache_manager.update_file(sf_v1)

        sf_v2 = _make_source_file("src/x.py", file_hash="v2", size_bytes=999)
        cache_manager.update_file(sf_v2)

        cache = cache_manager.load()
        assert cache.entries["src/x.py"].hash == "v2"
        assert cache.entries["src/x.py"].size_bytes == 999

    def test_remove_file_deletes_entry(self, cache_manager):
        """remove_file removes an entry from the cache."""
        sf = _make_source_file("src/gone.py", file_hash="gone_hash")
        cache_manager.update_file(sf)

        cache_manager.remove_file(Path("src/gone.py"))
        cache = cache_manager.load()
        assert "src/gone.py" not in cache.entries

    def test_remove_nonexistent_file_is_noop(self, cache_manager):
        """Removing a file not in cache does not raise."""
        cache_manager.load()
        cache_manager.remove_file(Path("src/never_existed.py"))


# --- Incremental mode behavior ---


class TestIncrementalMode:
    def test_get_changed_files_returns_all_on_empty_cache(self, cache_manager):
        """With an empty cache, all files are considered changed."""
        files = [
            _make_source_file("a.py", file_hash="h1"),
            _make_source_file("b.py", file_hash="h2"),
            _make_source_file("c.py", file_hash="h3"),
        ]
        changed = cache_manager.get_changed_files(files)
        assert len(changed) == 3

    def test_get_changed_files_filters_unchanged(self, cache_manager):
        """Files whose hashes match the cache are excluded."""
        sf1 = _make_source_file("a.py", file_hash="h1")
        sf2 = _make_source_file("b.py", file_hash="h2")
        cache_manager.update_file(sf1)
        cache_manager.update_file(sf2)

        sf2_mod = _make_source_file("b.py", file_hash="h2_modified")
        changed = cache_manager.get_changed_files([sf1, sf2_mod])
        assert len(changed) == 1
        assert changed[0].relative_path == Path("b.py")

    def test_get_changed_files_returns_empty_when_nothing_changed(self, cache_manager):
        """No files returned when all match the cache."""
        sf = _make_source_file("only.py", file_hash="same")
        cache_manager.update_file(sf)
        changed = cache_manager.get_changed_files([sf])
        assert changed == []

    def test_get_deleted_files_detects_removals(self, cache_manager):
        """Files in cache but not in current list are returned as deleted."""
        sf1 = _make_source_file("keep.py", file_hash="h1")
        sf2 = _make_source_file("delete_me.py", file_hash="h2")
        cache_manager.update_file(sf1)
        cache_manager.update_file(sf2)

        deleted = cache_manager.get_deleted_files([sf1])
        assert deleted == ["delete_me.py"]

    def test_get_deleted_files_returns_empty_when_all_present(self, cache_manager):
        """No deleted files when current list matches cache."""
        sf = _make_source_file("still_here.py", file_hash="h1")
        cache_manager.update_file(sf)
        deleted = cache_manager.get_deleted_files([sf])
        assert deleted == []

    def test_get_deleted_files_on_empty_cache(self, cache_manager):
        """Empty cache has no deleted files."""
        sf = _make_source_file("new.py", file_hash="h1")
        deleted = cache_manager.get_deleted_files([sf])
        assert deleted == []

    def test_clear_removes_cache_file_and_resets_memory(self, cache_manager):
        """clear() deletes the file and resets in-memory cache."""
        sf = _make_source_file("src/x.py", file_hash="h")
        cache_manager.update_file(sf)
        cache_manager.save()
        assert cache_manager.cache_path.exists()

        cache_manager.clear()
        assert not cache_manager.cache_path.exists()

        cache = cache_manager.load()
        assert cache.entries == {}

    def test_full_incremental_workflow(self, cache_manager):
        """Simulate a full incremental run: first pass caches all, second pass detects changes."""
        # First run: all files are new
        files_v1 = [
            _make_source_file("a.py", file_hash="a1"),
            _make_source_file("b.py", file_hash="b1"),
            _make_source_file("c.py", file_hash="c1"),
        ]
        changed = cache_manager.get_changed_files(files_v1)
        assert len(changed) == 3

        for f in files_v1:
            cache_manager.update_file(f)
        cache_manager.save()

        # Second run: one file modified, one deleted, one new
        files_v2 = [
            _make_source_file("a.py", file_hash="a1"),  # unchanged
            _make_source_file("b.py", file_hash="b2"),  # modified
            _make_source_file("d.py", file_hash="d1"),  # new
        ]

        # Load fresh manager to simulate new process
        cm2 = CacheManager(cache_manager.cache_path)
        changed = cm2.get_changed_files(files_v2)
        assert len(changed) == 2
        changed_paths = {str(f.relative_path) for f in changed}
        assert changed_paths == {"b.py", "d.py"}

        deleted = cm2.get_deleted_files(files_v2)
        assert deleted == ["c.py"]
