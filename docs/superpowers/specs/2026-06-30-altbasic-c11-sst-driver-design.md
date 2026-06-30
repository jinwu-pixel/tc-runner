# ALT Basic batch10 — C11 SST v1a chunk driver (design)

- date: 2026-06-30
- track: THOR2 ALT Basic — Part B (batch10 236 device-validation), 점진 dispatch 러너 1번째 increment
- device: F0 `B06201249E0002F0` (RY07260601S, ko-KR, simple-mode). B27 미접촉.
- 선행 결정: Part B(사용자 A→B) → Approach A(점진 dispatch 러너) → 청크 C11 → v1 core 12 → **v1a = SST 5**(디바이스 launch 실측 후 refine).
- 관련: C01 narrow 선례 `2026-06-26-altbasic-c01-narrow-driver-design.md`. §2.5(코드=thor2j, 계약/manifest/yaml=tc-runner). 글로벌 commit 정책 → spec commit은 EOD batch defer.

## 1. 목표 / 스코프

batch10 236 큐를 실행할 러너가 없음(현 커버: C01 narrow 4 + batch11 12). Part B 진짜 병목 = 러너. **점진 빌드**로 가장 tractable한 청크부터 1 device-window씩 GREEN화한다. 범용 dispatch 엔진을 선만들지 않는다(YAGNI — 2~3 청크 후 공통형 추출).

**v1a 대상 = SST 5** (9.Simple settings, 전건 verify_text·NAVIGATION_ONLY·denylist/PII 0):

| tc_id | entry (manifest) | verify literal (all-of) |
|---|---|---|
| ALTBASIC_SST_008 | 쉬운 설정 > press_key 방향키/OK | 소리 및 진동 |
| ALTBASIC_SST_012 | 쉬운 설정 > WiFi tap | 네트워크 및 인터넷 / WiFi |
| ALTBASIC_SST_013 | 쉬운 설정 > 배경화면 및 스타일 tap | 테마 및 배경화면 |
| ALTBASIC_SST_014 | 쉬운 설정 > 디스플레이 tap | 디스플레이 |
| ALTBASIC_SST_015 | 쉬운 설정 > 안심기능 tap | 안심기능 |

**성공 기준**: SST 5 중 launch·dump·literal이 도달한 건은 **TWO_RUN_GREEN(run1∧run2)** → RUNNABLE_NOW 회수. 비도달은 정직 분류(ENTRY_FAILED / LITERAL_PENDING / DEVICE_FIT_SKIP). 부수 목표 = dispatch+tap-nav+literal 아키텍처 end-to-end 검증.

**3축 점검**: 데이터 남음(evidence + RESULT_RECOVERY + literal backfill) / 정확·재현(2-run green only, 발명 0) / 누적(러너·키사전·launch 경로 = 다음 청크 재사용).

## 2. 디바이스 실측 (2026-06-30, read-only, 본 설계 근거)

- F0 단독연결, RY07260601S ko-KR, simple-mode 홈 = `com.hnlens.simplemode/.ui.home.MainActivity`.
- **화면 OFF → `uiautomator dump` null root** (간편모드 a11y-불투명 아님 — 화면 wake 후 정상 dump, BSC_015 GREEN과 정합). 러너는 **각 TC 시작 시 WAKEUP 보장** 필요.
- 홈 타일(awake dump 15라벨): 전화·메시지·카메라·갤러리·라디오·**설정** + 시계/날씨 위젯. → **SST(쉬운설정) launch = 홈 "설정" tap**(실측 tappable).
- 설치 확인: `com.hnlens.pedometer`(만보기)·`com.hnlens.magnifying`(돋보기) 존재하나 홈 p1 부재 → **PDM/MGN launch는 발견 선결(v1b)**.
- `am start` 직접기동 = §7 denylist → launch는 실 UI 경로(홈 tap)만.

## 3. 아키텍처 (C01 패턴 확장, no-fork)

