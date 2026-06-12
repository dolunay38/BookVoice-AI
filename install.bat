@echo off
title BookVoice-AI Installer v2.3
color 0A
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  BookVoice-AI v2.3 - Installation
echo  KI Audiobook Studio
echo ==========================================
echo.

set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
set REPO=https://raw.githubusercontent.com/dolunay38/BookVoice-AI/main
set USE_GPU=0
set COMPOSE_FILE=compose.yaml

REM ── [1/7] WSL2 ──────────────────────────────────────────
echo [1/7] Pruefe WSL2...
wsl --status > nul 2>&1
if %errorlevel% neq 0 (
    echo  WSL2 nicht gefunden - installiere WSL2...
    wsl --install
    echo.
    echo  WSL2 installiert! Bitte PC neu starten
    echo  und install.bat erneut ausfuehren.
    pause
    exit /b 0
)
echo  OK: WSL2 vorhanden

REM ── [2/7] Docker ─────────────────────────────────────────
echo.
echo [2/7] Pruefe Docker...
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo  FEHLER: Docker nicht installiert!
    echo  Bitte installieren: https://www.docker.com/products/docker-desktop
    start https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo  OK: Docker gefunden

REM ── [3/7] Docker starten ─────────────────────────────────
echo.
echo [3/7] Pruefe ob Docker laeuft...
docker ps > nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker laeuft nicht - starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo  Warte 30 Sekunden...
    timeout /t 30 /nobreak > nul
    docker ps > nul 2>&1
    if %errorlevel% neq 0 (
        echo  FEHLER: Docker konnte nicht gestartet werden!
        echo  Bitte Docker Desktop manuell starten und erneut versuchen.
        pause
        exit /b 1
    )
)
echo  OK: Docker laeuft

REM ── [4/7] GPU erkennen ───────────────────────────────────
echo.
echo [4/7] Erkenne Hardware...
nvidia-smi > nul 2>&1
if %errorlevel% equ 0 (
    set USE_GPU=1
    set COMPOSE_FILE=compose.gpu.yaml
    echo  GPU gefunden: NVIDIA - GPU-Modus aktiv (10x schneller!)
) else (
    echo  Kein NVIDIA-GPU - CPU-Modus (funktioniert, etwas langsamer)
)

REM ── [5/7] Ordner + Konfiguration ─────────────────────────
echo.
echo [5/7] Erstelle Ordner und Konfiguration...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM nginx-bookvoice.conf schreiben
(
echo server {
echo     listen 80;
echo     server_name _;
echo     client_max_body_size 500M;
echo     location / {
echo         root /usr/share/nginx/html;
echo         index index.html;
echo         try_files $uri $uri/ /index.html;
echo     }
echo     location /api/ {
echo         rewrite ^/api/^(.*^) /$1 break;
echo         proxy_pass http://bookvoice-tts:7500;
echo         proxy_read_timeout 300s;
echo         proxy_send_timeout 300s;
echo         proxy_buffering off;
echo         client_max_body_size 500M;
echo     }
echo }
) > "%INSTALL_DIR%\nginx-bookvoice.conf"
echo  OK: nginx-bookvoice.conf erstellt

REM ── [6/7] Dateien kopieren ───────────────────────────────
echo.
echo [6/7] Kopiere Dateien...

set FILES_OK=1
for %%F in (tts_server.py ki_archiv_tts_web.html Dockerfile.tts nginx-bookvoice.conf) do (
    if not exist "%~dp0%%F" (
        echo  FEHLER: %%F nicht gefunden!
        set FILES_OK=0
    )
)
if "%USE_GPU%"=="1" (
    if not exist "%~dp0Dockerfile.tts.gpu" (
        echo  FEHLER: Dockerfile.tts.gpu nicht gefunden!
        set FILES_OK=0
    )
)
if "%FILES_OK%"=="0" (
    echo.
    echo  Bitte alle Dateien im gleichen Ordner wie install.bat haben!
    pause
    exit /b 1
)

copy /Y "%~dp0tts_server.py"          "%INSTALL_DIR%\" > nul
copy /Y "%~dp0ki_archiv_tts_web.html" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0Dockerfile.tts"         "%INSTALL_DIR%\" > nul
copy /Y "%~dp0nginx-bookvoice.conf"   "%INSTALL_DIR%\" > nul
copy /Y "%~dp0version.txt"            "%INSTALL_DIR%\" > nul
if "%USE_GPU%"=="1" (
    copy /Y "%~dp0Dockerfile.tts.gpu"  "%INSTALL_DIR%\" > nul
    copy /Y "%~dp0compose.gpu.yaml"    "%INSTALL_DIR%\" > nul
) else (
    copy /Y "%~dp0compose.yaml"        "%INSTALL_DIR%\" > nul
)
echo  OK: Alle Dateien kopiert

REM ── [7/7] Container starten ──────────────────────────────
echo.
echo [7/7] Starte BookVoice-AI...
echo  Erster Start laedt ca. 2GB KI-Modell - bitte warten!
echo  (kann 5-15 Minuten dauern je nach Internetgeschwindigkeit)
echo.
cd /d "%INSTALL_DIR%"

if "%USE_GPU%"=="1" (
    docker compose -f compose.gpu.yaml up -d --build
) else (
    docker compose up -d --build
)

if %errorlevel% neq 0 (
    echo.
    echo  FEHLER: Container konnten nicht gestartet werden!
    echo  Bitte debug.bat ausfuehren und Log an Support schicken.
    pause
    exit /b 1
)
echo  OK: Container gestartet

REM ── Warten bis bereit ────────────────────────────────────
echo.
echo  Warte auf Server (max. 5 Minuten)...
set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 60 goto TIMEOUT
curl -s http://localhost:7500/health > nul 2>&1
if %errorlevel% equ 0 goto READY
timeout /t 5 /nobreak > nul
if %COUNTER% equ 1  echo  Lade KI-Modell... (kann einige Minuten dauern)
if %COUNTER% equ 12 echo  Noch da - grosse Modelle brauchen Zeit...
if %COUNTER% equ 24 echo  Fast fertig...
goto WAIT

:TIMEOUT
echo.
echo  Hinweis: Server braucht laenger als erwartet.
echo  Warte noch 2 Minuten und oeffne dann http://localhost:7502
echo  Bei Problemen: debug.bat ausfuehren
goto OPEN

:READY
echo  OK: Server bereit!

:OPEN
echo.
echo ==========================================
if "%USE_GPU%"=="1" (
echo   Modus: GPU-beschleunigt (NVIDIA) ^^^!
) else (
echo   Modus: CPU
)
echo.
echo   BookVoice-AI ist bereit!
echo   Browser: http://localhost:7502
echo ==========================================
echo.
start http://localhost:7502
pause
