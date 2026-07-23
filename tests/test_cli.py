import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from openpyxl import Workbook

import src.cli as cli
from src.action_runner import StepResult
from src.cli import _resolve_tc_files, main


ROOT = Path(__file__).resolve().parents[1]

TASK5_CORPUS = (
    "golden_tc_set/DEMO_01_basic_app_launch.yaml",
    "golden_tc_set/DEMO_02_device_info.yaml",
    "golden_tc_set/DEMO_03_wifi_airplane_toggle.yaml",
    "exported_tc1/BUG_25175_LGU_APN_menu.yaml",
    "exported_tc1/BUG_5426_airplane_reboot_apn.yaml",
    "exported_tc1/SS_01_main_screen.yaml",
    "exported_tc1/SS_02_family_contact.yaml",
    "exported_tc1/SS_03_detection_history.yaml",
    "exported_tc1/SS_04_phishing_training.yaml",
    "exported_tc1/SS_05_full_navigation.yaml",
    "exported_tc1/SS_06_realistic_call_path_critical.yaml",
    "exported_tc1/SS_07_banking_cooldown_full_60s.yaml",
    "exported_tc1/SS_B3_settings_version.yaml",
    "exported_tc1/SS_TC03_telebanking_simulation.yaml",
    "exported_tc1/SS_TC04_popup_cooldown_preview.yaml",
    "exported_tc1/SS_TC08_confirm_safe.yaml",
    "exported_tc1/SS_TC09_training_playthrough.yaml",
    "exported_tc1/SS_TC10_full_reset.yaml",
    "exported_tc1/SS_TC_ALPHA_1_home_sticky_60s.yaml",
    "exported_tc1/SS_TC_ALPHA_2_nonCall_suppression.yaml",
    "exported_tc1/SS_TC_ALPHA_4_upgrade_escape.yaml",
    "exported_tc1/TC-01_권한미부여.yaml",
    "exported_tc1/TC-02_권한허용_Idle진입.yaml",
    "exported_tc1/TC-05A_9초_경계값.yaml",
    "exported_tc1/TC-05B_10초_경계값.yaml",
    "exported_tc1/TC-06_부재중_거절.yaml",
    "exported_tc1/TC-08_긴통화_파이프라인.yaml",
    "exported_tc1/TC-10_권한흔들기.yaml",
    "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml",
    "THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml",
)


def _write_tc(
    path: Path,
    *,
    name: str,
    metadata: dict | None = None,
    steps: list[dict] | None = None,
) -> Path:
    document = {
        "tc_name": name,
        "metadata": {
            "runnable": True,
            "tc_class": "FULL_AUTO",
            "execution_type": "AUTO",
            "manual_detail": "NONE",
            **(metadata or {}),
        },
        "steps": steps or [{"action": "wait", "duration": 1}],
    }
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


class _ConnectedADB:
    def is_connected(self):
        return True

    def get_device_info(self):
        return {"serial": "HOST-FAKE", "model": "fake", "android_version": "0"}

    def device_serial(self):
        return "HOST-FAKE"


def create_test_excel(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["TC Name", "Step", "Action", "Parameter1", "Parameter2", "Expected"])
    ws.append(["테스트", 1, "key", "HOME", "", ""])
    ws.append(["테스트", 2, "wait", "1", "", ""])
    wb.save(path)


