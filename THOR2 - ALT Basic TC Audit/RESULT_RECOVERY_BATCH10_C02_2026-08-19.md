# RESULT — batch10 Part B C02 (11.Hard Key) F0 device 2-run 회수 (2026-08-19)

선행: [RUNSHEET_C02_HDK_DISCOVERY_2026-08-19.md](RUNSHEET_C02_HDK_DISCOVERY_2026-08-19.md) → [DISCOVERY_C02_HDK_SUMMARY_2026-08-19.md](DISCOVERY_C02_HDK_SUMMARY_2026-08-19.md) (discovery, Codex 실행·Claude 재검증) → backfill 11 yaml → driver slice v1 (spec `docs/superpowers/specs/2026-08-19-altbasic-c02-hdk-driver-design.md`) → **본 문서 = fresh 2-run**.

## 결론

- **TWO_RUN_GREEN 12 / drivable 13** → **RUNNABLE_NOW 후보 +12** (C02 chunk).
- **HDK_037 = 미승격** (`VERIFIER_FAILED` run2) — driver 결함 아님, **focus 유지 비결정성 `OBSERVED`** (§아래).
- registry 16 = 무접촉 사유 기록만 (device 미접촉 정상).
- mutation 0: pkg 219==219 diff 0 · io.appium 잔존 0 · 세션 remote temp 0 · MediaStore 신규 0.

## 환경

| 항목 | 값 |
|---|---|
| 단말 | F0 `B06201249E0002F0` 단독 (AT-M140, `RY07260601S`, ko-KR, pkg 219) |
| driver | thor2j `runner/altbasic_c02.py` + `altbasic_c02_driver.py` (adb-only, Appium/helper 0) |
| host-TDD | 43 passed (신규 36 + run1 보정 7) · altbasic 계열 회귀 108 passed |
| evidence | `evidence/altbasic_batch10_c02_v1_20260819/run{1,2}/` XML 202 (101+101, 0-byte 0) + `results_run{1,2}.csv` — thor2j local-only |

## 결과 (drivable 13)

| tc_id | disposition | run1 | run2 | 판정 |
|---|---|---|---|---|
| HDK_021 | LAUNCH_KEY | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_022 | LAUNCH_KEY | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_035 | HOME_FOCUS | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_036 | HOME_FOCUS | PASS | PASS | **TWO_RUN_GREEN** |
| **HDK_037** | HOME_FOCUS | PASS | **VERIFIER_FAILED** | **미승격** |
| HDK_038 | HOME_FOCUS | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_054 | POWER_MENU | PASS | PASS | **TWO_RUN_GREEN** (OK 미발신) |
| HDK_096 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_097 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_099 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_100 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_101 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |
| HDK_102 | SETTINGS_NAV | PASS | PASS | **TWO_RUN_GREEN** |

registry 16 (무접촉): KEYCODE_UNRESOLVED 3 (023/055/056) · FIXTURE_PENDING 3 (016/062/070) · RESCOPE_PENDING 5 (041/042/046/064/098) · DIVERGENCE 5 (019/050/052/053/094).

## HDK_037 mismatch 규명 (evidence 기반)

| | run1 | run2 |
|---|---|---|
| short LEFT 후 | `rl_home_app` focused | `rl_home_app` focused (동일) |
| **long LEFT 후** | `rl_first` focused **유지** | **focused 노드 전무** |
| 화면 자체 | p0 단축다이얼 (75 node / focusable 25) | **동일** (75 node / focusable 25, texts 일치) |

- 양 run 모두 long-press LEFT 가 **홈 p1 → p0(단축다이얼) 페이지 전이**를 일으켰고, **도달 화면은 동일**하다. 차이는 **전이 후 focus 유지 여부 하나**뿐이다.
- dump 내용·노드 수는 동일했다. 다만 레이아웃 settle 과 focus 할당 완료가 같은 시점이라는 보장은 없으므로 이 관찰만으로 캡처 레이스를 배제할 수 없다 (초판은 배제했으나 **철회** — 후속 측정 1 참조).
- 진단 어휘: **`OBSERVED`** (2 run 1 조건 = §4.2 매트릭스 미충족 → `CONFIRMED` 아님). 정/역 재현·연속 n회 측정 미실시.
- **driver 정상 동작**: verifier 가 `focus_move` 를 fail-closed 로 잡아 **false-promotion 을 차단**했다. run2 직후 HDK_038 이 `baseline=None` 으로 시작해 PASS 한 것도 focus 소실 상태와 정합.
- 후속: **같은 날 40 시행 매트릭스 실시 → 후속 측정 1**. 승격 전 처리 결정 필요.

## run1 보정 이력 (관찰-보정 1회 — attempt1 → fresh 2-run)

