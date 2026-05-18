"""M9: falsy bool поля (deleted/archived/completed) дропаются молча
из compact-ответа — НЕ попадают в _meta.omitted_fields.

Раньше каждая задача без флагов выдавала
_meta.omitted_fields = ['deleted', 'archived', 'completed', ...],
что засоряло envelope и вводило агента в заблуждение про "скрытые
полезные данные". На самом деле отсутствие = false.
"""
from src.utils.verbosity import apply_verbosity


def test_compact_task_drops_falsy_booleans_silently():
    raw = {
        "id": "uuid",
        "title": "x",
        "columnId": "col",
        "deleted": False,
        "archived": False,
        "completed": False,
    }
    result = apply_verbosity(raw, "task", verbosity="compact")
    omitted = result.get("_meta", {}).get("omitted_fields", [])
    assert "deleted" not in omitted
    assert "archived" not in omitted
    assert "completed" not in omitted
    # Сами поля тоже не должны вернуться
    assert "deleted" not in result
    assert "archived" not in result
    assert "completed" not in result


def test_compact_task_keeps_completed_when_true():
    raw = {
        "id": "uuid",
        "title": "x",
        "columnId": "col",
        "completed": True,
    }
    result = apply_verbosity(raw, "task", verbosity="compact")
    assert result.get("completed") is True


def test_compact_task_keeps_deleted_when_true():
    raw = {
        "id": "uuid",
        "title": "x",
        "columnId": "col",
        "deleted": True,
    }
    result = apply_verbosity(raw, "task", verbosity="compact")
    assert result.get("deleted") is True


def test_compact_project_drops_deleted_false_silently():
    raw = {"id": "uuid", "title": "p", "deleted": False}
    result = apply_verbosity(raw, "project", verbosity="compact")
    omitted = result.get("_meta", {}).get("omitted_fields", [])
    assert "deleted" not in omitted
    assert "deleted" not in result


def test_compact_keeps_other_real_omits_visible():
    """Регресс: дроп реально полезных полей (типа timestamps) всё ещё
    попадает в omitted_fields — мы убрали шум, а не сигнал."""
    raw = {
        "id": "uuid",
        "title": "x",
        "columnId": "col",
        "timestamp": 1_700_000_000_000,
        "createdBy": "user-uuid",
        "deleted": False,
    }
    result = apply_verbosity(raw, "task", verbosity="compact")
    omitted = result.get("_meta", {}).get("omitted_fields", [])
    assert "timestamp" in omitted
    assert "createdBy" in omitted
    assert "deleted" not in omitted  # тихо дропнут
