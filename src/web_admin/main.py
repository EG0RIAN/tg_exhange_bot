from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
import asyncpg
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("ADMIN_SECRET_KEY", "supersecret"))
templates = Jinja2Templates(directory="src/web_admin/templates")
app.mount("/static", StaticFiles(directory="src/web_admin/static"), name="static")

ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1i_X%9644XS1:d8=vHGV")

# Database connection pool
_db_pool = None

async def get_db_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "exchange"),
            user=os.getenv("POSTGRES_USER", "exchange"),
            password=os.getenv("POSTGRES_PASSWORD", "exchange"),
            min_size=1,
            max_size=10
        )
    return _db_pool

# Dependency
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_LOGIN and password == ADMIN_PASSWORD:
        request.session["user"] = username
        return RedirectResponse("/admin", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "user": user})

@app.get("/admin/rates-management", response_class=HTMLResponse)
async def rates_management(request: Request, user=Depends(get_current_user)):
    """Универсальная страница управления курсами"""
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("rates_management.html", {"request": request, "user": user})

# Trading Pairs CRUD
@app.get("/admin/trading-pairs", response_class=HTMLResponse)
async def trading_pairs_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        pairs = await conn.fetch("""
            SELECT id, base_currency, quote_currency, base_name, quote_name, is_active, sort_order
            FROM trading_pairs ORDER BY sort_order, id
        """)
    
    return templates.TemplateResponse("trading_pairs.html", {
        "request": request, 
        "user": user, 
        "pairs": pairs
    })

@app.get("/admin/trading-pairs/add", response_class=HTMLResponse)
async def add_trading_pair_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("trading_pair_form.html", {"request": request, "user": user})

@app.post("/admin/trading-pairs/add")
async def add_trading_pair(
    request: Request, 
    user=Depends(get_current_user),
    base_currency: str = Form(...),
    quote_currency: str = Form(...),
    base_name: str = Form(...),
    quote_name: str = Form(...),
    sort_order: int = Form(0)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO trading_pairs (base_currency, quote_currency, base_name, quote_name, sort_order)
            VALUES ($1, $2, $3, $4, $5)
        """, base_currency, quote_currency, base_name, quote_name, sort_order)
    
    return RedirectResponse("/admin/trading-pairs", status_code=status.HTTP_302_FOUND)

@app.get("/admin/trading-pairs/{pair_id}/edit", response_class=HTMLResponse)
async def edit_trading_pair_form(request: Request, pair_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        pair = await conn.fetchrow("""
            SELECT id, base_currency, quote_currency, base_name, quote_name, is_active, sort_order
            FROM trading_pairs WHERE id = $1
        """, pair_id)
    
    if not pair:
        return RedirectResponse("/admin/trading-pairs", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("trading_pair_form.html", {
        "request": request, 
        "user": user, 
        "pair": pair
    })

@app.post("/admin/trading-pairs/{pair_id}/edit")
async def edit_trading_pair(
    request: Request,
    pair_id: int,
    user=Depends(get_current_user),
    base_currency: str = Form(...),
    quote_currency: str = Form(...),
    base_name: str = Form(...),
    quote_name: str = Form(...),
    sort_order: int = Form(0),
    is_active: bool = Form(False)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE trading_pairs 
            SET base_currency = $1, quote_currency = $2, base_name = $3, quote_name = $4, 
                sort_order = $5, is_active = $6
            WHERE id = $7
        """, base_currency, quote_currency, base_name, quote_name, sort_order, is_active, pair_id)
    
    return RedirectResponse("/admin/trading-pairs", status_code=status.HTTP_302_FOUND)

