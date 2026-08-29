# AppWidget stale-provider 지식·재현 파이프라인 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** BUG27084에서 확인한 AppWidget stale-provider 진단 지식을 개인 메모리·repo 지침·이슈 원장에 누적하고, AT-M140 단말을 exact identity로 결박한 전용 재현 harness와 증거 bundle을 host-first로 구현한 뒤 known-bad/fixed-build A/B까지 단계적으로 검증한다.

**Architecture:** 보편 원칙은 `AGENTS.md`/`CLAUDE.md`, Android 상세 절차는 `docs/appwidget_stale_provider_verification.md`, 사례 상태는 `AT-M140 - Launcher BUG27084/`, 실행 로직은 `scripts/appwidget_stale_provider_repro.py`와 data-only profile로 분리한다. Harness는 `plan` 기본·phase state machine·exact serial/model/fingerprint·immutable APK hash pin·fail-closed evidence writer를 사용한다. 첫 구현은 `src/`, TC schema, validator, `runner_capability.yaml`을 변경하지 않는다.

**Tech Stack:** Python 3, pytest, argparse, dataclasses, pathlib, subprocess/ADB, JSON/JSONL, SHA-256, Markdown, PowerShell 5.1.

**Spec:** `docs/superpowers/specs/2026-08-29-appwidget-stale-provider-knowledge-pipeline-design.md`

## Global Constraints

- 이 계획의 승인은 계획 문서 작성 승인이다. 실제 파일 구현, 단말 mutation, commit, push는 각각 repo 승인 게이트를 따른다.
- Phase 1–2 구현 전 현재 dirty worktree를 `git status --short`로 다시 감사하고 사용자 파일을 보존한다.
- `C:\Users\momen\.codex\memories\MEMORY.md`는 직접 편집하지 않는다. 개인 메모리는 ad-hoc note만 생성한다.
- `AGENTS.md`와 `CLAUDE.md`는 플랫폼명 차이만 유지하고 AppWidget 규칙은 의미상 동일하게 반영한다.
- 여러 단말이 연결돼도 `adb devices -l` 외 모든 per-device 명령은 예를 들어 `adb -s B06201249E00030C shell getprop ro.product.model`처럼 대상 serial을 포함한다.
- known-bad identity는 model `AT-M140`, fingerprint `ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys`, incremental `RY07260901S`다.
- fixed build label은 `AT-M140Z0827U_DAILY_DEV_GMS_849`지만 실제 fingerprint는 미확보다. fingerprint를 추정하거나 known-bad profile을 재사용하지 않는다.
- `bind`, `arm`, `trigger`, `restore`, reboot, install/uninstall, data clear는 실행마다 별도 사용자 승인을 받는다.
- 자동 다중-cycle `campaign` 명령은 구현하지 않는다.
- 각 코드 task는 RED → 최소 구현 → GREEN → 관련 회귀 순서로 실행한다.
- 아래 commit 단계는 구현 단위를 표시하기 위한 체크포인트다. 사용자가 별도로 commit을 명시 승인한 경우에만 exact path를 stage/commit하며, 승인 전에는 unstaged 상태로 멈춘다. push는 이 계획 범위가 아니다.

---

## Phase 1 — 지식·상태 정렬

### Task 1: 개인 메모리 ad-hoc note를 추가한다

**Files:**

- Create: `C:\Users\momen\.codex\memories\extensions\ad_hoc\notes\20260829-appwidget-stale-provider-state-equivalence.md`
- Read-only reference: `AT-M140 - Launcher BUG27084/RESULT_2026-08-28.md`
- Read-only reference: `AT-M140 - Launcher BUG27084/RESULT_2026-08-29.md`

**Interfaces:**

- Memory scope: `tc-runner / Android AppWidget stale-provider diagnosis`
- Generalized rules only; serial, coordinates, widget IDs, temporary APK paths are excluded.

- [ ] **Step 1: Confirm the generated memory file is not edited**

Run:

```powershell
git -C C:\Users\momen\.codex\memories status --short
Get-Item -LiteralPath C:\Users\momen\.codex\memories\MEMORY.md | Format-List FullName,Length,LastWriteTime
```

Expected: current memory repo state is recorded; no write is made to `MEMORY.md`.

- [ ] **Step 2: Create the ad-hoc note with exact reusable rules**

Write this content:

```markdown
# Android AppWidget stale-provider: state-equivalence 진단

- scope: tc-runner / Android AppWidget stale-provider diagnosis
- source case: BUG27084, AT-M140 Launcher, 2026-08-28~29

## Reusable rules

1. `pm clear`, force-stop, disable, package replace, uninstall/reinstall은 서로 다른 package lifecycle이다.
2. 명령 목록이 비슷한지보다 Package / AppWidgetService / Launcher 내부 상태가 동등한지를 먼저 판정한다.
3. provider registry 존재와 실제 widget instance binding 존재를 분리해 기록한다.
4. inactive HOME을 유지한 채 provider 앱을 uninstall/reinstall하면 Launcher DB record만 남고 AppWidget binding이 사라지는 stale 상태가 만들어질 수 있다.
5. stale 상태를 증명하지 못한 비재현은 fixed `runtime PASS`가 아니라 `runtime precondition FAIL`이다.
6. destructive ADB는 exact serial·model·fingerprint를 결박하고 대상 외 연결 단말에 명령하지 않는다.
7. 재현 후 HOME role, stale-state 보존 여부, 잔존 mutation, 일반모드 전환 위험을 issue `RESUME.md`에 남긴다.

## Evidence boundary

- 직접 관찰된 root-cause 범위: Launcher DB stale record와 AppWidgetService binding 부재의 불일치.
- 모든 3rd-party widget update가 위험하다고 일반화하지 않는다.
- exact fixed build에서 동일 stale precondition의 역방향이 끝나기 전에는 fixed-build `runtime PASS`를 사용하지 않는다.
```

- [ ] **Step 3: Verify content and scope**

Run:

```powershell
rg -n "state-equivalence|runtime precondition FAIL|provider registry|RESUME.md|B06201249E00030C|480.800|widget id" C:\Users\momen\.codex\memories\extensions\ad_hoc\notes\20260829-appwidget-stale-provider-state-equivalence.md
```

Expected: generalized terms are present; serial, viewport coordinate, transient widget ID are absent.

- [ ] **Step 4: Do not commit generated/personal memory as part of tc-runner**

Expected: no tc-runner staging or commit action for this file.

### Task 2: repo 지침과 상세 플레이북을 contract test로 결박한다

**Files:**

