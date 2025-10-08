import os
from typing import Dict, Any

class RapiraConfig:
    """Конфигурация для интеграции с Rapira API"""
    
    # API endpoints
    API_BASE_URL = os.getenv("RAPIRA_API_BASE", "https://api.rapira.net")
    PLATE_MINI_URL = f"{API_BASE_URL}/market/exchange-plate-mini"
    RATES_URL = f"{API_BASE_URL}/open/market/rates"
    
    # Настройки запросов
    REQUEST_TIMEOUT = int(os.getenv("RAPIRA_TIMEOUT", 10))
    MAX_RETRIES = int(os.getenv("RAPIRA_MAX_RETRIES", 3))
    RETRY_DELAY_BASE = float(os.getenv("RAPIRA_RETRY_DELAY", 0.5))
    
    # Настройки кэширования
    CACHE_TTL = int(os.getenv("RAPIRA_CACHE_TTL", 5))  # секунды
    STALE_TTL = int(os.getenv("RAPIRA_STALE_TTL", 30))  # секунды
    
    # Настройки планировщика
    UPDATE_INTERVAL = int(os.getenv("RAPIRA_UPDATE_INTERVAL", 5))  # секунды
    
    # Настройки VWAP
    VWAP_DEFAULT_AMOUNT = float(os.getenv("RAPIRA_VWAP_AMOUNT", 50000.0))  # USD
    
    # Настройки спредов по локациям (в процентах)
    CITY_SPREADS = {
        "moscow": {
            "cash_in": float(os.getenv("RAPIRA_MOSCOW_CASH_IN_SPREAD", 0.5)),
            "cash_out": float(os.getenv("RAPIRA_MOSCOW_CASH_OUT_SPREAD", 0.5))
        },
        "spb": {
            "cash_in": float(os.getenv("RAPIRA_SPB_CASH_IN_SPREAD", 0.6)),
            "cash_out": float(os.getenv("RAPIRA_SPB_CASH_OUT_SPREAD", 0.6))
        },
        "other": {
            "cash_in": float(os.getenv("RAPIRA_OTHER_CASH_IN_SPREAD", 1.0)),
            "cash_out": float(os.getenv("RAPIRA_OTHER_CASH_OUT_SPREAD", 1.0))
        }
    }
    
    # Процентные правила
    PERCENT_RULES = {
        "default": {
            "cash_in": float(os.getenv("RAPIRA_DEFAULT_CASH_IN_PERCENT", 0.0)),
            "cash_out": float(os.getenv("RAPIRA_DEFAULT_CASH_OUT_PERCENT", 0.0))
        },
        "premium": {
            "cash_in": float(os.getenv("RAPIRA_PREMIUM_CASH_IN_PERCENT", -0.1)),
            "cash_out": float(os.getenv("RAPIRA_PREMIUM_CASH_OUT_PERCENT", -0.1))
        }
    }
    
    # Фиксированные корректировки
    FIXED_ADJUSTMENTS = {
        "USDT/RUB": {
            "cash_in": float(os.getenv("RAPIRA_USDT_RUB_CASH_IN_FIXED", 0.0)),
            "cash_out": float(os.getenv("RAPIRA_USDT_RUB_CASH_OUT_FIXED", 0.0))
        },
        "BTC/USDT": {
            "cash_in": float(os.getenv("RAPIRA_BTC_USDT_CASH_IN_FIXED", 0.0)),
            "cash_out": float(os.getenv("RAPIRA_BTC_USDT_CASH_OUT_FIXED", 0.0))
        }
    }
    
    # Поддерживаемые торговые пары
    SUPPORTED_PAIRS = [
        "USDT/RUB",
        "BTC/USDT", 
        "EUR/USDT",
        "USD/RUB"
    ]
    
    # Настройки логирования
    LOG_LEVEL = os.getenv("RAPIRA_LOG_LEVEL", "INFO")
    LOG_REQUESTS = os.getenv("RAPIRA_LOG_REQUESTS", "true").lower() == "true"
    LOG_RESPONSES = os.getenv("RAPIRA_LOG_RESPONSES", "false").lower() == "true"
    
    # Настройки мониторинга
    HEALTH_CHECK_INTERVAL = int(os.getenv("RAPIRA_HEALTH_CHECK_INTERVAL", 30))  # секунды
    ALERT_ON_ERRORS = os.getenv("RAPIRA_ALERT_ON_ERRORS", "true").lower() == "true"
    MAX_ERRORS_BEFORE_ALERT = int(os.getenv("RAPIRA_MAX_ERRORS_BEFORE_ALERT", 3))
    
    @classmethod
    def get_city_spread(cls, city: str, operation: str) -> float:
        """Получает спред для города и операции"""
        city = city.lower()
        if city not in cls.CITY_SPREADS:
            city = "other"
        
        return cls.CITY_SPREADS[city].get(operation, 0.0)
    
    @classmethod
    def get_percent_rule(cls, rule_type: str, operation: str) -> float:
        """Получает процентное правило"""
        return cls.PERCENT_RULES.get(rule_type, cls.PERCENT_RULES["default"]).get(operation, 0.0)
    
    @classmethod
    def get_fixed_adjustment(cls, pair: str, operation: str) -> float:
        """Получает фиксированную корректировку"""
        return cls.FIXED_ADJUSTMENTS.get(pair, {}).get(operation, 0.0)
    
    @classmethod
    def is_pair_supported(cls, pair: str) -> bool:
        """Проверяет, поддерживается ли пара"""
        return pair in cls.SUPPORTED_PAIRS
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """Возвращает сводку конфигурации"""
        return {
            "api_base_url": cls.API_BASE_URL,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "cache_ttl": cls.CACHE_TTL,
            "stale_ttl": cls.STALE_TTL,
            "update_interval": cls.UPDATE_INTERVAL,
            "vwap_default_amount": cls.VWAP_DEFAULT_AMOUNT,
            "supported_pairs": cls.SUPPORTED_PAIRS,
            "city_spreads": cls.CITY_SPREADS,
            "log_level": cls.LOG_LEVEL,
            "health_check_interval": cls.HEALTH_CHECK_INTERVAL
        }

# Глобальный экземпляр конфигурации
config = RapiraConfig()
