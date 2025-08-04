import pytest
from fastapi.testclient import TestClient
from src.web_admin.main import app

client = TestClient(app)

def test_login_page():
    """Тест страницы входа"""
    response = client.get("/login")
    assert response.status_code == 200
    assert "login" in response.text.lower()

def test_admin_redirect_without_auth():
    """Тест редиректа на страницу входа без авторизации"""
    response = client.get("/admin")
    assert response.status_code == 307  # Redirect
    assert response.headers["location"] == "/login"

def test_login_with_wrong_credentials():
    """Тест входа с неправильными учетными данными"""
    response = client.post("/login", data={
        "username": "wrong",
        "password": "wrong"
    })
    assert response.status_code == 200
    assert "неверный логин или пароль" in response.text.lower()

def test_login_with_correct_credentials():
    """Тест входа с правильными учетными данными"""
    response = client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 307  # Redirect
    assert response.headers["location"] == "/admin"

def test_admin_dashboard_with_auth():
    """Тест доступа к админке с авторизацией"""
    # Сначала логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    # Теперь проверяем доступ к админке
    response = client.get("/admin")
    assert response.status_code == 200
    assert "панель управления" in response.text.lower()

def test_trading_pairs_page():
    """Тест страницы торговых пар"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/trading-pairs")
    assert response.status_code == 200
    assert "торговые пары" in response.text.lower()

def test_rates_page():
    """Тест страницы курсов валют"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/rates")
    assert response.status_code == 200
    assert "курсы валют" in response.text.lower()

def test_payout_methods_page():
    """Тест страницы способов выплаты"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/payout-methods")
    assert response.status_code == 200
    assert "способы выплаты" in response.text.lower()

def test_faq_page():
    """Тест страницы FAQ"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/faq")
    assert response.status_code == 200
    assert "faq" in response.text.lower()

def test_orders_page():
    """Тест страницы заявок"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/orders")
    assert response.status_code == 200
    assert "заявки" in response.text.lower()

def test_users_page():
    """Тест страницы пользователей"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "пользователи" in response.text.lower()

def test_notifications_page():
    """Тест страницы уведомлений"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/notifications")
    assert response.status_code == 200
    assert "уведомления" in response.text.lower()

def test_stats_page():
    """Тест страницы статистики"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/stats")
    assert response.status_code == 200
    assert "статистика" in response.text.lower()

def test_live_chats_page():
    """Тест страницы live чатов"""
    # Логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    response = client.get("/admin/live-chats")
    assert response.status_code == 200
    assert "live чаты" in response.text.lower()

def test_logout():
    """Тест выхода из системы"""
    # Сначала логинимся
    client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    
    # Теперь выходим
    response = client.get("/logout")
    assert response.status_code == 307  # Redirect
    assert response.headers["location"] == "/login"
    
    # Проверяем, что после выхода нет доступа к админке
    response = client.get("/admin")
    assert response.status_code == 307  # Redirect to login 