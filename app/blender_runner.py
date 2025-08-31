

import asyncio
import os
import shlex
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BLENDER_BIN = os.getenv("BLENDER_BIN", "/opt/blender/blender")
JOBS_DIR = Path(os.getenv("JOBS_DIR", "/data/jobs"))
DB_PATH = os.getenv("DB_PATH", "/data/state.db")

@dataclass
class Job:
    id: int
    name: str
    basename: str
    folder: str
    blend_path: Path

class RenderQueue:
    def __init__(self):
        self.q: asyncio.Queue[Job] = asyncio.Queue()
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._worker())

    async def enqueue(self, job: Job):
        await self.q.put(job)

    async def _worker(self):
        while True:
            job = await self.q.get()
            try:
                await run_blender_render(job)
                set_job_status(job.id, "DONE")
            except Exception as e:
                set_job_status(job.id, "ERROR", str(e))
            finally:
                self.q.task_done()

queue = RenderQueue()

# --- Persistence helpers (very small SQLite) ---
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  basename TEXT NOT NULL,
  folder TEXT NOT NULL,
  blend_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'QUEUED',
  error TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    with conn:
        conn.executescript(SCHEMA)


def create_job_record(name: str, basename: str, folder: str, blend_path: Path) -> int:
    conn = db()
    with conn:
        cur = conn.execute(
            "INSERT INTO jobs (name, basename, folder, blend_path, status) VALUES (?,?,?,?, 'QUEUED')",
            (name, basename, folder, str(blend_path)),
        )
        return cur.lastrowid


def set_job_status(job_id: int, status: str, error: Optional[str] = None):
    conn = db()
    with conn:
        conn.execute(
            "UPDATE jobs SET status=?, error=? WHERE id=?",
            (status, error, job_id),
        )


def iter_queued_jobs():
    conn = db()
    cur = conn.execute("SELECT * FROM jobs WHERE status IN ('QUEUED','RUNNING') ORDER BY id ASC")
    for row in cur.fetchall():
        yield row

# --- Blender invocation ---
async def run_blender_render(job: Job):
    # Render frame 1 as PNG into job folder
    output_pattern = (JOBS_DIR / job.folder / "render_#####").as_posix()
    cmd = (
        f"{shlex.quote(BLENDER_BIN)} -b {shlex.quote(job.blend_path.as_posix())} "
        f"-o {shlex.quote(output_pattern)} -F PNG -f 1"
    )
    set_job_status(job.id, "RUNNING")
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    # Stream logs to stdout; could be captured for UI later
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(line.decode().rstrip())
    rc = await proc.wait()
    if rc != 0:
        raise RuntimeError(f"Blender exited with code {rc}")

# --- Folder naming helper ---

def unique_folder_name(base: str) -> str:
    target = base
    n = 1
    while (JOBS_DIR / target).exists():
        n += 1
        target = f"{base}_{n}"
    return target