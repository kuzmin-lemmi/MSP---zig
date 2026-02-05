import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models import JobState, JobStatus, JobResult
from runner import Runner

class Job:
    def __init__(self, job_id: str, request: dict):
        self.id = job_id
        self.state = JobState.QUEUED
        self.created_at = datetime.now()
        self.started_at = None
        self.finished_at = None
        self.request = request
        self.result = None
        self.error = None

class JobManager:
    def __init__(
        self,
        max_workers: int = 2,
        max_queue: int = 200,
        job_ttl_minutes: int = 30
    ):
        self.max_workers = max_workers
        self.max_queue = max_queue
        self.job_ttl = timedelta(minutes=job_ttl_minutes)
        
        self.queue = asyncio.Queue(maxsize=max_queue)
        self.jobs = {}
        self.lock = asyncio.Lock()
        
        self.workers = []
        self.running = False
        self.runner: Optional[Runner] = None
    
    async def start(self):
        if self.running:
            return
        
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self.max_workers)
        ]
        
        asyncio.create_task(self._ttl_cleanup_loop())
    
    async def stop(self):
        self.running = False
        
        for _ in range(self.max_workers):
            self.queue.put_nowait(None)
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    async def submit(self, task_id: str, code: str, mode: str = "check") -> str:
        if self.queue.qsize() >= self.max_queue:
            raise ValueError("Queue is full")
        
        job_id = str(uuid.uuid4())
        request = {"task_id": task_id, "code": code, "mode": mode}
        job = Job(job_id, request)
        
        async with self.lock:
            self.jobs[job_id] = job
        
        await self.queue.put(job_id)
        return job_id
    
    async def get_job(self, job_id: str):
        async with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            
            queue_position = None
            running_for_ms = None
            
            if job.state == JobState.QUEUED:
                queue_position = self._get_queue_position(job_id)
            elif job.state == JobState.RUNNING and job.started_at:
                running_for_ms = int(
                    (datetime.now() - job.started_at).total_seconds() * 1000
                )
            
            return JobStatus(
                job_id=job.id,
                state=job.state,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                queue_position=queue_position,
                running_for_ms=running_for_ms,
                result=job.result
            )
    
    async def cancel_job(self, job_id: str) -> bool:
        async with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.state != JobState.QUEUED:
                return False
            
            job.state = JobState.ERROR
            job.finished_at = datetime.now()
            job.error = "Cancelled by user"
            
            new_queue = asyncio.Queue(maxsize=self.max_queue)
            while not self.queue.empty():
                try:
                    item = self.queue.get_nowait()
                    if item != job_id:
                        new_queue.put_nowait(item)
                except asyncio.QueueEmpty:
                    break
            
            self.queue = new_queue
            del self.jobs[job_id]
            return True
    
    async def _worker_loop(self, worker_id: int):
        while self.running:
            try:
                job_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                if job_id is None:
                    break
                
                async with self.lock:
                    job = self.jobs.get(job_id)
                
                if not job:
                    continue
                
                job.state = JobState.RUNNING
                job.started_at = datetime.now()
                
                try:
                    result = await self.runner.execute_job(
                        job.request["task_id"],
                        job.request["code"],
                        job.request["mode"]
                    )
                    
                    job.result = result
                    job.state = JobState.DONE
                    
                except Exception as e:
                    job.state = JobState.ERROR
                    job.error = str(e)
                
                finally:
                    job.finished_at = datetime.now()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
    
    async def _ttl_cleanup_loop(self):
        while self.running:
            await asyncio.sleep(300)
            
            async with self.lock:
                now = datetime.now()
                to_delete = [
                    job_id for job_id, job in self.jobs.items()
                    if job.finished_at and (now - job.finished_at) > self.job_ttl
                ]
                
                for job_id in to_delete:
                    del self.jobs[job_id]
    
    def _get_queue_position(self, job_id: str) -> int:
        position = 0
        for item in list(self.queue._queue):
            if item == job_id:
                return position
            position += 1
        return position
