# Transformers Compatibility Fix (Colab)
try:
    import transformers.pytorch_utils as _pu
    import torch as _torch
    if not hasattr(_pu, 'isin_mps_friendly'):
        _pu.isin_mps_friendly = _torch.isin
except Exception:
    pass

import os, uuid, threading, torchaudio, torch, shutil, subprocess, re, tempfile
from faster_whisper import WhisperModel
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Konfiguration ──────────────────────────────────────────────
OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT", "/app/HOERBUCH"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPTION_DIR = Path("/app/TRANSKRIPTIONEN")
TRANSCRIPTION_DIR.mkdir(parents=True, exist_ok=True)
EINGABE_DIR = Path("/app/EINGABE")
EINGABE_DIR.mkdir(parents=True, exist_ok=True)
ARCHIV_DIR = Path("/app/ARCHIV")
ARCHIV_DIR.mkdir(parents=True, exist_ok=True)
# Dynamischer Modell-Pfad — funktioniert auf Docker und Colab
_possible_model_dirs = [
    Path("/app/tts_models/tts_models--multilingual--multi-dataset--xtts_v2"),
    Path("/root/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2"),
    Path("/content/tts_models/tts_models--multilingual--multi-dataset--xtts_v2"),
]
MODEL_DIR = next((p for p in _possible_model_dirs if p.exists()), _possible_model_dirs[0])

_possible_voice_dirs = [
    Path("/app/tts_models"),
    Path("/content/tts_models"),
]
VOICE_DIR = next((p for p in _possible_voice_dirs if p.exists()), _possible_voice_dirs[0])

DEFAULT_LANG = os.getenv("TTS_LANG", "tr")

_possible_stimme = [Path("/app/tts_models/stimme.wav"), Path("/content/tts_models/stimme.wav")]
DEFAULT_SPEAKER_WAV = str(next((p for p in _possible_stimme if p.exists()), _possible_stimme[0]))

# CPU/GPU Auto-Detect
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Device: {DEVICE.upper()}")

AUDIO_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".weba", ".opus"}
VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}
IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".heic"}
EBOOK_FORMATS = {".epub", ".mobi", ".azw3", ".fb2", ".lrf", ".txt", ".html", ".rtf", ".docx", ".pdf"}
ALL_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS | IMAGE_FORMATS | EBOOK_FORMATS

jobs = {}
jobs_lock = threading.Lock()
tts_engine = None
_cached_latents = {}

# ── Modell beim Start prüfen und herunterladen ─────────────────
def ensure_model():
    """Stellt sicher dass XTTS-v2 Modell vorhanden ist"""
    if not MODEL_DIR.exists() or not (MODEL_DIR / "config.json").exists():
        print("🔄 XTTS-v2 Modell wird heruntergeladen (~1.8 GB)...")
        print("   Bitte warten — dies dauert beim ersten Start einige Minuten!")
        try:
            from TTS.api import TTS as TTSDownloader
            TTSDownloader("tts_models/multilingual/multi-dataset/xtts_v2")
            print("✅ Modell erfolgreich heruntergeladen!")
        except Exception as e:
            print(f"❌ Modell-Download fehlgeschlagen: {e}")
    else:
        print("✅ XTTS-v2 Modell bereits vorhanden!")

# ── Standard-Stimme erstellen falls keine vorhanden ───────────
def ensure_default_voice():
    """Erstellt eine Standard-Stimme falls keine vorhanden"""
    voice_path = Path(DEFAULT_SPEAKER_WAV)
    if not voice_path.exists():
        print("🎙️ Erstelle Standard-Stimme...")
        try:
            import numpy as np
            sample_rate = 22050
            duration = 3
            t = np.linspace(0, duration, int(sample_rate * duration))
            # Einfacher Sinuston als Platzhalter
            audio = np.sin(2 * np.pi * 200 * t) * 0.3
            audio_tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
            torchaudio.save(str(voice_path), audio_tensor, sample_rate)
            print("✅ Standard-Stimme erstellt!")
            print("⚠️  Bitte eigene Stimme hochladen für beste Qualität!")
        except Exception as e:
            print(f"⚠️  Standard-Stimme konnte nicht erstellt werden: {e}")
    else:
        print("✅ Stimme vorhanden!")

# Beim Start ausführen
ensure_model()
ensure_default_voice()

def load_model():
    global tts_engine
    if tts_engine is not None:
        return
    print("🔊 Lade XTTS-v2 Modell...")
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    config = XttsConfig()
    config.load_json(str(MODEL_DIR / "config.json"))
    tts_engine = Xtts.init_from_config(config)
    tts_engine.load_checkpoint(config, checkpoint_dir=str(MODEL_DIR), eval=True)
    if DEVICE == "cuda":
        tts_engine = tts_engine.cuda()
    print(f"✅ XTTS-v2 bereit! [{DEVICE.upper()}]")

app = FastAPI(title="BookVoice-AI Server", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_credentials=False,
)

from fastapi import Request
from fastapi.responses import Response

@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    # Preflight OPTIONS direkt beantworten
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

class TTSRequest(BaseModel):
    text: str
    language: str = DEFAULT_LANG
    speaker_wav: str = DEFAULT_SPEAKER_WAV
    filename: str = ""
    temperature: float = 0.5
    repetition_penalty: float = 5.0
    top_k: int = 30
    speed: float = 1.0

class ChapterRequest(BaseModel):
    chapters: list[str]
    language: str = DEFAULT_LANG
    speaker_wav: str = DEFAULT_SPEAKER_WAV
    book_name: str = "hoerbuch"
    output_format: str = "mp3"
    temperature: float = 0.5
    repetition_penalty: float = 5.0
    top_k: int = 30
    speed: float = 1.0
    cover_path: str = ""
    use_emotion_tags: bool = False
    auto_tag: bool = False  # Optionales Cover-Bild  # mp3, wav, m4b

class EbookRequest(BaseModel):
    language: str = DEFAULT_LANG
    speaker_wav: str = DEFAULT_SPEAKER_WAV
    book_name: str = "hoerbuch"
    output_format: str = "m4b"

# ── SML Tag Parser ─────────────────────────────────────────────
def parse_sml_tags(text: str) -> list[dict]:
    """SML Tags parsen: [break], [pause], [pause:N]"""
    segments = []
    pattern = r'\[break\]|\[pause\]|\[pause:(\d+(?:\.\d+)?)\]'
    last = 0
    for m in re.finditer(pattern, text):
        if m.start() > last:
            segments.append({"type": "text", "content": text[last:m.start()].strip()})
        if m.group() == "[break]":
            segments.append({"type": "pause", "duration": 0.4})
        elif m.group() == "[pause]":
            segments.append({"type": "pause", "duration": 1.2})
        else:
            segments.append({"type": "pause", "duration": float(m.group(1))})
        last = m.end()
    if last < len(text):
        segments.append({"type": "text", "content": text[last:].strip()})
    return [s for s in segments if s.get("content", "x")]

# ── Text-Splitting ─────────────────────────────────────────────
def clean_extracted_text(text):
    stopwords = {'ve', 'de', 'da', 'ki', 'bu', 'bir', 'en', 'ya', 'mi'}
    import re
    text = re.sub(r'-[ \t]*\n[ \t]*', '', text)
    words = text.split()
    cleaned = []
    i = 0
    while i < len(words):
        w = words[i]
        if (len(w) <= 2 and w.isalpha() and w.lower() not in stopwords
                and i + 1 < len(words) and len(words[i+1]) >= 3):
            cleaned.append(w + words[i+1])
            i += 2
        else:
            cleaned.append(w)
            i += 1
    text = ' '.join(cleaned)
    text = re.sub(r'  +', ' ', text)
    return text.strip()
TAG_PRESETS = {
    'dramatic':   {'temperature': 0.85, 'repetition_penalty': 3.0, 'top_k': 50, 'speed': 0.95},
    'whispers':   {'temperature': 0.2,  'repetition_penalty': 8.0, 'top_k': 10, 'speed': 0.75},
    'sighs':      {'temperature': 0.5,  'repetition_penalty': 5.0, 'top_k': 30, 'speed': 0.8,  'silence': 0.4},
    'laughs':     {'temperature': 0.9,  'repetition_penalty': 2.5, 'top_k': 55, 'speed': 1.2},
    'sad':        {'temperature': 0.7,  'repetition_penalty': 3.5, 'top_k': 40, 'speed': 0.75},
    'happy':      {'temperature': 0.8,  'repetition_penalty': 3.0, 'top_k': 45, 'speed': 1.15},
    'pause':      {'silence': 0.8},
    'normal':     {'temperature': 0.5,  'repetition_penalty': 5.0, 'top_k': 30, 'speed': 1.0},
}

