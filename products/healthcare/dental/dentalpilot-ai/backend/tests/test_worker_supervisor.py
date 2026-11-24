from app.workers.run_workers import _run_once, _run_supervised


def test_run_once_returns_true_on_success():
    assert _run_once("test", lambda: None) is True


def test_run_once_returns_false_on_failure():
    def boom():
        raise RuntimeError("boom")

    assert _run_once("test", boom) is False


def test_run_supervised_restarts_after_failure():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")

    _run_supervised("test", flaky, sleep_seconds=0)
    assert calls["n"] == 2