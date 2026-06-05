# BookVoice-AI 🎙️📖

**Open-Source KI Hörbuch-Studio** — Texte, eBooks, PDFs und Dokumente in hochwertige Hörbücher verwandeln.

![Version](https://img.shields.io/badge/Version-1.2-green) ![Docker](https://img.shields.io/badge/Docker-Required-blue) ![GPU](https://img.shields.io/badge/GPU-Colab%20T4-orange) ![Language](https://img.shields.io/badge/UI-TR%20%7C%20DE%20%7C%20EN-purple)

> 💡 Selbst konzipiert und entwickelt — auf Basis von Open Source Technologien, als Teil meiner FISI Umschulung und aus Leidenschaft für KI.

---

## 🎥 Demo

> 📹 Video folgt

---

## ⚡ One-Click Installation

### Windows
```cmd
install.bat
```
Doppelklick — fertig!

### Linux / Mac
```bash
chmod +x install.sh && ./install.sh
```

**Voraussetzung:** [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## 🚀 Update
```cmd
update.bat
```
Lädt automatisch die neueste Version von GitHub!

---

## ✨ Features v1.2

| Feature | Beschreibung |
|---|---|
| 🧠 XTTS-v2 | Voice Cloning — eigene Stimme hochladen |
| ⚡ Edge TTS | 400+ Stimmen · Online · Sehr schnell |
| ☁️ GPU Colab | Google T4 GPU kostenlos · 10x schneller |
| 📚 Alle Formate | PDF, DOCX, DOC, EPUB, MOBI, PPTX, XLSX, HTML, OCR (JPG/PNG) |
| 🖼️ Cover-Bibliothek | Buchcover verwalten & in MP3/M4B einbetten |
| 🎵 Hintergrundmusik | Musik hochladen und mischen |
| ▶️ Audio-Player | Direkt im Browser abspielen |
| 🌍 Multi-Sprache | Türkisch, Deutsch, Englisch |
| 🌐 Multi-Language UI | Oberfläche auf TR / DE / EN umschalten |
| 🎛️ Stil-Presets | Sufi, Roman, Sachtext, Dramatisch, Kinder... |
| 📱 M4B Format | iPhone Hörbuch-Format mit Kapitel-Navigation |
| 👑 Admin Panel | Community GPU aktivieren, API Key, Passwort |
| ☁️ Community GPU | Admin stellt GPU für alle User bereit |
| 💾 Auto-Speicher | GPU generierte MP3 automatisch auf Server |
| 🐳 Docker | One-Click Install · CPU & GPU Auto-Detection |
| 🔒 Cloudflare | Sicher hinter Cloudflare Zero Trust |

---

## 🎙️ 3 Engines zur Auswahl

### 🧠 XTTS-v2 (Lokal/Offline)
- Eigene Stimme klonen
- Läuft komplett lokal
- Kein Internet nötig
- 11 Standard-Stimmen inklusive

### ⚡ Edge TTS (Online)
- 400+ Microsoft Neural Stimmen
- Sehr schnell (~2-3 Sek/Kapitel)
- Internet erforderlich
- Kostenlos

### ☁️ GPU Colab (Google T4)
- NVIDIA T4 GPU kostenlos
- 10x schneller als CPU
- Google Account benötigt
- ~3-4 Stunden pro Session
- Community GPU: Admin stellt GPU für alle User bereit
- MP3 automatisch auf Server gespeichert ✅

---

## 📄 Unterstützte Dateiformate

| Kategorie | Formate |
|---|---|
| Dokumente | TXT, MD, CSV, RTF |
| Word | DOC (LibreOffice), DOCX, ODT |
| PDF | PDF (PyPDF2 + Calibre Fallback) |
| Präsentationen | PPTX, PPT |
| Tabellen | XLSX, XLS |
| E-Books | EPUB, MOBI, AZW3, FB2 |
| Web | HTML, XML |
| Bilder (OCR) | JPG, PNG, WEBP, TIFF, BMP |
| Audio (Stimme) | WAV, MP3, M4A, OGG, WEBA, OPUS |

---

## ⚡ Performance Vergleich

| | CPU (Dell i3-9th/32GB) | Edge TTS | GPU Colab T4 |
|---|---|---|---|
| 1.679 Zeichen (1 Kap.) | ~16 Min | 9 Sek | ~2 Min |
| 11.325 Zeichen (6 Kap.) | ~108 Min | 72 Sek | ~9 Min |
| Qualität | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Voice Cloning | ✅ | ❌ | ✅ |
| Kosten | $0 | $0 | ~$0.05/Kap |

---

## 📓 GPU Colab Schnellstart

1. [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dolunay38/BookVoice-AI/blob/main/BookVoice_AI_Colab.ipynb)
2. Runtime → T4 GPU aktivieren
3. Strg+F9 → Alle ausführen (~10 Min beim ersten Mal)
4. URL kopieren → BookVoice-AI GUI → GPU Colab → Verbinden
5. ✅ Verbunden! GPU: CUDA — MP3 wird automatisch auf Server gespeichert

---

## 🖥️ Server Deployment

```bash
git clone https://github.com/dolunay38/BookVoice-AI.git
cd BookVoice-AI
docker compose -f compose.server.yaml up -d
```

📖 [Server Anleitung](SERVER_DEPLOYMENT.md)

---

## 🚀 Verwendung

1. **Sprache** wählen (🇩🇪 DE / 🇹🇷 TR / 🇬🇧 EN) — oben rechts
2. **Engine** wählen (XTTS-v2 / Edge TTS / GPU Colab)
3. **Text** eingeben oder Datei hochladen (PDF, DOCX, EPUB...)
4. **Stimme** auswählen (11 Standard + eigene)
5. **Preset** wählen (Sufi, Roman, Sachtext...)
6. **Test-Audio** anhören
7. **HÖRBUCH GENERIEREN**
8. **Bibliothek** → direkt abspielen oder herunterladen

---

## 📁 Projektstruktur

```
BookVoice-AI/
├── install.bat              # Windows One-Click
├── install.sh               # Linux/Mac
├── update.bat               # Auto-Update
├── uninstall.bat            # Deinstallation
├── debug.bat                # Diagnose
├── BookVoice_AI_Colab.ipynb # Google Colab GPU
├── compose.yaml             # Lokal Docker
├── compose.server.yaml      # Server Docker
├── Dockerfile.tts           # Container Build
├── tts_server.py            # FastAPI Backend
├── ki_archiv_tts_web.html   # Web-GUI (TR/DE/EN)
└── nginx-bookvoice.conf     # Reverse Proxy
```

---

## 🔧 Systemvoraussetzungen

| | Minimum | Empfohlen |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Speicher | 10 GB | 50 GB |
| CPU | 4 Kerne | 8+ Kerne |
| GPU | Nicht nötig | NVIDIA (10x schneller) |

---

## 🛠️ Tech Stack

- **Backend:** FastAPI · Python · Coqui TTS (XTTS-v2) · Edge TTS
- **Frontend:** Vanilla JS · HTML · CSS · i18n (TR/DE/EN)
- **Infrastruktur:** Docker · Nginx · Cloudflare Zero Trust
- **GPU:** Google Colab T4 · Cloudflare Tunnel
- **Dokumente:** LibreOffice · Calibre · PyPDF2 · python-docx · Tesseract OCR

---

## 🚀 Roadmap

- [ ] User-Verwaltung & Login System (Keycloak)
- [ ] RunPod.io GPU Integration (Pay-per-Use)
- [ ] CosyVoice 2 Engine (bessere Qualität)
- [ ] Queue System für mehrere User
- [ ] Google Drive Integration
- [ ] Mobile App

---

## 🤝 Verwandte Projekte

- [KI-ARCHIV-PRO](https://github.com/dolunay38/KI-ARCHIV-PRO) — KI Transkription & Archiv Studio

---

## 👤 Kontakt

- 💼 [LinkedIn — Ismail Aksoy](https://www.linkedin.com/in/ismail-aksoy-4a3a58369/)
- 🐙 [GitHub — @dolunay38](https://github.com/dolunay38)

---

## 📄 Lizenz

MIT License — kostenlos für private nutzung.

**Powered by:** XTTS-v2 · Edge TTS · FastAPI · Docker · Cloudflare · Google Colab · LibreOffice · Tesseract

---

*BookVoice-AI v1.2 — Entwickelt von Ismail Aksoy · Aksoy-Net Homelab · 2026*
