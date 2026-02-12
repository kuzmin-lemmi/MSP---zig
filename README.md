# 🦎 Zig Exercise Runner

Полный тренажёр Zig для курса с фронтендом и очередью задач.

---

## 🏗 Архитектура

```
┌─────────────┐     ┌─────────────┐
│   Stepik    │────▶ HTTP     │   Frontend    │
│  (ссылки)  │             │              │
│             │◀──── HTTP     │              │
└─────────────┘     └─────────────┘     └─────────────┘
                      │
                Zig Exercise Runner
               (FastAPI + Docker)
```

### Backend
- FastAPI (Python) с JobManager
- Docker Runner для Zig 0.13.0
- In-memory FIFO очередь
- 2-4 параллельных воркера

### Frontend  
- React 18 + TypeScript
- Список задач, редактор кода, результаты
- Автоматический поллинг статуса

---

## 🚀 Быстрый старт (10 минут)

### 1. Запуск Backend

```bash
# Установка зависимостей
pip install -r backend/requirements.txt

# Сборка Docker образа
docker build -t zig-runner:0.13.0 runner

# Запуск сервера
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Проверка:**
```bash
curl http://127.0.0.1:8000/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "workers": 2,
  "queue_size": 0,
  "jobs_count": 0
}
```

### 2. Запуск Frontend

```bash
# Установка зависимостей
cd frontend
npm install

# Запуск
npm run dev
```

Frontend доступен на http://localhost:5173

---

## 📡 API

### GET /tasks
Список всех задач.

```bash
curl http://127.0.0.1:8000/tasks
```

### GET /tasks/{id}
Условие и метаданные задачи.

```bash
curl http://127.0.0.1:8000/tasks/hello-world
```

### POST /submit
Отправить решение. Возвращает `job_id`.

```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }'
```

### GET /jobs/{job_id}
Статус выполнения.

```bash
curl http://127.0.0.1:8000/jobs/{job_id}
```

**Ответ:**
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
    "verdict": "accepted",
    "stdout": "Hello, World!",
    "stderr": "",
    "compile_log": "",
    "time_ms": 123.45,
    "test_results": [...]
  }
}
```

### DELETE /jobs/{job_id}
Отмена queued задач.

```bash
curl -X DELETE http://127.0.0.1:8000/jobs/{job_id}
```

---

## ✅ Verdicts

- **OK** — все тесты пройдены
- **WA** — неверный ответ
- **CE** — ошибка компиляции
- **RE** — runtime error
- **TLE** — timeout

---

## 📋 Добавление задачи

Структура:
```text
tasks/<task_id>/
  statement.md
  meta.json
  tests/
    01.in
    01.out
    02.in
    02.out
```

**meta.json:**
```json
{
  "id": "sum-two",
  "title": "Сумма двух чисел",
  "module": "basics",
  "type": "io",
  "time_limit_ms": 3000,
  "memory_mb": 128
}
```

После добавления — задача сразу в `GET /tasks`.

---

## ⚙ Конфигурация

Env переменные (для backend):
```bash
export MAX_WORKERS=2
export MAX_QUEUE=200
export JOB_TTL_MINUTES=30
export RUNNER_IMAGE=zig-runner:0.13.0
export TASKS_DIR=./tasks
export CODE_MAX_BYTES=131072
```

**VPS настройки:**

1 vCPU: `MAX_WORKERS=2`
2 vCPU: `MAX_WORKERS=4`

---

## 🐳 Docker ограничения

- `--network none` — без сети
- `--cpus=1` — 1 CPU
- `--memory=512m` — 512MB RAM
- `--pids-limit=128` — 128 процессов
- Таймаут: 3s на тест + общий таймаут

---

## 🔧 Команды

```bash
make build-runner    # Собрать Docker образ
make run-backend      # Запустить backend
make clean           # Очистка
make smoke           # E2E тест verdicts
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Структура проекта

```
zig-exercise-runner/
├── backend/
│   ├── main.py              # FastAPI + API
│   ├── job_manager.py       # Очередь + воркеры
│   ├── runner.py            # Docker runner
│   ├── models.py            # Модели
│   └── requirements.txt      # Зависимости
├── runner/
│   ├── Dockerfile           # Zig 0.13.0 образ
│   └── build.sh            # Сборка
├── tasks/                  # Задачи
│   └── hello-world/       # Пример
│       ├── meta.json
│       ├── statement.md
│       └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # React компоненты
│   │   │   ├── CodeEditor.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskView.tsx
│   │   │   └── ResultView.tsx
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── main.tsx
│   ├── package.json
│   └── index.html
├── scripts/
│   └── smoke_test.sh        # Автотест
├── Makefile
└── README.md
```

---

## 👨‍💻 Пример работы студента

1. Открыть фронтенд: http://localhost:5173
2. Выбрать задачу из списка
3. Написать код (есть пример)
4. Нажать "Check"
5. Получить `job_id`
6. Дождаться `state: "done"`
7. Посмотреть результаты (verdict, stdout, stderr)

---

## 🖥 Развертывание на VPS

### systemd service
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

### Nginx (HTTPS)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

---

## 📝 Frontend

**Технологии:** React 18 + TypeScript + Vite

**Компоненты:**
- `CodeEditor` — редактор Zig кода
- `TaskList` — список задач
- `TaskView` — условие задачи
- `ResultView` — результаты тестов

---

## 🧪 Тестирование

Автоматическое тестирование всех verdicts:

```bash
make smoke
```

Тестируемые сценарии:
- ✅ OK verdict
- ❌ WA verdict
- ⚠️ CE verdict
- 💥 RE verdict
- ⏱️ TLE verdict

---

## 📄 Лицензия

MIT (для использования в курсах)