def test_resolve_xlsx_converts_to_yaml(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    create_test_excel(xlsx)

    tc_files, temp_dirs = _resolve_tc_files([str(xlsx)])

    assert len(tc_files) == 1
    assert tc_files[0].suffix == ".yaml"
    assert tc_files[0].exists()
    assert len(temp_dirs) == 1

    # cleanup
    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_yaml_passes_through(tmp_path):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\nsteps:\n  - action: wait\n    seconds: 1\n")

    tc_files, temp_dirs = _resolve_tc_files([str(yaml_file)])

    assert len(tc_files) == 1
    assert tc_files[0] == yaml_file
    assert len(temp_dirs) == 0


def test_resolve_mixed_xlsx_and_yaml(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    create_test_excel(xlsx)
    yaml_file = tmp_path / "extra.yaml"
    yaml_file.write_text("name: extra\nsteps:\n  - action: wait\n    seconds: 1\n")

    tc_files, temp_dirs = _resolve_tc_files([str(xlsx), str(yaml_file)])

    assert len(tc_files) == 2
    assert len(temp_dirs) == 1

    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_invalid_xlsx_skips(tmp_path):
    bad_xlsx = tmp_path / "bad.xlsx"
    bad_xlsx.write_bytes(b"not an excel file")

    tc_files, temp_dirs = _resolve_tc_files([str(bad_xlsx)])

    assert len(tc_files) == 0
    assert len(temp_dirs) == 1

    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_run_subparser_accepts_run_id(monkeypatch):
    """`cli run` 이 --run-id override 를 파싱하여 cmd_run 에 전달한다."""
    captured = {}

    def fake_run(args):
        captured["run_id"] = args.run_id
        captured["tc_files"] = list(args.tc_files)

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "run", "dummy.yaml", "--run-id", "20260526T120000Z"],
    )
    main()
    assert captured == {"run_id": "20260526T120000Z", "tc_files": ["dummy.yaml"]}


def test_run_subparser_run_id_default_none(monkeypatch):
    """--run-id 미지정 시 args.run_id == None (cmd_run 안에서 _now_run_id() 적용)."""
    captured = {}

    def fake_run(args):
        captured["run_id"] = args.run_id

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr("sys.argv", ["cli", "run", "dummy.yaml"])
    main()
    assert captured["run_id"] is None


def test_run_contract_mode_defaults_to_legacy(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["contract_mode"] = args.contract_mode

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr("sys.argv", ["cli", "run", "dummy.yaml"])

    main()

    assert captured["contract_mode"] == "legacy"


def test_run_accepts_canonical_contract_mode(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["contract_mode"] = args.contract_mode

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr(
        "sys.argv", ["cli", "run", "dummy.yaml", "--contract-mode", "canonical"]
    )

    main()

    assert captured["contract_mode"] == "canonical"


def test_run_rejects_unknown_contract_mode(monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["cli", "run", "dummy.yaml", "--contract-mode", "future"]
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2


def test_run_parser_exposes_serial_and_strict_shell_independently(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["serial"] = args.serial
        captured["strict_shell"] = args.strict_shell

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli",
            "run",
            "dummy.yaml",
            "--serial",
            "SERIAL",
            "--strict-shell",
        ],
    )

    main()

    assert captured == {"serial": "SERIAL", "strict_shell": True}


def test_run_parser_serial_and_strict_shell_defaults_are_independent(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["serial"] = args.serial
        captured["strict_shell"] = args.strict_shell

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr("sys.argv", ["cli", "run", "dummy.yaml"])

    main()

    assert captured == {"serial": None, "strict_shell": False}


def test_invalid_serial_exits_before_adb_constructed(monkeypatch, capsys):
    adb_calls = []

    def forbidden_adb(*args, **kwargs):
        adb_calls.append((args, kwargs))
        raise AssertionError("invalid serial must stop before ADB construction")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=["unused.yaml"],
                run_id="20260722T010000Z",
                contract_mode="legacy",
                serial="BAD SERIAL",
                strict_shell=False,
            )
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert adb_calls == []
    assert "ERROR: --serial" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    ("serial", "strict_shell", "expected_args", "expected_kwargs"),
    [
        (None, False, (), {}),
        ("SERIAL", False, (), {"device_serial": "SERIAL"}),
        (None, True, (), {"strict_shell": True}),
        (
            "SERIAL",
            True,
            (),
            {"device_serial": "SERIAL", "strict_shell": True},
        ),
    ],
)
def test_cmd_run_adb_constructor_matrix(
    monkeypatch, serial, strict_shell, expected_args, expected_kwargs
):
    calls = []

    class DisconnectedADB:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def is_connected(self):
            return False

    monkeypatch.setattr(cli, "ADB", DisconnectedADB)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=["unused.yaml"],
                run_id="20260722T010001Z",
                contract_mode="legacy",
                serial=serial,
                strict_shell=strict_shell,
            )
        )

    assert exc_info.value.code == 1
    assert calls == [(expected_args, expected_kwargs)]


