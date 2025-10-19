"""
Централизованная система логирования
Обеспечивает единообразное логирование во всем проекте
"""

import logging
import sys
from functools import wraps
from typing import Callable, Any
from datetime import datetime
import traceback


# ============================================================================
# Конфигурация логирования
# ============================================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Цветные логи для консоли
COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'        # Reset
}


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом"""
    
    def format(self, record):
        # Добавляем цвет к уровню логирования
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        return super().format(record)


def setup_logging(level: str = "INFO", colored: bool = True):
    """
    Настраивает логирование для всего приложения
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        colored: Использовать цветной вывод
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Создаем handler для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Выбираем форматтер
    if colored:
        formatter = ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    else:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    console_handler.setFormatter(formatter)
    
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []  # Очищаем предыдущие handlers
    root_logger.addHandler(console_handler)
    
    # Настройка для внешних библиотек (уменьшаем verbose)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('aiogram').setLevel(logging.INFO)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={level}, colored={colored}")


# ============================================================================
# Декораторы для автоматического логирования
# ============================================================================

def log_function(func: Callable) -> Callable:
    """
    Декоратор для автоматического логирования вызовов функций
    
    Логирует:
    - Вход в функцию с параметрами
    - Выход из функции с результатом
    - Ошибки с полным traceback
    - Время выполнения
    """
    logger = logging.getLogger(func.__module__)
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = datetime.now()
        
        # Формируем строку с параметрами (без чувствительных данных)
        args_str = _format_args(args, kwargs)
        
        logger.debug(f"→ {func_name}({args_str})")
        
        try:
            result = await func(*args, **kwargs)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"← {func_name} completed in {duration:.0f}ms")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"✗ {func_name} failed after {duration:.0f}ms: {e}",
                exc_info=True
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = datetime.now()
        
        args_str = _format_args(args, kwargs)
        logger.debug(f"→ {func_name}({args_str})")
        
        try:
            result = func(*args, **kwargs)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"← {func_name} completed in {duration:.0f}ms")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"✗ {func_name} failed after {duration:.0f}ms: {e}",
                exc_info=True
            )
            raise
    
    # Выбираем async или sync wrapper
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_handler(handler_name: str = None):
    """
    Декоратор для логирования обработчиков Aiogram
    
    Логирует:
    - Входящие сообщения/callback
    - ID пользователя
    - Текст/данные
    - Результат обработки
    """
    def decorator(func: Callable) -> Callable:
        logger = logging.getLogger(func.__module__)
        name = handler_name or func.__name__
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Определяем тип события
            event = None
            user_id = None
            event_data = None
            
            for arg in args:
                if hasattr(arg, 'from_user'):
                    user_id = arg.from_user.id
                    if hasattr(arg, 'text'):
                        event_data = arg.text
                        event = "message"
                    elif hasattr(arg, 'data'):
                        event_data = arg.data
                        event = "callback"
            
            logger.info(
                f"🎯 Handler [{name}] started: user={user_id}, "
                f"type={event}, data={event_data}"
            )
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    f"✅ Handler [{name}] completed in {duration:.0f}ms"
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(
                    f"❌ Handler [{name}] failed after {duration:.0f}ms: {e}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Вспомогательные функции
# ============================================================================

def _format_args(args: tuple, kwargs: dict) -> str:
    """Форматирует аргументы функции для логирования (без sensitive данных)"""
    sensitive_keys = {'password', 'token', 'secret', 'api_key'}
    
    # Фильтруем args (только первые 3)
    args_strs = []
    for i, arg in enumerate(args[:3]):
        if i == 0 and hasattr(arg, '__class__'):
            # Пропускаем self/cls
            continue
        args_strs.append(_format_value(arg))
    
    # Фильтруем kwargs
    kwargs_strs = []
    for key, value in kwargs.items():
        if key.lower() in sensitive_keys:
            kwargs_strs.append(f"{key}=***")
        else:
            kwargs_strs.append(f"{key}={_format_value(value)}")
    
    all_args = args_strs + kwargs_strs
    return ", ".join(all_args) if all_args else ""


def _format_value(value: Any) -> str:
    """Форматирует значение для вывода"""
    if isinstance(value, str):
        return f'"{value[:50]}"' if len(value) > 50 else f'"{value}"'
    elif isinstance(value, (int, float, bool)):
        return str(value)
    elif value is None:
        return "None"
    else:
        return type(value).__name__


def log_error_with_context(logger, message: str, error: Exception, **context):
    """
    Логирует ошибку с дополнительным контекстом
    
    Args:
        logger: Logger instance
        message: Сообщение об ошибке
        error: Exception объект
        **context: Дополнительный контекст (user_id, order_id, и т.д.)
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    full_message = f"{message} [{context_str}]: {error}"
    
    logger.error(full_message, exc_info=True)


def get_logger(name: str) -> logging.Logger:
    """
    Получает logger с заданным именем
    
    Args:
        name: Имя модуля (обычно __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ============================================================================
# Мониторинг производительности
# ============================================================================

class PerformanceLogger:
    """Логгер для мониторинга производительности"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️ {self.operation} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000
        
        if exc_type:
            self.logger.error(
                f"⏱️ {self.operation} failed after {duration:.0f}ms: {exc_val}"
            )
        else:
            if duration > 1000:
                self.logger.warning(
                    f"⏱️ {self.operation} completed in {duration:.0f}ms (SLOW!)"
                )
            else:
                self.logger.debug(
                    f"⏱️ {self.operation} completed in {duration:.0f}ms"
                )
        
        return False  # Не подавляем исключение


# ============================================================================
# Structured logging helpers
# ============================================================================

def log_user_action(logger, user_id: int, action: str, **details):
    """Логирует действие пользователя"""
    details_str = ", ".join(f"{k}={v}" for k, v in details.items())
    logger.info(f"👤 User {user_id}: {action} [{details_str}]")


def log_order_event(logger, order_id: int, event: str, **details):
    """Логирует событие заявки"""
    details_str = ", ".join(f"{k}={v}" for k, v in details.items())
    logger.info(f"📋 Order #{order_id}: {event} [{details_str}]")


def log_api_call(logger, service: str, endpoint: str, duration_ms: float, status: str = "success"):
    """Логирует API вызов"""
    if status == "success":
        logger.info(f"🌐 API {service}/{endpoint}: {duration_ms:.0f}ms ✅")
    else:
        logger.error(f"🌐 API {service}/{endpoint}: {duration_ms:.0f}ms ❌ {status}")


def log_db_query(logger, query_type: str, table: str, duration_ms: float, rows: int = None):
    """Логирует запрос к БД"""
    rows_str = f", rows={rows}" if rows is not None else ""
    
    if duration_ms > 100:
        logger.warning(f"🗄️ DB {query_type} {table}: {duration_ms:.0f}ms{rows_str} (SLOW)")
    else:
        logger.debug(f"🗄️ DB {query_type} {table}: {duration_ms:.0f}ms{rows_str}")