def auto_tag_text(text: str) -> str:
    """Regel-basierte Emotions-Tags automatisch erkennen und einfügen"""
    import re
    lines = text.split('\n')
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            result.append('')
            continue
        # Bereits getaggt
        if line.startswith('['):
            result.append(line)
            continue
        # Ausrufezeichen → dramatic
        if '!' in line and len(line) > 10:
            result.append(f'[dramatic] {line}')
        # Drei Punkte am Ende → sighs
        elif line.endswith('...') or line.endswith('…'):
            result.append(f'[sighs] {line}')
        # Sehr kurzer Satz → whispers
        elif len(line) < 30 and line.endswith('.'):
            result.append(f'[whispers] {line}')
        # Fragezeichen → normal
        elif line.endswith('?'):
            result.append(line)
        # Anführungszeichen → leicht dramatisch
        elif line.startswith('"') or line.startswith('"'):
            result.append(f'[dramatic] {line}')
        else:
            result.append(line)
    return '\n'.join(result)

def parse_emotion_chunks(text: str, base_req) -> list[dict]:
    """Text mit Emotion-Tags in Chunks mit Preset-Parametern aufteilen"""
    import re
    TAGS = list(TAG_PRESETS.keys())
    pattern = r'\[(' + '|'.join(TAGS) + r')\]'
    parts = re.split(pattern, text)
    
    chunks = []
    current_tag = 'normal'
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part in TAG_PRESETS:
            current_tag = part
        else:
            preset = TAG_PRESETS.get(current_tag, TAG_PRESETS['normal'])
            if 'silence' in preset:
                chunks.append({'type': 'silence', 'duration': preset['silence']})
            if part:
                chunks.append({
                    'type': 'speech',
                    'text': part,
                    'temperature': preset.get('temperature', base_req.temperature),
                    'repetition_penalty': preset.get('repetition_penalty', base_req.repetition_penalty),
                    'top_k': preset.get('top_k', base_req.top_k),
                    'speed': preset.get('speed', base_req.speed),
                })
            current_tag = 'normal'
    
    return chunks

def split_text(text: str, max_chars: int = 220) -> list[str]:
    sentences = re.split(r'(?<=[.!?،؟\n])\s+', text.strip())
    chunks = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > max_chars:
            parts = re.split(r'(?<=[,،;:])\s+', s)
            for p in parts:
                if len(current) + len(p) < max_chars:
                    current += " " + p
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    current = p
        elif len(current) + len(s) < max_chars:
            current += " " + s
        else:
            if current.strip():
                chunks.append(current.strip())
            current = s
    if current.strip():
        chunks.append(current.strip())
    # Sicherstellen dass jeder Chunk mit Satzzeichen endet (verhindert Halluzination)
    result = []
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) > 2:
            if chunk[-1] not in '.!?،؟…':
                chunk = chunk + '.'
            result.append(chunk)
    return result

# ── Audio Merge ────────────────────────────────────────────────
def make_silence(duration: float, out_path: Path, sample_rate: int = 24000):
    samples = int(duration * sample_rate)
    silence = torch.zeros(1, samples)
    torchaudio.save(str(out_path), silence, sample_rate)

def merge_wav_files(input_files: list[Path], output_file: Path):
    if len(input_files) == 1:
        shutil.copy(input_files[0], output_file)
        return
    # Kurze Stille (300ms) zwischen Chunks einfügen — verhindert Knackser
    silence_path = output_file.parent / f"_silence_{uuid.uuid4().hex[:6]}.wav"
    make_silence(0.3, silence_path)
    list_file = output_file.parent / f"_list_{uuid.uuid4().hex[:6]}.txt"
    with open(list_file, "w") as f:
        for i, wav in enumerate(input_files):
            f.write(f"file '{wav.resolve()}'\n")
            if i < len(input_files) - 1:
                f.write(f"file '{silence_path.resolve()}'\n")
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-af", "aresample=24000,dynaudnorm=f=150:g=15",
        str(output_file), "-y"
    ], capture_output=True)
    list_file.unlink(missing_ok=True)
    silence_path.unlink(missing_ok=True)

def merge_to_mp3(input_files: list[Path], output_file: Path, cover_path: Path = None):
    if not input_files:
        return
    list_file = output_file.parent / f"_list_{uuid.uuid4().hex[:6]}.txt"
    with open(list_file, "w") as f:
        for wav in input_files:
            f.write(f"file '{wav.resolve()}'\n")

    if cover_path and cover_path.exists():
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-i", str(cover_path),
            "-map", "0:a", "-map", "1:v",
            "-af", "dynaudnorm=f=150:g=15",
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            "-codec:v", "copy",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            str(output_file), "-y"
        ], capture_output=True)
    else:
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-af", "dynaudnorm=f=150:g=15",
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            str(output_file), "-y"
        ], capture_output=True)
    list_file.unlink(missing_ok=True)

def merge_to_m4b(input_files: list[Path], output_file: Path, title: str = "Hörbuch", cover_path: Path = None):
    if not input_files:
        return
    list_file = output_file.parent / f"_list_{uuid.uuid4().hex[:6]}.txt"
    with open(list_file, "w") as f:
        for wav in input_files:
            f.write(f"file '{wav.resolve()}'\n")

    if cover_path and cover_path.exists():
        # M4B mit Cover einbetten
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-i", str(cover_path),
            "-map", "0:a",
            "-map", "1:v",
            "-af", "dynaudnorm=f=150:g=15",
            "-c:a", "aac", "-b:a", "64k",
            "-c:v", "copy",
            "-disposition:v", "attached_pic",
            "-metadata", f"title={title}",
            "-metadata", "genre=Audiobook",
            str(output_file), "-y"
        ], capture_output=True)
    else:
        # M4B ohne Cover
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-af", "dynaudnorm=f=150:g=15",
            "-c:a", "aac", "-b:a", "64k",
            "-metadata", f"title={title}",
            "-metadata", "genre=Audiobook",
            str(output_file), "-y"
        ], capture_output=True)
    list_file.unlink(missing_ok=True)

# ── Konvertierung ──────────────────────────────────────────────
def convert_to_wav(input_path: Path, output_path: Path):
    result = subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "22050", "-ac", "1",
        str(output_path), "-y"
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg Fehler: {result.stderr}")

def extract_text_from_image(image_path: Path, lang: str = "tur") -> str:
    import pytesseract
    from PIL import Image
    img = Image.open(image_path)
    lang_map = {"tr": "tur", "de": "deu", "en": "eng", "ar": "ara"}
    tess_lang = lang_map.get(lang, "tur")
    return pytesseract.image_to_string(img, lang=tess_lang)

def extract_text_from_ebook(file_path: Path) -> list[str]:
    """EPUB/MOBI/PDF → Kapitel-Liste"""
    suffix = file_path.suffix.lower()
    chapters = []
    if suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        # Kapitel erkennen
        parts = re.split(r'\n\s*(?:BÖLÜM|CHAPTER|KAPITEL|Bölüm|Chapter)\s*\d+', text)
        chapters = [p.strip() for p in parts if len(p.strip()) > 100]
        if not chapters:
            chapters = [text]
    elif suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(file_path))
            text = " ".join(page.extract_text() or "" for page in reader.pages)
            text = clean_extracted_text(text)
            chapters = [text]
        except:
            chapters = ["PDF konnte nicht gelesen werden"]
    else:
        # Calibre für EPUB/MOBI/AZW3
        txt_path = file_path.parent / f"{file_path.stem}_converted.txt"
        result = subprocess.run([
            "ebook-convert", str(file_path), str(txt_path)
        ], capture_output=True, text=True)
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
            txt_path.unlink()
            parts = re.split(r'\n\s*(?:BÖLÜM|CHAPTER|KAPITEL|Bölüm|Chapter)\s*\d+', text)
            chapters = [p.strip() for p in parts if len(p.strip()) > 100]
            if not chapters:
                chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
                chapters = chunks
        else:
            chapters = ["Datei konnte nicht konvertiert werden"]
    return chapters

# ── Kern-Synthese ──────────────────────────────────────────────
def get_latents(speaker_wav: str):
    """Conditioning Latents cachen für bessere Performance"""
    if speaker_wav in _cached_latents:
        return _cached_latents[speaker_wav]
    load_model()
    wav_path = Path(speaker_wav)
    if wav_path.suffix.lower() != ".wav":
        tmp = wav_path.with_suffix(".tmp.wav")
        convert_to_wav(wav_path, tmp)
        wav_path = tmp
    latents = tts_engine.get_conditioning_latents(audio_path=[str(wav_path)])
    _cached_latents[speaker_wav] = latents
    return latents

