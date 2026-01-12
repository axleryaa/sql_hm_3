"""
Конфигурация pytest для тестов приложения.

Предоставляет общие фикстуры для тестирования.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
