import shutil
import tempfile
from pathlib import Path

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
async def test_setup_skill_custom_memory_dir(tmp_path):
    """Кастомный memory_dir используется как target_path."""
    custom_path = str(tmp_path / "custom")
    result = await setup_yougile_skill_impl(memory_dir=custom_path)
    assert result["target_path"].startswith(custom_path)
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


# ---------------------------------------------------------------------------
# Новые тесты: копирование references/ и templates/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_copies_references_to_memory_dir():
    """setup_yougile_skill копирует references/ из template в memory_dir."""
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp) / "skill"
        result = await setup_yougile_skill_impl(memory_dir=str(memory))

        ref_dir = memory / "references"
        assert ref_dir.exists(), f"references/ должна быть создана в {memory}"
        assert (ref_dir / "tool-keys.md").exists()
        assert (ref_dir / "describe-response.md").exists()
        assert (ref_dir / "common-patterns.md").exists()
        assert (ref_dir / "custom-filters.md").exists()
        assert (ref_dir / "quirks.md").exists()

        assert "references_installed" in result
        assert len(result["references_installed"]) == 5


@pytest.mark.asyncio
async def test_setup_copies_templates_to_memory_dir():
    """setup_yougile_skill копирует templates/ из template в memory_dir."""
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp) / "skill"
        result = await setup_yougile_skill_impl(memory_dir=str(memory))

        tpl_dir = memory / "templates"
        assert tpl_dir.exists()
        assert (tpl_dir / "briefing.template.md").exists()
        assert (tpl_dir / "filters.template.md").exists()

        assert "templates_installed" in result
        assert len(result["templates_installed"]) == 2


@pytest.mark.asyncio
async def test_setup_idempotent_skip_unchanged():
    """Повторный вызов с тем же контентом — skip, не падает."""
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp) / "skill"
        r1 = await setup_yougile_skill_impl(memory_dir=str(memory))
        r2 = await setup_yougile_skill_impl(memory_dir=str(memory))
        # Оба должны работать без ошибки, файлы те же
        assert r2["references_installed"] == r1["references_installed"]


@pytest.mark.asyncio
async def test_setup_does_not_touch_existing_skill_md():
    """Если SKILL.md уже есть в memory_dir — не трогаем."""
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp) / "skill"
        memory.mkdir(parents=True)
        custom_skill = memory / "SKILL.md"
        custom_skill.write_text("# My custom SKILL — DO NOT TOUCH")

        await setup_yougile_skill_impl(memory_dir=str(memory))

        # SKILL.md остался нетронутым
        assert custom_skill.read_text() == "# My custom SKILL — DO NOT TOUCH"


@pytest.mark.asyncio
async def test_setup_returns_questions_still():
    """Backward compat: setup всё ещё возвращает questions для интерактивного wizard."""
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp) / "skill"
        result = await setup_yougile_skill_impl(memory_dir=str(memory))

        assert "questions" in result
        assert "target_path" in result
        assert len(result["questions"]) >= 5  # хотя бы базовые
