import asyncio
import os
from dotenv import load_dotenv
from src.db import get_pg_pool

load_dotenv()

async def init_db():
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Применяем все миграции по порядку
        migrations = [
            'migrations/001_init.sql',
            'migrations/002_extended_schema.sql',
            'migrations/003_faq_schema.sql'
        ]
        
        for migration_file in migrations:
            if os.path.exists(migration_file):
                print(f"Применяем миграцию: {migration_file}")
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                await conn.execute(sql)
                print(f"✅ {migration_file} применена успешно!")
            else:
                print(f"❌ Файл миграции не найден: {migration_file}")
        
        # Проверяем созданные таблицы
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"\n📋 Созданные таблицы ({len(tables)}):")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Проверяем данные в таблицах
        print(f"\n📊 Статистика данных:")
        
        # Пользователи
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"   👥 Пользователей: {users_count}")
        
        # Торговые пары
        pairs_count = await conn.fetchval("SELECT COUNT(*) FROM trading_pairs")
        print(f"   💱 Торговых пар: {pairs_count}")
        
        # Курсы
        rates_count = await conn.fetchval("SELECT COUNT(*) FROM rate_tiers")
        print(f"   📈 Курсов: {rates_count}")
        
        # Способы выплаты
        methods_count = await conn.fetchval("SELECT COUNT(*) FROM payout_methods")
        print(f"   💳 Способы выплаты: {methods_count}")
        
        # FAQ категории
        faq_categories_count = await conn.fetchval("SELECT COUNT(*) FROM faq_categories")
        print(f"   📚 FAQ категорий: {faq_categories_count}")
        
        # FAQ вопросы
        faq_questions_count = await conn.fetchval("SELECT COUNT(*) FROM faq_questions")
        print(f"   ❓ FAQ вопросов: {faq_questions_count}")

if __name__ == "__main__":
    asyncio.run(init_db()) 