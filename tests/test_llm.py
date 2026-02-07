"""Tests for the LLM classification module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from docmaker.config import LLMConfig
from docmaker.llm import (
    CLASSIFICATION_PROMPT,
    FileClassifier,
    LMStudioProvider,
    NoOpProvider,
    OllamaProvider,
    OpenAIProvider,
    create_llm_provider,
)
from docmaker.models import FileCategory, Language, SourceFile


@pytest.fixture
def sample_file():
    """Create a sample SourceFile for testing."""
    return SourceFile(
        path=Path("/repo/src/main/java/com/example/UserService.java"),
        relative_path=Path("src/main/java/com/example/UserService.java"),
        language=Language.JAVA,
        category=FileCategory.UNKNOWN,
        size_bytes=500,
        hash="abc123",
        header_content="package com.example;\n\n@Service\npublic class UserService {}",
    )


@pytest.fixture
def ollama_config():
    return LLMConfig(provider="ollama", model="llama3.2", base_url="http://localhost:11434")


@pytest.fixture
def lmstudio_config():
    return LLMConfig(provider="lmstudio", model="local-model", base_url="http://localhost:1234/v1")


@pytest.fixture
def openai_config():
    return LLMConfig(
        provider="openai",
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-key",
    )


# --- _parse_category tests ---


class TestParseCategory:
    """Tests for LLMProvider._parse_category response parsing."""

    def _parse(self, answer: str) -> FileCategory:
        """Helper: use NoOpProvider to access _parse_category."""
        return NoOpProvider()._parse_category(answer)

    def test_valid_categories(self):
        assert self._parse("BACKEND") == FileCategory.BACKEND
        assert self._parse("FRONTEND") == FileCategory.FRONTEND
        assert self._parse("CONFIG") == FileCategory.CONFIG
        assert self._parse("TEST") == FileCategory.TEST
        assert self._parse("IGNORE") == FileCategory.IGNORE

    def test_category_with_trailing_text(self):
        assert self._parse("BACKEND - this is server code") == FileCategory.BACKEND
        assert self._parse("TEST (unit test file)") == FileCategory.TEST

    def test_empty_response_returns_unknown(self):
        assert self._parse("") == FileCategory.UNKNOWN

    def test_garbage_response_returns_unknown(self):
        assert self._parse("I think this file is a service") == FileCategory.UNKNOWN

    def test_lowercase_returns_unknown(self):
        assert self._parse("backend") == FileCategory.UNKNOWN


# --- create_llm_provider factory tests ---


class TestCreateLLMProvider:
    def test_disabled_returns_noop(self):
        config = LLMConfig(enabled=False)
        provider = create_llm_provider(config)
        assert isinstance(provider, NoOpProvider)

    def test_ollama_provider(self, ollama_config):
        provider = create_llm_provider(ollama_config)
        assert isinstance(provider, OllamaProvider)

    def test_lmstudio_provider(self, lmstudio_config):
        provider = create_llm_provider(lmstudio_config)
        assert isinstance(provider, LMStudioProvider)

    def test_openai_provider(self, openai_config):
        provider = create_llm_provider(openai_config)
        assert isinstance(provider, OpenAIProvider)

    def test_anthropic_uses_openai_provider(self):
        config = LLMConfig(provider="anthropic", api_key="sk-ant-test")
        provider = create_llm_provider(config)
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_returns_noop(self):
        config = LLMConfig(provider="nonexistent")
        provider = create_llm_provider(config)
        assert isinstance(provider, NoOpProvider)


# --- NoOpProvider tests ---


class TestNoOpProvider:
    def test_is_available(self):
        assert NoOpProvider().is_available() is True

    def test_classify_returns_original_category(self, sample_file):
        sample_file.category = FileCategory.BACKEND
        result = NoOpProvider().classify(sample_file)
        assert result == FileCategory.BACKEND

    def test_classify_preserves_unknown(self, sample_file):
        result = NoOpProvider().classify(sample_file)
        assert result == FileCategory.UNKNOWN


# --- OllamaProvider tests ---


class TestOllamaProvider:
    def test_is_available_success(self, ollama_config):
        provider = OllamaProvider(ollama_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("docmaker.llm.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            # Use the context manager mock pattern
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            assert provider.is_available() is True

    def test_is_available_failure(self, ollama_config):
        provider = OllamaProvider(ollama_config)
        with patch("docmaker.llm.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            assert provider.is_available() is False

    def test_classify_success(self, ollama_config, sample_file):
        provider = OllamaProvider(ollama_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "BACKEND"}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            result = provider.classify(sample_file)
            assert result == FileCategory.BACKEND

    def test_classify_http_error_returns_original(self, ollama_config, sample_file):
        provider = OllamaProvider(ollama_config)
        sample_file.category = FileCategory.UNKNOWN

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.side_effect = httpx.ConnectError("Connection refused")
            result = provider.classify(sample_file)
            assert result == FileCategory.UNKNOWN

    def test_classify_sends_correct_prompt(self, ollama_config, sample_file):
        provider = OllamaProvider(ollama_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "BACKEND"}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            provider.classify(sample_file)

            call_args = ctx.post.call_args
            assert call_args[0][0] == "http://localhost:11434/api/generate"
            body = call_args[1]["json"]
            assert body["model"] == "llama3.2"
            assert body["stream"] is False
            assert "UserService.java" in body["prompt"]


# --- LMStudioProvider tests ---


class TestLMStudioProvider:
    def test_classify_success(self, lmstudio_config, sample_file):
        provider = LMStudioProvider(lmstudio_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "FRONTEND"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            result = provider.classify(sample_file)
            assert result == FileCategory.FRONTEND

    def test_classify_uses_chat_completions_endpoint(self, lmstudio_config, sample_file):
        provider = LMStudioProvider(lmstudio_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "CONFIG"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            provider.classify(sample_file)

            url = ctx.post.call_args[0][0]
            assert url == "http://localhost:1234/v1/chat/completions"

    def test_classify_error_returns_original(self, lmstudio_config, sample_file):
        provider = LMStudioProvider(lmstudio_config)
        sample_file.category = FileCategory.TEST

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.side_effect = httpx.TimeoutException("Timeout")
            result = provider.classify(sample_file)
            assert result == FileCategory.TEST

    def test_is_available_success(self, lmstudio_config):
        provider = LMStudioProvider(lmstudio_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_response
            assert provider.is_available() is True

    def test_is_available_failure(self, lmstudio_config):
        provider = LMStudioProvider(lmstudio_config)
        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.get.side_effect = httpx.ConnectError("refused")
            assert provider.is_available() is False


# --- OpenAIProvider tests ---


class TestOpenAIProvider:
    def test_is_available_with_api_key(self, openai_config):
        provider = OpenAIProvider(openai_config)
        assert provider.is_available() is True

    def test_is_available_without_api_key(self):
        config = LLMConfig(provider="openai", api_key=None)
        provider = OpenAIProvider(config)
        assert provider.is_available() is False

    def test_is_available_empty_api_key(self):
        config = LLMConfig(provider="openai", api_key="")
        provider = OpenAIProvider(config)
        assert provider.is_available() is False

    def test_classify_success(self, openai_config, sample_file):
        provider = OpenAIProvider(openai_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "BACKEND"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            result = provider.classify(sample_file)
            assert result == FileCategory.BACKEND

    def test_classify_sends_auth_header(self, openai_config, sample_file):
        provider = OpenAIProvider(openai_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "BACKEND"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            provider.classify(sample_file)

            call_kwargs = ctx.post.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test-key"

    def test_classify_error_returns_original(self, openai_config, sample_file):
        provider = OpenAIProvider(openai_config)
        sample_file.category = FileCategory.CONFIG

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )
            result = provider.classify(sample_file)
            assert result == FileCategory.CONFIG

    def test_classify_empty_choices_returns_unknown(self, openai_config, sample_file):
        provider = OpenAIProvider(openai_config)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            result = provider.classify(sample_file)
            assert result == FileCategory.UNKNOWN


# --- FileClassifier tests ---


class TestFileClassifier:
    def test_already_categorized_skips_llm(self, sample_file):
        sample_file.category = FileCategory.BACKEND
        config = LLMConfig(enabled=True)
        classifier = FileClassifier(config)
        result = classifier.classify(sample_file)
        assert result == FileCategory.BACKEND

    def test_unknown_file_uses_llm_when_available(self, sample_file):
        config = LLMConfig(provider="openai", api_key="sk-test")
        classifier = FileClassifier(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "BACKEND"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response
            result = classifier.classify(sample_file)
            assert result == FileCategory.BACKEND

    def test_disabled_llm_returns_original(self, sample_file):
        config = LLMConfig(enabled=False)
        classifier = FileClassifier(config)
        result = classifier.classify(sample_file)
        assert result == FileCategory.UNKNOWN

    def test_unavailable_llm_returns_original(self, sample_file):
        config = LLMConfig(provider="ollama")
        classifier = FileClassifier(config)
        # Force LLM unavailable
        classifier._llm_available = False
        result = classifier.classify(sample_file)
        assert result == FileCategory.UNKNOWN

    def test_is_llm_available_caches_result(self):
        config = LLMConfig(provider="openai", api_key="sk-test")
        classifier = FileClassifier(config)
        # First call should check and cache
        result1 = classifier.is_llm_available()
        assert result1 is True
        assert classifier._llm_available is True
        # Subsequent call uses cache
        result2 = classifier.is_llm_available()
        assert result2 is True

    def test_classify_batch(self, sample_file):
        config = LLMConfig(enabled=False)
        classifier = FileClassifier(config)

        file2 = SourceFile(
            path=Path("/repo/test/TestFoo.java"),
            relative_path=Path("test/TestFoo.java"),
            language=Language.JAVA,
            category=FileCategory.TEST,
        )
        files = [sample_file, file2]
        result = classifier.classify_batch(files)

        assert len(result) == 2
        assert result[0].category == FileCategory.UNKNOWN  # no LLM, stays unknown
        assert result[1].category == FileCategory.TEST  # already categorized

    def test_classify_batch_with_llm(self, sample_file):
        config = LLMConfig(provider="openai", api_key="sk-test")
        classifier = FileClassifier(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "BACKEND"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch("docmaker.llm.httpx.Client") as mock_client:
            ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_response

            result = classifier.classify_batch([sample_file])
            assert result[0].category == FileCategory.BACKEND


# --- Classification prompt tests ---


class TestClassificationPrompt:
    def test_prompt_contains_all_categories(self):
        assert "BACKEND" in CLASSIFICATION_PROMPT
        assert "FRONTEND" in CLASSIFICATION_PROMPT
        assert "CONFIG" in CLASSIFICATION_PROMPT
        assert "TEST" in CLASSIFICATION_PROMPT
        assert "IGNORE" in CLASSIFICATION_PROMPT

    def test_prompt_formatting(self, sample_file):
        formatted = CLASSIFICATION_PROMPT.format(
            file_path=sample_file.relative_path,
            language=sample_file.language.value,
            num_lines=50,
            code_snippet=sample_file.header_content[:2000],
        )
        assert "UserService.java" in formatted
        assert "java" in formatted
        assert "@Service" in formatted
