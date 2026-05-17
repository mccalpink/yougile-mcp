"""
Compact/full response pruning for YouGile MCP read-tools.

Default behavior is compact: noisy fields (timestamps, createdBy,
human-readable duplicate IDs, type/extensionData/etc.) are dropped
unless the caller explicitly passes verbosity='full'. Compact responses
include a top-level '_meta' block listing what was dropped for the
specific object so the agent knows to ask for full mode if it needs them.

Whitelist / dropfields per DTO derived from the verbosity research:
docs_work/may17/yougile/plan/research/response_verbosity.md §C.2
"""

from typing import Any, Literal

Verbosity = Literal["custom", "compact", "full"]


# ---------------------------------------------------------------------------
# Per-DTO compactors
#
# Each compactor takes a single dict, returns (compacted_dict, omitted_fields).
# omitted_fields uses dot-notation for nested drops (e.g. "deadline.history")
# and is built dynamically from what was actually present in the input.
# ---------------------------------------------------------------------------


def _compact_task(task: dict) -> tuple[dict, list[str]]:
    """Drop noisy fields from a task dict. Returns (compacted, omitted_paths)."""
    out = dict(task)
    omitted: list[str] = []

    # Always drop (if present at all)
    DROP_ALWAYS = (
        "timestamp",
        "archivedTimestamp",
        "completedTimestamp",
        "createdBy",
        "idTaskCommon",
        "idTaskProject",
        "type",
        "extensionData",
    )
    for k in DROP_ALWAYS:
        if k in out:
            del out[k]
            omitted.append(k)

    # Drop if default / empty
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    if out.get("archived") is False:
        del out["archived"]
        omitted.append("archived")
    if out.get("completed") is False:
        del out["completed"]
        omitted.append("completed")
    if "assigned" in out and out["assigned"] == []:
        del out["assigned"]
        omitted.append("assigned")
    if "subtasks" in out and out["subtasks"] == []:
        del out["subtasks"]
        omitted.append("subtasks")
    if "stickers" in out and out["stickers"] in (None, {}):
        del out["stickers"]
        omitted.append("stickers")
    if "checklists" in out and out["checklists"] == []:
        del out["checklists"]
        omitted.append("checklists")
    if "color" in out and not out["color"]:
        del out["color"]
        omitted.append("color")
    if "description" in out and not out["description"]:
        del out["description"]
        omitted.append("description")
    if "timeTracking" in out and not out["timeTracking"]:
        del out["timeTracking"]
        omitted.append("timeTracking")
    if "stopwatch" in out and not out["stopwatch"]:
        del out["stopwatch"]
        omitted.append("stopwatch")
    if "timer" in out and not out["timer"]:
        del out["timer"]
        omitted.append("timer")

    # Trim nested deadline: drop history/blockedPoints/links inside it
    if "deadline" in out and isinstance(out["deadline"], dict):
        deadline = dict(out["deadline"])
        for nested_key in ("history", "blockedPoints", "links"):
            if nested_key in deadline:
                del deadline[nested_key]
                omitted.append(f"deadline.{nested_key}")
        out["deadline"] = deadline

    return out, omitted


def _compact_project(project: dict) -> tuple[dict, list[str]]:
    """Drop timestamps and users-role map from a project dict."""
    out = dict(project)
    omitted: list[str] = []
    for k in ("timestamp", "users"):
        if k in out:
            del out[k]
            omitted.append(k)
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


def _compact_board(board: dict) -> tuple[dict, list[str]]:
    out = dict(board)
    omitted: list[str] = []
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


def _compact_column(column: dict) -> tuple[dict, list[str]]:
    """Columns are already minimal; only strip default deleted flag."""
    out = dict(column)
    omitted: list[str] = []
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


def _compact_user(user: dict) -> tuple[dict, list[str]]:
    """Keep only id, email, realName."""
    KEEP = {"id", "email", "realName"}
    out = {k: v for k, v in user.items() if k in KEEP}
    omitted = [k for k in user.keys() if k not in KEEP]
    return out, omitted


def _compact_message(msg: dict) -> tuple[dict, list[str]]:
    out = dict(msg)
    omitted: list[str] = []
    for k in ("textHtml", "editTimestamp"):
        if k in out:
            del out[k]
            omitted.append(k)
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    if "reactions" in out and not out["reactions"]:
        del out["reactions"]
        omitted.append("reactions")
    return out, omitted


def _compact_group_chat(chat: dict) -> tuple[dict, list[str]]:
    out = dict(chat)
    omitted: list[str] = []
    for k in ("userRoleMap", "roleConfigMap"):
        if k in out:
            del out[k]
            omitted.append(k)
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


def _compact_sticker(sticker: dict) -> tuple[dict, list[str]]:
    out = dict(sticker)
    omitted: list[str] = []
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


