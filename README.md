# 📚 BookVoice-AI

**Open-Source KI-Hörbuch Studio** — Text zu Sprache mit Voice Cloning, Transkription und Hörbuch-Produktion.

[![GitHub](https://img.shields.io/badge/GitHub-dolunay38-black)](https://github.com/dolunay38/BookVoice-AI)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com)

---

## 🏗️ Architektur

```
Browser (DE/TR/EN)
    ↓
ki_archiv_tts_web.html (Single-File Frontend)
    ↓
Nginx Reverse Proxy (Port 7502 → /api)
    ↓
tts_server.py (FastAPI, Port 7500)
    ↓
┌─────────────────────────────────┐
│ XTTS-v2 (lokal, CPU/GPU)        │
│ Edge TTS (Microsoft Cloud)      │
│ GPU Colab (Cloudflare Tunnel)   │
│ FastWhisper (Transkription)     │
└─────────────────────────────────┘
```

---

## ✨ Features

### 🎙️ Text-to-Speech Engines
| Engine | Qualität | Speed | Voice Cloning | Sprachen |
|--------|----------|-------|---------------|---------|
| XTTS-v2 (CPU) | ⭐⭐⭐⭐⭐ | Langsam | ✅ | TR/DE/EN + |
| Edge TTS | ⭐⭐⭐ | Sehr schnell | ❌ | 400+ Stimmen |
| GPU Colab | ⭐⭐⭐⭐⭐ | Schnell | ✅ | TR/DE/EN + |

### 📝 Transkription (FastWhisper)
- **Modelle:** Small (CPU), Medium, Large-v3
- **Formate:** MP3, WAV, M4A, OGG, MP4, MKV, WebM
- **Sprachen:** TR, DE, EN, Auto-Erkennung
- **Export:** TXT + SRT (mit Zeitstempel)
- **Background Job System** — kein Cloudflare Timeout
- **Ordner-Verwaltung** — eigene Struktur erstellen

### 📖 Unterstützte Dateiformate
| Kategorie | Formate |
|-----------|---------|
| Dokumente | TXT, MD, CSV, RTF |
| Word | DOC, DOCX, ODT |
| PDF | PyPDF2 + Calibre |
| eBooks | EPUB, MOBI, AZW3, FB2 |
| Präsentationen | PPTX, PPT |
| Tabellen | XLSX, XLS |
| Bilder (OCR) | JPG, PNG, WEBP, TIFF |
| Audio (Stimme) | WAV, MP3, M4A, OGG |

### 🎭 Emotion-Tag System
```
[dramatic] [whispers] [sighs] [laughs] [sad] [happy] [pause]
```
Auto-Erkennung oder manuell setzen.

### 🌐 Mehrsprachige GUI
- 🇩🇪 Deutsch / 🇹🇷 Türkisch / 🇬🇧 Englisch
- Vollständige i18n Unterstützung

---

## 🚀 Installation

### Voraussetzungen
- Docker + Docker Compose
- 8GB RAM (min), 16GB empfohlen
- Ubuntu Server / Windows WSL2

### Quick Start
```bash
git clone https://github.com/dolunay38/BookVoice-AI.git
cd BookVoice-AI
docker compose -f compose.server.yaml build
docker compose -f compose.server.yaml up -d
```

Dann öffnen: `http://localhost:7502`

### SCP Deploy (Homelab)
```bash
scp tts_server.py aksadmin@SERVER_IP:/pfad/ki-archiv/
scp ki_archiv_tts_web.html aksadmin@SERVER_IP:/pfad/ki-archiv/
cd /pfad/ki-archiv
docker compose -f compose.server.yaml build ki-archiv-tts
docker compose -f compose.server.yaml up -d ki-archiv-tts
```

---

## 📁 Ordnerstruktur (Server)

```
/app/
├── HOERBUCH/          → Fertige Hörbücher (MP3/M4B/WAV)
├── TRANSKRIPTIONEN/   → FastWhisper Texte (TXT/SRT)
├── EINGABE/           → Rohdateien (temporär)
├── ARCHIV/            → Verarbeitete Dateien
├── tts_models/        → XTTS-v2 Modell + Stimmen
├── covers/            → Buchcover
└── musik/             → Hintergrundmusik
```

---

## ☁️ Google Colab (GPU)

Für schnelle GPU-Generierung:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dolunay38/BookVoice-AI/blob/main/BookVoice_AI_Colab.ipynb)

**Performance:**
| | CPU (i3-9th) | Edge TTS | GPU Colab T4 |
|--|--|--|--|
| 1 Kapitel | ~16 Min | 9 Sek | ~2 Min |
| 6 Kapitel | ~108 Min | 72 Sek | ~9 Min |

---

## 🔌 API Endpoints

```
GET  /health                     → Server Status
POST /tts/generate               → Text zu Audio
POST /tts/book                   → Hörbuch generieren
GET  /tts/book/status/{job_id}   → Job Status
POST /tts/cancel/{job_id}        → Job abbrechen
POST /transcribe/async           → Transkription starten
GET  /transcribe/status/{job_id} → Transkriptions-Status
GET  /transcribe/files           → Transkriptionen auflisten
POST /transcribe/folder          → Ordner erstellen
GET  /edge/voices                → Edge TTS Stimmen
POST /admin/colab-url            → GPU URL setzen
GET  /admin/logs                 → Server Logs
```

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.11
- **TTS:** Coqui XTTS-v2, Microsoft Edge TTS
- **Transkription:** faster-whisper
- **OCR:** Tesseract (TR/DE/EN/AR)
- **Dokumente:** LibreOffice, Calibre, PyPDF2
- **Frontend:** Vanilla JS, Single HTML File
- **Container:** Docker, Nginx
- **Tunnel:** Cloudflare Zero Trust

---

## 📋 Roadmap

### v1.3 (Aktuell)
- [x] FastWhisper Transkriptions-Tab
- [x] Background Job System (kein Timeout)
- [x] Ordner-Verwaltung für Transkriptionen
- [x] Admin Log-Fenster
- [x] 2-spaltig SRT + Text Ansicht
- [ ] CosyVoice Integration (wenn Türkisch stabil)
- [ ] Speaker Diarization (pyannote.audio)

### v2.0
- [ ] Auto-Workflow (Buch → Kapitel → Tagging → Hörbuch)
- [ ] User Login (Keycloak)
- [ ] RunPod.io Integration
- [ ] RAG Chat
- [ ] Qwen-7B Emotion Tags

### v3.0
- [ ] Mobile App
- [ ] Stripe/PayPal
- [ ] CosyVoice Türkisch

---

## 👤 Autor

**Ismail Aksoy (Dolunay)**
- GitHub: [@dolunay38](https://github.com/dolunay38)
- LinkedIn: [ismail-aksoy](https://www.linkedin.com/in/ismail-aksoy-4a3a58369/)
- Homelab: Aksoy-Net (Dell OptiPlex 7060, i3-9th Gen, 32GB RAM)
- Projekt: FISI Umschulung @ Diakonie Michaelshoven / anqa-it security

---

## 📄 Lizenz

MIT License — Open Source, kostenlos nutzbar.
