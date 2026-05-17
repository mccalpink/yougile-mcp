import pytest
from src.utils.normalizers import normalize_webhook_filters
from src.core.exceptions import ValidationError


def test_webhook_filters_string_name_passthrough():
    """Строка — корректный тип, без изменений."""
    filters = [{"name": "location", "value": ["some-uuid"]}]
    result, _ = normalize_webhook_filters(filters)
    assert result[0]["name"] == "location"


def test_webhook_filters_array_single_element_coerced():
    """Массив из одного элемента — берём первый."""
    filters = [{"name": ["location"], "value": ["some-uuid"]}]
    result, _ = normalize_webhook_filters(filters)
    assert result[0]["name"] == "location"


def test_webhook_filters_array_single_adds_meta_note():
    """При коррекции возвращается meta.notes."""
    filters = [{"name": ["location"], "value": ["some-uuid"]}]
    result, meta = normalize_webhook_filters(filters)
    notes = meta.get("notes", [])
    assert any("auto-corrected" in note or "coerced" in note for note in notes)


def test_webhook_filters_array_multiple_raises_error():
    """Массив из нескольких элементов — ошибка с ясным текстом."""
    filters = [{"name": ["location", "title"], "value": ["uuid"]}]
    with pytest.raises(Exception) as exc_info:
        normalize_webhook_filters(filters)
    assert "multiple" in str(exc_info.value).lower() or "array" in str(exc_info.value).lower()


def test_webhook_filters_empty_list_passthrough():
    """Пустой список фильтров — no-op."""
    result, meta = normalize_webhook_filters([])
    assert result == []
    assert meta == {}


def test_webhook_filters_idempotent():
    """Повторная нормализация строки не ломает данные."""
    filters = [{"name": "location", "value": ["uuid"]}]
    r1, _ = normalize_webhook_filters(filters)
    r2, _ = normalize_webhook_filters(r1)
    assert r1[0]["name"] == r2[0]["name"]


def test_webhook_filters_always_returns_tuple():
    """Функция всегда возвращает tuple (list, dict)."""
    filters = [{"name": "location", "value": ["uuid"]}]
    result = normalize_webhook_filters(filters)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], list)
    assert isinstance(result[1], dict)
