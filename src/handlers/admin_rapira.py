import logging
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.services.rapira import get_rapira_provider
from src.services.rates_calculator import get_rates_calculator
from src.services.rates_scheduler import get_scheduler_status, force_update_rates
from src.services.rates import get_current_rate, calculate_vwap_rate
from src.services.rates_calculator import OperationType

logger = logging.getLogger(__name__)
router = Router()

class RapiraAdminStates(StatesGroup):
    waiting_for_vwap_amount = State()
    waiting_for_pair = State()
    waiting_for_operation = State()

@router.message(Command("rapira_status"))
async def cmd_rapira_status(message: types.Message):
    """Показывает статус интеграции с Rapira"""
    try:
        # Получаем статус планировщика
        scheduler_status = await get_scheduler_status()
        
        # Получаем статус провайдера
        provider = await get_rapira_provider()
        provider_health = provider.get_health()
        
        # Формируем сообщение
        status_text = "📊 **Статус интеграции с Rapira API**\n\n"
        
        # Статус планировщика
        status_text += "🔄 **Планировщик курсов:**\n"
        status_text += f"• Статус: {'🟢 Работает' if scheduler_status['is_running'] else '🔴 Остановлен'}\n"
        status_text += f"• Интервал: {scheduler_status['update_interval']} сек\n"
        status_text += f"• Последнее обновление: {scheduler_status['last_update'] or 'Никогда'}\n"
        status_text += f"• Обновлений: {scheduler_status['update_count']}\n"
        status_text += f"• Ошибок: {scheduler_status['error_count']}\n"
        
        if scheduler_status['last_error']:
            status_text += f"• Последняя ошибка: {scheduler_status['last_error']}\n"
        
        # Статус провайдера
        status_text += "\n🌐 **Rapira API:**\n"
        status_text += f"• Статус: {'🟢 Активен' if provider_health.is_fresh else '🟡 Устарел'}\n"
        status_text += f"• Задержка: {provider_health.latency:.1f} мс\n"
        status_text += f"• HTTP код: {provider_health.http_code}\n"
        status_text += f"• Последнее обновление: {provider_health.last_update.strftime('%H:%M:%S') if provider_health.last_update else 'Никогда'}\n"
        status_text += f"• Ошибок: {provider_health.error_count}\n"
        
        if provider_health.last_error:
            status_text += f"• Последняя ошибка: {provider_health.last_error}\n"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить курсы", callback_data="rapira_force_update"),
                InlineKeyboardButton(text="📊 Детальный статус", callback_data="rapira_detailed_status")
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="rapira_settings"),
                InlineKeyboardButton(text="🧪 Тест API", callback_data="rapira_test_api")
            ]
        ])
        
        await message.answer(status_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to get Rapira status: {e}")
        await message.answer(f"❌ Ошибка получения статуса: {e}")

@router.callback_query(lambda c: c.data == "rapira_force_update")
async def rapira_force_update(callback: types.CallbackQuery):
    """Принудительно обновляет курсы из Rapira"""
    try:
        await callback.answer("🔄 Обновление курсов...")
        
        result = await force_update_rates()
        
        if result["success"]:
            await callback.message.edit_text(
                f"✅ **Курсы обновлены успешно!**\n\n"
                f"• Обновлено пар: {result['updated_count']}\n"
                f"• Время: {result['timestamp']}\n"
                f"• Длительность: {result['duration_ms']:.1f} мс",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                f"❌ **Ошибка обновления курсов**\n\n"
                f"• Ошибка: {result['error']}\n"
                f"• Время: {result['timestamp']}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Force update failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {e}")

@router.callback_query(lambda c: c.data == "rapira_detailed_status")
async def rapira_detailed_status(callback: types.CallbackQuery):
    """Показывает детальный статус"""
    try:
        await callback.answer("📊 Получение детального статуса...")
        
        # Получаем детальную информацию
        provider = await get_rapira_provider()
        calculator = await get_rates_calculator()
        
        # Проверяем доступные пары
        pairs = ["USDT/RUB", "BTC/USDT", "EUR/USDT"]
        rates_info = []
        
        for pair in pairs:
            try:
                # Получаем курсы для обеих операций
                cash_in = await get_current_rate(pair, OperationType.CASH_IN)
                cash_out = await get_current_rate(pair, OperationType.CASH_OUT)
                
                rates_info.append({
                    "pair": pair,
                    "cash_in": cash_in,
                    "cash_out": cash_out
                })
            except Exception as e:
                rates_info.append({
                    "pair": pair,
                    "error": str(e)
                })
        
        # Формируем детальный отчет
        detailed_text = "📊 **Детальный статус Rapira API**\n\n"
        
        for info in rates_info:
            detailed_text += f"**{info['pair']}:**\n"
            
            if "error" in info:
                detailed_text += f"❌ Ошибка: {info['error']}\n"
            else:
                detailed_text += f"• CASH_IN: {info['cash_in'].final_rate:.4f} (спред: {info['cash_in'].spread:.2f}%)\n"
                detailed_text += f"• CASH_OUT: {info['cash_out'].final_rate:.4f} (спред: {info['cash_out'].spread:.2f}%)\n"
                detailed_text += f"• Источник: {info['cash_in'].source}\n"
                detailed_text += f"• Время: {info['cash_in'].timestamp or 'Неизвестно'}\n"
            
            detailed_text += "\n"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="rapira_back_to_status")]
        ])
        
        await callback.message.edit_text(detailed_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Detailed status failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения детального статуса: {e}")

@router.callback_query(lambda c: c.data == "rapira_back_to_status")
async def rapira_back_to_status(callback: types.CallbackQuery):
    """Возврат к основному статусу"""
    await cmd_rapira_status(callback.message)

@router.callback_query(lambda c: c.data == "rapira_test_api")
async def rapira_test_api(callback: types.CallbackQuery):
    """Тестирует API Rapira"""
    try:
        await callback.answer("🧪 Тестирование API...")
        
        provider = await get_rapira_provider()
        
        # Тестируем получение курсов
        test_results = []
        
        # Тест 1: Получение plate mini
        try:
            plate = await provider.get_plate_mini("USDT/RUB")
            if plate:
                test_results.append("✅ Plate mini API работает")
            else:
                test_results.append("❌ Plate mini API не вернул данные")
        except Exception as e:
            test_results.append(f"❌ Plate mini API ошибка: {e}")
        
        # Тест 2: Получение rates
        try:
            rates = await provider.get_rates()
            if rates:
                test_results.append(f"✅ Rates API работает ({len(rates)} пар)")
            else:
                test_results.append("❌ Rates API не вернул данные")
        except Exception as e:
            test_results.append(f"❌ Rates API ошибка: {e}")
        
        # Тест 3: Расчет курса
        try:
            calculator = await get_rates_calculator()
            rate = await calculator.calculate_rate("USDT/RUB", OperationType.CASH_IN)
            test_results.append(f"✅ Расчет курса работает: {rate.final_rate:.2f}")
        except Exception as e:
            test_results.append(f"❌ Расчет курса ошибка: {e}")
        
        # Формируем результат
        test_text = "🧪 **Результаты тестирования Rapira API**\n\n"
        test_text += "\n".join(test_results)
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="rapira_back_to_status")]
        ])
        
        await callback.message.edit_text(test_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"API test failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка тестирования: {e}")

