# AI-Powered Screen Content Analyzer

> **Doktora Tezi Araştırma Aracı** — Yapay zeka destekli araçların sınav performansına etkisini ölçmek için geliştirilmiş Windows masaüstü uygulaması.

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Tesseract OCR** — [UB-Mannheim Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - Kurulum sırasında **Turkish** dil paketini seçin
  - Varsayılan kurulum yolu: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- **OpenAI API Anahtarı** — [platform.openai.com](https://platform.openai.com/api-keys)

### 2. Kurulum

```powershell
# Depoyu klonla
git clone https://github.com/kullaniciadi/Screen-To-Answer.git
cd Screen-To-Answer

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 3. Konfigürasyon

```powershell
# .env.example'ı kopyala
copy .env.example .env
```

`.env` dosyasını düzenle:
```
OPENAI_API_KEY=sk-...
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 4. Çalıştır

```powershell
python main.py
```

> **Not:** `pynput` global kısayol için yönetici yetkisi gerekebilir. Sorun yaşarsan `python main.py`'yi "Yönetici Olarak Çalıştır" ile başlat.

---

## 🎮 Kullanım

| Kısayol | İşlev |
|---|---|
| `Ctrl+Shift+S` | Ekran alanı seç → OCR → AI cevabı al |
| `Ctrl+Shift+H` | Overlay penceresini gizle / göster |
| `Esc` (ROI seçimde) | Seçimi iptal et |

**Akış:**
1. `Ctrl+Shift+S` → Ekran karartılır, imleç artı (+) şekline döner
2. Soru alanını sürükle-seç
3. Birkaç saniye içinde şeffaf overlay penceresinde cevap görünür
4. Cevabı gizlemek için `Ctrl+Shift+H`

---

## 📁 Proje Yapısı

```
Screen-To-Answer/
├── main.py              # Giriş noktası & orchestrator
├── config.py            # Konfigürasyon yönetimi
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Örnek ortam değişkenleri
│
├── modules/
│   ├── capture.py       # Ekran yakalama + ROI seçici + kısayol
│   ├── ocr.py           # OCR + görüntü ön işleme
│   ├── ai_engine.py     # GPT-4o API entegrasyonu
│   └── overlay.py       # Always-on-top şeffaf arayüz
│
├── prompts/
│   ├── multiple_choice.txt   # Çoktan seçmeli prompt
│   └── open_ended.txt        # Açık uçlu prompt
│
├── logs/                # Oturum logları (otomatik oluşturulur)
└── tests/               # Birim testleri
    ├── test_capture.py
    ├── test_ocr.py
    └── test_ai_engine.py
```

---

## 🧪 Testler

```powershell
pytest tests/ -v
```

---

## ⚙️ Konfigürasyon Referansı

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API anahtarı (zorunlu) |
| `OPENAI_MODEL` | `gpt-4o` | Kullanılacak model |
| `TESSERACT_PATH` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Tesseract ikili yolu |
| `OCR_LANG` | `tur+eng` | OCR dil kodu |
| `OVERLAY_ALPHA` | `0.85` | Overlay saydamlığı (0.0–1.0) |
| `HOTKEY_CAPTURE` | `ctrl+shift+s` | Yakalama kısayolu |
| `HOTKEY_TOGGLE` | `ctrl+shift+h` | Gizle/Göster kısayolu |

---

## 🔧 Sorun Giderme

**Tesseract bulunamadı hatası:**
```
TESSERACT_PATH değişkenini .env dosyasında doğru yola ayarlayın.
```

**Kısayol çalışmıyor:**
- Uygulamayı Yönetici olarak çalıştırın

**OCR boş sonuç döndürüyor:**
- Daha net/yüksek çözünürlüklü bir alan seçin
- `config.py`'de `OCR_LANG` değerini kontrol edin

**API yanıt vermiyor:**
- `OPENAI_API_KEY` değerini doğrulayın
- İnternet bağlantısını kontrol edin

---

## 📋 Teknik Yığın

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.10+ |
| Ekran Yakalama | `mss` |
| Kısayol Dinleme | `pynput` |
| OCR | `pytesseract` + Tesseract |
| Görüntü İşleme | `Pillow`, `OpenCV` |
| AI API | `openai` (GPT-4o) |
| Arayüz | `tkinter` |
| Konfigürasyon | `python-dotenv` |

---

> *Bu araç yalnızca kontrollü araştırma ortamında kullanılmak üzere tasarlanmıştır.*
