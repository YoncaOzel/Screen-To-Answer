"""
modules/overlay.py — Modül 4: Overlay Arayüzü

Sorumluluklar:
  - Şeffaf arka planlı, always-on-top tkinter penceresi (kamufle modu)
  - Cevabı büyük puntoda gösterme
  - Pencereyi sürükle-bırak ile taşıma
  - İçeriğe göre otomatik pencere boyutlandırma
  - Gizle / Göster (Ctrl+Shift+H kısayolu main.py'den çağrılır)
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
    Şeffaf, always-on-top tkinter penceresi (kamufle/stealth modu).

    - Pencere arka planı tamamen şeffaf (transparentcolor ile)
    - Sadece metin kabarcığı görünür
    - Pencere boyutu cevap içeriğine göre otomatik ayarlanır
    - Başlık ve durum çubuğu yoktur (kamufle için)

    Kullanım:
        overlay = OverlayWindow()
        overlay.start()          # arka plan thread'de arayüzü başlatır
        overlay.show_answer("C") # ana thread'den güvenle çağrılır
        overlay.toggle()         # gizle / göster (Ctrl+Shift+H)
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
        self._drag_moved: bool = False   # sürükleme mi yoksa tıklama mı?

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
        self._root.title("")

        # Pencere özellikleri
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", config.OVERLAY_ALPHA)
        self._root.overrideredirect(True)   # başlık çubuğunu gizle

        # Arka planı şeffaf yap: root key rengi + transparentcolor
        self._root.configure(bg=config.OVERLAY_TRANSPARENT_KEY)
        self._root.attributes("-transparentcolor", config.OVERLAY_TRANSPARENT_KEY)

        # Başlangıç konumu (boyut içerik sonrası ayarlanır)
        self._root.geometry("+50+50")

        self._build_ui()
        self._ready.set()
        self._root.mainloop()

    def _build_ui(self) -> None:
        """Pencere içeriğini oluşturur — sadece metin kabarcığı."""
        root = self._root

        # Frame: tamamen şeffaf (arka plan yok)
        self._frame = tk.Frame(
            root,
            bg=config.OVERLAY_TRANSPARENT_KEY,
            padx=0,
            pady=0,
        )
        self._frame.pack()

        # Label: çok küçük koyu arka plan — ClearType font rendering için gerekli
        # (şeffaf bg üzerinde Tkinter text anti-aliasing bozulur)
        answer_font = tkfont.Font(
            family="Segoe UI", size=config.OVERLAY_FONT_SIZE
        )
        self._label = tk.Label(
            self._frame,
            text="",
            bg=config.OVERLAY_BG_COLOR,   # koyu arka plan → metin düzgün render edilir
            fg=config.OVERLAY_FG_COLOR,
            font=answer_font,
            wraplength=400,
            justify=tk.CENTER,
            padx=10,
            pady=6,
        )
        self._label.pack()

        # Olaylar: frame ve label üzerinden
        for widget in (self._frame, self._label):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_click)

    # ─── İçeriğe Göre Boyutlandır ────────────────────────────────────────────

    def _resize_to_content(self) -> None:
        """Pencereyi mevcut metin içeriğine tam sığacak şekilde yeniden boyutlandırır."""
        self._root.update_idletasks()
        w = self._label.winfo_reqwidth()
        h = self._label.winfo_reqheight()
        x = self._root.winfo_x()
        y = self._root.winfo_y()
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    # ─── Sürükle / Taşı ────────────────────────────────────────────────────

    def _drag_start(self, event: tk.Event) -> None:
        self._drag_start_x = event.x_root - self._root.winfo_x()
        self._drag_start_y = event.y_root - self._root.winfo_y()
        self._drag_moved = False

    def _drag_motion(self, event: tk.Event) -> None:
        dx = abs(event.x_root - (self._drag_start_x + self._root.winfo_x()))
        dy = abs(event.y_root - (self._drag_start_y + self._root.winfo_y()))
        if dx > 4 or dy > 4:
            self._drag_moved = True
        x = event.x_root - self._drag_start_x
        y = event.y_root - self._drag_start_y
        self._root.geometry(f"+{x}+{y}")

    def _on_click(self, event: tk.Event) -> None:
        """Fare bırakıldığında: sürükleme değilse gizle."""
        if not self._drag_moved:
            self._root.withdraw()
            self._visible = False
            logger.debug("Tıklamayla gizlendi.")

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
                self._resize_to_content()
            if not self._visible:
                self._root.deiconify()
                self._visible = True
        self._safe_update(_update)
        logger.debug("Overlay güncellendi: %s", answer[:50] if answer else "boş")

    def set_status(self, message: str) -> None:
        """Durum bilgisini etiket üzerinde kısaca gösterir."""
        def _update():
            if self._label:
                self._label.config(text=message)
                self._resize_to_content()
        self._safe_update(_update)

    def hide(self) -> None:
        """Pencereyi gizler (pipeline başlamadan önce çağrılır)."""
        def _hide():
            self._root.withdraw()
            self._visible = False
        self._safe_update(_hide)

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
        """Yükleniyor durumunu gösterir (API isteği süresince)."""
        def _update():
            if self._label:
                self._label.config(text="⏳  AI yanıtı alınıyor…")
                self._resize_to_content()
        self._safe_update(_update)

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()