def synthesize_chunk(text: str, language: str, speaker_wav: str, out_path: Path,
                     temperature: float = 0.5, repetition_penalty: float = 5.0, top_k: int = 30, speed: float = 1.0):
    load_model()
    gpt_cond_latent, speaker_embedding = get_latents(speaker_wav)
    out = tts_engine.inference(
        text=text,
        language=language,
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
        temperature=temperature,
        length_penalty=1.0,
        repetition_penalty=repetition_penalty,
        top_k=top_k,
        top_p=0.85,
        speed=speed,
        enable_text_splitting=False
    )
    torchaudio.save(str(out_path), src=torch.tensor(out["wav"]).unsqueeze(0), sample_rate=24000)

def synthesize(text: str, language: str, speaker_wav: str, out_path: Path,
               temperature: float = 0.5, repetition_penalty: float = 5.0, top_k: int = 30, speed: float = 1.0):
    """Text mit SML Tags und Auto-Split verarbeiten"""
    segments = parse_sml_tags(text)
    tmp_dir = out_path.parent / f"_tmp_{uuid.uuid4().hex[:6]}"
    tmp_dir.mkdir(exist_ok=True)
    audio_files = []
    try:
        for i, seg in enumerate(segments):
            if seg["type"] == "pause":
                sil_path = tmp_dir / f"silence_{i:04d}.wav"
                make_silence(seg["duration"], sil_path)
                audio_files.append(sil_path)
            else:
                chunks = split_text(seg["content"])
                for j, chunk in enumerate(chunks):
                    chunk_path = tmp_dir / f"chunk_{i:04d}_{j:04d}.wav"
                    synthesize_chunk(chunk, language, speaker_wav, chunk_path,
                                     temperature, repetition_penalty, top_k, speed)
                    audio_files.append(chunk_path)
        merge_wav_files(audio_files, out_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# ── API Endpoints ──────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "BookVoice-AI Server",
        "version": "1.0",
        "model": "XTTS-v2",
        "device": DEVICE,
        "status": "bereit",
        "sprachen": ["tr", "de", "en", "ar"]
    }

@app.get("/health")
def health():
    info = {"status": "ok", "device": DEVICE, "model_loaded": tts_engine is not None}
    if torch.cuda.is_available():
        try:
            info["gpu_util"] = torch.cuda.utilization()
            mem = torch.cuda.mem_get_info()
            used = (mem[1] - mem[0]) / 1024**3
            total = mem[1] / 1024**3
            info["gpu_mem"] = f"{used:.1f}/{total:.0f}GB"
        except:
            pass
    return info

@app.post("/tts/generate")
def generate(req: TTSRequest):
    try:
        filename = req.filename or f"tts_{uuid.uuid4().hex[:8]}.wav"
        if not filename.endswith(".wav"):
            filename += ".wav"
        out_path = OUTPUT_DIR / filename
        synthesize(req.text, req.language, req.speaker_wav, out_path,
                   req.temperature, req.repetition_penalty, req.top_k, getattr(req, 'speed', 1.0))
        return {"status": "ok", "datei": filename, "groesse_kb": round(out_path.stat().st_size / 1024, 1)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts/book")
def generate_book(req: ChapterRequest, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"status": "running", "total": len(req.chapters), "done": 0, "files": [], "errors": [], "output": ""}
    background_tasks.add_task(_process_book, job_id, req)
    return {"job_id": job_id, "status": "gestartet", "kapitel_anzahl": len(req.chapters)}

@app.post("/tts/ebook")
async def process_ebook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = DEFAULT_LANG,
    speaker_wav: str = DEFAULT_SPEAKER_WAV,
    book_name: str = "hoerbuch",
    output_format: str = "m4b"
):
    """eBook direkt hochladen und konvertieren"""
    suffix = Path(file.filename).suffix.lower()
    tmp_path = OUTPUT_DIR / f"_upload_{uuid.uuid4().hex[:8]}{suffix}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    chapters = extract_text_from_ebook(tmp_path)
    tmp_path.unlink(missing_ok=True)

    req = ChapterRequest(
        chapters=chapters,
        language=language,
        speaker_wav=speaker_wav,
        book_name=book_name,
        output_format=output_format
    )
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"status": "running", "total": len(chapters), "done": 0, "files": [], "errors": [], "output": ""}
    background_tasks.add_task(_process_book, job_id, req)
    return {"job_id": job_id, "status": "gestartet", "kapitel_anzahl": len(chapters), "buch": book_name}

@app.post("/tts/image-to-speech")
async def image_to_speech(
    file: UploadFile = File(...),
    language: str = DEFAULT_LANG,
    speaker_wav: str = DEFAULT_SPEAKER_WAV
):
    """Foto von Buchseite → Audio"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail="Nur Bilder erlaubt (JPG, PNG etc.)")
    tmp_path = OUTPUT_DIR / f"_img_{uuid.uuid4().hex[:8]}{suffix}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        text = extract_text_from_image(tmp_path, language)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Kein Text im Bild erkannt")
        filename = f"ocr_{uuid.uuid4().hex[:8]}.wav"
        out_path = OUTPUT_DIR / filename
        synthesize(text, language, speaker_wav, out_path)
        return {"status": "ok", "text": text[:200], "datei": filename, "groesse_kb": round(out_path.stat().st_size / 1024, 1)}
    finally:
        tmp_path.unlink(missing_ok=True)

@app.post("/tts/cancel/{job_id}")
def cancel_job(job_id: str):
    """Laufenden Job abbrechen"""
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'abgebrochen'
        active_jobs[job_id]['cancelled'] = True
        return {"status": "ok", "message": f"Job {job_id} abgebrochen"}
    return {"status": "not_found", "message": "Job nicht gefunden"}

@app.get("/tts/book/status/{job_id}")
def book_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job

@app.get("/tts/files")
def list_files():
    import datetime
    files = []
    for ext in ["*.wav", "*.mp3", "*.m4b"]:
        for f in OUTPUT_DIR.rglob(ext):
            if not f.name.startswith("_"):
                files.append({
                    "name": f.name,
                    "groesse_mb": round(f.stat().st_size / 1024 / 1024, 2),
                    "datum": f.stat().st_mtime,
                    "datum_str": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
                })
    # Neueste zuerst
    files.sort(key=lambda x: x["datum"], reverse=True)
    return {"dateien": files, "anzahl": len(files)}

@app.get("/tts/download/{filename}")
def download(filename: str):
    for f in OUTPUT_DIR.rglob(filename):
        if filename.endswith(".mp3"):
            media_type = "audio/mpeg"
        elif filename.endswith(".m4b"):
            media_type = "audio/mp4"
        else:
            media_type = "audio/wav"
        return FileResponse(f, media_type=media_type, filename=filename)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden")

@app.delete("/tts/files/{filename}")
def delete_file(filename: str):
    for f in OUTPUT_DIR.rglob(filename):
        f.unlink()
        return {"status": "ok", "geloescht": filename}
    raise HTTPException(status_code=404, detail="Datei nicht gefunden")

@app.post("/tts/upload-cover")
async def upload_cover(file: UploadFile = File(...), book_name: str = "hoerbuch"):
    """Buchcover hochladen"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Nur JPG/PNG/WEBP erlaubt")
    cover_dir = OUTPUT_DIR / book_name
    cover_dir.mkdir(parents=True, exist_ok=True)
    cover_path = cover_dir / f"cover{suffix}"
    with open(cover_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "cover_path": str(cover_path), "datei": f"cover{suffix}"}


