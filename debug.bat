@echo off
title BookVoice-AI Debug
set OUTPUT=%USERPROFILE%\Desktop\bookvoice_debug.txt

echo BookVoice-AI Debug Output > %OUTPUT%
echo Datum: %date% %time% >> %OUTPUT%
echo. >> %OUTPUT%

echo [1] Docker Version >> %OUTPUT%
docker --version >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [2] Docker Container >> %OUTPUT%
docker ps -a >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [3] Container Logs TTS >> %OUTPUT%
docker logs bookvoice-tts --tail 30 >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [4] Container Logs Proxy >> %OUTPUT%
docker logs bookvoice-proxy --tail 20 >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [5] Dateien vorhanden >> %OUTPUT%
dir "%USERPROFILE%\BookVoice-AI" >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [6] Netzwerk Test Port 7500 >> %OUTPUT%
curl -s http://localhost:7500/health >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [7] Netzwerk Test Port 7502 >> %OUTPUT%
curl -s http://localhost:7502 >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo [8] compose.yaml Inhalt >> %OUTPUT%
type "%USERPROFILE%\BookVoice-AI\compose.yaml" >> %OUTPUT% 2>&1
echo. >> %OUTPUT%

echo Fertig! Debug-Datei gespeichert auf Desktop.
echo Bitte die Datei "bookvoice_debug.txt" vom Desktop schicken!
echo.
start %USERPROFILE%\Desktop\bookvoice_debug.txt
pause
