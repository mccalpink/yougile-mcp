import gc
import threading
import weakref
import pytest
from unittest.mock import MagicMock
from src.core.session_state import get_active, set_active, clear_active, resolve_workspace
from src.core.session_state import _state  # для teardown очистки
from src.core.exceptions import WorkspaceNotConfiguredError


class FakeSession:
    """Минимальная fake-сессия для тестов (weakref-compatible)."""
    pass


class TestGetActiveDefault:
    def test_returns_none_for_unknown_session(self):
        obj = FakeSession()
        assert get_active(obj) is None

    def test_returns_none_after_clear(self):
        obj = FakeSession()
        set_active(obj, "main")
        clear_active(obj)
        assert get_active(obj) is None


class TestSetActive:
    def test_stores_slug(self):
        obj = FakeSession()
        set_active(obj, "main")
        assert get_active(obj) == "main"

    def test_overwrite_is_idempotent(self):
        obj = FakeSession()
        set_active(obj, "main")
        set_active(obj, "team")
        assert get_active(obj) == "team"

    def test_sessions_are_isolated(self):
        obj_a = FakeSession()
        obj_b = FakeSession()
        set_active(obj_a, "alpha")
        set_active(obj_b, "beta")
        assert get_active(obj_a) == "alpha"
        assert get_active(obj_b) == "beta"


class TestClearActive:
    def test_clear_nonexistent_is_safe(self):
        obj = FakeSession()
        clear_active(obj)  # не должно бросать

    def test_clear_removes_entry(self):
        obj = FakeSession()
        set_active(obj, "main")
        clear_active(obj)
        assert get_active(obj) is None


class TestThreadSafety:
    def test_concurrent_set_get_no_race(self):
        results = []
        errors = []

        def worker(session_obj):
            try:
                for _ in range(50):
                    set_active(session_obj, f"ws_{id(session_obj)}")
                    val = get_active(session_obj)
                    results.append(val)
            except Exception as e:
                errors.append(e)

        sessions = [FakeSession() for _ in range(10)]
        threads = [threading.Thread(target=worker, args=(s,)) for s in sessions]
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
        session_obj = FakeSession()
        set_active(session_obj, "main")
        ctx = MagicMock()
        ctx.session = FakeSession()  # другая сессия без active
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
        ctx.session = FakeSession()  # нет set_active для этого объекта
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "default"

    def test_session_active_used_when_no_explicit(self):
        session_obj = FakeSession()
        set_active(session_obj, "team")
        ctx = MagicMock()
        ctx.session = session_obj
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "team"

    def test_session_active_invalid_slug_raises(self):
        session_obj = FakeSession()
        set_active(session_obj, "ghost_workspace")
        ctx = MagicMock()
        ctx.session = session_obj
        with pytest.raises(WorkspaceNotConfiguredError):
            resolve_workspace(None, ctx, self.registry)


class TestWeakrefAutoCleanup:
    def setup_method(self):
        _state.clear()

    def teardown_method(self):
        _state.clear()

    def test_weakref_auto_cleanup_after_gc(self):
        """После GC объекта-сессии entry автоматически удаляется из _state."""
        obj = FakeSession()
        set_active(obj, "main")
        assert get_active(obj) == "main"

        # Запоминаем weakref, потом удаляем strong ref
        ref = weakref.ref(obj)
        del obj
        gc.collect()

        # Объект должен быть мёртв, _state не должна содержать stale entry
        assert ref() is None, "Объект должен быть garbage collected"
        assert len(_state) == 0, f"_state должна быть пустой после GC, осталось: {len(_state)} entries"