**신규 순수 모듈 `runner/altbasic_c11.py`** (host-TDD, appium 0) — `altbasic_narrow as N` **import-only**:
- 재사용(import): `N.parse_entry_detail`, `N.literal_decision`(all-of present=PASS/부분=PENDING/전무=ABSENT), result code 상수, `N.KEY_DICT` 기반.
- 신규:
  - `C11_KEY_DICT` = `{**N.KEY_DICT, ...DPAD/OK 후보}` — 방향키/OK candidate keycode(DPAD_UP19/DOWN20/LEFT21/RIGHT22/CENTER(OK)23). **candidate = run1 device-verify**(no-guess; 미해석은 fail-closed). "방향키 or OK" 모호키 = OK(23) 우선.
  - `parse_sst_entry(entry_detail)` → `(launch_step, action_steps)`. **실제 manifest 문법 기준**(`N.parse_entry_detail`로 `>` 분할; golden은 SST 5행 verbatim):
    - step1 = launch — body에 `쉬운 설정` 또는 `Simple setting` 포함 시 action prefix가 `press_key`/`tap` **어느 쪽이어도 launch token으로 인정**(실측: SST_008=`press_key:쉬운 설정`, SST_012~015=`tap:방향키로 Simple setting`).
    - step2 = bare(콜론 prefix 없음). `WiFi tap`/`디스플레이 tap`/`배경화면 및 스타일 tap`/`안심기능 tap` → 말미 `tap` 제거 → **`tap:<label>`로 정규화**. `Press 방향키 or OK` → **`press_key OK(23) candidate, run1 device-verify required`**로 정규화.
  - `classify_sst(tc_id, entry_detail, vc)` → `SST_TAPNAV`(launch + tap label + literal: 012~015) / `SST_KEY`(launch + press_key OK + literal: 008) / `FAIL_CLOSED`(launch 미인식·label 미정규화·모호·미해석). C01 분류기가 tap-nav를 FAIL_CLOSED하던 것을 SST용으로 명시 지원.

**device executor `runner/altbasic_c11_driver.py`** (appium lazy import, import-safe until --run) — C01 driver 자산 import-only 재사용:
- **`b1`는 `run` 경로 안에서만 lazy import** (`import altbasic_validation_batch1 as b1`; b1은 top-level에서 appium import하므로 모듈을 import-safe 유지 — C01 driver 동일). `b1.run_one(tc, fn, run_no)` 세션(helper 생명주기·pre/post pkg snapshot·uninstall) + `v`(`.home()/.evidence()/.src()/.d.press_keycode()/.tap_text(t,partial=)`). **`v.wake()` 메서드 없음** → §4 `_ensure_awake(v)` 사용(b1 무수정).
- C01 driver(`altbasic_c01_driver`)에서 import: `check_literal`, `_literals`(vc→literal 리스트), `_text_set`, `_record`. (private 재사용 = fork 회피; 공통화 리팩터는 별도 티켓 — §2.3.)
- `PINNED_UDID = "B06201249E0002F0"`; `b1.UDID != PINNED_UDID` → **ABORT**(wrong-device 가드).
- `EV_REL = ("evidence", "altbasic_batch10_c11sst_<runtag>")` — C01 evidence와 분리.

## 4. per-TC 실행 흐름 (NAVIGATION_ONLY)

```
_ensure_awake(v)                      # C11 driver 내부 헬퍼: v.d.press_keycode(224) → sleep → v.src() sanity (b1 무수정·v.wake() 없음; 실측: screen-off면 dump null)
v.home(); v.evidence("home")
launch: v.tap_text("설정")            # 간편모드 홈 설정 타일 → 쉬운설정 (run1 진입경로 확정·backfill)
  └ tap 실패 → ENTRY_FAILED
SST_KEY (008):   v.d.press_keycode(C11_KEY_DICT[OK])   # 방향키/OK
SST_TAPNAV(012~015): v.tap_text(<menu label>, partial=True)   # 디스플레이/안심기능/배경화면 및 스타일/WiFi
  └ tap 실패(미발견/스크롤 필요) → ENTRY_FAILED (실측 text 채록)
v.evidence("after"); dump = v.src()
check_literal(dump, expected_all_of):
  LIT_PASS    → "PASS"
  LIT_PENDING → LITERAL_PENDING (의미일치·표기차, 실측 literal 채록, 발명 0)
  LIT_ABSENT  → VERIFIER_FAILED
cleanup: Back(설정 root 복귀) → v.home()   # 다음 TC 독립
```

