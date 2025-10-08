import os
import httpx
import asyncio
import json
import redis.asyncio as aioredis
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from src.db import get_pg_pool

# Конфигурация
RAPIRA_API_BASE = os.getenv("RAPIRA_API_BASE", "https://api.rapira.net")
RAPIRA_PLATE_MINI_URL = f"{RAPIRA_API_BASE}/market/exchange-plate-mini"
RAPIRA_RATES_URL = f"{RAPIRA_API_BASE}/open/market/rates"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Настройки
CACHE_TTL = int(os.getenv("RAPIRA_CACHE_TTL", 5))  # секунды
STALE_TTL = int(os.getenv("RAPIRA_STALE_TTL", 30))  # секунды
REQUEST_TIMEOUT = int(os.getenv("RAPIRA_TIMEOUT", 10))  # секунды
MAX_RETRIES = int(os.getenv("RAPIRA_MAX_RETRIES", 3))
VWAP_DEFAULT_AMOUNT = float(os.getenv("RAPIRA_VWAP_AMOUNT", 50000))  # USD

logger = logging.getLogger(__name__)

class Side(Enum):
    BID = "bid"
    ASK = "ask"

@dataclass
class OrderLevel:
    price: float
    qty: float

@dataclass
class PlateMini:
    symbol: str
    ts: str  # ISO8601
    best_bid: Optional[OrderLevel] = None
    best_ask: Optional[OrderLevel] = None
    bids: Optional[List[OrderLevel]] = None
    asks: Optional[List[OrderLevel]] = None
    last_price: Optional[float] = None
    last_qty: Optional[float] = None
    last_ts: Optional[str] = None

@dataclass
class ProviderHealth:
    latency: float
    http_code: int
    is_fresh: bool
    last_update: datetime
    error_count: int = 0
    last_error: Optional[str] = None