async def upload_voice(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (AUDIO_FORMATS | VIDEO_FORMATS):
        raise HTTPException(status_code=400, detail="Nur Audio/Video erlaubt")
    save_path = VOICE_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    if suffix != ".wav":
        wav_path = save_path.with_suffix(".wav")
        convert_to_wav(save_path, wav_path)
        save_path.unlink()
        save_path = wav_path
    if save_path in _cached_latents:
        del _cached_latents[str(save_path)]
    return {"status": "ok", "datei": save_path.name}

@app.post("/tts/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """MP3/M4B von Colab GPU empfangen und auf Server speichern"""
    suffix = Path(file.filename).suffix.lower()
    save_path = OUTPUT_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size_kb = save_path.stat().st_size // 1024
    return {"status": "ok", "datei": file.filename, "groesse_kb": size_kb}

@app.post("/admin/colab-url")
async def set_colab_url(url: str):
    """Colab URL vom Notebook empfangen und speichern"""
    with open("/tmp/colab_url.txt", "w") as f:
        f.write(url)
    return {"status": "ok", "url": url}

@app.get("/admin/colab-url")
def get_colab_url():
    """Gespeicherte Colab URL abrufen"""
    try:
        with open("/tmp/colab_url.txt", "r") as f:
            url = f.read().strip()
        return {"status": "ok", "url": url}
    except:
        return {"status": "empty", "url": ""}



@app.post("/tts/convert-to-text")
async def convert_to_text(file: UploadFile = File(...)):
    """Alle Dokument-Formate zu Text konvertieren"""
    suffix = Path(file.filename).suffix.lower()
    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        text = ""
        
        # ── TXT / Markdown / CSV ──
        if suffix in {".txt", ".md", ".csv", ".rtf"}:
            text = tmp_path.read_text(encoding="utf-8", errors="ignore")
        
        # ── PDF ──
        elif suffix == ".pdf":
            try:
                import PyPDF2
                with open(tmp_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: text += t + "\n"
                text = clean_extracted_text(text)
            except:
                pass
            if not text.strip():
                txt_path = tmp_path.with_suffix(".txt")
                subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
                if txt_path.exists():
                    text = txt_path.read_text(encoding="utf-8", errors="ignore")
                    txt_path.unlink(missing_ok=True)
        
        # ── WORD (docx, doc, odt) ──
        elif suffix in {".docx", ".odt"}:
            try:
                from docx import Document
                doc = Document(str(tmp_path))
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except:
                txt_path = tmp_path.with_suffix(".txt")
                subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
                if txt_path.exists():
                    text = txt_path.read_text(encoding="utf-8", errors="ignore")
                    txt_path.unlink(missing_ok=True)

        elif suffix == ".doc":
            # .doc via LibreOffice → docx → python-docx
            try:
                out_dir = Path(tempfile.mkdtemp())
                result = subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "docx", 
                     "--outdir", str(out_dir), str(tmp_path)],
                    capture_output=True, timeout=30
                )
                docx_path = out_dir / (tmp_path.stem + ".docx")
                if docx_path.exists():
                    from docx import Document
                    doc = Document(str(docx_path))
                    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    docx_path.unlink(missing_ok=True)
                out_dir.rmdir()
            except:
                pass
            if not text.strip():
                try:
                    result = subprocess.run(["antiword", str(tmp_path)], capture_output=True, text=True)
                    if result.returncode == 0:
                        text = result.stdout
                except:
                    pass
            if not text.strip():
                txt_path = tmp_path.with_suffix(".txt")
                subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
                if txt_path.exists():
                    text = txt_path.read_text(encoding="utf-8", errors="ignore")
                    txt_path.unlink(missing_ok=True)
        
        # ── PowerPoint (pptx, ppt) ──
        elif suffix in {".pptx", ".ppt"}:
            try:
                from pptx import Presentation
                prs = Presentation(str(tmp_path))
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            text += shape.text + "\n"
            except:
                txt_path = tmp_path.with_suffix(".txt")
                subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
                if txt_path.exists():
                    text = txt_path.read_text(encoding="utf-8", errors="ignore")
                    txt_path.unlink(missing_ok=True)
        
        # ── Excel (xlsx, xls) ──
        elif suffix in {".xlsx", ".xls"}:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(str(tmp_path), read_only=True, data_only=True)
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        row_text = " | ".join([str(c) for c in row if c is not None])
                        if row_text.strip():
                            text += row_text + "\n"
            except:
                try:
                    import xlrd
                    wb = xlrd.open_workbook(str(tmp_path))
                    for sheet in wb.sheets():
                        for row in range(sheet.nrows):
                            text += " | ".join([str(sheet.cell_value(row, col)) for col in range(sheet.ncols)]) + "\n"
                except:
                    pass
        
        # ── E-Books (epub, mobi, azw3, fb2) ──
        elif suffix in {".epub", ".mobi", ".azw3", ".fb2", ".lrf"}:
            txt_path = tmp_path.with_suffix(".txt")
            subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8", errors="ignore")
                txt_path.unlink(missing_ok=True)
        
        # ── HTML / XML ──
        elif suffix in {".html", ".htm", ".xml"}:
            try:
                from html.parser import HTMLParser
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.parts = []
                    def handle_data(self, data):
                        if data.strip():
                            self.parts.append(data.strip())
                parser = TextExtractor()
                parser.feed(tmp_path.read_text(encoding="utf-8", errors="ignore"))
                text = "\n".join(parser.parts)
            except:
                text = tmp_path.read_text(encoding="utf-8", errors="ignore")
        
        # ── Bilder (OCR) ──
        elif suffix in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"}:
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(str(tmp_path))
                text = pytesseract.image_to_string(img, lang="tur+deu+eng")
            except:
                raise HTTPException(status_code=400, detail="OCR fehlgeschlagen — Tesseract nicht verfügbar")
        
        # ── Unbekanntes Format — Calibre Fallback ──
        else:
            txt_path = tmp_path.with_suffix(".txt")
            subprocess.run(["ebook-convert", str(tmp_path), str(txt_path)], capture_output=True)
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8", errors="ignore")
                txt_path.unlink(missing_ok=True)
            
        if not text.strip():
            raise HTTPException(status_code=400, detail=f"Text konnte nicht extrahiert werden! Format: {suffix}")
            
        return {
            "status": "ok",
            "text": text.strip(),
            "zeichen": len(text.strip()),
            "datei": file.filename
        }
        
    finally:
        tmp_path.unlink(missing_ok=True)


async def upload_cover(file: UploadFile = File(...), book_name: str = "hoerbuch"):
    """Buchcover hochladen"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Nur JPG/PNG/WEBP erlaubt")
    cover_dir = OUTPUT_DIR / book_name
    cover_dir.mkdir(parents=True, exist_ok=True)
    cover_path = cover_dir / f"cover{suffix}"
    with open(cover_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "cover_path": str(cover_path), "datei": f"cover{suffix}"}


@app.post("/tts/upload-voice")
async def upload_voice(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (AUDIO_FORMATS | VIDEO_FORMATS):
        raise HTTPException(status_code=400, detail="Nur Audio/Video erlaubt")
    save_path = VOICE_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    if suffix != ".wav":
        wav_path = save_path.with_suffix(".wav")
        convert_to_wav(save_path, wav_path)
        save_path.unlink()
        save_path = wav_path
    if save_path in _cached_latents:
        del _cached_latents[str(save_path)]
    return {"status": "ok", "datei": save_path.name}

@app.get("/tts/voices")
def list_voices():
    voices = []
    for ext in ["*.wav", "*.mp3"]:
        for f in VOICE_DIR.glob(ext):
            if not f.name.startswith("tts_models") and not f.name.startswith("_"):
                voices.append({"name": f.name, "groesse_kb": round(f.stat().st_size / 1024, 1)})
    return {"stimmen": voices}

@app.get("/tts/voices/{filename}")
def get_voice(filename: str):
    """Einzelne Stimmdatei herunterladen"""
    path = VOICE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stimme nicht gefunden")
    return FileResponse(str(path), media_type="audio/wav", filename=filename)

@app.delete("/tts/voices/{filename}")
def delete_voice(filename: str):
    if filename == "stimme.wav":
        raise HTTPException(status_code=400, detail="Standard-Stimme kann nicht gelöscht werden")
    path = VOICE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    path.unlink()
    if str(path) in _cached_latents:
        del _cached_latents[str(path)]
    return {"status": "ok", "geloescht": filename}

MUSIK_DIR = Path("/app/musik")
MUSIK_DIR.mkdir(parents=True, exist_ok=True)

COVER_DIR = Path("/app/covers")
COVER_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/tts/covers")
def list_covers():
    """Cover-Bibliothek auflisten"""
    files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for f in sorted(COVER_DIR.glob(ext)):
            files.append({"name": f.name, "groesse_kb": round(f.stat().st_size/1024, 1)})
    return {"covers": files, "anzahl": len(files)}

@app.post("/tts/upload-cover-library")
async def upload_cover_library(file: UploadFile = File(...)):
    """Cover in Bibliothek hochladen"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Nur JPG/PNG/WEBP erlaubt")
    save_path = COVER_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "datei": file.filename}

@app.get("/tts/covers/{filename}")
def get_cover(filename: str):
    """Cover-Bild anzeigen"""
    path = COVER_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Cover nicht gefunden")
    return FileResponse(str(path))


    path = COVER_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Cover nicht gefunden")
    path.unlink()
    return {"status": "ok", "geloescht": filename}

@app.post("/tts/add-cover-to-file")
async def add_cover_to_file(audio_file: str, cover_file: str):
    """Cover nachträglich zu einer Audio-Datei hinzufügen"""
    # Audio suchen
    audio_path = None
    for f in OUTPUT_DIR.rglob(audio_file):
        audio_path = f
        break
    if not audio_path:
        raise HTTPException(status_code=404, detail=f"Audio nicht gefunden: {audio_file}")

    # Cover suchen (erst in Bibliothek, dann in Buch-Ordner)
    cover_path = COVER_DIR / cover_file
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail=f"Cover nicht gefunden: {cover_file}")

    suffix = audio_path.suffix.lower()
    out_path = audio_path.parent / f"{audio_path.stem}_cover{suffix}"

    if suffix == ".mp3":
        result = subprocess.run([
            "ffmpeg", "-i", str(audio_path), "-i", str(cover_path),
            "-map", "0:a", "-map", "1:v",
            "-codec:a", "copy", "-codec:v", "copy",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            str(out_path), "-y"
        ], capture_output=True)
    elif suffix == ".m4b":
        result = subprocess.run([
            "ffmpeg", "-i", str(audio_path), "-i", str(cover_path),
            "-map", "0:a", "-map", "1:v",
            "-codec:a", "copy", "-codec:v", "copy",
            "-disposition:v", "attached_pic",
            str(out_path), "-y"
        ], capture_output=True)
    else:
        raise HTTPException(status_code=400, detail="Nur MP3 und M4B unterstützt")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Fehler: {result.stderr.decode()}")

    return {
        "status": "ok",
        "datei": out_path.name,
        "groesse_mb": round(out_path.stat().st_size/1024/1024, 2)
    }


class MixRequest(BaseModel):
    audio_file: str
    musik_file: str
    musik_volume: float = 0.15  # 0.0 = kein Musik, 1.0 = volle Lautstärke
    output_name: str = ""

@app.get("/tts/musik")
def list_musik():
    """Verfügbare Hintergrundmusik auflisten"""
    files = []
    for ext in ["*.mp3", "*.wav", "*.m4a", "*.ogg"]:
        for f in sorted(MUSIK_DIR.glob(ext)):
            files.append({"name": f.name, "groesse_mb": round(f.stat().st_size/1024/1024, 2)})
    return {"musik": files, "anzahl": len(files)}

@app.post("/tts/upload-musik")
async def upload_musik(file: UploadFile = File(...)):
    """Hintergrundmusik hochladen"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in AUDIO_FORMATS:
        raise HTTPException(status_code=400, detail="Nur Audio-Dateien erlaubt")
    save_path = MUSIK_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "datei": file.filename}

@app.post("/tts/mix-musik")
def mix_musik(req: MixRequest):
    """Hörbuch mit Hintergrundmusik mischen"""
    audio_path = None
    for f in OUTPUT_DIR.rglob(req.audio_file):
        audio_path = f
        break
    if not audio_path:
        raise HTTPException(status_code=404, detail=f"Audio-Datei nicht gefunden: {req.audio_file}")

    musik_path = MUSIK_DIR / req.musik_file
    if not musik_path.exists():
        raise HTTPException(status_code=404, detail=f"Musik-Datei nicht gefunden: {req.musik_file}")

    output_name = req.output_name or f"{audio_path.stem}_mit_musik.mp3"
    output_path = audio_path.parent / output_name

    # ffmpeg: Musik loopen, Lautstärke anpassen, mischen
    result = subprocess.run([
        "ffmpeg",
        "-i", str(audio_path),
        "-stream_loop", "-1",  # Musik endlos loopen
        "-i", str(musik_path),
        "-filter_complex",
        f"[0:a]volume=1.0[speech];[1:a]volume={req.musik_volume}[music];[speech][music]amix=inputs=2:duration=first:dropout_transition=3[out]",
        "-map", "[out]",
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        str(output_path), "-y"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Mix-Fehler: {result.stderr}")

    return {
        "status": "ok",
        "datei": output_name,
        "groesse_mb": round(output_path.stat().st_size/1024/1024, 2)
    }

@app.delete("/tts/musik/{filename}")
def delete_musik(filename: str):
    path = MUSIK_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    path.unlink()
    return {"status": "ok", "geloescht": filename}

# ── Edge TTS ──────────────────────────────────────────────────
class EdgeTTSRequest(BaseModel):
    text: str
    voice: str = "tr-TR-EmelNeural"
    filename: str = ""
    rate: str = "+0%"
    pitch: str = "+0Hz"
    output_format: str = "mp3"

class EdgeTTSBookRequest(BaseModel):
    chapters: list[str]
    voice: str = "tr-TR-EmelNeural"
    book_name: str = "hoerbuch"
    output_format: str = "mp3"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    cover_path: str = ""
    use_emotion_tags: bool = False
    auto_tag: bool = False

@app.get("/edge/voices")
async def edge_voices():
    """Alle verfügbaren Edge TTS Stimmen auflisten"""
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        result = []
        for v in voices:
            result.append({
                "name": v["ShortName"],
                "display": v.get("FriendlyName", v["ShortName"]),
                "lang": v["Locale"],
                "gender": v["Gender"]
            })
        return {"voices": result, "anzahl": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/edge/generate")
async def edge_generate(req: EdgeTTSRequest):
    """Einzelnen Text mit Edge TTS generieren"""
    try:
        import edge_tts
        filename = req.filename or f"edge_{uuid.uuid4().hex[:8]}.mp3"
        out_path = OUTPUT_DIR / filename
        communicate = edge_tts.Communicate(req.text, req.voice, rate=req.rate, pitch=req.pitch)
        await communicate.save(str(out_path))
        return {
            "status": "ok",
            "datei": filename,
            "groesse_kb": round(out_path.stat().st_size/1024, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/edge/book")
async def edge_book(req: EdgeTTSBookRequest, background_tasks: BackgroundTasks):
    """Hörbuch mit Edge TTS generieren"""
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"status": "running", "done": 0, "total": len(req.chapters), "files": [], "errors": [], "output": ""}
    background_tasks.add_task(_process_edge_book, job_id, req)
    return {"job_id": job_id, "status": "gestartet", "kapitel_anzahl": len(req.chapters)}

async def _process_edge_book_async(job_id: str, req: EdgeTTSBookRequest):
    """Edge TTS Buch-Generierung (async)"""
    import edge_tts
    book_dir = OUTPUT_DIR / req.book_name
    book_dir.mkdir(parents=True, exist_ok=True)
    kapitel_files = []

    for i, chapter_text in enumerate(req.chapters):
        if not chapter_text.strip():
            continue
        kapitel_num = f"{i+1:03d}"
        filename = f"kapitel_{kapitel_num}.mp3"
        out_path = book_dir / filename
        try:
            communicate = edge_tts.Communicate(chapter_text, req.voice, rate=req.rate, pitch=req.pitch)
            await communicate.save(str(out_path))
            kapitel_files.append(out_path)
            with jobs_lock:
                jobs[job_id]["done"] += 1
                jobs[job_id]["files"].append(filename)
        except Exception as e:
            with jobs_lock:
                jobs[job_id]["errors"].append(f"Kapitel {kapitel_num}: {str(e)}")

    # Zusammenfügen
    if kapitel_files:
        cover = Path(req.cover_path) if req.cover_path else None
        fmt = req.output_format.lower()
        if fmt == "m4b":
            out = book_dir / f"{req.book_name}.m4b"
            # MP3 zu WAV konvertieren für merge
            wav_files = []
            for mp3 in kapitel_files:
                wav = mp3.with_suffix('.wav')
                subprocess.run(["ffmpeg", "-i", str(mp3), str(wav), "-y"], capture_output=True)
                wav_files.append(wav)
            merge_to_m4b(wav_files, out, title=req.book_name, cover_path=cover)
        else:
            out = book_dir / f"{req.book_name}_komplett.mp3"
            # Alle MP3s zusammenfügen
            list_file = book_dir / "_list.txt"
            with open(list_file, "w") as f:
                for mp3 in kapitel_files:
                    f.write(f"file '{mp3.resolve()}'\n")
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-codec:a", "copy",
                str(out), "-y"
            ], capture_output=True)
            list_file.unlink(missing_ok=True)
            if cover and cover.exists():
                out_cover = book_dir / f"{req.book_name}_mit_cover.mp3"
                subprocess.run([
                    "ffmpeg", "-i", str(out), "-i", str(cover),
                    "-map", "0:a", "-map", "1:v",
                    "-codec:a", "copy", "-codec:v", "copy",
                    "-id3v2_version", "3",
                    str(out_cover), "-y"
                ], capture_output=True)
                out = out_cover

        with jobs_lock:
            jobs[job_id]["status"] = "fertig"
            jobs[job_id]["output"] = out.name
    else:
        with jobs_lock:
            jobs[job_id]["status"] = "fertig_mit_fehlern"

def _process_edge_book(job_id: str, req: EdgeTTSBookRequest):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_edge_book_async(job_id, req))
    finally:
        loop.close()


def system_info():
    return {
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model_loaded": tts_engine is not None,
        "cached_voices": len(_cached_latents)
    }

# ── Buch-Job ──────────────────────────────────────────────────
def _process_book(job_id: str, req: ChapterRequest):
    book_dir = OUTPUT_DIR / req.book_name
    book_dir.mkdir(parents=True, exist_ok=True)
    kapitel_files = []

    for i, chapter_text in enumerate(req.chapters):
        # Cancel Check
        with jobs_lock:
            if jobs[job_id].get("cancelled"):
                jobs[job_id]["status"] = "abgebrochen"
                return
        kapitel_num = str(i + 1).zfill(3)
        filename = f"kapitel_{kapitel_num}.wav"
        out_path = book_dir / filename
        # Text bereinigen — Halluzination am Ende verhindern
        chapter_text = chapter_text.strip()
        if chapter_text and chapter_text[-1] not in '.!?،؟…':
            chapter_text = chapter_text + '.'
        try:
            # Auto-Tag wenn aktiviert
            if req.auto_tag:
                chapter_text = auto_tag_text(chapter_text)
            # Emotion Tags verarbeiten wenn vorhanden
            if req.use_emotion_tags and any(f'[{t}]' in chapter_text for t in TAG_PRESETS):
                chunks = parse_emotion_chunks(chapter_text, req)
                wav_parts = []
                for chunk in chunks:
                    if chunk['type'] == 'silence':
                        sil_path = out_path.parent / f"_sil_{uuid.uuid4().hex[:6]}.wav"
                        make_silence(chunk['duration'], sil_path)
                        wav_parts.append(sil_path)
                    elif chunk['type'] == 'speech' and chunk['text'].strip():
                        part_path = out_path.parent / f"_part_{uuid.uuid4().hex[:6]}.wav"
                        synthesize(chunk['text'], req.language, req.speaker_wav, part_path,
                                  chunk['temperature'], chunk['repetition_penalty'], 
                                  chunk['top_k'], chunk['speed'])
                        wav_parts.append(part_path)
                if wav_parts:
                    merge_wav_files(wav_parts, out_path)
                    for p in wav_parts:
                        p.unlink(missing_ok=True)
            else:
                synthesize(chapter_text, req.language, req.speaker_wav, out_path,
                          req.temperature, req.repetition_penalty, req.top_k, req.speed)
            kapitel_files.append(out_path)
            with jobs_lock:
                jobs[job_id]["done"] += 1
                jobs[job_id]["files"].append(filename)
        except Exception as e:
            with jobs_lock:
                jobs[job_id]["errors"].append(f"Kapitel {kapitel_num}: {str(e)}")

    # Output Format
    if kapitel_files:
        try:
            fmt = req.output_format.lower()
            cover = Path(req.cover_path) if req.cover_path else None
            if fmt == "m4b":
                out = book_dir / f"{req.book_name}.m4b"
                merge_to_m4b(kapitel_files, out, title=req.book_name, cover_path=cover)
            elif fmt == "wav":
                out = book_dir / f"{req.book_name}_komplett.wav"
                merge_wav_files(kapitel_files, out)
            else:
                out = book_dir / f"{req.book_name}_komplett.mp3"
                merge_to_mp3(kapitel_files, out, cover_path=cover)
            with jobs_lock:
                jobs[job_id]["output"] = out.name
        except Exception as e:
            with jobs_lock:
                jobs[job_id]["errors"].append(f"Merge: {str(e)}")

    with jobs_lock:
        jobs[job_id]["status"] = "fertig" if not jobs[job_id]["errors"] else "fertig_mit_fehlern"
        jobs[job_id]["ausgabe_ordner"] = str(book_dir)


# ════════════════════════════════════════════════════════════════
# FastWhisper Transkription
# ════════════════════════════════════════════════════════════════

_whisper_model = None
_whisper_model_size = None
_whisper_lock = threading.Lock()

def merge_short_segments(segments, min_words=8):
    """Kurze Segmente zusammenführen für bessere Lesbarkeit beim Hörbuch"""
    merged = []
    buffer_text = ""
    buffer_start = None
    buffer_end = None

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue

        if buffer_text == "":
            buffer_text = text
            buffer_start = seg.start
            buffer_end = seg.end
        else:
            word_count = len(buffer_text.split())
            # Zusammenführen wenn:
            # 1. Vorheriges Segment zu kurz (unter min_words)
            # 2. Vorheriges Segment endet nicht mit Satzzeichen
            ends_with_punct = buffer_text[-1] in '.!?…'
            if word_count < min_words or not ends_with_punct:
                buffer_text += " " + text
                buffer_end = seg.end
            else:
                merged.append((buffer_text, buffer_start, buffer_end))
                buffer_text = text
                buffer_start = seg.start
                buffer_end = seg.end

    if buffer_text:
        merged.append((buffer_text, buffer_start, buffer_end))

    return merged

def get_whisper_model(size: str = "small"):
    global _whisper_model, _whisper_model_size
    with _whisper_lock:
        if _whisper_model is None or _whisper_model_size != size:
            _whisper_model = None  # altes Modell freigeben
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            _whisper_model = WhisperModel(size, device=device, compute_type=compute)
            _whisper_model_size = size
    return _whisper_model


# ── Transkription Background Jobs ────────────────────────────
_transcribe_jobs: dict = {}
_transcribe_jobs_lock = threading.Lock()

@app.post("/transcribe/async")
async def transcribe_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model_size: str = Form("small"),
    archive: bool = Form(True),
    project_name: str = Form(""),
    folder: str = Form("")
):
    """Transkription als Background Job — kein Cloudflare Timeout"""
    job_id = uuid.uuid4().hex[:12]
    content = await file.read()
    suffix = Path(file.filename).suffix.lower()
    filename = file.filename

    with _transcribe_jobs_lock:
        _transcribe_jobs[job_id] = {"status": "running", "fortschritt": 0, "text": "", "srt": "", "modell": model_size, "fehler": ""}

    background_tasks.add_task(
        _run_transcribe_job, job_id, content, suffix, filename,
        language, model_size, archive, project_name, folder
    )
    return {"job_id": job_id, "status": "gestartet"}

def _run_transcribe_job(job_id, content, suffix, filename, language, model_size, archive, project_name, folder):
    import asyncio
    try:
        tmp_path = EINGABE_DIR / f"{uuid.uuid4().hex}{suffix}"
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        wav_path = tmp_path.with_suffix(".wav")
        if suffix not in [".wav"]:
            result = subprocess.run([
                "ffmpeg", "-i", str(tmp_path),
                "-ar", "16000", "-ac", "1", "-y", str(wav_path)
            ], capture_output=True)
            if result.returncode != 0 or not wav_path.exists():
                raise Exception(f"FFmpeg Fehler: {result.stderr.decode()[:200]}")
        else:
            wav_path = tmp_path

        model = get_whisper_model(model_size)
        lang = None if language == "auto" else language
        segments_list, info = model.transcribe(str(wav_path), language=lang, beam_size=5, vad_filter=True)
        segments = list(segments_list)

        text_parts = []
        srt_parts = []
        merged = merge_short_segments(segments, min_words=5)
        for i, (text, start_t, end_t) in enumerate(merged, 1):
            text_parts.append(text)
            start = f"{int(start_t//3600):02d}:{int((start_t%3600)//60):02d}:{start_t%60:06.3f}".replace(".", ",")
            end = f"{int(end_t//3600):02d}:{int((end_t%3600)//60):02d}:{end_t%60:06.3f}".replace(".", ",")
            srt_parts.append(f"{i}\n{start} --> {end}\n{text}\n")

        full_text = "\n".join(text_parts)
        srt_text = "\n".join(srt_parts)

        base_name = re.sub(r'[^\w\-_]', '_', base_name)
        if folder.strip():
            folder_clean = re.sub(r'[^\w\-_]', '_', folder.strip())
            save_dir = TRANSCRIPTION_DIR / folder_clean
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = TRANSCRIPTION_DIR

        (save_dir / f"{base_name}.txt").write_text(full_text, encoding="utf-8")
        (save_dir / f"{base_name}.srt").write_text(srt_text, encoding="utf-8")

        if archive:
            shutil.copy2(tmp_path, ARCHIV_DIR / tmp_path.name)

        with _transcribe_jobs_lock:
            _transcribe_jobs[job_id].update({
                "status": "fertig",
                "text": full_text,
                "srt": srt_text,
                "sprache": info.language,
                "sprache_wahrscheinlichkeit": round(info.language_probability, 2),
                "dauer_sek": round(info.duration, 1),
                "woerter": len(full_text.split()),
                "txt_datei": f"{base_name}.txt",
                "srt_datei": f"{base_name}.srt",
                "modell": model_size
            })
    except Exception as e:
        with _transcribe_jobs_lock:
            _transcribe_jobs[job_id]["status"] = "fehler"
            _transcribe_jobs[job_id]["fehler"] = str(e)
    finally:
        if wav_path != tmp_path and wav_path.exists():
            wav_path.unlink()

@app.get("/transcribe/status/{job_id}")
def transcribe_status(job_id: str):
    with _transcribe_jobs_lock:
        job = _transcribe_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job

@app.post("/transcribe/stream")
async def transcribe_stream(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model_size: str = Form("small"),
    project_name: str = Form(""),
    folder: str = Form("")
):
    """Live-Transkription mit Server-Sent Events — Satz für Satz"""
    content = await file.read()
    suffix = Path(file.filename).suffix.lower()
    filename = file.filename

    async def generate():
        tmp_path = EINGABE_DIR / f"{uuid.uuid4().hex}{suffix}"
        wav_path = None
        try:
            # Datei speichern
            with open(tmp_path, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # FFmpeg konvertieren
            wav_path = tmp_path.with_suffix(".wav")
            if suffix not in [".wav"]:
                result = subprocess.run([
                    "ffmpeg", "-i", str(tmp_path),
                    "-ar", "16000", "-ac", "1", "-y", str(wav_path)
                ], capture_output=True)
                if result.returncode != 0 or not wav_path.exists():
                    yield f"data: {{\"fehler\": \"FFmpeg Fehler\"}}\n\n"
                    return
            else:
                wav_path = tmp_path

            # FastWhisper streamen
            model = get_whisper_model(model_size)
            lang = None if language == "auto" else language
            segments_list, info = model.transcribe(
                str(wav_path), language=lang, beam_size=5, vad_filter=True
            )

            # Sprache senden
            import json
            yield f"data: {json.dumps({'typ': 'info', 'sprache': info.language, 'modell': model_size})}\n\n"

            # Live streamen UND sammeln für Merge
            raw_segments = []
            all_text_live = []
            all_srt_live = []
            seg_num_live = 0

            for seg in segments_list:
                raw_segments.append(seg)
                seg_num_live += 1
                text = seg.text.strip()
                start = f"{int(seg.start//3600):02d}:{int((seg.start%3600)//60):02d}:{seg.start%60:06.3f}".replace(".", ",")
                end = f"{int(seg.end//3600):02d}:{int((seg.end%3600)//60):02d}:{seg.end%60:06.3f}".replace(".", ",")
                srt_zeile = f"{seg_num_live}\n{start} --> {end}\n{text}"
                all_text_live.append(text)
                all_srt_live.append(srt_zeile)
                yield f"data: {json.dumps({'typ': 'segment', 'nr': seg_num_live, 'text': text, 'start': start, 'end': end, 'srt': srt_zeile})}\n\n"

            # Nach dem Stream: Segmente mergen für Speicherung
            merged = merge_short_segments(raw_segments, min_words=5)
            all_text = [t for t, _, _ in merged]
            all_srt = []
            for i, (text, start_t, end_t) in enumerate(merged, 1):
                start = f"{int(start_t//3600):02d}:{int((start_t%3600)//60):02d}:{start_t%60:06.3f}".replace(".", ",")
                end = f"{int(end_t//3600):02d}:{int((end_t%3600)//60):02d}:{end_t%60:06.3f}".replace(".", ",")
                all_srt.append(f"{i}\n{start} --> {end}\n{text}")

            # Fertig — speichern
            full_text = "\n".join(all_text)
            srt_text = "\n\n".join(all_srt)

            base_name = project_name.strip() if project_name.strip() else Path(filename).stem
            base_name = re.sub(r'[^\w\-_]', '_', base_name)
            save_dir = TRANSCRIPTION_DIR
            if folder.strip():
                folder_clean = re.sub(r'[^\w\-_]', '_', folder.strip())
                save_dir = TRANSCRIPTION_DIR / folder_clean
                save_dir.mkdir(parents=True, exist_ok=True)

            (save_dir / f"{base_name}.txt").write_text(full_text, encoding="utf-8")
            (save_dir / f"{base_name}.srt").write_text(srt_text, encoding="utf-8")

            yield f"data: {json.dumps({'typ': 'fertig', 'woerter': len(full_text.split()), 'txt_datei': f'{base_name}.txt', 'srt_datei': f'{base_name}.srt', 'text': full_text, 'srt': srt_text})}\n\n"

        except Exception as e:
            import json
            yield f"data: {json.dumps({'typ': 'fehler', 'nachricht': str(e)})}\n\n"
        finally:
            if wav_path and wav_path != tmp_path and wav_path.exists():
                wav_path.unlink()
            if tmp_path.exists():
                tmp_path.unlink()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model_size: str = Form("small"),
    archive: bool = Form(True),
    project_name: str = Form(""),
    folder: str = Form("")
):
    """Audio/Video Datei transkribieren mit FastWhisper"""
    suffix = Path(file.filename).suffix.lower()
    tmp_path = EINGABE_DIR / f"{uuid.uuid4().hex}{suffix}"

    try:
        # Datei speichern — komplett schreiben
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # FFmpeg: zu WAV konvertieren falls nötig
        wav_path = tmp_path.with_suffix(".wav")
        if suffix not in [".wav"]:
            result = subprocess.run([
                "ffmpeg", "-i", str(tmp_path),
                "-ar", "16000", "-ac", "1", "-y", str(wav_path)
            ], capture_output=True)
            if result.returncode != 0 or not wav_path.exists():
                raise HTTPException(status_code=400, detail=f"FFmpeg Fehler: {result.stderr.decode()[:500]}")
        else:
            wav_path = tmp_path
        
        if not wav_path.exists():
            raise HTTPException(status_code=500, detail=f"WAV Datei nicht gefunden: {wav_path}")

        # FastWhisper transkribieren
        model = get_whisper_model(model_size)
        lang = None if language == "auto" else language
        segments_list, info = model.transcribe(
            str(wav_path),
            language=lang,
            beam_size=5,
            vad_filter=True
        )
        # Segmente sofort konsumieren (Generator leeren bevor WAV gelöscht wird)
        segments = list(segments_list)

        # Kurze Segmente zusammenführen für bessere Lesbarkeit
        text_parts = []
        srt_parts = []
        merged = merge_short_segments(segments, min_words=5)
        for i, (text, start_t, end_t) in enumerate(merged, 1):
            text_parts.append(text)
            start = f"{int(start_t//3600):02d}:{int((start_t%3600)//60):02d}:{start_t%60:06.3f}".replace(".", ",")
            end = f"{int(end_t//3600):02d}:{int((end_t%3600)//60):02d}:{end_t%60:06.3f}".replace(".", ",")
            srt_parts.append(f"{i}\n{start} --> {end}\n{text}\n")

        full_text = "\n".join(text_parts)
        srt_text = "\n".join(srt_parts)

        # Transkription speichern — Projektname + Ordner nutzen
        base_name = project_name.strip() if project_name.strip() else Path(file.filename).stem
        base_name = re.sub(r'[^\w\-_]', '_', base_name)

        # Zielordner bestimmen
        if folder.strip():
            folder_clean = re.sub(r'[^\w\-_]', '_', folder.strip())
            save_dir = TRANSCRIPTION_DIR / folder_clean
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = TRANSCRIPTION_DIR

        txt_path = save_dir / f"{base_name}.txt"
        srt_path = save_dir / f"{base_name}.srt"
        txt_path.write_text(full_text, encoding="utf-8")
        srt_path.write_text(srt_text, encoding="utf-8")

        # Archivieren
        if archive:
            archiv_path = ARCHIV_DIR / tmp_path.name
            shutil.copy2(tmp_path, archiv_path)

        return {
            "status": "ok",
            "sprache": info.language,
            "sprache_wahrscheinlichkeit": round(info.language_probability, 2),
            "dauer_sek": round(info.duration, 1),
            "text": full_text,
            "srt": srt_text,
            "woerter": len(full_text.split()),
            "txt_datei": txt_path.name,
            "srt_datei": srt_path.name,
            "ordner": folder_clean if folder.strip() else "",
            "modell": model_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Temp WAV aufräumen
        if wav_path != tmp_path and wav_path.exists():
            wav_path.unlink()

@app.get("/transcribe/files")
def list_transcriptions():
    """Alle Transkriptionen + Ordner auflisten"""
    import datetime
    files = []
    ordner = []
    for f in TRANSCRIPTION_DIR.iterdir():
        if f.is_dir():
            ordner.append({
                "name": f.name,
                "typ": "ordner",
                "dateien_anzahl": len(list(f.glob("*.txt"))) + len(list(f.glob("*.srt")))
            })
        elif f.suffix in [".txt", ".srt"]:
            files.append({
                "name": f.name,
                "groesse_kb": round(f.stat().st_size / 1024, 1),
                "datum": f.stat().st_mtime,
                "datum_str": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
                "typ": "datei"
            })
    # Neueste zuerst
    files.sort(key=lambda x: x["datum"], reverse=True)
    return {"dateien": files, "ordner": ordner}

@app.get("/transcribe/download/{filename}")
def download_transcription(filename: str):
    path = TRANSCRIPTION_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    return FileResponse(path, filename=filename)

@app.delete("/transcribe/files/{filepath:path}")
def delete_transcription(filepath: str):
    path = TRANSCRIPTION_DIR / filepath
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    path.unlink()
    return {"status": "ok", "geloescht": filepath}

@app.get("/transcribe/folder/{folder_name}")
def get_folder_contents(folder_name: str):
    """Inhalt eines Transkriptions-Ordners abrufen"""
    import datetime
    folder = TRANSCRIPTION_DIR / folder_name
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
    files = []
    for f in folder.iterdir():
        if f.suffix in [".txt", ".srt"]:
            files.append({
                "name": f.name,
                "pfad": f"{folder_name}/{f.name}",
                "groesse_kb": round(f.stat().st_size / 1024, 1),
                "datum": f.stat().st_mtime,
                "datum_str": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
            })
    files.sort(key=lambda x: x["datum"], reverse=True)
    return {"ordner": folder_name, "dateien": files}

@app.get("/transcribe/download/{folder_or_file}/{filename}")
def download_transcription_in_folder(folder_or_file: str, filename: str):
    """Datei aus Unterordner herunterladen"""
    path = TRANSCRIPTION_DIR / folder_or_file / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    return FileResponse(path, filename=filename)
@app.post("/transcribe/folder")
async def create_transcription_folder(data: dict):
    """Neuen Ordner in TRANSKRIPTIONEN erstellen"""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Kein Ordnername angegeben")
    name = re.sub(r'[^\w\-_]', '_', name)
    folder = TRANSCRIPTION_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "ordner": name}

@app.delete("/transcribe/folder/{folder_name}")
def delete_transcription_folder(folder_name: str):
    """Ordner in TRANSKRIPTIONEN löschen"""
    folder = TRANSCRIPTION_DIR / folder_name
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
    shutil.rmtree(folder)
    return {"status": "ok", "geloescht": folder_name}

# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
# Hörbuch Ordner-Struktur
# ════════════════════════════════════════════════════════════════
@app.get("/tts/hoerbuch/folders")
def list_hoerbuch_folders():
    import datetime
    folders = []
    files_root = []
    for item in OUTPUT_DIR.iterdir():
        if item.is_dir():
            audio_files = []
            for ext in ["*.mp3", "*.wav", "*.m4b"]:
                audio_files.extend(item.glob(ext))
            audio_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            folders.append({
                "name": item.name,
                "dateien_anzahl": len(audio_files),
                "datum": item.stat().st_mtime,
                "datum_str": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
            })
        elif item.suffix in [".mp3", ".wav", ".m4b"] and not item.name.startswith("_"):
            files_root.append({
                "name": item.name,
                "groesse_mb": round(item.stat().st_size / 1024 / 1024, 2),
                "datum": item.stat().st_mtime,
                "datum_str": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
            })
    folders.sort(key=lambda x: x["datum"], reverse=True)
    files_root.sort(key=lambda x: x["datum"], reverse=True)
    return {"ordner": folders, "dateien": files_root}

@app.get("/tts/hoerbuch/folder/{folder_name}")
def get_hoerbuch_folder(folder_name: str):
    import datetime
    folder = OUTPUT_DIR / folder_name
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
    files = []
    for ext in ["*.mp3", "*.wav", "*.m4b"]:
        for f in folder.glob(ext):
            files.append({
                "name": f.name,
                "pfad": f"{folder_name}/{f.name}",
                "groesse_mb": round(f.stat().st_size / 1024 / 1024, 2),
                "datum": f.stat().st_mtime,
                "datum_str": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
            })
    files.sort(key=lambda x: x["datum"], reverse=True)
    return {"ordner": folder_name, "dateien": files}

@app.post("/tts/hoerbuch/folder")
async def create_hoerbuch_folder(data: dict):
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Kein Ordnername")
    name = re.sub(r'[^\w\-_]', '_', name)
    folder = OUTPUT_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "ordner": name}

