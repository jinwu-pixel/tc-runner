# BUG-23025 래퍼 실집계 검증 — summary.txt 가 source of truth / PASS 합성 0 / INFRA_FAILURE fail-closed
import os
import subprocess

import pytest

from tests.base_test import InfraFailure
from tests.bug_23025_harness import (
    Bug23025Harness,
    SummaryParseError,
    parse_harness_summary,
    resolve_bash,
)

FAKE_BASH = "X:/fake/Git/bin/bash.exe"


def make_config(tmp_path, count=3):
    return {
        "run_dir": str(tmp_path / "run"),
        "repeat": count,
        "iter_gap": 0,
        "bug_23025": {"scenarios": "basic", "count": count},
    }


def summary_text(rows, total):
    """하니스 print_summary 포맷 재현 (tee 산출물)."""
    lines = [
        "",
        "================= 검증 요약 (BUG #23025) =================",
        "시나리오          횟수     PASS     WARN     FAIL",
        "---------------------------------------------------------",
    ]
    for name, c, p, w, f in rows:
        lines.append("%-12s %8s %8s %8s %8s" % (name, c, p, w, f))
    lines.append("---------------------------------------------------------")
    tc, tp, tw, tf = total
    lines.append("%-12s %8s %8s %8s %8s" % ("합계", tc, tp, tw, tf))
    lines += ["", "산출물:", "  - 결과 CSV    : x", "", "[판정] x",
              "========================================================="]
    return "\n".join(lines) + "\n"


