"""LLM integration for file classification and summarization."""

import logging
from abc import ABC, abstractmethod

import httpx

from docmaker.config import LLMConfig
from docmaker.models import ClassDef, FileCategory, FunctionDef, SourceFile, SymbolTable

logger = logging.getLogger(__name__)


CLASSIFICATION_PROMPT = """You are a code classifier. Analyze the code snippet below.
Classify it into ONE of these categories:

- BACKEND: Server-side code (APIs, services, controllers, repositories, business logic)
- FRONTEND: Client-side code (UI components, views, client-side logic)
- CONFIG: Configuration files (settings, properties, build configs)
- TEST: Test files (unit tests, integration tests, test utilities)
- IGNORE: Generated code, vendored code, or files that shouldn't be documented

File path: {file_path}
Language: {language}

Code snippet (first {num_lines} lines):
```
{code_snippet}
```

Respond with ONLY one word: BACKEND, FRONTEND, CONFIG, TEST, or IGNORE
"""

CLASS_SUMMARY_PROMPT = """You are a technical documentation writer. Write a concise summary
of the following class in 1-3 sentences. Focus on the class's purpose, responsibilities,
and how it fits into the application.

Class: {class_name}
Language: {language}
Package: {package}
Extends: {superclass}
Implements: {interfaces}
Annotations: {annotations}
Methods: {methods}

Source code:
```
{source_code}
```

Write a clear, concise summary (1-3 sentences). Do not include code or formatting.
"""

METHOD_SUMMARY_PROMPT = """You are a technical documentation writer. Write a one-sentence
summary of the following method. Focus on what it does, not how.

Class: {class_name}
Method: {method_name}
Language: {language}
Parameters: {parameters}
Returns: {return_type}
Annotations: {annotations}

Source code:
```
{source_code}
```

Write a single clear sentence describing what this method does. Do not include code or formatting.
"""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using the LLM."""
        pass

    @abstractmethod
    def generate(self, prompt: str) -> str | None:
        """Generate text from a prompt. Returns None on failure."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        pass

    def _parse_category(self, answer: str) -> FileCategory:
        """Parse the LLM response into a FileCategory."""
        answer = answer.split()[0] if answer else ""
        mapping = {
            "BACKEND": FileCategory.BACKEND,
            "FRONTEND": FileCategory.FRONTEND,
            "CONFIG": FileCategory.CONFIG,
            "TEST": FileCategory.TEST,
            "IGNORE": FileCategory.IGNORE,
        }
        return mapping.get(answer, FileCategory.UNKNOWN)


class OllamaProvider(LLMProvider):
    """Ollama LLM provider."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> str | None:
        """Generate text using Ollama."""
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return None

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using Ollama."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )
        answer = self.generate(prompt)
        if answer:
            return self._parse_category(answer.upper())
        return file.category


class LMStudioProvider(LLMProvider):
    """LM Studio provider (OpenAI-compatible API)."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def is_available(self) -> bool:
        """Check if LM Studio is running."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str) -> str | None:
        """Generate text using LM Studio."""
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return None

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using LM Studio."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )
        answer = self.generate(prompt)
        if answer:
            return self._parse_category(answer.upper())
        return file.category


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)

    def generate(self, prompt: str) -> str | None:
        """Generate text using OpenAI."""
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return None

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using OpenAI."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )
        answer = self.generate(prompt)
        if answer:
            return self._parse_category(answer.upper())
        return file.category


class NoOpProvider(LLMProvider):
    """No-op provider when LLM is disabled."""

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str) -> str | None:
        return None

    def classify(self, file: SourceFile) -> FileCategory:
        return file.category


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Factory function to create the appropriate LLM provider."""
    if not config.enabled:
        return NoOpProvider()

    providers = {
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "openai": OpenAIProvider,
        "anthropic": OpenAIProvider,
    }

    provider_class = providers.get(config.provider.lower())
    if not provider_class:
        logger.warning(f"Unknown LLM provider: {config.provider}, using no-op")
        return NoOpProvider()

    return provider_class(config)


class FileClassifier:
    """Classifies files using LLM and/or heuristics."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = create_llm_provider(config)
        self._llm_available: bool | None = None

    def is_llm_available(self) -> bool:
        """Check if the LLM provider is available."""
        if self._llm_available is None:
            self._llm_available = self.provider.is_available()
        return self._llm_available

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file, using LLM if available, otherwise keep heuristic result."""
        if file.category != FileCategory.UNKNOWN:
            return file.category

        if self.config.enabled and self.is_llm_available():
            return self.provider.classify(file)

        return file.category

    def classify_batch(self, files: list[SourceFile]) -> list[SourceFile]:
        """Classify multiple files."""
        for file in files:
            file.category = self.classify(file)
        return files


class Summarizer:
    """Generates natural-language summaries for classes and methods using LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = create_llm_provider(config)
        self._llm_available: bool | None = None

    def is_llm_available(self) -> bool:
        """Check if the LLM provider is available."""
        if self._llm_available is None:
            self._llm_available = self.provider.is_available()
        return self._llm_available

    def summarize_class(self, cls: ClassDef, language: str) -> str | None:
        """Generate a summary for a class."""
        prompt = CLASS_SUMMARY_PROMPT.format(
            class_name=cls.name,
            language=language,
            package=cls.package or "N/A",
            superclass=cls.superclass or "None",
            interfaces=", ".join(cls.interfaces) if cls.interfaces else "None",
            annotations=(
                ", ".join(f"@{a.name}" for a in cls.annotations) if cls.annotations else "None"
            ),
            methods=", ".join(m.name for m in cls.methods) if cls.methods else "None",
            source_code=cls.source_code[:3000] if cls.source_code else "N/A",
        )
        return self.provider.generate(prompt)

    def summarize_method(self, method: FunctionDef, class_name: str, language: str) -> str | None:
        """Generate a summary for a method."""
        prompt = METHOD_SUMMARY_PROMPT.format(
            class_name=class_name,
            method_name=method.name,
            language=language,
            parameters=", ".join(f"{p.name}: {p.type or 'Any'}" for p in method.parameters)
            if method.parameters
            else "None",
            return_type=method.return_type or "None",
            annotations=(
                ", ".join(f"@{a.name}" for a in method.annotations)
                if method.annotations
                else "None"
            ),
            source_code=method.source_code[:2000] if method.source_code else "N/A",
        )
        return self.provider.generate(prompt)

    def summarize_symbol_table(self, symbol_table: SymbolTable) -> tuple[int, int]:
        """Generate summaries for all classes and methods in the symbol table.

        Returns (class_count, method_count) of summaries generated.
        """
        class_count = 0
        method_count = 0

        for file_symbols in symbol_table.files.values():
            language = file_symbols.file.language.value

            for cls in file_symbols.classes:
                summary = self.summarize_class(cls, language)
                if summary:
                    cls.summary = summary
                    class_count += 1

                for method in cls.methods:
                    summary = self.summarize_method(method, cls.name, language)
                    if summary:
                        method.summary = summary
                        method_count += 1

            for func in file_symbols.functions:
                summary = self.summarize_method(func, "(module-level)", language)
                if summary:
                    func.summary = summary
                    method_count += 1

        return class_count, method_count