@router.callback_query(lambda c: c.data == "rapira_settings")
async def rapira_settings(callback: types.CallbackQuery):
    """Показывает настройки интеграции"""
    try:
        await callback.answer("⚙️ Настройки интеграции")
        
        # Получаем текущие настройки
        from src.services.rapira import (
            CACHE_TTL, STALE_TTL, REQUEST_TIMEOUT, 
            MAX_RETRIES, VWAP_DEFAULT_AMOUNT
        )
        
        settings_text = "⚙️ **Настройки интеграции с Rapira**\n\n"
        settings_text += f"• **Кэш TTL:** {CACHE_TTL} сек\n"
        settings_text += f"• **Устаревание:** {STALE_TTL} сек\n"
        settings_text += f"• **Таймаут запроса:** {REQUEST_TIMEOUT} сек\n"
        settings_text += f"• **Макс. попыток:** {MAX_RETRIES}\n"
        settings_text += f"• **VWAP сумма по умолчанию:** ${VWAP_DEFAULT_AMOUNT:,.0f}\n"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить интервал", callback_data="rapira_change_interval"),
                InlineKeyboardButton(text="💾 Изменить кэш", callback_data="rapira_change_cache")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="rapira_back_to_status")]
        ])
        
        await callback.message.edit_text(settings_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Settings failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения настроек: {e}")

@router.message(Command("rapira_vwap"))
async def cmd_rapira_vwap(message: types.Message, state: FSMContext):
    """Запускает расчет VWAP курса"""
    await state.set_state(RapiraAdminStates.waiting_for_vwap_amount)
    await message.answer(
        "💰 **Расчет VWAP курса**\n\n"
        "Введите сумму в USD для расчета VWAP (например: 50000):",
        parse_mode="Markdown"
    )

@router.message(RapiraAdminStates.waiting_for_vwap_amount)
async def process_vwap_amount(message: types.Message, state: FSMContext):
    """Обрабатывает введенную сумму для VWAP"""
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        await state.update_data(vwap_amount=amount)
        await state.set_state(RapiraAdminStates.waiting_for_pair)
        
        await message.answer(
            f"📊 **Сумма: ${amount:,.0f}**\n\n"
            "Теперь введите торговую пару (например: USDT/RUB):",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await message.answer("❌ Некорректная сумма. Введите число (например: 50000)")

@router.message(RapiraAdminStates.waiting_for_pair)
async def process_vwap_pair(message: types.Message, state: FSMContext):
    """Обрабатывает введенную пару для VWAP"""
    pair = message.text.strip().upper()
    
    # Проверяем формат пары
    if "/" not in pair:
        await message.answer("❌ Неверный формат пары. Используйте формат BASE/QUOTE (например: USDT/RUB)")
        return
    
    await state.update_data(pair=pair)
    await state.set_state(RapiraAdminStates.waiting_for_operation)
    
    # Кнопки выбора операции
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 CASH_IN (клиент отдает USDT)", callback_data="vwap_cash_in"),
            InlineKeyboardButton(text="💵 CASH_OUT (клиент получает USDT)", callback_data="vwap_cash_out")
        ]
    ])
    
    await message.answer(
        f"📊 **Пара: {pair}**\n\n"
        "Выберите тип операции:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data.startswith("vwap_"))
async def process_vwap_operation(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор операции для VWAP"""
    try:
        operation_type = callback.data.replace("vwap_", "")
        operation = OperationType.CASH_IN if operation_type == "cash_in" else OperationType.CASH_OUT
        
        # Получаем данные из состояния
        data = await state.get_data()
        amount = data.get("vwap_amount")
        pair = data.get("pair")
        
        await callback.answer("🧮 Расчет VWAP...")
        
        # Рассчитываем VWAP курс
        rate = await calculate_vwap_rate(pair, operation, amount)
        
        # Формируем результат
        result_text = f"💰 **VWAP курс для {pair}**\n\n"
        result_text += f"• **Операция:** {operation.value.upper()}\n"
        result_text += f"• **Сумма:** ${amount:,.0f}\n"
        result_text += f"• **Базовый курс:** {rate.base_rate:.4f}\n"
        result_text += f"• **Финальный курс:** {rate.final_rate:.4f}\n"
        result_text += f"• **Спред:** {rate.spread:.2f}%\n"
        result_text += f"• **Источник:** {rate.source}\n"
        result_text += f"• **VWAP:** {'Да' if rate.is_vwap else 'Нет'}\n"
        
        if rate.timestamp:
            result_text += f"• **Время:** {rate.timestamp}\n"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к статусу", callback_data="rapira_back_to_status")]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"VWAP calculation failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка расчета VWAP: {e}")
        await state.clear()

@router.message(Command("rapira_help"))
async def cmd_rapira_help(message: types.Message):
    """Показывает справку по командам Rapira"""
    help_text = "📚 **Справка по командам Rapira API**\n\n"
    help_text += "**Основные команды:**\n"
    help_text += "• `/rapira_status` - Статус интеграции\n"
    help_text += "• `/rapira_vwap` - Расчет VWAP курса\n"
    help_text += "• `/rapira_help` - Эта справка\n\n"
    
    help_text += "**Функции:**\n"
    help_text += "• Автоматическое обновление курсов каждые 5 сек\n"
    help_text += "• Поддержка VWAP для больших сумм\n"
    help_text += "• Fallback на БД при недоступности API\n"
    help_text += "• Мониторинг здоровья API\n"
    help_text += "• Применение бизнес-правил (спреды, корректировки)\n\n"
    
    help_text += "**Поддерживаемые пары:**\n"
    help_text += "• USDT/RUB, BTC/USDT, EUR/USDT\n\n"
    
    help_text += "**Типы операций:**\n"
    help_text += "• CASH_IN - клиент отдает USDT, получает RUB\n"
    help_text += "• CASH_OUT - клиент отдает RUB, получает USDT"
    
    await message.answer(help_text, parse_mode="Markdown")
