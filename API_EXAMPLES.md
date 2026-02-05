# Тестовые примеры для API

## 1. Проверка здоровья
```bash
curl http://localhost:8000/health
```

## 2. Список задач
```bash
curl http://localhost:8000/tasks
```

## 3. Получение задачи
```bash
curl http://localhost:8000/tasks/hello-world
```

## 4. Отправка решения (OK)
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }'
```

## 5. Отправка решения (WA - неправильный ответ)
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, Wrong!\", .{}); }",
    "mode": "check"
  }'
```

## 6. Отправка решения (CE - ошибка компиляции)
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { invalid syntax }",
    "mode": "check"
  }'
```

## 7. Проверка статуса (замените {job_id} на полученный)
```bash
curl http://localhost:8000/jobs/{job_id}
```

## 8. Отмена задачи (если в очереди)
```bash
curl -X DELETE http://localhost:8000/jobs/{job_id}
```

## Пример полного цикла (скрипт)
```bash
# Отправляем решение
JOB_ID=$(curl -s -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "hello-world",
    "code": "const std = @import(\"std\"); pub fn main() !void { try std.io.getStdOut().writer().print(\"Hello, World!\", .{}); }",
    "mode": "check"
  }' | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Поллинг статуса
while true; do
  STATUS=$(curl -s http://localhost:8000/jobs/$JOB_ID | jq -r '.state')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ]; then
    curl -s http://localhost:8000/jobs/$JOB_ID | jq
    break
  fi
  
  sleep 1
done
```
