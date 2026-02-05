"""Cache management for incremental updates."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from docmaker.models import SourceFile


@dataclass
class CacheEntry:
    """Represents a cached file entry."""

    relative_path: str
    hash: str
    language: str
    category: str
    size_bytes: int
    last_processed: str


@dataclass
class CacheData:
    """The complete cache structure."""

    version: str = "1.0"
    last_run: str = ""
    entries: dict[str, CacheEntry] | None = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = {}


class CacheManager:
    """Manages the file cache for incremental updates."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self._cache: CacheData | None = None

    def load(self) -> CacheData:
        """Load the cache from disk."""
        if self._cache is not None:
            return self._cache

        if not self.cache_path.exists():
            self._cache = CacheData()
            return self._cache

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            entries = {}
            for path, entry_data in data.get("entries", {}).items():
                entries[path] = CacheEntry(
                    relative_path=entry_data["relative_path"],
                    hash=entry_data["hash"],
                    language=entry_data["language"],
                    category=entry_data["category"],
                    size_bytes=entry_data["size_bytes"],
                    last_processed=entry_data["last_processed"],
                )

            self._cache = CacheData(
                version=data.get("version", "1.0"),
                last_run=data.get("last_run", ""),
                entries=entries,
            )
        except (json.JSONDecodeError, KeyError):
            self._cache = CacheData()

        return self._cache

    def save(self) -> None:
        """Save the cache to disk."""
        if self._cache is None:
            return

        self._cache.last_run = datetime.now().isoformat()

        data = {
            "version": self._cache.version,
            "last_run": self._cache.last_run,
            "entries": {path: asdict(entry) for path, entry in self._cache.entries.items()},
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def is_file_changed(self, file: SourceFile) -> bool:
        """Check if a file has changed since last processing."""
        cache = self.load()
        path_key = str(file.relative_path)

        if path_key not in cache.entries:
            return True

        cached = cache.entries[path_key]
        return cached.hash != file.hash

    def update_file(self, file: SourceFile) -> None:
        """Update the cache entry for a file."""
        cache = self.load()
        path_key = str(file.relative_path)

        cache.entries[path_key] = CacheEntry(
            relative_path=str(file.relative_path),
            hash=file.hash,
            language=file.language.value,
            category=file.category.value,
            size_bytes=file.size_bytes,
            last_processed=datetime.now().isoformat(),
        )

    def remove_file(self, relative_path: Path) -> None:
        """Remove a file from the cache."""
        cache = self.load()
        path_key = str(relative_path)
        cache.entries.pop(path_key, None)

    def get_changed_files(self, files: list[SourceFile]) -> list[SourceFile]:
        """Filter to only files that have changed since last run."""
        return [f for f in files if self.is_file_changed(f)]

    def get_deleted_files(self, current_files: list[SourceFile]) -> list[str]:
        """Get files that were in cache but no longer exist."""
        cache = self.load()
        current_paths = {str(f.relative_path) for f in current_files}
        return [path for path in cache.entries.keys() if path not in current_paths]

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache = CacheData()
        if self.cache_path.exists():
            self.cache_path.unlink()
