# Руководство по настройке для VPS

## Рекомендуемые параметры

### Для 1 vCPU (DigitalOcean Droplet $5-6/мес)
```python
MAX_WORKERS = 2
MAX_QUEUE = 200
JOB_TTL_MINUTES = 30
```

### Для 2 vCPU (DigitalOcean Droplet $12-16/мес)
```python
MAX_WORKERS = 4
MAX_QUEUE = 200
JOB_TTL_MINUTES = 30
```

### Для 4+ vCPU
```python
MAX_WORKERS = 6-8
MAX_QUEUE = 300
JOB_TTL_MINUTES = 30
```

## Развертывание

### 1. Подготовка сервера

```bash
# Обновление
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Python
sudo apt install python3 python3-pip python3-venv -y

# Создание пользователя
sudo useradd -m -s /bin/bash zig-runner
sudo su - zig-runner
```

### 2. Развертывание проекта

```bash
# Клонирование или копирование файлов
cd /opt
sudo git clone <repo-url> zig-exercise-runner
sudo chown -R zig-runner:zig-runner zig-exercise-runner
cd zig-exercise-runner

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Сборка Docker образа
make build-runner
```

### 3. Настройка systemd service

```bash
sudo nano /etc/systemd/system/zig-runner.service
```

Содержимое:
```ini
[Unit]
Description=Zig Exercise Runner
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=zig-runner
WorkingDirectory=/opt/zig-exercise-runner
Environment="PATH=/opt/zig-exercise-runner/venv/bin"
ExecStart=/opt/zig-exercise-runner/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zig-runner
sudo systemctl start zig-runner
sudo systemctl status zig-runner
```

### 4. Настройка Nginx (опционально, для HTTPS)

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
sudo nano /etc/nginx/sites-available/zig-runner
```

Содержимое:
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
        
        # Увеличение timeout для долгих запросов
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/zig-runner /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com
```

## Мониторинг

### Проверка health
```bash
curl http://localhost:8000/health
```

### Просмотр логов
```bash
sudo journalctl -u zig-runner -f
```

### Проверка Docker контейнеров
```bash
docker ps -a
docker stats
```

### Проверка queue size
```bash
curl http://localhost:8000/health | jq .queue_size
```

## Оптимизация производительности

### 1. Ограничение памяти

Если VPS имеет мало памяти (512MB-1GB), уменьшите MAX_QUEUE:
```python
MAX_QUEUE = 50  # вместо 200
```

### 2. Очистка старых контейнеров

Добавьте cron задачу:
```bash
sudo crontab -e
```

```cron
# Каждую ночь удалять остановленные контейнеры
0 3 * * * docker container prune -f

# Раз в неделю удалять неиспользуемые образы
0 4 * * 0 docker image prune -a -f
```

### 3. Мониторинг ресурсов

Используйте htop:
```bash
sudo apt install htop -y
htop
```

## Безопасность

### 1. Firewall (UFW)
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Ограничение по IP (если нужно)

Добавьте в FastAPI middleware или в Nginx:
```nginx
location / {
    allow 1.2.3.4;  # ваш IP
    deny all;
    # ...
}
```

## Траблшутинг

### Проблема: Docker не хватает памяти

**Решение:** Уменьшите ограничения в runner.py:
```python
mem_limit="256m",  # вместо "512m"
```

### Проблема: Много остановленных контейнеров

**Решение:** Проверьте логи:
```bash
docker ps -a | grep Exited
docker logs <container-id>
```

Возможно, нужно увеличить таймаут или ограничить количество воркеров.

### Проблема: Queue переполняется

**Решение:** Увеличьте MAX_QUEUE или уменьшите MAX_WORKERS для балансировки.

### Проблема: Ошибки компиляции Zig

**Решение:** Проверьте версию Zig в Dockerfile:
```dockerfile
ARG ZIG_VERSION=0.13.0
```

Обновите при необходимости и пересоберите:
```bash
make clean
make build-runner
sudo systemctl restart zig-runner
```

## Резервное копирование

### Бэкап задач
```bash
tar -czf tasks-backup-$(date +%Y%m%d).tar.gz tasks/
```

### Восстановление
```bash
tar -xzf tasks-backup-YYYYMMDD.tar.gz
```

## Масштабирование

Если нагрузки не хватает на одном VPS:

1. **Горизонтальное масштабирование:** Разверните несколько инстансов и используйте балансировщик нагрузки (Nginx + upstream).

2. **Добавление Redis:** Замените in-memory queue на Redis для распределенной обработки.

3. **Отдельная база данных:** Добавьте PostgreSQL для хранения результатов и статистики.