def write_run_dir(out_root, rows=None, total=None, csv_rows=None, with_summary=True,
                  summary_raw=None, csv_raw=None, with_csv=True):
    run_dir = os.path.join(out_root, "run_20260612_010101")
    os.makedirs(run_dir, exist_ok=True)
    if with_summary:
        text = summary_raw if summary_raw is not None else summary_text(rows, total)
        with open(os.path.join(run_dir, "summary.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    if with_csv:
        if csv_raw is not None:
            csv_text = csv_raw
        else:
            csv_lines = ["scenario,index,level,reason,artifact_dir"]
            for row in (csv_rows or []):
                csv_lines.append(",".join(row))
            csv_text = "\n".join(csv_lines) + "\n"
        with open(os.path.join(run_dir, "results.csv"), "w", encoding="utf-8") as f:
            f.write(csv_text)
    return run_dir


def fake_harness(monkeypatch, rc=0, builder=None):
    """하니스 subprocess 호출을 가짜로 대체. builder(cmd) 가 산출물 생성."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if builder:
            builder(cmd)
        return subprocess.CompletedProcess(cmd, rc)

    monkeypatch.setattr("tests.bug_23025_harness.subprocess.run", fake_run)
    monkeypatch.setattr("tests.bug_23025_harness.resolve_bash", lambda configured=None: FAKE_BASH)
    return calls


def out_root_from_cmd(cmd):
    return cmd[cmd.index("-o") + 1]


def statuses(results):
    return [s for s, _, _ in results]


# ---------- parse_harness_summary ----------

def test_parse_summary_ok(tmp_path):
    run_dir = write_run_dir(str(tmp_path), rows=[("basic", 3, 1, 1, 1)], total=(3, 1, 1, 1))
    rows, total = parse_harness_summary(os.path.join(run_dir, "summary.txt"))
    assert rows == [{"name": "basic", "count": 3, "pass": 1, "warn": 1, "fail": 1}]
    assert total == {"count": 3, "pass": 1, "warn": 1, "fail": 1}


def test_parse_summary_row_internal_mismatch_raises(tmp_path):
    # count(3) != pass+warn+fail(2)
    run_dir = write_run_dir(str(tmp_path), rows=[("basic", 3, 1, 0, 1)], total=(3, 1, 0, 1))
    with pytest.raises(SummaryParseError):
        parse_harness_summary(os.path.join(run_dir, "summary.txt"))


def test_parse_summary_grand_total_mismatch_raises(tmp_path):
    # 시나리오 합 (3,1,1,1) != 합계 행 (3,3,0,0)
    run_dir = write_run_dir(str(tmp_path), rows=[("basic", 3, 1, 1, 1)], total=(3, 3, 0, 0))
    with pytest.raises(SummaryParseError):
        parse_harness_summary(os.path.join(run_dir, "summary.txt"))


def test_parse_summary_garbage_raises(tmp_path):
    run_dir = write_run_dir(str(tmp_path), with_summary=True, summary_raw="broken\nnonsense\n")
    with pytest.raises(SummaryParseError):
        parse_harness_summary(os.path.join(run_dir, "summary.txt"))


# ---------- run() 실집계 ----------

def test_run_real_aggregation_from_summary(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(
            out_root_from_cmd(cmd),
            rows=[("basic", 3, 1, 1, 1)], total=(3, 1, 1, 1),
            csv_rows=[("basic", "2", "WARN", "blank suspect", "a/w1"),
                      ("basic", "3", "FAIL", "focus null", "a/f1")],
        )

    fake_harness(monkeypatch, rc=1, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 1
    assert st.count("WARN") == 1
    assert st.count("FAIL") == 1
    assert "INFRA_FAILURE" not in st
    warn_row = [r for r in res if r[0] == "WARN"][0]
    assert "blank suspect" in warn_row[1]
    assert warn_row[2] == "a/w1"


def test_run_missing_run_dir_is_infra_zero_pass(monkeypatch, tmp_path):
    fake_harness(monkeypatch, rc=0, builder=None)  # 산출물 없음
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_missing_summary_is_infra_zero_pass(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), with_summary=False)

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_broken_summary_is_infra_zero_pass(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), summary_raw="garbage\n")

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_exit_code_summary_mismatch_appends_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 2, 2, 0, 0)], total=(2, 2, 0, 0))

    fake_harness(monkeypatch, rc=1, builder=builder)  # summary 는 전부 PASS 인데 exit 1
    res = Bug23025Harness(make_config(tmp_path, count=2)).run()
    st = statuses(res)
    assert st.count("PASS") == 2
    assert "INFRA_FAILURE" in st


def test_run_csv_summary_contradiction_is_infra_zero_pass(monkeypatch, tmp_path):
    def builder(cmd):
        # summary 는 FAIL 1 인데 results.csv 에 상세 행 없음 → 증거 모순
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 1, 1, 1)], total=(3, 1, 1, 1),
                      csv_rows=[])

    fake_harness(monkeypatch, rc=1, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_zero_iterations_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[], total=(0, 0, 0, 0))

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_harness_execution_exception_is_infra(monkeypatch, tmp_path):
    def fake_run(cmd, **kw):
        raise OSError("bash not found")

    monkeypatch.setattr("tests.bug_23025_harness.subprocess.run", fake_run)
    monkeypatch.setattr("tests.bug_23025_harness.resolve_bash", lambda configured=None: FAKE_BASH)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st == ["INFRA_FAILURE"]


# ---------- P1-1: 요청 시나리오·count 계약 (순서·중복 포함 정확 대조) ----------

def test_run_ignored_scenario_is_infra_zero_pass(monkeypatch, tmp_path):
    """하니스가 미등록 시나리오를 무시해도 성공 위장 금지 — 요청 집합과 정확 대조."""
    def builder(cmd):
        # 요청은 basic,bogus 인데 summary 에는 basic 만 (하니스 warn 후 무시 동작 재현)
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0))

    fake_harness(monkeypatch, rc=0, builder=builder)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["scenarios"] = "basic,bogus"
    res = Bug23025Harness(cfg).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_scenario_order_mismatch_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd),
                      rows=[("basic", 3, 3, 0, 0), ("toggle", 3, 3, 0, 0)],
                      total=(6, 6, 0, 0))

    fake_harness(monkeypatch, rc=0, builder=builder)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["scenarios"] = "toggle,basic"  # summary 와 순서 다름
    res = Bug23025Harness(cfg).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_row_count_contract_mismatch_is_infra(monkeypatch, tmp_path):
    """완화된 <= 검사 금지 — 각 행 count == 요청 count 정확 일치."""
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 2, 2, 0, 0)], total=(2, 2, 0, 0))

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path, count=3)).run()  # 요청 3 vs 실행 2
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_zero_count_request_is_infra_without_launch(monkeypatch, tmp_path):
    """count <= 0 요청은 하니스 실행 전 차단."""
    calls = fake_harness(monkeypatch, rc=0, builder=None)
    res = Bug23025Harness(make_config(tmp_path, count=0)).run()
    assert statuses(res) == ["INFRA_FAILURE"]
    assert calls == [], "하니스를 실행하지 않아야 함"


def test_run_records_resolved_bash_path(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0))

    calls = fake_harness(monkeypatch, rc=0, builder=builder)
    cfg = make_config(tmp_path)
    res = Bug23025Harness(cfg).run()
    assert statuses(res).count("PASS") == 3
    assert calls[0][0] == FAKE_BASH, "bare 'bash' 의존 금지 — resolved 경로 사용"
    rec = os.path.join(cfg["run_dir"], "bash_resolved.txt")
    assert os.path.isfile(rec)
    assert FAKE_BASH in open(rec, encoding="utf-8").read()


# ---------- Track B-1: extra_args 예약 옵션 차단 ----------

@pytest.mark.parametrize("bad_args", [
    ["-s", "OTHER_SERIAL"],
    ["--serial", "OTHER_SERIAL"],
    ["-S", "reboot"],
    ["--scenarios", "reboot"],
    ["-n", "999"],
    ["--count=999"],
    ["-o", "/tmp/elsewhere"],
    ["--out", "/tmp/elsewhere"],
    ["--menu"],
    ["--no-menu"],
    ["--hwkeys", "K1", "-s", "OTHER"],  # 허용 옵션 뒤에 숨은 예약 옵션
])
def test_run_reserved_extra_args_rejected_without_launch(monkeypatch, tmp_path, bad_args):
    calls = fake_harness(monkeypatch, rc=0, builder=None)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["extra_args"] = bad_args
    res = Bug23025Harness(cfg).run()
    assert statuses(res) == ["INFRA_FAILURE"]
    assert calls == [], "예약 옵션 감지 시 하니스 미실행"


def test_run_allowed_extra_args_pass_through(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0))

    calls = fake_harness(monkeypatch, rc=0, builder=builder)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["extra_args"] = ["--hwkeys", "KEYCODE_F1", "--clearxy", "240,700"]
    res = Bug23025Harness(cfg).run()
    assert statuses(res).count("PASS") == 3
    assert "--hwkeys" in calls[0]


# ---------- Track B-1: 빈 토큰·중복 시나리오 fail-closed ----------

@pytest.mark.parametrize("scen", ["basic,,toggle", ",basic", "basic,", " , basic"])
def test_run_empty_scenario_token_is_infra_without_launch(monkeypatch, tmp_path, scen):
    calls = fake_harness(monkeypatch, rc=0, builder=None)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["scenarios"] = scen
    res = Bug23025Harness(cfg).run()
    assert statuses(res) == ["INFRA_FAILURE"]
    assert calls == []


def test_run_duplicate_scenario_request_is_infra_without_launch(monkeypatch, tmp_path):
    """중복 시나리오 요청은 (scenario,index) 순서 복원이 모호 → 사전 거부."""
    calls = fake_harness(monkeypatch, rc=0, builder=None)
    cfg = make_config(tmp_path)
    cfg["bug_23025"]["scenarios"] = "basic,basic"
    res = Bug23025Harness(cfg).run()
    assert statuses(res) == ["INFRA_FAILURE"]
    assert calls == []


# ---------- Track B-1: results.csv (scenario, index) 회차 순서 복원 ----------

def test_run_order_restored_from_csv_index(monkeypatch, tmp_path):
    """실제 회차 순서 보존: 누락 index 만 PASS 복원."""
    def builder(cmd):
        write_run_dir(
            out_root_from_cmd(cmd),
            rows=[("basic", 5, 2, 2, 1)], total=(5, 2, 2, 1),
            csv_rows=[("basic", "1", "WARN", "w1", "a/1"),
                      ("basic", "3", "FAIL", "f3", "a/3"),
                      ("basic", "5", "WARN", "w5", "a/5")],
        )

    fake_harness(monkeypatch, rc=1, builder=builder)
    res = Bug23025Harness(make_config(tmp_path, count=5)).run()
    assert statuses(res) == ["WARN", "PASS", "FAIL", "PASS", "WARN"]
    assert "[basic#1]" in res[0][1]
    assert "[basic#3]" in res[2][1]
    assert res[2][2] == "a/3"


def test_run_csv_index_out_of_range_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 2, 1, 0)], total=(3, 2, 1, 0),
                      csv_rows=[("basic", "9", "WARN", "w", "a/9")])

    fake_harness(monkeypatch, rc=2, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_csv_duplicate_index_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 1, 2, 0)], total=(3, 1, 2, 0),
                      csv_rows=[("basic", "2", "WARN", "w", "a/2"),
                                ("basic", "2", "WARN", "w", "a/2dup")])

    fake_harness(monkeypatch, rc=2, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_csv_unknown_scenario_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 2, 1, 0)], total=(3, 2, 1, 0),
                      csv_rows=[("hwkeys", "1", "WARN", "w", "a/h1")])

    fake_harness(monkeypatch, rc=2, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_restored_counts_recompared_with_summary(monkeypatch, tmp_path):
    """복원 후 재대조: csv 부족으로 PASS 복원 수가 summary pass 와 다르면 INFRA."""
    def builder(cmd):
        # summary: P1/W2 인데 csv 에 WARN 1건만 → 복원 PASS 2 != summary PASS 1
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 1, 2, 0)], total=(3, 1, 2, 0),
                      csv_rows=[("basic", "1", "WARN", "w", "a/1")])

    fake_harness(monkeypatch, rc=2, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


# ---------- B-1 마감: csv level 닫힌 enum + 필수 헤더 검증 ----------

def test_run_unknown_csv_level_is_infra_zero_pass(monkeypatch, tmp_path):
    """level 오타(WARM 등)를 조용히 건너뛰면 PASS 복원으로 위장될 수 있음 → INFRA."""
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0),
                      csv_rows=[("basic", "2", "WARM", "typo level", "a/2")])

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_csv_missing_header_is_infra(monkeypatch, tmp_path):
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0),
                      csv_raw="foo,bar\nx,y\n")

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_missing_csv_file_is_infra_even_all_pass(monkeypatch, tmp_path):
    """하니스는 시작 시 csv 헤더를 반드시 생성 — 파일 부재는 비정상, all-PASS 도 거부."""
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0),
                      with_csv=False)

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    st = statuses(res)
    assert st.count("PASS") == 0
    assert "INFRA_FAILURE" in st


def test_run_header_only_csv_with_all_pass_summary_ok(monkeypatch, tmp_path):
    """헤더만 있는 csv + all-PASS summary 는 정상 (WARN/FAIL 0건이면 상세 행 없음)."""
    def builder(cmd):
        write_run_dir(out_root_from_cmd(cmd), rows=[("basic", 3, 3, 0, 0)], total=(3, 3, 0, 0),
                      csv_rows=[])

    fake_harness(monkeypatch, rc=0, builder=builder)
    res = Bug23025Harness(make_config(tmp_path)).run()
    assert statuses(res) == ["PASS", "PASS", "PASS"]


# ---------- resolve_bash (Git Bash 만 허용, WSL/System32 차단) ----------

def make_bash(tmp_path, *parts):
    p = tmp_path
    for part in parts:
        p = p / part
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"")
    return str(p)


def test_resolve_bash_explicit_config_path(tmp_path):
    p = make_bash(tmp_path, "tools", "Git", "bin", "bash.exe")
    assert resolve_bash(p) == p


def test_resolve_bash_explicit_missing_is_infra(tmp_path):
    with pytest.raises(InfraFailure):
        resolve_bash(str(tmp_path / "nope" / "bash.exe"))


def test_resolve_bash_rejects_system32(monkeypatch, tmp_path):
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    p = make_bash(tmp_path, "Windows", "System32", "bash.exe")  # WSL launcher 위치
    with pytest.raises(InfraFailure):
        resolve_bash(p)


def test_resolve_bash_explicit_nongit_rejected(tmp_path):
    """Track B-1: 명시 bash_path 도 Git 경로 검증 (cygwin/msys 등 거부)."""
    p = make_bash(tmp_path, "cygwin", "bin", "bash.exe")
    with pytest.raises(InfraFailure):
        resolve_bash(p)


@pytest.mark.parametrize("comp", ["notgit", "GitHub", "git-tools", "msys64"])
def test_resolve_bash_substring_lookalikes_rejected(tmp_path, comp):
    """경로 구성요소 정확 일치만 인정 — 부분문자열(notgit/GitHub/git-tools) 통과 금지."""
    p = make_bash(tmp_path, comp, "bin", "bash.exe")
    with pytest.raises(InfraFailure):
        resolve_bash(p)


def test_resolve_bash_explicit_portablegit_accepted(tmp_path):
    p = make_bash(tmp_path, "PortableGit", "bin", "bash.exe")
    assert resolve_bash(p) == p


def test_resolve_bash_auto_finds_git_candidate(monkeypatch, tmp_path):
    p = make_bash(tmp_path, "PF", "Git", "bin", "bash.exe")
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "PF"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "PFX"))
    monkeypatch.setenv("LocalAppData", str(tmp_path / "LAD"))
    assert resolve_bash(None) == p


def test_resolve_bash_path_nongit_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "PF"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "PFX"))
    monkeypatch.setenv("LocalAppData", str(tmp_path / "LAD"))
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    monkeypatch.setattr("tests.bug_23025_harness.shutil.which",
                        lambda name: str(tmp_path / "Windows" / "System32" / "bash.exe"))
    with pytest.raises(InfraFailure):
        resolve_bash(None)


def test_resolve_bash_none_found_is_infra(monkeypatch, tmp_path):
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "PF"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "PFX"))
    monkeypatch.setenv("LocalAppData", str(tmp_path / "LAD"))
    monkeypatch.setattr("tests.bug_23025_harness.shutil.which", lambda name: None)
    with pytest.raises(InfraFailure):
        resolve_bash(None)
