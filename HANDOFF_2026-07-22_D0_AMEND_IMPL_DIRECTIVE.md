# D0 설계 판정 + 구속 수정 + 구현 지시서 (Codex 실행용)

역할: **Codex = 실행 / Claude = 계획·검증**.
대상 설계: `docs/superpowers/specs/2026-07-22-d0-device-safety-reconcile-design.md` (sha256 `09e8530c…f44084b`, 306줄).
Baseline: HEAD `0937895` = contract slice 26파일 커밋 완료(검증 일치) · origin 대비 ahead 1 · pytest tests/ 1293 · matrix `16ee5ae8ca8f55c4`.

## 0. 판정

**조건부 승인 (ACCEPT WITH REQUIRED AMENDMENTS)** — 설계 방향(serial pin · /data/local/tmp 격리 · active locale 증거 · 결정론 ledger 재생성)은 승인. 단, 아래 **A-1~A-14는 구속(binding)** 이며 반영 전 구현 착수 금지.

Claude 적대 리뷰 3종 결과: BLOCK 1 / ACCEPT_WITH_CORRECTIONS 2. critical 3 + important 다수. 근거는 각 항목에 인용.

**작업 순서**: ① 설계 문서에 A-1~A-14 반영(untracked 문서, 커밋 무관) → ② TDD 구현(§2) → ③ 게이트(§3) → ④ STOP·보고. Part B(단말)는 §4 선결 결정 후 별도 지시.

---

## 1. 구속 수정 (A-1 ~ A-14)

### A-1 (critical) `strict_shell`은 `device_serial`과 **독립**

`strict_shell`은 기본값 `False`인 **독립 keyword** 파라미터. `device_serial`은 **첫 번째 positional** 유지. **serial 단독은 절대 strict를 의미하지 않는다.**

근거: `scripts/contract_drift_ledger.py:934`가 `ADB("PROBE_SERIAL").shell("bogus-cmd", timeout=5)` — **positional serial + rc=1에서 stdout 반환**을 전제로 `SHELL_RC_DISCARDED`(확정 결함 1)를 관측한다. 커플링 시: 예외가 `_probe_shell_rc`→`_build_all_rows`→`main`(except가 `LedgerInputError/OSError/yaml.YAMLError`만 포착)로 탈출해 **CSV/SUMMARY가 아예 생성되지 않음**. 추가로 `scripts/menu_mapper.py:374`·`scripts/settings_tree_explorer.py:603`도 raising transport로 변질.

테스트 잠금 필수: `ADB("PROBE_SERIAL").shell()`이 rc≠0에서 **stdout을 반환**함을 단언하는 테스트를 `tests/test_adb.py`에 추가.

### A-2 (critical) `--serial`과 strict/abort **분리** — 4-run 캠페인은 `--serial`만 사용

설계 §5.3의 "pinned ⇒ checked-shell + any-step abort"를 **분리**한다.

- `--serial <S>`: **transport pin 전용**. 실행 의미론 변경 **없음**.
- `--strict-shell`: 별도 opt-in 플래그. checked-shell + pinned any-step abort를 **함께** 활성화.
- **4-run 差등검증은 `--serial`만 사용** (`--strict-shell` 미사용).

근거(differential 리뷰어 BLOCK 사유): pinned-strict를 legacy에 적용하면 두 legacy run에서 **49개 지점이 신규 rc-검사 대상**이 되고 그 중 **42개(85.7%)가 TC에 선언되지 않은 ADB helper 호출**(screencap/pull/uiautomator dump/cat/rm)이다. 역사 baseline `11/11`·`13/13`은 이 검사가 **전혀 없던** 조건에서 기록됐다. 또한 `dump_ui()` raise는 `_verify_text`의 `max_retries=3` 재시도 루프를 **1회에 붕괴**시켜(action_runner.py:305-311), 11개 verify_text가 baseline보다 **더 취약**해진다. 반면 canonical 팔은 `shell_result` 기반으로 **이미 fail-closed**(action_runner.py:270-271·392-399, cli.py:380-383)라 strict가 추가하는 것이 없다.