def test_canonical_preflight_rejects_runnable_false_before_adb_constructed(
    tmp_path, monkeypatch
):
    tc_file = _write_tc(
        tmp_path / "blocked.yaml",
        name="BLOCKED",
        metadata={"runnable": False, "runnable_reason": ["FIXTURE_REQUIRED"]},
    )
    adb_calls = []

    def forbidden_adb():
        adb_calls.append("constructed")
        raise AssertionError("ADB must not be constructed before canonical gate passes")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260721T010000Z",
                contract_mode="canonical",
                serial="SERIAL",
                strict_shell=True,
            )
        )

    assert exc_info.value.code == 1
    assert adb_calls == []


def test_canonical_preflight_rejects_unresolved_before_adb_constructed(
    tmp_path, monkeypatch
):
    tc_file = _write_tc(
        tmp_path / "unresolved.yaml",
        name="UNRESOLVED",
        metadata={
            "runnable": False,
            "runnable_reason": ["UNRESOLVED_PARAMS"],
            "has_unresolved_params": True,
        },
        steps=[
            {
                "action": "shell",
                "command": "am start -n com.example/.Main",
                "compile_status": "UNRESOLVED_PARAMS",
                "_unresolved_params": ["package"],
            }
        ],
    )
    adb_calls = []

    def forbidden_adb():
        adb_calls.append("constructed")
        raise AssertionError("ADB must not be constructed before canonical gate passes")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260721T010001Z",
                contract_mode="canonical",
            )
        )

    assert exc_info.value.code == 1
    assert adb_calls == []


@pytest.mark.parametrize(
    ("metadata", "steps", "reason_prefix"),
    [
        (
            {},
            [{"action": "tap_id"}],
            "CANONICAL_LOAD_OR_VALIDATION_ERROR",
        ),
        (
            {"runnable": False},
            None,
            "NOT_RUNNABLE",
        ),
        (
            {"runnable": False, "runnable_reason": ["FIXTURE_REQUIRED"]},
            None,
            "RUNNABLE_REASON_PRESENT",
        ),
        (
            {"has_unresolved_params": True},
            None,
            "METADATA_UNRESOLVED_PARAMS",
        ),
        (
            {},
            [{"action": "wait", "duration": 1, "compile_status": "UNRESOLVED_PARAMS"}],
            "STEP_UNRESOLVED_COMPILE_STATUS",
        ),
        (
            {},
            [{"action": "wait", "duration": 1, "_unresolved_params": ["duration"]}],
            "STEP_UNRESOLVED_PARAMS",
        ),
        (
            {},
            [{"action": "shell", "command": "am start -n {package}/.Main"}],
            "CANONICAL_LOAD_OR_VALIDATION_ERROR",
        ),
        (
            {},
            [{"action": "tap_text", "target": "canonical", "text": "legacy"}],
            "CANONICAL_LOAD_OR_VALIDATION_ERROR",
        ),
        (
            {},
            [{"action": "wait", "seconds": "not-a-number"}],
            "CANONICAL_LOAD_OR_VALIDATION_ERROR",
        ),
    ],
    ids=[
        "schema",
        "runnable-false",
        "runnable-reason",
        "metadata-unresolved",
        "compile-status",
        "unresolved-details",
        "shell-placeholder",
        "alias-conflict",
        "invalid-unit",
    ],
)
def test_canonical_host_preflight_rejects_each_blocker(
    tmp_path, metadata, steps, reason_prefix
):
    tc_file = _write_tc(
        tmp_path / "blocked.yaml",
        name="BLOCKED",
        metadata=metadata,
        steps=steps,
    )

    report = cli.host_preflight([tc_file], "canonical")

    assert report.passed is False
    assert report.loaded_tcs == ()
    assert any(
        reason.startswith(reason_prefix)
        for reason in report.verdicts[0].reasons
    )


