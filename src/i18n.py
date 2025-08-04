import os
from aiogram.types import User

DEFAULT_LANG = 'ru'

# Простые переводы
TRANSLATIONS = {
    'ru': {
        'start_message': '👋 Привет! Я бот обменного сервиса. Используйте меню ниже.',
        'language_set': 'Язык успешно переключён.',
        'faq_intro': 'FAQ: Вопросы и ответы появятся здесь.',
        'rates_intro': 'Курсы валют: (заглушка)',
        'manager_intro': 'Live-chat с оператором: (заглушка)',
        'settings_intro': 'Настройки: выберите действие.',
        'select_trading_pair': 'Выберите торговую пару:',
        'no_rates_available': 'Курсы валют временно недоступны.',
        'pair_not_found': 'Торговая пара не найдена.',
        'no_rates_for_pair': 'Курсы для этой пары временно недоступны.',
    },
    'en': {
        'start_message': '👋 Hi! I am the exchange service bot. Use the menu below.',
        'language_set': 'Language switched successfully.',
        'faq_intro': 'FAQ: Questions and answers will appear here.',
        'rates_intro': 'Exchange rates: (placeholder)',
        'manager_intro': 'Live-chat with operator: (placeholder)',
        'settings_intro': 'Settings: choose an action.',
        'select_trading_pair': 'Select trading pair:',
        'no_rates_available': 'Exchange rates are temporarily unavailable.',
        'pair_not_found': 'Trading pair not found.',
        'no_rates_for_pair': 'Rates for this pair are temporarily unavailable.',
    }
}

def _(key, lang=DEFAULT_LANG):
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)

async def detect_user_lang(user: User, db_pool=None):
    """Определяет язык пользователя и регистрирует его в БД"""
    # Определяем язык по Telegram
    code = (user.language_code or '').split('-')[0]
    lang = code if code in ('ru', 'en') else DEFAULT_LANG
    
    # Регистрируем пользователя в БД
    if db_pool:
        from src.db import get_or_create_user
        try:
            db_user = await get_or_create_user(
                db_pool, 
                user.id, 
                user.first_name, 
                user.username, 
                lang
            )
            # Возвращаем язык из БД (может быть изменен пользователем)
            return db_user['lang']
        except Exception as e:
            print(f"Ошибка при регистрации пользователя: {e}")
            return lang
    
    return lang 