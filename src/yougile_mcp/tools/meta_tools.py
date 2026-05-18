"""Мета-инструменты для интроспекции MCP-сервера YouGile.

Содержит:
- describe_response_impl — логика описания DTO-схем (тестируется напрямую)
- setup_yougile_skill_impl — возвращает манифест для установки персонального скилла
  агентом (MCP сам файлы не пишет — см. design B, review-fixes/PLAN.md)
"""
from __future__ import annotations

from ..resources.skill_template import (
    SKILL_FILES,
    compute_skill_file_sha256,
)
from ...utils.schema_catalog import get_all_entities, get_entity_schema


# ---------------------------------------------------------------------------
# describe_response
# ---------------------------------------------------------------------------


async def describe_response_impl(
    entity: str | None,
    verbosity: str = "compact",
) -> dict:
    """Схема полей для YouGile entity (или обзор всех сущностей).

    Args:
        entity: Имя сущности (task, project, board, column, user,
                message, group_chat, sticker, webhook) или None для обзора.
        verbosity: 'compact' — поля compact-уровня; 'full' — все поля
                   включая opt-in.

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
    """Обзор всех 9 сущностей."""
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
    """Детальное описание одной сущности."""
    all_fields = schema["fields"]

    if verbosity == "compact":
        visible_fields = [
            f for f in all_fields
            if "compact" in f["in_verbosity"] or "custom" in f["in_verbosity"]
        ]
    else:
        visible_fields = [f for f in all_fields if f["in_verbosity"]]

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

_DEFAULT_TARGET_DIR = "~/.agents/skills/yougile-personal/"

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

_INSTRUCTIONS = (
    "Установка скилла полностью на стороне агента — MCP-сервер не пишет на "
    "диск.\n\n"
    "Шаги:\n"
    "1. Для каждого files[i] прочитай содержимое через ReadMcpResource(uri).\n"
    "   Текст приходит дословно — не переформулируй.\n"
    "2. Запиши его в default_target_dir + files[i].target (или другое место, "
    "если пользователь предпочитает).\n"
    "3. После записи каждого файла свернись sha256 содержимого: при "
    "расхождении с files[i].sha256 — перезапиши.\n"
    "4. Задай пользователю questions, заполни briefing.md из шаблона "
    "templates/briefing.template.md и сохрани в target_dir/briefing.md.\n"
    "5. Если briefing.md уже существует в target_dir — спроси у пользователя "
    "перед перезаписью.\n"
    "6. Перед заменой существующего SKILL.md/references/* делай бэкап "
    "(имя.bak.<unix-timestamp>) — только для файлов, которые реально "
    "отличаются от устанавливаемого содержимого."
)


async def setup_yougile_skill_impl() -> dict:
    """Возвращает манифест для установки персонального скилла агентом.

    MCP-сервер сам файлы не пишет (см. design B). Манифест содержит:
    - questions: вопросы пользователю для briefing.md
    - default_target_dir: рекомендуемое место установки
    - files: список (uri, target, sha256) — где uri это MCP resource,
      target — относительный путь записи, sha256 — для verification
    - instructions: пошаговый протокол для агента

    Returns:
        dict с ключами questions, default_target_dir, files, instructions.
    """
    files = [
        {
            "uri": f"yougile://skill-template/{relpath}",
            "target": relpath,
            "sha256": compute_skill_file_sha256(relpath),
        }
        for relpath in SKILL_FILES
    ]

    return {
        "questions": _SETUP_QUESTIONS,
        "default_target_dir": _DEFAULT_TARGET_DIR,
        "files": files,
        "instructions": _INSTRUCTIONS,
    }
