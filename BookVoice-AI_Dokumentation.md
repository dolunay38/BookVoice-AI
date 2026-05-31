# BookVoice-AI — Vollständige Dokumentation
**Version 1.0 | Stand: Mai 2026 | Ismail Aksoy**

---

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Systemvoraussetzungen](#2-systemvoraussetzungen)
3. [Projektstruktur](#3-projektstruktur)
4. [Installation — Schritt für Schritt](#4-installation--schritt-für-schritt)
5. [Konfiguration](#5-konfiguration)
6. [Deployment auf Server](#6-deployment-auf-server)
7. [Cloudflare Tunnel & Zugang](#7-cloudflare-tunnel--zugang)
8. [Web-GUI Bedienung](#8-web-gui-bedienung)
9. [API-Referenz](#9-api-referenz)
10. [Stimmen verwalten](#10-stimmen-verwalten)
11. [Formate & Ausgabe](#11-formate--ausgabe)
12. [Troubleshooting](#12-troubleshooting)
13. [GitHub Veröffentlichung](#13-github-veröffentlichung)

---

## 1. Projektübersicht

**BookVoice-AI** ist ein selbst-gehostetes KI-Hörbuch-Studio. Es konvertiert Text, eBooks (EPUB, PDF, MOBI) und Fotos von Buchseiten automatisch in hochwertige Hörbücher — mit geklonter Stimme, in Türkisch, Deutsch und Englisch.

### Features

| Feature | Beschreibung |
|---|---|
| XTTS-v2 TTS | Hochwertige KI-Sprachsynthese mit Stimm-Klonung |
| EPUB/MOBI Support | Calibre konvertiert alle eBook-Formate |
| OCR | Fotos von Buchseiten werden per Tesseract erkannt |
| Web-GUI | Matrix-Style Browser-Oberfläche |
| Multi-Format | MP3, WAV, M4B Ausgabe |
| Stimme-Upload | Eigene Stimme direkt im Browser hochladen |
| SML Tags | `[pause]` `[break]` `[pause:3]` für natürliches Vorlesen |
| CPU/GPU | Automatische Erkennung — läuft auch ohne GPU |
| Docker | Ein Befehl zum Starten |
| Cloudflare | Sicherer externer Zugang per E-Mail-Policy |

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
| OS | Ubuntu 22.04 / 24.04 LTS |
| Docker | 24.x oder neuer |

### Empfohlen

| Komponente | Empfohlen |
|---|---|
| RAM | 16–32 GB |
| GPU | NVIDIA GTX 1650+ (optional, 10x schneller) |
| Speicher | 100 GB+ (für Hörbücher und Modelle) |

### Software-Voraussetzungen

```bash
# Docker installieren
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER

# Docker Compose (in Docker enthalten ab v24)
docker compose version
```

---

## 3. Projektstruktur

```
BookVoice-AI/
├── compose.server.yaml        # Docker Compose für Server
├── Dockerfile.tts             # TTS Container Build
├── tts_server.py              # FastAPI TTS Server (Haupt-Backend)
├── ki_archiv_tts_web.html     # Web-GUI (Frontend)
├── nginx-bookvoice.conf       # Nginx Reverse Proxy Config
└── README.md                  # Diese Dokumentation
```

### Docker Container

| Container | Port | Funktion |
|---|---|---|
| ki-archiv-tts | 7500 | TTS API Server (XTTS-v2) |
| ki-archiv-web | 7501 | Web-GUI (nginx static) |
| ki-archiv-proxy | 7502 | Reverse Proxy (GUI + API) |
| ollama | 11434 | LLM Server (optional) |
| open-webui | 3400 | Chat-Interface (optional) |

---

## 4. Installation — Schritt für Schritt

### Schritt 1: Repository klonen

```bash
git clone https://github.com/IsmailAksoy/BookVoice-AI.git
cd BookVoice-AI
```

### Schritt 2: Verzeichnisse anlegen

```bash
sudo mkdir -p /mnt/data/docker-data/ki-archiv/{EINGABE,ARCHIV,ERGEBNISSE,HOERBUCH,tts_models,models,webui_storage,nllb_models}
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

### Schritt 4: Web-GUI Container starten

```bash
docker run -d \
  --name ki-archiv-web \
  -p 7501:80 \
  -v /mnt/data/docker-data/ki-archiv/ki_archiv_tts_web.html:/usr/share/nginx/html/index.html:ro \
  nginx:alpine
```

### Schritt 5: TTS Server bauen und starten

```bash
cd /mnt/data/docker-data/ki-archiv
docker compose -f compose.server.yaml up -d ki-archiv-tts
```

> **Hinweis:** Beim ersten Start wird das XTTS-v2 Modell heruntergeladen (~1.8 GB). Das dauert je nach Internetgeschwindigkeit 5–15 Minuten.

### Schritt 6: Nginx Proxy starten

```bash
docker compose -f compose.server.yaml up -d ki-archiv-proxy
```

### Schritt 7: Installation prüfen

```bash
# Health-Check
curl http://localhost:7502/api/health
# Erwartete Antwort: {"status":"ok","device":"cpu"}

# Web-GUI
curl http://localhost:7502/ | head -5
```

### Schritt 8: Referenzstimme hinzufügen

```bash
# WAV-Datei (20–60 Sekunden, klare Sprache) nach tts_models kopieren
cp meine_stimme.wav /mnt/data/docker-data/ki-archiv/tts_models/stimme.wav
```

---

## 5. Konfiguration

### compose.server.yaml — Wichtige Einstellungen

```yaml
services:
  ki-archiv-tts:
    environment:
      - TTS_OUTPUT=/app/HOERBUCH   # Ausgabe-Ordner
      - TTS_LANG=tr                # Standard-Sprache
      - COQUI_TOS_AGREED=1        # Lizenz-Bestätigung
```

### Volume-Mapping

```yaml
volumes:
  - /mnt/data/docker-data/ki-archiv/tts_models:/app/tts_models
  - /mnt/data/docker-data/ki-archiv/HOERBUCH:/app/HOERBUCH
  - /mnt/data/docker-data/ki-archiv/tts_server.py:/app/tts_server.py  # Live-Reload
```

> **Wichtig:** Das `tts_server.py` Volume ermöglicht Live-Änderungen ohne Rebuild. Nach Änderungen nur `docker restart ki-archiv-tts` nötig.

### Stimme-Parameter anpassen

In `tts_server.py` oder über die Web-GUI:

| Parameter | Wert | Beschreibung |
|---|---|---|
| temperature | 0.1–1.0 | Wärme/Emotion (Standard: 0.5) |
| repetition_penalty | 2–15 | Natürlichkeit (Standard: 5.0) |
| top_k | 10–100 | Kreativität (Standard: 30) |

---

## 6. Deployment auf Server

### Proxmox Setup (optional)

```bash
# Dynamisches RAM (Ballooning) aktivieren
qm set 100 --memory 28672 --balloon 4096

# Balloon Driver in Ubuntu VM
sudo apt install virtio-balloon-dkms
sudo modprobe virtio_balloon
```

### Alle Container auf einmal starten

```bash
cd /mnt/data/docker-data/ki-archiv

# TTS + Proxy
docker compose -f compose.server.yaml up -d

# Web-GUI
docker run -d \
  --name ki-archiv-web \
  -p 7501:80 \
  -v /mnt/data/docker-data/ki-archiv/ki_archiv_tts_web.html:/usr/share/nginx/html/index.html:ro \
  nginx:alpine
```

### Container-Status prüfen

```bash
docker ps | grep ki-archiv
```

### Logs anzeigen

```bash
# TTS Server Logs
docker logs ki-archiv-tts -f

# Proxy Logs
docker logs ki-archiv-proxy -f
```

### Neu starten (nach Code-Änderungen)

```bash
# Nur tts_server.py geändert:
docker restart ki-archiv-tts

# GUI geändert:
docker restart ki-archiv-web ki-archiv-proxy

# Alles neu bauen (Dockerfile geändert):
docker compose -f compose.server.yaml up -d --build ki-archiv-tts
```

---

## 7. Cloudflare Tunnel & Zugang

### Tunnel einrichten

1. Cloudflare Dashboard → **Zero Trust** → **Tunnels**
2. Tunnel auswählen → **Public Hostname** → **Add**
3. Eintrag hinzufügen:
   - Subdomain: `hoerbuch` (oder eigene Wahl)
   - Domain: `deine-domain.de`
   - Type: `HTTP`
   - URL: `10.10.10.10:7502` (Server-IP:Proxy-Port)

### Zugangs-Policy (E-Mail-Authentifizierung)

1. **Zero Trust** → **Access** → **Applications** → **Add**
2. **Self-hosted and private** auswählen
3. Application domain: `hoerbuch.deine-domain.de`
4. Policy hinzufügen:
   - Name: `Benutzer-Zugang`
   - Action: `Allow`
   - Include → **Emails** → Erlaubte E-Mail-Adressen eintragen
5. Speichern

> User erhalten bei Zugang eine Magic-Link-E-Mail — kein Passwort nötig.

---

## 8. Web-GUI Bedienung

### Zugang

- **Intern:** `http://SERVER-IP:7502`
- **Extern:** `https://hoerbuch.deine-domain.de`

### Hörbuch erstellen

1. **Sprache** auswählen (TR/DE/EN)
2. **Text eingeben** oder **Datei hochladen** (TXT, PDF)
3. **Referenzstimme** auswählen oder neue hochladen
4. **Stimme einstellen** (Wärme, Natürlichkeit, Kreativität)
5. **Format** wählen (MP3/M4B/WAV)
6. **Projekt-Name** eingeben
7. **HÖRBUCH GENERIEREN** klicken
8. Fortschritt im **System Log** und **Aktive Jobs** verfolgen
9. Fertige Datei unter **Fertige Dateien** herunterladen

### SML Tags im Text

```
Normaler Text [pause] nach Pause weiter.
Kapitelende [pause:3] nächstes Kapitel.
Kurze Pause [break] im Satz.
```

### Stimme hochladen

- Klick auf **⬆ Upload** bei Referenzstimme
- WAV oder MP3 auswählen (20–60 Sekunden empfohlen)
- Stimme wird automatisch zu WAV konvertiert
- Sofort verfügbar für neue Generierungen

---

## 9. API-Referenz

### Base URL

```
http://SERVER-IP:7500
# oder über Proxy:
http://SERVER-IP:7502/api
```

### Endpoints

#### Health Check
```http
GET /health
Response: {"status":"ok","device":"cpu"}
```

#### Text zu Audio (synchron)
```http
POST /tts/generate
Content-Type: application/json

{
  "text": "Merhaba dünya!",
  "language": "tr",
  "speaker_wav": "/app/tts_models/stimme.wav",
  "filename": "test.wav"
}
```

#### Buch generieren (asynchron)
```http
POST /tts/book
Content-Type: application/json

{
  "chapters": ["Kapitel 1 Text...", "Kapitel 2 Text..."],
  "language": "tr",
  "speaker_wav": "/app/tts_models/stimme.wav",
  "book_name": "mein_buch",
  "output_format": "mp3",
  "temperature": 0.65,
  "repetition_penalty": 4.0,
  "top_k": 25
}

Response: {"job_id": "abc123", "status": "gestartet", "kapitel_anzahl": 2}
```

#### Job-Status abfragen
```http
GET /tts/book/status/{job_id}
Response: {"status":"running","total":2,"done":1,"files":["kapitel_001.wav"]}
```

#### Dateien auflisten
```http
GET /tts/files
Response: {"dateien":[{"name":"test.wav","groesse_mb":1.2}],"anzahl":1}
```

#### Datei herunterladen
```http
GET /tts/download/{filename}
```

#### Datei löschen
```http
DELETE /tts/files/{filename}
```

#### Stimme hochladen
```http
POST /tts/upload-voice
Content-Type: multipart/form-data
file: <WAV/MP3/MP4 Datei>
```

#### Stimmen auflisten
```http
GET /tts/voices
Response: {"stimmen":[{"name":"stimme.wav","groesse_kb":456}]}
```

#### Stimme löschen
```http
DELETE /tts/voices/{filename}
```

#### System-Info
```http
GET /system/info
Response: {"device":"cpu","cuda_available":false,"model_loaded":true}
```

---

## 10. Stimmen verwalten

### Empfehlungen für gute Stimm-Aufnahmen

- Länge: **30–60 Sekunden**
- Format: WAV (22050 Hz, Mono)
- Umgebung: Ruhiger Raum, kein Hintergrundgeräusch
- Inhalt: In der Zielsprache sprechen
- Qualität: Klare, deutliche Aussprache

### Stimme aus YouTube extrahieren

```bash
# yt-dlp installieren
winget install yt-dlp

# Audio herunterladen
yt-dlp -x --audio-format mp3 "https://youtube.com/watch?v=..."

# 60 Sekunden ausschneiden (ab Minute 2)
ffmpeg -i video.mp3 -ss 00:02:00 -t 00:01:00 -acodec pcm_s16le -ar 22050 -ac 1 stimme.wav
```

### Stimme auf Server hochladen

```bash
scp stimme.wav user@server:/mnt/data/docker-data/ki-archiv/tts_models/
```

### Parameter für verschiedene Textstile

| Textstil | Temperature | Rep. Penalty | Top-K |
|---|---|---|---|
| Sachtext/Nachricht | 0.3 | 8.0 | 40 |
| Roman/Erzählung | 0.6 | 5.0 | 30 |
| Sufi/Spirituell | 0.65 | 4.0 | 25 |
| Lyrik/Poesie | 0.75 | 3.0 | 20 |

---

## 11. Formate & Ausgabe

### MP3
- Standard für alle Geräte
- Kleinste Dateigröße
- Ideal für WhatsApp, E-Mail

### M4B
- Offizielles Hörbuch-Format (Apple/iPhone)
- Kapitel-Navigation
- Lesezeichen-Funktion
- Metadaten eingebettet

### WAV
- Verlustfreie Qualität
- Größte Dateien
- Für Nachbearbeitung geeignet

### Automatisches Zusammenfügen

Alle Kapitel werden automatisch zu einer finalen Datei zusammengefügt:
```
hoerbuch/
├── kapitel_001.wav
├── kapitel_002.wav
├── kapitel_003.wav
└── hoerbuch_komplett.mp3  ← Finale Datei
```

---

## 12. Troubleshooting

### Container startet nicht

```bash
# Logs prüfen
docker logs ki-archiv-tts --tail 30

# Container neu starten
docker restart ki-archiv-tts
```

### OFFLINE in Web-GUI

```bash
# API-Erreichbarkeit prüfen
curl http://localhost:7502/api/health

# Proxy prüfen
docker logs ki-archiv-proxy --tail 10
```

### Stimme klingt verzerrt

- Referenzstimme zu kurz (unter 20 Sek.) → längere Aufnahme machen
- Temperature zu hoch → auf 0.3–0.5 reduzieren
- Hintergrundgeräusche in Referenz → sauberere Aufnahme verwenden

### "400 Token" Fehler

Wird automatisch durch Text-Splitting gelöst. Falls trotzdem Fehler:
```python
# In tts_server.py split_text() max_chars reduzieren
max_chars: int = 180  # statt 220
```

### Port bereits belegt

```bash
# Belegte Ports anzeigen
sudo ss -tlnp | grep docker-proxy

# Anderen Port in compose.server.yaml verwenden
ports:
  - "7503:80"  # anderen Port wählen
```

### Speicher voll

```bash
# Alte Hörbücher löschen
rm -rf /mnt/data/docker-data/ki-archiv/HOERBUCH/*

# Speicher prüfen
df -h /mnt/data
```

---

## 13. GitHub Veröffentlichung

### Repository vorbereiten

```bash
git init
git add .
git commit -m "BookVoice-AI v1.0 — Self-hosted AI audiobook studio"
git branch -M main
git remote add origin https://github.com/USERNAME/BookVoice-AI.git
git push -u origin main
```

### .gitignore

```
tts_models/
HOERBUCH/
EINGABE/
ARCHIV/
ERGEBNISSE/
__pycache__/
*.pyc
.env
```

### Tags & Releases

```bash
git tag -a v1.0 -m "Version 1.0 — Initial Release"
git push origin v1.0
```

---

## Kontakt & Support

**Entwickler:** Ismail Aksoy  
**Projekt:** BookVoice-AI  
**Server:** Aksoy-Net Homelab  
**GitHub:** github.com/IsmailAksoy/BookVoice-AI

---

*BookVoice-AI — Open Source AI Audiobook Studio*  
*Powered by XTTS-v2, FastAPI, Docker & Cloudflare*
