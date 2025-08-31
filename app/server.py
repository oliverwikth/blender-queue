import os
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import aiofiles

from .blender_runner import (
    JOBS_DIR, init_db, create_job_record, unique_folder_name, queue, Job
)

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UI_DIR = Path(__file__).parent / "ui"

app = FastAPI(title="Blender Render Queue")
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

@app.on_event("startup")
async def startup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    await queue.start()

@app.get("/")
async def root():
    index_path = UI_DIR / "index.html"
    return HTMLResponse(index_path.read_text("utf-8"))

@app.post("/api/upload")
async def upload_blend(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".blend"):
        raise HTTPException(status_code=400, detail="Only .blend files supported")

    basename = Path(file.filename).stem
    folder = unique_folder_name(basename)
    job_dir = JOBS_DIR / folder
    job_dir.mkdir(parents=True, exist_ok=True)

    blend_path = job_dir / file.filename
    async with aiofiles.open(blend_path, "wb") as f:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            await f.write(chunk)

    job_id = create_job_record(name=file.filename, basename=basename, folder=folder, blend_path=blend_path)
    await queue.enqueue(Job(id=job_id, name=file.filename, basename=basename, folder=folder, blend_path=blend_path))

    return {"ok": True, "job_id": job_id, "folder": folder}

@app.get("/api/jobs")
async def list_jobs():
    # Very small: read direct database
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", "/data/state.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, folder, status, error, created_at FROM jobs ORDER BY id DESC").fetchall()
    return {"jobs": [dict(r) for r in rows]}

@app.get("/api/folders")
async def list_folders():
    out = []
    for p in sorted(JOBS_DIR.iterdir()):
        if p.is_dir():
            files = [f.name for f in sorted(p.iterdir()) if f.is_file()]
            out.append({"folder": p.name, "files": files})
    return {"folders": out}

@app.get("/api/folder/{folder}")
async def folder_detail(folder: str):
    p = JOBS_DIR / folder
    if not p.exists() or not p.is_dir():
        raise HTTPException(404, detail="Folder not found")
    files = [f.name for f in sorted(p.iterdir()) if f.is_file()]
    return {"folder": folder, "files": files}

@app.get("/api/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    p = JOBS_DIR / folder / filename
    if not p.exists():
        raise HTTPException(404, detail="File not found")
    return FileResponse(p)