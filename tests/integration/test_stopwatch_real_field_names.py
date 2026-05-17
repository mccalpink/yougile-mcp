"""Integration test: Зафиксировать реальные имена полей Stopwatch.

Quirk 2: OpenAPI схема говорит 'running/seconds/atMoment',
runtime пример показывает 'running/time/timestamp'.
Этот тест устанавливает истину.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.mark.integration
def test_stopwatch_real_field_names(api_key, test_workspace_slug, tmp_path):
    """Получить задачу с секундомером и зафиксировать реальные имена полей."""
    import asyncio
    from src.core.client import YouGileClient
    from src.core.auth import AuthManager
    from src.config import settings
    import httpx

    # Прямой API запрос для получения задач с stopwatch
    headers = {"Authorization": f"Bearer {api_key}"}

    async def fetch_tasks():
        async with httpx.AsyncClient(
            base_url=settings.yougile_base_url,
            headers=headers,
            timeout=30
        ) as client:
            resp = await client.get(
                "/tasks",
                params={"limit": 50}
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("content", [])

    tasks = asyncio.run(fetch_tasks())

    # Найти задачи с секундомером
    stopwatch_tasks = [
        t for t in tasks
        if t.get("stopwatch") is not None
    ]

    if not stopwatch_tasks:
        pytest.skip(
            "Нет задач с секундомером в тестовом workspace. "
            "Создай задачу с запущенным секундомером вручную перед запуском теста."
        )

    # Зафиксируем реальные поля
    sample_stopwatch = stopwatch_tasks[0]["stopwatch"]
    real_fields = list(sample_stopwatch.keys()) if isinstance(sample_stopwatch, dict) else []

    # Сохранить результат в постоянное место для Task 8.8
    import pathlib
    result_dir = pathlib.Path(
        "/home/user/projects/pets/yougile-mcp/docs/quirk_discoveries"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "stopwatch_fields.json").write_text(
        json.dumps({
            "real_fields": real_fields,
            "sample": sample_stopwatch,
            "openapi_expected": ["running", "seconds", "atMoment"],
            "runtime_example_showed": ["running", "time", "timestamp"],
            "actual": real_fields
        }, indent=2)
    )

    print(f"\nРеальные поля Stopwatch: {real_fields}")
    print(f"Значение: {sample_stopwatch}")

    # Минимальная проверка: поле 'running' должно быть (есть в обеих версиях схемы)
    assert "running" in real_fields, \
        f"Поле 'running' отсутствует в реальном ответе. Поля: {real_fields}"
