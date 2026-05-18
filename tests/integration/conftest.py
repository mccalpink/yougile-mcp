"""Конфигурация integration tests для yougile-mcp.

Все integration тесты пропускаются если YOUGILE_TEST_API_KEY не задан.
Запуск: YOUGILE_TEST_API_KEY=<key> pytest -m integration
"""

import os
import pytest


@pytest.fixture(scope="session")
def api_key():
    """API ключ для integration тестов."""
    key = os.getenv("YOUGILE_TEST_API_KEY")
    if not key:
        pytest.skip("YOUGILE_TEST_API_KEY не задан — пропускаем integration тесты")
    return key


@pytest.fixture(scope="session")
def test_workspace_id():
    """UUID тестового workspace."""
    return os.getenv(
        "YOUGILE_TEST_WORKSPACE_ID",
        "f5080490-0038-4416-8831-69009b069390"  # workspace "test"
    )


@pytest.fixture(scope="session")
def test_workspace_slug():
    """Slug тестового workspace."""
    return os.getenv("YOUGILE_TEST_WORKSPACE", "test")
