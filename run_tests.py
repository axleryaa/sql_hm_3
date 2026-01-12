#!/usr/bin/env python3
"""
Скрипт для запуска тестов приложения.

Использование:
    python run_tests.py              # Запуск всех тестов
    python run_tests.py -v           # Запуск с подробным выводом
    python run_tests.py -k test_name # Запуск конкретного теста
"""

import subprocess
import sys
import os

def main():
    """Запуск тестов с правильными зависимостями"""
    cmd = ["uv", "run", "python", "-m", "pytest"] + sys.argv[1:]

    try:
        result = subprocess.run(cmd, cwd=os.getcwd())
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nТестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка запуска тестов: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
