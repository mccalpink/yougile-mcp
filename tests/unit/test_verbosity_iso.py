import pytest
from src.utils.verbosity import apply_verbosity, iso_from_ms


def test_iso_from_ms_basic():
    """1779019200000 ms → '2026-05-17T12:00:00Z' (UTC ISO-8601)."""
    result = iso_from_ms(1779019200000)
    assert result == "2026-05-17T12:00:00Z"


def test_iso_from_ms_none():
    """None → None (нет конвертации)."""
    assert iso_from_ms(None) is None


def test_iso_from_ms_zero():
    """0 → None (epoch 0 считается пустым)."""
    assert iso_from_ms(0) is None


def test_compact_task_has_created_at_iso():
    """compact task: createdAt присутствует как ISO строка, timestamp отсутствует."""
    data = {
        "id": "abc",
        "title": "Задача",
        "columnId": "col-1",
        "timestamp": 1779019200000,
        "completedTimestamp": None,
        "archivedTimestamp": None,
    }
    result = apply_verbosity(data, dto_type="task", verbosity="compact")
    assert "createdAt" in result
    assert result["createdAt"] == "2026-05-17T12:00:00Z"
    # Raw timestamp дропнут в compact
    assert "timestamp" not in result


def test_compact_task_completed_at_if_nonempty():
    """compact task: completedAt появляется только если completedTimestamp непустой."""
    data = {
        "id": "abc",
        "title": "Задача",
        "columnId": "col-1",
        "timestamp": 1747483200000,
        "completedTimestamp": 1748217600000,
        "archivedTimestamp": None,
    }
    result = apply_verbosity(data, dto_type="task", verbosity="compact")
    assert "completedAt" in result
    assert "archivedAt" not in result  # archivedTimestamp=None → не показываем


def test_full_keeps_raw_timestamps():
    """full mode: raw timestamp/completedTimestamp/archivedTimestamp остаются как ms."""
    data = {
        "id": "abc",
        "title": "Задача",
        "timestamp": 1747483200000,
        "completedTimestamp": 1748217600000,
        "archivedTimestamp": None,
    }
    result = apply_verbosity(data, dto_type="task", verbosity="full")
    assert result["timestamp"] == 1747483200000
    assert result["completedTimestamp"] == 1748217600000
    assert "createdAt" not in result
