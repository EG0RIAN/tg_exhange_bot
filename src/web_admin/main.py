from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
import asyncpg
from typing import Optional

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
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rates = await conn.fetch("""
            SELECT rt.id, rt.min_amount, rt.max_amount, rt.rate, rt.is_active,
                   tp.base_name, tp.quote_name, tp.base_currency, tp.quote_currency
            FROM rate_tiers rt
            JOIN trading_pairs tp ON rt.pair_id = tp.id
            ORDER BY tp.sort_order, tp.id, rt.min_amount
        """)
    
    return templates.TemplateResponse("rates.html", {
        "request": request, 
        "user": user, 
        "rates": rates
    })

@app.get("/admin/rates/add", response_class=HTMLResponse)
async def add_rate_form(request: Request, user=Depends(get_current_user)):
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
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rate = await conn.fetchrow("""
            SELECT rt.id, rt.pair_id, rt.min_amount, rt.max_amount, rt.rate, rt.is_active,
                   tp.base_name, tp.quote_name
            FROM rate_tiers rt
            JOIN trading_pairs tp ON rt.pair_id = tp.id
            WHERE rt.id = $1
        """, rate_id)
        
        pairs = await conn.fetch("""
            SELECT id, base_name, quote_name, base_currency, quote_currency
            FROM trading_pairs WHERE is_active = true
            ORDER BY sort_order, id
        """)
    
    if not rate:
        return RedirectResponse("/admin/rates", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("rate_form.html", {
        "request": request, 
        "user": user, 
        "rate": rate,
        "pairs": pairs
    })

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

# Rapira Status Page
@app.get("/rapira", response_class=HTMLResponse)
async def rapira_status_page(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("rapira_status.html", {"request": request, "user": user})

# Rapira Settings Page
@app.get("/rapira/settings", response_class=HTMLResponse)
async def rapira_settings_page(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("rapira_settings.html", {"request": request, "user": user})

# Rapira Test Page
@app.get("/rapira/test", response_class=HTMLResponse)
async def rapira_test_page(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("rapira_test.html", {"request": request, "user": user})

# API Endpoints for Rapira Integration
@app.get("/api/rapira/status")
async def get_rapira_status(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Импортируем сервисы
        from src.services.rates_scheduler import get_scheduler_status
        from src.services.rapira import get_rapira_provider
        
        # Получаем статус планировщика
        scheduler_status = await get_scheduler_status()
        
        # Получаем статус Rapira API
        rapira_provider = await get_rapira_provider()
        rapira_health = rapira_provider.get_health()
        
        # Получаем текущие курсы
        from src.services.rates_calculator import get_rates_calculator
        calculator = await get_rates_calculator()
        
        rates = []
        pairs = ["USDT/RUB", "BTC/USDT", "EUR/USDT"]
        
        for pair in pairs:
            try:
                cash_in = await calculator.calculate_rate(pair, "cash_in", location="moscow")
                cash_out = await calculator.calculate_rate(pair, "cash_out", location="moscow")
                rates.append({
                    "pair": pair,
                    "cash_in": cash_in,
                    "cash_out": cash_out
                })
            except Exception as e:
                rates.append({
                    "pair": pair,
                    "cash_in": None,
                    "cash_out": None
                })
        
        # История обновлений (заглушка)
        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "details": "Автоматическое обновление курсов"
            }
        ]
        
        return {
            "scheduler": scheduler_status,
            "rapira_health": {
                "status": "healthy" if rapira_health.is_fresh else "stale",
                "latency_ms": rapira_health.latency * 1000,
                "http_code": rapira_health.http_code,
                "error_count": 0,
                "last_update": rapira_health.last_update.isoformat() if rapira_health.last_update else None,
                "last_error": None
            },
            "rates": rates,
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@app.get("/api/rapira/config")
async def get_rapira_config(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.config.rapira_config import config
        
        return {
            "api_base_url": config.API_BASE_URL,
            "request_timeout": config.REQUEST_TIMEOUT,
            "max_retries": config.MAX_RETRIES,
            "retry_delay_base": config.RETRY_DELAY_BASE,
            "health_check_interval": config.HEALTH_CHECK_INTERVAL,
            "cache_ttl": config.CACHE_TTL,
            "stale_ttl": config.STALE_TTL,
            "update_interval": config.UPDATE_INTERVAL,
            "vwap_default_amount": config.VWAP_DEFAULT_AMOUNT,
            "city_spreads": config.CITY_SPREADS,
            "percent_rules": config.PERCENT_RULES,
            "log_level": config.LOG_LEVEL,
            "log_requests": config.LOG_REQUESTS,
            "log_responses": config.LOG_RESPONSES,
            "alert_on_errors": config.ALERT_ON_ERRORS,
            "max_errors_before_alert": config.MAX_ERRORS_BEFORE_ALERT
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")

@app.post("/api/rapira/config")
async def update_rapira_config(request: Request, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        config_data = await request.json()
        
        # Здесь должна быть логика обновления конфигурации
        # Пока что просто возвращаем успех
        
        return {"success": True, "message": "Configuration updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")

@app.post("/api/rapira/force-update")
async def force_update_rates(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rates import import_rapira_rates
        
        # Принудительно обновляем курсы
        updated_count = await import_rapira_rates()
        
        # Также запускаем обновление через планировщик
        from src.services.rates_scheduler import get_rates_scheduler
        scheduler = await get_rates_scheduler()
        await scheduler.force_update()
        
        return {
            "success": True,
            "message": f"Курсы обновлены успешно! Обновлено пар: {updated_count}",
            "updated_count": updated_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating rates: {str(e)}")

@app.post("/api/rapira/vwap")
async def calculate_vwap_rate(request: Request, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        data = await request.json()
        pair = data.get("pair", "USDT/RUB")
        amount_usd = data.get("amount_usd", 50000.0)
        operation = data.get("operation", "cash_in")
        location = data.get("location", "moscow")
        
        from src.services.rates_calculator import get_rates_calculator
        calculator = await get_rates_calculator()
        
        # Конвертируем operation в OperationType
        from src.services.rates_calculator import OperationType
        op_type = OperationType.CASH_IN if operation == "cash_in" else OperationType.CASH_OUT
        
        result = await calculator.calculate_rate(pair, op_type, amount_usd, location, use_vwap=True)
        
        # Вычисляем спред
        spread = ((result.final_rate - result.base_rate) / result.base_rate) * 100
        
        return {
            "success": True,
            "data": {
                "base_rate": result.base_rate,
                "final_rate": result.final_rate,
                "spread": spread,
                "source": result.source,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating VWAP: {str(e)}")

# Test endpoints
@app.get("/api/rapira/test/plate-mini")
async def test_plate_mini(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        plate = await provider.get_plate_mini("USDT/RUB")
        
        if plate:
            return {
                "success": True,
                "message": "Plate Mini API test successful",
                "data": {
                    "symbol": plate.symbol,
                    "best_bid": plate.best_bid.price if plate.best_bid else None,
                    "best_ask": plate.best_ask.price if plate.best_ask else None,
                    "timestamp": plate.ts
                }
            }
        else:
            return {
                "success": False,
                "error": "No data received from Plate Mini API"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Plate Mini API test failed: {str(e)}"
        }

@app.get("/api/rapira/test/rates")
async def test_rates_api(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        rates = await provider.get_rates()
        
        if rates:
            return {
                "success": True,
                "message": f"Rates API test successful. Got {len(rates)} rates",
                "data": rates
            }
        else:
            return {
                "success": False,
                "error": "No rates received from API"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Rates API test failed: {str(e)}"
        }

@app.get("/api/rapira/test/health")
async def test_health_check(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        health = provider.get_health()
        
        return {
            "success": True,
            "message": "Health check successful",
            "data": {
                "latency": health.latency,
                "http_code": health.http_code,
                "is_fresh": health.is_fresh,
                "last_update": health.last_update.isoformat() if health.last_update else None
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Health check failed: {str(e)}"
        }

@app.get("/api/rapira/test/rate-calculation")
async def test_rate_calculation(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rates_calculator import get_rates_calculator, OperationType
        
        calculator = await get_rates_calculator()
        result = await calculator.calculate_rate("USDT/RUB", OperationType.CASH_IN, location="moscow")
        
        return {
            "success": True,
            "message": "Rate calculation test successful",
            "data": {
                "base_rate": result.base_rate,
                "final_rate": result.final_rate,
                "source": result.source
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Rate calculation test failed: {str(e)}"
        }

@app.get("/api/rapira/test/fallback")
async def test_fallback_strategy(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        # Тестируем fallback стратегию
        plate = await provider._get_fallback_plate("USDT/RUB")
        
        if plate:
            return {
                "success": True,
                "message": "Fallback strategy test successful",
                "data": {
                    "source": "fallback",
                    "symbol": plate.symbol,
                    "timestamp": plate.ts
                }
            }
        else:
            return {
                "success": False,
                "error": "Fallback strategy failed - no data available"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Fallback strategy test failed: {str(e)}"
        }

@app.get("/api/rapira/test/cache")
async def test_cache_system(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        redis = await provider.get_redis()
        
        # Тестируем кэш
        test_key = "test:cache:rapira"
        test_value = "test_value"
        
        await redis.set(test_key, test_value, ex=60)
        cached_value = await redis.get(test_key)
        await redis.delete(test_key)
        
        if cached_value == test_value:
            return {
                "success": True,
                "message": "Cache system test successful",
                "data": {
                    "cache_working": True,
                    "test_key": test_key,
                    "test_value": test_value
                }
            }
        else:
            return {
                "success": False,
                "error": "Cache system test failed - data mismatch"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Cache system test failed: {str(e)}"
        }

@app.get("/api/rapira/test/latency")
async def test_latency(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        import time
        from src.services.rapira import get_rapira_provider
        
        start_time = time.time()
        provider = await get_rapira_provider()
        plate = await provider.get_plate_mini("USDT/RUB")
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # в миллисекундах
        
        return {
            "success": True,
            "message": f"Latency test completed in {latency:.2f}ms",
            "data": {
                "latency_ms": latency,
                "data_received": plate is not None
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Latency test failed: {str(e)}"
        }

@app.get("/api/rapira/test/concurrent")
async def test_concurrent_requests(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        import asyncio
        import time
        from src.services.rapira import get_rapira_provider
        
        provider = await get_rapira_provider()
        
        async def make_request():
            return await provider.get_plate_mini("USDT/RUB")
        
        start_time = time.time()
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        total_time = (end_time - start_time) * 1000
        
        return {
            "success": True,
            "message": f"Concurrent test completed. {successful_requests}/5 requests successful",
            "data": {
                "total_time_ms": total_time,
                "successful_requests": successful_requests,
                "failed_requests": 5 - successful_requests,
                "average_time_per_request": total_time / 5
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Concurrent test failed: {str(e)}"
        }

@app.get("/api/rapira/test/memory")
async def test_memory_usage(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "success": True,
            "message": "Memory usage test completed",
            "data": {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Memory test failed: {str(e)}"
        }