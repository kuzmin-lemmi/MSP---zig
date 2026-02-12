from fastapi import FastAPI, HTTPException, status
from pathlib import Path
import os
import json
from typing import List

try:
    from .models import TaskMeta, SubmitRequest, JobStatus
    from .job_manager import JobManager
    from .runner import Runner
except ImportError:
    from models import TaskMeta, SubmitRequest, JobStatus
    from job_manager import JobManager
    from runner import Runner

app = FastAPI(title="Zig Exercise Runner")

BASE_DIR = Path(__file__).resolve().parent
TASKS_DIR = os.getenv("TASKS_DIR", str(BASE_DIR.parent / "tasks"))
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "zig-runner:0.13.0")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
MAX_QUEUE = int(os.getenv("MAX_QUEUE", "200"))
JOB_TTL_MINUTES = int(os.getenv("JOB_TTL_MINUTES", "30"))
CODE_MAX_BYTES = int(os.getenv("CODE_MAX_BYTES", "131072"))

job_manager = JobManager(
    max_workers=MAX_WORKERS,
    max_queue=MAX_QUEUE,
    job_ttl_minutes=JOB_TTL_MINUTES
)
runner = Runner(docker_image=RUNNER_IMAGE, tasks_dir=TASKS_DIR)
job_manager.runner = runner


def _task_meta_path(task_id: str) -> Path:
    return Path(TASKS_DIR) / task_id / "meta.json"


def _task_exists(task_id: str) -> bool:
    return _task_meta_path(task_id).exists()


@app.on_event("startup")
async def startup():
    await job_manager.start()


@app.on_event("shutdown")
async def shutdown():
    await job_manager.stop()


@app.get("/")
async def root():
    return {
        "service": "zig-exercise-runner",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/tasks", response_model=List[TaskMeta])
async def list_tasks():
    tasks = []
    tasks_path = Path(TASKS_DIR)

    if not tasks_path.exists():
        return tasks

    for task_dir in tasks_path.iterdir():
        if task_dir.is_dir():
            meta_file = task_dir / "meta.json"
            if meta_file.exists():
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)
                    tasks.append(TaskMeta(**meta))

    return tasks


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task_dir = Path(TASKS_DIR) / task_id

    if not task_dir.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    statement_file = task_dir / "statement.md"
    meta_file = task_dir / "meta.json"

    if not statement_file.exists() or not meta_file.exists():
        raise HTTPException(status_code=404, detail="Task files not found")

    with open(statement_file, encoding="utf-8") as f:
        statement = f.read()

    with open(meta_file, encoding="utf-8") as f:
        meta = json.load(f)

    return {"statement": statement, "meta": TaskMeta(**meta)}


@app.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_solution(request: SubmitRequest):
    if not _task_exists(request.task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    if request.mode not in {"run", "check"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    code_size = len(request.code.encode("utf-8"))
    if code_size > CODE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Code size exceeds limit"
        )

    try:
        job_id = await job_manager.submit(
            task_id=request.task_id,
            code=request.code,
            mode=request.mode
        )
        return {"job_id": job_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    job_status = await job_manager.get_job(job_id)

    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    cancelled = await job_manager.cancel_job(job_id)

    if cancelled:
        return {"cancelled": True, "message": "Job cancelled"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled (already running or done)"
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "workers": job_manager.max_workers,
        "queue_size": len(job_manager.queued_order),
        "jobs_count": len(job_manager.jobs)
    }
