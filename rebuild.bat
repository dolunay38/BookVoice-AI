@echo off
title BookVoice-AI Rebuild
color 0A
setlocal enabledelayedexpansion

set INSTALL_DIR=%USERPROFILE%\BookVoice-AI

echo.
echo ==========================================
echo  BookVoice-AI - Einmaliger Rebuild
echo  (Wegen neuem YouTube-Fix)
echo ==========================================
echo.

REM ── Installiert? ─────────────────────────────────────────
if not exist "%INSTALL_DIR%\tts_server.py" (
    echo  FEHLER: BookVoice-AI nicht gefunden.
    echo  Bitte zuerst install.bat ausfuehren.
    pause
    exit /b 1
)

REM ── Neue Dateien kopieren ────────────────────────────────
echo [1/3] Kopiere neue Dateien...
copy /Y "%~dp0Dockerfile.tts"         "%INSTALL_DIR%\" > nul
copy /Y "%~dp0start.sh"               "%INSTALL_DIR%\" > nul
copy /Y "%~dp0tts_server.py"          "%INSTALL_DIR%\" > nul
copy /Y "%~dp0ki_archiv_tts_web.html" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0version.txt"            "%INSTALL_DIR%\" > nul
echo  OK: Dateien kopiert

REM ── GPU erkennen ─────────────────────────────────────────
set COMPOSE_FILE=compose.yaml
nvidia-smi > nul 2>&1
if %errorlevel% equ 0 (
    if exist "%~dp0compose.gpu.yaml" copy /Y "%~dp0compose.gpu.yaml" "%INSTALL_DIR%\" > nul
    if exist "%~dp0Dockerfile.tts.gpu" copy /Y "%~dp0Dockerfile.tts.gpu" "%INSTALL_DIR%\" > nul 2>&1
    if exist "%INSTALL_DIR%\compose.gpu.yaml" (
        if exist "%INSTALL_DIR%\Dockerfile.tts.gpu" (
            set COMPOSE_FILE=compose.gpu.yaml
        ) else (
            echo  Hinweis: Dockerfile.tts.gpu fehlt - nutze CPU-Modus
        )
    )
)

REM ── Rebuild ──────────────────────────────────────────────
echo.
echo [2/3] Baue Container neu (einmalig, ca. 5-10 Min)...
echo  Bitte warten - YouTube-Fix wird eingebaut...
echo.
cd /d "%INSTALL_DIR%"

if "!COMPOSE_FILE!"=="compose.gpu.yaml" (
    docker compose -f compose.gpu.yaml up -d --build
) else (
    docker compose up -d --build
)

if %errorlevel% neq 0 (
    echo.
    echo  FEHLER beim Rebuild!
    echo  Bitte debug.bat ausfuehren.
    pause
    exit /b 1
)

REM ── Warten ───────────────────────────────────────────────
echo.
echo [3/3] Warte auf Server...
set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 60 goto OPEN
curl -s http://localhost:7500/health > nul 2>&1
if %errorlevel% equ 0 goto READY
timeout /t 5 /nobreak > nul
echo  Startet... (%COUNTER%/60)
goto WAIT

:READY
echo  OK: Bereit!

:OPEN
echo.
echo ==========================================
echo  Rebuild fertig! YouTube funktioniert
echo  ab jetzt automatisch wieder.
echo  Browser: http://localhost:7502
echo ==========================================
echo.
start http://localhost:7502
pause
