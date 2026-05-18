"""Тесты для setup_yougile_skill_impl (manifest-based install).

Дизайн B (см. review-fixes/PLAN.md): тул возвращает манифест с URI ресурсов
и sha256 для verification — никаких файловых операций со стороны MCP.
"""
import hashlib
from pathlib import Path

import pytest

from src.yougile_mcp.resources.skill_template import (
    SKILL_FILES,
    get_skill_file_content,
)
from src.yougile_mcp.tools.meta_tools import setup_yougile_skill_impl


@pytest.mark.asyncio
async def test_setup_returns_manifest_shape():
    result = await setup_yougile_skill_impl()
    assert set(result.keys()) >= {
        "questions",
        "default_target_dir",
        "files",
        "instructions",
    }


@pytest.mark.asyncio
async def test_setup_questions_cover_workspace_and_routing():
    result = await setup_yougile_skill_impl()
    text = " ".join(result["questions"]).lower()
    assert "workspace" in text or "компани" in text
    assert "routing" in text or "правил" in text or "маршрут" in text


@pytest.mark.asyncio
async def test_setup_default_target_in_home():
    result = await setup_yougile_skill_impl()
    assert ".agents/skills/yougile-personal" in result["default_target_dir"]


@pytest.mark.asyncio
async def test_setup_files_match_whitelist():
    result = await setup_yougile_skill_impl()
    targets = {f["target"] for f in result["files"]}
    uris = {f["uri"] for f in result["files"]}

    assert targets == set(SKILL_FILES)
    assert uris == {f"yougile://skill-template/{p}" for p in SKILL_FILES}


@pytest.mark.asyncio
async def test_setup_files_carry_sha256_matching_content():
    result = await setup_yougile_skill_impl()
    for entry in result["files"]:
        expected = hashlib.sha256(
            get_skill_file_content(entry["target"]).encode("utf-8")
        ).hexdigest()
        assert entry["sha256"] == expected, (
            f"sha256 mismatch for {entry['target']}: "
            f"manifest={entry['sha256']}, actual={expected}"
        )


@pytest.mark.asyncio
async def test_setup_does_not_touch_filesystem(tmp_path, monkeypatch):
    """MCP не должен ничего писать на диск — даже если cwd временный."""
    monkeypatch.chdir(tmp_path)
    before = sorted(tmp_path.iterdir())
    await setup_yougile_skill_impl()
    after = sorted(tmp_path.iterdir())
    assert before == after, "setup_yougile_skill_impl modified the filesystem"


@pytest.mark.asyncio
async def test_setup_instructions_mention_verification():
    result = await setup_yougile_skill_impl()
    instr = result["instructions"].lower()
    assert "sha256" in instr
    assert "readmcpresource" in instr or "resource" in instr
