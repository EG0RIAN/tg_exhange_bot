from src.db import get_pg_pool

async def get_categories():
    """Получает список активных категорий FAQ"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name 
            FROM faq_categories 
            WHERE is_active = true 
            ORDER BY sort_order, id
        """)
        return [(row["id"], row["name"]) for row in rows]

async def get_questions(category_id):
    """Получает список вопросов в категории"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, question 
            FROM faq_questions 
            WHERE category_id = $1 AND is_active = true 
            ORDER BY sort_order, id
        """, category_id)
        return [(row["id"], row["question"]) for row in rows]

async def get_answer(question_id):
    """Получает ответ на вопрос"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT question, answer 
            FROM faq_questions 
            WHERE id = $1 AND is_active = true
        """, question_id)
        return {"question": row["question"], "answer": row["answer"]} if row else None

async def add_category(name, sort_order=0):
    """Добавляет новую категорию FAQ"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO faq_categories (name, sort_order) 
            VALUES ($1, $2)
        """, name, sort_order)

async def get_questions_in_category(category_id):
    """Получает все вопросы в категории"""
    return await get_questions(category_id)

async def add_question(category_id, question, answer, sort_order=0):
    """Добавляет новый вопрос в категорию"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO faq_questions (category_id, question, answer, sort_order) 
            VALUES ($1, $2, $3, $4)
        """, category_id, question, answer, sort_order)

async def update_question(question_id, question, answer):
    """Обновляет вопрос"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE faq_questions 
            SET question = $1, answer = $2 
            WHERE id = $3
        """, question, answer, question_id)

async def delete_question(question_id):
    """Удаляет вопрос"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM faq_questions WHERE id = $1", question_id) 

async def get_category_name(category_id):
    """Получает название категории по ID"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT name 
            FROM faq_categories 
            WHERE id = $1 AND is_active = true
        """, category_id)
        return row["name"] if row else None 