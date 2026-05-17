import threading
import pytest
from unittest.mock import MagicMock
from src.core.session_state import get_active, set_active, clear_active, resolve_workspace
from src.core.session_state import _state  # для teardown очистки
from src.core.exceptions import WorkspaceNotConfiguredError


class TestGetActiveDefault:
    def test_returns_none_for_unknown_session(self):
        assert get_active(99999) is None

    def test_returns_none_after_clear(self):
        set_active(1, "main")
        clear_active(1)
        assert get_active(1) is None


class TestSetActive:
    def test_stores_slug(self):
        set_active(10, "main")
        assert get_active(10) == "main"

    def test_overwrite_is_idempotent(self):
        set_active(11, "main")
        set_active(11, "team")
        assert get_active(11) == "team"

    def test_sessions_are_isolated(self):
        set_active(20, "alpha")
        set_active(21, "beta")
        assert get_active(20) == "alpha"
        assert get_active(21) == "beta"


class TestClearActive:
    def test_clear_nonexistent_is_safe(self):
        clear_active(99998)  # не должно бросать

    def test_clear_removes_entry(self):
        set_active(30, "main")
        clear_active(30)
        assert get_active(30) is None


class TestThreadSafety:
    def test_concurrent_set_get_no_race(self):
        results = []
        errors = []

        def worker(session_id: int):
            try:
                for _ in range(50):
                    set_active(session_id, f"ws_{session_id}")
                    val = get_active(session_id)
                    results.append(val)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100, 110)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 10 * 50


class FakeRegistry:
    def __init__(self, slugs):
        self._slugs = slugs

    def slugs(self):
        return self._slugs


class TestResolveWorkspace:
    def setup_method(self):
        self.registry = FakeRegistry(["default", "main", "team"])
        # Очистка глобального состояния перед каждым тестом
        _state.clear()

    def teardown_method(self):
        _state.clear()

    def test_explicit_wins_over_session(self):
        set_active(200, "main")
        ctx = MagicMock()
        ctx.session = object()  # id() будет уникальным
        # Явный workspace передан → возвращаем его
        result = resolve_workspace("team", ctx, self.registry)
        assert result == "team"

    def test_explicit_wins_when_session_also_set(self):
        # Явный workspace передан → возвращаем его (session не важен)
        result = resolve_workspace("main", None, self.registry)
        assert result == "main"

    def test_explicit_invalid_raises(self):
        with pytest.raises(WorkspaceNotConfiguredError):
            resolve_workspace("nonexistent", None, self.registry)

    def test_none_workspace_no_ctx_returns_default(self):
        result = resolve_workspace(None, None, self.registry)
        assert result == "default"

    def test_none_workspace_no_session_active_returns_default(self):
        ctx = MagicMock()
        ctx.session = object()  # нет set_active для этого id
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "default"

    def test_session_active_used_when_no_explicit(self):
        # Создаём объект сессии, запоминаем его id
        session_obj = object()
        sid = id(session_obj)
        set_active(sid, "team")
        ctx = MagicMock()
        ctx.session = session_obj
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "team"

    def test_session_active_invalid_slug_raises(self):
        session_obj = object()
        sid = id(session_obj)
        set_active(sid, "ghost_workspace")
        ctx = MagicMock()
        ctx.session = session_obj
        with pytest.raises(WorkspaceNotConfiguredError):
            resolve_workspace(None, ctx, self.registry)
