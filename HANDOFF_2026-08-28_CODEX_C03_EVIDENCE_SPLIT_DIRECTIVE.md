# CODEX 지시문 — C03 T2 사전 host 보강 (2026-08-28)

**역할**: Codex = 구현 / Claude = 설계 lock·독립 재검증 / 사용자 = 승인 게이트.
**규칙 source**: tc-runner root `AGENTS.md` 전 섹션 (특히 §2.1 승인 게이트 · §2.2 보고 어휘 · §5.7 오염 · §7 commit 정책). 본 지시문은 AGENTS.md 를 보충하며, 충돌 시 AGENTS.md 가 우선.
**선행 지시문**: `HANDOFF_2026-08-27_CODEX_C03_QPN_DIRECTIVE.md` — §0 T0 게이트 · §3 T2 · §4 금지는 **전부 승계**. 본 지시문은 그 T2 착수 전 단계다.

> **후속 상태 주석 (2026-09-03)**: 아래 본문은 2026-08-28 실행 당시의 지시와
> 측정값을 보존한다. T-E 구현은 thor2j 로컬 commit
> `30beec0f15403ce325534137d9f054403df145d4`에 반영됐고, 정리 승인 후 현재 canonical
> evidence tree의 파일 수는 0이다. §6의 `rest31`은 당시 예비 구상이므로 실행 계약으로
> 사용하지 않는다. 최종 T2 계약은
> `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md` §7.2의
> `d1` → `rest41`이며, device 2-run은 아직 미실행이다. 본 주석은 당시 본문을 소급
> 변경하지 않는다.

**승인 상태**:
- **T-E (본 지시문, host-only)** — 사용자가 본 지시문을 Codex 에 전달한 시점 = 착수 승인.
- **T2 (F0 device 2-run)** — **여전히 별도 명시 승인 필요.** 본 작업 완료가 T2 승인을 만들지 않는다.
- **commit / push** — 각각 별도 명시 승인. 본 구간 commit 0.

**작업 repo**: thor2j (`C:\Users\momen\Projects\thor2j-tc-appium`). tc-runner 문서는 본 구간에서 수정하지 않는다.

---

## 0. T0 — 전제 게이트 (착수 전 전부 확인, 하나라도 FAIL = STOP + 보고)

1. **baseline** — thor2j HEAD = `e225639` (C03 QPN idle-probe T1 slice). 불일치 = STOP.
2. **다른-writer 파일 접촉 금지** — 선존 무관 tracked M 6. 읽기 외 **편집·stage 절대 금지**:
   `docs/annotation_candidate_dossier_2026-07-06.md` · `docs/recovery_honesty.md` ·
   `testcases/focusrule/focusrule_tc_catalog.yaml` · `testcases/focusrule/tc_profiles_index.yaml` ·
   `tests/test_recovery_feasibility_audit.py` · `tests/test_tc_quality_audit.py`
3. **5-suite + probe GREEN 기준선**:
   `python -m pytest tests/test_altbasic_c01_driver.py tests/test_altbasic_c02.py tests/test_altbasic_c03.py tests/test_altbasic_c03_idle_probe.py tests/test_altbasic_c11.py tests/test_altbasic_narrow.py`
   → 기준선 **222 passed** (`e225639` 커밋 메시지 기록값). 미달 = STOP.
4. **dry-run 등가**: `python runner/altbasic_c03_driver.py --dry-run` → `drivable=34 registry=10`. 불일치 = STOP.
5. **device 호출 0회** — 본 구간 전체에서 `adb` 실행 0. `--run 1` / `--run 2` 호출 금지.

## 0.1 착수 전 STOP 보고 1건 (사용자 결정 영역)

`evidence/altbasic_batch10_c03_v1_20260820/run1/_diagnostics/` 에 다음 2 파일이 **이미 존재**한다:

```
packages.xml   60 bytes  CAPTURE_FAILED: 'FakeDevice' object has no attribute 'shell'
qs_tiles.xml   60 bytes  CAPTURE_FAILED: 'FakeDevice' object has no attribute 'shell'
```

= host 테스트 누출 산물 (§1 FINDING-2). `evidence/*` 는 `.gitignore` 대상이라 untracked 다.

[측정 2026-08-28 10:44:04 KST] 두 파일의 mtime 은 **직전 5-suite 실행 시각**과 일치한다 —
잔재는 08-20 의 1회성 산물이 아니라 **suite 를 돌릴 때마다 덮어써지는 상시 누출**이다.
따라서 T-E1 이전에는 이 경로가 정지 상태가 아니며, 재자격 기준 §4-3 의 "전후 동일" 판정은
T-E1 적용 후에만 성립한다.
**삭제·이동은 사용자 결정 영역** — Codex 가 임의 삭제하지 않는다 (AGENTS §7.3).
착수 시 존재 사실만 보고하고, 잔재를 남긴 채 §2 를 구현한다. 잔재 처리는 §4 재자격 직전에
사용자 지시를 받는다.