@app.delete("/tts/hoerbuch/folder/{folder_name}")
def delete_hoerbuch_folder(folder_name: str):
    folder = OUTPUT_DIR / folder_name
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
    shutil.rmtree(folder)
    return {"status": "ok", "geloescht": folder_name}

# Archiv Endpoints (Gemini)
# ════════════════════════════════════════════════════════════════
(ARCHIV_DIR / "hoerbuch").mkdir(exist_ok=True)
(ARCHIV_DIR / "transkription").mkdir(exist_ok=True)

@app.get("/archiv/folders")
def list_archiv_folders():
    import datetime
    result = {}
    for sub in ["hoerbuch", "transkription"]:
        d = ARCHIV_DIR / sub
        d.mkdir(exist_ok=True)
        files = sorted(
            [f for f in d.iterdir() if f.is_file() and not f.name.startswith("_")],
            key=lambda f: f.stat().st_mtime, reverse=True
        )
        result[sub] = [{
            "name": f.name,
            "groesse_mb": round(f.stat().st_size / 1024 / 1024, 2),
            "datum": f.stat().st_mtime,
            "datum_str": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
        } for f in files]
    return {"ordner": result}

@app.delete("/archiv/files/{subfolder}/{filename}")
def delete_archiv_file(subfolder: str, filename: str):
    if subfolder not in ["hoerbuch", "transkription"]:
        raise HTTPException(status_code=400, detail="Ungültiger Ordner")
    path = ARCHIV_DIR / subfolder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    path.unlink()
    return {"status": "ok"}

