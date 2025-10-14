"""
Тесты для FX модуля (валютные курсы с наценками)
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.services.fx_rates import FXRatesService, RoundingMode


class TestMarkupCalculations:
    """Тесты вычисления наценок"""
    
    def test_percent_markup(self):
        """Тест процентной наценки"""
        service = FXRatesService()
        
        # Создаем мок-правило
        class MockRule:
            percent = Decimal('2.5')
            fixed = Decimal('0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('100.00')
        
        result = service._apply_markup(raw_price, rule)
        
        # 100 * (1 + 2.5/100) = 102.50
        assert result == Decimal('102.50')
    
    def test_fixed_markup(self):
        """Тест фиксированной наценки"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('0')
            fixed = Decimal('5.0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('100.00')
        
        result = service._apply_markup(raw_price, rule)
        
        # 100 + 5 = 105.00
        assert result == Decimal('105.00')
    
    def test_combined_markup(self):
        """Тест комбинированной наценки (процент + фикс)"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('2.5')
            fixed = Decimal('5.0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('100.00')
        
        result = service._apply_markup(raw_price, rule)
        
        # 100 * 1.025 = 102.5
        # 102.5 + 5 = 107.50
        assert result == Decimal('107.50')
    
    def test_negative_percent_discount(self):
        """Тест отрицательного процента (скидка)"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('-1.5')
            fixed = Decimal('0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('100.00')
        
        result = service._apply_markup(raw_price, rule)
        
        # 100 * (1 - 1.5/100) = 98.50
        assert result == Decimal('98.50')
    
    def test_rounding_modes(self):
        """Тест различных режимов округления"""
        service = FXRatesService()
        
        # ROUND_HALF_UP
        assert service._round_price(Decimal('1.235'), 'ROUND_HALF_UP', 2) == Decimal('1.24')
        assert service._round_price(Decimal('1.234'), 'ROUND_HALF_UP', 2) == Decimal('1.23')
        
        # ROUND_DOWN
        assert service._round_price(Decimal('1.239'), 'ROUND_DOWN', 2) == Decimal('1.23')
        
        # ROUND_UP
        assert service._round_price(Decimal('1.231'), 'ROUND_UP', 2) == Decimal('1.24')
        
        # BANKERS (ROUND_HALF_EVEN)
        assert service._round_price(Decimal('1.235'), 'BANKERS', 2) == Decimal('1.24')
        assert service._round_price(Decimal('1.225'), 'BANKERS', 2) == Decimal('1.22')
    
    def test_decimal_precision(self):
        """Тест точности десятичных знаков"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('0')
            fixed = Decimal('0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 8
        
        rule = MockRule()
        raw_price = Decimal('123.456789123')
        
        result = service._apply_markup(raw_price, rule)
        
        # Должно округлить до 8 знаков
        assert result == Decimal('123.45678912')


class TestRulePriority:
    """Тесты приоритета правил"""
    
    def test_pair_rule_priority(self):
        """Тест что правило для пары имеет приоритет над остальными"""
        service = FXRatesService()
        
        # Мокируем правила с разными уровнями
        class MockRule:
            def __init__(self, level, source_id, pair_id, percent):
                self.level = level
                self.source_id = source_id
                self.source_pair_id = pair_id
                self.percent = percent
                self.enabled = True
                self.valid_from = None
                self.valid_to = None
        
        service._rules_cache = [
            MockRule('pair', 1, 10, Decimal('3.0')),    # Приоритет 1
            MockRule('source', 1, None, Decimal('2.0')), # Приоритет 2
            MockRule('global', None, None, Decimal('1.0')) # Приоритет 3
        ]
        
        # Должно вернуть правило для пары
        rule = service._find_applicable_rule(source_id=1, pair_id=10)
        assert rule.level == 'pair'
        assert rule.percent == Decimal('3.0')
    
    def test_source_rule_priority(self):
        """Тест что правило для источника применяется если нет правила для пары"""
        service = FXRatesService()
        
        class MockRule:
            def __init__(self, level, source_id, pair_id, percent):
                self.level = level
                self.source_id = source_id
                self.source_pair_id = pair_id
                self.percent = percent
                self.enabled = True
                self.valid_from = None
                self.valid_to = None
        
        service._rules_cache = [
            MockRule('source', 1, None, Decimal('2.0')),
            MockRule('global', None, None, Decimal('1.0'))
        ]
        
        # Должно вернуть правило для источника
        rule = service._find_applicable_rule(source_id=1, pair_id=10)
        assert rule.level == 'source'
        assert rule.percent == Decimal('2.0')
    
    def test_global_rule_fallback(self):
        """Тест что глобальное правило применяется как fallback"""
        service = FXRatesService()
        
        class MockRule:
            def __init__(self, level, source_id, pair_id, percent):
                self.level = level
                self.source_id = source_id
                self.source_pair_id = pair_id
                self.percent = percent
                self.enabled = True
                self.valid_from = None
                self.valid_to = None
        
        service._rules_cache = [
            MockRule('global', None, None, Decimal('1.0'))
        ]
        
        # Должно вернуть глобальное правило
        rule = service._find_applicable_rule(source_id=1, pair_id=10)
        assert rule.level == 'global'
        assert rule.percent == Decimal('1.0')
    
    def test_no_rule_found(self):
        """Тест когда нет подходящего правила"""
        service = FXRatesService()
        service._rules_cache = []
        
        rule = service._find_applicable_rule(source_id=1, pair_id=10)
        assert rule is None


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_zero_markup(self):
        """Тест нулевой наценки"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('0')
            fixed = Decimal('0')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('100.00')
        
        result = service._apply_markup(raw_price, rule)
        assert result == Decimal('100.00')
    
    def test_very_small_price(self):
        """Тест очень малой цены"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('10')
            fixed = Decimal('0.01')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 8
        
        rule = MockRule()
        raw_price = Decimal('0.00000001')
        
        result = service._apply_markup(raw_price, rule)
        # 0.00000001 * 1.1 + 0.01 = 0.01000001
        assert result == Decimal('0.01000001')
    
    def test_very_large_price(self):
        """Тест очень большой цены"""
        service = FXRatesService()
        
        class MockRule:
            percent = Decimal('0.5')
            fixed = Decimal('1000')
            rounding_mode = 'ROUND_HALF_UP'
            round_to = 2
        
        rule = MockRule()
        raw_price = Decimal('1000000.00')
        
        result = service._apply_markup(raw_price, rule)
        # 1000000 * 1.005 + 1000 = 1006000.00
        assert result == Decimal('1006000.00')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