class RapiraProvider:
    def __init__(self):
        self.health = ProviderHealth(
            latency=0.0,
            http_code=200,
            is_fresh=True,
            last_update=datetime.now()
        )
        self._redis_pool = None
        self._fallback_rates = {}
    
    async def get_redis(self):
        if not self._redis_pool:
            self._redis_pool = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
        return self._redis_pool
    
    async def close(self):
        if self._redis_pool:
            await self._redis_pool.close()
            self._redis_pool = None
    
    async def _make_request(self, url: str, params: Optional[Dict] = None, retries: int = 0) -> Tuple[Dict, float]:
        """Выполняет HTTP-запрос с retry логикой и измерением latency"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000  # в миллисекундах
                
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=None, response=response)
                
                self.health.latency = latency
                self.health.http_code = response.status_code
                self.health.last_update = datetime.now()
                self.health.error_count = 0
                self.health.last_error = None
                
                return response.json(), latency
                
        except Exception as e:
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = str(e)
            
            self.health.error_count += 1
            self.health.last_error = error_msg
            self.health.last_update = datetime.now()
            
            if retries < MAX_RETRIES and isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError)):
                # Экспоненциальная пауза
                delay = (2 ** retries) * 0.5
                logger.warning(f"Rapira API retry {retries + 1}/{MAX_RETRIES} after {delay}s: {error_msg}")
                await asyncio.sleep(delay)
                return await self._make_request(url, params, retries + 1)
            
            logger.error(f"Rapira API request failed after {retries} retries: {error_msg}")
            raise
    
    async def get_plate_mini(self, symbol: str) -> Optional[PlateMini]:
        """Получает мини-стакан по паре"""
        try:
            params = {"symbol": symbol}
            data, _ = await self._make_request(RAPIRA_PLATE_MINI_URL, params)
            
            # Парсим ответ
            plate = PlateMini(
                symbol=symbol,
                ts=data.get("ts", datetime.now().isoformat()),
                best_bid=OrderLevel(**data["bestBid"]) if data.get("bestBid") else None,
                best_ask=OrderLevel(**data["bestAsk"]) if data.get("bestAsk") else None,
                bids=[OrderLevel(**bid) for bid in data.get("bids", [])],
                asks=[OrderLevel(**ask) for ask in data.get("asks", [])],
                last_price=data.get("lastPrice"),
                last_qty=data.get("lastQty"),
                last_ts=data.get("lastTs")
            )
            
            # Кэшируем
            await self._cache_plate_mini(symbol, plate)
            return plate
            
        except Exception as e:
            logger.error(f"Failed to get plate mini for {symbol}: {e}")
            # Fallback на кэш или rates endpoint
            return await self._get_fallback_plate(symbol)
    
    async def get_rates(self) -> Dict[str, float]:
        """Получает сводные курсы по всем парам (fallback источник)"""
        try:
            data, _ = await self._make_request(RAPIRA_RATES_URL)
            
            rates = {}
            for item in data.get("rates", []):
                symbol = item.get("symbol")
                if symbol and "lastPrice" in item:
                    rates[symbol] = float(item["lastPrice"])
            
            # Обновляем fallback
            self._fallback_rates = rates
            await self._cache_rates(rates)
            
            return rates
            
        except Exception as e:
            logger.error(f"Failed to get rates: {e}")
            # Возвращаем последний валидный fallback
            return self._fallback_rates
    
    async def calculate_vwap(self, plate: PlateMini, side: Side, amount_usd: float = VWAP_DEFAULT_AMOUNT) -> float:
        """Рассчитывает VWAP для заданной суммы"""
        if not plate or not (plate.bids or plate.asks):
            # Fallback на top-of-book
            return self._get_top_of_book(plate, side)
        
        levels = plate.asks if side == Side.ASK else plate.bids
        if not levels:
            return self._get_top_of_book(plate, side)
        
        # Сортируем уровни (asks - по возрастанию, bids - по убыванию)
        sorted_levels = sorted(levels, key=lambda x: x.price, reverse=(side == Side.BID))
        
        total_qty = 0.0
        weighted_sum = 0.0
        
        for level in sorted_levels:
            if total_qty >= amount_usd:
                break
            
            qty_to_use = min(level.qty, amount_usd - total_qty)
            weighted_sum += level.price * qty_to_use
            total_qty += qty_to_use
        
        if total_qty == 0:
            return self._get_top_of_book(plate, side)
        
        return weighted_sum / total_qty
    
    def _get_top_of_book(self, plate: PlateMini, side: Side) -> float:
        """Получает top-of-book цену"""
        if side == Side.BID and plate.best_bid:
            return plate.best_bid.price
        elif side == Side.ASK and plate.best_ask:
            return plate.best_ask.price
        elif plate.last_price:
            return plate.last_price
        else:
            raise ValueError(f"No price available for {plate.symbol} {side.value}")
    
    async def _cache_plate_mini(self, symbol: str, plate: PlateMini):
        """Кэширует plate mini в Redis"""
        try:
            redis = await self.get_redis()
            key = f"rapira:plate:{symbol}"
            data = {
                "symbol": plate.symbol,
                "ts": plate.ts,
                "best_bid": {"price": plate.best_bid.price, "qty": plate.best_bid.qty} if plate.best_bid else None,
                "best_ask": {"price": plate.best_ask.price, "qty": plate.best_ask.qty} if plate.best_ask else None,
                "bids": [{"price": b.price, "qty": b.qty} for b in (plate.bids or [])],
                "asks": [{"price": a.price, "qty": a.qty} for a in (plate.asks or [])],
                "last_price": plate.last_price,
                "last_qty": plate.last_qty,
                "last_ts": plate.last_ts
            }
            await redis.set(key, json.dumps(data), ex=CACHE_TTL)
        except Exception as e:
            logger.error(f"Failed to cache plate mini: {e}")
    
    async def _cache_rates(self, rates: Dict[str, float]):
        """Кэширует rates в Redis"""
        try:
            redis = await self.get_redis()
            for symbol, rate in rates.items():
                key = f"rapira:rate:{symbol}"
                await redis.set(key, str(rate), ex=CACHE_TTL)
        except Exception as e:
            logger.error(f"Failed to cache rates: {e}")
    
    async def _get_fallback_plate(self, symbol: str) -> Optional[PlateMini]:
        """Получает fallback данные из кэша или rates endpoint"""
        try:
            # Пробуем кэш
            redis = await self.get_redis()
            key = f"rapira:plate:{symbol}"
            cached = await redis.get(key)
            
            if cached:
                data = json.loads(cached)
                return PlateMini(
                    symbol=data["symbol"],
                    ts=data["ts"],
                    best_bid=OrderLevel(**data["best_bid"]) if data.get("best_bid") else None,
                    best_ask=OrderLevel(**data["best_ask"]) if data.get("best_ask") else None,
                    bids=[OrderLevel(**b) for b in data.get("bids", [])],
                    asks=[OrderLevel(**a) for a in data.get("asks", [])],
                    last_price=data.get("last_price"),
                    last_qty=data.get("last_qty"),
                    last_ts=data.get("last_ts")
                )
            
            # Fallback на rates endpoint
            rates = await self.get_rates()
            if symbol in rates:
                return PlateMini(
                    symbol=symbol,
                    ts=datetime.now().isoformat(),
                    last_price=rates[symbol]
                )
                
        except Exception as e:
            logger.error(f"Fallback failed for {symbol}: {e}")
        
        return None
    
    async def get_cached_plate(self, symbol: str) -> Optional[PlateMini]:
        """Получает кэшированные данные с проверкой свежести"""
        try:
            redis = await self.get_redis()
            key = f"rapira:plate:{symbol}"
            cached = await redis.get(key)
            
            if cached:
                data = json.loads(cached)
                # Проверяем свежесть
                cache_time = datetime.fromisoformat(data["ts"])
                age = (datetime.now() - cache_time).total_seconds()
                
                self.health.is_fresh = age <= STALE_TTL
                
                return PlateMini(
                    symbol=data["symbol"],
                    ts=data["ts"],
                    best_bid=OrderLevel(**data["best_bid"]) if data.get("best_bid") else None,
                    best_ask=OrderLevel(**data["best_ask"]) if data.get("best_ask") else None,
                    bids=[OrderLevel(**b) for b in data.get("bids", [])],
                    asks=[OrderLevel(**a) for a in data.get("asks", [])],
                    last_price=data.get("last_price"),
                    last_qty=data.get("last_qty"),
                    last_ts=data.get("last_ts")
                )
                
        except Exception as e:
            logger.error(f"Failed to get cached plate: {e}")
        
        return None
    
    def get_health(self) -> ProviderHealth:
        """Возвращает текущее состояние провайдера"""
        return self.health

# Глобальный экземпляр провайдера
_rapira_provider = None

async def get_rapira_provider() -> RapiraProvider:
    """Получает глобальный экземпляр RapiraProvider"""
    global _rapira_provider
    if not _rapira_provider:
        _rapira_provider = RapiraProvider()
    return _rapira_provider

# Backward compatibility functions
async def get_rates(pairs: list[str], bot=None):
    """Legacy функция для совместимости"""
    provider = await get_rapira_provider()
    rates = {}
    
    for pair in pairs:
        try:
            plate = await provider.get_plate_mini(pair)
            if plate and plate.last_price:
                rates[pair] = {"ask": str(plate.last_price), "bid": str(plate.last_price)}
            elif plate and plate.best_ask and plate.best_bid:
                rates[pair] = {
                    "ask": str(plate.best_ask.price),
                    "bid": str(plate.best_bid.price)
                }
        except Exception as e:
            logger.error(f"Failed to get rate for {pair}: {e}")
            # Fallback на БД
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT pair, ask, bid FROM rates WHERE pair = $1", pair)
                if row:
                    rates[pair] = {"ask": str(row["ask"]), "bid": str(row["bid"])}
    
    # Alert в админ-чат при ошибках
    if bot and ADMIN_IDS and not rates:
                for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"[ALERT] Rapira API недоступен для всех пар")
    
    return rates 

async def fetch_rapira_rates(pairs: list[str]):
    """Legacy функция для совместимости"""
    provider = await get_rapira_provider()
    return await provider.get_rates() 