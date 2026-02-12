#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "[1/7] health"
curl -sS "$BASE_URL/health" | python -m json.tool

echo "[2/7] tasks"
curl -sS "$BASE_URL/tasks" | python -m json.tool

submit() {
  local payload="$1"
  curl -sS -X POST "$BASE_URL/submit" \
    -H "Content-Type: application/json" \
    -d "$payload" | python -c "import json,sys; print(json.load(sys.stdin)['job_id'])"
}

wait_job() {
  local job_id="$1"
  for _ in $(seq 1 60); do
    body=$(curl -sS "$BASE_URL/jobs/$job_id")
    state=$(python -c "import json,sys;print(json.load(sys.stdin)['state'])" <<< "$body")
    if [[ "$state" == "done" || "$state" == "error" ]]; then
      echo "$body"
      return
    fi
    sleep 0.4
  done
  echo "timeout waiting job $job_id" >&2
  exit 1
}

echo "[3/7] OK verdict"
JOB_OK=$(submit '{"task_id":"hello-world","code":"const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }","mode":"check"}')
wait_job "$JOB_OK" | python -m json.tool

echo "[4/7] WA verdict"
JOB_WA=$(submit '{"task_id":"hello-world","code":"const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"WRONG\", .{}); }","mode":"check"}')
wait_job "$JOB_WA" | python -m json.tool

echo "[5/7] CE verdict"
JOB_CE=$(submit '{"task_id":"hello-world","code":"const std = @import(\"std\"); pub fn main() !void { this is bad zig }","mode":"check"}')
wait_job "$JOB_CE" | python -m json.tool

echo "[6/7] RE verdict"
JOB_RE=$(submit '{"task_id":"hello-world","code":"pub fn main() !void { @panic(\"boom\"); }","mode":"check"}')
wait_job "$JOB_RE" | python -m json.tool

echo "[7/7] TLE verdict"
JOB_TLE=$(submit '{"task_id":"hello-world","code":"pub fn main() !void { while (true) {} }","mode":"check"}')
wait_job "$JOB_TLE" | python -m json.tool

echo "Smoke test finished"
