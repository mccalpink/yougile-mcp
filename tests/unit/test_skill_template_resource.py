"""Тесты для skill_template MCP-ресурса.

Дизайн B (см. review-fixes/PLAN.md): MCP отдаёт файлы шаблона как resources
через whitelist; никаких записей на диск, никакого path traversal.
"""
import hashlib
from pathlib import Path

import pytest

from src.yougile_mcp.resources.skill_template import (
    SKILL_FILES,
    SkillFileNotAllowed,
    compute_skill_file_sha256,
    get_skill_file_content,
    list_skill_files,
)


def test_list_skill_files_returns_whitelist():
    files = list_skill_files()
    assert isinstance(files, list)
    assert "SKILL.md" in files
    assert "references/tool-keys.md" in files
    assert "templates/briefing.template.md" in files


def test_skill_files_whitelist_matches_template_dir():
    """SKILL_FILES совпадает с физическим состоянием template dir.

    Защита от расхождения: добавили файл в template — забыли в whitelist.
    """
    template_dir = (
        Path(__file__).parents[2] / "templates" / "yougile-personal-skill"
    ).resolve()
    actual_files = {
        str(p.relative_to(template_dir))
        for p in template_dir.rglob("*.md")
        # README.md из template для разработчика, не публикуется
        if p.name != "README.md"
    }
    assert actual_files == set(SKILL_FILES), (
        f"Whitelist расходится с template dir. "
        f"В файлах: {actual_files - set(SKILL_FILES)}, "
        f"в whitelist: {set(SKILL_FILES) - actual_files}"
    )


def test_get_skill_file_content_returns_real_content():
    content = get_skill_file_content("SKILL.md")
    assert isinstance(content, str)
    assert len(content) > 0
    assert content.startswith("#") or "yougile" in content.lower()


def test_get_skill_file_content_all_whitelist_readable():
    """Каждый файл из whitelist реально читается."""
    for relpath in SKILL_FILES:
        content = get_skill_file_content(relpath)
        assert isinstance(content, str)
        assert len(content) > 0, f"Empty content for {relpath}"


def test_get_skill_file_content_rejects_path_traversal():
    with pytest.raises(SkillFileNotAllowed):
        get_skill_file_content("../../etc/passwd")


def test_get_skill_file_content_rejects_absolute_path():
    with pytest.raises(SkillFileNotAllowed):
        get_skill_file_content("/etc/passwd")


def test_get_skill_file_content_rejects_unknown_relative():
    with pytest.raises(SkillFileNotAllowed):
        get_skill_file_content("nonexistent.md")


def test_get_skill_file_content_rejects_dotdot_inside():
    with pytest.raises(SkillFileNotAllowed):
        get_skill_file_content("references/../../etc/passwd")


def test_compute_skill_file_sha256_matches_manual():
    expected = hashlib.sha256(
        get_skill_file_content("SKILL.md").encode("utf-8")
    ).hexdigest()
    assert compute_skill_file_sha256("SKILL.md") == expected


def test_compute_skill_file_sha256_rejects_unknown_path():
    with pytest.raises(SkillFileNotAllowed):
        compute_skill_file_sha256("nonexistent.md")
