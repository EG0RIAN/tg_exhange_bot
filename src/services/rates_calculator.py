import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.services.rapira import RapiraProvider, Side, get_rapira_provider

logger = logging.getLogger(__name__)

class OperationType(Enum):
    CASH_IN = "cash_in"   # Клиент отдает USDT, получает RUB (ПРОДАЖА USDT)
    CASH_OUT = "cash_out"  # Клиент отдает RUB, получает USDT (ПОКУПКА USDT)
    SELL = "sell"  # Синоним для CASH_IN - клиент продает USDT
    BUY = "buy"    # Синоним для CASH_OUT - клиент покупает USDT
    
    @classmethod
    def normalize(cls, operation: str) -> 'OperationType':
        """Нормализует операцию к нужному типу"""
        operation_lower = operation.lower()
        if operation_lower in ('sell', 'cash_in'):
            return cls.CASH_IN
        elif operation_lower in ('buy', 'cash_out'):
            return cls.CASH_OUT
        else:
            return cls(operation_lower)

@dataclass
class RateCalculation:
    base_rate: float
    final_rate: float
    spread: float
    source: str
    is_vwap: bool
    vwap_amount: Optional[float] = None
    timestamp: Optional[str] = None

class RatesCalculator:
    def __init__(self):
        self._rapira_provider: Optional[RapiraProvider] = None
        self._city_spreads = {
            "moscow": {"cash_in": 0.5, "cash_out": 0.5},
            "spb": {"cash_in": 0.6, "cash_out": 0.6},
            "other": {"cash_in": 1.0, "cash_out": 1.0}
        }
        self._percent_rules = {
            "default": {"cash_in": 0.0, "cash_out": 0.0},
            "premium": {"cash_in": -0.1, "cash_out": -0.1}
        }
        self._fixed_adjustments = {
            "USDT/RUB": {"cash_in": 0.0, "cash_out": 0.0},
            "BTC/USDT": {"cash_in": 0.0, "cash_out": 0.0}
        }
    
    async def get_rapira_provider(self) -> RapiraProvider:
        """Получает экземпляр RapiraProvider"""
        if not self._rapira_provider:
            self._rapira_provider = await get_rapira_provider()
        return self._rapira_provider
    
    async def calculate_rate(
        self,
        pair: str,
        operation: OperationType,
        amount_usd: Optional[float] = None,
        location: str = "moscow",
        use_vwap: bool = False,
        vwap_amount: float = 50000.0
    ) -> RateCalculation:
        """
        Рассчитывает финальный курс для операции
        
        Args:
            pair: Торговая пара (например, "USDT/RUB")
            operation: Тип операции (CASH_IN или CASH_OUT)
            amount_usd: Сумма в USD для расчета VWAP
            location: Локация для применения спреда
            use_vwap: Использовать ли VWAP вместо top-of-book
            vwap_amount: Сумма для VWAP расчета в USD
        
        Returns:
            RateCalculation с деталями расчета
        """
        try:
            provider = await self.get_rapira_provider()
            
            # Получаем базовый курс
            if use_vwap and amount_usd:
                base_rate = await self._get_vwap_rate(provider, pair, operation, amount_usd)
                is_vwap = True
                vwap_amount = amount_usd
            else:
                base_rate = await self._get_top_of_book_rate(provider, pair, operation)
                is_vwap = False
                vwap_amount = None
            
            # Применяем бизнес-правила
            final_rate = await self._apply_business_rules(
                base_rate, pair, operation, location
            )
            
            # Рассчитываем спред
            spread = ((final_rate - base_rate) / base_rate) * 100
            
            return RateCalculation(
                base_rate=base_rate,
                final_rate=final_rate,
                spread=spread,
                source="rapira",
                is_vwap=is_vwap,
                vwap_amount=vwap_amount,
                timestamp=provider.health.last_update.isoformat() if provider.health.last_update else None
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate rate for {pair} {operation.value}: {e}")
            # Fallback на последний известный курс
            return await self._get_fallback_rate(pair, operation, location)
    
    async def _get_vwap_rate(
        self,
        provider: RapiraProvider,
        pair: str,
        operation: OperationType,
        amount_usd: float
    ) -> float:
        """Получает VWAP курс для заданной суммы"""
        try:
            plate = await provider.get_plate_mini(pair)
            if not plate:
                raise ValueError(f"No plate data for {pair}")
            
            # Определяем сторону для VWAP
            side = Side.BID if operation == OperationType.CASH_IN else Side.ASK
            
            return await provider.calculate_vwap(plate, side, amount_usd)
            
        except Exception as e:
            logger.error(f"VWAP calculation failed for {pair}: {e}")
            # Fallback на top-of-book
            return await self._get_top_of_book_rate(provider, pair, operation)
    
    async def _get_top_of_book_rate(
        self,
        provider: RapiraProvider,
        pair: str,
        operation: OperationType
    ) -> float:
        """Получает top-of-book курс"""
        try:
            plate = await provider.get_plate_mini(pair)
            if not plate:
                raise ValueError(f"No plate data for {pair}")
            
            if operation == OperationType.CASH_IN:
                # Клиент отдает USDT, используем bid (рынок покупает USDT)
                if plate.best_bid:
                    return plate.best_bid.price
                elif plate.last_price:
                    return plate.last_price
            else:  # CASH_OUT
                # Клиент получает USDT, используем ask (рынок продает USDT)
                if plate.best_ask:
                    return plate.best_ask.price
                elif plate.last_price:
                    return plate.last_price
            
            raise ValueError(f"No price available for {pair} {operation.value}")
            
        except Exception as e:
            logger.error(f"Top-of-book rate failed for {pair}: {e}")
            raise
    
    async def _apply_business_rules(
        self,
        base_rate: float,
        pair: str,
        operation: OperationType,
        location: str
    ) -> float:
        """Применяет бизнес-правила к базовому курсу"""
        rate = base_rate
        
        # 1. Применяем спред по локации
        rate = self._apply_city_spread(rate, location, operation)
        
        # 2. Применяем процентные правила
        rate = self._apply_percent_rules(rate, location, operation)
        
        # 3. Применяем фиксированные корректировки
        rate = self._apply_fixed_adjustments(rate, pair, operation)
        
        # 4. Округляем согласно валюте котировки
        rate = self._round_by_quote_currency(rate, pair, operation)
        
        return rate
    
    def _apply_city_spread(self, rate: float, location: str, operation: OperationType) -> float:
        """Применяет спред по локации"""
        city = location.lower()
        if city not in self._city_spreads:
            city = "other"
        
        spread_percent = self._city_spreads[city][operation.value]
        return rate * (1 + spread_percent / 100)
    
    def _apply_percent_rules(self, rate: float, location: str, operation: OperationType) -> float:
        """Применяет процентные правила"""
        # В будущем можно добавить логику определения premium клиентов
        rule_type = "default"
        percent = self._percent_rules[rule_type][operation.value]
        return rate * (1 + percent / 100)
    
    def _apply_fixed_adjustments(self, rate: float, pair: str, operation: OperationType) -> float:
        """Применяет фиксированные корректировки"""
        if pair in self._fixed_adjustments:
            adjustment = self._fixed_adjustments[pair][operation.value]
            return rate + adjustment
        return rate
    
    def _round_by_quote_currency(self, rate: float, pair: str, operation: OperationType) -> float:
        """Округляет курс согласно валюте котировки"""
        # Определяем валюту котировки
        if "/" in pair:
            quote_currency = pair.split("/")[1]
        else:
            quote_currency = "RUB"  # По умолчанию
        
        if quote_currency == "RUB":
            # Округляем до копеек (2 знака после запятой)
            return round(rate, 2)
        elif quote_currency == "USD":
            # Округляем до центов (2 знака после запятой)
            return round(rate, 2)
        elif quote_currency == "USDT":
            # Округляем до 4 знаков после запятой
            return round(rate, 4)
        else:
            # По умолчанию округляем до 4 знаков
            return round(rate, 4)
    
    async def _get_fallback_rate(
        self,
        pair: str,
        operation: OperationType,
        location: str
    ) -> RateCalculation:
        """Получает fallback курс из БД"""
        try:
            from src.db import get_pg_pool
            
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT ask, bid, source, updated_at FROM rates WHERE pair = $1",
                    pair
                )
                
                if row:
                    # Используем соответствующий курс
                    if operation == OperationType.CASH_IN:
                        base_rate = float(row["bid"])
                    else:
                        base_rate = float(row["ask"])
                    
                    # Применяем бизнес-правила
                    final_rate = await self._apply_business_rules(
                        base_rate, pair, operation, location
                    )
                    
                    spread = ((final_rate - base_rate) / base_rate) * 100
                    
                    return RateCalculation(
                        base_rate=base_rate,
                        final_rate=final_rate,
                        spread=spread,
                        source=row["source"] or "database",
                        is_vwap=False,
                        timestamp=row["updated_at"].isoformat() if row["updated_at"] else None
                    )
                else:
                    raise ValueError(f"No fallback rate found for {pair}")
                    
        except Exception as e:
            logger.error(f"Fallback rate failed for {pair}: {e}")
            # Возвращаем дефолтный курс
            return RateCalculation(
                base_rate=100.0,  # Дефолтный курс
                final_rate=100.0,
                spread=0.0,
                source="default",
                is_vwap=False
            )
    
    def get_health_status(self) -> Dict:
        """Возвращает статус здоровья калькулятора"""
        if self._rapira_provider:
            health = self._rapira_provider.get_health()
            return {
                "provider": "rapira",
                "status": "healthy" if health.is_fresh else "stale",
                "latency_ms": health.latency,
                "last_update": health.last_update.isoformat() if health.last_update else None,
                "error_count": health.error_count,
                "last_error": health.last_error
            }
        else:
            return {
                "provider": "rapira",
                "status": "not_initialized",
                "latency_ms": 0,
                "last_update": None,
                "error_count": 0,
                "last_error": None
            }

# Глобальный экземпляр калькулятора
_calculator = None

async def get_rates_calculator() -> RatesCalculator:
    """Получает глобальный экземпляр RatesCalculator"""
    global _calculator
    if not _calculator:
        _calculator = RatesCalculator()
    return _calculator

# Удобные функции для быстрого доступа
async def calculate_exchange_rate(
    pair: str,
    operation: OperationType,
    amount_usd: Optional[float] = None,
    location: str = "moscow",
    use_vwap: bool = False
) -> RateCalculation:
    """Быстрый расчет курса обмена"""
    calculator = await get_rates_calculator()
    return await calculator.calculate_rate(
        pair=pair,
        operation=operation,
        amount_usd=amount_usd,
        location=location,
        use_vwap=use_vwap
    )

async def get_rapira_health() -> Dict:
    """Получает статус здоровья Rapira провайдера"""
    calculator = await get_rates_calculator()
    return calculator.get_health_status()
