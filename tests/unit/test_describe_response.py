import pytest
from unittest.mock import AsyncMock, MagicMock

# Тестируем логику напрямую, без MCP-протокола
from src.yougile_mcp.tools.meta_tools import describe_response_impl


@pytest.mark.asyncio
async def test_describe_response_no_entity_returns_overview():
    result = await describe_response_impl(entity=None, verbosity="compact")
    assert "entities" in result
    assert "task" in result["entities"]
    assert "project" in result["entities"]
    assert len(result["entities"]) == 9
    assert "note" in result


@pytest.mark.asyncio
async def test_describe_response_overview_has_compact_fields_count():
    result = await describe_response_impl(entity=None, verbosity="compact")
    task_info = result["entities"]["task"]
    assert "compact_fields" in task_info
    assert isinstance(task_info["compact_fields"], int)
    assert task_info["compact_fields"] > 0


@pytest.mark.asyncio
async def test_describe_response_overview_has_optins():
    result = await describe_response_impl(entity=None, verbosity="compact")
    task_info = result["entities"]["task"]
    assert "optins" in task_info
    assert "description" in task_info["optins"]
    assert "checklists" in task_info["optins"]


@pytest.mark.asyncio
async def test_describe_response_with_entity_task_returns_fields():
    result = await describe_response_impl(entity="task", verbosity="compact")
    assert result["entity"] == "task"
    assert "verbosity_applied" in result
    assert "fields" in result
    field_names = [f["name"] for f in result["fields"]]
    assert "id" in field_names
    assert "title" in field_names


@pytest.mark.asyncio
async def test_describe_response_task_has_quirks():
    result = await describe_response_impl(entity="task", verbosity="compact")
    assert "quirks" in result
    assert len(result["quirks"]) > 0


@pytest.mark.asyncio
async def test_describe_response_task_has_hints_in_compact():
    result = await describe_response_impl(entity="task", verbosity="compact")
    assert "hints_in_compact" in result
    assert "has_description" in result["hints_in_compact"]


@pytest.mark.asyncio
async def test_describe_response_unknown_entity_returns_error():
    result = await describe_response_impl(entity="unicorn", verbosity="compact")
    assert "error" in result
    assert "available_entities" in result


@pytest.mark.asyncio
async def test_describe_response_entity_case_insensitive():
    result_lower = await describe_response_impl(entity="task", verbosity="compact")
    result_upper = await describe_response_impl(entity="Task", verbosity="compact")
    assert result_lower["entity"] == result_upper["entity"]


@pytest.mark.asyncio
async def test_describe_response_full_verbosity_shows_optin_fields():
    result = await describe_response_impl(entity="task", verbosity="full")
    field_names = [f["name"] for f in result["fields"]]
    # При full verbosity включаем opt-in поля
    assert "description" in field_names
    assert "checklists" in field_names


@pytest.mark.asyncio
@pytest.mark.parametrize("entity,expected_compact_fields,expected_optins", [
    ("task",        ["id", "title", "columnId", "createdAt"],
                    ["description", "checklists", "stickers", "stopwatch", "timer",
                     "time_tracking", "deal", "extension_data", "deadline_history", "timestamps"]),
    ("project",     ["id", "title", "createdAt"],
                    ["timestamps"]),
    ("board",       ["id", "name", "projectId"],
                    []),
    ("column",      ["id", "title", "boardId"],
                    []),
    ("user",        ["id", "email", "realName", "status"],
                    []),
    ("message",     ["id", "text", "chatId", "userId"],
                    []),
    ("group_chat",  ["id", "name", "users"],
                    ["chat_maps"]),
    ("sticker",     ["id", "name", "type"],
                    ["sprint_states", "string_states"]),
    ("webhook",     ["id", "url", "events", "filters"],
                    []),
])
async def test_describe_response_entity_compact_fields(
    entity, expected_compact_fields, expected_optins
):
    result = await describe_response_impl(entity=entity, verbosity="compact")
    assert result["entity"] == entity
    field_names = [f["name"] for f in result["fields"]]
    for expected in expected_compact_fields:
        assert expected in field_names, f"Missing field '{expected}' in {entity} compact schema"
    # Проверяем include_key через schema_catalog напрямую
    from src.utils.schema_catalog import get_entity_schema
    schema = get_entity_schema(entity)
    actual_optins = {f["include_key"] for f in schema["fields"] if f["include_key"]}
    for opt in expected_optins:
        assert opt in actual_optins, f"Missing optin '{opt}' in {entity} schema"


@pytest.mark.asyncio
async def test_describe_response_task_field_has_include_key():
    result = await describe_response_impl(entity="task", verbosity="full")
    fields = {f["name"]: f for f in result["fields"]}
    assert fields["description"]["include_key"] == "description"
    assert fields["checklists"]["include_key"] == "checklists"
    assert fields["timestamp"]["include_key"] == "timestamps"
    assert fields["id"]["include_key"] is None


@pytest.mark.asyncio
async def test_describe_response_task_notes_not_empty_for_special_fields():
    result = await describe_response_impl(entity="task", verbosity="full")
    fields = {f["name"]: f for f in result["fields"]}
    # description имеет важную заметку о context-sensitive поведении
    assert fields["description"]["notes"] is not None
    assert len(fields["description"]["notes"]) > 0