부수 효과(의도된 것): `run_status`가 legacy↔canonical 판별자로 **보존**된다(부모 §9.3 step 5의 5개 비교항 중 하나).

`--strict-shell`은 구현·테스트하되 캠페인에서는 쓰지 않는다(후속 별도 라벨 진단 run용).

### A-3 (critical) 단말 정체를 **증거에 기록**

`cmd_run`에서:
```python
reporter.device_info = {
    **adb.get_device_info(),
    "serial_pinned": device_serial,          # None이면 그대로 None
    "serial_observed": adb.device_serial(),  # adb -s <S> get-serialno 결과
}
```
근거: **THOR2_J(`B2700125BW000083`)와 THOR2_K(`B06201249E0002F0`)가 둘 다 `AT-M140`**이고 동시 연결된 이력이 있다(`THOR2_K - Settings/SETTINGS_DEEPEN_PROBE_RESULTS_2026-06-09.md:3-4`). 현재 `get_device_info()`는 `{model, android_version}`만 반환(adb.py:108-111)하고 `summary.json`의 `device` 블록 전체가 그것이므로(reporter.py:181), **캠페인 증거가 어느 단말을 구동했는지 증명할 수 없다.** `reporter.py`는 수정하지 않는다(dict를 그대로 직렬화하므로 scope 내 `cli.py` 변경으로 충분).

### A-4 (important) 저장 속성명 구속: `self._device_serial`

`ADB.device_serial()`은 **기존 public 메서드**(adb.py:113)이며 `src/preflight.py:273`이 `adb.device_serial()`로 호출한다. `self.device_serial = ...`로 저장하면 메서드를 가려 `TypeError: 'str' object is not callable`. 반드시 `self._device_serial`.

### A-5 (important) `None` serial은 **명시 전달이어도** unpinned

`scripts/menu_mapper.py:374`·`scripts/settings_tree_explorer.py:603`이 `ADB(device_serial=args.serial)`로 **None을 명시 전달**한다(`--serial` 기본값 없음). sentinel 기반 "kwarg가 전달됐는가" 판정 금지 — **`None` = unpinned**, 거부 대상은 **non-None 공백/whitespace 포함 값**뿐.

### A-6 (important) 잘못된 `--serial`은 stderr + exit 1

traceback 금지. `src/cli.py:322-324`(`--run-id` 검증)와 동일한 형태로 ERROR 출력 후 `sys.exit(1)`, **ADB 생성 이전**.

### A-7 (important) checked cleanup은 `strict_shell=True`에만

설계 §6 2문단이 무조건절로 읽혀 unpinned 경로까지 오염된다. `src/preflight.py:349/371`·`src/app_explorer.py:138/157`은 unpinned `ADB()`를 쓰고 warn-only(`except Exception`)라, 무조건 checked cleanup은 정상 단말 manifest를 `xml_dump_failed`/`screenshot_failed`로 **거짓 강등**시킨다. unpinned은 **경로 변경 + `finally` cleanup 시도**만, 신규 실패 표면 0.

### A-8 (important) strict 하에서 legacy load-SKIP은 치명

`--strict-shell` 지정 시 legacy `load_tc`의 `TCValidationError`는 `SKIP + continue`(cli.py:364-366)가 아니라 **invocation 중단 + 비정상 종료**. (`--serial` 단독에서는 현행 유지.)

### A-9 (important) ledger 동결은 **byte** 기준

`src/adb.py`는 ledger actor source이므로 새 digest·새 출력 디렉토리가 생긴다. 그러나 actor 파일 해시는 **SUMMARY §1에만** 나타나고 CSV row에는 없다. 따라서:

- **신규 세대의 `contract_drift_matrix.csv`는 `16ee5ae8ca8f55c4`의 CSV와 byte-identical이어야 한다.**
- SUMMARY는 `input_digest` / `out_dir prefix` / `src/adb.py` 해시 줄 / CSV sha 줄 외에는 동일해야 한다.
- `shell()`의 subprocess `timeout=` **인자 값·타입 불변**(예: `shell_result`로 위임하며 `float(timeout)`가 되면 frozen row의 `"subprocess_timeout":5`가 `5.0`으로 바뀌어 카운트는 그대로인 채 CSV 해시만 달라진다 — count-only 대조로는 못 잡는다).
- 임의의 row/verdict/count 변화는 baseline 자동 갱신이 아니라 **STOP**.

