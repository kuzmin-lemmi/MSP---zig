# Zig Exercise Runner

MVP+Queue для проверки Zig кода на внешней платформе.

## Архитектура

- **FastAPI Backend**: REST API + JobManager с in-memory очередью
- **Docker Runner**: изолированное выполнение Zig 0.13.0 кода
- **Task System**: файловая система для задач (tasks/<id>/)
- **Queue**: FIFO, bounded, без внешних БД

## Требования

- Python 3.9+
- Docker
- Zig (для локальной разработки, не обязателен на сервере)

## Установка

1. Клонировать проект
2. Установить зависимости:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Собрать Docker образ:
   ```bash
   make build-runner
   ```

4. Запустить бэкенд:
   ```bash
   make run-backend
   ```

## API

### GET /tasks
Возвращает список всех задач.

```bash
curl http://localhost:8000/tasks
```

### GET /tasks/{id}
Возвращает statement и meta задачи.

```bash
curl http://localhost:8000/tasks/hello-world
```

### POST /submit
Отправляет решение на проверку. Возвращает `job_id`.

```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }'
```

### GET /jobs/{job_id}
Возвращает статус выполнения задачи.

```bash
curl http://localhost:8000/jobs/{job_id}
```

Ответ:
```json
{
  "job_id": "...",
  "state": "done",
  "created_at": "2024-01-01T00:00:00",
  "started_at": "2024-01-01T00:00:01",
  "finished_at": "2024-01-01T00:00:02",
  "queue_position": null,
  "running_for_ms": null,
  "result": {
    "verdict": "OK",
    "stdout": "Hello, World!",
    "stderr": "",
    "compile_log": "",
    "time_ms": 123.45,
    "test_results": [
      {
        "test_num": 1,
        "passed": true,
        "expected": "Hello, World!",
        "actual": "Hello, World!",
        "time_ms": 123.45
      }
    ]
  }
}
```

### DELETE /jobs/{job_id}
Отменяет задачу если она в очереди.

```bash
curl -X DELETE http://localhost:8000/jobs/{job_id}
```

### GET /health
Проверка здоровья.

```bash
curl http://localhost:8000/health
```

## Verdicts

- **CE** (Compile Error): ошибка компиляции
- **TLE** (Time Limit Exceeded): превышение времени
- **RE** (Runtime Error): ошибка выполнения (exit code != 0)
- **WA** (Wrong Answer): неверный ответ
- **OK** (Accepted): все тесты пройдены

## Формат задач

```
tasks/<task_id>/
├── meta.json
├── statement.md
└── tests/
    ├── 01.in
    ├── 01.out
    ├── 02.in
    └── 02.out
```

### meta.json
```json
{
  "id": "hello-world",
  "title": "Привет, мир!",
  "module": "zig-basics",
  "type": "io",
  "time_limit_ms": 3000,
  "memory_mb": 128
}
```

## Конфигурация

Параметры через переменные окружения:

```bash
MAX_WORKERS=2
MAX_QUEUE=200
JOB_TTL_MINUTES=30
RUNNER_IMAGE=zig-runner:0.13.0
TASKS_DIR=./tasks
CODE_MAX_BYTES=131072
```

### Настройка для VPS

**1 vCPU:**
```python
MAX_WORKERS = 2
```

**2 vCPU:**
```python
MAX_WORKERS = 4
```

## Docker ограничения

- `--network none`: отключение сети
- `--cpus=1`: ограничение CPU
- `--memory=512m`: ограничение памяти
- `--pids-limit=128`: ограничение процессов
- Таймаут выполнения: 3 секунды на тест + общий таймаут на задачу

## Команды

```bash
make build-runner    # Собрать Docker образ
make run-backend      # Запустить бэкенд
make clean           # Очистка
make test            # Проверить health
make smoke           # E2E smoke-тест verdicts
```

## systemd service

```ini
[Unit]
Description=Zig Exercise Runner
After=network.target

[Service]
Type=simple
User=zig-runner
WorkingDirectory=/opt/zig-exercise-runner
ExecStart=/usr/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
