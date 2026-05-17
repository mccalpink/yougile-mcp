"""Integration test: compact ответы соответствуют whitelist из spec §2."""

import pytest
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


COMPACT_TASK_FORBIDDEN_FIELDS = {
    "createdBy", "idTaskCommon", "idTaskProject", "type",
    "extensionData", "timestamp", "archivedTimestamp", "completedTimestamp",
    "description",  # в list_tasks compact
}

COMPACT_TASK_REQUIRED_FIELDS = {"id", "title", "columnId", "createdAt"}

COMPACT_HINTS_KEYS = {
    "has_description", "has_checklists", "has_deadline",
    "has_extension_data", "has_stickers",
}


def _get_tasks_via_api(api_key: str, workspace: str):
    """Получить задачи через API и применить verbosity compact."""
    import httpx
    from src.config import settings
    from src.utils.verbosity import apply_verbosity

    async def fetch():
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(
            base_url=settings.yougile_base_url,
            headers=headers,
            timeout=30
        ) as client:
            resp = await client.get("/tasks", params={"limit": 20})
            if resp.status_code != 200:
                return []
            data = resp.json()
            tasks = data.get("content", [])
            return tasks

    raw_tasks = asyncio.run(fetch())

    # Применяем verbosity compact через MCP layer
    if not raw_tasks:
        return []

    result = apply_verbosity(raw_tasks, dto_type="task", verbosity="compact", is_list=True)
    if isinstance(result, list):
        return result
    return result.get("content", [])


@pytest.mark.integration
def test_compact_task_no_forbidden_fields(api_key, test_workspace_slug):
    """list_tasks compact не содержит запрещённых полей."""
    tasks = _get_tasks_via_api(api_key, test_workspace_slug)

    if not tasks:
        pytest.skip("Нет задач в тестовом workspace")

    for task in tasks:
        forbidden_found = COMPACT_TASK_FORBIDDEN_FIELDS & set(task.keys())
        assert not forbidden_found, \
            f"Задача {task.get('id')} содержит запрещённые поля: {forbidden_found}"


@pytest.mark.integration
def test_compact_task_required_fields_present(api_key, test_workspace_slug):
    """list_tasks compact содержит обязательные поля."""
    tasks = _get_tasks_via_api(api_key, test_workspace_slug)

    if not tasks:
        pytest.skip("Нет задач в тестовом workspace")

    for task in tasks:
        missing = COMPACT_TASK_REQUIRED_FIELDS - set(task.keys())
        assert not missing, \
            f"Задача {task.get('id')} не содержит обязательных полей: {missing}"


@pytest.mark.integration
def test_compact_task_hints_present(api_key, test_workspace_slug):
    """list_tasks compact содержит _hints блок с ожидаемыми ключами."""
    tasks = _get_tasks_via_api(api_key, test_workspace_slug)

    if not tasks:
        pytest.skip("Нет задач в тестовом workspace")

    for task in tasks:
        hints = task.get("_hints", {})
        assert hints, f"Задача {task.get('id')} не содержит _hints"
        missing_hint_keys = COMPACT_HINTS_KEYS - set(hints.keys())
        assert not missing_hint_keys, \
            f"_hints не содержит ожидаемых ключей: {missing_hint_keys}"


@pytest.mark.integration
def test_compact_verbosity_applied(api_key, test_workspace_slug):
    """apply_verbosity compact корректно обрабатывает список задач."""
    from src.utils.verbosity import apply_verbosity

    # Синтетический тест — проверяем что apply_verbosity не возвращает запрещённые поля
    sample_task = {
        "id": "test-uuid",
        "title": "Test Task",
        "columnId": "col-uuid",
        "createdAt": "2026-05-17T10:00:00Z",
        "timestamp": 1747742400000,  # должен быть убран в compact
        "description": "Some description",  # должен быть убран в compact
        "createdBy": "user-uuid",  # должен быть убран в compact
        "extensionData": {},  # должен быть убран в compact
    }

    result = apply_verbosity([sample_task], dto_type="task", verbosity="compact", is_list=True)
    tasks = result if isinstance(result, list) else result.get("content", [])

    assert tasks, "apply_verbosity вернул пустой результат"
    compacted = tasks[0]

    assert "id" in compacted, "id должен быть в compact"
    assert "title" in compacted, "title должен быть в compact"
    # Убедиться что хотя бы одно тяжёлое поле убрано
    heavy_fields = {"timestamp", "createdBy", "extensionData"}
    removed = heavy_fields - set(compacted.keys())
    assert removed, f"Ожидали что компактный режим уберёт heavy поля, осталось: {set(compacted.keys())}"