def _compact_webhook(wh: dict) -> tuple[dict, list[str]]:
    out = dict(wh)
    omitted: list[str] = []
    for k in ("lastSuccess", "failuresSinceLastSuccess"):
        if k in out:
            del out[k]
            omitted.append(k)
    if "deleted" in out and out["deleted"] in (None, False):
        del out["deleted"]
        omitted.append("deleted")
    return out, omitted


_COMPACTORS = {
    "task": _compact_task,
    "project": _compact_project,
    "board": _compact_board,
    "column": _compact_column,
    "user": _compact_user,
    "message": _compact_message,
    "group_chat": _compact_group_chat,
    "sticker": _compact_sticker,
    "webhook": _compact_webhook,
}


# ---------------------------------------------------------------------------
# Include[] resolution
# ---------------------------------------------------------------------------

# Словарь специальных opt-in ключей для include[]
# Ключ → (поле или поля для добавления, вложенный путь если нужен)
_INCLUDE_KEYS: dict = {
    "deadline_history": {"field": "deadline", "nested": "history", "dto": "task"},
    "description": {"field": "description", "dto": "task"},
    "checklists": {"field": "checklists", "dto": "task"},
    "extension_data": {"field": "extensionData", "dto": "task"},
    "stickers": {"field": "stickers", "dto": "task"},
    "deal": {"field": "deal", "dto": "task"},
    "stopwatch": {"field": "stopwatch", "dto": "task"},
    "timer": {"field": "timer", "dto": "task"},
    "time_tracking": {"field": "timeTracking", "dto": "task"},
    "permissions": {"field": "permissions", "dto": "project_role"},
    "sprint_states": {"field": "states", "dto": "sticker"},
    "string_states": {"field": "states", "dto": "sticker"},
    "chat_maps": {"fields": ["userRoleMap", "roleConfigMap"], "dto": "group_chat"},
    "crm_fields": {"fields": ["fields", "customFields"], "dto": "crm"},
    "timestamps": {"fields": ["timestamp", "archivedTimestamp", "completedTimestamp"], "dto": "task"},
}

# Все зарегистрированные opt-in ключи (для include=["all"])
_ALL_INCLUDE_KEYS: set = set(_INCLUDE_KEYS.keys())


def apply_includes(obj: dict, source: dict, include: list, dto_type: str) -> tuple:
    """Добавляет поля из include[] к уже отфильтрованному obj.

    Args:
        obj: уже отфильтрованный объект (после custom/compact strip).
        source: оригинальный сырой объект (источник полей для include).
        include: список include-ключей или имён полей.
        dto_type: тип DTO для разрешения специальных ключей.

    Returns:
        (обновлённый obj, список неизвестных ключей)
    """
    unknown: list = []
    effective_keys = _ALL_INCLUDE_KEYS if "all" in include else include

    for key in effective_keys:
        if key == "all":
            continue

        if key in _INCLUDE_KEYS:
            spec = _INCLUDE_KEYS[key]
            nested = spec.get("nested")
            if nested:
                # Вложенное поле: например deadline.history
                parent_field = spec["field"]
                if parent_field in source:
                    parent_val = source[parent_field]
                    if isinstance(parent_val, dict) and nested in parent_val:
                        # Мержим в уже имеющийся parent или создаём
                        existing = obj.get(parent_field, {})
                        if not isinstance(existing, dict):
                            existing = {}
                        existing[nested] = parent_val[nested]
                        obj[parent_field] = existing
            elif "fields" in spec:
                for field_name in spec["fields"]:
                    if field_name in source:
                        obj[field_name] = source[field_name]
            else:
                field_name = spec["field"]
                if field_name in source:
                    obj[field_name] = source[field_name]
        elif key in source:
            # Прямое имя поля (не спец. ключ) — добавляем напрямую
            obj[key] = source[key]
        else:
            unknown.append(key)

    return obj, unknown


# ---------------------------------------------------------------------------
# Custom mode helper
# ---------------------------------------------------------------------------


def _apply_custom(data: Any, dto_type: str, include: "list[str] | None") -> Any:
    """Custom mode: id + явно запрошенные поля через include[]."""

    def _strip_and_include(obj: dict) -> tuple:
        base = {"id": obj["id"]} if "id" in obj else dict(obj)
        unknown: list = []
        if include:
            base, unknown = apply_includes(base, obj, include, dto_type)
        return base, unknown

    if isinstance(data, dict) and "paging" in data and "content" in data:
        compacted_content = []
        all_unknown: set = set()
        for item in data["content"]:
            if isinstance(item, dict):
                c, unknown = _strip_and_include(item)
                compacted_content.append(c)
                all_unknown.update(unknown)
            else:
                compacted_content.append(item)
        out: dict = {"paging": data["paging"], "content": compacted_content}
        meta: dict = {"verbosity": "custom"}
        if all_unknown:
            meta["unknown_includes"] = sorted(all_unknown)
        out["_meta"] = meta
        return out

    if isinstance(data, list):
        all_unknown_list: set = set()
        result = []
        for item in data:
            if isinstance(item, dict):
                c, unknown = _strip_and_include(item)
                result.append(c)
                all_unknown_list.update(unknown)
            else:
                result.append(item)
        return result

    if isinstance(data, dict):
        c, unknown = _strip_and_include(data)
        if unknown:
            meta: dict = {"verbosity": "custom", "unknown_includes": sorted(unknown)}
            return {"_meta": meta, **c}
        return c

    return data


