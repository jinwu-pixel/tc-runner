# 배치 커밋 + §9.3 THOR2_J device differential 실행 지시서 (Codex 실행용)

역할: **Codex = 실행 / Claude = 계획·검증**. 근거: 사용자 지시 2026-07-22 "배치 커밋 이후 2번(§9.3 device differential) 진입".
설계 SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md` §9.3·§9.5·§3.5.
Baseline: HEAD `742445a` = origin/master 0/0 · pytest tests/ **1293 passed** · matrix `16ee5ae8ca8f55c4` · cutover 판정 = G2-device만 잔여(canonical opt-in 유지).

순서 강제: **Part A(커밋) 완료·검증 후에만 Part B(단말) 진입.** Part A 실패 시 Part B 진입 금지.

---

## Part A — contract slice 배치 커밋 (승인 완료 — push는 금지)

**승인 근거**: 글로벌 정책 예외 5(batch commit) + 사용자 명시 지시(2026-07-22). **push는 별도 "push now" 승인 전 금지.**

### A-1. 사전 게이트

1. `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` → **1293 passed** (아니면 STOP)
2. `git status --short` + `git diff --name-only` + `git diff --name-only --cached`(staged 0 확인)
3. ledger digest `16ee5ae8ca8f55c4` 불변 확인 (CSV sha `416fb1d9…d1620d10`)

### A-2. 커밋 대상 — 정확 26 path (이 목록 외 stage 절대 금지)

tracked 수정 21:
```text
validate_tc.py  tc_step_schema.json  tc_prompts/STAGE2_COMPILE.md
tests/test_execution_type.py  tests/test_validate_lint.py
src/tc_loader.py  src/excel_converter.py  src/mmi_converter/compiler.py  src/mmi_converter/exporter.py
tests/test_tc_loader.py  tests/test_excel_converter.py  tests/test_mmi_compiler.py  tests/test_exporter.py
src/adb.py  src/action_runner.py  tests/test_adb.py  tests/test_action_runner.py
src/cli.py  src/reporter.py  tests/test_cli.py  tests/test_reporter.py
```
untracked 신규 5:
```text
src/execution_contract.py  tests/test_execution_contract.py
scripts/contract_drift_ledger.py  tests/test_contract_drift_ledger.py
tests/test_thor2j_smoke_differential.py
```

**절대 미포함**: `THOR2_J_missed_call_issue/` 3 수정+`RESULT_2026-07-21.md`(사용자 병행 트랙) · `AGENTS.md` · `HANDOFF_*.md` 전부 · `reports/`(gitignored) · 그 외 backlog untracked 전부. broad add(`.`/`-A`/디렉토리) 영구 금지 — **26개 개별 exact-path `git add`만**.

### A-3. staging 검증 → 커밋

1. stage 후 `git diff --name-only --cached` == 위 26개와 **정확 일치** (초과·누락·예상외 1개라도 있으면 즉시 STOP·보고, 커밋 금지)
2. redaction: 신규 유입 0 확정됨 — hit 2종은 사용자 A안 확정(더미 `01012345678` allowlist·serial `B06201249E0002F0` HEAD 선존 debt 등재). 재스캔 시 이 2종 외 hit 발견되면 STOP.
3. 커밋 메시지 (1 커밋):
```text
feat(contract): canonical execution contract Slice 0.5~1b + THOR2_J host differential

- Slice 0.5: contract drift ledger (measure-first, byte-deterministic, 3세대 digest 95750a5a/bb695f17/16ee5ae8)
- Task 2: src/execution_contract.py 공유 normalizer + validator 단일 경로 + schema/STAGE2 정렬
- Task 3: loader/Excel/MMI canonical opt-in mode (legacy 무변경)
- R1: derive/validate execution_type 단일 규칙 공유 (manual-routed 한정, corpus 0/30·0/16)
- Task 4: ShellResult/shell_result + runner canonical branch (rc!=0 FAIL, timeout ms->s, tap_id target)
- Task 5: cli --contract-mode + host_preflight 8조건 pre-device gate(ADB 0) + any-step abort + reporter summary v2
- Task 6/7-host: 1120 nodeid 전량 보존 + THOR2_J SMOKE legacy<->canonical host differential GREEN

