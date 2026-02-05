from fastapi import FastAPI, HTTPException, status
from pathlib import Path
import os
import json
from typing import List
from models import TaskMeta, SubmitRequest, JobStatus
from job_manager import JobManager
from runner import Runner

app = FastAPI(title="Zig Exercise Runner")

job_manager = JobManager(max_workers=2)
runner = Runner()
job_manager.runner = runner

TASKS_DIR = os.path.join(os.path.dirname(__file__), "..", "tasks")

@app.on_event("startup")
async def startup():
    await job_manager.start()

@app.on_event("shutdown")
async def shutdown():
    await job_manager.stop()

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
                with open(meta_file) as f:
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
    
    with open(statement_file) as f:
        statement = f.read()
    
    with open(meta_file) as f:
        meta = json.load(f)
    
    return {"statement": statement, "meta": TaskMeta(**meta)}

@app.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_solution(request: SubmitRequest):
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
        "queue_size": job_manager.queue.qsize(),
        "jobs_count": len(job_manager.jobs)
    }
