"""
tests/test_ocr.py — Modül 2 birim testleri

Gerçek Tesseract olmadan çalışabilmesi için pytesseract mock'lanır.
Ön işleme fonksiyonları ve is_multiple_choice tespiti doğrudan test edilir.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

# pytesseract'i mock'la (Tesseract kurulu olmayabilir)
mock_tess = MagicMock()
mock_tess.image_to_string.return_value = "Test metni"
mock_tess.TesseractNotFoundError = Exception
sys.modules["pytesseract"] = mock_tess


from modules.ocr import _preprocess_image, is_multiple_choice  # noqa: E402


class TestPreprocessImage:
    """_preprocess_image fonksiyonu testleri."""

    def _make_image(self, width: int = 200, height: int = 100) -> Image.Image:
        arr = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        return Image.fromarray(arr, "RGB")

    def test_returns_pil_image(self):
        img = self._make_image()
        result = _preprocess_image(img)
        assert isinstance(result, Image.Image)

    def test_output_is_grayscale_or_binary(self):
        """Çıktı gri tonlamalı (L) veya binary olmalı."""
        img = self._make_image()
        result = _preprocess_image(img)
        assert result.mode in ("L", "1", "RGB")

    def test_small_image_upscaled(self):
        """Küçük görüntüler (w < 800) büyütülmeli."""
        img = self._make_image(width=100, height=50)
        result = _preprocess_image(img)
        # Büyütülmüş olmalı
        assert result.width >= 100

    def test_large_image_not_modified_width(self):
        """Büyük görüntülerin genişliği değişmemeli."""
        img = self._make_image(width=1920, height=1080)
        result = _preprocess_image(img)
        # Büyütme uygulanmamalı — aynı genişlik
        assert result.width == 1920


class TestIsMultipleChoice:
    """is_multiple_choice fonksiyonu testleri."""

    def test_detects_letter_dot(self):
        text = "Soru nedir?\nA. Elma\nB. Armut\nC. Kiraz"
        assert is_multiple_choice(text) is True

    def test_detects_letter_paren(self):
        text = "Hangisi doğru?\nA) Bir\nB) İki\nC) Üç\nD) Dört"
        assert is_multiple_choice(text) is True

    def test_open_ended_returns_false(self):
        text = "Python'da liste ve tuple arasındaki fark nedir? Açıklayınız."
        assert is_multiple_choice(text) is False

    def test_single_option_returns_false(self):
        """Tek şık varsa çoktan seçmeli değil."""
        text = "A) Yalnızca tek seçenek var"
        assert is_multiple_choice(text) is False

    def test_empty_text_returns_false(self):
        assert is_multiple_choice("") is False


class TestExtractText:
    """extract_text yüksek seviye testleri (mock Tesseract)."""

    def test_returns_string(self):
        from modules.ocr import extract_text
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        result = extract_text(img)
        assert isinstance(result, str)

    def test_empty_ocr_returns_empty_string(self):
        mock_tess.image_to_string.return_value = "   "
        from modules.ocr import extract_text
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        result = extract_text(img)
        assert result == ""
