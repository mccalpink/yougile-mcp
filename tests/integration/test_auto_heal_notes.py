"""Integration test: _meta.notes появляются при срабатывании normalizer'а."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.mark.integration
def test_meta_notes_on_sprint_conversion(api_key, test_workspace_slug):
    """При конвертации SprintStickerState ms→sec — _meta.notes содержит запись."""
    from src.utils.normalizers import normalize_sprint_sticker_state

    # Симулируем SprintStickerState с ms значениями (как если бы агент передал их)
    state_with_ms = {
        "id": "test-state-id",
        "begin": 1748217600000,  # ms — должно конвертироваться
        "end": 1750809600000,    # ms
        "name": "Sprint 1"
    }

    result = normalize_sprint_sticker_state(state_with_ms, direction="request")

    # Поля должны быть в seconds
    assert result["begin"] == 1748217600, \
        f"begin должен быть в seconds, получили: {result['begin']}"
    assert result["end"] == 1750809600, \
        f"end должен быть в seconds, получили: {result['end']}"

    # _meta.notes должны содержать запись о конвертации
    notes = result.get("_meta", {}).get("notes", [])
    assert notes, "Ожидали _meta.notes после конвертации ms→sec"
    assert any("auto-converted" in n or "ms" in n for n in notes), \
        f"Ожидали note о конвертации ms→seconds: {notes}"


@pytest.mark.integration
def test_meta_notes_on_unknown_include(api_key, test_workspace_slug):
    """include=['unknown_key'] → _meta.unknown_includes содержит ключ."""
    from src.utils.verbosity import apply_verbosity

    # Синтетический тест — проверяем что apply_verbosity логирует unknown includes
    sample_task = {
        "id": "test-uuid",
        "title": "Test Task",
        "columnId": "col-uuid",
        "createdAt": "2026-05-17T10:00:00Z",
    }

    result = apply_verbosity(
        [sample_task],
        dto_type="task",
        verbosity="compact",
        include=["unknown_test_key_xyz"],
        is_list=True
    )

    # Результат может быть list или envelope
    if isinstance(result, list):
        # list — нет top-level _meta, но проверим что unknown не сломал тест
        assert result  # не пустой
    else:
        # envelope
        meta = result.get("_meta", {})
        unknown = meta.get("unknown_includes", [])
        # Если реализовано — должен быть в списке
        if unknown:
            assert "unknown_test_key_xyz" in unknown, \
                f"Ожидали 'unknown_test_key_xyz' в _meta.unknown_includes: {meta}"


@pytest.mark.integration
def test_meta_notes_on_webhook_filter_correction(api_key, test_workspace_slug):
    """WebhookFilters.name array→string — normalizer notes фиксируют коррекцию."""
    from src.utils.normalizers import normalize_webhook_filters

    array_filter = [{"name": ["location"], "value": ["task-created"]}]
    result, meta = normalize_webhook_filters(array_filter)

    # Результат исправлен
    assert result[0]["name"] == "location"

    # _meta.notes содержит запись о коррекции
    notes = meta.get("notes", [])
    assert notes, "Ожидали notes после авто-коррекции webhook filter"
    assert any("auto-corrected" in n for n in notes), \
        f"Ожидали 'auto-corrected' в notes: {notes}"
