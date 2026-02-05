from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Verdict(str, Enum):
    CE = "compile_error"
    TLE = "time_limit_exceeded"
    RE = "runtime_error"
    WA = "wrong_answer"
    OK = "accepted"

class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"

class TaskMeta(BaseModel):
    id: str
    title: str
    module: str
    type: str = "io"
    time_limit_ms: int
    memory_mb: int
    starter_code: Optional[str] = None

class SubmitRequest(BaseModel):
    task_id: str
    code: str
    mode: str = "check"

class TestResult(BaseModel):
    test_num: int
    passed: bool
    expected: str
    actual: str
    time_ms: float

class JobResult(BaseModel):
    verdict: Verdict
    stdout: str
    stderr: str
    compile_log: str
    time_ms: float
    test_results: List[TestResult]

class JobStatus(BaseModel):
    job_id: str
    state: JobState
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    queue_position: Optional[int] = None
    running_for_ms: Optional[int] = None
    result: Optional[JobResult] = None
