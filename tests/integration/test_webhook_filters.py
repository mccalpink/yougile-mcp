"""Integration tests: WebhookFilters.name normalizer (Quirk 3)."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.mark.integration
def test_webhook_filters_string_accepted(api_key, test_workspace_slug):
    """Передать name как строку — проходит без ошибки."""
    from src.utils.normalizers import normalize_webhook_filters

    # normalize_webhook_filters принимает list[dict]
    valid_filters = [{"name": "location", "value": ["task-created"]}]
    result, meta = normalize_webhook_filters(valid_filters)

    assert result[0]["name"] == "location"
    # Нет лишних notes (строка — правильный формат, нормализация не нужна)
    assert not meta.get("notes"), f"Не ожидали notes для корректного фильтра: {meta}"


@pytest.mark.integration
def test_webhook_filters_array_single_corrected(api_key, test_workspace_slug):
    """Передать name как массив из одного элемента — normalizer исправляет."""
    from src.utils.normalizers import normalize_webhook_filters

    array_filters = [{"name": ["location"], "value": ["task-created"]}]
    result, meta = normalize_webhook_filters(array_filters)

    # Normalizer берёт первый элемент массива
    assert result[0]["name"] == "location", \
        f"Ожидали 'location', получили: {result[0]['name']}"
    # meta.notes фиксирует коррекцию
    assert any("auto-corrected" in n for n in meta.get("notes", [])), \
        f"Ожидали запись о коррекции в notes: {meta}"


@pytest.mark.integration
def test_webhook_filters_array_multiple_raises(api_key, test_workspace_slug):
    """Передать name как массив из 2+ элементов — возвращает ошибку."""
    from src.utils.normalizers import normalize_webhook_filters
    from src.core.exceptions import ValidationError

    bad_filters = [{"name": ["location", "task"], "value": ["task-created"]}]

    with pytest.raises(ValidationError, match="WebhookFilters.name"):
        normalize_webhook_filters(bad_filters)