# ---------------------------------------------------------------------------
# Hints builder
# ---------------------------------------------------------------------------

# Поля, для которых строятся _hints в compact list_* (только для TaskDto)
_TASK_HINT_FIELDS = {
    "has_description": lambda t: bool(t.get("description")),
    "has_checklists": lambda t: bool(t.get("checklists")),
    "has_stickers": lambda t: bool(t.get("stickers")),
    "has_extension_data": lambda t: bool(t.get("extensionData")),
    "has_deadline": lambda t: bool(t.get("deadline") and t["deadline"].get("deadline")),
    "has_stopwatch": lambda t: bool(t.get("stopwatch")),
    "has_timer": lambda t: bool(t.get("timer")),
}


def build_hints(obj: dict, dto_type: str) -> "dict | None":
    """Строит _hints блок для compact list_* ответов.

    Returns:
        Словарь has_X: bool, или None если для dto_type _hints не предусмотрены.
    """
    if dto_type != "task":
        return None
    return {key: checker(obj) for key, checker in _TASK_HINT_FIELDS.items()}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_verbosity(
    data: Any,
    dto_type: str,
    verbosity: Verbosity = "compact",
    include: "list[str] | None" = None,
    is_list: bool = False,
) -> Any:
    """Apply verbosity rules to an API response.

    Args:
        data: a single dict (get-style), a list of dicts (list-style),
              or a paging envelope ``{'paging': ..., 'content': [...]}``.
        dto_type: one of the registered compactor types
                  ('task', 'project', 'board', 'column', 'user', 'message',
                  'group_chat', 'sticker', 'webhook').
        verbosity: 'compact' (default) — apply pruning;
                   'full' — pass-through, no changes.

    Returns:
        - For ``verbosity='full'``: ``data`` unchanged.
        - For ``verbosity='compact'``:
            * single dict → compacted dict; ``_meta`` inserted iff anything
              was actually omitted for that object.
            * list[dict] → list of compacted dicts (no top-level ``_meta``
              because lists have no place for it — agents rely on the
              tool description for the awareness signal).
            * paging envelope → same envelope with content items compacted;
              top-level ``_meta`` added iff any aggregate field was omitted.
        - Unknown ``dto_type`` is passed through untouched.
    """
    if verbosity == "full":
        return data

    if dto_type not in _COMPACTORS:
        return data  # Unknown DTO — fail open, don't mangle.

    # --- custom: только id, остальное через include[] ---
    if verbosity == "custom":
        return _apply_custom(data, dto_type, include)

    compactor = _COMPACTORS[dto_type]

    # Case 1: paging envelope ({paging, content})
    if isinstance(data, dict) and "paging" in data and "content" in data:
        compacted_content: list[Any] = []
        all_omitted: set[str] = set()
        for item in data["content"]:
            if isinstance(item, dict):
                c, omitted = compactor(item)
                if is_list:
                    hints = build_hints(item, dto_type)  # строим по СЫРОМУ item
                    if hints is not None:
                        c["_hints"] = hints
                compacted_content.append(c)
                all_omitted.update(omitted)
            else:
                compacted_content.append(item)
        out: dict[str, Any] = {"paging": data["paging"], "content": compacted_content}
        # Preserve any extra top-level keys.
        for k, v in data.items():
            if k not in ("paging", "content"):
                out[k] = v
        if all_omitted:
            out["_meta"] = _make_meta(sorted(all_omitted))
        return out

    # Case 2: bare list of dicts
    if isinstance(data, list):
        compacted_items: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                c, _omitted = compactor(item)
                compacted_items.append(c)
            else:
                compacted_items.append(item)
        # Bare lists have no slot for `_meta` — the tool description carries
        # the awareness signal instead.
        return compacted_items

    # Case 3: single dict
    if isinstance(data, dict):
        compacted, omitted = compactor(data)
        if omitted:
            # _meta-first ordering: agents tend to scan top-of-object first.
            return {"_meta": _make_meta(omitted), **compacted}
        return compacted

    # Anything else (None, scalar) — leave alone.
    return data


def _make_meta(omitted: list[str]) -> dict:
    return {
        "verbosity": "compact",
        "omitted_fields": omitted,
        "hint": "Pass verbosity='full' to include all fields",
    }
