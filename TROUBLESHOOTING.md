# 🔧 Устранение проблем с веб-админкой

## 🚨 Проблема: Разделы не работают (404 ошибки)

### Причина
Новые функции не были добавлены в Docker контейнер после обновления кода.

### Решение
```bash
# 1. Остановить контейнер админки
docker-compose down webadmin

# 2. Пересобрать образ
docker-compose build webadmin

# 3. Запустить заново
docker-compose up webadmin -d
```

## 🚨 Проблема: Ошибка "too many clients already"

### Причина
Слишком много подключений к базе данных PostgreSQL.

### Решение
```bash
# 1. Остановить все сервисы
docker-compose down

# 2. Запустить заново
docker-compose up -d

# 3. Проверить логи
docker-compose logs webadmin
```

## 🚨 Проблема: Разделы возвращают 302 (редирект)

### Причина
Это **нормальное поведение**! Разделы работают, но требуют авторизации.

### Проверка
```bash
# Тест без авторизации (должен возвращать 302)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/orders

# Тест с авторизацией (должен возвращать 200)
# Откройте браузер: http://localhost:8000
# Войдите с логином: admin, паролем: admin123
```

## 🚨 Проблема: База данных недоступна

### Проверка
```bash
# Проверить статус PostgreSQL
docker-compose ps postgres

# Проверить логи PostgreSQL
docker-compose logs postgres

# Проверить подключение к БД
docker-compose exec postgres psql -U exchange -d exchange -c "SELECT 1;"
```

### Решение
```bash
# Перезапустить PostgreSQL
docker-compose restart postgres

# Или пересоздать контейнер
docker-compose down postgres
docker-compose up postgres -d
```

## 🚨 Проблема: Админка не запускается

### Проверка
```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить логи админки
docker-compose logs webadmin

# Проверить порты
netstat -an | grep 8000
```

### Решение
```bash
# Полная перезагрузка
docker-compose down
docker-compose up -d

# Проверить, что все сервисы запущены
docker-compose ps
```

## 🚨 Проблема: Неправильные учетные данные

### Проверка переменных окружения
```bash
# Проверить файл .env
cat .env

# Должны быть установлены:
# ADMIN_LOGIN=admin
# ADMIN_PASSWORD=admin123
# ADMIN_SECRET_KEY=your_secret_key
```

### Решение
```bash
# Создать/обновить файл .env
echo "ADMIN_LOGIN=admin" > .env
echo "ADMIN_PASSWORD=admin123" >> .env
echo "ADMIN_SECRET_KEY=supersecret" >> .env
echo "POSTGRES_HOST=postgres" >> .env
echo "POSTGRES_PORT=5432" >> .env
echo "POSTGRES_DB=exchange" >> .env
echo "POSTGRES_USER=exchange" >> .env
echo "POSTGRES_PASSWORD=exchange" >> .env

# Перезапустить сервисы
docker-compose down
docker-compose up -d
```

## 🚨 Проблема: Статические файлы не загружаются

### Проверка
```bash
# Проверить доступность CSS
curl -I http://localhost:8000/static/bootstrap.min.css
```

### Решение
```bash
# Пересобрать контейнер
docker-compose build webadmin
docker-compose up webadmin -d
```

## 🚨 Проблема: Медленная работа админки

### Причины
1. Слишком много подключений к БД
2. Недостаточно памяти
3. Медленная сеть

### Решение
```bash
# Ограничить количество подключений к БД
# В src/web_admin/main.py уже настроено:
# min_size=1, max_size=10

# Перезапустить с ограничениями ресурсов
docker-compose down
docker-compose up -d
```

## 🧪 Тестирование

### Автоматические тесты
```bash
# Запустить тесты
python3 test_admin_sections.py
python3 test_admin_with_auth.py
```

### Ручное тестирование
1. Откройте http://localhost:8000
2. Войдите с логином `admin` и паролем `admin123`
3. Проверьте все разделы:
   - ✅ Главная панель
   - ✅ Торговые пары
   - ✅ Курсы валют
   - ✅ Способы выплаты
   - ✅ FAQ
   - ✅ Заявки
   - ✅ Пользователи
   - ✅ Уведомления
   - ✅ Статистика
   - ✅ Live чаты

## 📊 Мониторинг

### Проверка логов
```bash
# Логи админки
docker-compose logs webadmin

# Логи PostgreSQL
docker-compose logs postgres

# Логи Redis
docker-compose logs redis
```

### Проверка статуса
```bash
# Статус всех сервисов
docker-compose ps

# Использование ресурсов
docker stats
```

## 🔄 Обновление

### Обновление кода
```bash
# 1. Остановить сервисы
docker-compose down

# 2. Пересобрать образы
docker-compose build

# 3. Запустить заново
docker-compose up -d

# 4. Проверить работу
docker-compose logs webadmin
```

### Обновление зависимостей
```bash
# 1. Обновить requirements.txt
# 2. Пересобрать образ
docker-compose build webadmin
docker-compose up webadmin -d
```

## 📞 Поддержка

Если проблемы не решаются:

1. **Проверьте логи**: `docker-compose logs webadmin`
2. **Проверьте статус**: `docker-compose ps`
3. **Проверьте сеть**: `docker network ls`
4. **Проверьте тома**: `docker volume ls`

### Полезные команды
```bash
# Полная очистка
docker-compose down -v
docker system prune -f
docker-compose up -d

# Проверка конфигурации
docker-compose config

# Проверка образов
docker images | grep tg_exchange_bot
``` 