import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.services.grinex import get_grinex_client
from src.services.fx_rates import get_fx_service
from src.services.fx_scheduler import get_fx_scheduler

logger = logging.getLogger(__name__)
router = Router()

class GrinexAdminStates(StatesGroup):
    waiting_for_pair = State()
    waiting_for_amount = State()

@router.message(Command("grinex_status"))
async def cmd_grinex_status(message: types.Message):
    """Показывает статус интеграции с Grinex"""
    try:
        # Получаем клиент и планировщик
        client = await get_grinex_client()
        health = client.get_health()
        scheduler = await get_fx_scheduler()
        scheduler_status = scheduler.get_status()
        
        # Формируем сообщение
        status_text = "📊 **Статус интеграции с Grinex Exchange**\n\n"
        
        # Статус API
        status_text += "🌐 **Grinex API:**\n"
        status_text += f"• Статус: {'🟢 Активен' if health.is_available else '🔴 Недоступен'}\n"
        status_text += f"• Задержка: {health.latency_ms:.1f} мс\n"
        status_text += f"• HTTP код: {health.http_code}\n"
        status_text += f"• Последнее обновление: {health.last_update.strftime('%H:%M:%S')}\n"
        status_text += f"• Ошибок: {health.error_count}\n"
        
        if health.last_error:
            status_text += f"• Последняя ошибка: {health.last_error[:100]}\n"
        
        # Статус планировщика FX
        status_text += "\n🔄 **FX Планировщик:**\n"
        status_text += f"• Статус: {'🟢 Работает' if scheduler_status['running'] else '🔴 Остановлен'}\n"
        
        if scheduler_status['last_sync'].get('grinex'):
            status_text += f"• Последняя синхронизация Grinex: {scheduler_status['last_sync']['grinex']}\n"
        
        if scheduler_status['config']:
            status_text += f"• Интервал обновления: {scheduler_status['config']['update_interval_seconds']} сек\n"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Синхронизировать", callback_data="grinex_sync"),
                InlineKeyboardButton(text="📊 Курсы", callback_data="grinex_rates")
            ],
            [
                InlineKeyboardButton(text="📈 Тикеры", callback_data="grinex_tickers"),
                InlineKeyboardButton(text="🧪 Тест API", callback_data="grinex_test")
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="grinex_settings")
            ]
        ])
        
        await message.answer(status_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to get Grinex status: {e}")
        await message.answer(f"❌ Ошибка получения статуса: {e}")

@router.callback_query(lambda c: c.data == "grinex_sync")
async def grinex_sync(callback: types.CallbackQuery):
    """Принудительная синхронизация курсов Grinex"""
    try:
        await callback.answer("🔄 Синхронизация курсов Grinex...")
        
        scheduler = await get_fx_scheduler()
        result = await scheduler.trigger_sync('grinex')
        
        if result.get('status') == 'success':
            await callback.message.edit_text(
                f"✅ **Синхронизация Grinex завершена успешно!**\n\n"
                f"• Обработано пар: {result.get('pairs_processed', 0)}\n"
                f"• Успешно: {result.get('pairs_succeeded', 0)}\n"
                f"• Ошибок: {result.get('pairs_failed', 0)}\n"
                f"• Длительность: {result.get('duration_ms', 0)} мс",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                f"⚠️ **Синхронизация Grinex завершена с ошибками**\n\n"
                f"• Обработано пар: {result.get('pairs_processed', 0)}\n"
                f"• Успешно: {result.get('pairs_succeeded', 0)}\n"
                f"• Ошибок: {result.get('pairs_failed', 0)}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Grinex sync failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка синхронизации: {e}")

@router.callback_query(lambda c: c.data == "grinex_rates")
async def grinex_rates(callback: types.CallbackQuery):
    """Показывает текущие курсы из Grinex"""
    try:
        await callback.answer("📊 Загрузка курсов...")
        
        fx_service = await get_fx_service()
        rates = await fx_service.get_all_final_rates(source_code='grinex', allow_stale=True)
        
        if not rates:
            await callback.message.edit_text(
                "📊 **Курсы Grinex**\n\n"
                "Нет доступных курсов. Запустите синхронизацию.",
                parse_mode="Markdown"
            )
            return
        
        rates_text = "📊 **Текущие курсы Grinex**\n\n"
        
        for rate in rates[:10]:  # Ограничиваем 10 парами
            stale_mark = "🟡" if rate.stale else "🟢"
            rates_text += f"{stale_mark} **{rate.internal_symbol}**\n"
            rates_text += f"  • Raw: {rate.raw_price:.8f}\n"
            rates_text += f"  • Final: {rate.final_price:.8f}\n"
            
            if rate.markup_percent or rate.markup_fixed:
                rates_text += f"  • Наценка: {rate.markup_percent or 0}% + {rate.markup_fixed or 0}\n"
            
            rates_text += f"  • Обновлено: {rate.calculated_at.strftime('%H:%M:%S')}\n\n"
        
        if len(rates) > 10:
            rates_text += f"\n_...и еще {len(rates) - 10} пар_"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_back")]
        ])
        
        await callback.message.edit_text(rates_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to get Grinex rates: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения курсов: {e}")

@router.callback_query(lambda c: c.data == "grinex_tickers")
async def grinex_tickers(callback: types.CallbackQuery):
    """Показывает тикеры с Grinex (raw данные)"""
    try:
        await callback.answer("📈 Загрузка тикеров...")
        
        client = await get_grinex_client()
        tickers = await client.get_all_tickers()
        
        if not tickers:
            await callback.message.edit_text(
                "📈 **Тикеры Grinex**\n\n"
                "Нет доступных тикеров или API недоступен.",
                parse_mode="Markdown"
            )
            return
        
        tickers_text = "📈 **Тикеры Grinex (Raw)**\n\n"
        
        # Показываем первые 8 тикеров
        for symbol, ticker in list(tickers.items())[:8]:
            tickers_text += f"**{symbol}**\n"
            tickers_text += f"  • Price: {ticker.last_price}\n"
            
            if ticker.bid and ticker.ask:
                tickers_text += f"  • Bid/Ask: {ticker.bid} / {ticker.ask}\n"
            
            if ticker.volume_24h:
                tickers_text += f"  • Volume 24h: {ticker.volume_24h}\n"
            
            if ticker.change_24h:
                change_emoji = "🟢" if ticker.change_24h > 0 else "🔴"
                tickers_text += f"  • Change 24h: {change_emoji} {ticker.change_24h}%\n"
            
            tickers_text += "\n"
        
        if len(tickers) > 8:
            tickers_text += f"\n_Всего тикеров: {len(tickers)}_"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_back")]
        ])
        
        await callback.message.edit_text(tickers_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to get Grinex tickers: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения тикеров: {e}")

@router.callback_query(lambda c: c.data == "grinex_test")
async def grinex_test(callback: types.CallbackQuery):
    """Тестирует Grinex API"""
    try:
        await callback.answer("🧪 Тестирование Grinex API...")
        
        client = await get_grinex_client()
        test_results = []
        
        # Тест 1: Получение одного тикера
        try:
            ticker = await client.get_ticker("USDTRUB")
            if ticker:
                test_results.append(f"✅ get_ticker('USDTRUB'): {ticker.last_price}")
            else:
                test_results.append("❌ get_ticker('USDTRUB'): Нет данных")
        except Exception as e:
            test_results.append(f"❌ get_ticker ошибка: {str(e)[:50]}")
        
        # Тест 2: Получение всех тикеров
        try:
            tickers = await client.get_all_tickers()
            if tickers:
                test_results.append(f"✅ get_all_tickers(): {len(tickers)} пар")
            else:
                test_results.append("❌ get_all_tickers(): Нет данных")
        except Exception as e:
            test_results.append(f"❌ get_all_tickers ошибка: {str(e)[:50]}")
        
        # Тест 3: Health статус
        health = client.get_health()
        test_results.append(f"{'✅' if health.is_available else '❌'} Health: latency={health.latency_ms:.1f}ms, errors={health.error_count}")
        
        # Тест 4: Синхронизация через FX сервис
        try:
            fx_service = await get_fx_service()
            result = await fx_service.sync_source_rates('grinex')
            if result['status'] == 'success':
                test_results.append(f"✅ FX sync: {result['pairs_succeeded']}/{result['pairs_processed']} пар")
            else:
                test_results.append(f"⚠️ FX sync: {result['status']}")
        except Exception as e:
            test_results.append(f"❌ FX sync ошибка: {str(e)[:50]}")
        
        # Формируем результат
        test_text = "🧪 **Результаты тестирования Grinex API**\n\n"
        test_text += "\n".join(test_results)
        test_text += f"\n\n**Latency:** {health.latency_ms:.1f} мс"
        test_text += f"\n**Timestamp:** {health.last_update.strftime('%H:%M:%S')}"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_back")]
        ])
        
        await callback.message.edit_text(test_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Grinex test failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка тестирования: {e}")

@router.callback_query(lambda c: c.data == "grinex_settings")
async def grinex_settings(callback: types.CallbackQuery):
    """Показывает настройки Grinex"""
    try:
        await callback.answer("⚙️ Настройки Grinex")
        
        from src.services.grinex import GRINEX_API_BASE, GRINEX_TIMEOUT, GRINEX_MAX_RETRIES
        from src.services.fx_scheduler import (
            FX_UPDATE_INTERVAL_SECONDS,
            FX_STALE_CHECK_INTERVAL,
            FX_STALE_THRESHOLD_SECONDS
        )
        
        settings_text = "⚙️ **Настройки Grinex Exchange**\n\n"
        
        settings_text += "**API Configuration:**\n"
        settings_text += f"• Base URL: {GRINEX_API_BASE}\n"
        settings_text += f"• Timeout: {GRINEX_TIMEOUT} сек\n"
        settings_text += f"• Max retries: {GRINEX_MAX_RETRIES}\n\n"
        
        settings_text += "**FX Scheduler:**\n"
        settings_text += f"• Update interval: {FX_UPDATE_INTERVAL_SECONDS} сек\n"
        settings_text += f"• Stale check: {FX_STALE_CHECK_INTERVAL} сек\n"
        settings_text += f"• Stale threshold: {FX_STALE_THRESHOLD_SECONDS} сек\n\n"
        
        settings_text += "_Для изменения настроек отредактируйте переменные окружения и перезапустите бота._"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика пар", callback_data="grinex_pairs_stats"),
                InlineKeyboardButton(text="🔄 Планировщик", callback_data="grinex_scheduler_info")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_back")]
        ])
        
        await callback.message.edit_text(settings_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Settings failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения настроек: {e}")

@router.callback_query(lambda c: c.data == "grinex_pairs_stats")
async def grinex_pairs_stats(callback: types.CallbackQuery):
    """Статистика по парам Grinex"""
    try:
        await callback.answer("📊 Загрузка статистики...")
        
        from src.db import get_pg_pool
        
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_pairs,
                    COUNT(*) FILTER (WHERE enabled = true) as enabled_pairs,
                    COUNT(DISTINCT sp.base_currency) as unique_bases,
                    COUNT(DISTINCT sp.quote_currency) as unique_quotes
                FROM fx_source_pair sp
                JOIN fx_source s ON s.id = sp.source_id
                WHERE s.code = 'grinex'
            """)
            
            # Самые популярные пары
            top_pairs = await conn.fetch("""
                SELECT sp.internal_symbol, fr.final_price, fr.calculated_at, fr.stale
                FROM fx_source_pair sp
                JOIN fx_source s ON s.id = sp.source_id
                LEFT JOIN fx_final_rate fr ON fr.source_pair_id = sp.id
                WHERE s.code = 'grinex' AND sp.enabled = true
                ORDER BY fr.calculated_at DESC NULLS LAST
                LIMIT 5
            """)
        
        stats_text = "📊 **Статистика пар Grinex**\n\n"
        stats_text += f"• Всего пар: {stats['total_pairs']}\n"
        stats_text += f"• Активных: {stats['enabled_pairs']}\n"
        stats_text += f"• Уникальных базовых валют: {stats['unique_bases']}\n"
        stats_text += f"• Уникальных котируемых: {stats['unique_quotes']}\n\n"
        
        if top_pairs:
            stats_text += "**Топ-5 актуальных пар:**\n"
            for pair in top_pairs:
                stale = "🟡" if pair['stale'] else "🟢"
                price = f"{pair['final_price']:.4f}" if pair['final_price'] else "N/A"
                time = pair['calculated_at'].strftime('%H:%M') if pair['calculated_at'] else "N/A"
                stats_text += f"{stale} {pair['internal_symbol']}: {price} ({time})\n"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_settings")]
        ])
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Pairs stats failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения статистики: {e}")

@router.callback_query(lambda c: c.data == "grinex_scheduler_info")
async def grinex_scheduler_info(callback: types.CallbackQuery):
    """Информация о планировщике"""
    try:
        await callback.answer("🔄 Информация о планировщике...")
        
        scheduler = await get_fx_scheduler()
        status = scheduler.get_status()
        
        info_text = "🔄 **FX Планировщик - Grinex**\n\n"
        
        info_text += f"**Статус:** {'🟢 Работает' if status['running'] else '🔴 Остановлен'}\n\n"
        
        if status['jobs']:
            info_text += "**Задачи:**\n"
            for job in status['jobs']:
                next_run = job.get('next_run', 'N/A')
                info_text += f"• {job['name']}\n"
                info_text += f"  Next run: {next_run}\n"
        
        if status['last_sync'].get('grinex'):
            info_text += f"\n**Последняя синхронизация Grinex:**\n{status['last_sync']['grinex']}\n"
        
        if status['config']:
            info_text += f"\n**Конфигурация:**\n"
            info_text += f"• Интервал: {status['config']['update_interval_seconds']}s\n"
            info_text += f"• Stale check: {status['config']['stale_check_interval']}s\n"
            info_text += f"• Stale threshold: {status['config']['stale_threshold_seconds']}s\n"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Синхронизировать", callback_data="grinex_sync"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="grinex_settings")
            ]
        ])
        
        await callback.message.edit_text(info_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Scheduler info failed: {e}")
        await callback.message.edit_text(f"❌ Ошибка получения информации: {e}")

@router.callback_query(lambda c: c.data == "grinex_back")
async def grinex_back(callback: types.CallbackQuery):
    """Возврат к основному статусу"""
    await cmd_grinex_status(callback.message)

@router.message(Command("grinex_ticker"))
async def cmd_grinex_ticker(message: types.Message, state: FSMContext):
    """Получает конкретный тикер"""
    await state.set_state(GrinexAdminStates.waiting_for_pair)
    await message.answer(
        "📈 **Получение тикера Grinex**\n\n"
        "Введите символ пары (например: USDTRUB, BTCUSDT):",
        parse_mode="Markdown"
    )

@router.message(GrinexAdminStates.waiting_for_pair)
async def process_ticker_pair(message: types.Message, state: FSMContext):
    """Обрабатывает запрос тикера"""
    try:
        symbol = message.text.strip().upper()
        
        client = await get_grinex_client()
        ticker = await client.get_ticker(symbol)
        
        if not ticker:
            await message.answer(f"❌ Тикер {symbol} не найден")
            await state.clear()
            return
        
        ticker_text = f"📈 **Тикер {symbol}**\n\n"
        ticker_text += f"• **Price:** {ticker.last_price}\n"
        
        if ticker.bid and ticker.ask:
            ticker_text += f"• **Bid:** {ticker.bid}\n"
            ticker_text += f"• **Ask:** {ticker.ask}\n"
            spread = ((ticker.ask - ticker.bid) / ticker.bid * 100) if ticker.bid else 0
            ticker_text += f"• **Spread:** {spread:.2f}%\n"
        
        if ticker.volume_24h:
            ticker_text += f"• **Volume 24h:** {ticker.volume_24h}\n"
        
        if ticker.high_24h and ticker.low_24h:
            ticker_text += f"• **High 24h:** {ticker.high_24h}\n"
            ticker_text += f"• **Low 24h:** {ticker.low_24h}\n"
        
        if ticker.change_24h:
            change_emoji = "🟢" if ticker.change_24h > 0 else "🔴"
            ticker_text += f"• **Change 24h:** {change_emoji} {ticker.change_24h}%\n"
        
        if ticker.timestamp:
            ticker_text += f"• **Timestamp:** {ticker.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        await message.answer(ticker_text, parse_mode="Markdown")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Failed to get ticker: {e}")
        await message.answer(f"❌ Ошибка получения тикера: {e}")
        await state.clear()

@router.message(Command("grinex_help"))
async def cmd_grinex_help(message: types.Message):
    """Справка по командам Grinex"""
    help_text = "📚 **Справка по командам Grinex**\n\n"
    help_text += "**Основные команды:**\n"
    help_text += "• `/grinex_status` - Статус интеграции с Grinex\n"
    help_text += "• `/grinex_ticker` - Получить конкретный тикер\n"
    help_text += "• `/grinex_help` - Эта справка\n\n"
    
    help_text += "**Возможности:**\n"
    help_text += "• Получение реал-тайм тикеров\n"
    help_text += "• Автоматическая синхронизация курсов\n"
    help_text += "• Система наценок (процент + фикс)\n"
    help_text += "• Приоритет правил (pair > source > global)\n"
    help_text += "• Health мониторинг API\n"
    help_text += "• Stale detection для устаревших данных\n\n"
    
    help_text += "**Интерфейс:**\n"
    help_text += "Используйте кнопки в `/grinex_status` для:\n"
    help_text += "• Синхронизации курсов\n"
    help_text += "• Просмотра текущих курсов\n"
    help_text += "• Проверки тикеров\n"
    help_text += "• Тестирования API\n"
    help_text += "• Настроек\n\n"
    
    help_text += "**Web Admin:**\n"
    help_text += "http://localhost:8000/admin/fx/sources"
    
    await message.answer(help_text, parse_mode="Markdown")

