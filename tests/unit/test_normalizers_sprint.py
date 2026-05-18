import pytest
from src.utils.normalizers import normalize_sprint_sticker_state

# --- Direction: Request → API (ms → seconds) ---


def test_sprint_state_request_ms_converted_to_seconds():
    """Если begin > 10^11 — выглядит как ms — конвертируем в seconds."""
    state = {"begin": 1748217600000, "end": 1748304000000}
    result = normalize_sprint_sticker_state(state, direction="request")
    assert result["begin"] == 1748217600   # 1748217600000 / 1000
    assert result["end"] == 1748304000


def test_sprint_state_request_seconds_not_changed():
    """Если begin < 10^11 — уже в секундах — не трогаем."""
    state = {"begin": 1748217600, "end": 1748304000}
    result = normalize_sprint_sticker_state(state, direction="request")
    assert result["begin"] == 1748217600
    assert result["end"] == 1748304000


def test_sprint_state_request_adds_meta_note_when_converted():
    """При конвертации ms→sec добавляем заметку в _meta.notes."""
    state = {"begin": 1748217600000, "end": 1748304000000}
    result = normalize_sprint_sticker_state(state, direction="request")
    assert "_meta" in result
    notes = result["_meta"].get("notes", [])
    assert any("ms" in note and "seconds" in note for note in notes)


def test_sprint_state_request_no_meta_note_when_not_converted():
    """Если конвертация не нужна — _meta.notes не добавляем."""
    state = {"begin": 1748217600, "end": 1748304000}
    result = normalize_sprint_sticker_state(state, direction="request")
    # _meta может отсутствовать или notes пустой
    if "_meta" in result:
        assert not result["_meta"].get("notes")


# --- Direction: Response ← API (seconds → ms) ---


def test_sprint_state_response_seconds_converted_to_ms():
    """API возвращает seconds — конвертируем в ms для единообразия."""
    state = {"begin": 1748217600, "end": 1748304000}
    result = normalize_sprint_sticker_state(state, direction="response")
    assert result["begin"] == 1748217600000
    assert result["end"] == 1748304000000


def test_sprint_state_response_none_begin_handled():
    """Если begin/end = None — не падаем."""
    state = {"begin": None, "end": None}
    result = normalize_sprint_sticker_state(state, direction="response")
    assert result["begin"] is None
    assert result["end"] is None


def test_sprint_state_idempotent_request():
    """Повторный вызов request с уже-seconds не ломает данные."""
    state = {"begin": 1748217600, "end": 1748304000}
    r1 = normalize_sprint_sticker_state(state, direction="request")
    r2 = normalize_sprint_sticker_state(
        {k: v for k, v in r1.items() if k != "_meta"},
        direction="request"
    )
    assert r1["begin"] == r2["begin"]


# --- M5: idempotency для response ---


def test_sprint_state_response_idempotent_double_call():
    """Повторный вызов response с уже-ms значениями не умножает дальше.

    Раньше функция безусловно делала val * 1000 — второй вызов давал
    timestamps в 1000× больше реального (год становился ~2099+ × 1000).
    """
    state = {"begin": 1748217600, "end": 1748304000}
    r1 = normalize_sprint_sticker_state(state, direction="response")
    r2 = normalize_sprint_sticker_state(r1, direction="response")
    assert r1["begin"] == r2["begin"] == 1748217600000
    assert r1["end"] == r2["end"] == 1748304000000


def test_sprint_state_response_already_ms_left_alone():
    """Если begin/end уже в ms — не трогаем."""
    state = {"begin": 1748217600000, "end": 1748304000000}
    result = normalize_sprint_sticker_state(state, direction="response")
    assert result["begin"] == 1748217600000
    assert result["end"] == 1748304000000


def test_sprint_state_invalid_direction_raises():
    state = {"begin": 1, "end": 2}
    with pytest.raises(ValueError, match="Unknown direction"):
        normalize_sprint_sticker_state(state, direction="foo")
