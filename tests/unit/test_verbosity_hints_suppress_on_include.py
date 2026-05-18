"""N13: _hints не должен дублировать сигнал, если поле уже в include[].

`list_tasks(include=['description'])` возвращает description в каждом
item. Параллельно показывать `_hints.has_description=true` — лишний
токен-шум без новой информации.
"""
from src.utils.verbosity import apply_verbosity, build_hints


def test_hints_suppress_description_when_in_include():
    raw = {"id": "u", "title": "x", "description": "<p>x</p>"}
    h = build_hints(raw, "task", include=["description"])
    assert "has_description" not in h
    # остальные hints — на месте
    assert "has_checklists" in h


def test_hints_keep_description_when_not_in_include():
    raw = {"id": "u", "title": "x", "description": "<p>x</p>"}
    h = build_hints(raw, "task", include=["checklists"])
    assert h.get("has_description") is True
    assert "has_checklists" not in h


def test_hints_include_all_suppresses_all_hints_with_include_key():
    """include=['all'] подтягивает все task-opt-ins, has_X становятся
    избыточными (кроме has_deadline — у которого нет include_key)."""
    raw = {"id": "u", "title": "x", "description": "<p>x</p>",
           "deadline": {"deadline": 1}}
    h = build_hints(raw, "task", include=["all"])
    # has_deadline остаётся (нет include_key для самого deadline)
    assert "has_deadline" in h
    # Все остальные hints с include_key — подавлены
    assert "has_description" not in h
    assert "has_checklists" not in h
    assert "has_stickers" not in h
    assert "has_stopwatch" not in h
    assert "has_timer" not in h


def test_hints_no_include_full_set():
    raw = {"id": "u", "title": "x"}
    h = build_hints(raw, "task")
    # все 7 hints на месте
    assert set(h.keys()) == {
        "has_description", "has_checklists", "has_stickers",
        "has_extension_data", "has_deadline", "has_stopwatch", "has_timer",
    }


def test_apply_verbosity_compact_list_propagates_include_to_hints():
    """End-to-end: apply_verbosity передаёт include в build_hints."""
    raw = [{
        "id": "u", "title": "x", "columnId": "c",
        "description": "<p>x</p>",
    }]
    result = apply_verbosity(
        raw, "task", verbosity="compact", include=["description"], is_list=True
    )
    item = result[0]
    assert item["description"] == "<p>x</p>"
    assert "has_description" not in item["_hints"]
