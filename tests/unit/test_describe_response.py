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