- Create: `tests/test_appwidget_guidance_contract.py`
- Create: `docs/appwidget_stale_provider_verification.md`
- Modify: `docs/tc_patterns.md:1-53`
- Modify: `AGENTS.md:194-264,498-525`
- Modify: `CLAUDE.md:194-264,498-525`

**Interfaces:**

- Guidance markers: `package lifecycle`, `state-equivalence`, `runtime precondition FAIL`, `axis applicability`
- Detailed SoT: `docs/appwidget_stale_provider_verification.md`
- AGENTS/CLAUDE AppWidget paragraphs must match exactly.

- [ ] **Step 1: Write the failing guidance contract test**

Add:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_appwidget_playbook_is_linked_and_complete():
    playbook = _text("docs/appwidget_stale_provider_verification.md")
    patterns = _text("docs/tc_patterns.md")
    for heading in (
        "## 1. 판정 경계",
        "## 2. 3층 상태 모델",
        "## 3. state-equivalence gate",
        "## 4. lifecycle trigger matrix",
        "## 5. fixed-build A/B",
        "## 6. Google Go 회귀",
        "## 7. 단말 안전과 복구",
        "## 8. 증거 계약",
    ):
        assert heading in playbook
    assert "docs/appwidget_stale_provider_verification.md" in patterns


def test_agents_and_claude_share_appwidget_guidance_markers():
    agents = _text("AGENTS.md")
    claude = _text("CLAUDE.md")
    markers = (
        "package lifecycle 분리",
        "state-equivalence gate",
        "runtime precondition FAIL",
        "axis applicability",
        "BUG-27084 AppWidget stale-provider",
    )
    for marker in markers:
        assert marker in agents
        assert marker in claude
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_appwidget_guidance_contract.py -q
```

Expected: FAIL because the playbook and markers do not yet exist.

- [ ] **Step 3: Create the detailed AppWidget playbook**

The document must include these exact sections and decisions:

```markdown
# AppWidget stale-provider 검증 플레이북

## 1. 판정 경계
- `pm clear` 비재현은 stale binding을 만들지 못하면 `runtime precondition FAIL`이다.
- exact fixed build에서 동등한 stale state를 증명하기 전에는 fixed `runtime PASS`를 쓰지 않는다.

## 2. 3층 상태 모델
| 층 | 권위 관찰 | 필수 필드 |
| Package | `dumpsys package` | package/version/signature/UID/stopped/notLaunched |
| AppWidgetService | `dumpsys appwidget` | provider_registered/widget_id/host/RemoteViews |
| Launcher | HOME role/log/crash/UI | stale record evidence/render/process stability |

## 3. state-equivalence gate
1. 정상 binding과 RemoteViews 존재
2. Launcher data 유지
3. 과거 widget id binding 소실
4. 동일 package/signature 재설치
5. General HOME이 stale record를 소비할 조건 유지

Launcher stale evidence는 `DIRECT_DB`, `LOADER_LOG`, `PRESERVED_PREUPGRADE`, `INFERRED_ONLY`로 기록한다. Fixed-build 판정은 처음 세 등급 중 하나를 요구한다.

## 4. lifecycle trigger matrix
`pm clear + force-stop + reboot`, uninstall/reinstall, `install-multiple -r`, version update, disable/enable, provider remove/rename, data-maintain OTA를 독립 fixture로 비교한다.

## 5. fixed-build A/B
stale precondition, HOME render, Launcher process stable, line185/88 NPE 0, safe placeholder/cleanup, normal widget update를 모두 확인한다.

## 6. Google Go 회귀
content description/DPAD focus, normal RemoteViews update, focus flag reset, pending null path, 일반 widget tap/update/resize를 stale-provider verdict와 분리한다.

## 7. 단말 안전과 복구
exact serial/model/fingerprint, 480×800 viewport, current HOME role, APK hash를 mutation 전에 확인한다. 기본 종료 상태는 Simple HOME 또는 clean General HOME이다. Preserve는 명시 승인과 `RESUME.md` 갱신이 필요하다.

## 8. 증거 계약
UTC run ID, UTC/KST event time, package/appwidget/role/build/crash snapshots, screenshots, `run.json`, `events.jsonl`, `inputs.json`, `result.json`, `verification.txt`, `evidence_sha256.txt`를 보존한다.
```

Expand each section with the design spec's exact allowed conclusions, lifecycle row purposes, verdict vocabulary, and evidence fields. Do not copy AT-M140 coordinates or serial into this generic document.

- [ ] **Step 4: Update `docs/tc_patterns.md` with a short link only**

Change the introduction to reference both `AGENTS.md` and `CLAUDE.md`, add an `AppWidget stale-provider` section linking to the detailed playbook, and update the improvement hook to point to both guidance files.

- [ ] **Step 5: Add universal rules to both guidance files**

Apply the same AppWidget text to both files:

- §4.1: add `package lifecycle 분리` for clear/force-stop/disable/package replace/uninstall-reinstall.
- §4.2: add `state-equivalence gate`, `runtime precondition FAIL`, and `axis applicability` for non-carrier domains.
- §4.6: add one-line case `BUG-27084 AppWidget stale-provider` with SimpleClock 3/3, developer procedure 0/3 precondition failure, root-cause scope, and fixed-build blocker.
- §8.2: add a 2026-08-29 row with status `applied` because the user approved the design and the body change is applied in the same unit.

- [ ] **Step 6: Run contract and mirror spot-checks**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_appwidget_guidance_contract.py -q
rg -n "package lifecycle 분리|state-equivalence gate|runtime precondition FAIL|axis applicability|BUG-27084 AppWidget stale-provider" AGENTS.md CLAUDE.md
```

Expected: contract tests PASS; each marker occurs in both guidance files.

- [ ] **Step 7: Commit gate — only after separate explicit approval**

Exact stage set:

```powershell
git add -- tests/test_appwidget_guidance_contract.py docs/appwidget_stale_provider_verification.md docs/tc_patterns.md AGENTS.md CLAUDE.md
git status --short
git commit -m "docs: codify AppWidget stale-state diagnosis"
```

Without commit approval: stop after verification and leave the exact files unstaged.

### Task 3: BUG27084 issue 원장과 APK provenance를 보강한다

**Files:**

