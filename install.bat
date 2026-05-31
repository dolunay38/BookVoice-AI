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
echo [1/5] Pruefe Docker...
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  FEHLER: Docker ist nicht installiert!
    echo  Bitte Docker Desktop installieren:
    echo  https://www.docker.com/products/docker-desktop
    echo.
    start https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo  OK: Docker gefunden!

:: ── Docker starten falls nicht läuft ────────────
echo.
echo [2/5] Pruefe ob Docker laeuft...
docker ps > nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker laeuft nicht - versuche zu starten...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo  Warte 30 Sekunden auf Docker...
    timeout /t 30 /nobreak > nul
    
    docker ps > nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  FEHLER: Docker konnte nicht gestartet werden!
        echo  Bitte Docker Desktop manuell starten und erneut versuchen.
        pause
        exit /b 1
    )
)
echo  OK: Docker laeuft!

:: ── Ordner anlegen ───────────────────────────────
echo.
echo [3/5] Erstelle Ordner...
set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\HOERBUCH" mkdir "%INSTALL_DIR%\HOERBUCH"
if not exist "%INSTALL_DIR%\tts_models" mkdir "%INSTALL_DIR%\tts_models"
if not exist "%INSTALL_DIR%\musik" mkdir "%INSTALL_DIR%\musik"
echo  OK: Ordner erstellt: %INSTALL_DIR%

:: ── Dateien kopieren ─────────────────────────────
echo.
echo [4/5] Kopiere Dateien...
copy /Y "%~dp0compose.yaml" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0tts_server.py" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0Dockerfile.tts" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0ki_archiv_tts_web.html" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0nginx-bookvoice.conf" "%INSTALL_DIR%\" > nul

if not exist "%INSTALL_DIR%\compose.yaml" (
    echo  FEHLER: Dateien konnten nicht kopiert werden!
    echo  Bitte alle Dateien im gleichen Ordner wie install.bat haben!
    pause
    exit /b 1
)
echo  OK: Alle Dateien kopiert!

:: ── Container starten ────────────────────────────
echo.
echo [5/5] Starte BookVoice-AI...
echo  (Erster Start laedt ~2GB Modell - bitte warten!)
echo.
cd /d "%INSTALL_DIR%"

docker compose down > nul 2>&1
docker compose up -d --build

if %errorlevel% neq 0 (
    echo.
    echo  FEHLER: Container konnten nicht gestartet werden!
    echo  Bitte debug.bat ausfuehren und Ausgabe schicken.
    pause
    exit /b 1
)

:: ── Warten bis bereit ────────────────────────────
echo.
echo  Warte auf Server...
set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 60 goto DONE
curl -s http://localhost:7502 > nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 5 /nobreak > nul
    echo  Warte... (%COUNTER%/60)
    goto WAIT
)

:DONE
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   BookVoice-AI ist bereit!               ║
echo  ║   http://localhost:7502                  ║
echo  ╚══════════════════════════════════════════╝
echo.
start http://localhost:7502
pause
