"""MCP resources для шаблона персонального скилла YouGile.

Шаблон выставлен как набор MCP resources под URI вида
`yougile://skill-template/<relative-path>`. Каждый файл — отдельный
ресурс; агент читает их через `resources/read` и записывает к себе
через свой Write-tool. MCP-сервер при этом ничего не пишет на диск
пользователя — никакого path-traversal риска со стороны тула.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


# Корень templates/yougile-personal-skill/ относительно репы MCP.
# parents[3] = корень репы (src/yougile_mcp/resources/skill_template.py).
_TEMPLATE_DIR: Path = (
    Path(__file__).parents[3] / "templates" / "yougile-personal-skill"
).resolve()


# Whitelist файлов скилла, доступных через resources/read.
# README.md из template НЕ публикуется — это документация для разработчика
# MCP, не для пользователя скилла.
SKILL_FILES: tuple[str, ...] = (
    "SKILL.md",
    "references/common-patterns.md",
    "references/custom-filters.md",
    "references/describe-response.md",
    "references/quirks.md",
    "references/tool-keys.md",
    "templates/briefing.template.md",
    "templates/filters.template.md",
)


class SkillFileNotAllowed(ValueError):
    """Запрошен путь, не входящий в whitelist (или path-traversal попытка)."""


def get_skill_file_content(relpath: str) -> str:
    """Содержимое одного файла шаблона по относительному пути.

    Принимает только пути из ``SKILL_FILES``. Любая попытка указать
    другой путь (включая `..`, абсолютные пути или symlink за пределы
    template dir) приводит к ``SkillFileNotAllowed``.

    Args:
        relpath: относительный путь файла в шаблоне, ровно как в SKILL_FILES.

    Returns:
        Содержимое файла как str (UTF-8).
    """
    if relpath not in SKILL_FILES:
        raise SkillFileNotAllowed(
            f"Path '{relpath}' is not in the skill template whitelist. "
            f"Allowed: {list(SKILL_FILES)}"
        )

    resolved = (_TEMPLATE_DIR / relpath).resolve()
    # Двойная защита: даже если whitelist кто-то расширит, путь обязан
    # остаться внутри template dir (защита от symlink escape).
    if not str(resolved).startswith(str(_TEMPLATE_DIR) + "/") and resolved != _TEMPLATE_DIR:
        raise SkillFileNotAllowed(
            f"Resolved path '{resolved}' escapes template dir '{_TEMPLATE_DIR}'"
        )

    return resolved.read_text(encoding="utf-8")


def compute_skill_file_sha256(relpath: str) -> str:
    """SHA-256 содержимого файла шаблона (для verification в manifest)."""
    content = get_skill_file_content(relpath).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def list_skill_files() -> list[str]:
    """Список относительных путей всех публикуемых файлов шаблона."""
    return list(SKILL_FILES)
