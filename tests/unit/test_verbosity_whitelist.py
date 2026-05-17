import pytest
from src.utils.verbosity import apply_verbosity


# --- Task ---

FULL_TASK = {
    "id": "t1", "title": "T", "columnId": "col1", "type": "task",
    "completed": False, "archived": False, "deleted": False,
    "assigned": ["u1"], "subtasks": [], "stickers": {}, "checklists": [],
    "color": None, "description": "<p>Desc</p>",
    "timeTracking": None, "stopwatch": None, "timer": None, "deal": None,
    "deadline": {"deadline": 1748217600000, "history": [], "blockedPoints": [], "links": []},
    "timestamp": 1747483200000, "archivedTimestamp": None, "completedTimestamp": None,
    "createdBy": "u-creator", "idTaskCommon": "ID-1", "idTaskProject": "DEV-1",
    "extensionData": {},
}


def test_task_compact_always_fields():
    """compact task: id, title, columnId, createdAt всегда присутствуют."""
    result = apply_verbosity(FULL_TASK, dto_type="task", verbosity="compact")
    assert result.get("id") == "t1"
    assert result.get("title") == "T"
    assert result.get("columnId") == "col1"
    assert "createdAt" in result


def test_task_compact_drops_always():
    """compact task: type, createdBy, idTaskCommon, idTaskProject, extensionData дропаются всегда."""
    result = apply_verbosity(FULL_TASK, dto_type="task", verbosity="compact")
    for field in ("type", "createdBy", "idTaskCommon", "idTaskProject", "extensionData"):
        assert field not in result, f"Поле '{field}' должно быть дропнуто"


def test_task_compact_drops_raw_timestamps():
    """compact task: raw timestamp/archivedTimestamp/completedTimestamp дропаются."""
    result = apply_verbosity(FULL_TASK, dto_type="task", verbosity="compact")
    for field in ("timestamp", "archivedTimestamp", "completedTimestamp"):
        assert field not in result


def test_task_compact_description_dropped_in_list():
    """compact list_*: description дропается (в list_* режиме) даже если непустой."""
    data = {"paging": {"totalCount": 1, "offset": 0, "limit": 20}, "content": [FULL_TASK]}
    result = apply_verbosity(data, dto_type="task", verbosity="compact", is_list=True)
    assert "description" not in result["content"][0]


def test_task_compact_deadline_history_dropped():
    """compact task: deadline.history дропается."""
    result = apply_verbosity(FULL_TASK, dto_type="task", verbosity="compact")
    deadline = result.get("deadline", {})
    assert "history" not in deadline


def test_task_compact_include_checklists():
    """include=['checklists'] при compact добавляет checklists к ответу."""
    task_with_cl = {**FULL_TASK, "checklists": [{"id": "cl1", "items": []}]}
    result = apply_verbosity(task_with_cl, dto_type="task", verbosity="compact", include=["checklists"])
    assert "checklists" in result


# --- Project ---

FULL_PROJECT = {"id": "p1", "title": "Проект", "deleted": False, "timestamp": 1747483200000, "users": {"u1": "admin"}}


def test_project_compact_always_fields():
    """compact project: id, title, createdAt присутствуют."""
    result = apply_verbosity(FULL_PROJECT, dto_type="project", verbosity="compact")
    assert result["id"] == "p1"
    assert result["title"] == "Проект"
    assert "createdAt" in result


def test_project_compact_drops():
    """compact project: users и timestamp (raw) дропаются."""
    result = apply_verbosity(FULL_PROJECT, dto_type="project", verbosity="compact")
    assert "users" not in result
    assert "timestamp" not in result


# --- User ---

FULL_USER = {"id": "u1", "email": "u@example.com", "realName": "Иван", "status": "online", "lastActivity": 1747483200000}


def test_user_compact_includes_status():
    """compact user: status присутствует (добавлен по spec §2)."""
    result = apply_verbosity(FULL_USER, dto_type="user", verbosity="compact")
    assert result.get("status") == "online"


def test_user_compact_drops_last_activity():
    """compact user: lastActivity дропается."""
    result = apply_verbosity(FULL_USER, dto_type="user", verbosity="compact")
    assert "lastActivity" not in result


# --- Sticker ---

FULL_STICKER = {"id": "s1", "name": "Priority", "type": "string", "deleted": False, "states": [{"id": "st1", "value": "High"}]}


def test_sticker_compact_drops_states():
    """compact sticker: states дропаются (opt-in через include=['sprint_states'/'string_states'])."""
    result = apply_verbosity(FULL_STICKER, dto_type="sticker", verbosity="compact")
    assert "states" not in result


def test_sticker_compact_always_fields():
    """compact sticker: id, name, type присутствуют."""
    result = apply_verbosity(FULL_STICKER, dto_type="sticker", verbosity="compact")
    assert result["id"] == "s1"
    assert result["name"] == "Priority"
    assert result["type"] == "string"
