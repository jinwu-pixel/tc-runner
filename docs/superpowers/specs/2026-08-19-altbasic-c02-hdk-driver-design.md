# ALT Basic batch10 — C02 (11.Hard Key) driver slice v1 설계 (2026-08-19)

**입력**: C02 discovery run (2026-08-19, `DISCOVERY_C02_LEDGER_2026-08-19.csv` + `DISCOVERY_C02_HDK_SUMMARY_2026-08-19.md`, Codex 실행·Claude 재검증) + backfill 11 yaml (동일자) + NAVI_ALL Excel 재판독.
**선례**: C11 driver (`runner/altbasic_c11*.py`, spec 2026-06-30) — 구조·no-guess·fail-closed 원칙 승계.
**차별점**: C02 는 전 TC keyevent-only → **Appium 불요, 순수 adb driver** (helper 설치 0 = mutation 표면 축소).

## 1. 스코프 — v1 drivable 13 / registry 16

**C02_V1 (device 2-run 대상 13)**:

| disposition | tc_id | 요지 |
|---|---|---|
| `HDK_LAUNCH_KEY` | 021, 022 | 하드키(207/27) → 목적지 literal (backfill 확정) |
| `HDK_HOME_FOCUS` | 035, 036, 037, 038 | 홈 DPAD short+long → focus_move (baseline 대비 최종 focused identity 변경) |
| `HDK_POWER_MENU` | 054 | `--longpress 26` → 팝업 3-label 게이트 → ↓=`다시 시작` / ↑=`긴급 전화` focused label → BACK 원복 |
| `HDK_SETTINGS_NAV` | 096, 097, 099, 100, 101, 102 | 홈 설정 타일 OK → root 게이트 → DOWN-to-label → (OK) → literal → BACK 원복 |

**registry (device 무접촉 기록 — run 시 사유 출력)**:

| bucket | tc_id | 해소 조건 |
|---|---|---|
| `C02_KEYCODE_UNRESOLVED` | 023, 055, 056 | 메시지 키 keycode discovery (65=Gmail 반증 완료, 2차 후보 시험 승인 대기) |
| `C02_FIXTURE_PENDING` | 016, 062, 070 | 빈 최근앱 fixture(모두 닫기=mutation) / 연락처 존재 fixture — 정책 승인 대기 |
| `C02_RESCOPE_PENDING` | 041, 042, 064, 098, 046 | NAVI_ALL any-key 재정의(§4) / 098 2-depth 경로 / 046 swipe 허용 — 사용자 승인 대기 |
| `C02_DIVERGENCE` | 019, 050, 052, 053, 094 | spec-device 불일치 재판정(§5) — BUG-GAP 후보 포함 |

합계 13 + 16 = 29 (chunk 전수).

## 2. 모듈 구조 (thor2j-tc-appium side, §2.5 cross-commit 금지)

| 파일 | 내용 |
|---|---|
| `runner/altbasic_c02.py` | **순수** (no adb import): keycode 사전(확정분만: 187/3/207/27/19-23/4/26), `ROOT_ORDER` 18항목(discovery 실측), `classify_c02(tc_id)` → disposition/registry, `build_key_plan(tc_id)` → KeyPlan(step 목록: keycode·longpress·verify 종류·expected), dump 파서(`focused_node(xml)` → (resource-id, text, bounds) / `text_present(xml, literal)` — **XML entity unescape 필수**(`&#10;`→`\n`, HDK_021 개행 literal)), `settings_nav_plan(target_label)` → DOWN 횟수 상한 25·anchor 게이트 |
| `runner/altbasic_c02_driver.py` | adb-only executor: `PINNED_UDID="B06201249E0002F0"` 전 호출 `-s` 핀, `_ensure_awake`(kc224+dump null 가드), settings stale-task heal(BACK×8→HOME→재진입 1회 — C11 R1 패턴), per-disposition runner, evidence 기록, `--dry-run`/`--run {1,2}`/`--only` CLI (C11 동일) |
| `tests/test_altbasic_c02.py` | host-TDD (synthetic dump fixture, RED→GREEN) |