- Create: `tests/test_bug27084_evidence_contract.py`
- Create: `AT-M140 - Launcher BUG27084/BUG_LOG.md`
- Create: `AT-M140 - Launcher BUG27084/RESUME.md`
- Create: `AT-M140 - Launcher BUG27084/MENU_TREE.md`
- Modify: `AT-M140 - Launcher BUG27084/RESULT_2026-08-28.md`
- Modify: `AT-M140 - Launcher BUG27084/RESULT_2026-08-29.md`
- Modify: `AT-M140 - Launcher BUG27084/evidence/20260829T003741KST_nonweather_controls/result.json`
- Read-only source: `AT-M140 - Launcher BUG27084/evidence/20260828T221502KST_widget_generality/evidence_sha256.txt`

**Interfaces:**

- Issue status: diagnosis `OBSERVED`, lifecycle `IN_PROGRESS`
- Current blocker: exact fixed build unavailable
- Immutable SimpleClock source manifest SHA-256: `53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8`
- Split APK SHA-256 values: base `BC7CFFF4E2A441864B35B9064EA6B4E0B3D907FCAA788C4F83EAA7F0152F0B29`, ko `5711AF8D4E523EC7768C6DBCE0D2E480AFA36B0AFB638B0D1A85BB5E32C94003`, tvdpi `3C03AF1D7B647A389FEA8F96EAF181B34B0F0DED077A0C0B49B8ED951061C92E`

- [ ] **Step 1: Write the failing issue/evidence contract test**

Add tests that:

```python
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ISSUE = ROOT / "AT-M140 - Launcher BUG27084"
BUNDLE = ISSUE / "evidence" / "20260829T003741KST_nonweather_controls"
SOURCE = ISSUE / "evidence" / "20260828T221502KST_widget_generality"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_issue_ledger_files_and_status_exist():
    for name in ("BUG_LOG.md", "RESUME.md", "MENU_TREE.md"):
        assert (ISSUE / name).is_file()
    bug_log = (ISSUE / "BUG_LOG.md").read_text(encoding="utf-8")
    assert "OBSERVED" in bug_log
    assert "IN_PROGRESS" in bug_log
    assert "AT-M140Z0827U_DAILY_DEV_GMS_849" in bug_log


def test_result_pins_simpleclock_source_manifest_and_splits():
    result = json.loads((BUNDLE / "result.json").read_text(encoding="utf-8"))
    provenance = result["input_provenance"]
    assert provenance["source_manifest_sha256"] == _sha(SOURCE / "evidence_sha256.txt")
    expected = {item["name"]: item["sha256"] for item in provenance["simpleclock_split_apks"]}
    for name, digest in expected.items():
        assert _sha(SOURCE / "simpleclock_apk" / name) == digest


def test_result_series_cross_links_both_directions():
    first = (ISSUE / "RESULT_2026-08-28.md").read_text(encoding="utf-8")
    second = (ISSUE / "RESULT_2026-08-29.md").read_text(encoding="utf-8")
    assert "RESULT_2026-08-29.md" in first
    assert "RESULT_2026-08-28.md" in second
```

- [ ] **Step 2: Run the contract to verify RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_bug27084_evidence_contract.py -q
```

Expected: FAIL because ledger files and `input_provenance` are absent.

- [ ] **Step 3: Create `BUG_LOG.md` with current state only**

Use the repo §6.4 shape:

```markdown
# BUG LOG — AT-M140 Launcher BUG27084

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| BUG27084 | Launcher/AppWidget | OBSERVED | IN_PROGRESS | stale Launcher record가 소실된 AppWidget binding을 읽을 때 line185→88 NPE | — | RESULT_2026-08-29.md |

## BUG27084
- 기능 영역: Launcher / AppWidget pending host view
- 진단 상태: OBSERVED
- 이슈 상태: IN_PROGRESS
- 단말: AT-M140
- 앱: Weather 7.7.8/7.8.2, AccuWeather, SimpleClock 2.1.6
- 요약: 특정 날씨앱 한정 가설은 기각. 직접 관찰 범위는 Launcher DB stale record ↔ AppWidgetService binding 부재다.
- 기대 결과: missing provider/pending widget을 안전하게 placeholder 처리하거나 stale record 정리
- 실제 결과: known-bad `RY07260901S`에서 SimpleClock 독립 fixture 3/3 line185→88 NPE
- 재현 절차: General widget bind → Simple HOME → uninstall/reinstall 동일 APK → old widget id 소실 확인 → General HOME
- 증거: RESULT_2026-08-28.md, RESULT_2026-08-29.md, evidence/20260829T003741KST_nonweather_controls/result.json
- 관련 TC: —
- 현재 blocker: exact fixed build `AT-M140Z0827U_DAILY_DEV_GMS_849` 미확보
- 정정 이력: 2026-08-29 SimpleClock 유효 binding 절차 확인 후 특정 날씨앱 한정 가설 기각

## 세션 결과
- 실행일: 2026-08-29
- 단말: AT-M140
- 앱: SimpleClock / Weather
- 범위: 비날씨 양성 대조군 3회, 개발사 절차 음성 대조군 3회
- PASS: —
- 신규 발견: SimpleClock 3/3 BUG-GAP observed; 개발사 절차는 stale precondition 0/3
- 변경·정정: 2026-08-28 SimpleClock 판정 제외를 정정
- 다음 확인 항목: exact fixed build state-equivalent A/B와 Google Go 회귀
```

- [ ] **Step 4: Create `RESUME.md` as the safe restart guard**

Record exact current state:

- AT-M140 serial `B06201249E00030C`
- model/fingerprint/incremental from Global Constraints
- ODIN2 `f2bfcc3c` is connected but untouched
- final HOME role `com.hnlens.simplemode`
- current stale SimpleClock state is preserved if still confirmed by read-only capture; otherwise state is marked not confirmed
- switching to General HOME may re-enter the Launcher crash loop
- Weather data-clear and prior package lifecycle mutations are listed
- next read-only action is identity/role/package/appwidget capture
- every device mutation requires approval

- [ ] **Step 5: Create the issue-specific `MENU_TREE.md`**

Use:

```text
Simple HOME (`com.hnlens.simplemode`)
  └─ SwitchModeActivity (`com.hnlens.simplemode/.ui.home.SwitchModeActivity`) → General HOME
General HOME (`com.hnlens.launcher3/com.android.launcher3.uioverrides.QuickstepLauncher`)
  ├─ long-press → Widget picker
  │   └─ search → provider group → widget preview → drag-and-drop → provider setup/confirm
  └─ SwitchModeActivity → Simple HOME
