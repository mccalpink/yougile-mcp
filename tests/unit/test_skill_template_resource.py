import pytest
from unittest.mock import patch, mock_open


def test_skill_template_resource_returns_string():
    """Resource возвращает строку (содержимое SKILL.md)."""
    from src.yougile_mcp.resources.skill_template import get_skill_template_content
    # Мокируем файл, так как реальный SKILL.md создаётся в Phase VI
    mock_content = "# YouGile Personal Skill\n## placeholder"
    with patch("builtins.open", mock_open(read_data=mock_content)):
        result = get_skill_template_content()
    assert isinstance(result, str)
    assert len(result) > 0


def test_skill_template_resource_returns_markdown():
    """Содержимое начинается с markdown-заголовка."""
    from src.yougile_mcp.resources.skill_template import get_skill_template_content
    mock_content = "# YouGile Personal Skill\n## placeholder"
    with patch("builtins.open", mock_open(read_data=mock_content)):
        result = get_skill_template_content()
    assert result.startswith("#")


def test_skill_template_resource_file_not_found_returns_error():
    """Если файл не найден — возвращает описательную ошибку, не падает."""
    from src.yougile_mcp.resources.skill_template import get_skill_template_content
    with patch("builtins.open", side_effect=FileNotFoundError("No such file")):
        result = get_skill_template_content()
    assert "not found" in result.lower() or "error" in result.lower()