---

## 1. 문제 정의 (측정 — Claude 독립 재검증 2026-08-28)

### FINDING-1 — split-call 이 `_diagnostics` 를 덮어쓴다

- `_write_evidence()` (`runner/altbasic_c03_driver.py:165`) 는 `open(path, "w")` = **절단 쓰기**.
  경로 = `evidence/altbasic_batch10_c03_v1_20260820/run{N}/{tc_id}/{tag}.xml`.
- `_capture_diagnostics(dev, run_no)` (`:312`) 는 `run_pilot()` **호출마다 1회** 실행되고
  (`:544`), 고정 이름 `_diagnostics/packages.xml` · `_diagnostics/qs_tiles.xml` 로 쓴다.
- 따라서 같은 `--run N` 을 `--only` 로 2회 나눠 호출하면 **두 번째 호출이 첫 번째의
  diagnostics 를 소실**시킨다.

[측정] **per-TC 증거는 split-call 로 충돌하지 않는다.** 모든 per-TC 쓰기가 `{step_no:02d}_`
접두를 갖고 (`:378`~`:464`), scroll/probe observe 람다도 `{index:02d}` 를 포함하므로 케이스 내
태그가 유일하다. 두 호출의 tc_id 집합이 서로소이므로 split-call 충돌은 `_diagnostics` **단독**이다.

[측정] `_record_result()` (`:174`) 는 append 모드 + 헤더 1회 조건부다. split-call 에서 정상
누적된다. **수정 대상 아님.**

### FINDING-2 — host 테스트가 실 evidence 트리에 쓴다 (신규)

`tests/test_altbasic_c03.py` 의 `run_pilot` 계열 3 테스트 (`:424` · `:453` · `:475`) 는
`AdbDevice` · `_wrong_device_guard` · `load_c03_rows` · `_run_case` · `_record_result` 를
monkeypatch 하지만 **`_capture_diagnostics` 와 `_ev_base` 는 패치하지 않는다.**
→ `run_pilot` 이 실제 `_capture_diagnostics` 를 호출 → `FakeDevice.shell` 부재 →
fail-soft 경로가 `CAPTURE_FAILED:...` 문자열을 **실 evidence 디렉토리에 기록**한다.

5-suite 를 돌릴 때마다 재발하는 상시 오염이며 AGENTS §5.7 phantom 계열이다.
**FINDING-2 를 먼저 고치지 않고 §2.3 가드를 넣으면 §0.1 잔재 때문에 테스트가 깨진다.**

### FINDING-3 — 증거 충돌 예외가 verifier FAIL 로 둔갑한다

`_run_case()` (`:473`) 는 `MutationGuardError` 만 재-raise 하고 나머지 `Exception` 을
`"runtime verifier FAIL"` 로 흡수한다. §2.3 가드의 예외를 그대로 두면 **증거 인프라 사고가
단말 버그 판정으로 오보**된다.

---

## 2. 구현 요구 (TDD 선행 — 각 항목 실패 테스트 먼저)

### 2.1 T-E1 — 테스트 격리 (FINDING-2)

- `run_pilot` 를 호출하는 모든 테스트가 실 evidence 트리에 쓰지 못하게 한다.
- 권장: `tests/test_altbasic_c03.py` 에 `_ev_base` 를 `tmp_path` 로 돌리는 **autouse fixture**
  추가. 개별 테스트 패치 누락이 다시 새지 않도록 **모듈 단위 봉인**이 목적이다.
- **회귀 테스트 필수**: 5-suite 실행 후 실 `evidence/altbasic_batch10_c03_v1_20260820/`
  아래에 새 파일이 생기지 않음을 검증하는 테스트 1건. (경로 존재 여부가 아니라
  **테스트 실행이 그 경로에 쓰지 않음**을 검증한다.)

### 2.2 T-E2 — diagnostics segment 네임스페이스 (FINDING-1)

- CLI 에 `--segment <label>` 추가.
  - 기본값 `full`.
  - `--only` 가 주어지면 `--segment` **필수** — 없으면 `parser.error` (fail-closed).
  - label 허용 문자 `[a-z0-9_-]{1,32}` 강제. 위반 = 오류 종료. (경로 조작 차단)
- diagnostics 경로: `run{N}/_diagnostics/{segment}/{name}.xml`.
- **per-TC 경로는 변경하지 않는다** (`run{N}/{tc_id}/{tag}.xml`). 근거: TC 집합이 서로소라
  충돌하지 않으며, 경로를 segment 로 쪼개면 §2.3 가드가 **같은 run_no 에서 같은 TC 재실행**을
  더 이상 잡지 못한다. 그 탐지력이 3회-입력 금지 규칙의 안전망이다.
- `run_pilot` 시그니처에 segment 를 전달한다. 기존 인자 순서·기본값 호환 유지.

### 2.3 T-E3 — write-once fail-closed 가드 (FINDING-1·3)

