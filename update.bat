@echo off
REM ============================================================
REM BookVoice-AI — Update
REM Holt die neueste Version von GitHub und baut neu auf.
REM
REM CPU-User:  Doppelklick auf diese Datei
REM GPU-User:  setze unten USE_GPU=1
REM ============================================================

REM --- GPU? (0 = CPU Standard, 1 = lokale NVIDIA-GPU) ---
set USE_GPU=0

echo.
echo ============================================
echo   BookVoice-AI Update
echo ============================================
echo.

echo [1/3] Hole neueste Version von GitHub...
git pull
if errorlevel 1 (
    echo FEHLER: git pull fehlgeschlagen. Aenderungen vorher committen oder stashen.
    pause
    exit /b 1
)

echo.
echo [2/3] Baue Container neu auf (--build holt neue Pakete)...
if "%USE_GPU%"=="1" (
    echo    GPU-Modus: compose.gpu.yaml
    docker compose -f compose.gpu.yaml up -d --build
) else (
    echo    CPU-Modus: compose.yaml
    docker compose up -d --build
)

echo.
echo [3/3] Status:
docker ps --filter "name=bookvoice" --format "table {{.Names}}\t{{.Status}}"

echo.
echo ============================================
echo   Update fertig! Browser: http://localhost:7502
echo ============================================
echo.
echo Hinweis: Wenn neue Pakete dazukamen und etwas fehlt,
echo          fuehre einmalig einen sauberen Rebuild aus:
echo.
if "%USE_GPU%"=="1" (
    echo    docker compose -f compose.gpu.yaml build --no-cache
    echo    docker compose -f compose.gpu.yaml up -d
) else (
    echo    docker compose build --no-cache
    echo    docker compose up -d
)
echo.
pause
