import pytest
from src.yougile_mcp.tools.meta_tools import setup_yougile_skill_impl


@pytest.mark.asyncio
async def test_setup_skill_returns_questions():
    """Тул возвращает список вопросов для агента."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    assert "questions" in result
    assert isinstance(result["questions"], list)
    assert len(result["questions"]) >= 5  # min 5 вопросов


@pytest.mark.asyncio
async def test_setup_skill_returns_target_path():
    """Тул возвращает путь куда сохранять briefing.md."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    assert "target_path" in result
    assert "briefing.md" in result["target_path"]


@pytest.mark.asyncio
async def test_setup_skill_default_path_in_home():
    """По умолчанию путь в ~/.agents/skills/yougile-personal/."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    assert ".agents/skills/yougile-personal" in result["target_path"]


@pytest.mark.asyncio
async def test_setup_skill_custom_memory_dir():
    """Кастомный memory_dir используется как target_path."""
    result = await setup_yougile_skill_impl(memory_dir="/custom/path")
    assert result["target_path"].startswith("/custom/path")
    assert "briefing.md" in result["target_path"]


@pytest.mark.asyncio
async def test_setup_skill_questions_cover_workspaces():
    """Вопросы включают тему workspace'ов."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    questions_text = " ".join(result["questions"]).lower()
    assert "workspace" in questions_text or "компани" in questions_text


@pytest.mark.asyncio
async def test_setup_skill_questions_cover_routing():
    """Вопросы включают тему routing rules."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    questions_text = " ".join(result["questions"]).lower()
    assert "routing" in questions_text or "правил" in questions_text or "маршрут" in questions_text


@pytest.mark.asyncio
async def test_setup_skill_returns_template_path():
    """Тул сообщает где шаблон briefing.template.md."""
    result = await setup_yougile_skill_impl(memory_dir=None)
    assert "template_path" in result or "template" in str(result)


@pytest.mark.asyncio
async def test_setup_skill_detects_existing_briefing(tmp_path):
    """Если briefing.md уже существует — сообщает об этом."""
    briefing = tmp_path / "briefing.md"
    briefing.write_text("# existing briefing")
    result = await setup_yougile_skill_impl(memory_dir=str(tmp_path))
    assert result.get("existing_briefing") is True or "existing" in str(result)
