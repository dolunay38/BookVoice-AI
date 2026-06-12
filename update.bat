@echo off
title BookVoice-AI Update
color 0A
setlocal enabledelayedexpansion

set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
set GITHUB_RAW=https://raw.githubusercontent.com/dolunay38/BookVoice-AI/main
set COMPOSE_FILE=compose.yaml

echo.
echo ==========================================
echo  BookVoice-AI - Update
echo ==========================================
echo.

REM ── Installiert? ─────────────────────────────────────────
if not exist "%INSTALL_DIR%\tts_server.py" (
    echo  FEHLER: BookVoice-AI nicht gefunden.
    echo  Bitte zuerst install.bat ausfuehren.
    pause
    exit /b 1
)

REM ── GPU-Modus ────────────────────────────────────────────
if exist "%INSTALL_DIR%\compose.gpu.yaml" (
    nvidia-smi > nul 2>&1
    if !errorlevel! equ 0 set COMPOSE_FILE=compose.gpu.yaml
)

REM ── [1/4] Versions-Check ─────────────────────────────────
echo [1/4] Pruefe Version...

set LOCAL_VERSION=unbekannt
if exist "%INSTALL_DIR%\version.txt" (
    set /p LOCAL_VERSION=<"%INSTALL_DIR%\version.txt"
)

set REMOTE_VERSION=unbekannt
curl -sf "%GITHUB_RAW%/version.txt" -o "%TEMP%\bv_version_check.txt" > nul 2>&1
if exist "%TEMP%\bv_version_check.txt" (
    set /p REMOTE_VERSION=<"%TEMP%\bv_version_check.txt"
    del "%TEMP%\bv_version_check.txt" > nul 2>&1
)

echo  Installiert: v!LOCAL_VERSION!
echo  GitHub:      v!REMOTE_VERSION!

if "!LOCAL_VERSION!"=="!REMOTE_VERSION!" (
    echo.
    echo  Bereits aktuell (v!LOCAL_VERSION!)
    echo  Trotzdem aktualisieren?
    set /p FORCE=  (j = ja, n = abbrechen): 
    if /i "!FORCE!" neq "j" (
        echo  Abgebrochen.
        pause
        exit /b 0
    )
) else (
    echo.
    echo  Update verfuegbar: v!LOCAL_VERSION! -> v!REMOTE_VERSION!
)

REM ── [2/4] Dateien holen ──────────────────────────────────
echo.
echo [2/4] Hole neue Dateien von GitHub...

REM git pull wenn vorhanden
if exist "%INSTALL_DIR%\.git" (
    cd /d "%INSTALL_DIR%"
    git pull
    if !errorlevel! neq 0 (
        echo  FEHLER: git pull fehlgeschlagen!
        echo  Versuche manuellen Download...
        goto MANUAL_DOWNLOAD
    )
    goto BUILD
)

REM Manueller Download (kein git)
:MANUAL_DOWNLOAD
echo  Lade Dateien direkt von GitHub...
curl -sf "%GITHUB_RAW%/tts_server.py"          -o "%INSTALL_DIR%\tts_server.py"
curl -sf "%GITHUB_RAW%/ki_archiv_tts_web.html" -o "%INSTALL_DIR%\ki_archiv_tts_web.html"
curl -sf "%GITHUB_RAW%/version.txt"            -o "%INSTALL_DIR%\version.txt"
if "!COMPOSE_FILE!"=="compose.gpu.yaml" (
    curl -sf "%GITHUB_RAW%/compose.gpu.yaml" -o "%INSTALL_DIR%\compose.gpu.yaml"
) else (
    curl -sf "%GITHUB_RAW%/compose.yaml" -o "%INSTALL_DIR%\compose.yaml"
)
echo  OK: Dateien aktualisiert

REM ── [3/4] Rebuild ────────────────────────────────────────
:BUILD
echo.
echo [3/4] Aktualisiere Container...
cd /d "%INSTALL_DIR%"

REM Nur rebuild wenn Dockerfile oder requirements sich geaendert haben
echo  Starte Container neu (ohne Rebuild - schnell)...
if "!COMPOSE_FILE!"=="compose.gpu.yaml" (
    docker compose -f compose.gpu.yaml up -d
) else (
    docker compose up -d
)

if !errorlevel! neq 0 (
    echo.
    echo  FEHLER! Versuche kompletten Rebuild...
    if "!COMPOSE_FILE!"=="compose.gpu.yaml" (
        docker compose -f compose.gpu.yaml up -d --build
    ) else (
        docker compose up -d --build
    )
)

REM ── [4/4] Status ─────────────────────────────────────────
echo.
echo [4/4] Status:
docker ps --filter "name=bookvoice" --format "  {{.Names}} - {{.Status}}"

echo.
echo ==========================================
echo  Update abgeschlossen!
echo  Version: v!REMOTE_VERSION!
echo  Browser: http://localhost:7502
echo ==========================================
echo.
start http://localhost:7502
pause