@app.post("/admin/trading-pairs/{pair_id}/delete")
async def delete_trading_pair(request: Request, pair_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM trading_pairs WHERE id = $1", pair_id)
    
    return RedirectResponse("/admin/trading-pairs", status_code=status.HTTP_302_FOUND)

# Rate Tiers CRUD
@app.get("/admin/rates", response_class=HTMLResponse)
async def rates_list(request: Request, user=Depends(get_current_user)):
    """Перенаправление на новую универсальную панель управления курсами"""
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на новую универсальную панель
    return RedirectResponse("/admin/rates-management", status_code=status.HTTP_302_FOUND)

@app.get("/admin/rates/add", response_class=HTMLResponse)
async def add_rate_form(request: Request, user=Depends(get_current_user)):
    """Перенаправление на новую универсальную панель"""
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse("/admin/rates-management", status_code=status.HTTP_302_FOUND)

@app.get("/admin/rates/add_old", response_class=HTMLResponse)
async def add_rate_form_old(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        pairs = await conn.fetch("""
            SELECT id, base_name, quote_name, base_currency, quote_currency
            FROM trading_pairs WHERE is_active = true
            ORDER BY sort_order, id
        """)
    
    return templates.TemplateResponse("rate_form.html", {
        "request": request, 
        "user": user, 
        "pairs": pairs
    })

@app.post("/admin/rates/add")
async def add_rate(
    request: Request, 
    user=Depends(get_current_user),
    pair_id: int = Form(...),
    min_amount: float = Form(...),
    max_amount: Optional[str] = Form(None),
    rate: float = Form(...)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    # Обрабатываем max_amount
    max_amount_float = None
    if max_amount and max_amount.strip():
        try:
            max_amount_float = float(max_amount)
        except ValueError:
            # Если не удается преобразовать в число, оставляем None
            max_amount_float = None
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO rate_tiers (pair_id, min_amount, max_amount, rate)
            VALUES ($1, $2, $3, $4)
        """, pair_id, min_amount, max_amount_float, rate)
    
    return RedirectResponse("/admin/rates", status_code=status.HTTP_302_FOUND)

@app.get("/admin/rates/{rate_id}/edit", response_class=HTMLResponse)
async def edit_rate_form(request: Request, rate_id: int, user=Depends(get_current_user)):
    """Перенаправление на новую универсальную панель"""
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse("/admin/rates-management", status_code=status.HTTP_302_FOUND)

@app.post("/admin/rates/{rate_id}/edit")
async def edit_rate(
    request: Request,
    rate_id: int,
    user=Depends(get_current_user),
    pair_id: int = Form(...),
    min_amount: float = Form(...),
    max_amount: Optional[str] = Form(None),
    rate: float = Form(...),
    is_active: bool = Form(False)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    # Обрабатываем max_amount
    max_amount_float = None
    if max_amount and max_amount.strip():
        try:
            max_amount_float = float(max_amount)
        except ValueError:
            # Если не удается преобразовать в число, оставляем None
            max_amount_float = None
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE rate_tiers 
            SET pair_id = $1, min_amount = $2, max_amount = $3, rate = $4, is_active = $5
            WHERE id = $6
        """, pair_id, min_amount, max_amount_float, rate, is_active, rate_id)
    
    return RedirectResponse("/admin/rates", status_code=status.HTTP_302_FOUND)

@app.post("/admin/rates/{rate_id}/delete")
async def delete_rate(request: Request, rate_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rate_tiers WHERE id = $1", rate_id)
    
    return RedirectResponse("/admin/rates", status_code=status.HTTP_302_FOUND)

# Payout Methods CRUD
@app.get("/admin/payout-methods", response_class=HTMLResponse)
async def payout_methods_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        methods = await conn.fetch("""
            SELECT id, name, type, is_active, sort_order
            FROM payout_methods ORDER BY sort_order, id
        """)
    
    return templates.TemplateResponse("payout_methods.html", {
        "request": request, 
        "user": user, 
        "methods": methods
    })

@app.get("/admin/payout-methods/add", response_class=HTMLResponse)
async def add_payout_method_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("payout_method_form.html", {"request": request, "user": user})

@app.post("/admin/payout-methods/add")
async def add_payout_method(
    request: Request, 
    user=Depends(get_current_user),
    name: str = Form(...),
    type: str = Form(...),
    sort_order: int = Form(0)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO payout_methods (name, type, sort_order)
            VALUES ($1, $2, $3)
        """, name, type, sort_order)
    
    return RedirectResponse("/admin/payout-methods", status_code=status.HTTP_302_FOUND)

@app.get("/admin/payout-methods/{method_id}/edit", response_class=HTMLResponse)
async def edit_payout_method_form(request: Request, method_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        method = await conn.fetchrow("""
            SELECT id, name, type, is_active, sort_order
            FROM payout_methods WHERE id = $1
        """, method_id)
    
    if not method:
        return RedirectResponse("/admin/payout-methods", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("payout_method_form.html", {
        "request": request, 
        "user": user, 
        "method": method
    })

@app.post("/admin/payout-methods/{method_id}/edit")
async def edit_payout_method(
    request: Request,
    method_id: int,
    user=Depends(get_current_user),
    name: str = Form(...),
    type: str = Form(...),
    sort_order: int = Form(0),
    is_active: bool = Form(False)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE payout_methods 
            SET name = $1, type = $2, sort_order = $3, is_active = $4
            WHERE id = $5
        """, name, type, sort_order, is_active, method_id)
    
    return RedirectResponse("/admin/payout-methods", status_code=status.HTTP_302_FOUND)

@app.post("/admin/payout-methods/{method_id}/delete")
async def delete_payout_method(request: Request, method_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM payout_methods WHERE id = $1", method_id)
    
    return RedirectResponse("/admin/payout-methods", status_code=status.HTTP_302_FOUND)

# FAQ CRUD
@app.get("/admin/faq", response_class=HTMLResponse)
async def faq_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        categories = await conn.fetch("""
            SELECT c.id, c.name, c.sort_order, c.is_active,
                   COUNT(q.id) as questions_count
            FROM faq_categories c
            LEFT JOIN faq_questions q ON c.id = q.category_id
            GROUP BY c.id, c.name, c.sort_order, c.is_active
            ORDER BY c.sort_order, c.id
        """)
    
    return templates.TemplateResponse("faq.html", {
        "request": request, 
        "user": user, 
        "categories": categories
    })

@app.get("/admin/faq/categories/add", response_class=HTMLResponse)
async def add_faq_category_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("faq_category_form.html", {"request": request, "user": user})

@app.post("/admin/faq/categories/add")
async def add_faq_category(
    request: Request, 
    user=Depends(get_current_user),
    name: str = Form(...),
    sort_order: int = Form(0)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO faq_categories (name, sort_order)
            VALUES ($1, $2)
        """, name, sort_order)
    
    return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)

@app.get("/admin/faq/categories/{category_id}/edit", response_class=HTMLResponse)
async def edit_faq_category_form(request: Request, category_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        category = await conn.fetchrow("""
            SELECT id, name, sort_order, is_active
            FROM faq_categories WHERE id = $1
        """, category_id)
    
    if not category:
        return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("faq_category_form.html", {
        "request": request, 
        "user": user, 
        "category": category
    })

@app.post("/admin/faq/categories/{category_id}/edit")
async def edit_faq_category(
    request: Request,
    category_id: int,
    user=Depends(get_current_user),
    name: str = Form(...),
    sort_order: int = Form(0),
    is_active: bool = Form(False)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE faq_categories 
            SET name = $1, sort_order = $2, is_active = $3
            WHERE id = $4
        """, name, sort_order, is_active, category_id)
    
    return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)

@app.post("/admin/faq/categories/{category_id}/delete")
async def delete_faq_category(request: Request, category_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM faq_categories WHERE id = $1", category_id)
    
    return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)

@app.get("/admin/faq/categories/{category_id}/questions", response_class=HTMLResponse)
async def faq_questions_list(request: Request, category_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        category = await conn.fetchrow("""
            SELECT id, name FROM faq_categories WHERE id = $1
        """, category_id)
        
        questions = await conn.fetch("""
            SELECT id, question, answer, sort_order, is_active
            FROM faq_questions 
            WHERE category_id = $1
            ORDER BY sort_order, id
        """, category_id)
    
    if not category:
        return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("faq_questions.html", {
        "request": request, 
        "user": user, 
        "category": category,
        "questions": questions
    })

@app.get("/admin/faq/categories/{category_id}/questions/add", response_class=HTMLResponse)
async def add_faq_question_form(request: Request, category_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        category = await conn.fetchrow("""
            SELECT id, name FROM faq_categories WHERE id = $1
        """, category_id)
    
    if not category:
        return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("faq_question_form.html", {
        "request": request, 
        "user": user, 
        "category": category
    })

@app.post("/admin/faq/categories/{category_id}/questions/add")
async def add_faq_question(
    request: Request,
    category_id: int,
    user=Depends(get_current_user),
    question: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(0)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO faq_questions (category_id, question, answer, sort_order)
            VALUES ($1, $2, $3, $4)
        """, category_id, question, answer, sort_order)
    
    return RedirectResponse(f"/admin/faq/categories/{category_id}/questions", status_code=status.HTTP_302_FOUND)

@app.get("/admin/faq/questions/{question_id}/edit", response_class=HTMLResponse)
async def edit_faq_question_form(request: Request, question_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        question = await conn.fetchrow("""
            SELECT q.id, q.category_id, q.question, q.answer, q.sort_order, q.is_active,
                   c.name as category_name
            FROM faq_questions q
            JOIN faq_categories c ON q.category_id = c.id
            WHERE q.id = $1
        """, question_id)
    
    if not question:
        return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("faq_question_form.html", {
        "request": request, 
        "user": user, 
        "question": question
    })

@app.post("/admin/faq/questions/{question_id}/edit")
async def edit_faq_question(
    request: Request,
    question_id: int,
    user=Depends(get_current_user),
    question_text: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(0),
    is_active: bool = Form(False)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("""
            UPDATE faq_questions 
            SET question = $1, answer = $2, sort_order = $3, is_active = $4
            WHERE id = $5
            RETURNING category_id
        """, question_text, answer, sort_order, is_active, question_id)
    
    if result:
        return RedirectResponse(f"/admin/faq/categories/{result['category_id']}/questions", status_code=status.HTTP_302_FOUND)
    return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND)

@app.post("/admin/faq/questions/{question_id}/delete")
async def delete_faq_question(request: Request, question_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("""
            DELETE FROM faq_questions WHERE id = $1
            RETURNING category_id
        """, question_id)
    
    if result:
        return RedirectResponse(f"/admin/faq/categories/{result['category_id']}/questions", status_code=status.HTTP_302_FOUND)
    return RedirectResponse("/admin/faq", status_code=status.HTTP_302_FOUND) 

# Orders Management
@app.get("/admin/orders", response_class=HTMLResponse)
async def orders_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        orders = await conn.fetch("""
            SELECT o.id, o.pair, o.amount, o.payout_method, o.contact, o.status, o.created_at,
                   u.first_name, u.username, u.tg_id
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 100
        """)
    
    return templates.TemplateResponse("orders.html", {
        "request": request, 
        "user": user, 
        "orders": orders
    })

@app.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT o.id, o.pair, o.amount, o.payout_method, o.contact, o.status, o.created_at,
                   o.rate_snapshot, u.first_name, u.username, u.tg_id, u.lang
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = $1
        """, order_id)
    
    if not order:
        return RedirectResponse("/admin/orders", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("order_detail.html", {
        "request": request, 
        "user": user, 
        "order": order
    })

@app.post("/admin/orders/{order_id}/status")
async def update_order_status(
    request: Request,
    order_id: int,
    user=Depends(get_current_user),
    status: str = Form(...)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET status = $1 WHERE id = $2
        """, status, order_id)
    
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=status.HTTP_302_FOUND)

# Users Management
@app.get("/admin/users", response_class=HTMLResponse)
async def users_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("""
            SELECT id, tg_id, first_name, username, lang, is_blocked, created_at,
                   (SELECT COUNT(*) FROM orders WHERE user_id = users.id) as orders_count
            FROM users
            ORDER BY created_at DESC
            LIMIT 100
        """)
    
    return templates.TemplateResponse("users.html", {
        "request": request, 
        "user": user, 
        "users": users
    })

@app.post("/admin/users/{user_id}/block")
async def block_user(request: Request, user_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users SET is_blocked = true WHERE id = $1
        """, user_id)
    
    return RedirectResponse("/admin/users", status_code=status.HTTP_302_FOUND)

@app.post("/admin/users/{user_id}/unblock")
async def unblock_user(request: Request, user_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users SET is_blocked = false WHERE id = $1
        """, user_id)
    
    return RedirectResponse("/admin/users", status_code=status.HTTP_302_FOUND)

# Notifications Management
@app.get("/admin/notifications", response_class=HTMLResponse)
async def notifications_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        notifications = await conn.fetch("""
            SELECT id, type, title, message, is_read, created_at
            FROM operator_notifications
            ORDER BY created_at DESC
            LIMIT 50
        """)
    
    return templates.TemplateResponse("notifications.html", {
        "request": request, 
        "user": user, 
        "notifications": notifications
    })

@app.post("/admin/notifications/{notification_id}/read")
async def mark_notification_read(request: Request, notification_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE operator_notifications SET is_read = true WHERE id = $1
        """, notification_id)
    
    return RedirectResponse("/admin/notifications", status_code=status.HTTP_302_FOUND)

@app.post("/admin/notifications/clear-read")
async def clear_read_notifications(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM operator_notifications WHERE is_read = true
        """)
    
    return RedirectResponse("/admin/notifications", status_code=status.HTTP_302_FOUND)

# Statistics Dashboard
@app.get("/admin/stats", response_class=HTMLResponse)
async def stats_dashboard(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Общая статистика
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as new_users_24h,
                COUNT(CASE WHEN is_blocked = true THEN 1 END) as blocked_users
            FROM users
        """)
        
        # Статистика заявок
        orders_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as new_orders_24h,
                COUNT(CASE WHEN status = 'new' THEN 1 END) as pending_orders,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount END), 0) as total_volume
            FROM orders
        """)
        
        # Статистика по парам
        pairs_stats = await conn.fetch("""
            SELECT pair, COUNT(*) as orders_count, 
                   COALESCE(SUM(amount), 0) as total_amount
            FROM orders 
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY pair 
            ORDER BY orders_count DESC 
            LIMIT 10
        """)
    
    return templates.TemplateResponse("stats.html", {
        "request": request, 
        "user": user, 
        "stats": stats,
        "orders_stats": orders_stats,
        "pairs_stats": pairs_stats
    })

# Live Chats Management
@app.get("/admin/live-chats", response_class=HTMLResponse)
async def live_chats_list(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        chats = await conn.fetch("""
            SELECT lc.user_id, lc.started_at, lc.is_active,
                   u.first_name, u.username, u.tg_id
            FROM live_chats lc
            LEFT JOIN users u ON lc.user_id = u.tg_id
            ORDER BY lc.started_at DESC
        """)
    
    return templates.TemplateResponse("live_chats.html", {
        "request": request, 
        "user": user, 
        "chats": chats
    })

@app.post("/admin/live-chats/{user_id}/close")
async def close_live_chat(request: Request, user_id: int, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE live_chats SET is_active = false WHERE user_id = $1
        """, user_id)
    
    return RedirectResponse("/admin/live-chats", status_code=status.HTTP_302_FOUND) 

# Utility function to create notifications
async def create_notification(type: str, title: str, message: str):
    """Создает уведомление для операторов"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO operator_notifications (type, title, message)
            VALUES ($1, $2, $3)
        """, type, title, message)

# API endpoints for creating notifications (for bot integration)
@app.post("/api/notifications")
async def api_create_notification(
    request: Request,
    type: str = Form(...),
    title: str = Form(...),
    message: str = Form(...)
):
    """API endpoint для создания уведомлений из бота"""
    await create_notification(type, title, message)
    return {"status": "success"}

# Manual notification creation in admin panel
@app.get("/admin/notifications/create", response_class=HTMLResponse)
async def create_notification_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("create_notification.html", {"request": request, "user": user})

@app.post("/admin/notifications/create")
async def create_notification_manual(
    request: Request,
    user=Depends(get_current_user),
    type: str = Form(...),
    title: str = Form(...),
    message: str = Form(...)
):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    await create_notification(type, title, message)
    return RedirectResponse("/admin/notifications", status_code=status.HTTP_302_FOUND) 

# ============================================================================
# RAPIRA API INTEGRATION ROUTES
# ============================================================================

from fastapi import HTTPException
import json
from datetime import datetime, timedelta

# ============================================================================
# FX RATES MODULE - API Endpoints
# ============================================================================

from fastapi import HTTPException
from src.services.fx_rates import get_fx_service
from src.services.fx_scheduler import get_fx_scheduler

# FX Sources Management
# ============================================================================
# LEGACY HTML PAGES REMOVED - Use /admin/rates-management instead
# ============================================================================
# Old routes removed:
# - /admin/fx/sources
# - /admin/fx/sources/{source_id}/pairs
# - /admin/fx/markup-rules
# - /admin/fx/markup-rules/new
# - /admin/fx/markup-rules/create
# - /admin/fx/markup-rules/{rule_id}/delete
# - /admin/fx/rates
# - /admin/fx/logs
#
# New universal page: /admin/rates-management
# ============================================================================

# API Endpoints (used by the new universal rates management page)
@app.get("/api/fx/rates")
async def api_get_rates(
    base: Optional[str] = None,
    quote: Optional[str] = None,
    source: Optional[str] = None,
    stale_ok: bool = False,
    user=Depends(get_current_user)
):
    """API: Получить курсы"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    fx_service = await get_fx_service()
    
    if base and quote:
        rate = await fx_service.get_final_rate(base, quote, source, allow_stale=stale_ok)
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        
            return {
            "base": rate.base_currency,
            "quote": rate.quote_currency,
            "source": rate.source_code,
            "final_price": str(rate.final_price),
            "raw_price": str(rate.raw_price),
            "applied_rule_id": rate.applied_rule_id,
            "markup": {
                "percent": str(rate.markup_percent) if rate.markup_percent else None,
                "fixed": str(rate.markup_fixed) if rate.markup_fixed else None
            },
            "calculated_at": rate.calculated_at.isoformat(),
            "stale": rate.stale,
            "bid": str(rate.bid_price) if rate.bid_price else None,
            "ask": str(rate.ask_price) if rate.ask_price else None
        }
    else:
        rates = await fx_service.get_all_final_rates(source, allow_stale=stale_ok)
        
        return {
            "rates": [
                {
                    "base": r.base_currency,
                    "quote": r.quote_currency,
                    "source": r.source_code,
                    "internal_symbol": r.internal_symbol,
                    "final_price": str(r.final_price),
                    "raw_price": str(r.raw_price),
                    "calculated_at": r.calculated_at.isoformat(),
                    "stale": r.stale
                }
                for r in rates
            ]
        }

@app.post("/api/fx/sync")
async def api_trigger_sync(
    source: Optional[str] = None,
    user=Depends(get_current_user)
):
    """API: Принудительная синхронизация"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scheduler = await get_fx_scheduler()
    result = await scheduler.trigger_sync(source)
    
    return {
        "success": True,
        "message": f"Sync triggered for {source or 'all sources'}",
        "result": result
    }

@app.get("/api/fx/scheduler/status")
async def api_scheduler_status(user=Depends(get_current_user)):
    """API: Статус планировщика"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scheduler = await get_fx_scheduler()
    status = scheduler.get_status()
    
    return status

@app.get("/api/fx/sources")
async def api_get_sources(user=Depends(get_current_user)):
    """API: Получить список источников данных"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, code, name, enabled, created_at
            FROM fx_source
            ORDER BY code
        """)
        
        return [
            {
                "id": r['id'],
                "code": r['code'],
                "name": r['name'],
                "enabled": r['enabled'],
                "created_at": r['created_at'].isoformat() if r['created_at'] else None
            }
            for r in rows
        ]

@app.put("/api/fx/sources/{code}")
async def api_update_source(code: str, request: Request, user=Depends(get_current_user)):
    """API: Включить/выключить источник"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    enabled = data.get('enabled', True)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE fx_source 
            SET enabled = $1, updated_at = NOW()
            WHERE code = $2 AND deleted_at IS NULL
        """, enabled, code)
    
    return {"success": True, "code": code, "enabled": enabled}

@app.get("/api/fx/logs")
async def api_get_sync_logs(limit: int = 20, user=Depends(get_current_user)):
    """API: Получить логи синхронизации"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                sl.id,
                sl.source_id,
                fs.code as source_code,
                fs.name as source_name,
                sl.started_at,
                sl.finished_at,
                sl.status,
                sl.pairs_processed,
                sl.pairs_succeeded,
                sl.pairs_failed,
                sl.duration_ms,
                sl.error_message
            FROM fx_sync_log sl
            JOIN fx_source fs ON sl.source_id = fs.id
            ORDER BY sl.started_at DESC
            LIMIT $1
        """, limit)
        
        return [
            {
                "id": r['id'],
                "source_code": r['source_code'],
                "source_name": r['source_name'],
                "started_at": r['started_at'].isoformat() if r['started_at'] else None,
                "finished_at": r['finished_at'].isoformat() if r['finished_at'] else None,
                "status": r['status'],
                "pairs_processed": r['pairs_processed'],
                "pairs_succeeded": r['pairs_succeeded'],
                "pairs_failed": r['pairs_failed'],
                "duration_ms": r['duration_ms'],
                "error_message": r['error_message']
            }
            for r in rows
        ]

@app.get("/api/fx/markup-rules")
async def api_get_markup_rules(user=Depends(get_current_user)):
    """API: Получить правила наценок"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id, level, source_id, source_pair_id,
                percent, fixed, enabled, description,
                rounding_mode, round_to,
                valid_from, valid_to, created_at
            FROM fx_markup_rule
            WHERE deleted_at IS NULL
            ORDER BY 
                CASE level
                    WHEN 'pair' THEN 1
                    WHEN 'source' THEN 2
                    WHEN 'global' THEN 3
                END,
                percent DESC
        """)
        
        return [
            {
                "id": r['id'],
                "level": r['level'],
                "source_id": r['source_id'],
                "source_pair_id": r['source_pair_id'],
                "percent": float(r['percent']) if r['percent'] else 0,
                "fixed": float(r['fixed']) if r['fixed'] else 0,
                "enabled": r['enabled'],
                "description": r['description'],
                "rounding_mode": r['rounding_mode'],
                "round_to": r['round_to'],
                "valid_from": r['valid_from'].isoformat() if r['valid_from'] else None,
                "valid_to": r['valid_to'].isoformat() if r['valid_to'] else None,
                "created_at": r['created_at'].isoformat() if r['created_at'] else None
            }
            for r in rows
        ]


# ============================================================================
# CITY RATES API - Упрощенная логика Rapira с наценками по городам
# ============================================================================

from src.services.rapira_simple import (
    get_city_rate, 
    get_rapira_simple_client, 
    CITIES
)

# Legacy /admin/city-rates page removed - use /admin/rates-management instead

@app.get("/api/city-rate/{city}")
async def api_get_city_rate(
    city: str,
    symbol: str,
    operation: str = "buy",
    user=Depends(get_current_user)
):
    """
    API: Получить курс для города
    
    city: moscow, rostov, nizhniy_novgorod, spb, etc.
    symbol: USDT/RUB, BTC/USDT, etc. (query parameter)
    operation: buy (клиент покупает) или sell (клиент продает)
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    rate = await get_city_rate(symbol, city, operation)
    
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    
    return rate

@app.get("/api/city-rates/all")
async def api_get_all_city_rates(
    symbol: str,
    operation: str = "buy",
    user=Depends(get_current_user)
):
    """API: Получить курсы для всех городов (оптимизированная версия)"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Получаем базовый курс из Rapira один раз
    client = await get_rapira_simple_client()
    base_data = await client.get_base_rate(symbol)
    
    if not base_data or not (base_data.get('best_ask') or base_data.get('best_bid')):
        return {
            "success": False,
            "error": "No base rate available",
            "symbol": symbol,
            "rates": {}
        }
    
    # Выбираем базовую цену
    base_rate = base_data['best_ask'] if operation == "buy" else base_data['best_bid']
    if not base_rate:
        return {
            "success": False,
            "error": "No rate for operation",
            "symbol": symbol,
            "rates": {}
        }
    
    # Получаем все города и их наценки одним запросом
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        cities_data = await conn.fetch("""
            SELECT 
                c.code,
                c.name,
                COALESCE(cpm.markup_percent, c.markup_percent) as markup_percent,
                COALESCE(cpm.markup_fixed, c.markup_fixed) as markup_fixed
            FROM cities c
            LEFT JOIN city_pair_markups cpm ON cpm.city_id = c.id 
                AND cpm.pair_symbol = $1 
                AND cpm.enabled = true
            WHERE c.enabled = true
            ORDER BY c.sort_order, c.name
        """, symbol)
    
    results = {}
    
    for city in cities_data:
        markup_percent = float(city['markup_percent'])
        markup_fixed = float(city['markup_fixed'])
        
        # Применяем наценку
        from decimal import Decimal
        final_rate = float(base_rate) * (1 + markup_percent / 100) + markup_fixed
        final_rate = round(final_rate, 2)
        
        results[city['code']] = {
            'symbol': symbol,
            'city': city['code'],
            'city_name': city['name'],
            'best_source': 'rapira',
            'base_rate': float(base_rate),
            'final_rate': final_rate,
            'markup_percent': markup_percent,
            'markup_fixed': markup_fixed,
            'operation': operation,
            'rapira_rate': float(base_rate),
            'grinex_rate': None,
            'timestamp': base_data['timestamp'].isoformat() if hasattr(base_data['timestamp'], 'isoformat') else str(base_data['timestamp'])
        }
    
    return {
        "success": True,
        "symbol": symbol,
        "operation": operation,
        "rates": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/city-rates/update-markup")
async def api_update_city_markup(
    request: Request,
    city: str = Form(...),
    percent: float = Form(...),
    user=Depends(get_current_user)
):
    """API: Обновить наценку для города"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Обновляем наценку
        await conn.execute("""
            UPDATE fx_markup_rule
            SET percent = $1, updated_at = NOW()
            WHERE description ILIKE $2
                AND deleted_at IS NULL
        """, percent, f"%город: {city}%")
    
    return {"success": True, "city": city, "percent": percent}

@app.get("/api/rapira/base-rate")
async def api_rapira_base_rate(
    symbol: str,
    user=Depends(get_current_user)
):
    """API: Получить базовый курс из Rapira (московский)"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        client = await get_rapira_simple_client()
        rate = await client.get_base_rate(symbol)
        
        if not rate:
            raise HTTPException(status_code=503, detail="Rapira API unavailable")
        
        return {
            "symbol": rate['symbol'],
            "best_ask": float(rate['best_ask']) if rate['best_ask'] else None,
            "best_bid": float(rate['best_bid']) if rate['best_bid'] else None,
            "timestamp": rate['timestamp'].isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get base rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Тестовый публичный эндпоинт (без аутентификации)
@app.get("/api/test/rapira-base-rate")
async def test_rapira_base_rate(symbol: str = "USDT/RUB"):
    """Тестовый эндпоинт для проверки Rapira API (без аутентификации)"""
    try:
        client = await get_rapira_simple_client()
        rate = await client.get_base_rate(symbol)
        
        if not rate:
            return {"error": "Rapira API unavailable", "symbol": symbol}
        
        return {
            "success": True,
            "symbol": rate['symbol'],
            "best_ask": float(rate['best_ask']) if rate['best_ask'] else None,
            "best_bid": float(rate['best_bid']) if rate['best_bid'] else None,
            "timestamp": rate['timestamp'].isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e), "symbol": symbol}


# ============================================================================
# CITIES MANAGEMENT API - Управление городами
# ============================================================================

@app.get("/api/cities")
async def api_get_cities(user=Depends(get_current_user)):
    """API: Получить список городов"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, code, name, markup_percent, markup_fixed, enabled, sort_order
            FROM cities
            ORDER BY sort_order, name
        """)
        
        return [
            {
                "id": r['id'],
                "code": r['code'],
                "name": r['name'],
                "markup_percent": float(r['markup_percent']),
                "markup_fixed": float(r['markup_fixed']),
                "enabled": r['enabled'],
                "sort_order": r['sort_order']
            }
            for r in rows
        ]

@app.post("/api/cities")
async def api_create_city(
    request: Request,
    user=Depends(get_current_user)
):
    """API: Создать новый город"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    code = data.get('code')
    name = data.get('name')
    markup_percent = float(data.get('markup_percent', 0))
    markup_fixed = float(data.get('markup_fixed', 0))
    enabled = data.get('enabled', True)
    
    if not code or not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Code and name are required")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO cities (code, name, markup_percent, markup_fixed, enabled)
                VALUES ($1, $2, $3, $4, $5)
            """, code, name, markup_percent, markup_fixed, enabled)
            
            return {"success": True, "code": code, "name": name}
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Error creating city: {str(e)}")

@app.put("/api/cities/{city_id}")
async def api_update_city(
    city_id: int,
    request: Request,
    user=Depends(get_current_user)
):
    """API: Обновить город"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        updates = []
        values = []
        idx = 1
        
        if 'name' in data:
            updates.append(f"name = ${idx}")
            values.append(data['name'])
            idx += 1
        
        if 'markup_percent' in data:
            updates.append(f"markup_percent = ${idx}")
            values.append(float(data['markup_percent']))
            idx += 1
        
        if 'markup_fixed' in data:
            updates.append(f"markup_fixed = ${idx}")
            values.append(float(data['markup_fixed']))
            idx += 1
        
        if 'enabled' in data:
            updates.append(f"enabled = ${idx}")
            values.append(data['enabled'])
            idx += 1
        
        if updates:
            updates.append(f"updated_at = NOW()")
            values.append(city_id)
            
            query = f"UPDATE cities SET {', '.join(updates)} WHERE id = ${idx}"
            await conn.execute(query, *values)
        
        return {"success": True, "city_id": city_id}

@app.delete("/api/cities/{city_id}")
async def api_delete_city(
    city_id: int,
    user=Depends(get_current_user)
):
    """API: Удалить город"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cities WHERE id = $1", city_id)
        
        return {"success": True, "city_id": city_id}


# ============================================================================
# CITY-PAIR MARKUPS API - Наценки для конкретной пары в конкретном городе
# ============================================================================

@app.get("/api/city-pair-markups")
async def api_get_city_pair_markups(
    city_id: Optional[int] = None,
    pair_symbol: Optional[str] = None,
    user=Depends(get_current_user)
):
    """API: Получить специфичные наценки город+пара"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT 
                cpm.id,
                cpm.city_id,
                c.code as city_code,
                c.name as city_name,
                cpm.pair_symbol,
                cpm.markup_percent,
                cpm.markup_fixed,
                cpm.enabled
            FROM city_pair_markups cpm
            JOIN cities c ON c.id = cpm.city_id
            WHERE 1=1
        """
        params = []
        
        if city_id:
            query += f" AND cpm.city_id = ${len(params) + 1}"
            params.append(city_id)
        
        if pair_symbol:
            query += f" AND cpm.pair_symbol = ${len(params) + 1}"
            params.append(pair_symbol)
        
        query += " ORDER BY c.sort_order, cpm.pair_symbol"
        
        rows = await conn.fetch(query, *params)
        
        return [
            {
                "id": r['id'],
                "city_id": r['city_id'],
                "city_code": r['city_code'],
                "city_name": r['city_name'],
                "pair_symbol": r['pair_symbol'],
                "markup_percent": float(r['markup_percent']),
                "markup_fixed": float(r['markup_fixed']),
                "enabled": r['enabled']
            }
            for r in rows
        ]

@app.post("/api/city-pair-markups")
async def api_create_city_pair_markup(
    request: Request,
    user=Depends(get_current_user)
):
    """API: Создать специфичную наценку для пары в городе"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    city_id = data.get('city_id')
    pair_symbol = data.get('pair_symbol')
    markup_percent = float(data.get('markup_percent', 0))
    markup_fixed = float(data.get('markup_fixed', 0))
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO city_pair_markups (city_id, pair_symbol, markup_percent, markup_fixed)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (city_id, pair_symbol) 
            DO UPDATE SET 
                markup_percent = EXCLUDED.markup_percent,
                markup_fixed = EXCLUDED.markup_fixed,
                updated_at = NOW()
        """, city_id, pair_symbol, markup_percent, markup_fixed)
        
        return {"success": True}

@app.delete("/api/city-pair-markups/{markup_id}")
async def api_delete_city_pair_markup(
    markup_id: int,
    user=Depends(get_current_user)
):
    """API: Удалить специфичную наценку"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM city_pair_markups WHERE id = $1", markup_id)
        
        return {"success": True}


# ============================================================================
# TRADING PAIRS MANAGEMENT API - Управление торговыми парами
# ============================================================================

@app.post("/api/fx/source-pairs")
async def api_create_source_pair(
    request: Request,
    user=Depends(get_current_user)
):
    """API: Добавить торговую пару для источника"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    source_code = data.get('source_code')
    source_symbol = data.get('source_symbol')  # Символ в API источника
    internal_symbol = data.get('internal_symbol')  # Наш внутренний символ
    enabled = data.get('enabled', True)
    
    if not source_code or not source_symbol or not internal_symbol:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="source_code, source_symbol and internal_symbol are required")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Получаем ID источника
        source = await conn.fetchrow("SELECT id FROM fx_source WHERE code = $1", source_code)
        if not source:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Source {source_code} not found")
        
        try:
            pair_id = await conn.fetchval("""
                INSERT INTO fx_source_pair (source_id, source_symbol, internal_symbol, enabled)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, source['id'], source_symbol, internal_symbol, enabled)
            
            # Также добавляем в trading_pairs если еще нет
            base, quote = internal_symbol.split('/')
            await conn.execute("""
                INSERT INTO trading_pairs (base_currency, quote_currency, base_name, quote_name, is_active)
                VALUES ($1, $2, $1, $2, $3)
                ON CONFLICT (base_currency, quote_currency) DO NOTHING
            """, base, quote, enabled)
            
            return {
                "success": True,
                "pair_id": pair_id,
                "source_code": source_code,
                "source_symbol": source_symbol,
                "internal_symbol": internal_symbol
            }
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Error creating pair: {str(e)}")

