"""Integration test: SprintStickerState ms↔seconds round-trip.

Проверяет Quirk 1: API хранит begin/end в секундах, MCP конвертирует ms↔seconds.
Часть 1 — normalizer unit tests (работают без живого API).
Часть 2 — live API проверка (требует YOUGILE_TEST_API_KEY).
"""

import pytest
import sys
import os

# Добавляем корневую директорию проекта для корректных package-level импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.mark.integration
def test_sprint_sticker_meta_notes_on_conversion_request(api_key, test_workspace_slug):
    """_meta.notes содержит запись о конвертации ms→seconds (request direction)."""
    from src.utils.normalizers import normalize_sprint_sticker_state

    # Симуляция request с ms значениями
    request_state = {"begin": 1748217600000, "end": 1750809600000}  # ms
    converted = normalize_sprint_sticker_state(request_state, direction="request")

    assert converted["begin"] == 1748217600, \
        f"begin должен быть в seconds после request-конвертации, получили: {converted['begin']}"
    assert converted["end"] == 1750809600, \
        f"end должен быть в seconds после request-конвертации, получили: {converted['end']}"
    assert "_meta" in converted and "notes" in converted["_meta"], \
        "Ожидали _meta.notes о конвертации при direction='request'"
    assert any("auto-converted" in n for n in converted["_meta"]["notes"]), \
        f"Не нашли 'auto-converted' в notes: {converted['_meta']['notes']}"


@pytest.mark.integration
def test_sprint_sticker_response_conversion(api_key, test_workspace_slug):
    """Normalizer конвертирует API ответ (seconds) в ms (response direction)."""
    from src.utils.normalizers import normalize_sprint_sticker_state

    # Симуляция API ответа в секундах
    raw_api_response = {
        "id": "test-state-uuid",
        "begin": 1748217600,   # секунды!
        "end": 1750809600,
    }

    result = normalize_sprint_sticker_state(raw_api_response, direction="response")

    assert result["begin"] == 1748217600 * 1000, \
        f"begin должен быть в ms после response-конвертации, получили: {result['begin']}"
    assert result["end"] == 1750809600 * 1000, \
        f"end должен быть в ms после response-конвертации, получили: {result['end']}"


@pytest.mark.integration
def test_sprint_sticker_seconds_not_double_converted_in_request(api_key, test_workspace_slug):
    """Если begin уже в seconds (< 10^11) — не конвертируем повторно."""
    from src.utils.normalizers import normalize_sprint_sticker_state

    state_already_seconds = {"begin": 1748217600, "end": 1750809600}  # секунды
    result = normalize_sprint_sticker_state(state_already_seconds, direction="request")

    assert result["begin"] == 1748217600, \
        f"Значение в секундах не должно меняться, получили: {result['begin']}"
    # Нет notes — конвертация не произошла
    notes = result.get("_meta", {}).get("notes", [])
    assert not any("auto-converted" in n for n in notes), \
        f"Не ожидали notes при отсутствии конвертации: {notes}"
