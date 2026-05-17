import pytest
from src.utils.verbosity import apply_verbosity


TASK_WITH_DESCRIPTION = {
    "id": "abc-123",
    "title": "Задача с описанием",
    "columnId": "col-1",
    "description": "<p>Есть описание</p>",
    "checklists": [],
    "stickers": {},
    "extensionData": {},
    "stopwatch": None,
    "timer": None,
    "deadline": {"deadline": 1748217600000},
    "timestamp": 1747483200000,
    "completed": False,
}

TASK_WITHOUT_DESCRIPTION = {
    "id": "def-456",
    "title": "Задача без описания",
    "columnId": "col-1",
    "description": "",
    "checklists": [{"id": "cl-1"}],
    "stickers": {"s1": "v1"},
    "extensionData": {},
    "stopwatch": {"running": True},
    "timer": None,
    "deadline": None,
    "timestamp": 1747483200000,
    "completed": False,
}


def test_list_compact_has_hints_with_description():
    """compact list_*: _hints присутствует, has_description=True для задачи с описанием."""
    data = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [TASK_WITH_DESCRIPTION],
    }
    result = apply_verbosity(data, dto_type="task", verbosity="compact", is_list=True)
    item = result["content"][0]
    assert "_hints" in item
    assert item["_hints"]["has_description"] is True
    assert item["_hints"]["has_checklists"] is False


def test_list_compact_has_hints_with_checklists():
    """compact list_*: has_checklists=True и has_stickers=True для задачи с данными."""
    data = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [TASK_WITHOUT_DESCRIPTION],
    }
    result = apply_verbosity(data, dto_type="task", verbosity="compact", is_list=True)
    item = result["content"][0]
    assert item["_hints"]["has_description"] is False
    assert item["_hints"]["has_checklists"] is True
    assert item["_hints"]["has_stickers"] is True
    assert item["_hints"]["has_stopwatch"] is True
    assert item["_hints"]["has_deadline"] is False


def test_get_compact_no_hints():
    """compact get_*: _hints отсутствует в одиночном объекте."""
    result = apply_verbosity(TASK_WITH_DESCRIPTION, dto_type="task", verbosity="compact", is_list=False)
    assert "_hints" not in result


def test_hints_only_shows_bool_flags():
    """_hints содержит только has_X: true|false — никаких вложенных данных."""
    data = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [TASK_WITH_DESCRIPTION],
    }
    result = apply_verbosity(data, dto_type="task", verbosity="compact", is_list=True)
    hints = result["content"][0]["_hints"]
    for key, value in hints.items():
        assert key.startswith("has_"), f"Ключ '{key}' не начинается с 'has_'"
        assert isinstance(value, bool), f"Значение для '{key}' не bool: {value!r}"
