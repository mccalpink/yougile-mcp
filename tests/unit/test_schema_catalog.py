from src.utils.schema_catalog import get_entity_schema, get_all_entities


def test_get_entity_schema_task_returns_dict():
    schema = get_entity_schema("task")
    assert isinstance(schema, dict)
    assert "entity" in schema
    assert "fields" in schema


def test_get_entity_schema_task_has_id_field():
    schema = get_entity_schema("task")
    fields = {f["name"]: f for f in schema["fields"]}
    assert "id" in fields
    assert fields["id"]["type"] == "string (UUID)"
    assert "custom" in fields["id"]["in_verbosity"]
    assert "compact" in fields["id"]["in_verbosity"]
    assert "full" in fields["id"]["in_verbosity"]
    assert fields["id"]["include_key"] is None


def test_get_entity_schema_all_nine_entities():
    for entity in ["task", "project", "board", "column", "user",
                   "message", "group_chat", "sticker", "webhook"]:
        schema = get_entity_schema(entity)
        assert schema["entity"] == entity


def test_get_entity_schema_unknown_returns_none():
    assert get_entity_schema("unknown_entity") is None


def test_get_all_entities_returns_nine():
    entities = get_all_entities()
    assert len(entities) == 9


def test_schema_field_has_required_keys():
    schema = get_entity_schema("task")
    for field in schema["fields"]:
        assert "name" in field
        assert "type" in field
        assert "in_verbosity" in field
        assert "include_key" in field
        # notes может быть None, но ключ должен присутствовать
        assert "notes" in field
