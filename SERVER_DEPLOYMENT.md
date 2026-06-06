# BookVoice-AI — Server Deployment Guide

**Für Proxmox / Ubuntu VM / VPS · Multi-User · 24/7 Betrieb**

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Server vorbereiten](#2-server-vorbereiten)
3. [Installation](#3-installation)
4. [Cloudflare Tunnel](#4-cloudflare-tunnel)
5. [Zugangs-Policy](#5-zugangs-policy)
6. [Container verwalten](#6-container-verwalten)
7. [Proxmox Optimierung](#7-proxmox-optimierung)

---

## 1. Voraussetzungen

| Komponente | Minimum | Empfohlen |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| RAM | 8 GB | 16–32 GB |
| CPU | 4 Kerne | 8+ Kerne |
| Speicher | 50 GB | 200 GB+ |
| Docker | 24.x | aktuell |
| GPU | optional | NVIDIA (10x schneller) |

---

## 2. Server vorbereiten

### Docker installieren

```bash
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

### Verzeichnisse anlegen

```bash
sudo mkdir -p /mnt/data/docker-data/ki-archiv/{HOERBUCH,TRANSKRIPTIONEN,tts_models,musik,EINGABE,ERGEBNISSE,ARCHIV,models,webui_storage,nllb_models}
sudo chown -R $USER:$USER /mnt/data/docker-data/ki-archiv
```

### (Optional) NVIDIA GPU Support

```bash
# NVIDIA Container Toolkit installieren
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Testen
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

---

## 3. Installation

### Repository klonen

```bash
git clone https://github.com/dolunay38/BookVoice-AI.git
cd BookVoice-AI
```

### Dateien auf Server kopieren

```bash
cp compose.server.yaml /mnt/data/docker-data/ki-archiv/
cp Dockerfile.tts /mnt/data/docker-data/ki-archiv/
cp tts_server.py /mnt/data/docker-data/ki-archiv/
cp ki_archiv_tts_web.html /mnt/data/docker-data/ki-archiv/
cp nginx-bookvoice.conf /mnt/data/docker-data/ki-archiv/
```

### Container starten

```bash
cd /mnt/data/docker-data/ki-archiv

# TTS Server + Proxy
docker compose -f compose.server.yaml up -d ki-archiv-tts
docker compose -f compose.server.yaml up -d ki-archiv-proxy

# Web-GUI
docker run -d \
  --name ki-archiv-web \
  -p 7501:80 \
  -v /mnt/data/docker-data/ki-archiv/ki_archiv_tts_web.html:/usr/share/nginx/html/index.html:ro \
  nginx:alpine
```

### Health Check

```bash
# API prüfen
curl http://localhost:7500/health
# Erwartete Antwort: {"status":"ok","device":"cpu"}

# Proxy prüfen
curl http://localhost:7502/api/health
# Erwartete Antwort: {"status":"ok","device":"cpu"}
```

### Referenzstimme hochladen

```bash
# WAV-Datei (20-60 Sekunden) nach tts_models kopieren
cp stimme.wav /mnt/data/docker-data/ki-archiv/tts_models/
```

### Erster Start — Modell Download

Beim ersten Start wird das XTTS-v2 Modell automatisch heruntergeladen (~1.8 GB):

```bash
docker logs ki-archiv-tts -f
# Warten bis: ✅ XTTS-v2 bereit!
```

---

## 4. Cloudflare Tunnel

### Neuen Hostname hinzufügen

1. **dash.cloudflare.com** → **Zero Trust** → **Tunnels**
2. Tunnel auswählen → **Public Hostname** → **Add**
3. Eintrag:
   - Subdomain: `hoerbuch` (oder eigene Wahl)
   - Domain: `deine-domain.de`
   - Type: `HTTP`
   - URL: `SERVER-IP:7502`
4. **Save** klicken

### Ports Übersicht

| Port | Service | Beschreibung |
|---|---|---|
| 7500 | TTS API | FastAPI Backend (intern) |
| 7501 | Web-GUI | nginx static (intern) |
| 7502 | Proxy | GUI + API zusammen (öffentlich) |

> **Wichtig:** Nur Port 7502 über Cloudflare freigeben!

---

## 5. Zugangs-Policy

### E-Mail Authentifizierung einrichten

1. **Zero Trust** → **Access** → **Applications** → **Add**
2. **Self-hosted and private** auswählen
3. **Application domain:** `hoerbuch.deine-domain.de`
4. Policy konfigurieren:
   - **Policy name:** `BookVoice Zugang`
   - **Action:** `Allow`
   - **Include** → **Emails** → Erlaubte E-Mail-Adressen eintragen
5. **Save** klicken

User erhalten bei Zugang automatisch eine Magic-Link E-Mail — kein Passwort nötig!

---

## 6. Container verwalten

### Status prüfen

```bash
docker ps | grep -E "ki-archiv|bookvoice"
```

### Logs anzeigen

```bash
# TTS Server
docker logs ki-archiv-tts -f

# Proxy
docker logs ki-archiv-proxy -f
```

### Neu starten

```bash
# Nach Code-Änderungen (kein Rebuild nötig):
docker restart ki-archiv-tts

# Alles neu starten:
docker restart ki-archiv-tts ki-archiv-web ki-archiv-proxy

# Komplett neu bauen (Dockerfile geändert) — IMMER --no-cache verwenden!
cd /mnt/data/docker-data/ki-archiv
docker compose -f compose.server.yaml build --no-cache ki-archiv-tts
docker compose -f compose.server.yaml up -d ki-archiv-tts
```

### Stoppen

```bash
docker compose -f compose.server.yaml down
docker stop ki-archiv-web
```

### Speicher verwalten

```bash
# Aktuelle Belegung
df -h /mnt/data

# Alte Hörbücher löschen
rm -rf /mnt/data/docker-data/ki-archiv/HOERBUCH/*

# Docker aufräumen
docker system prune -f
```

---

## 7. Proxmox Optimierung

### Dynamisches RAM (Ballooning)

```bash
# Auf Proxmox Host ausführen
qm set VM_ID --memory 28672 --balloon 4096

# Balloon Driver in Ubuntu VM
sudo apt install -y virtio-balloon-dkms
sudo modprobe virtio_balloon
echo "virtio_balloon" | sudo tee -a /etc/modules
```

### Empfohlene VM Einstellungen

| Einstellung | Wert |
|---|---|
| RAM Min (Balloon) | 4 GB |
| RAM Max | 24–28 GB |
| vCPUs | 4–8 |
| Disk | 100 GB+ (SSD) |
| OS | Ubuntu 24.04 |

### Frigate Aufnahmen bereinigen

Falls Frigate auf demselben Server läuft und Speicher frisst:

```bash
# Retention Policy in Frigate config.yml
record:
  retain:
    days: 3
    mode: motion
  events:
    retain:
      default: 7
      mode: active_objects
```

---

## Zugang

| Variante | URL |
|---|---|
| Intern | `http://SERVER-IP:7502` |
| Tailscale | `http://TAILSCALE-IP:7502` |
| Cloudflare | `https://hoerbuch.deine-domain.de` |

---

*BookVoice-AI Server Deployment · Aksoy-Net Homelab · 2026*
