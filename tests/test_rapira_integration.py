import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.rapira import RapiraProvider, Side, OrderLevel, PlateMini
from src.services.rates_calculator import RatesCalculator, OperationType, RateCalculation
from src.services.rates_scheduler import RatesScheduler

class TestRapiraProvider:
    """Тесты для RapiraProvider"""
    
    @pytest.fixture
    def provider(self):
        return RapiraProvider()
    
    @pytest.fixture
    def mock_plate_data(self):
        return {
            "symbol": "USDT/RUB",
            "ts": "2024-01-01T12:00:00Z",
            "bestBid": {"price": 95.0, "qty": 1000.0},
            "bestAsk": {"price": 95.5, "qty": 1000.0},
            "bids": [
                {"price": 95.0, "qty": 1000.0},
                {"price": 94.9, "qty": 2000.0},
                {"price": 94.8, "qty": 3000.0}
            ],
            "asks": [
                {"price": 95.5, "qty": 1000.0},
                {"price": 95.6, "qty": 2000.0},
                {"price": 95.7, "qty": 3000.0}
            ],
            "lastPrice": 95.25,
            "lastQty": 500.0,
            "lastTs": "2024-01-01T12:00:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_get_plate_mini_success(self, provider, mock_plate_data):
        """Тест успешного получения plate mini"""
        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_plate_data, 50.0)
            
            plate = await provider.get_plate_mini("USDT/RUB")
            
            assert plate is not None
            assert plate.symbol == "USDT/RUB"
            assert plate.best_bid.price == 95.0
            assert plate.best_ask.price == 95.5
            assert len(plate.bids) == 3
            assert len(plate.asks) == 3
            assert plate.last_price == 95.25
    
    @pytest.mark.asyncio
    async def test_calculate_vwap_bid_side(self, provider, mock_plate_data):
        """Тест расчета VWAP для bid стороны"""
        plate = PlateMini(
            symbol="USDT/RUB",
            ts="2024-01-01T12:00:00Z",
            bids=[
                OrderLevel(price=95.0, qty=1000.0),
                OrderLevel(price=94.9, qty=2000.0),
                OrderLevel(price=94.8, qty=3000.0)
            ]
        )
        
        vwap = await provider.calculate_vwap(plate, Side.BID, 5000.0)
        
        # Ожидаемый VWAP: (95.0*1000 + 94.9*2000 + 94.8*2000) / 5000
        expected_vwap = (95.0*1000 + 94.9*2000 + 94.8*2000) / 5000
        assert abs(vwap - expected_vwap) < 0.01
    
    @pytest.mark.asyncio
    async def test_calculate_vwap_ask_side(self, provider, mock_plate_data):
        """Тест расчета VWAP для ask стороны"""
        plate = PlateMini(
            symbol="USDT/RUB",
            ts="2024-01-01T12:00:00Z",
            asks=[
                OrderLevel(price=95.5, qty=1000.0),
                OrderLevel(price=95.6, qty=2000.0),
                OrderLevel(price=95.7, qty=3000.0)
            ]
        )
        
        vwap = await provider.calculate_vwap(plate, Side.ASK, 5000.0)
        
        # Ожидаемый VWAP: (95.5*1000 + 95.6*2000 + 95.7*2000) / 5000
        expected_vwap = (95.5*1000 + 95.6*2000 + 95.7*2000) / 5000
        assert abs(vwap - expected_vwap) < 0.01
    
    @pytest.mark.asyncio
    async def test_fallback_to_cache(self, provider):
        """Тест fallback на кэш при недоступности API"""
        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API недоступен")
            
            # Мокаем Redis
            with patch.object(provider, 'get_redis', new_callable=AsyncMock) as mock_redis:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.get.return_value = '{"symbol": "USDT/RUB", "last_price": 95.0}'
                mock_redis.return_value = mock_redis_instance
                
                plate = await provider.get_plate_mini("USDT/RUB")
                
                assert plate is not None
                assert plate.last_price == 95.0

