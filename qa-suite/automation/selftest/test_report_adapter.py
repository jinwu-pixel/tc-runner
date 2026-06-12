# summary.json adapter 검증 — tc-runner 기존 계약(schema_version=1) 채택, 신규 포맷 발명 금지
# 기준: tc-runner tests/test_reporter.py 의 bundle summary.json shape 단언과 동일 필드 집합
import json
import re

from report_adapter import (
    SCHEMA_VERSION,
    TOOL_VERSION,
    build_summary_payload,
    new_run_id,
    write_summary_json,
)

TOP_FIELDS = {"schema_version", "tool_version", "run_id", "generated_at",
              "device", "summary", "results"}
RESULT_FIELDS = {"name", "description", "passed", "duration_s", "steps"}
STEP_FIELDS = {"index", "action", "passed", "duration_s", "message", "execution_mode",
               "manual_action", "skip_reason", "paused", "screenshot_path"}


def sample_payload(warn_artifact="logs/a1"):
    return build_summary_payload(
        run_id="20260612T000000Z",
        device={"serial": "SER1"},
        tests_results={
            "bug_23025": [
                ("PASS", "", None),
                ("WARN", "[basic#2] blank suspect", warn_artifact),
                ("SKIP", "fit 제외", None),
            ],
            "all_skip": [("SKIP", "미지원", None)],
            "broken": [("INFRA_FAILURE", "summary 부재", None)],
        },
    )


def test_new_run_id_is_utc_shape():
    assert re.fullmatch(r"\d{8}T\d{6}Z", new_run_id())


def test_schema_version_and_tool_version():
    assert SCHEMA_VERSION == 1
    assert TOOL_VERSION  # 비어 있지 않은 식별 문자열


def test_payload_top_level_contract():
    data = sample_payload()
    assert set(data.keys()) == TOP_FIELDS
    assert data["schema_version"] == 1
    assert data["run_id"] == "20260612T000000Z"
    assert data["generated_at"].endswith("Z")
    assert data["device"] == {"serial": "SER1"}
    assert set(data["summary"].keys()) == {"total", "passed", "skipped", "failed"}


def test_payload_summary_counts():
    s = sample_payload()["summary"]
    # bug_23025: WARN 포함 → failed / all_skip: 전체 SKIP → skipped / broken: INFRA → failed
    assert s["total"] == 3
    assert s["passed"] == 0
    assert s["skipped"] == 1
    assert s["failed"] == 2


def test_payload_results_and_steps_shape():
    data = sample_payload()
    by_name = {r["name"]: r for r in data["results"]}
    assert set(by_name) == {"bug_23025", "all_skip", "broken"}

    r = by_name["bug_23025"]
    assert set(r.keys()) == RESULT_FIELDS
    assert r["passed"] is False
    steps = r["steps"]
    assert [st["index"] for st in steps] == [1, 2, 3], "index 는 1-based"
    for st in steps:
        assert set(st.keys()) == STEP_FIELDS

    assert steps[0]["passed"] is True
    assert steps[0]["message"] == ""

    assert steps[1]["passed"] is False
    assert "blank suspect" in steps[1]["message"]

    assert steps[2]["manual_action"] == "skip"
    assert steps[2]["skip_reason"] == "fit 제외"

    infra_step = by_name["broken"]["steps"][0]
    assert infra_step["passed"] is False
    assert "INFRA_FAILURE" in infra_step["message"]


def test_result_level_semantics_pinned():
    """result-level passed/skipped 의미 고정 (비중복 집계 — legacy Reporter 와 다름, §아래 주의).

    legacy Reporter: skip step 포함 TC 가 passed 와 skipped 양쪽에 계산될 수 있음 (중복).
    qa-suite adapter: 시험당 단일 분류 — all-SKIP → skipped / WARN·FAIL·INFRA 포함 → failed
    / 그 외(PASS, PASS+SKIP 혼합) → passed. 의미 통합은 트랙 B.
    """
    data = sample_payload()
    by_name = {r["name"]: r for r in data["results"]}

    # WARN 포함 → 실패 (사람 확인 전 성공 위장 금지)
    assert by_name["bug_23025"]["passed"] is False
    # all-SKIP → passed False + skipped 로만 집계 (비중복)
    assert by_name["all_skip"]["passed"] is False
    # INFRA → 실패
    assert by_name["broken"]["passed"] is False

    s = data["summary"]
    assert s["passed"] + s["skipped"] + s["failed"] == s["total"], "비중복 집계"

    # PASS+SKIP 혼합 → passed (전량 SKIP 만 skipped)
    mixed = build_summary_payload(
        "20260612T000000Z", {}, {"t": [("PASS", "", None), ("SKIP", "x", None)]})
    assert mixed["results"][0]["passed"] is True
    assert mixed["summary"] == {"total": 1, "passed": 1, "skipped": 0, "failed": 0}


# ---------- P2-4: screenshot 은 실재 파일만 evidence 로 기록 ----------

def test_screenshot_recorded_only_if_file_exists(tmp_path):
    art = tmp_path / "artifacts" / "w1"
    art.mkdir(parents=True)
    (art / "screen.png").write_bytes(b"\x89PNG")
    data = sample_payload(warn_artifact=str(art))
    step = data["results"][0]["steps"][1]
    assert step["screenshot_path"] == str(art).replace("\\", "/") + "/screen.png"


def test_screenshot_missing_file_not_recorded_but_artifact_pointer_kept(tmp_path):
    art = tmp_path / "artifacts" / "w2"
    art.mkdir(parents=True)  # screen.png 없음 (screencap 실패 상황)
    data = sample_payload(warn_artifact=str(art))
    step = data["results"][0]["steps"][1]
    assert step["screenshot_path"] is None, "깨진 링크를 evidence 로 기록 금지"
    assert str(art).replace("\\", "/") in step["message"], "아티팩트 포인터는 message 로 보존"


def test_write_summary_json_bundle_path(tmp_path):
    payload = sample_payload()
    path = write_summary_json(str(tmp_path / "report"), "20260612T000000Z", payload)
    assert path == str(tmp_path / "report" / "20260612T000000Z" / "summary.json")
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["schema_version"] == 1
