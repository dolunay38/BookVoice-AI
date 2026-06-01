import os, uuid, threading, torchaudio, torch, shutil, subprocess, re, tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Konfiguration ──────────────────────────────────────────────
OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT", "/app/HOERBUCH"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR = Path("/app/tts_models/tts_models--multilingual--multi-dataset--xtts_v2")
VOICE_DIR = Path("/app/tts_models")
DEFAULT_LANG = os.getenv("TTS_LANG", "tr")
DEFAULT_SPEAKER_WAV = "/app/tts_models/stimme.wav"

# CPU/GPU Auto-Detect
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Device: {DEVICE.upper()}")

AUDIO_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"}
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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    cover_path: str = ""  # Optionales Cover-Bild  # mp3, wav, m4b

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
    return [c for c in chunks if len(c) > 2]

# ── Audio Merge ────────────────────────────────────────────────
def make_silence(duration: float, out_path: Path, sample_rate: int = 24000):
    samples = int(duration * sample_rate)
    silence = torch.zeros(1, samples)
    torchaudio.save(str(out_path), silence, sample_rate)

def merge_wav_files(input_files: list[Path], output_file: Path):
    if len(input_files) == 1:
        shutil.copy(input_files[0], output_file)
        return
    list_file = output_file.parent / f"_list_{uuid.uuid4().hex[:6]}.txt"
    with open(list_file, "w") as f:
        for wav in input_files:
            f.write(f"file '{wav.resolve()}'\n")
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-af", "aresample=24000,dynaudnorm=f=150:g=15",
        str(output_file), "-y"
    ], capture_output=True)
    list_file.unlink(missing_ok=True)

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
    return {"status": "ok", "device": DEVICE}

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

@app.get("/tts/book/status/{job_id}")
def book_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job

@app.get("/tts/files")
def list_files():
    files = []
    for ext in ["*.wav", "*.mp3", "*.m4b"]:
        for f in sorted(OUTPUT_DIR.rglob(ext)):
            if not f.name.startswith("_"):
                files.append({"name": f.name, "groesse_mb": round(f.stat().st_size / 1024 / 1024, 2)})
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

@app.get("/tts/voices")
def list_voices():
    voices = []
    for ext in ["*.wav", "*.mp3"]:
        for f in VOICE_DIR.glob(ext):
            if not f.name.startswith("tts_models") and not f.name.startswith("_"):
                voices.append({"name": f.name, "groesse_kb": round(f.stat().st_size / 1024, 1)})
    return {"stimmen": voices}

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
        kapitel_num = str(i + 1).zfill(3)
        filename = f"kapitel_{kapitel_num}.wav"
        out_path = book_dir / filename
        try:
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
