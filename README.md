# 📚 BookVoice-AI

**Open-Source KI-Hörbuch Studio** — Text zu Sprache mit Voice Cloning, Transkription und Hörbuch-Produktion.

[![GitHub](https://img.shields.io/badge/GitHub-dolunay38-black)](https://github.com/dolunay38/BookVoice-AI)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com)
[![Version](https://img.shields.io/badge/Version-1.3-orange)](https://github.com/dolunay38/BookVoice-AI)

---

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Systemvoraussetzungen](#2-systemvoraussetzungen)
3. [Installation Windows](#3-installation-windows)
4. [Installation Server (Linux)](#4-installation-server-linux)
5. [Konfiguration](#5-konfiguration)
6. [Deployment & Updates](#6-deployment--updates)
7. [Cloudflare Tunnel & Zugang](#7-cloudflare-tunnel--zugang)
8. [Web-GUI Bedienung](#8-web-gui-bedienung)
9. [Transkription](#9-transkription)
10. [API-Referenz](#10-api-referenz)
11. [Stimmen verwalten](#11-stimmen-verwalten)
12. [Formate & Ausgabe](#12-formate--ausgabe)
13. [Troubleshooting](#13-troubleshooting)
14. [Roadmap](#14-roadmap)

---

## 1. Projektübersicht

**BookVoice-AI** ist ein selbst-gehostetes KI-Hörbuch-Studio. Es konvertiert Text, eBooks (EPUB, PDF, MOBI) und Fotos von Buchseiten automatisch in hochwertige Hörbücher — mit geklonter Stimme, in Türkisch, Deutsch und Englisch.

### Architektur

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

### TTS Engines

| Engine | Qualität | Speed | Voice Cloning | Sprachen |
|--------|----------|-------|---------------|---------|
| XTTS-v2 (CPU) | ⭐⭐⭐⭐⭐ | Langsam | ✅ | TR/DE/EN + |
| Edge TTS | ⭐⭐⭐ | Sehr schnell | ❌ | 400+ Stimmen |
| GPU Colab T4 | ⭐⭐⭐⭐⭐ | Schnell | ✅ | TR/DE/EN + |

### Unterstützte Dateiformate

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

### Unterstützte Sprachen

- 🇹🇷 Türkisch (tr)
- 🇩🇪 Deutsch (de)
- 🇬🇧 Englisch (en)
- 🇸🇦 Arabisch (ar)

---

## 2. Systemvoraussetzungen

### Minimum

| Komponente | Minimum |
|---|---|
| RAM | 8 GB |
| CPU | 4 Kerne (Intel i3 9. Gen oder besser) |
| Speicher | 20 GB frei |
| OS | Ubuntu 22.04+ / Windows 10/11 mit WSL2 |
| Docker | 24.x oder neuer |

### Empfohlen

| Komponente | Empfohlen |
|---|---|
| RAM | 16–32 GB |
| GPU | NVIDIA GTX 1650+ (optional, 10x schneller) |
| Speicher | 100 GB+ (für Hörbücher und Modelle) |

---

## 3. Installation Windows

### Ein-Klick Installation

1. Repository herunterladen: [GitHub](https://github.com/dolunay38/BookVoice-AI)
2. `install.bat` als Administrator ausführen
3. Browser öffnet sich automatisch auf `http://localhost:7502`

### Voraussetzungen (automatisch geprüft)
- Docker Desktop
- WSL2

### Update

```bat
update.bat
```

Lädt automatisch neue Dateien von GitHub und baut Container neu.

### Starten / Stoppen

```bat
start.bat    # BookVoice-AI starten
stop.bat     # BookVoice-AI stoppen
```

---

## 4. Installation Server (Linux)

### Schritt 1: Repository klonen

```bash
git clone https://github.com/dolunay38/BookVoice-AI.git
cd BookVoice-AI
```

### Schritt 2: Verzeichnisse anlegen

```bash
sudo mkdir -p /mnt/data/docker-data/ki-archiv/{EINGABE,ARCHIV,ERGEBNISSE,HOERBUCH,TRANSKRIPTIONEN,tts_models,models,webui_storage}
sudo chown -R $USER:$USER /mnt/data/docker-data/ki-archiv
```

### Schritt 3: Dateien kopieren

```bash
cp compose.server.yaml /mnt/data/docker-data/ki-archiv/
cp Dockerfile.tts /mnt/data/docker-data/ki-archiv/
cp tts_server.py /mnt/data/docker-data/ki-archiv/
cp ki_archiv_tts_web.html /mnt/data/docker-data/ki-archiv/
cp nginx-bookvoice.conf /mnt/data/docker-data/ki-archiv/
```

### Schritt 4: Container bauen und starten

```bash
cd /mnt/data/docker-data/ki-archiv
docker compose -f compose.server.yaml up -d --build
```

> **Hinweis:** Beim ersten Start wird XTTS-v2 Modell heruntergeladen (~1.8 GB). Dauert 5–15 Min.

### Schritt 5: Installation prüfen

```bash
curl http://localhost:7502/api/health
# Erwartete Antwort: {"status":"ok","device":"cpu"}
```

---

## 5. Konfiguration

### compose.server.yaml — Wichtige Einstellungen

```yaml
services:
  ki-archiv-tts:
    environment:
      - TTS_OUTPUT=/app/HOERBUCH
      - TTS_LANG=tr
```

### Ordnerstruktur (Server)

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

### Stimme-Parameter

| Parameter | Wert | Beschreibung |
|---|---|---|
| temperature | 0.1–1.0 | Wärme/Emotion |
| repetition_penalty | 2–15 | Natürlichkeit |
| top_k | 10–100 | Kreativität |

### Presets

| Preset | Temperature | Rep. Penalty | Top-K | Speed |
|--------|-------------|--------------|-------|-------|
| 🎯 Original | 0.1 | 10.0 | 10 | 1.0 |
| 🕌 Sufi | 0.65 | 4.0 | 25 | 0.85 |
| 📖 Roman | 0.55 | 5.0 | 30 | 1.0 |
| 📰 Sachtext | 0.4 | 6.0 | 20 | 1.05 |
| 🎭 Dramatisch | 0.85 | 3.0 | 50 | 0.95 |

---

## 6. Deployment & Updates

### Nach Code-Änderungen (nur .py oder .html)

```bash
scp tts_server.py aksadmin@SERVER_IP:/pfad/ki-archiv/
docker restart ki-archiv-tts
```

### Nach Dockerfile-Änderungen (Rebuild nötig!)

```bash
scp Dockerfile.tts aksadmin@SERVER_IP:/pfad/ki-archiv/
cd /mnt/data/docker-data/ki-archiv
docker compose -f compose.server.yaml build --no-cache ki-archiv-tts
docker compose -f compose.server.yaml up -d ki-archiv-tts
```

> ⚠️ **Wichtig:** Immer `--no-cache` beim Rebuild verwenden, sonst werden neue Dateien ignoriert!

### Logs anzeigen

```bash
docker logs ki-archiv-tts -f
docker logs ki-archiv-proxy -f
```

---

## 7. Cloudflare Tunnel & Zugang

### Tunnel einrichten

1. Cloudflare Dashboard → **Zero Trust** → **Tunnels**
2. Tunnel auswählen → **Public Hostname** → **Add**
3. Eintrag:
   - Subdomain: `hoerbuch`
   - Domain: `deine-domain.de`
   - Type: `HTTP`
   - URL: `SERVER-IP:7502`

### Zugangs-Policy (E-Mail-Authentifizierung)

1. **Zero Trust** → **Access** → **Applications** → **Add**
2. **Self-hosted** auswählen
3. Policy: Allow → Emails → Erlaubte Adressen eintragen

> User erhalten Magic-Link per E-Mail — kein Passwort nötig.

---

## 8. Web-GUI Bedienung

### Zugang

- **Intern:** `http://SERVER-IP:7502`
- **Extern:** `https://hoerbuch.deine-domain.de`

### Hörbuch erstellen

1. **Engine** wählen (XTTS-v2 / Edge TTS / GPU Colab)
2. **Sprache** auswählen (TR/DE/EN)
3. **Text eingeben** oder **Datei hochladen**
4. **Referenzstimme** auswählen
5. **Preset** wählen oder manuell einstellen
6. **Projekt-Name** eingeben
7. **HÖRBUCH GENERIEREN** klicken
8. Fortschritt im **Log** verfolgen
9. Fertige Datei in **Dateien** herunterladen

### Emotion Tags

```
[dramatic] [whispers] [sighs] [laughs] [sad] [happy] [pause]
```

Auto-Erkennung aktivierbar per Checkbox.

### GPU Colab verbinden

1. Colab Notebook öffnen: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dolunay38/BookVoice-AI/blob/main/BookVoice_AI_Colab.ipynb)
2. Alle Zellen ausführen
3. Tunnel-URL kopieren
4. In GUI → GPU Colab → URL eingeben → Verbinden

### Performance

| | CPU (i3-9th) | Edge TTS | GPU Colab T4 |
|--|--|--|--|
| 1 Kapitel (~1.700 Z.) | ~16 Min | 9 Sek | ~2 Min |
| 6 Kapitel (~11.000 Z.) | ~108 Min | 72 Sek | ~9 Min |

---

## 9. Transkription

### FastWhisper Modelle

| Modell | Qualität | Speed | Empfohlen für |
|--------|----------|-------|---------------|
| Small | ⭐⭐⭐ | Schnell | CPU, kurze Dateien |
| Medium | ⭐⭐⭐⭐ | Mittel | Standard |
| Large-v3 | ⭐⭐⭐⭐⭐ | Langsam | Beste Qualität |

### Unterstützte Formate

MP3, WAV, M4A, OGG, MP4, MKV, WebM

### Workflow

1. **Transkription Tab** öffnen
2. **Modus** wählen (Audio/Video oder Bild/OCR)
3. **Projektname** eingeben
4. **Zielordner** wählen (optional)
5. **Datei hochladen**
6. **Sprache** und **Modell** wählen
7. **TRANSKRIBIEREN** klicken
8. Ergebnis: Links SRT mit Zeitstempel, Rechts Text
9. **→ Hörbuch** Button überträgt Text direkt ins Studio

### Export

- **TXT** — Reiner Text
- **SRT** — Mit Zeitstempel (für Untertitel)

---

## 10. API-Referenz

### Base URL

```
http://SERVER-IP:7500
# oder über Proxy:
http://SERVER-IP:7502/api
```

### Endpoints

```
GET  /health                      → Server Status
POST /tts/generate                → Text zu Audio
POST /tts/book                    → Hörbuch generieren
GET  /tts/book/status/{job_id}    → Job Status
POST /tts/cancel/{job_id}         → Job abbrechen
GET  /tts/files                   → Dateien auflisten
GET  /tts/download/{filename}     → Datei herunterladen
DELETE /tts/files/{filename}      → Datei löschen
POST /tts/upload-voice            → Stimme hochladen
GET  /tts/voices                  → Stimmen auflisten
DELETE /tts/voices/{filename}     → Stimme löschen
GET  /edge/voices                 → Edge TTS Stimmen
POST /edge/book                   → Edge TTS Hörbuch
POST /transcribe/async            → Transkription starten
GET  /transcribe/status/{job_id}  → Transkriptions-Status
GET  /transcribe/files            → Transkriptionen auflisten
POST /transcribe/folder           → Ordner erstellen
DELETE /transcribe/folder/{name}  → Ordner löschen
POST /admin/colab-url             → GPU URL setzen
GET  /admin/logs                  → Server Logs
```

---

## 11. Stimmen verwalten

### Empfehlungen

- Länge: **8–60 Sekunden** (min. 8s für Voice Cloning)
- Format: WAV oder MP3
- Umgebung: Ruhiger Raum, kein Hintergrundgeräusch
- Inhalt: In der Zielsprache sprechen

### Stimme aus YouTube extrahieren

```bash
yt-dlp -x --audio-format mp3 "https://youtube.com/watch?v=..."
ffmpeg -i video.mp3 -ss 00:02:00 -t 00:01:00 -acodec pcm_s16le -ar 22050 -ac 1 stimme.wav
```

### Parameter für verschiedene Textstile

| Textstil | Temperature | Rep. Penalty | Top-K |
|---|---|---|---|
| Sachtext | 0.35 | 7.0 | 15 |
| Roman | 0.55 | 5.0 | 30 |
| Sufi/Spirituell | 0.65 | 4.0 | 25 |
| Lyrik/Poesie | 0.85 | 2.5 | 55 |

---

## 12. Formate & Ausgabe

### MP3
- Standard für alle Geräte
- Kleinste Dateigröße
- Ideal für WhatsApp, E-Mail

### M4B
- Offizielles Hörbuch-Format (Apple/iPhone)
- Kapitel-Navigation + Lesezeichen
- Metadaten + Cover eingebettet

### WAV
- Verlustfreie Qualität
- Für Nachbearbeitung geeignet

### Ausgabestruktur

```
HOERBUCH/
└── mein_buch/
    ├── kapitel_001.mp3
    ├── kapitel_002.mp3
    └── mein_buch_komplett.mp3  ← Finale Datei
```

---

## 13. Troubleshooting

### Container startet nicht

```bash
docker logs ki-archiv-tts --tail 30
docker restart ki-archiv-tts
```

### OFFLINE in Web-GUI

```bash
curl http://localhost:7502/api/health
docker logs ki-archiv-proxy --tail 10
```

### Stimme klingt verzerrt

- Referenzstimme zu kurz → längere Aufnahme (min. 8s)
- Temperature zu hoch → auf 0.3–0.5 reduzieren
- Hintergrundgeräusche → sauberere Aufnahme

### Cloudflare 524 Timeout

Passiert bei langen Transkriptionen (Medium/Large). Ab v1.3 automatisch durch Background Job System gelöst — kein Timeout mehr.

### Rebuild ignoriert neue Dateien

```bash
# Immer --no-cache verwenden!
docker compose -f compose.server.yaml build --no-cache ki-archiv-tts
```

### Speicher voll

```bash
rm -rf /mnt/data/docker-data/ki-archiv/HOERBUCH/*
df -h /mnt/data
```

---

## 14. Roadmap

### v1.3 (Aktuell) ✅
- [x] FastWhisper Transkriptions-Tab
- [x] Background Job System (kein Cloudflare Timeout)
- [x] Ordner-Verwaltung für Transkriptionen
- [x] Admin Log-Fenster (live, Auto-Refresh)
- [x] 2-spaltig SRT + Text Ansicht
- [x] Modell-Wahl (Small/Medium/Large-v3)
- [x] install.bat / update.bat / start.bat / stop.bat

### v2.0
- [ ] Auto-Workflow (Buch → Kapitel → Tagging → Hörbuch)
- [x] Live-Transkription (Satz für Satz)
- [ ] Speaker Diarization (pyannote.audio)
- [ ] User Login (Keycloak)
- [ ] RunPod.io Integration
- [ ] RAG Chat direkt in GUI
- [ ] Qwen-7B Emotion Tags

### v3.0
- [ ] CosyVoice (wenn Türkisch stabil)
- [ ] Mobile App
- [ ] Stripe/PayPal
- [ ] NLLB Übersetzung

---

## 👤 Autor

**Ismail Aksoy (Dolunay)**
- GitHub: [@dolunay38](https://github.com/dolunay38)
- LinkedIn: [ismail-aksoy](https://www.linkedin.com/in/ismail-aksoy-4a3a58369/)
- Homelab: Aksoy-Net (Dell OptiPlex 7060, i3-9th Gen, 32GB RAM)

---

## 📄 Lizenz

MIT License — Open Source, kostenlos nutzbar.

---

*BookVoice-AI — Open Source AI Audiobook Studio*  
*Powered by XTTS-v2, FastWhisper, FastAPI, Docker & Cloudflare*
