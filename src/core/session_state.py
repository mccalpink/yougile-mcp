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
