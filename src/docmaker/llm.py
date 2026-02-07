"""LLM integration for file classification and symbol summarization."""

import logging
from abc import ABC, abstractmethod

import httpx

from docmaker.config import LLMConfig
from docmaker.models import ClassDef, FileCategory, FunctionDef, SourceFile

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

CLASS_SUMMARY_PROMPT = """\
You are a technical documentation writer. Write a concise summary of this class.

Class: {class_name}
Package: {package}
Superclass: {superclass}
Interfaces: {interfaces}
Annotations: {annotations}
Fields: {fields}
Methods: {methods}

Source code:
```
{source_code}
```

Write a 2-3 sentence natural-language summary describing what this class does, its role in the \
application, and its key responsibilities. Be specific and technical. Do not start with \
"This class" - start with what it does.
"""

FUNCTION_SUMMARY_PROMPT = """You are a technical documentation writer. Write a concise summary \
of this function/method.

Function: {function_name}
Class: {class_name}
Parameters: {parameters}
Return type: {return_type}
Annotations: {annotations}

Source code:
```
{source_code}
```

Write a 1-2 sentence natural-language summary describing what this function does and why. \
Be specific and technical. Do not start with "This function" - start with what it does.
"""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        pass

    @abstractmethod
    def summarize(self, prompt: str) -> str | None:
        """Send a summarization prompt and return the response text."""
        pass

    def summarize_class(self, cls: ClassDef) -> str | None:
        """Generate a natural-language summary for a class."""
        prompt = CLASS_SUMMARY_PROMPT.format(
            class_name=cls.name,
            package=cls.package or "N/A",
            superclass=cls.superclass or "None",
            interfaces=", ".join(cls.interfaces) if cls.interfaces else "None",
            annotations=(
                ", ".join(f"@{a.name}" for a in cls.annotations) if cls.annotations else "None"
            ),
            fields=", ".join(f.name for f in cls.fields) if cls.fields else "None",
            methods=(
                ", ".join(m.name for m in cls.methods) if cls.methods else "None"
            ),
            source_code=cls.source_code[:3000],
        )
        return self.summarize(prompt)

    def summarize_function(self, func: FunctionDef, class_name: str | None = None) -> str | None:
        """Generate a natural-language summary for a function/method."""
        prompt = FUNCTION_SUMMARY_PROMPT.format(
            function_name=func.name,
            class_name=class_name or "N/A (module-level)",
            parameters=", ".join(
                f"{p.name}: {p.type or 'Any'}" for p in func.parameters
            ) if func.parameters else "None",
            return_type=func.return_type or "None",
            annotations=(
                ", ".join(f"@{a.name}" for a in func.annotations)
                if func.annotations
                else "None"
            ),
            source_code=func.source_code[:3000],
        )
        return self.summarize(prompt)

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

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using Ollama."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )

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
                answer = result.get("response", "").strip().upper()
                return self._parse_category(answer)
        except Exception as e:
            logger.warning(f"LLM classification failed for {file.relative_path}: {e}")
            return file.category

    def summarize(self, prompt: str) -> str | None:
        """Send a summarization prompt to Ollama."""
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
                return result.get("response", "").strip() or None
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return None


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

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using LM Studio."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 10,
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
                result = response.json()
                answer = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                    .upper()
                )
                return self._parse_category(answer)
        except Exception as e:
            logger.warning(f"LLM classification failed for {file.relative_path}: {e}")
            return file.category

    def summarize(self, prompt: str) -> str | None:
        """Send a summarization prompt to LM Studio."""
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                ) or None
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return None


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)

    def classify(self, file: SourceFile) -> FileCategory:
        """Classify a file using OpenAI."""
        prompt = CLASSIFICATION_PROMPT.format(
            file_path=file.relative_path,
            language=file.language.value,
            num_lines=50,
            code_snippet=file.header_content[:2000],
        )

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 10,
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
                result = response.json()
                answer = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                    .upper()
                )
                return self._parse_category(answer)
        except Exception as e:
            logger.warning(f"LLM classification failed for {file.relative_path}: {e}")
            return file.category

    def summarize(self, prompt: str) -> str | None:
        """Send a summarization prompt to OpenAI."""
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={
                        "model": self.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                ) or None
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return None


class NoOpProvider(LLMProvider):
    """No-op provider when LLM is disabled."""

    def is_available(self) -> bool:
        return True

    def classify(self, file: SourceFile) -> FileCategory:
        return file.category

    def summarize(self, prompt: str) -> str | None:
        return None


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


class SymbolSummarizer:
    """Generates natural-language summaries for code symbols using LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = create_llm_provider(config)
        self._llm_available: bool | None = None

    def is_available(self) -> bool:
        """Check if the LLM provider is available for summarization."""
        if self._llm_available is None:
            self._llm_available = self.provider.is_available()
        return self._llm_available

    def summarize_class(self, cls: ClassDef) -> str | None:
        """Generate a summary for a class definition."""
        if not self.config.enabled or not self.is_available():
            return None
        return self.provider.summarize_class(cls)

    def summarize_function(
        self, func: FunctionDef, class_name: str | None = None
    ) -> str | None:
        """Generate a summary for a function/method definition."""
        if not self.config.enabled or not self.is_available():
            return None
        return self.provider.summarize_function(func, class_name)