`ROOT_ORDER` (Settings root, discovery 실측 순서): 네트워크 및 인터넷 / 연결된 기기 / 해외 로밍 / 앱 / 안심 기능 / 알림 / 알림 읽어주기 / 배터리 / 저장용량 / 소리 및 진동 / 디스플레이 / 배경화면 및 스타일 / 모드 설정 / 접근성 / 보안 / 개인 정보 보호 / 위치 / 안전 및 긴급 상황

## 3. verify 의미론 (fail-closed)

- **literal**: dump text attr 기준 substring — 단 HDK_100 류 substring 위양성(`잠금 디스플레이`⊃`디스플레이`)은 backfill 단계에서 이미 회피(`밝기` 확정). `text_present`는 entity unescape 후 비교.
- **focus_move (035~038)**: s1_pre baseline focused identity(rid+text+bounds) vs 최종 post — **변경 또는 생성 = PASS**. 경계 정지·가속(long) 의미는 **비단정**(dump 전부 보존, NOTE). 무초점 초기(035 실측) 허용.
- **focus label (054, 096)**: post dump focused 노드의 text/자식 text == 기대 label (054: `다시 시작`→`긴급 전화` / 096: `디스플레이` — ROOT_ORDER 상 소리 및 진동 차하 grounded). 096은 OK 미발신.
- **T2 가드**: literal 노출 + focus 반증 공존 시 승격 금지 → `VERIFIER_GAP` 기록 (handoff §3).

## 4. 안전 (hard guard — 코드 강제)

- `HDK_POWER_MENU` runner는 **keycode 23(OK) 발신 경로 자체가 없음** (key plan 생성기가 23 포함 시 pure 단계 예외). 이탈 = BACK 고정, cleanup 후 팝업 부재 재확인.
- `HDK_SETTINGS_NAV` OK 발신은 **plan 상 명시된 target 1회만**. Wi-Fi/토글/값 변경 keycode 시퀀스 생성 금지.
- 102: 진입 literal 확인 후 즉시 BACK (SOS/긴급 항목 위 OK 금지 — plan 에 OK 1회만 존재).
- pkg pre/post diff 0 + remote temp(`/data/local/tmp`) 세션분 정리 + MediaStore 오염 0 (`/sdcard` 사용 금지).
- B27(`B2700125BW000083`)/타 단말 감지 시 즉시 abort.

## 5. 재판정 대기 항목 (driver 범위 밖 — 사용자 결정)

1. **NAVI_ALL any-key 재정의** (041/042/064): Excel 재판독 확정 — "Navi 키(모든/전체)" = 임의 방향키(무초점→첫 초점 활성). re-scope 안 = 4방향 전수(각 시행 전 무초점 상태 요구 — **초점 clear 동선 미확보**, 차기 device discovery 필요) 또는 대표 1키+NOTE. 참고: KT FAIL 이력 BTS 21069(최초 포커스 갤러리) = 초기 포커스 위치가 본 TC군의 실제 결함 이력.
2. **052/053 초점 순환 부재**: 스펙 "순환" vs 실측 boundary stop — BUG-GAP observed 후보 vs 스펙 re-scope(boundary-stop 수용) 결정.
3. **019 홈 길게=퀵패널 미개방 / 050 BACK 분할복귀 없음**: 동일 축 (spec-device gap).
4. **094 root 항목 부재** (`텍스트 크기`/`Wifi`): 부분 re-scope(실측 root 기준) vs spec-gap.
5. **098 2-depth 경로** (네트워크 및 인터넷→Wi-Fi): precondition re-scope (SST_012 선례).

## 6. host-TDD 케이스 (필수 커버)

classify 29/29 전수 매핑(등록 외 tc_id = fail-closed) / key plan: 각 disposition 별 생성·**power-menu plan 에 23 부재 assert**·미등록 키 예외 / `focused_node`: focused 0·1·중첩 / `text_present`: 개행 literal(`&#10;`)·미노출·entity / settings_nav: target 도달·상한 초과 fail·anchor 게이트 / stale-heal 판정 함수. 전부 synthetic fixture (device 0).

