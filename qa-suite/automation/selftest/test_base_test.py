# BaseTest fail-closed 검증 — ADB CommandResult / 닫힌 enum / lifecycle
import subprocess

import pytest

from tests.base_test import BaseTest, CommandResult, InfraFailure, VALID_STATUSES


def make_config(tmp_path, **overrides):
    cfg = {"run_dir": str(tmp_path / "run"), "repeat": 1, "iter_gap": 0}
    cfg.update(overrides)
    return cfg


class PassTest(BaseTest):
    def run_once(self, index):
        return "PASS"


# ---------- CommandResult / adb ----------

def test_adb_success_returns_command_result(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        assert isinstance(argv, list), "argv 기반이어야 함 (shell=True 금지)"
        assert kw.get("shell") is not True
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    r = t.adb(["shell", "echo ok"])
    assert isinstance(r, CommandResult)
    assert r.ok
    assert r.stdout.strip() == "ok"
    assert r.timed_out is False


def test_adb_nonzero_exit_not_ok(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        return subprocess.CompletedProcess(argv, 1, b"", b"error: no devices/emulators found\n")

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    r = t.adb(["get-state"])
    assert not r.ok
    assert r.returncode == 1
    assert "no devices" in r.stderr


def test_adb_timeout_flagged_not_empty_string(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5)

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    r = t.adb(["logcat", "-d"])
    assert r.timed_out is True
    assert not r.ok


def test_adb_missing_executable_not_ok(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        raise FileNotFoundError("adb")

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    r = t.adb(["devices"])
    assert not r.ok
    assert "adb" in r.stderr


def test_adb_invalid_utf8_replaced(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, b"\xff\xfeabc", b"")

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    r = t.adb(["shell", "x"])  # 예외 없이 decode 되어야 함
    assert "abc" in r.stdout


# ---------- 판정 경로 InfraFailure 전파 ----------

def test_judgment_adb_failure_raises_infra(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        return subprocess.CompletedProcess(argv, 1, b"", b"error: device offline\n")

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    with pytest.raises(InfraFailure):
        t.crashed("com.example.app")


def test_anr_judgment_adb_failure_raises_infra(monkeypatch, tmp_path):
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=5)

    monkeypatch.setattr("tests.base_test.subprocess.run", fake_run)
    t = PassTest(make_config(tmp_path))
    with pytest.raises(InfraFailure):
        t.anr_of("com.example.app")


# ---------- 닫힌 status enum ----------

def test_valid_statuses_closed_set():
    assert set(VALID_STATUSES) == {"PASS", "WARN", "FAIL", "SKIP", "INFRA_FAILURE"}


def test_run_invalid_status_string_is_infra_not_pass(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            return "PASSS"  # 오타

    res = T(make_config(tmp_path, repeat=3)).run()
    assert res, "결과가 비어 있으면 안 됨"
    assert res[0][0] == "INFRA_FAILURE"
    assert all(s != "PASS" for s, _, _ in res)


def test_run_invalid_return_shape_is_infra(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            return 42

    res = T(make_config(tmp_path)).run()
    assert res[0][0] == "INFRA_FAILURE"


def test_run_skip_status_recorded(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            return ("SKIP", "device fit 제외")

    res = T(make_config(tmp_path)).run()
    assert res == [("SKIP", "device fit 제외", None)]


def test_run_warn_collects_artifacts(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            return ("WARN", "blank 의심")

        def collect_artifacts(self, index, status, reason):
            return "ARTDIR"

    res = T(make_config(tmp_path)).run()
    assert res == [("WARN", "blank 의심", "ARTDIR")]


# ---------- lifecycle ----------

def test_setup_failure_still_runs_teardown(tmp_path):
    calls = []

    class T(BaseTest):
        def setup(self):
            raise RuntimeError("setup boom")

        def teardown(self):
            calls.append("teardown")

        def run_once(self, index):
            calls.append("run_once")
            return "PASS"

    res = T(make_config(tmp_path, repeat=2)).run()
    assert calls == ["teardown"], "setup 실패 시 run_once 없이 teardown 만 실행"
    assert res[0][0] == "INFRA_FAILURE"
    assert "setup" in res[0][1]


def test_teardown_failure_appends_infra_keeps_results(tmp_path):
    class T(BaseTest):
        def teardown(self):
            raise RuntimeError("teardown boom")

        def run_once(self, index):
            return "PASS"

    res = T(make_config(tmp_path)).run()
    assert res[0] == ("PASS", "", None), "원래 결과 보존"
    assert res[-1][0] == "INFRA_FAILURE"
    assert "teardown" in res[-1][1]


def test_infra_failure_in_run_once_stops_loop(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            raise InfraFailure("adb dead")

    res = T(make_config(tmp_path, repeat=5)).run()
    assert len(res) == 1, "infra 실패 후 잔여 회차 중단"
    assert res[0][0] == "INFRA_FAILURE"


def test_unhandled_exception_in_run_once_is_infra(tmp_path):
    class T(BaseTest):
        def run_once(self, index):
            raise ValueError("bug in module")

    res = T(make_config(tmp_path, repeat=3)).run()
    assert res[0][0] == "INFRA_FAILURE"
    assert "ValueError" in res[0][1]
