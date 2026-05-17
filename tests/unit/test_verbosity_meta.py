import pytest
from src.utils.verbosity import apply_verbosity


TASK = {
    "id": "abc-123",
    "title": "Задача",
    "columnId": "col-1",
    "timestamp": 1747483200000,
    "createdBy": "user-uuid",
    "extensionData": {},
}


def test_meta_verbosity_always_present_compact():
    """_meta.verbosity присутствует всегда при compact."""
    result = apply_verbosity(TASK, dto_type="task", verbosity="compact")
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "compact"


def test_meta_verbosity_always_present_custom():
    """_meta.verbosity присутствует всегда при custom."""
    # Нужен unknown_includes чтобы _meta появился в single dict
    result = apply_verbosity(TASK, dto_type="task", verbosity="custom", include=["foo_bar"])
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "custom"


def test_meta_omitted_fields_only_if_dropped():
    """_meta.omitted_fields присутствует только если реально что-то дропнули."""
    result = apply_verbosity(TASK, dto_type="task", verbosity="compact")
    # TASK содержит timestamp, createdBy, extensionData — они дропаются
    assert "omitted_fields" in result["_meta"]
    assert "timestamp" in result["_meta"]["omitted_fields"]


def test_meta_omitted_fields_absent_if_nothing_dropped():
    """_meta.omitted_fields отсутствует если ничего не дропнули."""
    # Колонка минимальна — compact почти no-op
    column_data = {"id": "col-1", "title": "Backlog", "boardId": "board-1"}
    result = apply_verbosity(column_data, dto_type="column", verbosity="compact")
    if "_meta" in result:
        assert "omitted_fields" not in result["_meta"]


def test_meta_unknown_includes_only_if_unknown():
    """_meta.unknown_includes присутствует только при нераспознанных ключах."""
    result = apply_verbosity(TASK, dto_type="task", verbosity="custom", include=["foo_bar"])
    assert "unknown_includes" in result["_meta"]
    assert "foo_bar" in result["_meta"]["unknown_includes"]


def test_meta_unknown_includes_absent_for_valid_include():
    """_meta.unknown_includes отсутствует при валидном include ключе."""
    result = apply_verbosity(TASK, dto_type="task", verbosity="custom", include=["title"])
    if "_meta" in result:
        assert "unknown_includes" not in result["_meta"]


def test_meta_no_hint_key_in_new_format():
    """Старый 'hint' ключ в _meta убран — используется omitted_fields."""
    result = apply_verbosity(TASK, dto_type="task", verbosity="compact")
    assert "hint" not in result.get("_meta", {})
