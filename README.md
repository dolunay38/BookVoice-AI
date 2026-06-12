# 🎙️ BookVoice-AI

<div align="center">

![BookVoice-AI](https://img.shields.io/badge/BookVoice--AI-v2.3-22c55e?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Offline](https://img.shields.io/badge/100%25-Lokal-27AE60?style=for-the-badge&logo=shield&logoColor=white)
![Status](https://img.shields.io/badge/Status-Aktiv-brightgreen?style=for-the-badge)

**Selbst-gehostetes KI-Studio für Hörbücher & Transkription.**  
Texte, eBooks, PDFs & Fotos → Hörbücher (XTTS-v2 Voice Cloning).  
Audio/Video → Text (FastWhisper, live). Eigene Stimmen trainieren (KI-Trainingsraum).  
Alles lokal — kein Abo, keine Cloud.

[🚀 Schnellstart](#-schnellstart) · [✨ Features](#-features) · [🧱 Architektur](#-architektur) · [⚙️ Konfiguration](#-konfiguration)

</div>

---

## ✨ Features

| Funktion | Technologie | Beschreibung |
|---|---|---|
| 🎙️ Hörbuch-Erstellung | XTTS-v2 Voice Cloning | Text, EPUB, PDF, Foto → MP3/M4B/WAV, eigene Stimme, Stil-Presets |
| 🎤 FastWhisper Transkription | faster-whisper | Live SSE-Stream, TR/DE/EN/AR, Stapel-Transkription, SRT-Export |
| 🎓 KI-Trainingsraum | XTTS-v2 Fine-tuning | Audio → Clips → Review → Dataset → Colab T4 Training (4 Stufen) |
| 🖼️ OCR & Dokumente | Tesseract + pdf2image | JPG/PNG/PDF/DOCX/EPUB/MOBI → Text |
| ⚡ Edge TTS | Microsoft Edge TTS | Online-Fallback, viele Stimmen, kein GPU nötig |
| ☁️ GPU Engine | Google Colab T4 | Transkription + TTS auf GPU via Cloudflare Tunnel |
| 📚 Mediathek | Registry-Modell | Hörbücher/Transkripte/Stimmen/Downloads/Archiv verwalten |
| 🌍 Mehrsprachig | TR / DE / EN / AR | UI in 3 Sprachen, Stimmen nach Sprache gruppiert |
| 🎭 Stimmen-Bibliothek | Voice Cloning | 11 eingebaute Stimmen + eigene hochladbar + trainierbar |

---

## 🧱 Architektur

```
┌─────────────────────────────────────────────────────────┐
│              Browser (http://localhost:7502)             │
│              ki_archiv_tts_web.html (~5000 Z.)           │
└──────────────────────────┬──────────────────────────────┘
                           │ nginx-proxy (Port 7502)
┌──────────────────────────▼──────────────────────────────┐
│              Docker Compose                              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  bookvoice-tts  (Port 7500)                      │   │
│  │  FastAPI tts_server.py (~2900 Zeilen)            │   │
│  │  XTTS-v2 · FastWhisper · Edge TTS · Trainingsraum│   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Volumes: tts_models · HOERBUCH · TRANSKRIPTIONEN        │
│           ARCHIV · TRAINING · musik                      │
└─────────────────────────────────────────────────────────┘
         │ optional: Colab GPU Engine
         └─► getComputeUrl() → Cloudflare Tunnel → T4
```

---

## 🚀 Schnellstart

### Voraussetzungen
- Windows 10/11 64-bit
- [Docker Desktop](https://www.docker.com/products/docker-desktop) installiert + läuft
- 16 GB RAM (empfohlen 32 GB)
- 20 GB freier Speicher

### Installation (One-Click)

```
1. Diesen Ordner herunterladen (oder git clone)
2. install.bat doppelklicken
3. Warten (~5-15 Min beim ersten Start — lädt ~9 GB KI-Modelle)
4. Browser öffnet automatisch: http://localhost:7502
```

`install.bat` erkennt automatisch ob du eine NVIDIA-GPU hast und wählt den richtigen Modus.

### Danach

| Aktion | Datei |
|---|---|
| BookVoice-AI starten | `start.bat` |
| Update installieren | `update.bat` |
| Fehler diagnostizieren | `debug.bat` |
| Deinstallieren | `uninstall.bat` |

---

## 📁 Dateien-Übersicht

| Datei | Zweck |
|---|---|
| `compose.yaml` | 🖥️ Lokal · CPU-User |
| `compose.gpu.yaml` | ⚡ Lokal · GPU-User (NVIDIA) |
| `compose.server.yaml` | 🖧 Server-Deployment (eigener Server) |
| `Dockerfile.tts` | CPU-Image |
| `Dockerfile.tts.gpu` | GPU-Image (CUDA + pyannote) |
| `tts_server.py` | FastAPI Backend (~2900 Zeilen) |
| `ki_archiv_tts_web.html` | Single-File Frontend (~5000 Zeilen) |
| `nginx-bookvoice.conf` | Proxy-Konfiguration |
| `version.txt` | Aktuelle Version (für update.bat) |
| `install.bat` | 🖥️ Erstinstallation (Windows) |
| `start.bat` | 🖥️ Starten (Windows) |
| `update.bat` | 🖥️ Update mit Versions-Check (Windows) |
| `debug.bat` | 🖥️ Fehlerdiagnose (Windows) |
| `uninstall.bat` | 🖥️ Deinstallation (Windows) |
| `install.sh` | 🐧 Installation (Linux/Mac) |

---

## ⚙️ Konfiguration

### GPU aktivieren (optional, 10x schneller)

NVIDIA-GPU vorhanden? `install.bat` erkennt sie automatisch und nutzt `compose.gpu.yaml`.

Für Sprecher-Diarization (Wer hat was gesagt?) zusätzlich:
```
HF_TOKEN=dein_huggingface_token
```
in `.env` oder als Umgebungsvariable setzen.

### Colab GPU Engine (TTS + Transkription auf T4)

1. `BookVoice_AI_Colab.ipynb` in Google Colab öffnen
2. T4-GPU Runtime wählen
3. Notebook ausführen → Tunnel-URL kopieren
4. In BookVoice-AI unter Einstellungen → Colab URL einfügen

---

## 📊 Projektstatus

| Metrik | Wert |
|---|---|
| Version | **v2.3** (Juni 2026) |
| Backend | FastAPI `tts_server.py` (~2900 Zeilen, Port 7500) |
| Frontend | Single-File HTML (~5000 Zeilen) |
| Eingebaute Stimmen | **11** (TR/DE/EN) + eigene hochladbar + trainierbar |
| Unterstützte Formate | Audio: `.mp3 .wav .m4a .ogg .mp4` · Docs: `.pdf .epub .mobi .docx .pptx .jpg .png` |
| Plattform | Windows 10/11 (Docker) · Linux/Mac (install.sh) |

---

## 🗺️ Roadmap

- [x] XTTS-v2 Voice Cloning + Stil-Presets
- [x] FastWhisper Live-Transkription (SSE-Stream)
- [x] KI-Trainingsraum Stufe 1–4 (Dataset-Werkstatt + Modell-Registrierung)
- [x] Mediathek mit Ordner-Gruppierung, Suche, Löschen
- [x] Stapel-Transkription
- [x] Stimmen-Panel: Gruppierung TR/DE/EN + Meta-Editor
- [x] Speaker Diarization (Colab GPU, pyannote)
- [ ] `dev → main` Merge (nach vollständigem Test)
- [ ] Dynamische UI-Übersetzung (NLLB, #17)
- [ ] RunPod Pay-per-Use
- [ ] RAG-Chat (lokales LLM)
- [ ] Mobile/PWA

---

## 👤 Entwickler

**Ismail Aksoy (Dolunay)**

Angehender Fachinformatiker für Systemintegration (FISI) mit Fokus IT-Security & Infrastruktur.

BookVoice-AI ist ein Eigenprojekt — selbst-gehostetes KI-Audiobook-Studio, entwickelt parallel zur FISI-Umschulung und zum [Aksoy-Net Home Lab](https://github.com/dolunay38/aksoy-net-homelab).

- 🔗 GitHub: [github.com/dolunay38](https://github.com/dolunay38)
- 💼 LinkedIn: [Ismail Aksoy](https://linkedin.com/in/ismail-aksoy)
- 🌐 Homelab: [aksoy-net.de](https://aksoy-net.de)

---

<div align="center">

*BookVoice-AI — Hörbücher. Lokal. Mit deiner Stimme.*

</div>
