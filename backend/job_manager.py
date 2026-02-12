import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

try:
    from .models import JobState, JobStatus, JobResult
    from .runner import Runner
except ImportError:
    from models import JobState, JobStatus, JobResult
    from runner import Runner

DEFAULT_AVG_DURATION_MS = 3000
RECENT_DURATION_WINDOW = 20


class Job:
    def __init__(self, job_id: str, request: dict):
        self.id = job_id
        self.state = JobState.QUEUED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.request = request
        self.result: Optional[JobResult] = None
        self.error_message: Optional[str] = None


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

        self.queue: asyncio.Queue = asyncio.Queue()
        self.jobs: Dict[str, Job] = {}
        self.queued_order: deque[str] = deque()
        self.queued_set: set[str] = set()
        self.recent_durations: deque[float] = deque(maxlen=RECENT_DURATION_WINDOW)
        self.lock = asyncio.Lock()

        self.workers: List[asyncio.Task] = []
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
        async with self.lock:
            if len(self.queued_order) >= self.max_queue:
                raise ValueError("Queue is full")

            job_id = str(uuid.uuid4())
            request = {"task_id": task_id, "code": code, "mode": mode}
            job = Job(job_id, request)
            self.jobs[job_id] = job
            self.queued_order.append(job_id)
            self.queued_set.add(job_id)

        await self.queue.put(job_id)
        return job_id

    async def get_job(self, job_id: str) -> Optional[JobStatus]:
        async with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None

            queue_position = None
            eta_ms = None
            running_for_ms = None

            if job.state == JobState.QUEUED:
                queue_position = self._get_queue_position(job_id)
                eta_ms = self._estimate_eta_ms(queue_position)
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
                eta_ms=eta_ms,
                running_for_ms=running_for_ms,
                result=job.result,
                error_message=job.error_message
            )

    async def cancel_job(self, job_id: str) -> bool:
        async with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.state != JobState.QUEUED:
                return False

            job.state = JobState.ERROR
            job.finished_at = datetime.now()
            job.error_message = "Cancelled by user"

            if job_id in self.queued_set:
                self.queued_set.remove(job_id)
            if job_id in self.queued_order:
                self.queued_order.remove(job_id)

            return True

    async def _worker_loop(self, worker_id: int):
        while self.running:
            try:
                job_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                if job_id is None:
                    break

                async with self.lock:
                    job = self.jobs.get(job_id)
                    if not job or job.state != JobState.QUEUED:
                        continue

                    job.state = JobState.RUNNING
                    job.started_at = datetime.now()
                    if job_id in self.queued_set:
                        self.queued_set.remove(job_id)
                    if job_id in self.queued_order:
                        self.queued_order.remove(job_id)

                try:
                    if not self.runner:
                        raise RuntimeError("Runner is not initialized")

                    result = await self.runner.execute_job(
                        job.request["task_id"],
                        job.request["code"],
                        job.request["mode"]
                    )

                    async with self.lock:
                        job.result = result
                        job.state = JobState.DONE
                        job.finished_at = datetime.now()
                        self._record_duration(job)

                except Exception as e:
                    async with self.lock:
                        job.state = JobState.ERROR
                        job.error_message = str(e)
                        job.finished_at = datetime.now()
                        self._record_duration(job)

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
                    if job_id in self.queued_set:
                        self.queued_set.remove(job_id)
                    if job_id in self.queued_order:
                        self.queued_order.remove(job_id)
                    del self.jobs[job_id]

    def _get_queue_position(self, job_id: str) -> int:
        try:
            return list(self.queued_order).index(job_id)
        except ValueError:
            return 0

    def _estimate_eta_ms(self, queue_position: int) -> int:
        avg_duration = self._average_duration_ms()
        return int((queue_position + 1) * avg_duration / max(1, self.max_workers))

    def _average_duration_ms(self) -> float:
        if not self.recent_durations:
            return DEFAULT_AVG_DURATION_MS
        return sum(self.recent_durations) / len(self.recent_durations)

    def _record_duration(self, job: Job) -> None:
        if not job.started_at or not job.finished_at:
            return
        duration_ms = (job.finished_at - job.started_at).total_seconds() * 1000
        self.recent_durations.append(duration_ms)
