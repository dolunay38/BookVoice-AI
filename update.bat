@echo off
title BookVoice-AI Update
color 0A

echo.
echo ==========================================
echo  BookVoice-AI - Auto Update
echo  github.com/dolunay38/BookVoice-AI
echo ==========================================
echo.

set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
set GITHUB=https://raw.githubusercontent.com/dolunay38/BookVoice-AI/main

REM Docker pruefen
echo [1/4] Pruefe Docker...
docker ps > nul 2>&1
if %errorlevel% neq 0 (
    echo Docker laeuft nicht - starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    timeout /t 30 /nobreak > nul
    docker ps > nul 2>&1
    if %errorlevel% neq 0 (
        echo FEHLER: Docker konnte nicht gestartet werden!
        pause
        exit /b 1
    )
)
echo OK: Docker laeuft!

REM Neue Dateien laden
echo.
echo [2/4] Lade neue Dateien von GitHub...
curl -s -o "%INSTALL_DIR%\compose.yaml" "%GITHUB%/compose.yaml"
curl -s -o "%INSTALL_DIR%\tts_server.py" "%GITHUB%/tts_server.py"
curl -s -o "%INSTALL_DIR%\ki_archiv_tts_web.html" "%GITHUB%/ki_archiv_tts_web.html"
curl -s -o "%INSTALL_DIR%\nginx-bookvoice.conf" "%GITHUB%/nginx-bookvoice.conf"
curl -s -o "%INSTALL_DIR%\Dockerfile.tts" "%GITHUB%/Dockerfile.tts"
echo OK: Dateien aktualisiert!

REM Container neu starten
echo.
echo [3/4] Starte Container neu...
cd /d "%INSTALL_DIR%"
docker compose down > nul 2>&1
docker compose up -d --build

if %errorlevel% neq 0 (
    echo FEHLER: Container konnten nicht gestartet werden!
    pause
    exit /b 1
)
echo OK: Container gestartet!

REM Warten
echo.
echo [4/4] Warte auf Server...
set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 60 goto DONE
curl -s http://localhost:7502 > nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 5 /nobreak > nul
    echo Warte... (%COUNTER%/60)
    goto WAIT
)

:DONE
echo.
echo ==========================================
echo  Update erfolgreich!
echo  Browser: http://localhost:7502
echo ==========================================
echo.
start http://localhost:7502
pause
