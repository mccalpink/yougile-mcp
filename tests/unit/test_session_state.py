import threading
import pytest
from src.core.session_state import get_active, set_active, clear_active


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
