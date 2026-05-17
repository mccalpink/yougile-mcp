"""
Статичный каталог DTO-схем для YouGile MCP.

Используется инструментом describe_response для объяснения агенту
состав полей в ответах, уровни verbosity и include-ключи для opt-in полей.

Источник: spec §2 (compact whitelist per DTO) и dto_map/_ANALYSIS.md.
"""

from __future__ import annotations


def _f(
    name: str,
    type_: str,
    in_verbosity: list[str],
    include_key: str | None = None,
    notes: str | None = None,
) -> dict:
    """Вспомогательный конструктор поля схемы."""
    return {
        "name": name,
        "type": type_,
        "in_verbosity": in_verbosity,
        "include_key": include_key,
        "notes": notes,
    }


_ALL = ["custom", "compact", "full"]
_CF = ["compact", "full"]
_F = ["full"]
_NONE: list[str] = []


_SCHEMA: dict[str, dict] = {
    "task": {
        "entity": "task",
        "fields": [
            _f("id",                  "string (UUID)",       _ALL,  None,               "Primary key. Always present."),
            _f("title",               "string",              _CF,   None,               "Task name."),
            _f("columnId",            "string (UUID)",       _CF,   None,               "Current column (board position)."),
            _f("completed",           "boolean",             _CF,   None,               "Included in compact if non-null."),
            _f("archived",            "boolean",             _CF,   None,               "Included in compact if non-null."),
            _f("deleted",             "boolean",             _CF,   None,               "Included in compact only if true."),
            _f("assigned",            "array[UUID]",         _CF,   None,               "List of assignee UUIDs."),
            _f("subtasks",            "array[UUID]",         _CF,   None,               "Included in compact if non-empty."),
            _f("color",               "string (enum)",       _CF,   None,               "Included in compact if non-null."),
            _f("deadline.deadline",   "integer (ms epoch)",  _CF,   None,               "Only the timestamp, not history."),
            _f("createdAt",           "string (ISO-8601)",   _CF,   None,               "Derived from timestamp ms in compact."),
            _f("completedAt",         "string (ISO-8601)",   _CF,   None,               "Included if completedTimestamp non-null."),
            _f("archivedAt",          "string (ISO-8601)",   _CF,   None,               "Included if archivedTimestamp non-null."),
            _f("_hints",              "object",              ["compact"], None,          "list_* only. Has_description, has_checklists, etc."),
            _f("description",         "string (HTML)",       _F,    "description",      "Dropped in list_* compact. See in_verbosity_context."),
            _f("checklists",          "array[CheckList]",    _F,    "checklists",       "Unbounded nested array."),
            _f("stickers",            "object (map)",        _F,    "stickers",         "Map stickerID→stateID. Grows with custom stickers."),
            _f("extensionData",       "object",              _F,    "extension_data",   "Arbitrary blob; size unpredictable."),
            _f("stopwatch",           "object",              _F,    "stopwatch",        "Field name mismatch vs OpenAPI — see quirks."),
            _f("timer",               "object",              _F,    "timer",            "Timer object."),
            _f("timeTracking",        "object",              _F,    "time_tracking",    "Time tracking data."),
            _f("deal",                "object",              _F,    "deal",             "CRM only: sum, contacts, customFields."),
            _f("deadline.history",    "array",               _F,    "deadline_history", "Audit trail; format not described in OpenAPI."),
            _f("timestamp",           "integer (ms epoch)",  _F,    "timestamps",       "Raw creation timestamp. Use createdAt instead."),
            _f("archivedTimestamp",   "integer (ms epoch)",  _F,    "timestamps",       "Raw archived timestamp."),
            _f("completedTimestamp",  "integer (ms epoch)",  _F,    "timestamps",       "Raw completed timestamp."),
            _f("createdBy",           "string (UUID)",       _NONE, None,               "Always dropped."),
            _f("idTaskCommon",        "string",              _NONE, None,               "Always dropped."),
            _f("idTaskProject",       "string",              _NONE, None,               "Always dropped."),
        ],
        "optins": [
            "description", "checklists", "stickers", "stopwatch", "timer",
            "time_tracking", "deal", "extension_data", "deadline_history", "timestamps",
        ],
        "hints_in_compact": [
            "has_description", "has_checklists", "has_stickers",
            "has_extension_data", "has_deadline", "has_stopwatch", "has_timer",
        ],
        "quirks": [
            "stopwatch: OpenAPI schema says {running, seconds, atMoment}, but runtime may expose "
            "{running, time, timestamp}. Field names unverified — pending integration test.",
            "SprintStickerState.begin/end stored in seconds, not ms like other time fields.",
            "WebhookFilters.name described as array in OpenAPI, actually a string enum.",
            "CompanyListDtoBase uses 'name', CompanyDto uses 'title'.",
        ],
        "heavy_fields_warning": "description may be multi-KB HTML; checklists grow unbounded",
    },
    "project": {
        "entity": "project",
        "fields": [
            _f("id",        "string (UUID)",       _ALL,  None,        "Primary key."),
            _f("title",     "string",              _CF,   None,        "Project name."),
            _f("deleted",   "boolean",             _CF,   None,        "Included only if true."),
            _f("createdAt", "string (ISO-8601)",   _CF,   None,        "Derived from timestamp ms."),
            _f("users",     "object (map)",        _F,    None,        "Members map; use get_project for full access."),
            _f("timestamp", "integer (ms epoch)",  _F,    "timestamps","Raw creation timestamp."),
        ],
        "optins": ["timestamps"],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "board": {
        "entity": "board",
        "fields": [
            _f("id",        "string (UUID)", _ALL,  None, "Primary key."),
            _f("name",      "string",        _CF,   None, "Board name."),
            _f("projectId", "string (UUID)", _CF,   None, "Parent project."),
            _f("deleted",   "boolean",       _CF,   None, "Included only if true."),
            _f("stickers",  "object",        _CF,   None, "Board sticker configuration (not task sticker values)."),
        ],
        "optins": [],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "column": {
        "entity": "column",
        "fields": [
            _f("id",      "string (UUID)", _ALL, None, "Primary key."),
            _f("title",   "string",        _CF,  None, "Column name."),
            _f("boardId", "string (UUID)", _CF,  None, "Parent board."),
            _f("deleted", "boolean",       _CF,  None, "Included only if true."),
        ],
        "optins": [],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "user": {
        "entity": "user",
        "fields": [
            _f("id",           "string (UUID)",      _ALL,  None, "Primary key."),
            _f("email",        "string",             _CF,   None, "User identifier."),
            _f("realName",     "string",             _CF,   None, "Display name."),
            _f("status",       "string (enum)",      _CF,   None, "online/offline."),
            _f("lastActivity", "integer (ms epoch)", _NONE, None, "Always dropped in compact."),
        ],
        "optins": [],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "message": {
        "entity": "message",
        "fields": [
            _f("id",            "string (UUID)",      _ALL,  None, "Primary key."),
            _f("text",          "string",             _CF,   None, "Plain text content."),
            _f("chatId",        "string (UUID)",      _CF,   None, "Parent chat/task."),
            _f("userId",        "string (UUID)",      _CF,   None, "Author UUID."),
            _f("deleted",       "boolean",            _CF,   None, "Included only if true."),
            _f("reactions",     "object",             _CF,   None, "Included if non-empty."),
            _f("textHtml",      "string (HTML)",      _NONE, None, "Always dropped; plain text sufficient."),
            _f("editTimestamp", "integer (ms epoch)", _NONE, None, "Always dropped."),
        ],
        "optins": [],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "group_chat": {
        "entity": "group_chat",
        "fields": [
            _f("id",            "string (UUID)", _ALL,  None,        "Primary key."),
            _f("name",          "string",        _CF,   None,        "Chat name."),
            _f("users",         "array[UUID]",   _CF,   None,        "Participant list."),
            _f("deleted",       "boolean",       _CF,   None,        "Included only if true."),
            _f("userRoleMap",   "object",        _F,    "chat_maps", "Role mapping; opt-in. Same include key as roleConfigMap."),
            _f("roleConfigMap", "object",        _F,    "chat_maps", "Role config; opt-in. Same include key as userRoleMap."),
        ],
        "optins": ["chat_maps"],
        "hints_in_compact": [],
        "quirks": [],
        "heavy_fields_warning": None,
    },
    "sticker": {
        "entity": "sticker",
        "fields": [
            _f("id",      "string (UUID)", _ALL,  None,                                    "Primary key."),
            _f("name",    "string",        _CF,   None,                                    "Sticker name."),
            _f("type",    "string (enum)", _CF,   None,                                    "'string' or 'sprint'."),
            _f("deleted", "boolean",       _CF,   None,                                    "Included only if true."),
            _f("states",  "array",         _F,    "sprint_states",                         "For sprint stickers. include_key depends on sticker type."),
            _f("states (string)", "array", _F,    "string_states",                         "For string stickers. include_key depends on sticker type."),
            _f("limit",   "integer",       _NONE, None,                                    "Pagination artifact dropped always (OpenAPI quirk)."),
            _f("offset",  "integer",       _NONE, None,                                    "Pagination artifact dropped always (OpenAPI quirk)."),
        ],
        "optins": ["sprint_states", "string_states"],
        "hints_in_compact": [],
        "quirks": [
            "SprintStickerState.begin/end stored in seconds, not ms like other time fields. "
            "normalize_sprint_sticker_state() auto-converts.",
            "limit and offset fields appear in sticker list responses (OpenAPI codegen artifact) — always dropped.",
            "Sprint vs string sticker: используй поле 'type' чтобы определить какой include_key валиден. "
            "'sprint' → include=['sprint_states'], 'string' → include=['string_states'].",
        ],
        "heavy_fields_warning": None,
    },
    "webhook": {
        "entity": "webhook",
        "fields": [
            _f("id",                      "string (UUID)",  _ALL,  None, "Primary key."),
            _f("url",                     "string",         _CF,   None, "Target URL."),
            _f("events",                  "array[string]",  _CF,   None, "Subscribed event types."),
            _f("filters",                 "array[object]",  _CF,   None, "WebhookFilters. See quirks: name field is string, not array."),
            _f("deleted",                 "boolean",        _CF,   None, "Included only if true."),
            _f("lastSuccess",             "integer (ms epoch)", _NONE, None, "Monitoring metric; dropped."),
            _f("failuresSinceLastSuccess","integer",        _NONE, None, "Monitoring metric; dropped."),
        ],
        "optins": [],
        "hints_in_compact": [],
        "quirks": [
            "WebhookFilters.name described as array in OpenAPI, actually a string enum. "
            "normalize_webhook_filters() auto-corrects before sending to API.",
        ],
        "heavy_fields_warning": None,
    },
}


def get_entity_schema(entity: str) -> dict | None:
    """
    Возвращает схему полей для указанной entity.

    Args:
        entity: Имя сущности (task, project, board, column, user,
                message, group_chat, sticker, webhook).

    Returns:
        Словарь {entity, fields, optins, hints_in_compact, quirks, heavy_fields_warning}
        или None если entity неизвестна.
    """
    return _SCHEMA.get(entity)


def get_all_entities() -> list[str]:
    """
    Возвращает список всех зарегистрированных entity.

    Returns:
        Список имён сущностей (9 элементов).
    """
    return list(_SCHEMA.keys())