```

Add the 480×800 viewport restriction and state that exact coordinates live only in the harness profile.

- [ ] **Step 6: Add immutable provenance to `result.json`**

Add this top-level object without changing existing diagnosis counts:

```json
"input_provenance": {
  "source_bundle": "../20260828T221502KST_widget_generality",
  "source_manifest": "evidence_sha256.txt",
  "source_manifest_sha256": "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8",
  "simpleclock_split_apks": [
    {"name": "base.apk", "size": 23871293, "sha256": "BC7CFFF4E2A441864B35B9064EA6B4E0B3D907FCAA788C4F83EAA7F0152F0B29"},
    {"name": "split_config.ko.apk", "size": 33177, "sha256": "5711AF8D4E523EC7768C6DBCE0D2E480AFA36B0AFB638B0D1A85BB5E32C94003"},
    {"name": "split_config.tvdpi.apk", "size": 167375, "sha256": "3C03AF1D7B647A389FEA8F96EAF181B34B0F0DED077A0C0B49B8ED951061C92E"}
  ]
}
```

- [ ] **Step 7: Cross-link the RESULT series**

- `RESULT_2026-08-28.md`: add a correction link to `RESULT_2026-08-29.md` without rewriting the historical body.
- `RESULT_2026-08-29.md`: link back to the prior result and name the pinned source manifest/split hashes.

- [ ] **Step 8: Run the contract and JSON parser**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_bug27084_evidence_contract.py -q
Get-Content -Raw -LiteralPath 'AT-M140 - Launcher BUG27084\evidence\20260829T003741KST_nonweather_controls\result.json' | ConvertFrom-Json | Out-Null
```

Expected: tests PASS and JSON parses.

- [ ] **Step 9: Commit gate — only after separate explicit approval**

Stage only the seven issue/doc paths and the contract test explicitly; do not broad-add the evidence tree.

---

## Phase 2 — host-only harness

### Task 4: profile, pure parsers, and adb-free `plan` CLI를 TDD로 만든다

**Files:**

- Create: `scripts/appwidget_stale_provider_profiles.py`
- Create: `scripts/appwidget_stale_provider_repro.py`
- Create: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```python
parse_adb_devices(stdout: str) -> dict[str, str]
parse_package_state(stdout: str, package: str) -> PackageState
parse_appwidget_state(stdout: str, component: str, launcher_package: str) -> AppWidgetState
parse_home_role(stdout: str, profile: dict) -> str
parse_crash_signature(stdout: str) -> CrashSignature
validate_profile(profile: dict) -> list[str]
render_plan(profile: dict) -> list[dict[str, object]]
main(argv: list[str] | None = None) -> int
```

- [ ] **Step 1: Write import/profile/parser/plan tests first**

Add tests named `test_import_has_no_subprocess_side_effect`, `test_profile_has_exact_known_bad_identity_and_apk_pins`, `test_parse_adb_devices_keeps_only_device_state`, `test_package_parser_extracts_version_signature_uid_and_flags`, `test_appwidget_parser_separates_registered_provider_from_bound_widget`, `test_appwidget_parser_detects_old_widget_id_absence_after_reinstall`, `test_home_role_parser_distinguishes_simple_and_general`, `test_crash_parser_requires_both_line_185_and_line_88`, `test_plan_is_default_and_adb_free`, and `test_unknown_profile_returns_exit_2`.

Use transcript excerpts copied into test string literals from the existing BUG27084 evidence; do not read live ADB in tests.

- [ ] **Step 2: Run focused tests to verify RED**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_appwidget_stale_provider_repro.py -q
```

Expected: FAIL because both script files are absent.

- [ ] **Step 3: Add the data-only known-bad profile**

Profile key: `AT_M140_BUG27084_KNOWN_BAD_V1`.

Required exact values:

```python
PROFILES = {
    "AT_M140_BUG27084_KNOWN_BAD_V1": {
        "model": "AT-M140",
        "fingerprint": "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys",
        "incremental": "RY07260901S",
        "viewport": (480, 800),
        "simple_home": "com.hnlens.simplemode",
        "general_home": "com.hnlens.launcher3",
        "general_home_activity": "com.hnlens.launcher3/com.android.launcher3.uioverrides.QuickstepLauncher",
        "switch_activity": "com.hnlens.simplemode/.ui.home.SwitchModeActivity",
        "launcher_package": "com.hnlens.launcher3",
        "app": {
            "package": "com.winson.simpleclock",
            "provider": "com.winson.simpleclock/com.winson.simpleclock.widget.SimpleClockWidgetProvider",
            "version_name": "2.1.6",
            "version_code": 216,
            "signature_token": "498de32a",
            "source_bundle": "AT-M140 - Launcher BUG27084/evidence/20260828T221502KST_widget_generality",
            "source_manifest_sha256": "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8",
            "splits": (
                ("base.apk", 23871293, "BC7CFFF4E2A441864B35B9064EA6B4E0B3D907FCAA788C4F83EAA7F0152F0B29"),
                ("split_config.ko.apk", 33177, "5711AF8D4E523EC7768C6DBCE0D2E480AFA36B0AFB638B0D1A85BB5E32C94003"),
                ("split_config.tvdpi.apk", 167375, "3C03AF1D7B647A389FEA8F96EAF181B34B0F0DED077A0C0B49B8ED951061C92E"),
            ),
        },
        "ui": {
            "home_long_press": (240, 450, 1200),
            "widget_menu_text": "위젯",
            "widget_search_text": "검색",
            "provider_label": "SimpleClock",
            "widget_drag": (240, 560, 240, 240, 1200),
            "provider_confirm_text": "OK",
            "provider_confirm_fallback": (346, 741),
        },
        "evidence_root": "AT-M140 - Launcher BUG27084/evidence",
    }
}
```

Coordinates are evidence-derived candidates and are never used unless the live 480×800 viewport and selector gates match. Device pilot Task 12 must verify the selector/coordinate pairing before mutation.

- [ ] **Step 4: Implement dataclasses and pure parsers**

Use immutable dataclasses:

```python
@dataclass(frozen=True)
class PackageState:
    package: str
    version_name: str | None
    version_code: int | None
    signature_token: str | None
    uid: int | None
    stopped: bool | None
    not_launched: bool | None


@dataclass(frozen=True)
class WidgetBinding:
    widget_id: int
    provider_component: str
    host_package: str
    remote_views_present: bool


@dataclass(frozen=True)
class AppWidgetState:
    provider_registered: bool
    provider_uid: int | None
    bindings: Sequence[WidgetBinding]
