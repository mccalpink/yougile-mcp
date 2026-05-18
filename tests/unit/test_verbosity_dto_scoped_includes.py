"""Spec §1.3 после M7: include[] ключ валиден только для своего DTO.

Раньше apply_includes искал ключ только в глобальном _INCLUDE_KEYS,
не учитывая dto_type — в результате include=['deadline_history'] для
webhook молча не делал ничего (deadline_history привязан к task).
Теперь такой ключ попадает в _meta.unknown_includes.
"""
from src.utils.verbosity import apply_verbosity


def test_other_dto_key_lands_in_unknown_includes():
    """deadline_history привязан к task — для webhook должен быть unknown."""
    raw = {"id": "uuid", "url": "https://example.com/hook", "event": "task.created"}
    result = apply_verbosity(
        raw, "webhook", verbosity="compact", include=["deadline_history"]
    )
    assert "_meta" in result
    assert "deadline_history" in result["_meta"].get("unknown_includes", [])


def test_same_dto_key_resolved_normally():
    """deadline_history для task работает как раньше."""
    raw = {
        "id": "uuid", "title": "x",
        "deadline": {"deadline": 1, "history": ["v1"]},
    }
    result = apply_verbosity(
        raw, "task", verbosity="full", include=["deadline_history"]
    )
    assert result["deadline"]["history"] == ["v1"]


def test_include_all_filters_by_dto_type_for_webhook():
    """include=['all'] для webhook не должен пытаться добавить task-only поля."""
    raw = {"id": "uuid", "url": "https://example.com/hook", "event": "task.created"}
    result = apply_verbosity(
        raw, "webhook", verbosity="full", include=["all"]
    )
    # task-only ключи не появились бы (их нет в source), но и в unknown не должны
    # быть — для webhook они отфильтрованы из 'all' заранее
    unknowns = result.get("_meta", {}).get("unknown_includes", [])
    assert "deadline_history" not in unknowns
    assert "description" not in unknowns
    assert "checklists" not in unknowns


def test_include_all_for_task_keeps_task_keys():
    """include=['all'] для task расширяется в task-specific ключи."""
    raw = {
        "id": "uuid", "title": "x",
        "description": "<p>hi</p>",
        "checklists": [{"items": []}],
    }
    result = apply_verbosity(raw, "task", verbosity="compact", include=["all"])
    # description и checklists подтянулись (это task-only opt-ins)
    assert result.get("description") == "<p>hi</p>"
    assert result.get("checklists") == [{"items": []}]


def test_completely_unknown_key_still_lands_in_unknown_includes():
    """Не-spec, не-source ключ — unknown как и раньше."""
    raw = {"id": "uuid", "title": "x"}
    result = apply_verbosity(
        raw, "task", verbosity="compact", include=["totally_made_up"]
    )
    assert "totally_made_up" in result["_meta"]["unknown_includes"]