@app.patch("/archiv/rename")
async def rename_archiv_file(data: dict):
    subfolder = data.get("subfolder", "")
    old_name  = data.get("old_name", "").strip()
    new_name  = re.sub(r'[^\w\-_.]', '_', data.get("new_name", "").strip())
    old_path = ARCHIV_DIR / subfolder / old_name
    new_path = ARCHIV_DIR / subfolder / new_name
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    old_path.rename(new_path)
    return {"status": "ok", "neu": new_name}

@app.get("/archiv/stream/{subfolder}/{filename}")
def stream_archiv_file(subfolder: str, filename: str):
    path = ARCHIV_DIR / subfolder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    media_map = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"}
    media_type = media_map.get(Path(filename).suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=filename)

# Admin Logging
# ════════════════════════════════════════════════════════════════
import logging as _logging
from collections import deque

_log_buffer = deque(maxlen=500)  # max 500 Zeilen im Speicher

class BufferHandler(_logging.Handler):
    def emit(self, record):
        _log_buffer.append({
            "zeit": self.formatter.formatTime(record, "%H:%M:%S"),
            "level": record.levelname,
            "nachricht": record.getMessage()
        })

_buf_handler = BufferHandler()
_buf_handler.setFormatter(_logging.Formatter())
_logging.getLogger().addHandler(_buf_handler)
_logging.getLogger("faster_whisper").addHandler(_buf_handler)
_logging.getLogger("uvicorn").addHandler(_buf_handler)

@app.get("/admin/logs")
def get_logs(n: int = 100):
    """Letzte n Log-Einträge abrufen"""
    entries = list(_log_buffer)[-n:]
    return {"logs": entries, "gesamt": len(_log_buffer)}

@app.delete("/admin/logs")
def clear_logs():
    _log_buffer.clear()
    return {"status": "ok"}