def test_one_invalid_file_prevents_all_valid_files_from_running(tmp_path, monkeypatch):
    valid = _write_tc(tmp_path / "valid.yaml", name="VALID")
    invalid = _write_tc(
        tmp_path / "invalid.yaml",
        name="INVALID",
        metadata={"runnable": False, "runnable_reason": ["FIXTURE_REQUIRED"]},
    )
    loaded = []
    real_load_tc = cli.load_tc

    def recording_load(path, contract_mode="legacy"):
        loaded.append(Path(path))
        return real_load_tc(path, contract_mode=contract_mode)

    monkeypatch.setattr(cli, "load_tc", recording_load)
    monkeypatch.setattr(
        cli,
        "ADB",
        lambda: (_ for _ in ()).throw(
            AssertionError("valid subset must not reach the device phase")
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(valid), str(invalid)],
                run_id="20260721T010002Z",
                contract_mode="canonical",
            )
        )

    assert exc_info.value.code == 1
    assert loaded == [valid, invalid]


def test_empty_host_preflight_is_blocking():
    report = cli.host_preflight([], "canonical")

    assert report.passed is False
    assert report.loaded_tcs == ()


def test_canonical_resolution_failure_cleans_temp_before_adb(tmp_path, monkeypatch):
    valid_xlsx = tmp_path / "valid.xlsx"
    create_test_excel(valid_xlsx)
    conversion_tmp = tmp_path / "conversion-tmp"
    adb_calls = []

    def fake_mkdtemp(*, prefix):
        assert prefix == "tc_runner_"
        conversion_tmp.mkdir()
        return str(conversion_tmp)

    def forbidden_adb():
        adb_calls.append("constructed")
        raise AssertionError("resolution failure must stop before ADB")

    monkeypatch.setattr(cli.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(valid_xlsx), "missing-task5-input-*.yaml"],
                run_id="20260721T010002Z",
                contract_mode="canonical",
            )
        )

    assert exc_info.value.code == 1
    assert adb_calls == []
    assert not conversion_tmp.exists()


def test_canonical_nonverifier_failure_stops_remaining_steps_and_tcs(
    tmp_path, monkeypatch
):
    first = _write_tc(
        tmp_path / "first.yaml",
        name="FIRST",
        steps=[
            {"action": "tap_xy", "x": 1, "y": 2},
            {"action": "wait", "duration": 1},
        ],
    )
    second = _write_tc(tmp_path / "second.yaml", name="SECOND")
    calls = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "canonical"

        def run_step(self, step, *args, **kwargs):
            calls.append(step["action"])
            return StepResult(
                action=step["action"],
                passed=step["action"] != "tap_xy",
                message="forced failure" if step["action"] == "tap_xy" else "",
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", _ConnectedADB)
    monkeypatch.setattr(cli, "ActionRunner", FakeRunner)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(first), str(second)],
                run_id="20260721T010003Z",
                contract_mode="canonical",
            )
        )

    assert exc_info.value.code == 1
    assert calls == ["tap_xy"]


def test_canonical_failed_run_returns_nonzero_and_writes_partial_summary(
    tmp_path, monkeypatch
):
    tc_file = _write_tc(
        tmp_path / "partial.yaml",
        name="PARTIAL",
        steps=[
            {"action": "wait", "duration": 1},
            {"action": "tap_xy", "x": 1, "y": 2},
            {"action": "screenshot", "name": "must-not-run"},
        ],
    )
    calls = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "canonical"

        def run_step(self, step, *args, **kwargs):
            calls.append(step["action"])
            return StepResult(
                action=step["action"],
                passed=step["action"] != "tap_xy",
                message="forced failure" if step["action"] == "tap_xy" else "",
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", _ConnectedADB)
    monkeypatch.setattr(cli, "ActionRunner", FakeRunner)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260721T010004Z",
                contract_mode="canonical",
            )
        )

    summary_path = tmp_path / "reports" / "20260721T010004Z" / "summary.json"
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert exc_info.value.code == 1
    assert calls == ["wait", "tap_xy"]
    assert data["contract_mode"] == "canonical"
    assert data["run_status"] == "ABORTED_FAIL_CLOSED"
    assert [step["action"] for step in data["results"][0]["steps"]] == calls


