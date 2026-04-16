"""
tests/test_capture.py — Modül 1 birim testleri

Not: Gerçek ekran yakalama ve kısayol testleri ortama bağlıdır.
     Burada bağımsız test edilebilir mantık (HOTkey parse) test edilir,
     mss ve tkinter mock'lanır.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# mss ve alt modüllerini mock'la (Tesseract/ekran ortamı gerektirmez)
_mss_mock = MagicMock()
sys.modules["mss"] = _mss_mock
sys.modules["mss.tools"] = _mss_mock.tools
sys.modules.setdefault("pynput", MagicMock())
sys.modules.setdefault("pynput.keyboard", MagicMock())

from modules.capture import HotkeyListener  # noqa: E402


class TestHotkeyListener:
    """HotkeyListener._parse_hotkey yöntemi testleri."""

    def _make_listener(self):
        return HotkeyListener(on_capture=lambda: None, on_toggle=lambda: None)

    def test_parse_ctrl_shift_s(self):
        listener = self._make_listener()
        result = listener._parse_hotkey("ctrl+shift+s")
        assert result == "<ctrl>+<shift>+s"

    def test_parse_ctrl_shift_h(self):
        listener = self._make_listener()
        result = listener._parse_hotkey("ctrl+shift+h")
        assert result == "<ctrl>+<shift>+h"

    def test_parse_single_modifier(self):
        listener = self._make_listener()
        result = listener._parse_hotkey("ctrl+a")
        assert result == "<ctrl>+a"

    def test_parse_alt(self):
        listener = self._make_listener()
        result = listener._parse_hotkey("alt+f4")
        assert result == "<alt>+f4"

    def test_parse_uppercase_input(self):
        """Büyük harf girişi küçük harfe normalize edilmeli."""
        listener = self._make_listener()
        result = listener._parse_hotkey("CTRL+SHIFT+S")
        assert result == "<ctrl>+<shift>+s"


class TestCaptureImport:
    """capture modülü import testleri."""

    def test_module_importable(self):
        import modules.capture as cap
        assert hasattr(cap, "capture_fullscreen")
        assert hasattr(cap, "capture_roi")
        assert hasattr(cap, "HotkeyListener")
        assert hasattr(cap, "ROISelector")
