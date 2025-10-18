# 🚀 Инструкция по деплою

## Быстрый деплой (локально или на сервере)

### Автоматический деплой

Просто запустите:

```bash
./deploy.sh
```

Скрипт автоматически:
1. Подтянет последние изменения из git
2. Остановит текущие контейнеры
3. Пересоберет контейнеры с новым кодом
4. Запустит все сервисы
5. Покажет статус и логи

### Ручной деплой

Если нужно больше контроля:

```bash
# 1. Подтянуть изменения
git pull origin main

# 2. Остановить контейнеры
docker-compose down

# 3. Пересобрать с нуля
docker-compose build --no-cache

# 4. Запустить
docker-compose up -d

# 5. Проверить статус
docker-compose ps

# 6. Посмотреть логи
docker-compose logs -f bot
docker-compose logs -f webadmin
```

## Деплой на удаленный сервер через SSH

### Вариант 1: SSH + команды

```bash
# Подключиться к серверу
ssh user@your-server.com

# Перейти в директорию проекта
cd /path/to/tg_exchange_bot

# Запустить деплой
./deploy.sh
```

### Вариант 2: Автоматизированный деплой

Создайте скрипт `remote_deploy.sh`:

```bash
#!/bin/bash

SERVER="user@your-server.com"
PROJECT_PATH="/path/to/tg_exchange_bot"

echo "🚀 Деплой на сервер $SERVER..."

ssh $SERVER << 'EOF'
cd /path/to/tg_exchange_bot
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose ps
EOF

echo "✅ Деплой завершен!"
```

## Проверка работоспособности

После деплоя проверьте:

### 1. Статус контейнеров

```bash
docker-compose ps
```

Должны быть запущены:
- ✅ `tg_exchange_bot-bot-1` (Telegram бот)
- ✅ `tg_exchange_bot-webadmin-1` (Веб-админка)
- ✅ `tg_exchange_bot-postgres-1` (База данных)
- ✅ `tg_exchange_bot-redis-1` (Redis)

### 2. Логи бота

```bash
docker-compose logs --tail=50 bot
```

Должны увидеть:
```
INFO:aiogram.dispatcher:Run polling for bot ...
INFO:src.scheduler:[Scheduler] Legacy scheduler запущен
INFO:src.services.fx_scheduler:FX rates scheduler started successfully
INFO:src.scheduler:[Scheduler] Rapira rates scheduler запущен
```

### 3. Веб-админка

Откройте в браузере:
```
http://localhost:8000/admin
```

Или на сервере:
```
http://your-server.com:8000/admin
```

### 4. Проверка обновлений

Проверьте, что новые изменения применились:

**В Telegram боте:**
- Отправьте `/start` боту
- Проверьте новый шаг подтверждения курса после выбора города
- Убедитесь, что кнопки "Назад" работают корректно

**В веб-админке:**
- Зайдите в админку
- Проверьте раздел "Курсы по городам"
- Убедитесь, что данные отображаются

## Решение проблем

### Порты заняты

Если получаете ошибку "port is already allocated":

```bash
# Найти процесс, занимающий порт
lsof -i :5432  # для PostgreSQL
lsof -i :6379  # для Redis
lsof -i :8000  # для webadmin

# Остановить контейнеры других проектов
docker stop deploy-db-1 deploy-redis-1

# Или изменить порты в docker-compose.yml
```

### Конфликт Telegram бота

Ошибка "Conflict: terminated by other getUpdates request":
- Где-то еще запущен экземпляр бота с тем же токеном
- Остановите другой экземпляр или используйте другой токен для локальной разработки

### Контейнер не запускается

```bash
# Посмотреть подробные логи
docker-compose logs <service_name>

# Пересоздать контейнер
docker-compose up -d --force-recreate <service_name>

# Очистить всё и начать заново
docker-compose down -v
docker-compose up -d --build
```

## Обновление на production сервере

### Рекомендуемая последовательность:

1. **Бэкап БД** (важно!)

```bash
docker-compose exec postgres pg_dump -U exchange exchange > backup_$(date +%Y%m%d_%H%M%S).sql
```

2. **Деплой**

```bash
./deploy.sh
```

3. **Миграции** (если есть новые)

```bash
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/XXX_new_migration.sql
```

4. **Проверка**

```bash
docker-compose ps
docker-compose logs --tail=100 bot
curl http://localhost:8000/admin
```

## Полезные команды

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Перезапуск отдельного сервиса
docker-compose restart bot

# Вход в контейнер
docker-compose exec bot bash

# Проверка БД
docker-compose exec postgres psql -U exchange -d exchange

# Очистка неиспользуемых ресурсов
docker system prune -a
```

## Версионирование

Текущая версия: **v1.2.0**

Changelog:
- ✅ Добавлен шаг подтверждения курса
- ✅ Улучшена навигация (кнопки "Назад")
- ✅ Добавлен `/start` для сброса состояния
- ✅ Обработчики `/start` во всех FSM процессах

---

**Дата последнего обновления:** 18 октября 2025