- **attempt1 에서 SETTINGS_NAV 5건 `ENTRY_FAILED`**: driver 진입이 고정 시퀀스(HOME→UP→OK)였는데, **UP 이 `weather_view` 에 앉는 것**이 실측돼 설정 타일에 도달하지 못했다(discovery HDK_094 1회 관찰을 시퀀스로 일반화한 것이 원인). 096 후 settings task 스크롤 resume 으로 anchor 미노출도 겹쳤다.
- **보정(TDD RED 7 → GREEN)**: ① 홈 **dump-피드백 기하 라우팅** — '설정' 타일 bounds 와 focused bounds 의 delta 로 이동 방향 계산, `focused label == '설정'` 일 때만 OK 발신(fail-closed), 경계 고착 시 직교 축 1회 회피 후 중단 ② Settings root **UP-루프 정규화**(스크롤 resume 흡수, `ROOT_ORDER` 밖 label = `not_root` → heal) ③ entry 실패 시 dump 보존(`00_entry_fail`).
- attempt1 evidence 는 `..._attempt1/` 로 격리 보존(혼합 금지), **fresh 2-run 은 보정 후 동일 driver 로 run1·run2 독립 실행**.

## 안전 / 종료 게이트

| 게이트 | 결과 |
|---|---|
| 전원메뉴 OK 발신 | **0** (plan 생성 단계 hard guard `_assert_no_ok` — 코드·테스트 이중 확인) |
| HDK_102 OK | 1회 (진입 확인 후 즉시 BACK) — SOS/긴급 항목 접촉 0 |
| 값 변경·토글·발신·삭제 | 0 (전 plan 이 nav+literal/focus 만) |
| pkg pre/post | 219 / 219, diff **0** |
| io.appium 잔존 | 0 (helper 미설치 — adb-only) |
| 세션 remote temp | 0 (`altbasic_c02_ui.xml`·진단 `probe.xml` 정리, **타 세션 잔존물 무접촉**) |
| MediaStore | 17 (세션 전후 동일 — 신규 0) |
| 최종 표면 | `com.hnlens.simplemode/.ui.home.MainActivity` (HOME) |

## NOTE (scope 밖 관찰)

- **MediaStore stale baseline**: 17건 = `ss_*.png` 16 (2026-07-22, owner `com.android.shell` — 타 트랙 스크린샷이 `/sdcard` 경유로 자동 등록된 흔적) + `IMG_20260731_183409_459.jpg` 1 (`com.hnlens.camera`, DCIM/Camera). gap-8/PFW 설계의 "MediaStore 0" baseline 은 **깨진 상태** — PFW Phase-2 착수 전 재베이스라인 필요. 본 C02 run 과 무관(신규 0).
- `/data/local/tmp` 에 타 세션 잔존물 다수(SeniorShield·w_session 계열) — 무접촉 유지.

## 후속 측정 1 — HDK_037 focus 소실 매트릭스 (같은 날, 비파괴)

run2 단발 소실의 근본원인 규명. **3 가설 전부 미재현 — 누적 소실 1/40.**

| 가설 | 실험 | 결과 |
|---|---|---|
| 단말 focus 비결정성 | LEFT 10 cycles + RIGHT 10 (역대조) | 소실 **0/20** |
| 캡처 타이밍 레이스 | long-press 후 settle 대기 **0.3s** / 1.3s × 각 10 | 소실 **0/20** |
| driver 경로 고유 요인 | `_ensure_awake`(kc224) + 중간 dump 포함 충실 복제 8 | 소실 **0/8** |

- 누적: run1 유지 · run2 소실 · 추가 38 유지 = **소실 1/40 (2.5%)**.
- 진단 어휘 **`OBSERVED` 유지** — 발생은 실재하나 root cause 미확정. `CONFIRMED` 아님.
- **본 RESULT 초판의 "캡처 레이스로 설명되지 않는다" 판단은 근거 부족으로 철회한다.** 레이아웃
  settle 시점과 focus 할당 완료 시점이 동일하다는 미검증 전제에 의존했다. 0.3s 실험도 소실을
  못 만들었으므로 레이스 가설은 **기각도 확정도 아닌 미확정**이다.
- 부수 확정 — **long-press 방향 비대칭**: LEFT 는 `rl_first[1 - 30]`에서 **정지**(가속 없음),
  RIGHT 는 `모든 앱`→`모드 전환`으로 **계속 이동**. 원문 "맨 왼쪽으로 빠르게 이동" 기대와 대조 필요.
- 데이터: `catalog/f0_c02_hdk_nav_2026-08-19/HDK037_FOCUS_MATRIX_2026-08-19.csv` (20행).

