"""M6: schema_catalog должен описывать поля, реально присутствующие в
verbosity='full' pass-through. Раньше createdBy/idTaskCommon/idTaskProject
(и аналогичные у других entities) помечались _NONE — скрывались из
describe_response(verbosity='full'), но в реальном full-ответе оставались.
Агент видел расхождение doc vs runtime.
"""
from src.utils.schema_catalog import get_entity_schema


def test_task_full_includes_legacy_ids():
    schema = get_entity_schema("task")
    field_names = {f["name"] for f in schema["fields"] if "full" in f["in_verbosity"]}
    assert "createdBy" in field_names
    assert "idTaskCommon" in field_names
    assert "idTaskProject" in field_names


def test_user_full_includes_lastActivity():
    schema = get_entity_schema("user")
    field_names = {f["name"] for f in schema["fields"] if "full" in f["in_verbosity"]}
    assert "lastActivity" in field_names


def test_message_full_includes_textHtml_and_editTimestamp():
    schema = get_entity_schema("message")
    field_names = {f["name"] for f in schema["fields"] if "full" in f["in_verbosity"]}
    assert "textHtml" in field_names
    assert "editTimestamp" in field_names


def test_webhook_full_includes_monitoring_fields():
    schema = get_entity_schema("webhook")
    field_names = {f["name"] for f in schema["fields"] if "full" in f["in_verbosity"]}
    assert "lastSuccess" in field_names
    assert "failuresSinceLastSuccess" in field_names


def test_sticker_full_includes_pagination_artifacts():
    schema = get_entity_schema("sticker")
    field_names = {f["name"] for f in schema["fields"] if "full" in f["in_verbosity"]}
    assert "limit" in field_names
    assert "offset" in field_names
