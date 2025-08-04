#!/usr/bin/env python3
"""
Скрипт для запуска веб-админки в режиме разработки
"""

import os
import sys
import uvicorn
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Запуск веб-админки"""
    print("🚀 Запуск веб-админки...")
    print("📊 Админка будет доступна по адресу: http://localhost:8000")
    print("🔐 Логин: admin, Пароль: admin123")
    print("⏹️  Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    # Настройки для разработки
    uvicorn.run(
        "src.web_admin.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src/web_admin"],
        log_level="info"
    )

if __name__ == "__main__":
    main() 