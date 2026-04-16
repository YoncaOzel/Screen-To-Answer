"""
config.py — Uygulama konfigürasyonu
Tesseract path, API anahtarları ve genel ayarlar buradan yönetilir.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizini
BASE_DIR = Path(__file__).parent

# .env dosyasını yükle
load_dotenv(BASE_DIR / ".env")

# ─── OpenAI ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TIMEOUT: int = 30          # saniye — API isteği maksimum bekleme süresi
OPENAI_MAX_TOKENS: int = 512

# ─── Tesseract OCR ───────────────────────────────────────────────────────────
TESSERACT_PATH: str = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
OCR_LANG: str = os.getenv("OCR_LANG", "tur+eng")

# ─── Ekran Yakalama ──────────────────────────────────────────────────────────
HOTKEY_CAPTURE: str = os.getenv("HOTKEY_CAPTURE", "ctrl+shift+s")
HOTKEY_TOGGLE: str = os.getenv("HOTKEY_TOGGLE", "ctrl+shift+h")
MOUSE_CAPTURE_BUTTON: str = os.getenv("MOUSE_CAPTURE_BUTTON", "middle")  # middle, right, x1, x2 veya "" (devre dışı)

# ─── Overlay ─────────────────────────────────────────────────────────────────
OVERLAY_ALPHA: float = float(os.getenv("OVERLAY_ALPHA", "0.82"))
OVERLAY_FONT_SIZE: int = 16
OVERLAY_TRANSPARENT_KEY: str = "#fefffe"   # root arka planı — bu renk şeffaf yapılır (siyahtan uzak)
OVERLAY_BG_COLOR: str = "#1e1e1e"          # koyu gri — label arka planı görünür kalır
OVERLAY_FG_COLOR: str = "#ffffff"          # beyaz metin — koyu arka planda okunaklı

# ─── Loglama ─────────────────────────────────────────────────────────────────
LOGS_DIR: Path = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_LEVEL: int = logging.DEBUG

# ─── Prompt Dosyaları ────────────────────────────────────────────────────────
PROMPTS_DIR: Path = BASE_DIR / "prompts"
PROMPT_MULTIPLE_CHOICE: Path = PROMPTS_DIR / "multiple_choice.txt"
PROMPT_OPEN_ENDED: Path = PROMPTS_DIR / "open_ended.txt"


def validate_config() -> list[str]:
    """Kritik konfigürasyon değerlerini doğrula; sorunları liste olarak döndür."""
    issues: list[str] = []
    if not OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY tanımlı değil (.env dosyasını kontrol edin)")
    if not Path(TESSERACT_PATH).exists():
        issues.append(
            f"Tesseract bulunamadı: {TESSERACT_PATH}\n"
            "  → https://github.com/UB-Mannheim/tesseract/wiki adresinden indirin"
        )
    return issues
