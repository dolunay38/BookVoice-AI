#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║      BookVoice-AI - One Click Install    ║${NC}"
echo -e "${GREEN}  ║      AI Audiobook Studio v1.0            ║${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════╝${NC}"
echo ""

INSTALL_DIR="$HOME/BookVoice-AI"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GPU_MODE=0

# ── Docker prüfen ───────────────────────────────
echo -e "${GREEN}[1/6]${NC} Prüfe Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[FEHLER]${NC} Docker ist nicht installiert!"
    echo ""
    echo "Bitte Docker installieren:"
    echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | bash"
    echo "  Mac: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo -e "${RED}[FEHLER]${NC} Docker läuft nicht! Bitte Docker starten."
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Docker gefunden und läuft!"

# ── GPU prüfen ───────────────────────────────────
echo ""
echo -e "${GREEN}[2/6]${NC} Prüfe GPU..."
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo -e "${YELLOW}[GPU]${NC} NVIDIA GPU gefunden: $GPU_NAME"
    echo -e "${YELLOW}[GPU]${NC} BookVoice-AI wird GPU-beschleunigt laufen - 10x schneller!"
    GPU_MODE=1

    # NVIDIA Container Toolkit prüfen
    if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}[GPU]${NC} Installiere NVIDIA Container Toolkit..."
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt update && sudo apt install -y nvidia-container-toolkit
        sudo systemctl restart docker
    fi
else
    echo -e "${BLUE}[CPU]${NC} Kein NVIDIA GPU - läuft auf CPU"
    echo -e "${BLUE}[CPU]${NC} Tipp: Mit GPU wird Hörbuch-Generierung 10x schneller"
fi

# ── Ordner anlegen ───────────────────────────────
echo ""
echo -e "${GREEN}[3/6]${NC} Erstelle Ordner..."
mkdir -p "$INSTALL_DIR"/{HOERBUCH,tts_models,musik}
echo -e "${GREEN}[OK]${NC} Ordner erstellt: $INSTALL_DIR"

# ── Dateien kopieren ─────────────────────────────
echo ""
echo -e "${GREEN}[4/6]${NC} Kopiere Dateien..."
cp "$SCRIPT_DIR/compose.yaml" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/tts_server.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/Dockerfile.tts" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ki_archiv_tts_web.html" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/nginx-bookvoice.conf" "$INSTALL_DIR/"
echo -e "${GREEN}[OK]${NC} Alle Dateien kopiert!"

# ── Container starten ────────────────────────────
echo ""
echo -e "${GREEN}[5/6]${NC} Starte BookVoice-AI..."
echo "  Erster Start lädt ~2GB KI-Modell - bitte warten!"
echo ""
cd "$INSTALL_DIR"
docker compose -f compose.yaml up -d

# Web-GUI
docker stop bookvoice-web 2>/dev/null || true
docker rm bookvoice-web 2>/dev/null || true
docker run -d --name bookvoice-web -p 7501:80 \
  -v "$INSTALL_DIR/ki_archiv_tts_web.html:/usr/share/nginx/html/index.html:ro" \
  nginx:alpine

# ── Warten bis bereit ────────────────────────────
echo ""
echo -e "${GREEN}[6/6]${NC} Warte auf Server..."
COUNTER=0
until curl -s http://localhost:7500/health &> /dev/null; do
    COUNTER=$((COUNTER+1))
    if [ $COUNTER -gt 60 ]; then
        echo -e "${RED}[TIMEOUT]${NC} Server antwortet nicht"
        break
    fi
    sleep 5
    echo "  Lädt... ($COUNTER)"
done

echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║                                          ║${NC}"
echo -e "${GREEN}  ║   BookVoice-AI ist bereit! 🎙️            ║${NC}"
if [ $GPU_MODE -eq 1 ]; then
echo -e "${YELLOW}  ║   Modus: GPU-Beschleunigt ⚡              ║${NC}"
else
echo -e "${BLUE}  ║   Modus: CPU                             ║${NC}"
fi
echo -e "${GREEN}  ║                                          ║${NC}"
echo -e "${GREEN}  ║   Browser: http://localhost:7502         ║${NC}"
echo -e "${GREEN}  ║                                          ║${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════╝${NC}"
echo ""

# Browser öffnen
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:7502
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:7502
fi

echo -e "${GREEN}Installation abgeschlossen!${NC} 🎉"
