# Part B — §9.3 THOR2_J device differential 실행 지시서 (self-contained, Codex 실행용)

**역할**: Codex = 단말 실행 / Claude = 계획·검증. 본 문서 하나로 실행 가능 (타 문서 참조 불필요).
**목표**: 같은 단말·같은 상태에서 **legacy vs canonical(contract_mode만 유일 변수)** SMOKE 대조 → RESULT 작성. (2단말 아님, 단일 THOR2_J.)

## 0. 확인된 상태 (Claude 실측, 2026-07-24)

- HEAD `de348e3`, ahead 3, tree clean. contract `0937895`(origin)·D0 `e615490`·verifier `770bab6`·docs `de348e3` 전부 반영.
- pytest tests/ **1390 passed** (직전 확인). validate SMOKE 01/02 **2/2 PASS**.
- 단말: serial `B2700125BW000083`(단일 연결)·`ro.product.model=AT-M140`·`persist.sys.locale=ja-JP`·Android 14. **정체 게이트 현재 통과.**

## 1. 불변 제약 (전 단계 공통)

- **모든 adb 명령에 `-s B2700125BW000083` 필수.** 다른 단말·다른 serial 접촉 절대 금지.
- adb는 **PowerShell로 호출**(Git Bash가 `/data/local/tmp` 경로 mangle). device 파싱은 tab-split(`$ln.Split([char]9)`), `'\tdevice$'` 정규식 금지(하네스 가드 오탐).
- 화면 sleep 대비 **wake→정체 재확인→실행을 원자적으로**. screencap/dump는 **`/data/local/tmp`만**(/sdcard 금지 — MediaStore 오염).
- 허용: 위 serial 대상 `cli run` 4종·비파괴 관찰(getprop/dumpsys/uiautomator dump/logcat -d). **금지**: install/uninstall·reboot·설정 값 변경·파일 push·SMOKE 외 앱 조작.
- **`--serial`은 pin 전용, `--strict-shell` 금지.** 이유: strict는 legacy 대비 신규 rc-check 다수 + `dump_ui` raise가 `_verify_text` retry 붕괴 → 역사 baseline보다 취약. differential 유일 변수는 **contract_mode**여야 하므로 strict는 오염.

## 2. B-0 정체 게이트 (매 실행 직전 재확인 — Codex 판단 금지)

`adb -s B2700125BW000083 shell "getprop ro.product.model; getprop persist.sys.locale"`:
- `ro.product.model` == `AT-M140` **AND** `persist.sys.locale` ∈ {`ja`, `ja-JP`} **AND** serial 일치.
- **하나라도 불일치 → 즉시 STOP + 보고** (en-US 복귀·타 단말·미연결 = 미준비, 실행 금지). 미연결/점유 징후 = `NOTE`/`미실행`(FAIL 아님).

## 3. B-1 legacy 재현

```
venv/Scripts/python.exe -m src.cli run "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml" --serial B2700125BW000083
```
- 출력 run_id·bundle 경로 기록. **전 step 성공 시에만** `runtime PASS 11/11` 기록(SMOKE_01 = 11 step). 1 step이라도 실패 → exact step 기록 후 **STOP**(canonical 진입 금지 — 역사 baseline 미재현).
- §3.5 무중단 조건(같은 단말×앱·직전 runtime PASS·validate PASS) 충족 시 SMOKE_02 이어서:
```
venv/Scripts/python.exe -m src.cli run "THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml" --serial B2700125BW000083
```
- 전 step 성공 시에만 `runtime PASS 13/13`(SMOKE_02 = 13 step, 역사 baseline).

## 4. B-2 canonical replay (contract_mode만 유일 변수)

같은 window·같은 단말 상태에서:
```
venv/Scripts/python.exe -m src.cli run "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml" --serial B2700125BW000083 --contract-mode canonical
venv/Scripts/python.exe -m src.cli run "THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml" --serial B2700125BW000083 --contract-mode canonical
```
- canonical은 any-step abort 설계 — 실패 시 `ABORTED_FAIL_CLOSED` bundle + exact step 기록 후 STOP(legacy default 유지 판정 근거로 보존).

## 5. B-3 대조 + RESULT

- **`THOR2_J - Settings/RESULT_2026-07-24.md`** 신규 작성(RESULT 날짜 시리즈).
- 대조표: run 4개(legacy 01/02·canonical 01/02)의 step별 `passed`·`duration`·shell `rc`(해당 시)·`message` + top-level `contract_mode`/`run_status` + **`device.serial_pinned`/`serial_observed`**(summary.json, D0 정체 증명).
- 첨부: 각 run_id·bundle 경로·summary.json sha256. 원본 J YAML 2파일 hash/mtime **불변(mutation 0)** 확인.
- 과거 11/11·13/13 재현 여부 명시. legacy≠canonical = **differential mismatch**(BUG-GAP 아님, 원인 판정은 Claude 리뷰 몫).

## 6. B-4 종료 + STOP

- 보고: run 4개 결과표 + RESULT 경로 + 단말 상태(연결·정체·serial 일치·mutation 0) + git 상태.
- **금지(전부)**: default flip·cutover 최종 판정·push·RESULT 커밋. RESULT는 untracked 유지 → Claude 재검증·cutover 리뷰 대기.
- mismatch 발생 시: legacy default 유지 상태로 exact step에서 STOP. 임의 보정·재시도 금지.

## 보고 어휘

`runtime PASS n/n`은 실단말 전 step 성공 run에만. 미가용/미준비 = `NOTE`/`미실행`(FAIL 아님). legacy·canonical 불일치 = `differential mismatch`.
