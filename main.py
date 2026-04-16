"""
main.py — Giriş Noktası

Uçtan uca akış:
  Ctrl+Shift+S → Ekran Yakalama → OCR → AI Engine → Overlay
  Ctrl+Shift+H → Overlay Gizle / Göster

Loglama: logs/session_YYYY-MM-DD.log
"""
from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

import config
from modules.capture import HotkeyListener, capture_roi
from modules.ocr import extract_text, is_multiple_choice
from modules.ai_engine import get_answer
from modules.overlay import OverlayWindow

# ─── Loglama Kurulumu ─────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    log_file = config.LOGS_DIR / f"session_{datetime.now().strftime('%Y-%m-%d')}.log"
    fmt = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(level=config.LOG_LEVEL, format=fmt, handlers=handlers)
    return logging.getLogger("main")


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class ScreenAnalyzerApp:
    """Tüm modülleri orchestrate eden ana uygulama sınıfı."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("ScreenAnalyzerApp")
        self.overlay = OverlayWindow()
        self._pipeline_lock = threading.Lock()   # aynı anda tek pipeline çalışsın

    def _run_pipeline(self) -> None:
        """
        Ekran yakalama → OCR → AI pipeline.
        Yeni bir thread'de çalışır (UI donmasın).
        """
        if self._pipeline_lock.locked():
            self.logger.warning("Pipeline zaten çalışıyor, istek yoksayıldı.")
            return

        with self._pipeline_lock:
            try:
                # 1. Ekran yakalama
                self.logger.info("── YENİ OTURUM ──")
                self.overlay.set_status("📷  Ekran yakalanıyor…")
                img = capture_roi()
                if img is None:
                    self.overlay.set_status("İptal edildi.")
                    return

                # 2. OCR
                self.overlay.set_status("🔍  Metin tanınıyor…")
                text = extract_text(img)
                if not text:
                    self.overlay.show_answer("⚠  Metin tanınamadı. Lütfen daha net bir alan seçin.")
                    self.logger.warning("OCR sonucu boş döndü.")
                    return
                self.logger.info("OCR çıktısı (%d kar.): %s", len(text), text[:120])

                # 3. Soru türü tespiti
                mc = is_multiple_choice(text)
                self.logger.info("Soru türü: %s", "Çoktan seçmeli" if mc else "Açık uçlu")

                # 4. AI engine
                self.overlay.set_loading()
                answer = get_answer(text, multiple_choice=mc)
                if not answer:
                    self.overlay.show_answer("⚠  AI cevabı alınamadı.")
                    return

                # 5. Overlay'e cevabı yaz
                self.overlay.show_answer(answer)
                self.logger.info("Cevap: %s", answer)

                # 6. Log kaydı
                self._write_log_entry(text, answer)

            except Exception as exc:  # noqa: BLE001
                self.logger.error("Pipeline hatası: %s", exc, exc_info=True)
                self.overlay.show_answer(f"⚠  Hata: {exc}")

    def _write_log_entry(self, question: str, answer: str) -> None:
        """Oturum log dosyasına soru-cevap kaydı ekler."""
        log_file = config.LOGS_DIR / f"session_{datetime.now().strftime('%Y-%m-%d')}.log"
        entry = (
            f"\n{'─' * 60}\n"
            f"[{datetime.now().strftime('%H:%M:%S')}] SORU:\n{question[:500]}\n"
            f"CEVAP: {answer}\n"
        )
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as exc:
            self.logger.error("Log yazma hatası: %s", exc)

    def on_capture(self) -> None:
        """Kısayol: Ctrl+Shift+S"""
        threading.Thread(target=self._run_pipeline, daemon=True).start()

    def on_toggle(self) -> None:
        """Kısayol: Ctrl+Shift+H"""
        self.overlay.toggle()

    def run(self) -> None:
        """Uygulamayı başlatır (bloke eden çağrı)."""
        # Konfigürasyon doğrulama
        issues = config.validate_config()
        if issues:
            for issue in issues:
                self.logger.error("⚠  Konfigürasyon sorunu: %s", issue)
            print("\n[!] Konfigürasyon sorunları tespit edildi:")
            for issue in issues:
                print(f"    • {issue}")
            print("\nLütfen sorunları çözüp uygulamayı yeniden başlatın.\n")
            # Tesseract yoksa yine de devam et (OCR modülü hata verir)

        # Overlay'i başlat
        self.overlay.start()
        self.logger.info("Overlay başlatıldı.")

        # Kısayol dinleyiciyi başlat
        listener = HotkeyListener(
            on_capture=self.on_capture,
            on_toggle=self.on_toggle,
        )
        listener.start()
        self.logger.info(
            "Uygulama hazır. %s → Yakalama | %s → Gizle/Göster",
            config.HOTKEY_CAPTURE,
            config.HOTKEY_TOGGLE,
        )
        print(
            f"\n✅  AI Screen Analyzer başlatıldı.\n"
            f"   {config.HOTKEY_CAPTURE.upper()}  →  Ekran yakala & AI cevabı al\n"
            f"   {config.HOTKEY_TOGGLE.upper()}  →  Overlay'i gizle / göster\n"
            f"   Çıkmak için terminal penceresini kapatın.\n"
        )

        # Ana thread'i canlı tut (overlay thread daemon olduğu için)
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Kullanıcı çıkışı (KeyboardInterrupt).")
            listener.stop()
            self.overlay.stop()


# ─── Giriş Noktası ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _setup_logging()
    app = ScreenAnalyzerApp()
    app.run()