### A-10 (important) 재시도 의미론 명시

설계 §5.3의 열거에 **`dump_ui`/`screenshot`을 포함**하고, strict 모드에서 이들의 실패가 verifier 재시도 루프를 1회로 붕괴시킨다는 점을 명시(A-2로 캠페인 영향은 제거되지만 `--strict-shell` 사용자에게는 유효한 계약).

### A-11 (important) `/data/local/tmp` 미검증 — 사전 probe 필수

repo 내 검증된 `uiautomator dump` 사례는 **전부 `/sdcard`**(`docs/tc_patterns.md:24`, `docs/talkback_dpad_verification.md:44`, `ODIN2 - Engineer IMS/VERIFY_PROTOCOL.md:60,64,68`, `THOR2_K - Settings/SETTINGS_DEEPEN_PROBE_RESULTS_2026-06-09.md:14`). AT-M140 계열에서 `/data/local/tmp` 쓰기 성공 근거가 **없다**. 설계 §3은 D0 중 단말 명령 0을 요구하고 §8은 `/sdcard` fallback을 금지하므로, 실패는 **캠페인 run 1의 SMOKE_01 step 5**에서 처음 드러난다.

→ 후속 device 지시서에 **step 0 read-only probe**를 필수로 넣는다:
```text
adb -s <S> shell 'uiautomator dump /data/local/tmp/tc_runner_ui_dump.xml && cat /data/local/tmp/tc_runner_ui_dump.xml | head -c 200 && rm -f /data/local/tmp/tc_runner_ui_dump.xml'
adb -s <S> shell 'screencap -p /data/local/tmp/tc_runner_screenshot_tmp.png && rm -f /data/local/tmp/tc_runner_screenshot_tmp.png'
```
실패 시 **D0 설계 STOP**(캠페인 결과 아님).

### A-12 (important) 캠페인 창 동안 다른 CLI 명령 금지

`cli devices`(cli.py:442)·`cli explore`(:577)·`cli preflight`(:692)는 **bare `ADB()`로 남는다**(D0는 `cmd_run`만 핀). 특히 `cli preflight`는 dumpsys/uiautomator dump/screencap을 unpinned로 구동한다. 후속 device 지시서에 "4-run 창 동안 `run --serial <S>` 외 tc-runner CLI 명령 금지"를 명문화. 설계 §5.1에도 "devices/explore/preflight는 의도적으로 unpinned 유지"를 명시.

### A-13 (important) 결과 증거 게이트 보강 (설계 §11)

기존 4항목에 추가:
- **0.** `reports/<run-id>/`가 **사전에 존재하지 않을 것** (reporter가 `exist_ok=True` + `open(w)`라 재호출 시 원본 증거를 덮어쓰고 게이트가 그 대체본을 승인함 — reporter.py:170-172,186)
- **5.** `summary.json`의 `device.serial_pinned == device.serial_observed == B2700125BW000083` (A-3)
- **6.** `summary.json`의 `contract_mode`가 그 run의 의도 모드와 일치 (runs 1-2 legacy / 3-4 canonical). 누락 시 `--contract-mode` 기본값 legacy 때문에 **legacy-vs-legacy 비교가 무해하게 통과**해 거짓 동등성 증거가 된다.
- **7.** 기대 cardinality를 **리터럴로 고정**: SMOKE_01 = 11 step, SMOKE_02 = 13 step, `len(results) == 1`. (`TCResult.is_pass`가 `all([])==True`라 step 0인 결과도 `passed: true`로 직렬화된다 — reporter.py:190-197.)
- **8.** run 전 `ls /data/local/tmp/` baseline 채록, run 후 `ls /data/local/tmp/tc_runner_*` 잔여 0 확인(read-only).

### A-14 (important) 비-목표 문구 정정 + divergence 판정표

