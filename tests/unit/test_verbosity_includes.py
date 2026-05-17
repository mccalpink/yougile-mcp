import pytest
from src.utils.verbosity import apply_verbosity


SAMPLE_TASK = {
    "id": "abc-123",
    "title": "Написать тесты",
    "columnId": "col-1",
    "completed": False,
    "description": "<p>Покрыть unit-тесты</p>",
    "checklists": [{"id": "cl-1", "items": []}],
    "deadline": {
        "deadline": 1748217600000,
        "history": [{"changed": 1747000000000}],
    },
    "stickers": {"sticker-uuid": "state-uuid"},
    "extensionData": {"foo": "bar"},
    "stopwatch": None,
    "timer": None,
    "timeTracking": None,
    "deal": None,
    "timestamp": 1747483200000,
    "archivedTimestamp": None,
    "completedTimestamp": None,
}


def test_include_title_at_custom():
    """include=['title'] при custom добавляет title к id."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=["title"])
    assert result["id"] == "abc-123"
    assert result["title"] == "Написать тесты"
    assert "columnId" not in result


def test_include_deadline_history():
    """include=['deadline_history'] при custom добавляет deadline.history."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=["deadline_history"])
    assert "deadline" in result
    assert "history" in result["deadline"]
    assert result["deadline"]["history"] == [{"changed": 1747000000000}]


def test_include_unknown_key_goes_to_meta():
    """include=['unknown_key'] → результат содержит _meta.unknown_includes."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=["unknown_key"])
    assert "_meta" in result
    assert "unknown_includes" in result["_meta"]
    assert "unknown_key" in result["_meta"]["unknown_includes"]


def test_include_all_adds_all_optins():
    """include=['all'] → все opt-in поля присутствуют в ответе."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=["all"])
    # Все opt-in ключи должны присутствовать (если поле непустое в SAMPLE_TASK)
    assert "description" in result
    assert "checklists" in result
    assert "stickers" in result
    assert "extensionData" in result


def test_include_idempotent_at_compact():
    """include=['title'] при compact (где title уже есть) — no-op, не ошибка."""
    data = {"id": "x", "title": "T", "columnId": "col"}
    result = apply_verbosity(data, dto_type="task", verbosity="compact", include=["title"])
    assert result.get("title") == "T"  # поле осталось, не задвоилось


def test_include_none_at_custom_returns_only_id():
    """include=None при custom → только id (базовый случай Task 1.1)."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=None)
    assert result == {"id": "abc-123"}


def test_include_multiple_fields():
    """include=['title', 'completed'] добавляет оба поля."""
    result = apply_verbosity(SAMPLE_TASK, dto_type="task", verbosity="custom", include=["title", "completed"])
    assert result["title"] == "Написать тесты"
    assert result["completed"] is False
    assert "columnId" not in result
