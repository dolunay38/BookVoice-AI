# KI-ARCHIV PRO

<div align="center">

![KI-ARCHIV PRO](https://img.shields.io/badge/KI--ARCHIV%20PRO-v1.0-1E3A5F?style=for-the-badge&logo=python&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Offline](https://img.shields.io/badge/100%25-Offline-27AE60?style=for-the-badge&logo=shield&logoColor=white)
![DSGVO](https://img.shields.io/badge/DSGVO-konform-27AE60?style=for-the-badge&logo=eu&logoColor=white)
![Status](https://img.shields.io/badge/Status-In%20Betrieb-brightgreen?style=for-the-badge)

**Lokales, datenschutzfreundliches KI-System zum Transkribieren, Übersetzen und Archivieren von Wissen.**

Alles läuft vollständig **offline** auf dem eigenen System — keine Cloud, keine Datenweitergabe.  
Ideal für Schulen, Seminare, Behörden, Kanzleien und Unternehmen mit hohen Datenschutzanforderungen.

[📖 Dokumentation](#-dokumentation) · [🚀 Schnellstart](#-installation--schnellstart) · [🧱 Architektur](#-architektur) · [⚙️ Konfiguration](#-konfiguration)

</div>

---

## ✨ Was kann KI-ARCHIV PRO?

| Funktion | Technologie | Beschreibung |
|---|---|---|
| 🎙 Audio-Transkription | Whisper / FastWhisper | Mehrsprachig (DE/TR/EN), Zeitstempel, Reintext, optionale KI-Korrektur |
| 📄 OCR & PDF | Tesseract + pdf2image | Scans & Bilder (JPG/PNG/TIFF), native PDFs, optionale Qwen-Korrektur |
| 🌍 Übersetzung (NLLB) | NLLB-200 (Meta AI) | 8 Sprachen offline: DE, EN, TR, FR, ES, RU, AR — ohne Internet |
| 🤖 Übersetzung (LLM) | Qwen via Ollama | Kontextbasierte Übersetzung mit lokalem Sprachmodell |
| ✏️ KI-Korrektur | Qwen 2.5 (3B / 7B) | Rechtschreibung, Fachsprache, amtlicher Stil, religiöse Texte |
| 💬 Lokaler KI-Chat | Ollama + Qwen | Chat in der GUI — Standard (3B) & Premium (7B), vollständig offline |
| 📂 Auto-Archivierung | Python / os.walk | Datumsbasierte Struktur `ARCHIV/YYYY-MM-DD/` — vollautomatisch |
| 📊 Dashboard & Monitoring | CustomTkinter | Docker-Status, Statistiken, Live-Transkript, Logs, Dateimanager |

---

## 🧱 Architektur

```
┌─────────────────────────────────────────────────────────┐
│                    WINDOWS HOST                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │           gui_zentrale_pro.py (CustomTkinter)   │    │
│  │  Dashboard │ Dateimanager │ Live-Transkript      │    │
│  │  System-Logs │ KI-Chat │ Konfiguration           │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │ localhost                      │
│  ┌──────────────────────▼──────────────────────────┐    │
│  │              DOCKER COMPOSE                      │    │
│  │                                                  │    │
│  │  ┌─────────────┐  ┌──────────────────────────┐  │    │
│  │  │   ollama    │  │    ki-archiv-ingest       │  │    │
│  │  │  Port 11434 │  │  ingest_winmaster.py      │  │    │
│  │  │ Qwen 3B/7B  │  │  Whisper │ OCR │ NLLB     │  │    │
│  │  └─────────────┘  └──────────────────────────┘  │    │
│  │  ┌─────────────┐  ┌──────────────────────────┐  │    │
│  │  │ open-webui  │  │   nllb-translator         │  │    │
│  │  │  Port 3000  │  │   Port 5000               │  │    │
│  │  │ Chat & RAG  │  │   FastAPI + NLLB-200       │  │    │
│  │  └─────────────┘  └──────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  E:\Archiv-KI\                                          │
│  ├── EINGABE\        ← Dateien hier ablegen             │
│  ├── ERGEBNISSE\     ← Verarbeitete Ergebnisse          │
│  └── ARCHIV\         ← Originale (YYYY-MM-DD\)          │
└─────────────────────────────────────────────────────────┘
```

### Datenfluss

```
Datei in EINGABE\ ablegen
        ↓  (max. 10 Sekunden)
Ingest-Worker erkennt Datei & Modus (anhand Ordnerpfad)
        ↓
Audio → Whisper Transkription
PDF   → Tesseract OCR
Text  → NLLB oder Qwen Übersetzung / Korrektur
        ↓
Ergebnis → ERGEBNISSE\...
Original → ARCHIV\YYYY-MM-DD\...
        ↓
GUI zeigt Live-Status & Ergebnis in Echtzeit
```

---

## 🔧 Tech Stack

| Bereich | Technologie |
|---|---|
| Sprache | Python 3.10+ |
| GUI-Framework | CustomTkinter |
| Containerisierung | Docker + Docker Compose |
| Transkription | faster-whisper (OpenAI Whisper) |
| OCR | Tesseract-OCR (DE/EN/TR/AR) + pytesseract + pdf2image |
| Offline-Übersetzung | NLLB-200-distilled-600M (Meta AI) via FastAPI |
| LLM-Backend | Ollama (Qwen 2.5 3B / 7B) |
| LLM-Chat-UI | Open-WebUI (optional, RAG-fähig) |
| Logging | Python logging mit FlushHandler (Echtzeit-GUI) |

---

## 📊 Projektstatus

| Metrik | Wert |
|---|---|
| Verarbeitete Audio-Dateien | **453** |
| Verarbeitete Textdateien | **14** |
| Unterstützte Sprachen (NLLB) | **8** (DE, EN, TR, FR, ES, RU, AR) |
| Unterstützte Audio-Formate | `.wav .mp3 .m4a .ogg .flac .opus` |
| Unterstützte Dokument-Formate | `.pdf .jpg .jpeg .png .tiff .tif` |
| Plattform | Windows 10/11 (Docker-Backend plattformunabhängig) |

---

## ⚙️ Systemvoraussetzungen

### Mindestanforderungen (CPU-Betrieb)

| Komponente | Minimum | Empfohlen |
|---|---|---|
| Betriebssystem | Windows 10 64-bit | Windows 11 64-bit |
| CPU | 4 Kerne | 8+ Kerne |
| RAM | 16 GB | 32 GB |
| Speicherplatz | ~30 GB | 100+ GB |
| Python | 3.10+ | 3.11 |
| Docker | Docker Desktop | Docker Desktop (aktuell) |

### Optional: GPU-Beschleunigung

- NVIDIA GPU mit CUDA-Unterstützung
- Aktuelle NVIDIA-Treiber (CUDA 11.x / 12.x)
- Docker Desktop mit WSL2-Backend
- Vorteil: Whisper-Transkription **5–10× schneller**

---

## 🚀 Installation & Schnellstart

### 1. Voraussetzungen installieren

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Python 3.11](https://www.python.org/) — **mit `py`-Launcher installieren!**
- [Git](https://git-scm.com/downloads) (optional)

### 2. Projekt klonen

```bash
git clone https://github.com/dolunay38/KI-ARCHIV-PRO.git
cd KI-ARCHIV-PRO
```

### 3. Datenordner anlegen (außerhalb des Repos)

```
E:\Archiv-KI\
  EINGABE\
  ERGEBNISSE\
  ARCHIV\
  models\whisper_models\
  nllb_models\
  ollama_storage\
```

### 4. `.env` anpassen

```env
ARCHIV_PFAD=E:/Archiv-KI/ERGEBNISSE
MODELS_DIR=E:/Archiv-KI/ollama_storage
NLLB_MODEL_PATH=E:/Archiv-KI/nllb_models
WHISPER_MODEL_PATH=E:/Archiv-KI/models/whisper_models
STORAGE_PATH=E:/Archiv-KI/webui_storage
```

> Pfade in `compose.yaml` und `config.ini` ggf. ebenfalls anpassen.

### 5. Docker-Container starten & Modelle laden

```bash
# Container bauen und starten
docker compose up -d --build

# Qwen-Modelle laden (einmalig, dauert einige Minuten)
docker exec -it ollama ollama pull qwen2.5:3b
docker exec -it ollama ollama pull qwen2.5:7b

# Status prüfen
docker compose ps
```

### 6. GUI starten

```bash
# Schnellstart (installiert Python-Dependencies automatisch)
GUI_STARTEN.bat

# Oder: Diagnose-Start (mit Docker-Check)
KI-ARCHIV-DIAGNOSE_START.bat
```

### 7. Erste Datei verarbeiten

1. Audio-Datei (`.mp3`, `.wav`) in `E:\Archiv-KI\EINGABE\` kopieren
2. Kurz warten (max. 10 Sekunden)
3. GUI → Tab **📝 Live-Transkript** → Transkription erscheint in Echtzeit
4. Ergebnis in `E:\Archiv-KI\ERGEBNISSE\EINGABE\` prüfen

---

## 🗂️ Pipelines — Modus-Erkennung über Ordner

Der Ingest-Worker erkennt den Verarbeitungsmodus **vollautomatisch** anhand des Ordners:

| Ordner | Was passiert |
|---|---|
| `EINGABE\` | Audio → Transkription · PDF/Bild → OCR · Text → ablegen |
| `UEBERSETZEN\NACH_DEUTSCH\` | NLLB-Übersetzung → Deutsch |
| `UEBERSETZEN\NACH_TUERKISCH\` | NLLB-Übersetzung → Türkisch |
| `UEBERSETZEN\NACH_ENGLISCH\` | NLLB-Übersetzung → Englisch |
| `UEBERSETZEN_QWEN\QWEN_DEUTSCH\` | Qwen-Übersetzung → Deutsch |
| `KORREKTUR\` | Qwen-Korrektur (Rechtschreibung / Fachsprache / Stil) |

---

## 📁 Ausgabedateien

| Eingabe | Erzeugte Dateien |
|---|---|
| Audio | `*_whisper_transkript.txt` (mit Zeitstempeln) |
| Audio | `*_whisper_transkript_reintext.txt` (Fließtext) |
| Audio + KI aktiv | `*_whisper_transkript_korrigiert.txt` |
| PDF / Bild | `*_ocr.txt` |
| PDF / Bild + KI | `*_ocr_korrigiert.txt` |
| Text (NLLB) | `*_uebersetzung_nllb.txt` |
| Text (Qwen) | `*_uebersetzung_qwen.txt` |
| Text (Korrektur) | `*_korrigiert.txt` |

---

## ⚙️ Konfiguration

Alle Einstellungen in `config.ini`:

```ini
[AUDIO]
whisper_size = small        # tiny / base / small / medium / large

[SYSTEM]
scan_interval = 10          # Sekunden zwischen Ordner-Scans

[KI_SETTINGS]
enabled = false             # Qwen-Korrektur aktivieren
model = qwen2.5:7b          # Standard-Modell
premium_model = qwen2.5:7b  # Premium-Modell
current_mode = Fach_Korrektur_Rechtschreibung

[NLLB_SETTINGS]
default_tgt_lang_name = NACH_DEUTSCH
```

---

## 🛡️ Datenschutz & DSGVO

- ✅ **Alle Daten bleiben lokal** — kein Cloud-Upload durch KI-ARCHIV PRO
- ✅ **Keine externen API-Aufrufe** — alle KI-Modelle laufen auf dem eigenen System
- ✅ **Keine Telemetrie** — das System kommuniziert nicht nach außen
- ✅ **Geeignet für** Schulen, Behörden, Kanzleien, Unternehmen mit DSGVO-Anforderungen

> ⚠️ Hinweis: Bei Nutzung externer Tools oder eigener Skripte kann dies abweichen.

---

## 📖 Dokumentation

| Dokument | Inhalt |
|---|---|
| [`docs/TECHNIK.md`](docs/TECHNIK.md) | Technische Detaildokumentation (Funktionen, Klassen, Pipelines) |
| [`KI-ARCHIV-PRO_Dokumentation_V1.pdf`](docs/KI-ARCHIV-PRO_Dokumentation_V1.pdf) | Vollständige Projektdokumentation (13 Kapitel) |

---

## 🗺️ Roadmap

- [ ] Speaker Diarization — Sprecher automatisch erkennen und markieren
- [ ] RAG-Integration — ERGEBNISSE als Wissensbasis für kontextbasierte Fragen
- [ ] N8n Workflow-Automation — automatische Einsortierung & Reports
- [ ] GPU-Support (Docker) — nvidia-container-toolkit für schnellere Transkription
- [ ] Weitere NLLB-Sprachpaare (200+ verfügbar)

---

## 👤 Entwickler

**Ismail Aksoy**

Angehender Fachinformatiker für Systemintegration (FISI) mit Fokus IT-Security & Infrastruktur.

KI-ARCHIV PRO ist ein Eigenprojekt, das aus dem konkreten Bedarf an einem datenschutzfreundlichen, offline-fähigen Transkriptions- und Archivierungswerkzeug entstanden ist — entwickelt parallel zur Umschulung und zum [Aksoy-Net Home Lab](https://github.com/dolunay38/aksoy-net-homelab).

- 🔗 GitHub: [github.com/dolunay38](https://github.com/dolunay38)
- 💼 LinkedIn: [Ismail Aksoy](https://linkedin.com/in/ismail-aksoy)
- 🌐 Homelab: [aksoy-net.de](https://aksoy-net.de)

---

<div align="center">

*KI-ARCHIV PRO — Wissen archivieren. Lokal. Sicher. Ohne Cloud.*

</div>
