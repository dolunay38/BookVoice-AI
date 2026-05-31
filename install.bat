@echo off
title BookVoice-AI Installer
color 0A

echo.
echo ==========================================
echo  BookVoice-AI - One Click Install v1.0
echo ==========================================
echo.

REM WSL2 pruefen
echo [1/6] Pruefe WSL2...
wsl --status > nul 2>&1
if %errorlevel% neq 0 (
    echo WSL2 nicht gefunden - installiere WSL2...
    echo Bitte warten...
    wsl --install
    echo.
    echo WSL2 wurde installiert!
    echo Bitte PC neu starten und install.bat erneut ausfuehren!
    pause
    exit /b 0
)
echo OK: WSL2 vorhanden!

REM Docker pruefen
echo.
echo [2/6] Pruefe Docker...
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo FEHLER: Docker nicht installiert!
    echo Bitte installieren: https://www.docker.com/products/docker-desktop
    start https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo OK: Docker gefunden!

REM Docker starten falls noetig
echo.
echo [3/6] Pruefe ob Docker laeuft...
docker ps > nul 2>&1
if %errorlevel% neq 0 (
    echo Docker laeuft nicht - starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Warte 30 Sekunden...
    timeout /t 30 /nobreak > nul
    docker ps > nul 2>&1
    if %errorlevel% neq 0 (
        echo FEHLER: Docker konnte nicht gestartet werden!
        echo Bitte Docker Desktop manuell starten und erneut versuchen.
        pause
        exit /b 1
    )
)
echo OK: Docker laeuft!

REM Ordner erstellen
echo.
echo [4/6] Erstelle Ordner...
set INSTALL_DIR=%USERPROFILE%\BookVoice-AI
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\HOERBUCH" mkdir "%INSTALL_DIR%\HOERBUCH"
if not exist "%INSTALL_DIR%\tts_models" mkdir "%INSTALL_DIR%\tts_models"
if not exist "%INSTALL_DIR%\musik" mkdir "%INSTALL_DIR%\musik"
echo OK: Ordner erstellt in %INSTALL_DIR%

REM Dateien kopieren
echo.
echo [5/6] Kopiere Dateien...
copy /Y "%~dp0compose.yaml" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0tts_server.py" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0Dockerfile.tts" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0ki_archiv_tts_web.html" "%INSTALL_DIR%\" > nul
copy /Y "%~dp0nginx-bookvoice.conf" "%INSTALL_DIR%\" > nul

if not exist "%INSTALL_DIR%\compose.yaml" (
    echo FEHLER: Dateien nicht gefunden!
    echo Bitte alle Dateien im gleichen Ordner wie install.bat haben!
    pause
    exit /b 1
)
echo OK: Dateien kopiert!

REM Container starten
echo.
echo [6/6] Starte BookVoice-AI...
echo Erster Start laedt ca. 2GB Modell - bitte warten!
echo.
cd /d "%INSTALL_DIR%"
docker compose down > nul 2>&1
docker compose up -d --build

if %errorlevel% neq 0 (
    echo FEHLER: Container konnten nicht gestartet werden!
    pause
    exit /b 1
)
echo OK: Container gestartet!

REM Warten bis bereit
echo.
echo Warte auf Server...
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
echo  BookVoice-AI ist bereit!
echo  Browser: http://localhost:7502
echo ==========================================
echo.
start http://localhost:7502
pause
