"""
tests/test_ai_engine.py — Modül 3 birim testleri

OpenAI API mock'lanarak prompt oluşturma, response parse ve
hata yönetimi (rate limit, timeout) test edilir.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# openai modülünü mock'la
mock_openai = MagicMock()
sys.modules["openai"] = mock_openai
# Hata sınıflarını tanımla
mock_openai.RateLimitError = type("RateLimitError", (Exception,), {})
mock_openai.APITimeoutError = type("APITimeoutError", (Exception,), {})
mock_openai.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 500, "message": "err"})


from modules.ai_engine import build_prompt, get_answer  # noqa: E402


class TestBuildPrompt:
    """build_prompt fonksiyonu testleri."""

    def test_multiple_choice_prompt_contains_text(self, tmp_path, monkeypatch):
        """Çoktan seçmeli prompt şablonu soru metnini içermeli."""
        template = "Çoktan seçmeli:\n{extracted_text}"
        prompt_file = tmp_path / "multiple_choice.txt"
        prompt_file.write_text(template, encoding="utf-8")

        import config
        monkeypatch.setattr(config, "PROMPT_MULTIPLE_CHOICE", prompt_file)

        result = build_prompt("Hangisi doğru?", multiple_choice=True)
        assert "Hangisi doğru?" in result

    def test_open_ended_prompt_contains_text(self, tmp_path, monkeypatch):
        """Açık uçlu prompt şablonu soru metnini içermeli."""
        template = "Açık uçlu:\n{extracted_text}"
        prompt_file = tmp_path / "open_ended.txt"
        prompt_file.write_text(template, encoding="utf-8")

        import config
        monkeypatch.setattr(config, "PROMPT_OPEN_ENDED", prompt_file)

        result = build_prompt("Python nedir?", multiple_choice=False)
        assert "Python nedir?" in result

    def test_missing_prompt_file_uses_default(self, monkeypatch):
        """Prompt dosyası yoksa varsayılan prompt kullanılmalı."""
        import config
        monkeypatch.setattr(config, "PROMPT_OPEN_ENDED", Path("nonexistent.txt"))
        result = build_prompt("Test sorusu", multiple_choice=False)
        assert "Test sorusu" in result

    def test_multiple_choice_uses_mc_template(self, monkeypatch):
        """multiple_choice=True → PROMPT_MULTIPLE_CHOICE kullanılmalı."""
        import config
        called_paths = []

        original_load = __import__("modules.ai_engine", fromlist=["_load_prompt"])._load_prompt

        def mock_load(path, text):
            called_paths.append(path)
            return text

        with patch("modules.ai_engine._load_prompt", side_effect=mock_load):
            build_prompt("Soru", multiple_choice=True)
            assert called_paths[0] == config.PROMPT_MULTIPLE_CHOICE


class TestGetAnswer:
    """get_answer fonksiyonu testleri."""

    def test_empty_text_returns_empty_string(self):
        result = get_answer("")
        assert result == ""

    def test_whitespace_only_returns_empty_string(self):
        result = get_answer("   \n\t  ")
        assert result == ""

    def test_successful_api_call(self, monkeypatch):
        """Başarılı API çağrısında cevap string döndürmeli."""
        import modules.ai_engine as engine

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  C  "

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        monkeypatch.setattr(engine, "_client", mock_client)

        result = get_answer("Hangisi doğru?\nA) B) C) D)", multiple_choice=True)
        assert result == "C"

    def test_api_returns_stripped_answer(self, monkeypatch):
        """Cevap baş/son boşluklardan arındırılmış olmalı."""
        import modules.ai_engine as engine

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "\n  Atatürk  \n"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        monkeypatch.setattr(engine, "_client", mock_client)

        result = get_answer("Türkiye'yi kim kurdu?")
        assert result == "Atatürk"

    def test_api_error_returns_empty_string(self, monkeypatch):
        """API hatası → boş string döndürmeli (uygulama çökmemeli)."""
        import modules.ai_engine as engine

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API down")
        monkeypatch.setattr(engine, "_client", mock_client)

        result = get_answer("Test sorusu")
        assert result == ""
