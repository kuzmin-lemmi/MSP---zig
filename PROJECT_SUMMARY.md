# Краткий обзор проекта (Project Summary)

## Что это?

MVP+Queue система для проверки Zig кода с:
- **FastAPI Backend** - REST API
- **Docker Runner** - изолированное выполнение Zig 0.13.0
- **In-Memory Queue** - управление задачами без внешних БД
- **2-4 параллельных воркера** - стабильная работа на VPS

## Архитектура

```
Клиент → FastAPI → JobManager → Runner → Docker (Zig)
                    ↓
               Queue (FIFO)
```

## Основные файлы

### Backend (`backend/`)
- `main.py` - FastAPI приложение + API эндпоинты
- `job_manager.py` - Очередь + воркеры + TTL cleanup
- `runner.py` - Docker контейнеры + компиляция + тесты
- `models.py` - Pydantic модели (Request, Response, Job)
- `requirements.txt` - Зависимости Python

### Runner (`runner/`)
- `Dockerfile` - Zig 0.13.0 образ
- `build.sh` - Скрипт сборки

### Tasks (`tasks/`)
- Файловая система для задач
- `meta.json` - Метаданные
- `statement.md` - Условие
- `tests/*.in, *.out` - Тесты

### Документация
- `README.md` - Полная документация
- `QUICKSTART.md` - Быстрый старт за 5 минут
- `API_EXAMPLES.md` - Примеры curl запросов
- `VPS_GUIDE.md` - Настройка для VPS

## API Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/tasks` | Список задач |
| GET | `/tasks/{id}` | Детали задачи |
| POST | `/submit` | Отправить решение |
| GET | `/jobs/{id}` | Статус выполнения |
| DELETE | `/jobs/{id}` | Отменить задачу |
| GET | `/health` | Health check |

## Verdicts

- **OK** - Все тесты пройдены
- **WA** - Неверный ответ
- **CE** - Ошибка компиляции
- **RE** - Runtime error
- **TLE** - Time limit exceeded

## Конфигурация

```python
MAX_WORKERS = 2        # Параллельные воркеры
MAX_QUEUE = 200        # Размер очереди
JOB_TTL_MINUTES = 30   # Время хранения результатов
```

## Docker ограничения

- `--network none` - Без сети
- `--cpus=1` - 1 CPU
- `--memory=512m` - 512MB RAM
- `--pids-limit=128` - 128 процессов
- Таймаут: 5 секунд

## Как запустить?

```bash
# 1. Установить зависимости
pip install -r backend/requirements.txt

# 2. Собрать Docker образ
make build-runner

# 3. Запустить бэкенд
make run-backend

# 4. Проверить
curl http://localhost:8000/health
```

## Пример использования

```bash
# 1. Получить задачи
curl http://localhost:8000/tasks

# 2. Отправить решение
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { ... }",
    "mode": "check"
  }'

# 3. Проверить статус
curl http://localhost:8000/jobs/{job_id}
```

## Структура задачи

```
tasks/<task_id>/
├── meta.json           # Метаданные (title, limits)
├── statement.md        # Условие задачи
└── tests/
    ├── 01.in / 01.out
    ├── 02.in / 02.out
    └── ...
```

## Технологии

- **Backend**: Python 3.9+, FastAPI, asyncio
- **Runner**: Docker, Zig 0.13.0
- **Queue**: asyncio.Queue (in-memory)
- **Lock**: asyncio.Lock

## Безопасность

- Docker изоляция
- Ограничение ресурсов (CPU, RAM, PIDs)
- Без сети
- temp dirs с UUID
- Гарантированная очистка

## Производительность

- 2-4 воркера для 1-2 vCPU
- 200 задач в очереди
- TTL cleanup каждые 5 минут
- Graceful shutdown

## Что НЕ включено

- ❌ База данных (in-memory)
- ❌ Redis (asyncio.Queue)
- ❌ WebSocket (поллинг)
- ❌ Фронтенд (только API)
- ❌ Авторизация (MVP)
- ❌ Античитерство (MVP)

## Что можно добавить позже

- ✅ PostgreSQL для истории
- ✅ Redis для распределенной очереди
- ✅ WebSocket для real-time
- ✅ Авторизация (JWT/OAuth)
- ✅ Статистика и аналитика
- ✅ Рейтинг студентов

## Быстрый запуск (1 минута)

```bash
pip install -r backend/requirements.txt
make build-runner
make run-backend
curl http://localhost:8000/health
```

## Для VPS

Смотрите [VPS_GUIDE.md](VPS_GUIDE.md) для:
- systemd service
- Nginx + HTTPS
- Мониторинг
- Оптимизация
- Траблшутинг

## Для примеров

Смотрите [API_EXAMPLES.md](API_EXAMPLES.md) для:
- curl примеры
- Полный цикл
- Все verdicts
- Скрипты

## Для быстрого старта

Смотрите [QUICKSTART.md](QUICKSTART.md) для:
- Установка
- Запуск
- Проверка
- Добавление задач

## License

MIT (для использования в курсах)

## Контакты

Вопросы и предложения приветствуются!
