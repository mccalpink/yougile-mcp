from src.utils.normalizers import normalize_stopwatch_warning


def test_stopwatch_with_stopwatch_field_adds_warning():
    """Если в ответе есть поле stopwatch — добавляем предупреждение в _meta."""
    task = {"id": "uuid-1", "stopwatch": {"running": True, "seconds": 3600}}
    result = normalize_stopwatch_warning(task)
    assert "_meta" in result
    notes = result["_meta"].get("notes", [])
    assert any("stopwatch" in note.lower() for note in notes)


def test_stopwatch_warning_mentions_field_name_mismatch():
    """Предупреждение должно объяснять суть проблемы."""
    task = {"id": "uuid-1", "stopwatch": {"running": True}}
    result = normalize_stopwatch_warning(task)
    notes = result["_meta"]["notes"]
    warning_text = " ".join(notes)
    # Должно упоминать что имена полей могут расходиться
    assert "mismatch" in warning_text.lower() or "field name" in warning_text.lower()


def test_stopwatch_no_stopwatch_field_no_warning():
    """Если stopwatch нет — _meta.notes не добавляем."""
    task = {"id": "uuid-1", "title": "Test"}
    result = normalize_stopwatch_warning(task)
    if "_meta" in result:
        assert not result["_meta"].get("notes")


def test_stopwatch_warning_is_idempotent():
    """Повторный вызов не дублирует предупреждение."""
    task = {"id": "uuid-1", "stopwatch": {"running": True}}
    r1 = normalize_stopwatch_warning(task)
    r2 = normalize_stopwatch_warning(r1)
    notes = r2["_meta"]["notes"]
    stopwatch_notes = [n for n in notes if "stopwatch" in n.lower()]
    assert len(stopwatch_notes) == 1
