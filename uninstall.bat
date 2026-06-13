@echo off
title BookVoice-AI Deinstallation
color 0C

echo.
echo ==========================================
echo  BookVoice-AI - Deinstallation
echo ==========================================
echo.
echo WARNUNG: Alle Hoerbucher und Stimmen werden geloescht!
echo.
set /p CONFIRM=Wirklich deinstallieren? (j/n): 
if /i "%CONFIRM%" neq "j" exit /b 0

echo.
echo [1/3] Stoppe und loesche Container...
docker stop bookvoice-tts bookvoice-proxy bookvoice-web > nul 2>&1
docker rm bookvoice-tts bookvoice-proxy bookvoice-web > nul 2>&1
docker rmi bookvoice-ai-bookvoice-tts > nul 2>&1
docker volume rm bookvoice-tts-models bookvoice-hoerbuch bookvoice-transkriptionen bookvoice-archiv bookvoice-training bookvoice-musik > nul 2>&1
echo OK: Container geloescht!

echo.
echo [2/3] Loesche Dateien...
rmdir /s /q "%USERPROFILE%\BookVoice-AI" > nul 2>&1
echo OK: Dateien geloescht!

echo.
echo [3/3] Docker aufraeumen...
docker system prune -f > nul 2>&1
echo OK: Docker bereinigt!

echo.
echo ==========================================
echo  BookVoice-AI wurde deinstalliert!
echo ==========================================
echo.
pause