```

Parsing rules:

- Provider registry lines and `Widgets:` blocks are parsed independently.
- `widget_bound` is true only when component, Launcher host, widget id, and `RemoteViews` match.
- `RemoteViews: null` is false; registry-only provider is not a binding.
- Crash signature requires the same crash record to contain `LauncherAppWidgetHostView.java:185` and `PendingAppWidgetHostView.java:88`.

- [ ] **Step 5: Implement an adb-free default `plan` command**

CLI grammar:

```text
appwidget_stale_provider_repro.py [plan]
  --profile AT_M140_BUG27084_KNOWN_BAD_V1
```

No subcommand is normalized to `plan`. `plan` prints JSON containing phases, mutation flags, required approvals, profile identity, source manifest digest, and `adb=OFF`. Import and plan must never invoke subprocess.

- [ ] **Step 6: Run focused tests to GREEN**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_appwidget_stale_provider_repro.py -q
```

Expected: all Task 4 tests PASS.

- [ ] **Step 7: Commit gate — only after separate explicit approval**

Exact stage set: the two scripts and one test file only.

### Task 5: exact-device preflight와 phase state machine을 구현한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```python
class Phase(str, Enum):
    BASELINE_CAPTURED = "BASELINE_CAPTURED"
    BOUND_GENERAL = "BOUND_GENERAL"
    SAFE_SIMPLE = "SAFE_SIMPLE"
    STALE_ARMED = "STALE_ARMED"
    TRIGGERED_BUG = "TRIGGERED_BUG"
    TRIGGERED_FIXED = "TRIGGERED_FIXED"
    RESTORED_SAFE = "RESTORED_SAFE"
```

`AdbTransport.list_devices()` returns `dict[str, str]`; `AdbTransport.run_target(args: Sequence[str], timeout_s: int = 60)` returns `CommandResult`. `preflight_identity(transport, serial, expected_model, expected_fingerprint, profile)` returns `DeviceIdentity`, and `assert_transition(current, command)` raises a phase error for an illegal edge.

- [ ] **Step 1: Add failing safety and transition tests**

Cover missing serial, offline, unauthorized, wrong model, wrong fingerprint, profile mismatch, two connected devices with zero calls to the non-target serial, missing `--execute` on every mutating command, and illegal phase order.

Assert all target calls have command prefix:

```python
assert call[:3] == ("adb", "-s", "B06201249E00030C")
```

- [ ] **Step 2: Run the new tests to verify RED**

- [ ] **Step 3: Implement `AdbTransport` and identity gates**

Rules:

- Only `adb devices -l` may omit `-s`.
- `run_target` constructs the serial prefix internally; callers cannot supply a serial argument.
- Model and fingerprint must match both CLI expected values and profile values.
- Connected non-target devices are listed in evidence but never addressed.
- Mutating subcommands require all of `--serial`, `--profile`, `--expected-model`, `--expected-fingerprint`, `--run-id`, `--execute`.

- [ ] **Step 4: Implement phase transitions and durable current state**

Persist `current_phase`, `completed_phases`, `old_widget_id`, `final_home_role`, and `mutations_remaining` in `run.json`. Write state atomically through a temporary file in the same run directory followed by replace.

Allowed transitions:

```text
capture -> BASELINE_CAPTURED
BASELINE_CAPTURED -> bind -> BOUND_GENERAL
BOUND_GENERAL -> arm/switch -> SAFE_SIMPLE
SAFE_SIMPLE -> arm/lifecycle -> STALE_ARMED
STALE_ARMED -> trigger -> TRIGGERED_BUG or TRIGGERED_FIXED
any mutating state -> restore -> RESTORED_SAFE
```

The developer negative control may return to `BOUND_GENERAL` with `precondition_status=FAIL` when binding remains; it must not synthesize `STALE_ARMED`.

- [ ] **Step 5: Run focused tests to GREEN**

### Task 6: deterministic evidence bundle과 input verifier를 구현한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```python
make_run_id(now_utc: datetime) -> str
EvidenceBundle.create(root: Path, run_id: str) -> EvidenceBundle
EvidenceBundle.append_event(event: Event) -> None
EvidenceBundle.write_json(name: str, payload: dict) -> None
verify_inputs(repo_root: Path, profile: dict) -> dict
write_evidence_manifest(bundle_dir: Path) -> Path
```

- [ ] **Step 1: Add failing bundle tests**

Cover UTC format `YYYYMMDDTHHMMSSZ`, UTC/KST event timestamps, logical input IDs instead of raw APK absolute paths, deterministic JSON key ordering/newlines with a fixed clock, source manifest mismatch, split size/hash mismatch, sorted evidence manifest, and exclusion of `evidence_sha256.txt` from its own digest list.

- [ ] **Step 2: Run the new tests to verify RED**

- [ ] **Step 3: Implement bundle layout**

Create exactly:

```text
AT-M140 - Launcher BUG27084/evidence/20260829T000000Z/
  run.json
  events.jsonl
  inputs.json
  snapshots/
  screenshots/
  result.json
  verification.txt
  evidence_sha256.txt
