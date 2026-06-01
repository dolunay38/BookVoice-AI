# BookVoice-AI 🎙️📖

**Open-Source KI Hörbuch-Studio** — Texte, eBooks und Fotos in hochwertige Hörbücher verwandeln.

![Version](https://img.shields.io/badge/Version-1.2-green) ![Docker](https://img.shields.io/badge/Docker-Required-blue) ![GPU](https://img.shields.io/badge/GPU-Colab%20T4-orange)

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
| 📚 eBook Support | EPUB, MOBI, PDF, AZW3 |
| 📸 OCR | Foto von Buchseite → automatisch Text |
| 🖼️ Cover-Bibliothek | Buchcover verwalten & in MP3/M4B einbetten |
| 🎵 Hintergrundmusik | Musik hochladen und mischen |
| ▶️ Audio-Player | Direkt im Browser abspielen |
| 🌍 Multi-Sprache | Türkisch, Deutsch, Englisch, Arabisch |
| 🎛️ Stil-Presets | Sufi, Roman, Sachtext, Dramatisch... |
| 📱 M4B Format | iPhone Hörbuch-Format mit Kapitel-Navigation |
| 🐳 Docker | One-Click Install · CPU & GPU Auto-Detection |

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

---

## 📓 GPU Colab Schnellstart

1. [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dolunay38/BookVoice-AI/blob/main/BookVoice_AI_Colab.ipynb)
2. Runtime → T4 GPU aktivieren
3. Strg+F9 → Alle ausführen
4. Link in BookVoice-AI GUI eingeben
5. ☁️ GPU Colab → Verbinden

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

1. **Engine** wählen (XTTS-v2 / Edge TTS / GPU Colab)
2. **Text** eingeben oder EPUB/PDF hochladen
3. **Stimme** auswählen (11 Standard + eigene)
4. **Preset** wählen (Sufi, Roman, Sachtext...)
5. **Test-Audio** anhören
6. **HÖRBUCH GENERIEREN**
7. **Bibliothek** → direkt abspielen oder herunterladen

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
├── ki_archiv_tts_web.html   # Web-GUI
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

## 🤝 Verwandte Projekte

- [KI-ARCHIV-PRO](https://github.com/dolunay38/KI-ARCHIV-PRO) — KI Transkription & Archiv Studio

---

## 📄 Lizenz

MIT License — kostenlos für private und kommerzielle Nutzung.

**Powered by:** XTTS-v2 · Edge TTS · FastAPI · Docker · Cloudflare · Google Colab

---

*BookVoice-AI v1.2 — Entwickelt von Ismail Aksoy · Aksoy-Net Homelab · 2026*
