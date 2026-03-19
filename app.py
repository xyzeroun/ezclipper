"""
TikTok Clipper — Main Application
FastAPI web server with processing pipeline.
"""
import os
import sys
import uuid
import asyncio
import logging
import webbrowser
import threading
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
import shutil

from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse

import config
from core.downloader import Downloader
from core.transcriber import Transcriber
from core.detector import Detector
from core.clipper import Clipper
from core.scheduler import JobScheduler

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("clipper")

# --- Global State ---
processing_jobs: dict = {}  # job_id -> status dict
scheduler = JobScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: open browser on startup."""
    settings = config.load_settings()
    if settings.get("auto_open_browser", True):
        port = settings.get("server_port", 8000)
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    yield


# --- FastAPI App ---
app = FastAPI(title="TikTok Clipper", lifespan=lifespan)

# Mount static files and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ========================
# ROUTES
# ========================

@app.get("/")
async def index(request: Request):
    """Main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/process")
async def start_processing(request: Request, background_tasks: BackgroundTasks):
    """Start processing a YouTube URL."""
    body = await request.json()
    url = body.get("url", "").strip()
    max_clips = body.get("max_clips", 5)
    is_livestream = body.get("is_livestream", False)
    livestream_duration = body.get("livestream_duration", 300)

    if not url:
        return JSONResponse({"error": "URL is required"}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    processing_jobs[job_id] = {
        "id": job_id,
        "url": url,
        "status": "starting",
        "progress": 0,
        "current_step": "Initializing...",
        "started_at": datetime.now().isoformat(),
        "clips": [],
        "error": None,
        "log": [],
    }

    # Run processing in background
    background_tasks.add_task(
        process_video, job_id, url, max_clips, is_livestream, livestream_duration
    )

    return {"job_id": job_id, "status": "started"}

@app.post("/api/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_clips: int = Form(5)
):
    """Upload a local video and start processing."""
    job_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file safely
    file_path = os.path.join(config.TEMP_DIR, f"{job_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    processing_jobs[job_id] = {
        "id": job_id,
        "url": f"Local File: {file.filename}",
        "status": "starting",
        "progress": 0,
        "current_step": "Formatting local video...",
        "started_at": datetime.now().isoformat(),
        "clips": [],
        "error": None,
        "log": [],
    }

    # Run processing in background (url holds the local path)
    background_tasks.add_task(
        process_video, job_id, file_path, max_clips, is_livestream=False, livestream_duration=300, is_local_file=True
    )

    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status."""
    job = processing_jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@app.get("/api/clips")
async def list_clips():
    """List all generated clips."""
    clips = []
    if os.path.exists(config.OUTPUT_DIR):
        for f in sorted(os.listdir(config.OUTPUT_DIR)):
            if f.endswith(".mp4") and not f.startswith("_"):
                fpath = os.path.join(config.OUTPUT_DIR, f)
                clips.append({
                    "filename": f,
                    "url": f"/output/{f}",
                    "size_mb": round(os.path.getsize(fpath) / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
                })
    return {"clips": clips}


@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    settings = config.load_settings()
    # Mask API keys for security
    masked = settings.copy()
    for key in ["reka_api_key"]:
        if masked.get(key):
            masked[key] = masked[key][:8] + "..." + masked[key][-4:]
    return masked


@app.post("/api/settings")
async def update_settings(request: Request):
    """Update settings."""
    body = await request.json()
    settings = config.load_settings()
    settings.update(body)
    config.save_settings(settings)
    return {"status": "saved"}


@app.get("/api/jobs")
async def list_jobs():
    """List all scheduled jobs."""
    return {"jobs": scheduler.get_all_jobs()}


@app.post("/api/jobs")
async def create_job(request: Request, background_tasks: BackgroundTasks):
    """Create a new scheduled job."""
    body = await request.json()
    job = scheduler.add_job(
        url=body.get("url", ""),
        schedule_time=body.get("schedule_time"),
        repeat_interval=body.get("repeat_interval"),
        max_clips=body.get("max_clips", 5),
    )

    # If no schedule time, process immediately
    if not body.get("schedule_time"):
        background_tasks.add_task(
            process_video, job["id"], job["url"], job["max_clips"]
        )

    return job


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a scheduled job."""
    if scheduler.delete_job(job_id):
        return {"status": "deleted"}
    return JSONResponse({"error": "Job not found"}, status_code=404)


@app.delete("/api/clips/{filename}")
async def delete_clip(filename: str):
    """Delete a clip file."""
    fpath = os.path.join(config.OUTPUT_DIR, filename)
    if os.path.exists(fpath) and fpath.endswith(".mp4"):
        os.remove(fpath)
        return {"status": "deleted"}
    return JSONResponse({"error": "File not found"}, status_code=404)


# ========================
# PROCESSING PIPELINE
# ========================

def _update_job(job_id: str, **kwargs):
    """Update a processing job's status."""
    if job_id in processing_jobs:
        processing_jobs[job_id].update(kwargs)
        if "current_step" in kwargs:
            processing_jobs[job_id]["log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] {kwargs['current_step']}"
            )


def process_video(
    job_id: str,
    url: str,
    max_clips: int = 5,
    is_livestream: bool = False,
    livestream_duration: int = 300,
    is_local_file: bool = False,
):
    """Full processing pipeline: download → transcribe → detect → clip."""
    settings = config.load_settings()

    try:
        if is_local_file:
            # url parameter holds the local file path
            video_path = url
            _update_job(
                job_id,
                status="transcribing",
                current_step=f"✅ Video ready from local file",
                progress=25,
            )
        else:
            # ===== STEP 1: DOWNLOAD =====
            _update_job(job_id, status="downloading", current_step="📥 Downloading video...", progress=5)

            downloader = Downloader(config.TEMP_DIR)

            def download_progress(step, pct):
                _update_job(job_id, progress=5 + int(pct * 0.2))

            if is_livestream:
                video_info = downloader.download_livestream(url, livestream_duration, download_progress)
            else:
                video_info = downloader.download(url, download_progress)

            video_path = video_info["file_path"]
            _update_job(
                job_id,
                status="transcribing",
                current_step=f"✅ Downloaded: {video_info['title']}",
                progress=25,
            )

        # ===== STEP 2: TRANSCRIBE =====
        _update_job(job_id, current_step="🎙️ Transcribing audio...")

        transcriber = Transcriber(
            model_size=settings.get("whisper_model", "base"),
            language=settings.get("whisper_language", "id"),
        )

        def transcribe_progress(step, pct):
            _update_job(job_id, progress=25 + int(pct * 0.2))

        transcript = transcriber.transcribe(video_path, transcribe_progress)

        _update_job(
            job_id,
            status="detecting",
            current_step=f"✅ Transcribed: {len(transcript['words'])} words",
            progress=50,
        )

        # ===== STEP 3: DETECT HIGHLIGHTS =====
        _update_job(job_id, current_step="🧠 AI analyzing highlights...")

        detector = Detector(
            reka_api_key=settings.get("reka_api_key", ""),
            reka_model=settings.get("reka_model", "reka-core"),
            min_clip_duration=settings.get("min_clip_duration", 15),
            max_clip_duration=settings.get("max_clip_duration", 60),
            max_clips=max_clips,
        )

        def detect_progress(step, pct):
            _update_job(job_id, progress=50 + int(pct * 0.15))

        highlights = detector.detect_highlights(transcript, video_path, detect_progress)

        _update_job(
            job_id,
            status="clipping",
            current_step=f"✅ Found {len(highlights)} highlights",
            progress=65,
        )

        # ===== STEP 4: CREATE CLIPS =====
        _update_job(job_id, current_step="✂️ Creating clips with captions...")

        clipper = Clipper(
            output_dir=config.OUTPUT_DIR,
            resolution=settings.get("output_resolution", "720p"),
            fps=settings.get("output_fps", 30),
            caption_font_size=settings.get("caption_font_size", 20),
            caption_color=settings.get("caption_color", "#FFFFFF"),
            caption_highlight_color=settings.get("caption_highlight_color", "#FFD700"),
            caption_position=settings.get("caption_position", "bottom"),
        )

        def clip_progress(step, pct):
            _update_job(job_id, progress=65 + int(pct * 0.30))

        clips = clipper.create_all_clips(
            video_path=video_path,
            highlights=highlights,
            words=transcript["words"],
            progress_callback=clip_progress,
        )

        # ===== DONE =====
        successful = [c for c in clips if c.get("file_path")]
        _update_job(
            job_id,
            status="completed",
            current_step=f"🎉 Done! {len(successful)} clips created",
            progress=100,
            clips=[
                {
                    "filename": os.path.basename(c["file_path"]),
                    "url": f"/output/{os.path.basename(c['file_path'])}",
                    "title": c["title"],
                    "reason": c.get("reason", ""),
                    "duration": round(c["duration"], 1),
                    "start": c["start"],
                    "end": c["end"],
                }
                for c in successful
            ],
        )

        # Clean up temp video
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except OSError:
            pass

        logger.info(f"Job {job_id} completed: {len(successful)} clips")

    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        _update_job(
            job_id,
            status="failed",
            current_step=f"❌ Error: {str(e)}",
            error=str(e),
        )


# ========================
# ENTRY POINT
# ========================

if __name__ == "__main__":
    import uvicorn

    settings = config.load_settings()
    port = settings.get("server_port", 8000)

    print(f"""
╔══════════════════════════════════════════╗
║          🎬 TikTok Clipper v1.0          ║
║     AI-Powered Video Clip Generator      ║
╠══════════════════════════════════════════╣
║  Server: http://localhost:{port}             ║
║  Output: {config.OUTPUT_DIR:<31s}║
╚══════════════════════════════════════════╝
    """)

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