**(a) §3 문구**: 승인된 TC는 실제로 상태를 바꾼다 — `am force-stop`(프로세스 종료 + PackageManager stopped-flag가 `packages.xml`에 영속) ×4, `am start -n`(포그라운드/태스크 변경) ×2, `input swipe` ×1. "no device-state mutation"은 사실과 다르다. → **"영속 설정(configuration) mutation 없음. 승인 TC의 process/navigation delta(`am force-stop`/`am start`/`input swipe`)가 유일하게 허용되는 상태 변화이며, 캠페인 종료 시 Settings는 force-stopped 상태로 남는다"** 로 정정하고 RESULT에 기록.

**(b) 판정표(사전 확정, §11에 삽입)**: divergence를 "environment failure"로 오보고하는 것을 차단한다.

| 관측 | 어휘 | 진단 | 조치 |
|---|---|---|---|
| 선언된 TC `shell` step에서 rc≠0이 메시지에 기록되며 실패 | `BUG-GAP observed` | `CONFIRMED` (기존 확정 결함 corroborate) | 기록 후 STOP·리뷰 |
| ADB helper(screencap/pull/uiautomator dump/cat/rm)에서 실패 | `NOTE` | `OBSERVED` | D0 transport 아티팩트 — STOP 후 설계 리뷰 복귀 (앱/단말 귀책 금지) |
| `verify_text`가 `Text '<X>' not found on screen`으로 실패 (rc 없음) | `BUG-GAP observed` | `OBSERVED` | 앱/단말 귀책 가능 유일 케이스 |
| 명령이 실행되지 않음(게이트 STOP 포함) | `미실행` + `NOTE` | — | 후속 run 전부 `미실행` |

**실행됐으나 실패한 run을 `미실행`으로 기록 금지. 표면화된 rc를 "environment failure"로 기록 금지.**
역사 기록 `11/11`·`13/13`은 소급 라벨 **`runtime PASS (legacy, rc-unchecked)`** 로 표기한다.
메시지 형태 차이(legacy=예외 문자열 vs canonical=`Shell rc=…` 구조화)는 **by-construction**이며 semantic mismatch가 아니다.

---

## 2. TDD 구현 계획

파일 범위 **정확히 4개**: `src/cli.py` · `src/adb.py` · `tests/test_cli.py` · `tests/test_adb.py`. (설계 문서 갱신은 별개·untracked.)

RED → GREEN 순서로 진행하고, 각 단계에서 **실패를 실제로 관찰**한 뒤 구현한다.

**S1. ADB transport (`src/adb.py`)**
- `ADB(device_serial=None, *, strict_shell=False)` — A-1/A-4/A-5 준수. 검증: non-None 공백/whitespace 거부(`ValueError`), `None`은 unpinned.
- `is_connected()`: pin 있으면 `adb -s <S> get-state`, rc 0 + trim된 stdout `device`만 True. timeout/FileNotFoundError → False, **unpinned `adb devices`로 재시도 금지**. pin 없으면 기존 경로 유지.
- `shell()`: `strict_shell=False`면 **현행 그대로**(stdout 반환, rc 무시 — A-1·A-9). `True`면 rc≠0에서 typed error(rc + stdout/stderr 각 200자) raise. subprocess `timeout=` 인자 **원형 보존**(A-9).
- 원격 경로 2종을 `/data/local/tmp/tc_runner_screenshot_tmp.png` · `/data/local/tmp/tc_runner_ui_dump.xml`로 변경. cleanup은 `finally`. checked creation/transfer/cleanup은 **strict에서만**(A-7). cleanup 실패가 선행 예외를 가리지 않을 것.

**S2. CLI (`src/cli.py`)**
- `run` 서브커맨드에 `--serial`·`--strict-shell` 추가(다른 서브커맨드 불변 — A-12).
- `cmd_run`: serial 검증 실패 → stderr + exit 1, **ADB 생성 전**(A-6). 생성점은 현행 `cli.py:312` 유지(canonical은 host preflight 이후 그대로).
- `device_info`에 `serial_pinned`/`serial_observed` 병합(A-3).
- `--strict-shell` 지정 시에만: pinned any-step abort(legacy 포함) + `run_status=ABORTED_FAIL_CLOSED` + load-SKIP 치명(A-8). 순서 = 실패 StepResult append → status → summary write → 비정상 종료. **`--serial` 단독은 실행 의미론 불변**(A-2).