@app.get("/api/fx/all-pairs")
async def api_get_all_pairs(user=Depends(get_current_user)):
    """API: Получить все торговые пары из всех источников"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                sp.id,
                sp.source_id,
                sp.source_symbol,
                sp.internal_symbol,
                sp.enabled,
                s.code as source_code,
                s.name as source_name,
                rr.raw_price as last_rate
            FROM fx_source_pair sp
            JOIN fx_source s ON sp.source_id = s.id
            LEFT JOIN fx_raw_rate rr ON rr.source_pair_id = sp.id
            ORDER BY sp.internal_symbol, s.code
        """)
        
        return [
            {
                "id": r['id'],
                "source_id": r['source_id'],
                "source_code": r['source_code'],
                "source_name": r['source_name'],
                "source_symbol": r['source_symbol'],
                "internal_symbol": r['internal_symbol'],
                "enabled": r['enabled'],
                "last_rate": float(r['last_rate']) if r['last_rate'] else None
            }
            for r in rows
        ]

@app.delete("/api/fx/source-pairs/{pair_id}")
async def api_delete_source_pair(
    pair_id: int,
    user=Depends(get_current_user)
):
    """API: Удалить торговую пару"""
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM fx_source_pair WHERE id = $1", pair_id)
        
        return {"success": True, "pair_id": pair_id}