```

Use UTF-8 without BOM and LF for JSON/JSONL/text generated by Python. `inputs.json` must pin source manifest and all split name/size/digest values before any install/uninstall.

- [ ] **Step 4: Implement event/result vocabulary**

`result.json` must expose diagnosis fields rather than one boolean:

```json
{
  "diagnosis_status": "OBSERVED",
  "evidence_term": "BUG-GAP observed",
  "precondition_status": "PASS",
  "provider_registered": true,
  "widget_bound_before": true,
  "widget_bound_after": false,
  "launcher_stale_record_evidence": "LOADER_LOG",
  "crash_signature_count": 1,
  "home_rendered": false,
  "launcher_process_stable": false,
  "final_home_role": "com.hnlens.simplemode",
  "mutations_remaining": []
}
```

Values are computed from evidence; this object is a schema example, not a hard-coded verdict.

- [ ] **Step 5: Run focused tests to GREEN**

### Task 7: read-only `capture`를 구현하고 snapshot completeness를 검증한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```text
capture --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --json
```

The shown run ID is the fixed-clock test fixture; live capture omits `--run-id` unless the caller deliberately supplies a unique UTC ID.

- [ ] **Step 1: Add failing fake-ADB capture tests**

Fake transcripts must verify collection of:

- `getprop ro.product.model`
- `getprop ro.build.fingerprint`
- `getprop ro.build.version.incremental`
- `wm size`
- HOME role / resumed activity
- `dumpsys package com.winson.simpleclock`
- `dumpsys appwidget`
- Launcher crash buffer and historical exit info
- boot ID and elapsed realtime
- screenshot and UI dump

Also test that screenshot/UI dump failure makes capture incomplete and prevents later mutation.

- [ ] **Step 2: Run the new tests to verify RED**

- [ ] **Step 3: Implement capture without clearing logs or changing device state**

Do not use `logcat -c`, force-stop, HOME switch, install, uninstall, reboot, tap, swipe, or data clear. Store raw command outputs under `snapshots/`, screenshot under `screenshots/`, parsed state in `run.json`, and verification summary in `verification.txt`.

- [ ] **Step 4: Add JSON stdout for orchestration**

With `--json`, print only:

```json
{"run_id":"20260829T000000Z","bundle":"AT-M140 - Launcher BUG27084/evidence/20260829T000000Z","current_phase":"BASELINE_CAPTURED"}
```

The real timestamp is injected at runtime; tests fix the clock.

- [ ] **Step 5: Run focused tests to GREEN**

### Task 8: `bind` UI flow와 binding gate를 구현한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```text
bind --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --execute
```

- [ ] **Step 1: Add failing bind tests**

Cover General HOME requirement, 480×800 viewport, selector presence before each coordinate fallback, `input touchscreen draganddrop`, provider setup `OK`, old widget id extraction, Launcher host match, provider component match, and `RemoteViews` non-null.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement selector-gated UI actions**

Sequence:

1. Re-run identity/viewport/current-role preflight.
2. If current role is the expected Simple HOME, use the approved switch activity/dialog path and poll until General HOME; if already General HOME, continue; any other role/activity is fail-closed.
3. Long-press blank HOME area.
4. UI dump must contain exact text `위젯`; tap its node center.
5. UI dump must contain exact search node `검색`; enter `SimpleClock`.
6. Expand exact provider label.
7. UI dump/screenshot must show the SimpleClock preview before executing profile drag coordinates.
8. Provider setup must show exact `OK`; use node center, with profile coordinate only if bounds are unavailable and viewport is exact.
9. Poll AppWidgetService until component, Launcher host, widget id, and non-null RemoteViews are observed.
10. Persist `old_widget_id` and transition to `BOUND_GENERAL`.

Fixed sleep is allowed only as a short UI settle between dumps; success is always condition-polled with a timeout.

- [ ] **Step 4: Run focused tests to GREEN**

### Task 9: `arm` lifecycle와 stale-precondition gate를 구현한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```text
arm --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --lifecycle uninstall-reinstall --execute
arm --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --lifecycle clear-force-stop-reboot --execute
```

- [ ] **Step 1: Add failing arm tests**

Cover:

- source manifest and split hash check occurs before device mutation
- Simple HOME role is verified before uninstall or clear
- uninstall success RC and `install-multiple` success RC
- installed version/name/signature match the immutable input pin
- new provider UID is recorded
- old widget ID is absent after uninstall/reinstall
- registry-only provider does not count as a binding
- developer procedure with retained binding returns `runtime precondition FAIL`, remains out of `STALE_ARMED`, and blocks trigger

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement role switch and positive lifecycle**

Start `com.hnlens.simplemode/.ui.home.SwitchModeActivity`, verify the user-visible mode flow, and poll until HOME role is `com.hnlens.simplemode`. Then:

```text
adb -s B06201249E00030C uninstall com.winson.simpleclock
adb -s B06201249E00030C install-multiple "C:\Users\momen\Projects\tc-runner\AT-M140 - Launcher BUG27084\evidence\20260828T221502KST_widget_generality\simpleclock_apk\base.apk" "C:\Users\momen\Projects\tc-runner\AT-M140 - Launcher BUG27084\evidence\20260828T221502KST_widget_generality\simpleclock_apk\split_config.ko.apk" "C:\Users\momen\Projects\tc-runner\AT-M140 - Launcher BUG27084\evidence\20260828T221502KST_widget_generality\simpleclock_apk\split_config.tvdpi.apk"
```

The actual subprocess argv contains absolute verified file paths, but `events.jsonl` stores logical IDs and digests instead of those paths.

Transition to `STALE_ARMED` only after all arm gates pass.

- [ ] **Step 4: Implement the developer negative lifecycle**

Run package clear, force-stop, and reboot only under `--lifecycle clear-force-stop-reboot`. After boot completion and role recovery, capture package/AppWidget/Launcher state. If the old binding remains, write `precondition_status=FAIL`, evidence term `runtime precondition FAIL`, and do not allow `trigger`.

- [ ] **Step 5: Run focused tests to GREEN**

### Task 10: `trigger`, `verify`, `restore`와 primary-error preservation을 구현한다

**Files:**

- Modify: `scripts/appwidget_stale_provider_repro.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`

**Interfaces:**

```text
trigger --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --execute
verify --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z
restore --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys --run-id 20260829T000000Z --execute
```

The fixed-clock run ID is replaced by the exact run ID emitted by live `capture`. `--preserve-armed-state` is added only after the separate preserve approval.

- [ ] **Step 1: Add failing tests**

Cover General HOME role polling, HOME render, Launcher PID stability window, exit-info, crash buffer signature count, stale evidence enum, timeout classification, known-bad verdict, fixed verdict six-condition gate, cleanup after primary failure, cleanup failure attached without replacing primary exception, and preserve flag/RESUME warning behavior.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement trigger and verify**

Trigger switches to General HOME and polls activity/role instead of relying on a fixed sleep. Capture post-state even when Launcher crashes. Classify:

- `TRIGGERED_BUG`: stale precondition PASS plus line185/88 signature observed.
- `TRIGGERED_FIXED`: stale precondition PASS plus HOME rendered, Launcher stable, signature 0, safe placeholder/cleanup, and normal widget update evidence.
- timeout/role mismatch: explicit step failure or `runtime precondition FAIL`; never fixed PASS.

`verify` is read-only and may be repeated against the same run.

- [ ] **Step 4: Implement default restore and explicit preserve**

Default restore stops the crash loop by returning to Simple HOME, captures final state, writes remaining mutations, and transitions to `RESTORED_SAFE`. Preserve requires `--preserve-armed-state`, prints the current role/general-mode crash risk, and leaves the run non-complete until `RESUME.md` is updated.

- [ ] **Step 5: Run focused tests to GREEN**

### Task 11: host-only verification, tool registration, and implementation review

**Files:**

- Modify: `AGENTS.md:288-310`
- Modify: `CLAUDE.md:288-310`
- Modify: `docs/appwidget_stale_provider_verification.md`
- Verify: all Phase 1–2 files

- [ ] **Step 1: Run the focused Phase 1–2 suite**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_appwidget_guidance_contract.py tests\test_bug27084_evidence_contract.py tests\test_appwidget_stale_provider_repro.py -q
```

