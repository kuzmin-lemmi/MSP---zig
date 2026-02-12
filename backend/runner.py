import asyncio
import tempfile
import shutil
import os
import json
import time
from pathlib import Path
from typing import List, Tuple

try:
    from .models import Verdict, TestResult, JobResult
except ImportError:
    from models import Verdict, TestResult, JobResult

DEFAULT_PER_TEST_TIMEOUT_MS = 3000
DOCKER_MEMORY_LIMIT = "512m"
DOCKER_CPU_LIMIT = "1"
DOCKER_PIDS_LIMIT = "128"
DOCKER_TIMEOUT_EXIT_CODE = 124
DOCKER_NOT_FOUND_EXIT_CODE = 127
CONTAINER_GRACE_MS = 2000


class Runner:
    def __init__(self, docker_image: str, tasks_dir: str):
        self.image = docker_image
        self.tasks_dir = tasks_dir

    async def execute_job(
        self,
        task_id: str,
        code: str,
        mode: str = "check"
    ) -> JobResult:
        meta = self._load_task_meta(task_id)
        per_test_timeout_ms = int(meta.get("time_limit_ms", DEFAULT_PER_TEST_TIMEOUT_MS))
        compile_timeout_ms = max(10000, per_test_timeout_ms * 2)
        tests = self._load_tests(task_id)
        overall_timeout_ms = self._calculate_overall_timeout_ms(per_test_timeout_ms, len(tests))

        temp_dir = tempfile.mkdtemp(prefix=f"zig_job_{task_id}_")
        started_at = time.monotonic()

        try:
            compile_log, compile_time_ms, compile_stdout, compile_stderr, compile_exit = await self._compile(
                code,
                temp_dir,
                compile_timeout_ms
            )

            if compile_exit != 0:
                return JobResult(
                    verdict=Verdict.CE,
                    stdout=compile_stdout,
                    stderr=compile_stderr,
                    compile_log=compile_log,
                    time_ms=compile_time_ms,
                    test_results=[]
                )

            if mode == "run":
                stdout, stderr, exit_code, exec_time = await self._run_binary(
                    temp_dir,
                    "",
                    per_test_timeout_ms + CONTAINER_GRACE_MS
                )
                verdict = Verdict.OK if exit_code == 0 else (
                    Verdict.TLE if exit_code == DOCKER_TIMEOUT_EXIT_CODE else Verdict.RE
                )
                return JobResult(
                    verdict=verdict,
                    stdout=stdout,
                    stderr=stderr,
                    compile_log=compile_log,
                    time_ms=compile_time_ms + exec_time,
                    test_results=[]
                )

            test_results = []
            total_time_ms = compile_time_ms

            for test_num, (input_data, expected_output) in enumerate(tests, 1):
                if self._is_overall_timeout(started_at, overall_timeout_ms):
                    return JobResult(
                        verdict=Verdict.TLE,
                        stdout="",
                        stderr="",
                        compile_log=compile_log,
                        time_ms=total_time_ms,
                        test_results=test_results
                    )

                stdout, stderr, exit_code, exec_time = await self._run_binary(
                    temp_dir,
                    input_data,
                    per_test_timeout_ms + CONTAINER_GRACE_MS
                )
                total_time_ms += exec_time

                passed = self._compare_output(stdout, expected_output)
                test_results.append(TestResult(
                    test_num=test_num,
                    passed=passed,
                    expected=expected_output,
                    actual=stdout,
                    time_ms=exec_time
                ))

                if exit_code != 0:
                    verdict = Verdict.TLE if exit_code == DOCKER_TIMEOUT_EXIT_CODE else Verdict.RE
                    return JobResult(
                        verdict=verdict,
                        stdout=stdout,
                        stderr=stderr,
                        compile_log=compile_log,
                        time_ms=total_time_ms,
                        test_results=test_results
                    )

                if not passed:
                    return JobResult(
                        verdict=Verdict.WA,
                        stdout=stdout,
                        stderr=stderr,
                        compile_log=compile_log,
                        time_ms=total_time_ms,
                        test_results=test_results
                    )

            return JobResult(
                verdict=Verdict.OK,
                stdout=test_results[-1].actual if test_results else "",
                stderr="",
                compile_log=compile_log,
                time_ms=total_time_ms,
                test_results=test_results
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _compile(self, code: str, work_dir: str, timeout_ms: int) -> Tuple[str, float, str, str, int]:
        code_path = os.path.join(work_dir, "main.zig")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)

        command = [
            "zig",
            "build-exe",
            "main.zig",
            "-O",
            "ReleaseSmall",
            "-femit-bin=main"
        ]

        stdout, stderr, exit_code, duration_ms = await self._run_docker_command(
            command=command,
            work_dir=work_dir,
            input_data="",
            timeout_ms=timeout_ms
        )

        compile_log = stderr if exit_code != 0 else ""
        return compile_log, duration_ms, stdout, stderr, exit_code

    async def _run_binary(
        self,
        work_dir: str,
        input_data: str,
        timeout_ms: int
    ) -> Tuple[str, str, int, float]:
        command = ["/workspace/main"]
        return await self._run_docker_command(
            command=command,
            work_dir=work_dir,
            input_data=input_data,
            timeout_ms=timeout_ms
        )

    async def _run_docker_command(
        self,
        command: List[str],
        work_dir: str,
        input_data: str,
        timeout_ms: int
    ) -> Tuple[str, str, int, float]:
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            DOCKER_CPU_LIMIT,
            "--memory",
            DOCKER_MEMORY_LIMIT,
            "--pids-limit",
            DOCKER_PIDS_LIMIT,
            "-v",
            f"{work_dir}:/workspace",
            "-w",
            "/workspace",
            self.image
        ] + command

        start_time = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input_data.encode("utf-8")),
                    timeout=timeout_ms / 1000
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                duration_ms = (time.monotonic() - start_time) * 1000
                return "", "", DOCKER_TIMEOUT_EXIT_CODE, duration_ms

            duration_ms = (time.monotonic() - start_time) * 1000
            stdout = stdout_bytes.decode("utf-8", errors="ignore")
            stderr = stderr_bytes.decode("utf-8", errors="ignore")
            returncode = proc.returncode if proc.returncode is not None else DOCKER_TIMEOUT_EXIT_CODE
            return stdout, stderr, returncode, duration_ms
        except FileNotFoundError:
            duration_ms = (time.monotonic() - start_time) * 1000
            return "", "Docker executable not found", DOCKER_NOT_FOUND_EXIT_CODE, duration_ms

    def _compare_output(self, actual: str, expected: str) -> bool:
        actual_normalized = actual.replace("\r", "").rstrip(" \n")
        expected_normalized = expected.replace("\r", "").rstrip(" \n")
        return actual_normalized == expected_normalized

    def _calculate_overall_timeout_ms(self, per_test_timeout_ms: int, test_count: int) -> int:
        base = per_test_timeout_ms * max(1, test_count)
        return base + 10000

    def _is_overall_timeout(self, started_at: float, overall_timeout_ms: int) -> bool:
        elapsed_ms = (time.monotonic() - started_at) * 1000
        return elapsed_ms > overall_timeout_ms

    def _load_task_meta(self, task_id: str) -> dict:
        meta_path = os.path.join(self.tasks_dir, task_id, "meta.json")
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_tests(self, task_id: str) -> List[Tuple[str, str]]:
        test_dir = os.path.join(self.tasks_dir, task_id, "tests")
        tests = []
        in_files = sorted(Path(test_dir).glob("*.in"))

        for in_file in in_files:
            out_file = in_file.with_suffix(".out")
            if out_file.exists():
                with open(in_file, encoding="utf-8") as f:
                    input_data = f.read()
                with open(out_file, encoding="utf-8") as f:
                    expected_output = f.read()
                tests.append((input_data, expected_output))

        return tests
