@echo off
title BookVoice-AI Installer
color 0A
chcp 65001 > nul

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      BookVoice-AI - One Click Install    ║
echo  ║      AI Audiobook Studio v1.0            ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Docker prüfen ───────────────────────────────
echo [1/6] Pruefe Docker...
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [FEHLER] Docker ist nicht installiert!
    echo.
    echo  Bitte zuerst Docker Desktop installieren:
    echo  https://www.docker.com/products/docker-desktop
    echo.
    start https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo  [OK] Docker gefunden!

docker ps > nul 2>&1
if %errorlevel% neq 0 (
    echo  [FEHLER] Docker Desktop laeuft nicht!
    echo  Bitte Docker Desktop starten und erneut versuchen.
    pause
    exit /b 1
)
echo  [OK] Docker laeuft!

:: ── GPU prüfen ───────────────────────────────────
echo.
echo [2/6] Pruefe GPU...
nvidia-smi > nul 2>&1
if %errorlevel% == 0 (
    echo  [GPU] NVIDIA GPU gefunden!
    echo  [GPU] BookVoice-AI wird GPU-beschleunigt laufen - 10x schneller!
    set GPU_MODE=1
) else (
    echo  [CPU] Kein NVIDIA GPU - laeuft auf CPU
    echo  [CPU] Tipp: Mit GPU wird Hoerbuch-Generierung 10x schneller
    set GPU_MODE=0
)

:: ── Ordner anlegen ───────────────────────────────
echo.
echo [3/6] Erstelle Ordner...
set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\HOERBUCH" mkdir "%INSTALL_DIR%\HOERBUCH"
if not exist "%INSTALL_DIR%\tts_models" mkdir "%INSTALL_DIR%\tts_models"
if not exist "%INSTALL_DIR%\musik" mkdir "%INSTALL_DIR%\musik"
echo  [OK] Ordner erstellt: %INSTALL_DIR%

:: ── Dateien kopieren ─────────────────────────────
echo.
echo [4/6] Kopiere Dateien...
copy /Y "%~dp0compose.yaml" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0tts_server.py" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0Dockerfile.tts" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0ki_archiv_tts_web.html" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0nginx-bookvoice.conf" "%INSTALL_DIR%\" > nul
echo  [OK] Alle Dateien kopiert!

:: ── Container bauen und starten ──────────────────
echo.
echo [5/6] Starte BookVoice-AI...
echo  Erster Start laedt ~2GB KI-Modell - bitte warten!
echo  (Internet-Verbindung benoetigt)
echo.
cd /d "%INSTALL_DIR%"

if %GPU_MODE% == 1 (
    echo  [GPU] Starte mit GPU-Unterstuetzung...
    docker compose -f compose.yaml up -d
) else (
    echo  [CPU] Starte im CPU-Modus...
    docker compose -f compose.yaml up -d
)

if %errorlevel% neq 0 (
    echo.
    echo  [FEHLER] Container konnte nicht gestartet werden!
    echo  Bitte Docker Desktop neu starten und erneut versuchen.
    pause
    exit /b 1
)

:: Web-GUI starten
docker stop bookvoice-web > nul 2>&1
docker rm bookvoice-web > nul 2>&1
docker run -d --name bookvoice-web -p 7501:80 ^
  -v "%INSTALL_DIR%\ki_archiv_tts_web.html:/usr/share/nginx/html/index.html:ro" ^
  nginx:alpine > nul 2>&1

:: ── Warten bis bereit ────────────────────────────
echo.
echo [6/6] Warte auf BookVoice-AI Server...
echo  (Kann beim ersten Mal 5-15 Minuten dauern)
echo.

set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 100 (
    echo  [TIMEOUT] Server antwortet nicht - bitte manuell pruefen
    goto DONE
)
curl -s http://localhost:7500/health > nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 5 /nobreak > nul
    echo  Warte... (%COUNTER%)
    goto WAIT
)

:DONE
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║                                          ║
echo  ║   BookVoice-AI ist bereit!               ║
if %GPU_MODE% == 1 (
echo  ║   Modus: GPU-Beschleunigt ⚡              ║
) else (
echo  ║   Modus: CPU                             ║
)
echo  ║                                          ║
echo  ║   Browser: http://localhost:7502         ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Browser öffnen
start http://localhost:7502

echo  Tipp: BookVoice-AI startet automatisch mit Windows
echo  Um es zu stoppen: docker compose down
echo.
pause