def test_canonical_summary_persistence_failure_returns_nonzero(
    tmp_path, monkeypatch, capsys
):
    tc_file = _write_tc(tmp_path / "passing.yaml", name="PASSING")
    attempted_contexts = []
    real_reporter = cli.Reporter

    class FailingSummaryReporter(real_reporter):
        def write_summary_json(self):
            attempted_contexts.append((self.contract_mode, self.run_status))
            raise OSError("simulated disk full")

    class PassingRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "canonical"

        def run_step(self, step, *args, **kwargs):
            return StepResult(action=step["action"], passed=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", _ConnectedADB)
    monkeypatch.setattr(cli, "ActionRunner", PassingRunner)
    monkeypatch.setattr(cli, "Reporter", FailingSummaryReporter)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260721T010006Z",
                contract_mode="canonical",
            )
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert attempted_contexts == [("canonical", "COMPLETED")]
    assert "ERROR: canonical summary.json persistence failed" in captured.err


def test_legacy_verifier_only_break_policy_is_unchanged(tmp_path, monkeypatch):
    first = tmp_path / "legacy-first.yaml"
    first.write_text(
        json.dumps(
            {
                "name": "LEGACY_FIRST",
                "steps": [
                    {"action": "tap_xy"},
                    {"action": "wait"},
                    {"action": "verify_text"},
                    {"action": "screenshot"},
                ],
            }
        ),
        encoding="utf-8",
    )
    second = tmp_path / "legacy-second.yaml"
    second.write_text(
        json.dumps({"name": "LEGACY_SECOND", "steps": [{"action": "wait"}]}),
        encoding="utf-8",
    )
    calls = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs.get("contract_mode", "legacy") == "legacy"

        def run_step(self, step, *args, **kwargs):
            calls.append(step["action"])
            return StepResult(
                action=step["action"],
                passed=step["action"] not in {"tap_xy", "verify_text"},
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", _ConnectedADB)
    monkeypatch.setattr(cli, "ActionRunner", FakeRunner)

    cli.cmd_run(
        SimpleNamespace(
            tc_files=[str(first), str(second)],
            run_id="20260721T010005Z",
            contract_mode="legacy",
        )
    )

    data = json.loads(
        (tmp_path / "reports" / "20260721T010005Z" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert calls == ["tap_xy", "wait", "verify_text", "wait"]
    assert data["contract_mode"] == "legacy"
    assert data["run_status"] == "COMPLETED"
    assert data["device"]["serial_pinned"] is None
    assert data["device"]["serial_observed"] == "HOST-FAKE"


def test_serial_only_legacy_preserves_continue_policy_and_records_identity(
    tmp_path, monkeypatch
):
    first = tmp_path / "serial-only-first.yaml"
    first.write_text(
        json.dumps(
            {
                "name": "SERIAL_ONLY_FIRST",
                "steps": [
                    {"action": "tap_xy"},
                    {"action": "wait"},
                    {"action": "verify_text"},
                    {"action": "screenshot"},
                ],
            }
        ),
        encoding="utf-8",
    )
    second = tmp_path / "serial-only-second.yaml"
    second.write_text(
        json.dumps(
            {"name": "SERIAL_ONLY_SECOND", "steps": [{"action": "wait"}]}
        ),
        encoding="utf-8",
    )
    created = []
    calls = []

    class IdentityADB:
        def __init__(self, device_serial=None, *, strict_shell=False):
            assert device_serial == "PINNED-SERIAL"
            assert strict_shell is False
            created.append(self)

        def is_connected(self):
            return True

        def get_device_info(self):
            return {"model": "AT-M140", "android_version": "14"}

        def device_serial(self):
            return "OBSERVED-SERIAL"

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["adb"] is created[0]
            assert kwargs["contract_mode"] == "legacy"

        def run_step(self, step, *args, **kwargs):
            calls.append(step["action"])
            return StepResult(
                action=step["action"],
                passed=step["action"] not in {"tap_xy", "verify_text"},
                message="forced legacy failure",
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", IdentityADB)
    monkeypatch.setattr(cli, "ActionRunner", FakeRunner)

    cli.cmd_run(
        SimpleNamespace(
            tc_files=[str(first), str(second)],
            run_id="20260722T010002Z",
            contract_mode="legacy",
            serial="PINNED-SERIAL",
            strict_shell=False,
        )
    )

    data = json.loads(
        (tmp_path / "reports" / "20260722T010002Z" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert calls == ["tap_xy", "wait", "verify_text", "wait"]
    assert data["run_status"] == "COMPLETED"
    assert data["device"]["serial_pinned"] == "PINNED-SERIAL"
    assert data["device"]["serial_observed"] == "OBSERVED-SERIAL"


def test_serial_only_legacy_preserves_load_skip_behavior(
    tmp_path, monkeypatch, capsys
):
    invalid = tmp_path / "serial-load-invalid.yaml"
    valid = tmp_path / "serial-load-valid.yaml"
    invalid.write_text("placeholder", encoding="utf-8")
    valid.write_text("placeholder", encoding="utf-8")
    load_calls = []
    runner_calls = []

    def fake_load(path):
        path = Path(path)
        load_calls.append(path)
        if path == invalid:
            raise cli.TCValidationError("legacy invalid")
        return {"name": "SERIAL_VALID", "steps": [{"action": "wait"}]}

    class IdentityADB:
        def __init__(self, device_serial=None, *, strict_shell=False):
            assert device_serial == "PINNED-SERIAL"
            assert strict_shell is False

        def is_connected(self):
            return True

        def get_device_info(self):
            return {"model": "AT-M140", "android_version": "14"}

        def device_serial(self):
            return "OBSERVED-SERIAL"

    class PassingRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "legacy"

        def run_step(self, step, *args, **kwargs):
            runner_calls.append(step["action"])
            return StepResult(action=step["action"], passed=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", IdentityADB)
    monkeypatch.setattr(cli, "ActionRunner", PassingRunner)
    monkeypatch.setattr(cli, "load_tc", fake_load)

    cli.cmd_run(
        SimpleNamespace(
            tc_files=[str(invalid), str(valid)],
            run_id="20260722T010008Z",
            contract_mode="legacy",
            serial="PINNED-SERIAL",
            strict_shell=False,
        )
    )

    captured = capsys.readouterr()
    data = json.loads(
        (tmp_path / "reports" / "20260722T010008Z" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert load_calls == [invalid, valid]
    assert runner_calls == ["wait"]
    assert "SKIP:" in captured.out
    assert data["run_status"] == "COMPLETED"
    assert [result["name"] for result in data["results"]] == ["SERIAL_VALID"]


def test_serial_only_legacy_summary_write_failure_remains_warning(
    tmp_path, monkeypatch, capsys
):
    tc_file = tmp_path / "serial-summary-warning.yaml"
    tc_file.write_text(
        json.dumps({"name": "SERIAL_WARNING", "steps": [{"action": "wait"}]}),
        encoding="utf-8",
    )
    attempted_contexts = []
    real_reporter = cli.Reporter

    class IdentityADB:
        def __init__(self, device_serial=None, *, strict_shell=False):
            assert device_serial == "PINNED-SERIAL"
            assert strict_shell is False

        def is_connected(self):
            return True

        def get_device_info(self):
            return {"model": "AT-M140", "android_version": "14"}

        def device_serial(self):
            return "OBSERVED-SERIAL"

    class FailingSummaryReporter(real_reporter):
        def write_summary_json(self):
            attempted_contexts.append((self.contract_mode, self.run_status))
            raise OSError("simulated legacy disk full")

    class PassingRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "legacy"

        def run_step(self, step, *args, **kwargs):
            return StepResult(action=step["action"], passed=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", IdentityADB)
    monkeypatch.setattr(cli, "ActionRunner", PassingRunner)
    monkeypatch.setattr(cli, "Reporter", FailingSummaryReporter)

    cli.cmd_run(
        SimpleNamespace(
            tc_files=[str(tc_file)],
            run_id="20260722T010009Z",
            contract_mode="legacy",
            serial="PINNED-SERIAL",
            strict_shell=False,
        )
    )

    captured = capsys.readouterr()
    assert attempted_contexts == [("legacy", "COMPLETED")]
    assert "WARNING:" in captured.out
    assert "ERROR:" not in captured.err


def test_strict_legacy_action_failure_aborts_and_persists_partial_summary(
    tmp_path, monkeypatch
):
    first = tmp_path / "strict-first.yaml"
    first.write_text(
        json.dumps(
            {
                "name": "STRICT_FIRST",
                "steps": [
                    {"action": "tap_xy"},
                    {"action": "wait"},
                ],
            }
        ),
        encoding="utf-8",
    )
    second = tmp_path / "strict-second.yaml"
    second.write_text(
        json.dumps({"name": "STRICT_SECOND", "steps": [{"action": "wait"}]}),
        encoding="utf-8",
    )
    calls = []

    class StrictADB(_ConnectedADB):
        def __init__(self, *, strict_shell=False):
            assert strict_shell is True

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            assert kwargs["contract_mode"] == "legacy"

        def run_step(self, step, *args, **kwargs):
            calls.append(step["action"])
            return StepResult(
                action=step["action"],
                passed=False,
                message="strict failure",
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", StrictADB)
    monkeypatch.setattr(cli, "ActionRunner", FakeRunner)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(first), str(second)],
                run_id="20260722T010003Z",
                contract_mode="legacy",
                serial=None,
                strict_shell=True,
            )
        )

    data = json.loads(
        (tmp_path / "reports" / "20260722T010003Z" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert exc_info.value.code == 1
    assert calls == ["tap_xy"]
    assert data["contract_mode"] == "legacy"
    assert data["run_status"] == "ABORTED_FAIL_CLOSED"
    assert [step["action"] for step in data["results"][0]["steps"]] == calls


def test_strict_legacy_load_error_preserves_prior_results_in_partial_summary(
    tmp_path, monkeypatch
):
    first = tmp_path / "load-first.yaml"
    second = tmp_path / "load-invalid.yaml"
    third = tmp_path / "load-never-reached.yaml"
    first.write_text("placeholder", encoding="utf-8")
    second.write_text("placeholder", encoding="utf-8")
    third.write_text("placeholder", encoding="utf-8")
    load_calls = []
    runner_calls = []

    def fake_load(path):
        path = Path(path)
        load_calls.append(path)
        if path == second:
            raise cli.TCValidationError("invalid second file")
        if path == first:
            return {"name": "LOAD_FIRST", "steps": [{"action": "wait"}]}
        return {"name": "LOAD_THIRD", "steps": [{"action": "key"}]}

    class StrictADB(_ConnectedADB):
        def __init__(self, *, strict_shell=False):
            assert strict_shell is True

    class PassingRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run_step(self, step, *args, **kwargs):
            runner_calls.append(step["action"])
            return StepResult(action=step["action"], passed=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", StrictADB)
    monkeypatch.setattr(cli, "ActionRunner", PassingRunner)
    monkeypatch.setattr(cli, "load_tc", fake_load)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(first), str(second), str(third)],
                run_id="20260722T010004Z",
                contract_mode="legacy",
                serial=None,
                strict_shell=True,
            )
        )

    data = json.loads(
        (tmp_path / "reports" / "20260722T010004Z" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert exc_info.value.code == 1
    assert load_calls == [first, second]
    assert runner_calls == ["wait"]
    assert data["run_status"] == "ABORTED_FAIL_CLOSED"
    assert [result["name"] for result in data["results"]] == ["LOAD_FIRST"]


def test_strict_first_legacy_load_error_has_no_synthetic_summary(
    tmp_path, monkeypatch, capsys
):
    invalid = tmp_path / "load-invalid.yaml"
    later = tmp_path / "load-never-reached.yaml"
    invalid.write_text("placeholder", encoding="utf-8")
    later.write_text("placeholder", encoding="utf-8")
    load_calls = []

    def fake_load(path):
        path = Path(path)
        load_calls.append(path)
        if path == invalid:
            raise cli.TCValidationError("invalid first")
        return {"name": "NEVER_REACHED", "steps": [{"action": "wait"}]}

    class StrictADB(_ConnectedADB):
        def __init__(self, *, strict_shell=False):
            assert strict_shell is True

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", StrictADB)
    monkeypatch.setattr(cli, "load_tc", fake_load)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(invalid), str(later)],
                run_id="20260722T010005Z",
                contract_mode="legacy",
                serial=None,
                strict_shell=True,
            )
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert load_calls == [invalid]
    assert "SKIP:" not in captured.out
    assert "ERROR:" in captured.err
    assert not (tmp_path / "reports" / "20260722T010005Z" / "summary.json").exists()


def test_strict_legacy_summary_persistence_failure_is_fatal(
    tmp_path, monkeypatch, capsys
):
    tc_file = tmp_path / "passing.yaml"
    tc_file.write_text(
        json.dumps({"name": "PASSING", "steps": [{"action": "wait"}]}),
        encoding="utf-8",
    )
    attempted_contexts = []
    real_reporter = cli.Reporter

    class StrictADB(_ConnectedADB):
        def __init__(self, *, strict_shell=False):
            assert strict_shell is True

    class FailingSummaryReporter(real_reporter):
        def write_summary_json(self):
            attempted_contexts.append((self.contract_mode, self.run_status))
            raise OSError("simulated disk full")

    class PassingRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run_step(self, step, *args, **kwargs):
            return StepResult(action=step["action"], passed=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", StrictADB)
    monkeypatch.setattr(cli, "ActionRunner", PassingRunner)
    monkeypatch.setattr(cli, "Reporter", FailingSummaryReporter)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260722T010006Z",
                contract_mode="legacy",
                serial=None,
                strict_shell=True,
            )
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert attempted_contexts == [("legacy", "COMPLETED")]
    assert "ERROR:" in captured.err
    assert "summary.json" in captured.err


def test_strict_device_info_failure_is_preexecution_without_summary(
    tmp_path, monkeypatch, capsys
):
    tc_file = tmp_path / "unused.yaml"
    tc_file.write_text(
        json.dumps({"name": "UNUSED", "steps": [{"action": "wait"}]}),
        encoding="utf-8",
    )
    runner_calls = []

    class FailingInfoADB:
        def __init__(self, *, strict_shell=False):
            assert strict_shell is True

        def is_connected(self):
            return True

        def get_device_info(self):
            raise RuntimeError("device info denied")

    def forbidden_runner(*args, **kwargs):
        runner_calls.append((args, kwargs))
        raise AssertionError("runner must not be constructed")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "ADB", FailingInfoADB)
    monkeypatch.setattr(cli, "ActionRunner", forbidden_runner)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(
            SimpleNamespace(
                tc_files=[str(tc_file)],
                run_id="20260722T010007Z",
                contract_mode="legacy",
                serial=None,
                strict_shell=True,
            )
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert runner_calls == []
    assert "ERROR:" in captured.err
    assert not (tmp_path / "reports" / "20260722T010007Z" / "summary.json").exists()


def test_primary_corpus_host_preflight_matches_declared_metadata():
    paths = tuple(ROOT / relative for relative in TASK5_CORPUS)
    assert len(paths) == 30
    assert all(path.is_file() for path in paths)

    report = cli.host_preflight(paths, "canonical")

    assert [entry.path for entry in report.verdicts] == list(paths)
    assert not any(
        reason.startswith("CANONICAL_LOAD_OR_VALIDATION_ERROR")
        for entry in report.verdicts
        for reason in entry.reasons
    )
    for path, entry in zip(paths, report.verdicts):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        metadata = raw.get("metadata") or {}
        declared_blocking = (
            metadata.get("runnable") is not True
            or bool(metadata.get("runnable_reason"))
            or metadata.get("has_unresolved_params") is True
            or any(
                step.get("compile_status") == "UNRESOLVED_PARAMS"
                or bool(step.get("_unresolved_params"))
                for step in raw.get("steps", [])
                if isinstance(step, dict)
            )
        )
        assert entry.passed is (not declared_blocking), path