**S3. 테스트 (설계 §9의 15항목 + 아래 추가)**
- `ADB("PROBE_SERIAL").shell()`이 rc≠0에서 stdout 반환 (A-1 잠금)
- `ADB(device_serial=None)` 명시 전달이 unpinned로 동작 (A-5)
- `self._device_serial` 저장 + `device_serial()` 메서드 호출 가능 유지 (A-4)
- `--serial` 단독 run이 legacy 계속 진행 정책을 **바꾸지 않음** (A-2)
- `--strict-shell` 지정 시 any-step abort + `ABORTED_FAIL_CLOSED` (A-2)
- unpinned screenshot/dump_ui가 cleanup 실패로 **새로 실패하지 않음** (A-7)
- `device_info`에 `serial_pinned`/`serial_observed` 직렬화 (A-3)

---

## 3. 완료 게이트

1. `venv/Scripts/python.exe -m pytest tests/test_adb.py tests/test_cli.py -q` 무실패
2. `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` 무실패, **1293 초과**(신규만 증가) — 사라진 nodeid **0**(`--collect-only -q` 대조로 증명)
3. ledger 재생성: `scripts/contract_drift_ledger.py --out-dir reports/contract_drift --verify-determinism --fail-on-blocking`
   → determinism exit 0 확인 후 blocking 12로 exit 1(정상). **신규 CSV가 `16ee5ae8ca8f55c4/contract_drift_matrix.csv`와 byte-identical**임을 해시로 증명(A-9). SUMMARY 차이는 digest·adb 해시·CSV sha 줄로 한정.
4. 독립 2회 실행 byte 동일 + 신규 digest 기록
5. `tools/untracked_contamination_scan.py` 0 · `git diff --name-only`가 **정확히 4파일**(사용자 트랙 `THOR2_J_missed_call_issue/` 3파일 제외) · staged 0
6. **STOP** — commit·push 금지(별도 승인), Part B 단말 진입 금지(§4 선결)

보고: A-1~A-14 반영 위치 / 테스트 수치 / CSV byte-identical 증명 / 신규 digest / 4파일 sha256 / git 상태.

---

## 4. Part B 진입 선결 조건 (사용자 결정 — Codex 판단 금지)

**캠페인은 현 단말 상태에서 성립하지 않는다.** 승인 TC 2건은 precondition `persist.sys.locale=ja`를 선언하는데, 2026-07-22 관측은 `persist.sys.locale=en-US`(`ro.product.locale=ja-JP`는 공장 기본값)다. 즉 UI가 영어이므로 일본어 앵커(`設定`·`設定を検索`·`ネットワークとインターネット`…)는 SMOKE_01 step 5부터 실패한다. 설계 §3은 locale mutation을 금지하므로 §7 게이트는 `NOTE` + `미실행` STOP으로 귀결된다.

따라서 Part B는 **사용자가 다음 중 하나를 결정**해야 진입 가능하다:
- (a) 단말 언어를 **일본어로 수동 설정**한 뒤 창 개시 (사람이 Settings UI에서 수행 — 자동화가 locale을 쓰지 않는다)
- (b) `미실행(NOTE)`로 기록하고 device differential을 보류 (cutover는 canonical opt-in 유지)

결정 전까지 **D0는 standalone 안전·ledger 작업으로만 정당화**되며, 캠페인 완주를 전제한 서술을 보고서에 쓰지 않는다.

---

## 5. 커밋 경계

D0 4파일은 구현·검증·ledger 재생성·리뷰 **이후 별도 명시 승인**으로만 1개 micro-commit. `0937895` amend 금지. push 별도 게이트. 설계 문서·지시서 포함 여부는 사용자 결정.
제안 제목: `fix(device): pin adb serial and confine temporary artifacts`