**HDK_037 처리 제안(결정 대기)**: (a) 단독 fresh 2-run 재시도 후 승격 — 1/40 재발 위험 잔존 /
(b) `focus_move` 가 `NONE` 을 읽으면 **1회 재-dump 후 양 판독 기록**(전이 시 PASS + `TRANSIENT_FOCUS_NONE`
주석, 재판독도 NONE 이면 FAIL) — 신호 보존형 하드닝, verifier 의미 변경이므로 승인 필요 /
(c) root cause 확정 전 미승격 유지.

## 후속 측정 2 — 물리 하드키 매핑 확정 (registry `C02_KEYCODE_UNRESOLVED` 해소)

키레이아웃 read-only 판독(`/system/usr/keylayout/Generic.kl` + `getevent -il`)으로 후보를 무추측
확보 후 시험:

| Android keycode | 물리 키 | 도달 |
|---|---|---|
| **132 (F2)** | 메시지 | `com.android.mms/.ui.ConversationList` |
| 131 (F1) | 연락처 | `com.hnlens.contacts/…PeopleActivity` |
| 133 (F3) | 단축버튼 | `com.hnlens.simplemode/…ShortcutEditActivity` |

- 근거: 키패드(`mtk-kpd`) 스캔코드에 **ENVELOPE/CONTACTS 부재**, F1/F2/F3 존재 → 종전
  65(ENVELOPE)=Gmail 은 물리 키 경로가 아니라 프레임워크 기본앱 해석 결과였음이 설명된다.
- **F4 미시험**: `gpio-keys` 소속(볼륨과 동거) = SOS 후보 → denylist 원칙으로 제외.
- **fidelity NOTE**: HDK_021 이 쓰는 207(CONTACTS)은 물리 키가 아닌 프레임워크 주입 경로다.
  목적지 액티비티는 131 과 동일하나 원문("연락처 버튼을 누른다") 충실도로는 131 이 정확하다.
  현 TWO_RUN_GREEN 무효화 사유는 아니며 re-scope 여부는 **결정 대기**.

## 후속 측정 3 — 메시지 3건 discovery (`manual evidence observed`)

상세·근거 = `catalog/f0_c02_hdk_nav_2026-08-19/MSG_DISCOVERY_MANIFEST_2026-08-19.md` (redacted).

| tc_id | 결과 | 잔여 차단 |
|---|---|---|
| HDK_023 | keycode 해소, 그러나 **메시지함에 기존 대화 존재** → 빈 상태 literal 미검증 | **fixture**(062/070 동일 계열). 원문의 설정 메뉴는 `전체 대화목록 삭제` 포함 → **미개방·별도 승인** |
| HDK_055 | **focus 순환 원문과 일치** — `메시지 작성`→`검색`→`옵션 더보기`→`메시지 작성` | literal 차이(`+메시지 작성`→`메시지 작성`, `더보기`→**content-desc** `옵션 더보기`) → **desc/element verifier 필요**(text 속성 부재) |
| HDK_056 | **우측 경계 정지 확인** — `옵션 더보기`에서 RIGHT 반복해도 유지 | literal 차이(`설정 버튼`→`옵션 더보기`) |

- 대화목록 진입 시 `android:id/list`(ListView) 컨테이너 focused = **list 모델** — 기존 카탈로그
  (`com.android.mms` = list)와 정합, 재확인.
- **055/056 은 backfill + desc 기반 verifier 추가 시 drivable 후보**(현재 미승격, 2-run 미실시).

## ★ 신규 위험 발견 — catalog/ 경로가 gitignore 미적용

메시지 화면 dump 는 **PII(수신 문자 본문·발신번호) 포함**인데 `THOR2 - ALT Basic TC Audit/catalog/`
는 `.gitignore` 대상이 아니다(`git check-ignore` 미매치) = 커밋 후보 경로.

- 조치: 본 세션 PII dump 8개를 **repo 밖 local-only 로 이동**, 무-PII manifest 만 잔류.
  이동 후 catalog 내 전화번호 패턴 스캔 **0**.
- 기존 자산 확인: Codex discovery 110 파일 **0** · 2-run evidence 202 파일 **0** (오염 없음).
- **미해소 제안**: `.gitignore` 에 device raw dump 규칙 추가(예: `**/catalog/**/*_MSG_*.xml` 또는
  discovery dump 디렉터리 패턴). repo 설정 변경이므로 **승인 필요**.

## 후속 측정 4 — 물리 하드키 전수 압인 (사용자 협업, getevent 2회)

사용자가 나머지 하드키(홈/뒤로/지움·취소/즐겨찾기/볼륨±/SOS)를 알려줘 **물리 압인으로 전수 확정**.
카탈로그 등재 = `catalog/f0_literal_catalog.csv` KEY-006~010 · STR-010/011.

