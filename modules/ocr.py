"""
modules/ocr.py — Modül 2: OCR / Metin Tanıma

Sorumluluklar:
  - Görüntü ön işleme (gri tonlama, threshold, keskinleştirme)
  - pytesseract ile metin çıkarma (Türkçe + İngilizce)
  - OCR başarısız olduğunda anlamlı hata döndürme
"""
from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageFilter

import config

logger = logging.getLogger(__name__)

# Tesseract ikili dosyasını konfigürasyondan ayarla
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH


# ─── Görüntü Ön İşleme ───────────────────────────────────────────────────────

def _preprocess_image(img: Image.Image) -> Image.Image:
    """
    OCR doğruluğunu artırmak için görüntüye ön işleme uygular:
      1. Gri tonlamaya çevir
      2. Boyutu 2x büyüt (küçük metinler için)
      3. Adaptive threshold (siyah-beyaz)
      4. Hafif keskinleştirme
    """
    # 1. Gri tonlama
    gray = img.convert("L")

    # 2. NumPy dizisine çevir ve ölçekle
    arr = np.array(gray)
    h, w = arr.shape
    # Küçük görüntüleri büyüt
    if w < 800:
        arr = cv2.resize(arr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # 3. Adaptive threshold (gürültü toleranslı)
    arr = cv2.adaptiveThreshold(
        arr, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8,
    )

    # 4. Dönüştür ve keskinleştir
    processed = Image.fromarray(arr)
    processed = processed.filter(ImageFilter.SHARPEN)
    return processed


# ─── Metin Çıkarma ───────────────────────────────────────────────────────────

def extract_text(img: Image.Image, lang: Optional[str] = None) -> str:
    """
    Verilen PIL Image'dan metin çıkarır.

    Args:
        img:  Kaynak görüntü
        lang: Tesseract dil kodu (None → config.OCR_LANG)

    Returns:
        Çıkarılan metin (başındaki/sonundaki boşluklar temizlenmiş).
        Başarısız olursa boş string döner.
    """
    language = lang or config.OCR_LANG
    custom_config = r"--oem 3 --psm 6"   # OEM 3: LSTM+Legacy, PSM 6: uniform block text

    try:
        processed = _preprocess_image(img)
        text: str = pytesseract.image_to_string(
            processed,
            lang=language,
            config=custom_config,
        )
        text = text.strip()

        if not text:
            logger.warning("OCR metin bulamadı — görüntü çok düşük kaliteli olabilir.")
            return ""

        logger.debug("OCR başarılı: %d karakter", len(text))
        return text

    except pytesseract.TesseractNotFoundError:
        logger.error(
            "Tesseract bulunamadı: %s\n"
            "  → Kurulum: https://github.com/UB-Mannheim/tesseract/wiki",
            config.TESSERACT_PATH,
        )
        raise

    except Exception as exc:  # noqa: BLE001
        logger.error("OCR hatası: %s", exc, exc_info=True)
        return ""


def is_multiple_choice(text: str) -> bool:
    """
    Metinde A) / B) / (A) / A. gibi çoktan seçmeli şıklar varsa True döner.
    Prompt şablonu seçimi için kullanılır.
    """
    import re
    pattern = r"\b[A-Ea-e][)\.]"
    matches = re.findall(pattern, text)
    return len(matches) >= 2