## 7. 실행 프로토콜 (차기 device 창)

run1/run2 독립 → `TWO_RUN_GREEN` 만 RUNNABLE_NOW 후보 (판정 = 오케스트레이터). evidence `evidence/altbasic_batch10_c02_v1_<date>/run{n}/{tc_id}/` local-only. registry 16 은 무접촉 사유 기록만.

## 8. 상태

- [x] 설계 lock (본 문서)
- [ ] host-TDD 구현 (thor2j 3파일) — RED→GREEN
- [ ] Claude 독립 재검증 (test 재실행·dry-run 29 매핑 검사)
- [ ] device 2-run (별도 승인)
- 커밋: 전부 batch 대기 (글로벌 정책)

---

## §9 개정 v1.1 (2026-08-19, device 2-run 후속 — 승인 후 구현 완료)

근거 = `RESULT_RECOVERY_BATCH10_C02_2026-08-19.md` 후속 측정 1~5 + catalog `KEY-001~010`·`STR-010/011`.

### 9.1 스코프 변경 — drivable **13 → 14**, registry **16 → 15**

| tc_id | 변경 | 근거 |
|---|---|---|
| HDK_056 | registry(`C02_KEYCODE_UNRESOLVED`) → **drivable `HDK_MSG_FOCUS`** | 메시지 keycode 132 압인 확정 + content-desc verifier 확보 |
| HDK_055 | `C02_KEYCODE_UNRESOLVED` → `C02_RESCOPE_PENDING` | keycode 해소되나 step-1(any-key) 전제가 **cold entry 에서만 성립** — focus carryover 실측 |
| HDK_050 | `C02_DIVERGENCE` → `C02_RESCOPE_PENDING` | discovery 의 divergence 판정 **근거 무효**(precondition·키 둘 다 오설정) |
| HDK_021 | keycode **207 → 131** | 물리 '연락처' = `KEY_F1` getevent 압인 확정. 207 은 프레임워크 주입 경로 |

### 9.2 신규 계약

- **`FORBIDDEN_KEYCODES = {134}`** + `_assert_no_forbidden()` — **전 plan 공통** hard guard(기존
  `_assert_no_ok` 은 power-menu 한정이었음). 134 = SOS(`gpio-keys KEY_F4`, **소거법 추론·미압인**).
  추론이 틀려도 금지 비용 0 이므로 안전측 결박.
- **content-desc verifier 3종**: `desc_focus`(focused 노드 desc 일치) / `desc_present`(desc 존재)
  / `desc_focus_soft`(탐색 중 도달 확인 — **미도달이 FAIL 아님**). 근거 = '옵션 더보기'는 text 속성이
  없고 content-desc 만 존재 → 기존 text 기반 verifier 로 검증 불가.
- **`seek_desc_plan(target_desc, direction, budget)`** — 탐색형 anchor(budget 1..8, 범위 밖 fail-closed).
  **고정 시퀀스 가정 금지**가 설계 원칙으로 승격: 메시지 앱은 재진입 시 focus carryover 가 있어
  출발점이 일정하지 않다(실측). driver 는 도달 즉시 잔여 seek 스텝을 skip.
- 물리키 상수화: `contacts_hw=131` / `message_hw=132` / `favorite_hw=133` / `cancel=67`(★BACK 아님).

### 9.3 미해소 (본 개정 범위 밖)

HDK_037 처리 결정 · NAVI_ALL 재정의(041/042/064/055) · fixture 정책(016/023/062/070) ·
퀵패널 자연 진입 경로(STR-010 — **QPN 44 공통 게이트**) · 023 설정 메뉴 개방 승인.

### 9.4 상태

- [x] host-TDD GREEN (신규 12 포함 **55 passed**, altbasic 계열 **120 passed**)
- [x] canonical backfill 2 (HDK_055/056) + manifest 재생성 · STAGE1 static 271/271 PASS
- [ ] device 2-run (021 re-scope 재검증 + 056 신규) — 다음 device 창
