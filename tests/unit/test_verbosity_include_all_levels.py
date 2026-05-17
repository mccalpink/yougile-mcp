"""Spec §1.3: include[] должен работать с любым уровнем verbosity."""
from src.utils.verbosity import apply_verbosity


def test_include_description_at_compact_list_paging():
    """include=['description'] возвращает description в compact list (paging envelope)."""
    raw = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [{
            "id": "uuid", "title": "x", "description": "<p>html</p>",
            "columnId": "col", "completed": False
        }]
    }
    result = apply_verbosity(raw, "task", verbosity="compact", include=["description"], is_list=True)
    assert "description" in result["content"][0], \
        f"description должна быть, got keys: {list(result['content'][0].keys())}"
    assert result["content"][0]["description"] == "<p>html</p>"


def test_include_description_at_compact_single():
    """include=['description'] возвращает description в compact get_*."""
    raw = {"id": "uuid", "title": "x", "description": "<p>html</p>", "columnId": "col"}
    result = apply_verbosity(raw, "task", verbosity="compact", include=["description"])
    assert "description" in result
    assert result["description"] == "<p>html</p>"


def test_include_deadline_history_at_full():
    """include=['deadline_history'] возвращает deadline.history в full."""
    raw = {
        "id": "uuid", "title": "x",
        "deadline": {"deadline": 1748217600000, "history": ["edit-1", "edit-2"]}
    }
    result = apply_verbosity(raw, "task", verbosity="full", include=["deadline_history"])
    # full дропает opt-in поля, но include должен их вернуть
    assert "history" in result.get("deadline", {}), \
        f"deadline.history должна вернуться. got deadline: {result.get('deadline')}"
    assert result["deadline"]["history"] == ["edit-1", "edit-2"]


def test_include_unknown_at_compact_paging():
    """Unknown include ключ → _meta.unknown_includes на root paging."""
    raw = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [{"id": "uuid", "title": "x", "columnId": "col"}]
    }
    result = apply_verbosity(raw, "task", verbosity="compact", include=["foo_bar"], is_list=True)
    assert "_meta" in result
    assert "unknown_includes" in result["_meta"]
    assert "foo_bar" in result["_meta"]["unknown_includes"]


def test_include_unknown_at_compact_single():
    """Unknown include ключ → _meta.unknown_includes для single dict."""
    raw = {"id": "uuid", "title": "x", "columnId": "col"}
    result = apply_verbosity(raw, "task", verbosity="compact", include=["foo_bar"])
    assert "_meta" in result
    assert "unknown_includes" in result["_meta"]


def test_include_all_at_compact():
    """include=['all'] добавляет все opt-in поля в compact."""
    raw = {
        "id": "uuid", "title": "x", "columnId": "col",
        "description": "<p>desc</p>",
        "checklists": [{"name": "step", "items": []}],
        "extensionData": {"key": "val"},
    }
    result = apply_verbosity(raw, "task", verbosity="compact", include=["all"])
    assert "description" in result
    assert "checklists" in result
    assert "extensionData" in result


def test_include_idempotent_at_compact():
    """include для поля, которое уже в compact — no-op, без ошибки."""
    raw = {"id": "uuid", "title": "x", "columnId": "col"}
    result = apply_verbosity(raw, "task", verbosity="compact", include=["title"])
    assert result["id"] == "uuid"
    assert result["title"] == "x"
    # _meta.unknown_includes не должен содержать 'title' (это валидное поле, idempotent)
    if "_meta" in result and "unknown_includes" in result.get("_meta", {}):
        assert "title" not in result["_meta"]["unknown_includes"]


def test_bare_list_uses_is_list_flag():
    """Bare list path передаёт is_list=True в compactor (description дропается)."""
    raw = [
        {"id": "u1", "title": "t1", "description": "html", "columnId": "c"},
        {"id": "u2", "title": "t2", "description": "html2", "columnId": "c"}
    ]
    result = apply_verbosity(raw, "task", verbosity="compact", is_list=True)
    # result — list. Description должен быть дропнут (is_list уважается).
    assert isinstance(result, list)
    for item in result:
        assert "description" not in item, f"description должна быть дропнута: {item}"


def test_meta_verbosity_always_compact_paging():
    """Spec §1.7: _meta.verbosity присутствует всегда."""
    raw = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [{"id": "x", "title": "y", "columnId": "c"}]  # минимум — ничего не дропается
    }
    result = apply_verbosity(raw, "task", verbosity="compact", is_list=True)
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "compact"


def test_meta_verbosity_always_compact_single():
    raw = {"id": "x", "title": "y", "columnId": "c"}
    result = apply_verbosity(raw, "task", verbosity="compact")
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "compact"


def test_meta_verbosity_always_custom_single():
    raw = {"id": "x", "title": "y"}
    result = apply_verbosity(raw, "task", verbosity="custom")
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "custom"


def test_meta_no_for_full():
    """В full _meta может отсутствовать (full = pass-through)."""
    raw = {"id": "x", "title": "y", "description": "html", "timestamp": 1748217600000}
    result = apply_verbosity(raw, "task", verbosity="full")
    # full без include — pass-through, _meta опционален
    # (не assert'им — допустимо и True и False; вопрос дизайна)
