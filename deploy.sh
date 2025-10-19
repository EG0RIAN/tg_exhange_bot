#!/bin/bash

# Скрипт для деплоя обновлений на сервер

set -e

echo "🚀 Начинаем деплой..."

# Подтягиваем последние изменения из git
echo "📥 Подтягиваем изменения из git..."
git pull origin main

# Останавливаем контейнеры
echo "🛑 Останавливаем контейнеры..."
docker-compose down

# Пересобираем контейнеры
echo "🔨 Пересобираем контейнеры..."
docker-compose build --no-cache

# Запускаем контейнеры
echo "▶️  Запускаем контейнеры..."
docker-compose up -d

# Ждем запуска
echo "⏳ Ожидаем запуска сервисов..."
sleep 5

# Проверяем статус
echo "✅ Проверяем статус контейнеров..."
docker-compose ps

# Показываем логи
echo "📋 Последние логи:"
docker-compose logs --tail=50

echo ""
echo "✨ Деплой завершен!"
echo "📊 Проверьте статус: docker-compose ps"
echo "📋 Логи бота: docker-compose logs -f bot"
echo "🌐 Логи веб-админки: docker-compose logs -f webadmin"


