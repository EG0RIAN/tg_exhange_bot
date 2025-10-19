"""
Сервис управления валютными курсами с интеграцией бирж и наценками
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, ROUND_HALF_EVEN
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.db import get_pg_pool
from src.services.grinex import get_grinex_client, GrinexTicker
from src.services.rapira_simple import get_rapira_simple_client

logger = logging.getLogger(__name__)


class RoundingMode(Enum):
    """Режимы округления"""
    ROUND_HALF_UP = "ROUND_HALF_UP"
    ROUND_DOWN = "ROUND_DOWN" 
    ROUND_UP = "ROUND_UP"
    BANKERS = "BANKERS"  # ROUND_HALF_EVEN


@dataclass
class FXSource:
    """Источник курсов"""
    id: int
    code: str
    name: str
    enabled: bool
    auth_type: str
    api_base_url: Optional[str]
    config: dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class FXSourcePair:
    """Пара источника"""
    id: int
    source_id: int
    source_symbol: str
    base_currency: str
    quote_currency: str
    internal_symbol: str
    enabled: bool
    config: dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class FXMarkupRule:
    """Правило наценки"""
    id: int
    level: str  # global, source, pair
    source_id: Optional[int]
    source_pair_id: Optional[int]
    percent: Decimal
    fixed: Decimal
    rounding_mode: str
    round_to: int
    enabled: bool
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    description: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


@dataclass
class FXRate:
    """Курс с наценкой"""
    source_code: str
    internal_symbol: str
    base_currency: str
    quote_currency: str
    raw_price: Decimal
    final_price: Decimal
    bid_price: Optional[Decimal]
    ask_price: Optional[Decimal]
    applied_rule_id: Optional[int]
    markup_percent: Optional[Decimal]
    markup_fixed: Optional[Decimal]
    calculated_at: datetime
    stale: bool = False


class FXRatesService:
    """Сервис управления курсами"""
    
    def __init__(self):
        self._pool = None
        self._sources_cache: Dict[str, FXSource] = {}
        self._pairs_cache: Dict[int, List[FXSourcePair]] = {}
        self._rules_cache: List[FXMarkupRule] = []
        self._cache_updated_at: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
    
    async def get_pool(self):
        """Получает пул подключений к БД"""
        if not self._pool:
            self._pool = await get_pg_pool()
        return self._pool
    
    async def _refresh_cache(self, force: bool = False):
        """Обновляет кэш источников, пар и правил"""
        now = datetime.now()
        if not force and self._cache_updated_at and (now - self._cache_updated_at) < self._cache_ttl:
            return
        
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Загружаем источники
            sources = await conn.fetch("SELECT * FROM fx_source WHERE enabled = true")
            self._sources_cache = {row['code']: FXSource(**dict(row)) for row in sources}
            
            # ОПТИМИЗАЦИЯ: Загружаем все пары одним запросом вместо N+1
            if sources:
                source_ids = [s['id'] for s in sources]
                all_pairs = await conn.fetch("""
                    SELECT * FROM fx_source_pair 
                    WHERE source_id = ANY($1) AND enabled = true
                """, source_ids)
                
                # Группируем пары по source_id
                self._pairs_cache = {}
                for pair in all_pairs:
                    source_id = pair['source_id']
                    if source_id not in self._pairs_cache:
                        self._pairs_cache[source_id] = []
                    self._pairs_cache[source_id].append(FXSourcePair(**dict(pair)))
            
            # Загружаем активные правила наценки
            rules = await conn.fetch("""
                SELECT * FROM fx_markup_rule 
                WHERE enabled = true AND deleted_at IS NULL
                ORDER BY 
                    CASE level 
                        WHEN 'pair' THEN 1
                        WHEN 'source' THEN 2
                        WHEN 'global' THEN 3
                    END
            """)
            self._rules_cache = [FXMarkupRule(**dict(row)) for row in rules]
        
        self._cache_updated_at = now
        logger.info(f"Cache refreshed: {len(self._sources_cache)} sources, {sum(len(p) for p in self._pairs_cache.values())} pairs, {len(self._rules_cache)} rules")
    
    async def sync_source_rates(self, source_code: str) -> Dict[str, any]:
        """Синхронизирует курсы от одного источника"""
        await self._refresh_cache()
        
        source = self._sources_cache.get(source_code)
        if not source:
            raise ValueError(f"Source {source_code} not found or disabled")
        
        pairs = self._pairs_cache.get(source.id, [])
        if not pairs:
            logger.warning(f"No pairs configured for source {source_code}")
            return {"pairs_processed": 0, "pairs_succeeded": 0, "pairs_failed": 0}
        
        pool = await self.get_pool()
        started_at = datetime.now()
        pairs_succeeded = 0
        pairs_failed = 0
        errors = []
        
        # Создаем запись лога
        async with pool.acquire() as conn:
            log_id = await conn.fetchval("""
                INSERT INTO fx_sync_log (source_id, started_at, status, pairs_processed)
                VALUES ($1, $2, 'running', 0)
                RETURNING id
            """, source.id, started_at)
        
        try:
            # Получаем курсы из источника
            if source_code == 'grinex':
                rates_data = await self._fetch_grinex_rates(pairs)
            elif source_code == 'rapira':
                rates_data = await self._fetch_rapira_rates(pairs)
            else:
                raise ValueError(f"Unknown source: {source_code}")
            
            # Сохраняем сырые курсы
            async with pool.acquire() as conn:
                for pair in pairs:
                    try:
                        rate_info = rates_data.get(pair.source_symbol)
                        if not rate_info:
                            pairs_failed += 1
                            errors.append(f"{pair.source_symbol}: no data")
                            continue
                        
                        # Вставляем/обновляем сырой курс
                        metadata = rate_info.get('metadata', {})
                        metadata_json = json.dumps(metadata) if metadata else None
                        
                        await conn.execute("""
                            INSERT INTO fx_raw_rate 
                            (source_id, source_pair_id, raw_price, bid_price, ask_price, volume_24h, metadata, received_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (source_id, source_pair_id) 
                            DO UPDATE SET 
                                raw_price = EXCLUDED.raw_price,
                                bid_price = EXCLUDED.bid_price,
                                ask_price = EXCLUDED.ask_price,
                                volume_24h = EXCLUDED.volume_24h,
                                metadata = EXCLUDED.metadata,
                                received_at = EXCLUDED.received_at
                        """, source.id, pair.id, rate_info['price'], 
                             rate_info.get('bid'), rate_info.get('ask'),
                             rate_info.get('volume'), metadata_json,
                             datetime.now())
                        
                        # Вычисляем и сохраняем финальный курс
                        await self._calculate_and_save_final_rate(
                            conn, source, pair, rate_info['price'],
                            rate_info.get('bid'), rate_info.get('ask')
                        )
                        
                        pairs_succeeded += 1
                        
                    except Exception as e:
                        pairs_failed += 1
                        error_msg = f"{pair.source_symbol}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"Failed to save rate for {pair.source_symbol}: {e}")
            
            # Обновляем лог
            finished_at = datetime.now()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            status = 'success' if pairs_failed == 0 else ('partial' if pairs_succeeded > 0 else 'error')
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE fx_sync_log 
                    SET finished_at = $1, status = $2, pairs_processed = $3,
                        pairs_succeeded = $4, pairs_failed = $5, duration_ms = $6,
                        error_message = $7
                    WHERE id = $8
                """, finished_at, status, len(pairs), pairs_succeeded, pairs_failed,
                     duration_ms, '; '.join(errors[:10]) if errors else None, log_id)
            
            return {
                "pairs_processed": len(pairs),
                "pairs_succeeded": pairs_succeeded,
                "pairs_failed": pairs_failed,
                "duration_ms": duration_ms,
                "status": status,
                "errors": errors
            }
            
        except Exception as e:
            # Обновляем лог с ошибкой
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE fx_sync_log 
                    SET finished_at = $1, status = 'error', error_message = $2
                    WHERE id = $3
                """, datetime.now(), str(e), log_id)
            raise
    
    async def _fetch_grinex_rates(self, pairs: List[FXSourcePair]) -> Dict[str, Dict]:
        """Получает курсы из Grinex"""
        client = await get_grinex_client()
        rates = {}
        
        try:
            # Пробуем получить все тикеры за раз
            all_tickers = await client.get_all_tickers()
            
            for pair in pairs:
                ticker = all_tickers.get(pair.source_symbol)
                if ticker:
                    rates[pair.source_symbol] = {
                        'price': ticker.last_price,
                        'bid': ticker.bid,
                        'ask': ticker.ask,
                        'volume': ticker.volume_24h,
                        'metadata': {
                            'high_24h': str(ticker.high_24h) if ticker.high_24h else None,
                            'low_24h': str(ticker.low_24h) if ticker.low_24h else None,
                            'change_24h': str(ticker.change_24h) if ticker.change_24h else None
                        }
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Grinex rates in bulk: {e}")
            # Fallback: получаем по одному
            for pair in pairs:
                try:
                    ticker = await client.get_ticker(pair.source_symbol)
                    if ticker:
                        rates[pair.source_symbol] = {
                            'price': ticker.last_price,
                            'bid': ticker.bid,
                            'ask': ticker.ask,
                            'volume': ticker.volume_24h
                        }
                except Exception as e2:
                    logger.error(f"Failed to fetch Grinex ticker for {pair.source_symbol}: {e2}")
        
        return rates
    
    async def _fetch_rapira_rates(self, pairs: List[FXSourcePair]) -> Dict[str, Dict]:
        """Получает курсы из Rapira (публичный API)"""
        client = await get_rapira_simple_client()
        rates = {}
        
        for pair in pairs:
            try:
                # source_symbol может быть в формате 'usdtrub' или 'USDT/RUB'
                # Rapira API принимает оба формата
                symbol = pair.source_symbol.upper()
                if '/' not in symbol:
                    # Конвертируем btcusdt -> BTC/USDT
                    if symbol.endswith('USDT'):
                        base = symbol[:-4]
                        symbol = f"{base}/USDT"
                    elif symbol.endswith('RUB'):
                        base = symbol[:-3]
                        symbol = f"{base}/RUB"
                
                rate_data = await client.get_base_rate(symbol)
                if rate_data and (rate_data['best_ask'] or rate_data['best_bid']):
                    # Используем mid price как основной курс
                    bid = rate_data['best_bid']
                    ask = rate_data['best_ask']
                    
                    if bid and ask:
                        price = (bid + ask) / 2
                    elif ask:
                        price = ask
                    elif bid:
                        price = bid
                    else:
                        continue
                    
                    rates[pair.source_symbol] = {
                        'price': Decimal(str(price)),
                        'bid': Decimal(str(bid)) if bid else None,
                        'ask': Decimal(str(ask)) if ask else None,
                        'volume': None  # Публичный API не возвращает volume
                    }
                    
            except Exception as e:
                logger.error(f"Failed to fetch Rapira rate for {pair.source_symbol}: {e}")
        
        return rates
    
    async def _calculate_and_save_final_rate(
        self, 
        conn, 
        source: FXSource, 
        pair: FXSourcePair, 
        raw_price: Decimal,
        bid_price: Optional[Decimal] = None,
        ask_price: Optional[Decimal] = None
    ):
        """Вычисляет и сохраняет финальный курс с наценкой"""
        # Находим подходящее правило наценки
        rule = self._find_applicable_rule(source.id, pair.id)
        
        if rule:
            # Применяем наценку
            final_price = self._apply_markup(raw_price, rule)
            markup_percent = rule.percent
            markup_fixed = rule.fixed
            rule_id = rule.id
        else:
            # Нет правила - курс без изменений
            final_price = raw_price
            markup_percent = Decimal('0')
            markup_fixed = Decimal('0')
            rule_id = None
        
        # Сохраняем финальный курс
        await conn.execute("""
            INSERT INTO fx_final_rate 
            (source_id, source_pair_id, raw_price, final_price, applied_rule_id, 
             markup_percent, markup_fixed, calculated_at, stale)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, false)
            ON CONFLICT (source_id, source_pair_id) 
            DO UPDATE SET 
                raw_price = EXCLUDED.raw_price,
                final_price = EXCLUDED.final_price,
                applied_rule_id = EXCLUDED.applied_rule_id,
                markup_percent = EXCLUDED.markup_percent,
                markup_fixed = EXCLUDED.markup_fixed,
                calculated_at = EXCLUDED.calculated_at,
                stale = false
        """, source.id, pair.id, raw_price, final_price, rule_id,
             markup_percent, markup_fixed, datetime.now())
    
    def _find_applicable_rule(self, source_id: int, pair_id: int) -> Optional[FXMarkupRule]:
        """Находит применимое правило наценки с учетом приоритета"""
        now = datetime.now()
        
        for rule in self._rules_cache:
            # Проверяем срок действия
            if rule.valid_from and rule.valid_from > now:
                continue
            if rule.valid_to and rule.valid_to < now:
                continue
            
            # Проверяем соответствие по уровню (приоритет: pair > source > global)
            if rule.level == 'pair' and rule.source_pair_id == pair_id:
                return rule
            elif rule.level == 'source' and rule.source_id == source_id:
                return rule
            elif rule.level == 'global':
                return rule
        
        return None
    
    def _apply_markup(self, raw_price: Decimal, rule: FXMarkupRule) -> Decimal:
        """Применяет наценку к курсу"""
        # Шаг 1: применяем процент
        price_with_percent = raw_price * (Decimal('1') + rule.percent / Decimal('100'))
        
        # Шаг 2: добавляем фиксированную наценку
        final_price = price_with_percent + rule.fixed
        
        # Шаг 3: округляем
        return self._round_price(final_price, rule.rounding_mode, rule.round_to)
    
    def _round_price(self, price: Decimal, mode: str, decimals: int) -> Decimal:
        """Округляет цену по заданному режиму"""
        quantizer = Decimal('0.1') ** decimals
        
        rounding_map = {
            'ROUND_HALF_UP': ROUND_HALF_UP,
            'ROUND_DOWN': ROUND_DOWN,
            'ROUND_UP': ROUND_UP,
            'BANKERS': ROUND_HALF_EVEN
        }
        
        rounding = rounding_map.get(mode, ROUND_HALF_UP)
        return price.quantize(quantizer, rounding=rounding)
    
    async def get_final_rate(
        self, 
        base: str, 
        quote: str, 
        source_code: str = None,
        allow_stale: bool = False
    ) -> Optional[FXRate]:
        """Получает финальный курс для пары"""
        await self._refresh_cache()
        
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    s.code as source_code,
                    sp.internal_symbol,
                    sp.base_currency,
                    sp.quote_currency,
                    fr.raw_price,
                    fr.final_price,
                    rr.bid_price,
                    rr.ask_price,
                    fr.applied_rule_id,
                    fr.markup_percent,
                    fr.markup_fixed,
                    fr.calculated_at,
                    fr.stale
                FROM fx_final_rate fr
                JOIN fx_source s ON s.id = fr.source_id
                JOIN fx_source_pair sp ON sp.id = fr.source_pair_id
                LEFT JOIN fx_raw_rate rr ON rr.source_id = fr.source_id AND rr.source_pair_id = fr.source_pair_id
                WHERE sp.base_currency = $1 AND sp.quote_currency = $2
                    AND s.enabled = true AND sp.enabled = true
            """
            params = [base, quote]
            
            if source_code:
                query += " AND s.code = $3"
                params.append(source_code)
            
            if not allow_stale:
                query += f" AND fr.stale = false"
            
            query += " ORDER BY fr.calculated_at DESC LIMIT 1"
            
            row = await conn.fetchrow(query, *params)
            
            if row:
                return FXRate(**dict(row))
            
            return None
    
    async def get_all_final_rates(
        self,
        source_code: Optional[str] = None,
        allow_stale: bool = False
    ) -> List[FXRate]:
        """Получает все финальные курсы"""
        await self._refresh_cache()
        
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    s.code as source_code,
                    sp.internal_symbol,
                    sp.base_currency,
                    sp.quote_currency,
                    fr.raw_price,
                    fr.final_price,
                    rr.bid_price,
                    rr.ask_price,
                    fr.applied_rule_id,
                    fr.markup_percent,
                    fr.markup_fixed,
                    fr.calculated_at,
                    fr.stale
                FROM fx_final_rate fr
                JOIN fx_source s ON s.id = fr.source_id
                JOIN fx_source_pair sp ON sp.id = fr.source_pair_id
                LEFT JOIN fx_raw_rate rr ON rr.source_id = fr.source_id AND rr.source_pair_id = fr.source_pair_id
                WHERE s.enabled = true AND sp.enabled = true
            """
            params = []
            
            if source_code:
                query += " AND s.code = $1"
                params.append(source_code)
            
            if not allow_stale:
                query += " AND fr.stale = false"
            
            query += " ORDER BY s.code, sp.internal_symbol"
            
            rows = await conn.fetch(query, *params)
            return [FXRate(**dict(row)) for row in rows]


# Глобальный экземпляр сервиса
_fx_service: Optional[FXRatesService] = None


async def get_fx_service() -> FXRatesService:
    """Получает глобальный экземпляр FXRatesService"""
    global _fx_service
    if not _fx_service:
        _fx_service = FXRatesService()
    return _fx_service