Expected: all focused tests PASS.

- [ ] **Step 2: Run adjacent regression tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_eng_mode_runner.py tests\test_adb.py tests\test_action_runner.py -q
```

Expected: PASS; no core runner behavior changed.

- [ ] **Step 3: Verify `plan` is adb-free and default**

Run:

```powershell
.\venv\Scripts\python.exe scripts\appwidget_stale_provider_repro.py --profile AT_M140_BUG27084_KNOWN_BAD_V1
.\venv\Scripts\python.exe scripts\appwidget_stale_provider_repro.py plan --profile AT_M140_BUG27084_KNOWN_BAD_V1
```

Expected: both return exit 0, equivalent plan JSON, `adb=OFF`, and no evidence/device mutation.

- [ ] **Step 4: Register the implemented tool**

Only after Steps 1–3 pass, add `appwidget_stale_provider_repro.py` + profile to §5.3 in both guidance files and change the playbook tool status from host-planned to host-implemented/device-smoke-pending.

- [ ] **Step 5: Confirm core runner non-change and worktree scope**

Run:

```powershell
git status --short
git diff -- src tc_prompts validate_tc.py
```

Expected: no diff in `src/`, `tc_prompts/`, or `validate_tc.py`; unrelated user changes remain untouched.

- [ ] **Step 6: Run verification-before-completion discipline**

Invoke the `superpowers:verification-before-completion` skill before reporting Phase 1–2 success. Report `host tests PASS`; do not report `runtime PASS` because no device mutation has run.

- [ ] **Step 7: Commit gate — only after separate explicit approval**

Audit exact changed paths, stage them individually, run the repo push-audit in staged-only mode if applicable, and commit. Do not push.

---

## Phase 3 — 승인된 known-bad device pilot

### Task 12: read-only capture와 selector/identity calibration을 실행한다

**Files:**

- Create at runtime: a directory such as `AT-M140 - Launcher BUG27084/evidence/20260829T000000Z/`, with the real UTC run ID emitted by `capture`
- Modify after observation: `AT-M140 - Launcher BUG27084/RESUME.md`

**Interfaces:** known-bad profile and exact identity from Global Constraints.

- [ ] **Step 1: Reconfirm connected devices read-only**

Run:

```powershell
adb devices -l
adb -s B06201249E00030C shell getprop ro.product.model
adb -s B06201249E00030C shell getprop ro.build.fingerprint
adb -s B06201249E00030C shell wm size
```

Expected: AT-M140 identity matches exactly; ODIN2 may be present but receives no per-device command.

- [ ] **Step 2: Run harness capture and retain emitted run ID**

Run:

```powershell
$pilotJson = & .\venv\Scripts\python.exe scripts\appwidget_stale_provider_repro.py capture --profile AT_M140_BUG27084_KNOWN_BAD_V1 --serial B06201249E00030C --expected-model AT-M140 --expected-fingerprint 'ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys' --json
$pilotRunId = ($pilotJson | ConvertFrom-Json).run_id
$pilotRunId
```

Expected: `BASELINE_CAPTURED`, exact evidence directory, no device mutation.

- [ ] **Step 3: Spot-check selector and coordinate evidence without tapping**

Inspect captured screenshot/UI dump/current HOME role. If current role is Simple HOME, do not switch modes in this task. Confirm that 480×800 and selector assumptions are still valid or record a profile mismatch and stop.

- [ ] **Step 4: Update `RESUME.md` with read-only current state**

Record the emitted run ID, current HOME role, whether stale state is preserved, and the next mutation requiring approval.

### Task 13: known-bad positive control 1-cycle을 단계별 승인으로 실행한다

**Files:**

- Update at runtime: the Task 12 evidence bundle
- Modify after each mutation: `AT-M140 - Launcher BUG27084/RESUME.md`

- [ ] **Step 1: Request explicit approval for `bind`**

State exact target, run ID, expected mode change/UI gestures, and that ODIN2 will not be addressed. Do not continue on a generic earlier design approval.

- [ ] **Step 2: Execute `bind` and inspect its evidence before the next mutation**

Use `$pilotRunId` captured in Task 12 and the exact identity arguments. Expected: `BOUND_GENERAL`, old widget ID, matching provider/host, non-null RemoteViews.

- [ ] **Step 3: Request explicit approval for `arm --lifecycle uninstall-reinstall`**

Report the immutable APK manifest/split hashes and expected final Simple HOME/stale state.

- [ ] **Step 4: Execute arm and stop on any gate mismatch**

Expected: `STALE_ARMED`, same package/version/signature, new provider UID, old widget ID absent, provider registered, no old binding.

- [ ] **Step 5: Request explicit approval for `trigger`**

Warn that General HOME may enter a Launcher crash loop and that restore will require a separate approved mutation.

- [ ] **Step 6: Execute trigger and collect the known-bad verdict**

Expected for the current build: `BUG-GAP observed`, diagnosis `OBSERVED`, line185/88 signature, and quantitative count. If the expected crash does not occur, report the observed evidence and do not force the conclusion.

- [ ] **Step 7: Request and execute default `restore`**

Expected: `RESTORED_SAFE`, final Simple HOME, complete mutation ledger. Update `RESUME.md` immediately.

- [ ] **Step 8: Verify bundle completeness and hashes**

Run the harness bundle verifier. Report `manual evidence observed`/`BUG-GAP observed` as appropriate, not standalone PASS.

### Task 14: developer procedure negative control 1-cycle을 독립 fixture로 실행한다

**Files:**

- Create at runtime: a new UTC evidence bundle under `AT-M140 - Launcher BUG27084/evidence/`
- Modify: `AT-M140 - Launcher BUG27084/RESUME.md`

- [ ] **Step 1: Start a new capture and new widget binding**

Do not reuse the positive fixture or widget ID. Capture a new run ID, then request/execute bind approval as in Task 13.

- [ ] **Step 2: Request explicit approval for clear/force-stop/reboot**

Name all three mutations and the target package/serial.

- [ ] **Step 3: Execute `arm --lifecycle clear-force-stop-reboot`**

Expected based on current evidence: old binding/RemoteViews remains and stale precondition is not established. The harness records `runtime precondition FAIL` and blocks trigger.

- [ ] **Step 4: Perform read-only verify after boot**

Collect role, HOME render, Launcher crash buffer, AppWidget binding, and package state. The expected 0-crash result is evidence that the developer procedure did not create the stale state, not evidence of a fix.

- [ ] **Step 5: Restore only if a mutation remains, with explicit approval**

Update `RESUME.md` and final evidence manifest.

- [ ] **Step 6: Decide n-cycle scope with the user**

Do not auto-run multiple cycles. Present positive/negative fixture equivalence and observed counts, then request a new explicit cycle count if more measurement is needed.

---

## Phase 4 — exact fixed-build A/B와 Google Go 회귀

### Task 15: fixed build identity/profile을 실제 artifact로만 추가한다

**Status gate:** blocked until `AT-M140Z0827U_DAILY_DEV_GMS_849` is available. This is an external availability gate, not an implementation success condition.

**Files:**

- Modify after read-only identification: `scripts/appwidget_stale_provider_profiles.py`
- Modify: `tests/test_appwidget_stale_provider_repro.py`
- Create: fixed-build UTC evidence bundle

- [ ] **Step 1: Obtain user direction for firmware application**

The harness does not download or flash firmware. Flash/update method, data-preserve choice, and authorization are outside this plan's automatic actions.

- [ ] **Step 2: Capture fixed-build identity read-only after the user-applied build is present**

Record full fingerprint, incremental, Launcher package version/hash, HOME roles, viewport, and boot identity. Require the build label `AT-M140Z0827U_DAILY_DEV_GMS_849` to be supported by device/artifact evidence.

- [ ] **Step 3: Add a new exact fixed profile via RED/GREEN**

First add a test asserting the newly observed exact fingerprint and Launcher artifact pin. Then add a separate profile key; never overwrite or relax the known-bad profile. Run the full harness tests.

- [ ] **Step 4: Commit gate — only after separate explicit approval**

Commit the fixed profile/test as a distinct unit if approved; otherwise leave unstaged.

### Task 16: state-equivalent fixed A/B를 실행한다

**Files:**

- Create at runtime: a fixed-build UTC evidence bundle under `AT-M140 - Launcher BUG27084/evidence/`
- Create: a new date-specific result file under `AT-M140 - Launcher BUG27084/`
- Modify: `AT-M140 - Launcher BUG27084/BUG_LOG.md`
- Modify: `AT-M140 - Launcher BUG27084/RESUME.md`

- [ ] **Step 1: Choose and document state preservation method**

- Data-preserve update: require `PRESERVED_PREUPGRADE` evidence and prove Launcher data/stale record survived.
- Clean flash: recreate the same SimpleClock stale state on the fixed build and require `DIRECT_DB` or `LOADER_LOG` evidence.

`INFERRED_ONLY` is a blocker.

- [ ] **Step 2: Execute capture/bind/arm/trigger/restore with separate mutation approvals**

Use the fixed profile's exact identity. Do not reuse known-bad run state or snapshots.

- [ ] **Step 3: Apply the six-condition fixed verdict**

Require all:

1. stale precondition PASS
2. General HOME rendered
3. Launcher process stable for the declared observation window
4. line185/88 NPE count 0
5. safe pending placeholder or stale record cleanup observed
6. normal SimpleClock/Weather widget update observed

Only then report fixed-build scope `runtime PASS`; otherwise use the exact failing/precondition vocabulary.

- [ ] **Step 4: Record numerator/denominator and observation window**

One successful cycle is evidence but not an unqualified generalization. Any additional cycle count requires user approval.

### Task 17: Google Go 및 일반 widget 회귀를 별도 축으로 검증한다

**Files:**

- Modify: the Task 16 date-specific fixed-build result
- Update at runtime: the Task 16 fixed-build bundle under a distinct `google_go_regression` phase

- [ ] **Step 1: Define the manual evidence checklist before execution**

Checklist:

- Google Go content description and DPAD focus
- normal `remoteViews != null` update path
- focus background reset when moving to a non-Google widget
- pending `remoteViews == null` path without NPE
- ordinary widget tap/update/resize

- [ ] **Step 2: Request explicit approval for each UI/device mutation group**

If Google Go is absent or setup is blocked by account/network policy, record `NOTE`; do not let that rewrite the stale-provider verdict.

- [ ] **Step 3: Execute and record evidence independently**

Report stale-provider and Google Go axes separately. Neither axis inherits the other's verdict.

- [ ] **Step 4: Update issue lifecycle only from evidence**

- Keep diagnosis `OBSERVED` until the required matrix and fixed A/B are satisfied.
- Change issue status to `RESOLVED` only when the developer fix is actually applied and verified in scope.
- Add a new RESULT file; do not overwrite historical results.

---

## Phase 5 — core 승격 판단만 수행한다

### Task 18: core runner promotion gate를 평가하고 별도 설계 여부를 결정한다

**Files:**

- Modify only if evidence exists: `docs/appwidget_stale_provider_verification.md`
- Do not modify in this task: `src/`, schemas, validators, `tc_prompts/runner_capability.yaml`

- [ ] **Step 1: Evaluate all promotion criteria**

Require host tests, known-bad positive/negative rerun, exact fixed A/B, two providers or two independent campaigns, fail-closed profile evidence, and cleanup/preserve device proof.

- [ ] **Step 2: Record one of two decisions**

- Gate incomplete: keep the dedicated harness as the operational tool and name missing evidence.
- Gate complete: request a new design approval for `drag_and_drop`, `verify_shell_until`, and `capture_shell`.

- [ ] **Step 3: Prevent schema drift**

If a core design is later approved, update action definition, schema, loader, runner, validator, tests, and `runner_capability.yaml` in one change. Never expose install/uninstall through generic shell.

---

## Final Verification Matrix

| Scope | Required evidence | Allowed report |
|---|---|---|
| Phase 1 docs/ledger | contract tests + JSON parse + cross-links | documentation/evidence contract PASS |
| Phase 2 harness | fake ADB suite + adjacent regression + adb-free plan | host tests PASS; device smoke pending |
| Phase 3 known-bad positive | stale gate + line185/88 stack | `BUG-GAP observed`, diagnosis `OBSERVED` |
| Phase 3 developer procedure | binding retained / stale gate absent | `runtime precondition FAIL` |
| Phase 4 fixed build | exact identity + state equivalence + six conditions | scoped `runtime PASS` only if all pass |
| Google Go regression | separate focus/update/manual evidence | separate runtime/manual verdict |

## Stop Conditions

Stop immediately and preserve evidence if serial/model/fingerprint, viewport, HOME role, APK manifest/split digest, widget binding, phase state, or Launcher data-preservation gate mismatches. Do not replace a primary failure with cleanup failure, do not touch ODIN2, do not infer fixed-build success from the current OTA, and do not commit or push without a separate explicit instruction.
