"""
Клиент для Grinex Exchange API
Получает курсы валют и тикеры через публичное API
"""

import os
import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

# Конфигурация
GRINEX_API_BASE = os.getenv("GRINEX_API_BASE", "https://api.grinex.io")
GRINEX_TIMEOUT = int(os.getenv("GRINEX_TIMEOUT", 5))  # секунды
GRINEX_MAX_RETRIES = int(os.getenv("GRINEX_MAX_RETRIES", 3))


@dataclass
class GrinexTicker:
    """Тикер с биржи Grinex"""
    symbol: str
    last_price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    change_24h: Optional[Decimal] = None
    timestamp: Optional[datetime] = None


@dataclass
class GrinexHealth:
    """Статус здоровья API"""
    latency_ms: float
    http_code: int
    is_available: bool
    last_update: datetime
    error_count: int = 0
    last_error: Optional[str] = None


class GrinexClient:
    """Клиент для работы с Grinex API"""
    
    def __init__(self):
        self.health = GrinexHealth(
            latency_ms=0.0,
            http_code=200,
            is_available=True,
            last_update=datetime.now()
        )
        self._fallback_tickers: Dict[str, GrinexTicker] = {}
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        retries: int = 0
    ) -> Tuple[Dict, float]:
        """Выполняет HTTP-запрос с retry логикой"""
        url = f"{GRINEX_API_BASE}{endpoint}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with httpx.AsyncClient(timeout=GRINEX_TIMEOUT) as client:
                response = await client.get(url, params=params)
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                response.raise_for_status()
                
                # Обновляем health статус
                self.health.latency_ms = latency_ms
                self.health.http_code = response.status_code
                self.health.is_available = True
                self.health.last_update = datetime.now()
                self.health.error_count = 0
                self.health.last_error = None
                
                return response.json(), latency_ms
                
        except Exception as e:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = str(e)
            
            self.health.error_count += 1
            self.health.last_error = error_msg
            self.health.last_update = datetime.now()
            self.health.is_available = False
            
            if retries < GRINEX_MAX_RETRIES:
                # Экспоненциальная пауза: 1s, 2s, 4s
                delay = 2 ** retries
                logger.warning(f"Grinex API retry {retries + 1}/{GRINEX_MAX_RETRIES} after {delay}s: {error_msg}")
                await asyncio.sleep(delay)
                return await self._make_request(endpoint, params, retries + 1)
            
            logger.error(f"Grinex API request failed after {retries} retries: {error_msg}")
            raise
    
    async def get_ticker(self, symbol: str) -> Optional[GrinexTicker]:
        """Получает тикер для конкретной пары"""
        try:
            # Стандартный эндпоинт для тикеров (может отличаться)
            data, _ = await self._make_request(f"/api/v1/ticker/{symbol}")
            
            ticker = self._parse_ticker(data)
            if ticker:
                self._fallback_tickers[symbol] = ticker
            
            return ticker
            
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            # Возвращаем fallback если есть
            return self._fallback_tickers.get(symbol)
    
    async def get_all_tickers(self) -> Dict[str, GrinexTicker]:
        """Получает все тикеры одним запросом"""
        try:
            # Bulk endpoint для всех тикеров
            data, _ = await self._make_request("/api/v1/tickers")
            
            tickers = {}
            # Поддержка разных форматов ответа
            if isinstance(data, list):
                for item in data:
                    ticker = self._parse_ticker(item)
                    if ticker:
                        tickers[ticker.symbol] = ticker
            elif isinstance(data, dict):
                # Если ответ в виде словаря {symbol: {...}}
                for symbol, item in data.items():
                    if isinstance(item, dict):
                        item['symbol'] = symbol
                    ticker = self._parse_ticker(item)
                    if ticker:
                        tickers[ticker.symbol] = ticker
            
            # Обновляем fallback
            self._fallback_tickers.update(tickers)
            
            return tickers
            
        except Exception as e:
            logger.error(f"Failed to get all tickers: {e}")
            return self._fallback_tickers.copy()
    
    async def get_ticker_24h(self, symbol: str) -> Optional[GrinexTicker]:
        """Получает тикер с 24h статистикой"""
        try:
            data, _ = await self._make_request(f"/api/v1/ticker/24h", params={"symbol": symbol})
            
            ticker = self._parse_ticker(data)
            if ticker:
                self._fallback_tickers[symbol] = ticker
            
            return ticker
            
        except Exception as e:
            logger.error(f"Failed to get 24h ticker for {symbol}: {e}")
            return self._fallback_tickers.get(symbol)
    
    def _parse_ticker(self, data: Dict) -> Optional[GrinexTicker]:
        """Парсит данные тикера из разных форматов API"""
        try:
            # Поддержка разных форматов ключей
            symbol = data.get('symbol') or data.get('pair') or data.get('s')
            if not symbol:
                return None
            
            # Различные варианты названий полей
            last_price = self._extract_decimal(data, ['lastPrice', 'last', 'price', 'c', 'close'])
            bid = self._extract_decimal(data, ['bid', 'bidPrice', 'b'])
            ask = self._extract_decimal(data, ['ask', 'askPrice', 'a'])
            volume_24h = self._extract_decimal(data, ['volume', 'volume24h', 'v', 'quoteVolume'])
            high_24h = self._extract_decimal(data, ['high', 'high24h', 'h'])
            low_24h = self._extract_decimal(data, ['low', 'low24h', 'l'])
            change_24h = self._extract_decimal(data, ['change', 'priceChange', 'priceChangePercent'])
            
            # Timestamp
            timestamp = None
            ts_value = data.get('timestamp') or data.get('time') or data.get('t')
            if ts_value:
                if isinstance(ts_value, int):
                    # Миллисекунды или секунды
                    ts_value = ts_value / 1000 if ts_value > 10**10 else ts_value
                    timestamp = datetime.fromtimestamp(ts_value)
                elif isinstance(ts_value, str):
                    timestamp = datetime.fromisoformat(ts_value.replace('Z', '+00:00'))
            
            return GrinexTicker(
                symbol=symbol,
                last_price=last_price,
                bid=bid,
                ask=ask,
                volume_24h=volume_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                change_24h=change_24h,
                timestamp=timestamp or datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse ticker data: {e}, data: {data}")
            return None
    
    def _extract_decimal(self, data: Dict, keys: List[str]) -> Optional[Decimal]:
        """Извлекает Decimal значение из словаря по списку возможных ключей"""
        for key in keys:
            value = data.get(key)
            if value is not None:
                try:
                    return Decimal(str(value))
                except:
                    pass
        return None
    
    def get_health(self) -> GrinexHealth:
        """Возвращает статус здоровья API"""
        return self.health


# Глобальный экземпляр клиента
_grinex_client: Optional[GrinexClient] = None


async def get_grinex_client() -> GrinexClient:
    """Получает глобальный экземпляр GrinexClient"""
    global _grinex_client
    if not _grinex_client:
        _grinex_client = GrinexClient()
    return _grinex_client