- 각 TC run1/run2 독립. TWO_RUN_GREEN(run1 PASS ∧ run2 PASS)만 승격.
- tap = **메뉴 진입(네비게이션)만** — 토글/값변경/저장 0. risk_note "설정 변경 금지" 준수.

## 5. 안전 / mutation 0

- 전건 NAVIGATION_ONLY: launch tap + 메뉴 tap/press_key + dump + Back/HOME. 설정 토글·항목삭제·발신 0.
- 위험 tap denylist(batch11/R2 재사용) 준수: `켜기/사용 설정/시작/전송/연결/확인(영속)/저장/삭제/전원 끄기/SOS/am start` 0. **SST_016(Emergency, §6 SOS) = v1a 제외**.
- helper 생명주기 = `b1.run_one`(pre/post `pm list packages` snapshot, `io.appium.*` uninstall, 잔존 0).
- redaction: SST sheet = `not_required`. evidence(xml/png) local-only, 미커밋.

## 6. 2-run / 산출

- run1 = discovery(진입경로·실측 literal 채록) + verify, run2 = 독립 재현. 결과코드 = `altbasic_narrow` 상수 재사용.
- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_c11sst_<runtag>/run{1,2}/{tc_id}/` (xml+png, local-only) + `results_run{1,2}.csv`.
- 회수: tc-runner `RESULT_RECOVERY_BATCH10_C11SST_2026-06-30.md`(RUNNABLE / LITERAL_PENDING / ENTRY_FAILED 분리). literal/entry 확정분 → STAGE1 yaml 환류(별도 무단말 보정 라운드, §4 backfill 포맷).

## 7. 테스트 (host-TDD, 단말 0)

순수 모듈 `altbasic_c11.py`만 host-test (device I/O는 b1 경유·테스트 제외, C01 split 동일):
- `C11_KEY_DICT`: 방향키/OK 후보 매핑 존재, 미등록키 → None(no-guess).
- `parse_sst_entry`: **golden = 실제 SST 5행 entry_detail verbatim**. step1 launch 인정(press_key/tap 양쪽), step2 bare `<label> tap`→`tap:<label>` 정규화·`Press 방향키 or OK`→`press_key OK(candidate)`, 모호·빈 entry → FAIL_CLOSED.
- `classify_sst`: SST 5 → SST_TAPNAV(012~015)/SST_KEY(008), launch 미인식·label 미정규화 → FAIL_CLOSED.
- `N.literal_decision` 재사용 검증(all-of/부분/전무) + multi-literal(SST_012 2개) 분해.
- import-safe: `--run` 없이 appium import 0.

## 8. 위험 / 한계

- **launch 동치 가정**: 홈 "설정" = 쉬운설정(simple settings)인지 run1 확정. full Android Settings로 빠지면 메뉴 라벨 상이 → ENTRY_FAILED/실측 채록 후 경로 보정.
- **메뉴 스크롤**: 디스플레이/안심기능 등이 below-fold면 tap_text 실패 → run1에서 스크롤 필요 판정(v1a는 1스크롤 probe까지, 초과는 ENTRY_FAILED).
- **DPAD 매핑 미검증**: SST_008 방향키/OK candidate는 run1 device-verify(no-guess).
- literal paraphrase(confidence 0.5) → 표기차는 LITERAL_PENDING(FAIL 아님), 실측 환류.

## 9. Out of scope (v1a)

- PDM 5(만보기)·MGN 2(돋보기) = v1b(launch 발견 선결). MGN_005/006·PFW 6·SST_016 = 이후 increment.
- 범용 dispatch 엔진 추출(2~3 청크 후). C01 driver 공통 device-helper 리팩터(별도 티켓).
- STAGE1 yaml backfill 실행(run1 후 별도 무단말 라운드).

## 10. §2.5 / commit 경계

- 코드(`altbasic_c11.py`, `altbasic_c11_driver.py`, tests) = thor2j-tc-appium side. spec/manifest/yaml/RESULT = tc-runner side. cross-commit 금지.
- 본 spec 및 모든 산출물 commit = 사용자 명시 승인 또는 EOD batch까지 defer(글로벌 정책). 작업 중 commit/push 0.
