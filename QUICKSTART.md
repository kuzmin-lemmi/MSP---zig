# Быстрый старт (Quick Start)

## Локальный запуск за 5 минут

### Требования
- Python 3.9+
- Docker
- Git

### 1. Установка зависимостей

```bash
# Установка Python зависимостей
pip install -r backend/requirements.txt
```

### 2. Сборка Docker образа

```bash
make build-runner
```

Или вручную:
```bash
cd runner && bash build.sh
```

### 3. Запуск бэкенда

```bash
make run-backend
```

Или вручную:
```bash
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Сервер запустится на http://localhost:8000

### 4. Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Список задач
curl http://localhost:8000/tasks
```

## Пример использования

### 1. Получить список задач

```bash
curl http://localhost:8000/tasks
```

Ответ:
```json
[
  {
    "id": "hello-world",
    "title": "Привет, мир!",
    "module": "zig-basics",
    "type": "io",
    "time_limit_ms": 3000,
    "memory_mb": 128
  }
]
```

### 2. Получить детали задачи

```bash
curl http://localhost:8000/tasks/hello-world
```

### 3. Отправить решение (OK)

```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }'
```

Ответ:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Проверить статус

```bash
curl http://localhost:8000/jobs/{job_id}
```

Ответ (завершено):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "done",
  "created_at": "2024-01-01T12:00:00",
  "started_at": "2024-01-01T12:00:01",
  "finished_at": "2024-01-01T12:00:02",
  "queue_position": null,
  "running_for_ms": null,
  "result": {
    "verdict": "accepted",
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

## Пример полного цикла (bash скрипт)

```bash
#!/bin/bash

# Отправка решения
RESPONSE=$(curl -s -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }')

JOB_ID=$(echo $RESPONSE | grep -oP '(?<="job_id": ")[^"]*')
echo "Job ID: $JOB_ID"

# Поллинг статуса
while true; do
  STATUS=$(curl -s http://localhost:8000/jobs/$JOB_ID | grep -oP '(?<="state": ")[^"]*')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ]; then
    curl -s http://localhost:8000/jobs/$JOB_ID | jq
    break
  fi
  
  sleep 1
done
```

## Добавление новой задачи

### 1. Создать директорию задачи

```bash
mkdir tasks/my-task
mkdir tasks/my-task/tests
```

### 2. Создать meta.json

```json
{
  "id": "my-task",
  "title": "Моя задача",
  "module": "my-module",
  "type": "io",
  "time_limit_ms": 1000,
  "memory_mb": 64
}
```

### 3. Создать statement.md

```markdown
# Моя задача

Напишите программу, которая...

## Пример ввода:
```
42
```

## Пример вывода:
```
42 * 2 = 84
```
```

### 4. Создать тесты

```bash
# Тест 1
echo "" > tasks/my-task/tests/01.in
echo "Hello, World!" > tasks/my-task/tests/01.out

# Тест 2 (если нужно)
echo "42" > tasks/my-task/tests/02.in
echo "84" > tasks/my-task/tests/02.out
```

### 5. Проверить задачу

```bash
# Список задач должен содержать новую задачу
curl http://localhost:8000/tasks

# Отправить решение для проверки
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "my-task",
    "code": "ваш код",
    "mode": "check"
  }'
```

## Настройка параметров

Измените параметры в `backend/main.py`:

```python
job_manager = JobManager(
    max_workers=2,        # Количество параллельных воркеров
    max_queue=200,        # Максимальный размер очереди
    job_ttl_minutes=30    # Время хранения результатов
)
```

## Очистка

```bash
make clean
```

Или вручную:
```bash
docker rmi zig-runner:0.13.0
rm -rf backend/__pycache__ backend/.pytest_cache
```

## Следующие шаги

- Читайте [README.md](README.md) для полной документации
- Читайте [API_EXAMPLES.md](API_EXAMPLES.md) для больше примеров
- Читайте [VPS_GUIDE.md](VPS_GUIDE.md) для развертывания на сервере

## Проблемы?

### Docker не найден
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Выйдите и войдите снова
```

### Ошибка: "Queue is full"
Увеличьте `MAX_QUEUE` в `backend/main.py`

### Ошибка компиляции Zig
Проверьте версию Zig в `runner/Dockerfile`:
```dockerfile
ARG ZIG_VERSION=0.13.0
```

### Ошибка: "Task not found"
Убедитесь, что директория задачи существует и содержит `meta.json`
