"""
Хранилище per-session активных workspace'ов.

Ключ: объект ServerSession (или любой weakref-compatible объект).
Значение: slug активного workspace (строка).

Использует WeakKeyDictionary — при GC сессии запись удаляется автоматически,
исключая утечку состояния при переиспользовании id() Python'ом.

Не персистентен — только на время жизни процесса.
"""
import threading
import weakref
from typing import Optional

_lock = threading.Lock()
_state: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def get_active(session_obj) -> Optional[str]:
    """Возвращает активный workspace slug или None если не установлен."""
    with _lock:
        return _state.get(session_obj)


def set_active(session_obj, slug: str) -> None:
    """Сохраняет активный workspace slug для данной сессии."""
    with _lock:
        _state[session_obj] = slug


def clear_active(session_obj) -> None:
    """Удаляет запись для сессии (idempotent — не бросает если нет)."""
    with _lock:
        _state.pop(session_obj, None)


def resolve_workspace(
    workspace: Optional[str],
    ctx,
    registry,
) -> str:
    """
    Определяет эффективный workspace slug для тул-вызова.

    Приоритет:
    1. Явный workspace (не None) → используем его (backward compat).
    2. Session active workspace (из ctx.session объекта) → если установлен.
    3. "default" — fallback.

    Бросает WorkspaceNotConfiguredError если итоговый slug не зарегистрирован.
    """
    from src.core.exceptions import WorkspaceNotConfiguredError

    if workspace is not None:
        effective = workspace
    elif ctx is not None:
        session_active = get_active(ctx.session)
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