tests/ 1293 passed (baseline 1120 + 173) / corpus 30/30 validate PASS / canonical blocking 0 (legacy 12 측정 유지)
cutover: G2-host까지 충족, canonical opt-in 유지 (device differential 별도)
```
4. 커밋 후: `git show --stat HEAD` 로 26파일 확인, `git status --short`(사용자 트랙 3+1과 backlog만 잔존해야 정상), ahead 1 확인. **push 금지.**
5. 보고: changed/staged 목록·메시지·pytest 수치·non-goals 준수·final status.

---

## Part B — §9.3 THOR2_J SMOKE device differential (게이트 ② 진입)

### B-0. 승인 스코프 (본 지시서 dispatch = serial-pinned 캠페인 승인)

- **핀 고정 serial: `B2700125BW000083`** (THOR2_J, ja-JP). 모든 adb 명령에 `-s B2700125BW000083` 필수.
- 실측 정체 게이트: `getprop ro.product.model`·`persist.sys.locale`(ja-JP 계열)·serial 일치 — **하나라도 불일치 시 즉시 STOP** (다른 단말 접촉 절대 금지).
- 미연결/타 세션 점유 징후(예: 예상 외 프로세스·다른 작업 흔적) → **`NOTE` + `미실행` 기록 후 STOP** (§9.3:618 — 미가용은 FAIL 아님).
- 허용 명령: 위 serial 대상 `cli run` 2종(SMOKE 01/02)·비파괴 관찰(getprop/dumpsys/uiautomator dump/screencap→**/data/local/tmp만**·logcat -d). **금지**: install/uninstall·reboot·설정 값 변경·파일 push·/sdcard 기록·SMOKE 외 앱 조작.
- 단말 함정(선행 세션 실측): adb는 PowerShell로 호출(Git Bash 경로 mangle) · device 파싱은 tab-split(`$ln.Split([char]9)`, `'\tdevice$'` 정규식 금지) · 화면 sleep 대비 wake→확인→실행을 한 호출에 원자적으로.

### B-1. legacy 재현 (§9.3:612)

1. 사전: validate 재확인 `venv/Scripts/python.exe validate_tc.py "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml" "THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml" --no-lint` → 2/2
2. `venv/Scripts/python.exe -m src.cli run "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml"` (legacy 기본값) — 출력의 run_id·bundle 경로 기록
3. **전 step 성공 시에만 `runtime PASS 11/11` 기록** — 1 step이라도 실패 시 exact step 기록 후 **STOP** (canonical 진입 금지 — 역사 baseline 미재현)
4. §3.5 조건 충족(같은 단말×앱·직전 runtime PASS·validate PASS) 시 SMOKE 02 무중단 진행 → 전 step 성공 시에만 `runtime PASS 13/13`

### B-2. canonical replay (§9.3:614 — contract mode만 유일 변수)

같은 window·같은 단말 상태에서:
1. `… -m src.cli run "…SMOKE_01…" --contract-mode canonical` → 이어서 SMOKE 02 동일 순서
2. canonical은 any-step abort 설계 — 실패 시 `ABORTED_FAIL_CLOSED` bundle과 exact step 기록 후 **STOP** (legacy default 유지 판정 근거로 보존)

### B-3. 대조 + RESULT 작성 (§9.3:615)

- run 4개(legacy 01/02·canonical 01/02) bundle의 step별 passed·duration·shell rc(해당 시)·message, top-level `contract_mode`/`run_status` 대조표 작성
- `THOR2_J - Settings/RESULT_2026-07-22.md` 신규 작성 (RESULT 날짜 시리즈 규약): 대조표 + run_id/bundle 경로 + summary.json sha256 + §2.2 어휘 (`runtime PASS n/n`은 전 step 성공 run에만) + 과거 11/11·13/13 기록과의 관계(재현 여부)
- 원본 J YAML 2파일 hash/mtime 불변 확인 (mutation 0)

### B-4. 종료 + STOP

- 보고: Part A 커밋 결과 + Part B run 4개 결과표 + RESULT 문서 경로 + 단말 상태(연결·정체·mutation 0) + git 상태(RESULT는 untracked 유지 — 커밋 금지)
- **default flip·cutover 최종 판정·push·RESULT 커밋 전부 금지** — Claude 재검증·cutover 최종 리뷰 대기
- mismatch 발생 시: legacy default 유지 상태로 exact step에서 STOP (§9.3:616) — 어떤 보정·재시도도 임의 수행 금지

## 보고 어휘

`runtime PASS`는 실단말 전 step 성공 run에만. 미가용 = `NOTE`/`미실행`(FAIL 아님). legacy·canonical 결과 불일치는 `BUG-GAP observed`가 아니라 **differential mismatch**로 기록 (원인 판정은 리뷰 몫).
