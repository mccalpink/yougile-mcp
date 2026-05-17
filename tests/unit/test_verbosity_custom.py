import pytest
from src.utils.verbosity import apply_verbosity


def test_custom_returns_only_id_for_single_dict():
    """custom mode: single dict → только id, всё остальное дропнуто."""
    data = {"id": "abc-123", "title": "Задача", "columnId": "col-1", "completed": False}
    result = apply_verbosity(data, dto_type="task", verbosity="custom")
    assert result == {"id": "abc-123"}


def test_custom_returns_only_ids_in_paging_envelope():
    """custom mode: paging envelope → content содержит только {id} на каждый элемент."""
    data = {
        "paging": {"totalCount": 2, "offset": 0, "limit": 20},
        "content": [
            {"id": "abc-123", "title": "Задача 1", "completed": False},
            {"id": "def-456", "title": "Задача 2", "completed": True},
        ],
    }
    result = apply_verbosity(data, dto_type="task", verbosity="custom")
    assert result["content"] == [{"id": "abc-123"}, {"id": "def-456"}]
    assert "paging" in result


def test_custom_returns_only_ids_in_bare_list():
    """custom mode: bare list → каждый элемент содержит только id."""
    data = [{"id": "a"}, {"id": "b", "title": "X"}]
    result = apply_verbosity(data, dto_type="task", verbosity="custom")
    assert result == [{"id": "a"}, {"id": "b"}]


def test_full_still_passthrough():
    """Backward-compat: verbosity='full' возвращает данные без изменений."""
    data = {"id": "abc-123", "title": "Задача", "timestamp": 1747483200000}
    result = apply_verbosity(data, dto_type="task", verbosity="full")
    assert result == data


def test_custom_unknown_dto_passthrough():
    """custom mode с неизвестным dto_type → данные без изменений (fail open)."""
    data = {"id": "x", "foo": "bar"}
    result = apply_verbosity(data, dto_type="unknown_dto", verbosity="custom")
    assert result == data
