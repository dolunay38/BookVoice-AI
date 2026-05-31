# BookVoice-AI 🎙️📖

**Open-Source KI Hörbuch-Studio** — Texte, eBooks und Fotos in hochwertige Hörbücher verwandeln.

![BookVoice-AI](https://img.shields.io/badge/Version-1.0-green) ![Docker](https://img.shields.io/badge/Docker-Required-blue) ![Python](https://img.shields.io/badge/Python-3.11-blue)

---

## ⚡ One-Click Installation

### Windows
```cmd
install.bat
```
Doppelklick auf `install.bat` — fertig!

### Linux / Mac
```bash
chmod +x install.sh && ./install.sh
```

**Voraussetzung:** [Docker Desktop](https://www.docker.com/products/docker-desktop) installiert

---

## ✨ Features

| Feature | Beschreibung |
|---|---|
| 🎙️ Voice Cloning | Eigene Stimme hochladen → KI spricht damit |
| 📚 eBook Support | EPUB, MOBI, PDF, AZW3 direkt hochladen |
| 📸 OCR | Foto von Buchseite → automatisch Text erkennen |
| 🎵 Hintergrundmusik | Musik mit Hörbuch mischen |
| 🌍 Multi-Sprache | Türkisch, Deutsch, Englisch, Arabisch |
| 🎛️ Stil-Presets | Sufi, Roman, Sachtext, Dramatisch... |
| 📱 M4B Format | iPhone Hörbuch-Format mit Kapitel-Navigation |
| 🖥️ Web-GUI | Modernes Browser-Interface |
| 🐳 Docker | Ein Befehl — läuft überall |

---

## 🖼️ Screenshots

*Web-GUI im Matrix-Style*

---

## 🖥️ Server Deployment (Proxmox / Ubuntu / VPS)

Für 24/7 Betrieb mit mehreren Usern über Cloudflare:

```bash
git clone https://github.com/dolunay38/BookVoice-AI.git
cd BookVoice-AI
docker compose -f compose.server.yaml up -d
```

📖 **Vollständige Server-Anleitung:** [SERVER_DEPLOYMENT.md](SERVER_DEPLOYMENT.md)

Enthält:
- Proxmox VM Setup & Ballooning
- Cloudflare Tunnel Konfiguration
- E-Mail Zugangs-Policy
- GPU Support (NVIDIA)
- Container Verwaltung

---

## 🚀 Verwendung

1. Installation starten → Browser öffnet automatisch
2. **Projekt-Namen** eingeben
3. **Text** eingeben oder Datei hochladen
4. **Stimme** auswählen oder eigene hochladen
5. **Stil-Preset** wählen (z.B. Sufi für religiöse Texte)
6. **Test-Audio** generieren und anhören
7. **HÖRBUCH GENERIEREN** klicken
8. Fertige MP3/M4B herunterladen

### SML Tags für natürlicheres Vorlesen

```
Bismillah. [pause:2] Bu kitabın birinci bölümü...
[break] Ve böylece devam etti.
```

---

## 📁 Projektstruktur

```
BookVoice-AI/
├── install.bat          # Windows Installer
├── install.sh           # Linux/Mac Installer
├── compose.yaml         # Docker Compose
├── Dockerfile.tts       # TTS Container
├── tts_server.py        # FastAPI Backend
├── ki_archiv_tts_web.html  # Web-GUI
└── nginx-bookvoice.conf # Reverse Proxy
```

---

## 🔧 Systemvoraussetzungen

| | Minimum | Empfohlen |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Speicher | 10 GB frei | 50 GB |
| CPU | 4 Kerne | 8+ Kerne |
| GPU | Nicht nötig | NVIDIA (10x schneller) |

---

## 🌐 Server-Deployment

Für Server-Deployment (Proxmox, Ubuntu VM):

```bash
git clone https://github.com/IsmailAksoy/BookVoice-AI.git
cd BookVoice-AI
docker compose -f compose.server.yaml up -d
```

---

## 📖 Für welche Texte geeignet?

- Sufi & islamische Literatur (Türkisch)
- Romane & Erzählungen
- Sachtexte & Nachrichten
- Kinderbücher
- Lernmaterialien
- Religiöse Texte (Arabisch)

---

## 🤝 Mitmachen

Pull Requests willkommen! Geplante Features:

- [ ] Mehrere Stimmen pro Buch (Dialoge)
- [ ] Automatische Kapitel-Erkennung
- [ ] Mobile App
- [ ] Mehr Sprachen

---

## 📄 Lizenz

MIT License — kostenlos für private und kommerzielle Nutzung.

**Powered by:** XTTS-v2 · FastAPI · Docker · Nginx · Cloudflare

---

*BookVoice-AI — Entwickelt von Ismail Aksoy · Aksoy-Net Homelab · 2026*
