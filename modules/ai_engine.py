"""
modules/ai_engine.py — Modül 3: AI Cevap Motoru

Sorumluluklar:
  - OpenAI GPT-4o API entegrasyonu
  - Prompt şablonlarını dosyadan yükleme (çoktan seçmeli / açık uçlu)
  - API timeout ve exponential backoff yönetimi
  - Kısa, net cevap çıkarma
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import openai

import config

logger = logging.getLogger(__name__)

# ─── OpenAI istemcisi ─────────────────────────────────────────────────────────
_client: Optional[openai.OpenAI] = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY tanımlı değil. "
                ".env dosyasını kontrol edin."
            )
        _client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_TIMEOUT,
        )
    return _client


# ─── Prompt Yönetimi ──────────────────────────────────────────────────────────

def _load_prompt(path: Path, extracted_text: str) -> str:
    """Prompt şablonunu dosyadan okur ve {extracted_text} yer tutucusunu doldurur."""
    try:
        template = path.read_text(encoding="utf-8")
        return template.format(extracted_text=extracted_text)
    except FileNotFoundError:
        logger.warning("Prompt dosyası bulunamadı: %s — varsayılan kullanılıyor", path)
        return (
            "Sen bir sınav asistanısın. Aşağıdaki soruyu yanıtla. "
            "Yalnızca kısa, net cevabı ver.\n\nSoru:\n" + extracted_text
        )


def build_prompt(extracted_text: str, multiple_choice: bool = False) -> str:
    """Soru türüne göre uygun prompt şablonunu yükler."""
    prompt_path = (
        config.PROMPT_MULTIPLE_CHOICE if multiple_choice else config.PROMPT_OPEN_ENDED
    )
    return _load_prompt(prompt_path, extracted_text)


# ─── API Çağrısı ──────────────────────────────────────────────────────────────

def _call_api_with_backoff(prompt: str) -> str:
    """
    OpenAI API'ye istek atar.
    Hız sınırı (429) durumunda max 3 deneme × exponential backoff uygular.
    """
    max_retries = 3
    delay = 2.0  # saniye

    for attempt in range(1, max_retries + 1):
        try:
            client = _get_client()
            t0 = time.monotonic()
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.0,   # deterministik cevap
            )
            elapsed = time.monotonic() - t0

            if elapsed > 5:
                logger.warning(
                    "API yanıt süresi %s saniyeyi aştı: %.1fs",
                    5,
                    elapsed,
                )

            answer = response.choices[0].message.content or ""
            logger.debug("API yanıtı alındı (%.1fs): %s", elapsed, answer[:80])
            return answer.strip()

        except openai.RateLimitError:
            if attempt == max_retries:
                logger.error("API hız sınırı — max deneme sayısına ulaşıldı.")
                raise
            wait = delay * (2 ** (attempt - 1))
            logger.warning("Rate limit — %ds bekleniyor (deneme %d/%d)", wait, attempt, max_retries)
            time.sleep(wait)

        except openai.APITimeoutError:
            logger.error("API isteği zaman aşımına uğradı (%ds).", config.OPENAI_TIMEOUT)
            raise

        except openai.APIStatusError as exc:
            logger.error("API hatası %s: %s", exc.status_code, exc.message)
            raise

    return ""  # ulaşılamaz; mypy için


# ─── Ana Fonksiyon ────────────────────────────────────────────────────────────

def get_answer(extracted_text: str, multiple_choice: bool = False) -> str:
    """
    OCR çıktısını alır, prompt oluşturur, GPT-4o'ya gönderir ve cevabı döndürür.

    Args:
        extracted_text: OCR'dan gelen ham metin
        multiple_choice: True → çoktan seçmeli prompt; False → açık uçlu prompt

    Returns:
        AI cevabı (string). Hata durumunda boş string.
    """
    if not extracted_text.strip():
        logger.warning("Boş metin geldi — API çağrısı atlandı.")
        return ""

    prompt = build_prompt(extracted_text, multiple_choice=multiple_choice)
    logger.debug("Prompt oluşturuldu (%d kar.)", len(prompt))

    try:
        answer = _call_api_with_backoff(prompt)
        return answer
    except Exception as exc:  # noqa: BLE001
        logger.error("AI cevabı alınamadı: %s", exc)
        return ""
