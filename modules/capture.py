"""
modules/capture.py — Modül 1: Ekran Yakalama

Sorumluluklar:
  - mss ile hızlı ekran yakalama (tam ekran veya ROI)
  - tkinter tabanlı ROI seçim aracı (sürükle-seç)
  - Global kısayol dinleme (pynput) → Ctrl+Shift+S
  - Görüntüyü PIL Image olarak döndürme
"""
from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
from typing import Callable, Optional, Tuple

import mss
from PIL import Image
from pynput import keyboard

import config

logger = logging.getLogger(__name__)

# ─── ROI Seçim Aracı ─────────────────────────────────────────────────────────

class ROISelector:
    """
    Tam ekranı geçici olarak kaplayan şeffaf bir tkinter penceresi açar.
    Kullanıcı sürükle-bırak ile ROI alanını seçer; seçim koordinatları döndürülür.
    """

    def __init__(self) -> None:
        self.result: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)

    def select(self) -> Optional[Tuple[int, int, int, int]]:
        """Bloke eden çağrı: ROI seçildikten sonra (x, y, w, h) döndürür."""
        root = tk.Tk()
        root.title("ROI Seç")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.25)
        root.configure(bg="black")
        root.config(cursor="crosshair")

        canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        start_x = start_y = 0
        rect_id = None

        def on_press(event: tk.Event) -> None:
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            rect_id = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline="#00e5ff", width=2, fill=""
            )

        def on_drag(event: tk.Event) -> None:
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_release(event: tk.Event) -> None:
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)
            w, h = x2 - x1, y2 - y1
            if w > 10 and h > 10:
                self.result = (x1, y1, w, h)
            root.destroy()

        def on_escape(event: tk.Event) -> None:
            root.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", on_escape)

        root.mainloop()
        return self.result


# ─── Ekran Yakalama ──────────────────────────────────────────────────────────

def capture_fullscreen(monitor_index: int = 1) -> Image.Image:
    """Belirtilen monitörün tam ekranını yakalar ve PIL Image döndürür."""
    t0 = time.monotonic()
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    elapsed = (time.monotonic() - t0) * 1000
    logger.debug("Tam ekran yakalandı (%.1f ms)", elapsed)
    if elapsed > 500:
        logger.warning("Yakalama 500ms limitini aştı: %.1f ms", elapsed)
    return img


def capture_roi() -> Optional[Image.Image]:
    """
    ROI seçim aracını açar; kullanıcı seçim yaptıktan sonra
    yalnızca o alanı yakalar ve PIL Image döndürür.
    Returns None kullanıcı iptal ederse.
    """
    selector = ROISelector()
    roi = selector.select()
    if roi is None:
        logger.info("ROI seçimi iptal edildi.")
        return None

    x, y, w, h = roi
    t0 = time.monotonic()
    with mss.mss() as sct:
        region = {"left": x, "top": y, "width": w, "height": h}
        screenshot = sct.grab(region)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    elapsed = (time.monotonic() - t0) * 1000
    logger.debug("ROI yakalandı (%dx%d, %.1f ms)", w, h, elapsed)
    return img


# ─── Global Kısayol Dinleyici ─────────────────────────────────────────────────

class HotkeyListener:
    """
    pynput ile global kısayol tuşlarını dinler.
    Thread güvenlidir; daemon thread olarak çalışır.
    """

    def __init__(
        self,
        on_capture: Callable[[], None],
        on_toggle: Callable[[], None],
    ) -> None:
        self._on_capture = on_capture
        self._on_toggle = on_toggle
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def _parse_hotkey(self, hotkey_str: str) -> str:
        """'ctrl+shift+s' → '<ctrl>+<shift>+s' formatına çevirir."""
        parts = hotkey_str.lower().split("+")
        formatted = []
        for p in parts:
            p = p.strip()
            if p in ("ctrl", "alt", "shift", "cmd"):
                formatted.append(f"<{p}>")
            else:
                formatted.append(p)
        return "+".join(formatted)

    def start(self) -> None:
        """Arka planda kısayol dinlemeye başlar."""
        capture_key = self._parse_hotkey(config.HOTKEY_CAPTURE)
        toggle_key = self._parse_hotkey(config.HOTKEY_TOGGLE)

        hotkeys = {
            capture_key: self._on_capture,
            toggle_key: self._on_toggle,
        }
        logger.info(
            "Kısayollar: Yakalama=%s | Toggle=%s", capture_key, toggle_key
        )
        self._listener = keyboard.GlobalHotKeys(hotkeys)
        thread = threading.Thread(target=self._listener.run, daemon=True)
        thread.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            logger.debug("Kısayol dinleyici durduruldu.")
