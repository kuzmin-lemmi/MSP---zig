import docker
import asyncio
import tempfile
import shutil
import os
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional
from models import Verdict, TestResult, JobResult

class Runner:
    def __init__(self, docker_image: str = "zig-runner:0.13.0"):
        self.client = docker.from_env()
        self.image = docker_image
    
    async def execute_job(
        self, 
        task_id: str, 
        code: str, 
        mode: str = "check"
    ) -> JobResult:
        meta = self._load_task_meta(task_id)
        temp_dir = tempfile.mkdtemp(prefix=f"zig_job_{task_id}_")
        
        try:
            compile_log = await self._compile(code, temp_dir)
            if compile_log:
                return JobResult(
                    verdict=Verdict.CE,
                    stdout="", stderr="",
                    compile_log=compile_log,
                    time_ms=0, test_results=[]
                )
            
            tests = self._load_tests(task_id)
            test_results = []
            total_time = 0
            
            for test_num, (input_data, expected_output) in enumerate(tests, 1):
                stdout, stderr, exit_code, exec_time = await self._run_test(
                    temp_dir, input_data, meta.time_limit_ms
                )
                
                passed = self._compare_output(stdout, expected_output)
                test_results.append(TestResult(
                    test_num=test_num,
                    passed=passed,
                    expected=expected_output,
                    actual=stdout,
                    time_ms=exec_time
                ))
                
                total_time += exec_time
                
                if exit_code != 0:
                    verdict = Verdict.TLE if exit_code == 124 else Verdict.RE
                    return JobResult(
                        verdict=verdict,
                        stdout=stdout, stderr=stderr,
                        compile_log="",
                        time_ms=total_time,
                        test_results=test_results
                    )
            
            all_passed = all(t.passed for t in test_results)
            verdict = Verdict.OK if all_passed else Verdict.WA
            
            return JobResult(
                verdict=verdict,
                stdout=test_results[-1].actual if test_results else "",
                stderr="",
                compile_log="",
                time_ms=total_time,
                test_results=test_results
            )
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _compile(self, code: str, work_dir: str) -> Optional[str]:
        code_path = os.path.join(work_dir, "main.zig")
        with open(code_path, "w") as f:
            f.write(code)
        
        try:
            container = self.client.containers.run(
                self.image,
                command="zig build-exe main.zig -O ReleaseSmall",
                volumes={work_dir: {"bind": "/workspace", "mode": "rw"}},
                network_disabled=True,
                cpuset_cpus="0",
                mem_limit="128m",
                pids_limit=64,
                timeout=10,
                remove=True,
                stderr=True,
                stdout=True
            )
            return None
        except docker.errors.ContainerError as e:
            return e.stderr.decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Compilation error: {str(e)}"
    
    async def _run_test(
        self, 
        work_dir: str, 
        input_data: str, 
        time_limit_ms: int
    ) -> Tuple[str, str, int, float]:
        timeout_sec = min(time_limit_ms / 1000 + 1, 5)
        container = None
        
        try:
            container = self.client.containers.create(
                self.image,
                command="./main",
                volumes={work_dir: {"bind": "/workspace", "mode": "ro"}},
                network_disabled=True,
                cpuset_cpus="0",
                mem_limit="512m",
                pids_limit=128,
                detach=True
            )
            
            start_time = time.time()
            container.start()
            result = container.wait(timeout=timeout_sec)
            exec_time = (time.time() - start_time) * 1000
            
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="ignore")
            container.remove()
            
            stdout = logs
            stderr = ""
            exit_code = result["StatusCode"]
            
            return stdout, stderr, exit_code, exec_time
            
        except Exception as e:
            if container:
                container.remove(force=True)
            return "", "", 124, timeout_sec * 1000
    
    def _compare_output(self, actual: str, expected: str) -> bool:
        actual_normalized = actual.replace("\r", "").rstrip(" \n")
        expected_normalized = expected.replace("\r", "").rstrip(" \n")
        return actual_normalized == expected_normalized
    
    def _load_task_meta(self, task_id: str):
        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
        meta_path = os.path.join(tasks_dir, task_id, "meta.json")
        with open(meta_path) as f:
            return json.load(f)
    
    def _load_tests(self, task_id: str) -> List[Tuple[str, str]]:
        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
        test_dir = os.path.join(tasks_dir, task_id, "tests")
        
        tests = []
        in_files = sorted(Path(test_dir).glob("*.in"))
        
        for in_file in in_files:
            out_file = in_file.with_suffix(".out")
            if out_file.exists():
                with open(in_file) as f:
                    input_data = f.read()
                with open(out_file) as f:
                    expected_output = f.read()
                tests.append((input_data, expected_output))
        
        return tests
