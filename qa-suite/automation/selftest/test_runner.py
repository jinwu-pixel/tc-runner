# runner fail-fast 검증 — 닫힌 exit code 체계 / config·단말 검사 / 결과 0건 INFRA
import glob
import json
import os
import re

import pytest

import runner
from runner import (
    RunnerInfraError,
    compute_exit,
    load_config,
    parse_adb_devices,
    resolve_device,
)


# ---------- exit code 체계 ----------

@pytest.mark.parametrize("statuses,expected", [
    ([], 3),                                  # 결과 0건 = INFRA
    (["PASS", "INFRA_FAILURE"], 3),           # INFRA 최우선
    (["INFRA_FAILURE", "FAIL"], 3),
    (["PASS", "FAIL", "WARN"], 1),            # FAIL > WARN
    (["PASS", "WARN"], 2),
    (["WARN"], 2),
    (["SKIP", "SKIP"], 2),                    # 전체 SKIP = 2
    (["PASS"], 0),
    (["PASS", "SKIP"], 0),                    # PASS+SKIP = 0
])
def test_compute_exit_matrix(statuses, expected):
    assert compute_exit(statuses) == expected


# ---------- config fail-fast ----------

def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(RunnerInfraError):
        load_config(str(tmp_path / "config.local.yaml"))


def test_load_config_broken_yaml_raises(tmp_path):
    p = tmp_path / "config.local.yaml"
    p.write_text("tests: [unclosed", encoding="utf-8")
    with pytest.raises(RunnerInfraError):
        load_config(str(p))


def test_load_config_requires_pyyaml(monkeypatch, tmp_path):
    p = tmp_path / "config.local.yaml"
    p.write_text("repeat: 1", encoding="utf-8")
    monkeypatch.setattr(runner, "yaml", None)
    with pytest.raises(RunnerInfraError):
        load_config(str(p))


def test_load_config_ok(tmp_path):
    p = tmp_path / "config.local.yaml"
    p.write_text("device_id: ''\nrepeat: 5\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["repeat"] == 5


# ---------- 단말 검사 ----------

def test_parse_adb_devices_filters_states():
    out = ("List of devices attached\n"
           "SER1\tdevice\n"
           "SER2\toffline\n"
           "SER3\tunauthorized\n\n")
    assert parse_adb_devices(out) == ["SER1"]


def test_resolve_device_single_auto():
    assert resolve_device({"device_id": ""}, ["SER1"]) == "SER1"


def test_resolve_device_zero_raises():
    with pytest.raises(RunnerInfraError):
        resolve_device({"device_id": ""}, [])


def test_resolve_device_multiple_raises():
    with pytest.raises(RunnerInfraError):
        resolve_device({"device_id": ""}, ["SER1", "SER2"])


def test_resolve_device_explicit_connected():
    assert resolve_device({"device_id": "SER2"}, ["SER1", "SER2"]) == "SER2"


def test_resolve_device_explicit_missing_raises():
    with pytest.raises(RunnerInfraError):
        resolve_device({"device_id": "SERX"}, ["SER1"])


# ---------- main e2e (단말·하니스 호출 없음) ----------

class FakePassTest:
    def __init__(self, config):
        self.config = config

    def run(self):
        return [("PASS", "", None), ("SKIP", "fit 제외", None)]


class FakeWarnTest(FakePassTest):
    def run(self):
        return [("WARN", "의심", None)]


class FakeEmptyTest(FakePassTest):
    def run(self):
        return []


class FakeBadStatusTest(FakePassTest):
    def run(self):
        return [("PASSS", "", None)]


def run_main(monkeypatch, tmp_path, registry, config_text, devices=("SER1",)):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.local.yaml").write_text(config_text, encoding="utf-8")
    monkeypatch.setattr(runner, "TEST_REGISTRY", registry)
    with pytest.raises(SystemExit) as e:
        runner.main(query_devices=lambda: list(devices))
    return e.value.code


def test_main_all_pass_exit0_and_summary_json(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakePassTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 0
    found = glob.glob(str(tmp_path / "report" / "*" / "summary.json"))
    assert len(found) == 1
    run_id = os.path.basename(os.path.dirname(found[0]))
    assert re.fullmatch(r"\d{8}T\d{6}Z", run_id), "run_id 는 UTC YYYYMMDDTHHMMSSZ"
    data = json.loads(open(found[0], encoding="utf-8").read())
    assert data["schema_version"] == 1
    assert data["run_id"] == run_id


def test_main_warn_exit2(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakeWarnTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 2


def test_main_unknown_test_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {}, "device_id: ''\ntests: [nope]\n")
    assert code == 3


def test_main_zero_selected_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakePassTest},
                    "device_id: ''\ntests: []\n")
    assert code == 3


def test_main_zero_results_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakeEmptyTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 3


def test_main_invalid_status_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakeBadStatusTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 3


def test_main_no_device_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakePassTest},
                    "device_id: ''\ntests: [fake]\n", devices=())
    assert code == 3


def test_main_two_devices_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakePassTest},
                    "device_id: ''\ntests: [fake]\n", devices=("SER1", "SER2"))
    assert code == 3


def test_main_missing_config_exit3(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "TEST_REGISTRY", {"fake": FakePassTest})
    with pytest.raises(SystemExit) as e:
        runner.main(query_devices=lambda: ["SER1"])
    assert e.value.code == 3


# ---------- P1-2: runner 최외곽 예외도 INFRA_FAILURE(3) ----------

class FakeRaisingTest(FakePassTest):
    def run(self):
        raise PermissionError("logs dir denied")


class FakeMalformedTupleTest(FakePassTest):
    def run(self):
        return [("FAIL",)]  # (status, reason, artifact) 3-tuple 계약 위반


def test_main_module_exception_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakeRaisingTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 3


def test_main_malformed_result_tuple_exit3(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, {"fake": FakeMalformedTupleTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 3


def test_main_report_write_failure_exit3(monkeypatch, tmp_path):
    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(runner, "write_summary_json", boom)
    code = run_main(monkeypatch, tmp_path, {"fake": FakePassTest},
                    "device_id: ''\ntests: [fake]\n")
    assert code == 3
