@echo off
title BookVoice-AI Start
color 0A

set INSTALL_DIR=%USERPROFILE%\BookVoice-AI

REM Installiert?
if not exist "%INSTALL_DIR%\tts_server.py" (
    echo.
    echo  BookVoice-AI ist nicht installiert.
    echo  Bitte zuerst install.bat ausfuehren.
    echo.
    pause
    exit /b 1
)

REM GPU-Modus erkennen
set COMPOSE_FILE=compose.yaml
if exist "%INSTALL_DIR%\compose.gpu.yaml" (
    nvidia-smi > nul 2>&1
    if %errorlevel% equ 0 set COMPOSE_FILE=compose.gpu.yaml
)

cd /d "%INSTALL_DIR%"

REM Laeuft schon?
docker ps --filter "name=bookvoice-tts" --filter "status=running" | findstr "bookvoice-tts" > nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  BookVoice-AI laeuft bereits.
    echo  Browser: http://localhost:7502
    echo.
    start http://localhost:7502
    pause
    exit /b 0
)

echo.
echo  Starte BookVoice-AI...
if "%COMPOSE_FILE%"=="compose.gpu.yaml" (
    echo  Modus: GPU
    docker compose -f compose.gpu.yaml up -d
) else (
    echo  Modus: CPU
    docker compose up -d
)

if %errorlevel% neq 0 (
    echo.
    echo  FEHLER beim Starten!
    echo  Bitte debug.bat ausfuehren.
    pause
    exit /b 1
)

echo.
echo  Warte auf Server...
set COUNTER=0
:WAIT
set /a COUNTER+=1
if %COUNTER% gtr 36 goto OPEN
curl -s http://localhost:7500/health > nul 2>&1
if %errorlevel% equ 0 goto READY
timeout /t 5 /nobreak > nul
echo  Warte... (%COUNTER%/36)
goto WAIT

:READY
echo  OK: BookVoice-AI bereit!

:OPEN
echo.
echo  Browser: http://localhost:7502
start http://localhost:7502
pause
