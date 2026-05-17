"""
Мета-инструменты для интроспекции MCP-сервера YouGile.

Содержит:
- describe_response_impl — логика описания DTO-схем (тестируется напрямую)
- setup_yougile_skill_impl — логика настройки персонального скилла
"""
from __future__ import annotations

import os
from pathlib import Path

from ...utils.schema_catalog import get_entity_schema, get_all_entities


# ---------------------------------------------------------------------------
# describe_response
# ---------------------------------------------------------------------------


async def describe_response_impl(
    entity: str | None,
    verbosity: str = "compact",
) -> dict:
    """
    Возвращает схему полей для указанной YouGile entity или обзор всех сущностей.

    Args:
        entity: Имя сущности (task, project, board, column, user,
                message, group_chat, sticker, webhook) или None для обзора.
        verbosity: 'compact' — только поля compact-уровня;
                   'full' — все поля включая opt-in.

    Returns:
        Словарь с описанием схемы.
    """
    if entity is None:
        return _describe_overview(verbosity)

    normalized = entity.strip().lower()
    schema = get_entity_schema(normalized)

    if schema is None:
        return {
            "error": f"Unknown entity '{entity}'",
            "available_entities": get_all_entities(),
        }

    return _describe_entity(schema, verbosity)


def _describe_overview(verbosity: str) -> dict:
    """Возвращает обзор всех 9 сущностей."""
    entities = {}
    for name in get_all_entities():
        schema = get_entity_schema(name)
        compact_fields = sum(
            1 for f in schema["fields"]
            if "compact" in f["in_verbosity"] or "custom" in f["in_verbosity"]
        )
        entities[name] = {
            "compact_fields": compact_fields,
            "optins": schema.get("optins", []),
        }

    return {
        "entities": entities,
        "note": "Call describe_response(entity='task') for detailed field-level schema.",
    }


def _describe_entity(schema: dict, verbosity: str) -> dict:
    """Возвращает детальное описание одной сущности."""
    all_fields = schema["fields"]

    if verbosity == "compact":
        # Показываем только поля, присутствующие в compact или custom
        visible_fields = [
            f for f in all_fields
            if "compact" in f["in_verbosity"] or "custom" in f["in_verbosity"]
        ]
    else:
        # full — показываем все поля кроме тех, у кого in_verbosity == []
        visible_fields = [
            f for f in all_fields
            if f["in_verbosity"]  # скрываем поля с пустым in_verbosity (всегда dropped)
        ]

    return {
        "entity": schema["entity"],
        "verbosity_applied": verbosity,
        "fields": visible_fields,
        "quirks": schema.get("quirks", []),
        "hints_in_compact": schema.get("hints_in_compact", []),
        "optins": schema.get("optins", []),
    }


# ---------------------------------------------------------------------------
# setup_yougile_skill
# ---------------------------------------------------------------------------

_DEFAULT_MEMORY_DIR = Path.home() / ".agents" / "skills" / "yougile-personal"
_BRIEFING_FILENAME = "briefing.md"

_SETUP_QUESTIONS = [
    "1. Какие YouGile-компании (воркспейсы) вы используете? "
    "Для каждой: slug (короткое имя латиницей) и человекочитаемое название. "
    "Пример: main / Личная компания, team / Стартап X",

    "2. Какой воркспейс использовать по умолчанию (когда явно не указан)?",

    "3. Назовите 3-5 главных проектов в каждом воркспейсе. "
    "Я запрошу их UUID через list_projects автоматически.",

    "4. Routing rules: при каких словах или фразах переключаться на конкретный воркспейс? "
    "Пример: 'клиент ACME' → client_acme, 'в команде' → team. "
    "Без routing agent будет переспрашивать воркспейс на каждый запрос.",

    "5. Стандартные колонки на ваших досках? "
    "Пример: Backlog / In Progress / Done. "
    "Или у каждой доски свои — тогда скажите, и я запрошу отдельно.",

    "6. Чего никогда не делать автоматически (anti-patterns)? "
    "Пример: не перемещать задачи без подтверждения, не писать в чат без просьбы.",
]


async def setup_yougile_skill_impl(
    memory_dir: str | None = None,
) -> dict:
    """
    Возвращает список вопросов и параметры для создания персонализированного briefing.md.

    Не выполняет интерактивную логику — это делает агент (Claude).
    Тул только описывает что нужно сделать и где сохранять.

    Args:
        memory_dir: Путь для сохранения briefing.md.
                    По умолчанию: ~/.agents/skills/yougile-personal/

    Returns:
        dict с ключами: questions, target_path, template_path, existing_briefing, instructions.
    """
    target_dir = Path(memory_dir) if memory_dir else _DEFAULT_MEMORY_DIR
    target_path = target_dir / _BRIEFING_FILENAME

    existing = target_path.exists() and target_path.stat().st_size > 0

    template_path = (
        Path(__file__).parents[4] / "templates" / "yougile-personal-skill" / "briefing.template.md"
    )

    return {
        "questions": _SETUP_QUESTIONS,
        "target_path": str(target_path),
        "template_path": str(template_path),
        "existing_briefing": existing,
        "instructions": (
            "Ask the user these questions one by one (or all at once). "
            "Then call list_projects for each workspace to resolve project UUIDs. "
            "Save the completed briefing.md to target_path. "
            "If existing_briefing is True — ask user: 'Back up and overwrite?' before saving."
        ),
    }
