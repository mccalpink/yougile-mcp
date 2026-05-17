"""
Хранилище per-session активных workspace'ов.

Ключ: id(ctx.session) — Python id объекта ServerSession (уникален per-connection).
Значение: slug активного workspace (строка).

Не персистентен — только на время жизни процесса.
"""
import threading
from typing import Optional

_lock = threading.Lock()
_state: dict[int, str] = {}


def get_active(session_id: int) -> Optional[str]:
    """Возвращает активный workspace slug или None если не установлен."""
    with _lock:
        return _state.get(session_id)


def set_active(session_id: int, slug: str) -> None:
    """Сохраняет активный workspace slug для данной сессии."""
    with _lock:
        _state[session_id] = slug


def clear_active(session_id: int) -> None:
    """Удаляет запись для сессии (idempotent — не бросает если нет)."""
    with _lock:
        _state.pop(session_id, None)


def resolve_workspace(
    workspace: Optional[str],
    ctx,
    registry,
) -> str:
    """
    Определяет эффективный workspace slug для тул-вызова.

    Приоритет:
    1. Явный workspace (не None) → используем его (backward compat).
    2. Session active workspace (из id(ctx.session)) → если установлен.
    3. "default" — fallback.

    Бросает WorkspaceNotConfiguredError если итоговый slug не зарегистрирован.
    """
    from src.core.exceptions import WorkspaceNotConfiguredError

    if workspace is not None:
        effective = workspace
    elif ctx is not None:
        session_active = get_active(id(ctx.session))
        effective = session_active if session_active is not None else "default"
    else:
        effective = "default"

    if effective not in registry.slugs():
        raise WorkspaceNotConfiguredError(
            f"Workspace '{effective}' не настроен. "
            f"Доступные: {registry.slugs()}. "
            f"Установите YOUGILE_KEY_{effective.upper()}=... в .env или вызовите "
            f"set_active_workspace() с существующим slug."
        )
    return effective
