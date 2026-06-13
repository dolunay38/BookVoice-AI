#!/bin/bash
# yt-dlp beim Start aktualisieren (YouTube aendert API haeufig)
echo "[BookVoice] Pruefe yt-dlp Update..."
yt-dlp -U 2>/dev/null || true
echo "[BookVoice] yt-dlp OK: $(yt-dlp --version)"

# Server starten
exec uvicorn tts_server:app --host 0.0.0.0 --port 7500