class TestRatesCalculator:
    """Тесты для RatesCalculator"""
    
    @pytest.fixture
    def calculator(self):
        return RatesCalculator()
    
    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.get_plate_mini = AsyncMock()
        provider.calculate_vwap = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_calculate_rate_cash_in(self, calculator, mock_provider):
        """Тест расчета курса для CASH_IN операции"""
        with patch.object(calculator, 'get_rapira_provider', return_value=mock_provider):
            # Мокаем plate
            mock_plate = PlateMini(
                symbol="USDT/RUB",
                ts="2024-01-01T12:00:00Z",
                best_bid=OrderLevel(price=95.0, qty=1000.0)
            )
            mock_provider.get_plate_mini.return_value = mock_plate
            
            rate = await calculator.calculate_rate(
                "USDT/RUB", 
                OperationType.CASH_IN, 
                location="moscow"
            )
            
            assert rate.base_rate == 95.0
            assert rate.final_rate > 95.0  # Должен быть выше из-за спреда
            assert rate.operation == OperationType.CASH_IN
            assert rate.source == "rapira"
    
    @pytest.mark.asyncio
    async def test_calculate_rate_cash_out(self, calculator, mock_provider):
        """Тест расчета курса для CASH_OUT операции"""
        with patch.object(calculator, 'get_rapira_provider', return_value=mock_provider):
            # Мокаем plate
            mock_plate = PlateMini(
                symbol="USDT/RUB",
                ts="2024-01-01T12:00:00Z",
                best_ask=OrderLevel(price=95.5, qty=1000.0)
            )
            mock_provider.get_plate_mini.return_value = mock_plate
            
            rate = await calculator.calculate_rate(
                "USDT/RUB", 
                OperationType.CASH_OUT, 
                location="moscow"
            )
            
            assert rate.base_rate == 95.5
            assert rate.final_rate > 95.5  # Должен быть выше из-за спреда
            assert rate.operation == OperationType.CASH_OUT
            assert rate.source == "rapira"
    
    @pytest.mark.asyncio
    async def test_calculate_rate_with_vwap(self, calculator, mock_provider):
        """Тест расчета курса с VWAP"""
        with patch.object(calculator, 'get_rapira_provider', return_value=mock_provider):
            mock_provider.calculate_vwap.return_value = 94.8
            
            rate = await calculator.calculate_rate(
                "USDT/RUB", 
                OperationType.CASH_IN, 
                amount_usd=50000.0,
                use_vwap=True,
                location="moscow"
            )
            
            assert rate.is_vwap is True
            assert rate.vwap_amount == 50000.0
            assert rate.base_rate == 94.8
    
    def test_apply_city_spread(self, calculator):
        """Тест применения спреда по локации"""
        base_rate = 100.0
        
        # Москва: 0.5% спред
        moscow_rate = calculator._apply_city_spread(base_rate, "moscow", OperationType.CASH_IN)
        assert moscow_rate == 100.5
        
        # СПб: 0.6% спред
        spb_rate = calculator._apply_city_spread(base_rate, "spb", OperationType.CASH_IN)
        assert spb_rate == 100.6
        
        # Другой город: 1.0% спред
        other_rate = calculator._apply_city_spread(base_rate, "other", OperationType.CASH_IN)
        assert other_rate == 101.0
    
    def test_round_by_quote_currency(self, calculator):
        """Тест округления по валюте котировки"""
        # RUB: округление до 2 знаков
        rub_rate = calculator._round_by_quote_currency(95.12345, "USDT/RUB", OperationType.CASH_IN)
        assert rub_rate == 95.12
        
        # USDT: округление до 4 знаков
        usdt_rate = calculator._round_by_quote_currency(1.12345678, "BTC/USDT", OperationType.CASH_IN)
        assert usdt_rate == 1.1235

class TestRatesScheduler:
    """Тесты для RatesScheduler"""
    
    @pytest.fixture
    def scheduler(self):
        return RatesScheduler()
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Тест запуска и остановки планировщика"""
        assert not scheduler._is_running
        
        await scheduler.start(update_interval=1)
        assert scheduler._is_running
        assert scheduler._update_interval == 1
        
        await scheduler.stop()
        assert not scheduler._is_running
    
    @pytest.mark.asyncio
    async def test_force_update(self, scheduler):
        """Тест принудительного обновления"""
        with patch('src.services.rates.import_rapira_rates', new_callable=AsyncMock) as mock_import:
            mock_import.return_value = 3  # Обновлено 3 пары
            
            result = await scheduler.force_update()
            
            assert result["success"] is True
            assert result["updated_count"] == 3
            assert "timestamp" in result
            assert "duration_ms" in result
    
    def test_get_status(self, scheduler):
        """Тест получения статуса планировщика"""
        status = scheduler.get_status()
        
        assert "is_running" in status
        assert "update_interval" in status
        assert "last_update" in status
        assert "update_count" in status
        assert "error_count" in status

@pytest.mark.asyncio
async def test_integration_workflow():
    """Интеграционный тест полного workflow"""
    # Создаем провайдер
    provider = RapiraProvider()
    
    # Мокаем HTTP запросы
    with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ({
            "symbol": "USDT/RUB",
            "ts": "2024-01-01T12:00:00Z",
            "bestBid": {"price": 95.0, "qty": 1000.0},
            "bestAsk": {"price": 95.5, "qty": 1000.0},
            "lastPrice": 95.25
        }, 50.0)
        
        # Получаем plate
        plate = await provider.get_plate_mini("USDT/RUB")
        assert plate is not None
        
        # Рассчитываем VWAP
        vwap = await provider.calculate_vwap(plate, Side.BID, 1000.0)
        assert vwap == 95.0  # Для суммы 1000 USDT используем только первый уровень
        
        # Создаем калькулятор
        calculator = RatesCalculator()
        with patch.object(calculator, 'get_rapira_provider', return_value=provider):
            # Рассчитываем курс
            rate = await calculator.calculate_rate(
                "USDT/RUB",
                OperationType.CASH_IN,
                location="moscow"
            )
            
            assert rate.base_rate == 95.0
            assert rate.final_rate > 95.0
            assert rate.source == "rapira"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
