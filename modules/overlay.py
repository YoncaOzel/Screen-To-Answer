"""
modules/overlay.py — Modül 4: Overlay Arayüzü

Sorumluluklar:
  - Tkinter always-on-top şeffaf pencere
  - Cevabı büyük puntoda gösterme
  - Pencereyi sürükle-bırak ile taşıma
  - Gizle / Göster (Ctrl+Shift+H kısayolu main.py'den çağrılır)
  - Opacity ayarı
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

import config

logger = logging.getLogger(__name__)


class OverlayWindow:
    """
    Şeffaf, always-on-top tkinter penceresi.

    Kullanım:
        overlay = OverlayWindow()
        overlay.start()          # arka plan thread'de arayüzü başlatır
        overlay.show_answer("C") # ana thread'den güvenle çağrılır
        overlay.toggle()         # gizle / göster
        overlay.stop()           # pencereyi kapat
    """

    def __init__(self) -> None:
        self._root: Optional[tk.Tk] = None
        self._label: Optional[tk.Label] = None
        self._frame: Optional[tk.Frame] = None
        self._visible: bool = True
        self._ready = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._drag_start_x = 0
        self._drag_start_y = 0

    # ─── Başlat / Durdur ────────────────────────────────────────────────────

    def start(self) -> None:
        """UI thread'ini arka planda başlatır; hazır olana kadar bekler."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def stop(self) -> None:
        if self._root:
            self._root.after(0, self._root.destroy)

    # ─── Pencere Oluşturma ────────────────────────────────────────────────────

    def _run(self) -> None:
        """Tkinter event loop — ayrı thread'de çalışır."""
        self._root = tk.Tk()
        self._root.title("AI Answer")

        # Boyut ve konum
        w, h = config.OVERLAY_WIDTH, config.OVERLAY_HEIGHT
        self._root.geometry(f"{w}x{h}+50+50")
        self._root.minsize(300, 80)

        # Pencere özellikleri
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", config.OVERLAY_ALPHA)
        self._root.overrideredirect(True)   # başlık çubuğunu gizle

        # Arka plan rengi
        self._root.configure(bg=config.OVERLAY_BG_COLOR)

        self._build_ui()
        self._ready.set()
        self._root.mainloop()

    def _build_ui(self) -> None:
        """Pencere içeriğini oluşturur."""
        root = self._root

        # ── Başlık çubuğu (sürükle için) ──
        title_bar = tk.Frame(root, bg="#0f0f23", height=24, cursor="fleur")
        title_bar.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            title_bar,
            text="🎓 AI Answer",
            bg="#0f0f23",
            fg="#7c83fd",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        title_lbl.pack(side=tk.LEFT, padx=8, pady=2)

        close_btn = tk.Button(
            title_bar,
            text="✕",
            command=self.stop,
            bg="#0f0f23",
            fg="#ff6b6b",
            font=("Segoe UI", 9),
            bd=0,
            padx=6,
            cursor="hand2",
            activebackground="#2a2a4a",
            activeforeground="#ff6b6b",
        )
        close_btn.pack(side=tk.RIGHT, padx=4, pady=2)

        # Sürükleme olayları
        for widget in (title_bar, title_lbl):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_motion)

        # ── Cevap etiketi ──
        answer_font = tkfont.Font(family="Segoe UI", size=config.OVERLAY_FONT_SIZE, weight="bold")
        self._label = tk.Label(
            root,
            text="⌨  Ctrl+Shift+S ile ekran yakalayın…",
            bg=config.OVERLAY_BG_COLOR,
            fg=config.OVERLAY_FG_COLOR,
            font=answer_font,
            wraplength=config.OVERLAY_WIDTH - 24,
            justify=tk.CENTER,
            padx=12,
            pady=12,
        )
        self._label.pack(fill=tk.BOTH, expand=True)

        # ── Alt durum çubuğu ──
        status_bar = tk.Frame(root, bg="#0d0d1f", height=20)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_lbl = tk.Label(
            status_bar,
            text="Hazır",
            bg="#0d0d1f",
            fg="#555577",
            font=("Segoe UI", 8),
            anchor="e",
        )
        self._status_lbl.pack(side=tk.RIGHT, padx=8)

    # ─── Sürükle / Taşı ────────────────────────────────────────────────────

    def _drag_start(self, event: tk.Event) -> None:
        self._drag_start_x = event.x_root - self._root.winfo_x()
        self._drag_start_y = event.y_root - self._root.winfo_y()

    def _drag_motion(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_start_x
        y = event.y_root - self._drag_start_y
        self._root.geometry(f"+{x}+{y}")

    # ─── Güvenli UI Güncelleme ──────────────────────────────────────────────

    def _safe_update(self, fn) -> None:
        """Ana thread dışından tkinter widget güncellemek için."""
        if self._root:
            self._root.after(0, fn)

    # ─── Genel API ─────────────────────────────────────────────────────────

    def show_answer(self, answer: str) -> None:
        """Cevabı overlay'de gösterir (herhangi bir thread'den çağrılabilir)."""
        def _update():
            if self._label:
                display = answer if answer else "⚠  Cevap alınamadı."
                self._label.config(text=display)
            if self._status_lbl:
                self._status_lbl.config(text="✓ Yanıt alındı")
            if not self._visible:
                self._root.deiconify()
                self._visible = True
        self._safe_update(_update)
        logger.debug("Overlay güncellendi: %s", answer[:50] if answer else "boş")

    def set_status(self, message: str) -> None:
        """Alt durum çubuğunu günceller."""
        def _update():
            if self._status_lbl:
                self._status_lbl.config(text=message)
        self._safe_update(_update)

    def toggle(self) -> None:
        """Pencereyi gizler veya gösterir (Ctrl+Shift+H kısayolu)."""
        def _toggle():
            if self._visible:
                self._root.withdraw()
                self._visible = False
                logger.debug("Overlay gizlendi.")
            else:
                self._root.deiconify()
                self._root.lift()
                self._visible = True
                logger.debug("Overlay gösterildi.")
        self._safe_update(_toggle)

    def set_loading(self) -> None:
        """Yükleniyor animasyonu gösterir (API isteği süresince)."""
        def _update():
            if self._label:
                self._label.config(text="⏳  AI yanıtı alınıyor…")
            if self._status_lbl:
                self._status_lbl.config(text="İşleniyor…")
        self._safe_update(_update)

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()