| 물리 버튼 | scancode (input device) | Android keycode |
|---|---|---|
| 메시지 | `KEY_F2` (mtk-kpd) | **132** |
| 연락처 | `KEY_F1` (mtk-kpd) | **131** |
| 즐겨 찾기 | `KEY_F3` (mtk-kpd) | **133** (→ `ShortcutEditActivity`) |
| 홈 / 뒤로 가기 | `KEY_HOMEPAGE` / `KEY_BACK` | 3 / 4 (기존 값 정합) |
| **지움 \| 취소** | `KEY_BACKSPACE` (mtk-kpd) | **67 (DEL)** — ★BACK(4) 아님 |
| 카메라 / 최근앱 (대조군) | `KEY_CAMERA` / `KEY_APPSELECT` | 27 / 187 (기존 값 정합 → 판독법 검증) |
| 볼륨 UP / DOWN | `KEY_VOLUMEUP`(pmic) / `KEY_VOLUMEDOWN`(gpio) | — |
| **SOS** | **`KEY_F4` (gpio-keys) — 소거법 추론, 미압인** | **134 = 자동화 금지** |

- SOS 는 **누르지 않고** 확정: `gpio-keys` 키 집합 = {`KEY_F4`, `KEY_VOLUMEDOWN`} 이고 볼륨DOWN 이 압인
  확정되어, 물리 버튼 중 미할당 잔여는 SOS 하나. **추론이며 측정 아님** — 그러나 금지 결정은 추론이
  틀려도 비용 0 이므로 **134 를 plan 생성 hard guard 에 추가**할 것을 제안(전원메뉴 OK 가드와 동형).
- 3-way 판별 표준 확립(KEY-005): ① `getevent -lt` 물리 압인 ② `keylayout/*.kl` 매핑 ③ 주입 후 목적지.
  단일 축 추론 금지 — 65(ENVELOPE)=Gmail 오판이 정확히 단일 축 추론이었다.

## 후속 측정 5 — HDK_050 재시험: **divergence 판정 근거 무효**

discovery 는 ⓐ precondition 을 `expand-notifications`(=분할화면, 원문의 **목적지**)로 잡았고
ⓑ 취소키를 BACK(4)로 가정했다. 원문 precondition 은 **퀵패널 전체화면**이다. 올바른 조건으로 재시험:

| 항목 | 결과 |
|---|---|
| 전체화면 → 취소(67) | **분할화면 전환 + 알림 영역 생성 확인** (`brightness_slider`·`footer_page_indicator` 소실, `expandableNotificationRow`·`manage_text` 출현) |
| 67 vs 4 | 결과 dump **byte-identical** (원문이 "뒤로가기 / 지움\|취소" 둘 다 명시한 것과 정합) |
| WIFI 초점 | **미확인** — `focused` 노드 부재, `selected` 는 `shade_carrier_text` |
| discovery 의 "HOME 완전 collapse" | **분할 상태에서 눌렀기 때문** — 전체화면에서는 미재현 |

→ **HDK_050 의 `C02_DIVERGENCE` 판정은 근거 무효**(단말 거동이 아니라 시작 상태 오설정 산물).
`C02_RESCOPE_PENDING` 으로 재분류 제안. 단 승격은 아직 불가 — 아래 게이트 때문.

## ★ 신규 게이트 — 퀵패널 자연 진입 경로 미확정 (STR-010)

`cmd statusbar expand-settings` 는 **합성 진입**이라 focus 상태가 자연 경로와 다를 수 있다
(실제로 WiFi 초점이 안 잡힘). 자연 하드키 경로를 탐색했으나 **미발견**: 홈 길게 무효(HDK_019 실측),
홈에서 DPAD UP 반복은 `weather_view` 에서 정지(상태바 미도달), weather OK 무반응.

**영향 범위가 크다** — batch10 잔여 청크 중 **C03/C04 = Quick panel 44건**이 같은 진입에 의존한다.
즉 이 경로 확정은 C02 잔여 2건이 아니라 **44건의 선행 게이트**다. 다음 device 창 최우선 후보.

## 미실행 / 다음

- manifest `handoff_status` 갱신·ledger 재집계(`scripts/ledger_recompute.py`)·전체 RUNNABLE 총계 재산출 = **미수행**(본 문서는 C02 delta 만 주장).
- 037 처리 결정(위 (a)/(b)/(c)) · 055/056 backfill+desc verifier 후 2-run · 023 fixture 정책 ·
  재판정 5건 · `.gitignore` 규칙 승인 · HDK_021 keycode fidelity re-scope 여부.
- **commit/push 0** — 전부 batch 대기.