- `_write_evidence()` 는 대상 경로가 **이미 존재하면 절대 절단하지 않는다.**
  전용 예외 `EvidenceCollisionError` 를 정의해 raise 한다 (`RuntimeError` 파생,
  `MutationGuardError` / `LiteralPendingError` 와 **구분되는 별도 타입**).
- `_run_case()` 의 `except MutationGuardError: raise` 옆에
  `except EvidenceCollisionError: raise` 를 **추가**한다 — verifier FAIL 흡수 금지 (FINDING-3).
- `run_pilot` 에서 이 예외는 **전체 run 중단**으로 전파한다. `MutationGuardError` 와 동일 계층의
  중단이되, `_record_result` 어휘는 구분한다: `runtime mutation FAIL` 이 아니라
  `evidence collision STOP` 으로 기록한다. **버그 판정 어휘를 재사용하지 않는다** (AGENTS §2.2).
- `_capture_diagnostics` 의 fail-soft 는 **`dev.shell` 실패에 한정**한다.
  `EvidenceCollisionError` 는 fail-soft 로 삼키지 않는다.

### 2.4 T-E4 — 전 34건 증거 경로 유일성 테스트 (device 0)

- drivable 34 전건에 대해 `C.build_qpn_plan(tc_id)` 로 plan 을 만들고, `_run_plan_steps` 가
  발행할 evidence 태그를 host 에서 열거해 **run 내 중복 0** 을 단언하는 테스트를 추가한다.
- observe 람다가 발행하는 인덱스 태그(`ensure_focus` · `scroll_inventory` · `literal_probe`)를
  budget 상한까지 포함해 열거한다.
- 목적: §2.3 가드가 정상 run 에서 **오탐으로 터지지 않음**을 착수 전에 증명한다.
  device 실행으로 확인하지 않는다.

---

## 3. 비목표 / 금지 (착수 금지 — 손대면 scope 위반)

- `results.csv` 스키마 변경 (segment 열 추가 등) — tc_id 로 이미 구분 가능. **불필요.**
- 판정 로직 · verify 계약 · plan 상수 · disposition 표 변경 0. `drivable=34 registry=10` 불변.
- `EV_REL` (evidence 루트 이름) 변경 금지.
- §0.1 잔재 파일 삭제·이동 (사용자 결정 영역).
- tc-runner 쪽 설계·RUNSHEET·HANDOFF 문서 편집 (본 구간 non-goal — T2 결과와 함께 별도 정렬).
- 선행 지시문 §4 금지 전부 승계: D2 · D2-a · 102 비-scalar guard · 145 Appium 채널 · activity
  backfill · 원문 canonical yaml 편집 · broad add.
- `--run 1` / `--run 2` 실행, `adb` 호출.

---

## 4. 재자격 기준 (완료 조건)

1. 5-suite + probe **fresh 실행** → `222 + 신규 N passed`, **failed 0**. 신규 테스트 목록 명시.
2. `--dry-run` → `drivable=34 registry=10` **무변화**.
3. 5-suite 실행 전후 실 evidence 트리 파일 목록 **동일** (T-E1 증명. §0.1 잔재 2개 외 증가 0).
4. `--only` + `--segment` 누락 조합이 fail-closed 로 거부됨을 테스트로 증명.
5. device 호출 0회 확인.
6. `git status --short` — 변경 파일이 `runner/altbasic_c03_driver.py` ·
   `tests/test_altbasic_c03.py` (+ 필요 시 신규 테스트 파일) **로 한정**되고,
   §0-2 무관 M 6 이 **그대로 M 상태 유지**(추가 편집 0).

## 5. 보고 형식

- PASS 어휘 4종 한정 (AGENTS §2.2). 단독 `PASS` 금지. scope 밖 관찰은 `NOTE`.
- `[측정]` / `[추론]` 구분 표기.
- 보고 항목: 변경 파일 목록 · 신규 테스트 목록과 수 · 5-suite 총계 · dry-run `34/10` ·
  evidence 트리 전후 비교 · device 호출 0 · §0.1 잔재 현황 · 미해결 잔여 항목.
- **commit 하지 않는다.** 완료 보고 후 사용자 batch commit 승인 대기.

## 6. 이후 단계 (본 지시문 범위 밖 — 별도 승인)

1. T2 실행 캡슐 확정 — run 별 `D1 3건 → 나머지 31건` 분할, TC 당 run 내 입력 정확히 1회,
   segment label 확정 (예: `d1` / `rest31`), 145 목적지 T1 관찰기 동반 1건.
2. F0 device 2-run — 사용자 "2-run 실행 승인" 후에만. D1 mutation FAIL = 즉시 중단,
   나머지 31건 입력 0.
3. run1·run2 완료 후에야 T1 영구/일시 판별이 성립한다. 설계 §8·§10.5 상태 갱신은 그 다음.
4. commit · push 는 각각 별도 승인.
