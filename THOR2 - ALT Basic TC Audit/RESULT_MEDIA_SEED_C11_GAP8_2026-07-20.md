# RESULT — C11 gap-8 G1 pre-gate 재검증 + Phase-2 Option-A Stage 1/T1 (2026-07-20)

RESULT 시리즈: [RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md](RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md) (S1 관찰 + 2026-07-16 G1 1차 취소) → 본 파일 (2026-07-20). 설계: [MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md](MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md) §9.

**본 문서 2부 구성 (같은 날 순차·별개 사건)**: **Part 1** = 오전 G1 pre-gate 재검증(§결론~§9.6, `pm clear` **0회**·STOP). **Part 2** = 이후 [Phase-2 DRAFT](PHASE2_DIRECTIVE_DRAFT_C11_GAP8_2026-07-20.md) 발효(Option A/④Y/⑥T1) 후 실행한 Stage 1/T1(§Part 2, `pm clear` **1회**). Part 1의 "clear 0회"와 Part 2의 "clear 1회"는 모순이 아니라 순차 이벤트다.

## 결론

- **G1 = precondition 소멸로 안전 종결.** `pm clear` 호출 **0회**.
- read-only pre-gate 재검증에서 p3가 이미 canonical 빈 앨범(`0086D75E…C352E`, 20-node + 4 markers)으로 렌더링 중이라 §9.4 step1의 stale 21-node 전제가 불일치했다. 목적이 명령 전에 달성된 상태에서 launcher data를 지우는 것은 §9.1(rollback UNKNOWN)상 불필요한 mutation이므로 fail-closed로 clear를 생략했다.
- 이는 **07-16에 이은 2번째 자연 canonical 관찰**이며, media 상태와의 연관성을 강화한다 — 그러나 **인과 확정은 아니다**(아래 §가설).

## 환경·범위

| 항목 | 값 |
|---|---|
| 단말 | F0 `B06201249E0002F0` 단독 연결 |
| 모델 / build.display.id | AT-M140 / `UP1A.231005.007` |
| 방법 | `uiautomator dump` + `input swipe`(navigation-only, §2.1 비파괴). p1→p2→p3 page scan 후 p3 dump |
| mutation | `pm clear` 0 / seed 0 / 사진 선택 0 / 설정 변경 0 |
| 작업 dump 보관 | 세션 scratchpad only (repo 오염 0, staging/commit/push 0) |

## pre-gate 표 (2026-07-20, manual evidence observed)

| anchor | 설계 §9.4 기대 | 07-20 측정 | 판정 |
|---|---|---|---|
| **p3 위젯** | stale `223A0964…D98EC` 21-node | **canonical `0086D75E…C352E` 20-node + 4 markers** (`사진 추가하기`·`frame_bg`·`cl_vp2`·`ll_album_add`; `cl_translucent`/`iv_album` 0) | ⛔ precondition 불일치 → STOP |
| MediaStore images / PFWSEED | (설계 10 / 07-16 수용 baseline 0) / 0 | **0 / 0** | 07-16 baseline 동일 |
| package / io.appium | (설계 219 / 07-16 수용 218) / 0 | **218 / 0** | 07-16 baseline 동일 |
| simplemode version | local-only package dump에 보존 | 동일 (local-only 보존값이 07-14 baseline과 일치) | 유지 |
| HOME role / resolve | `com.hnlens.simplemode` / `.ui.home.MainActivity` | 동일, isDefault=true | 유지 |
| F0 / 모델 | 단독 / AT-M140 | 단독 / AT-M140 | 유지 |
| remote temp | 0 | probe 잔여 `/sdcard/window_dump.xml` → **cleanup 완료** (guard: sole+AT-M140 재확인 후 해당 1파일만 삭제) | 정리 확인 |

p3 raw SHA와 focus-정규화 SHA가 모두 `0086D75E1AAFBF4049A2471E944B5533A117AF0BC0440BFADEB5002DF04C352E`로 canonical baseline과 byte-for-byte 일치했다(focus 차이 없음).

## 관찰 체인 (07-14 / 07-16 / 07-20)

| 일자 | MediaStore images | p3 상태 | clear |
|---|---|---|---|
| 2026-07-14 (baseline capture) | **10** | stale 21-node `223A0964…D98EC` | (미실행, baseline) |
| 2026-07-16 (G1 1차) | **0** | canonical 20-node `0086D75E…C352E` | 생략·STOP |
| 2026-07-20 (G1 재검증) | **0** | canonical 20-node `0086D75E…C352E` | 생략·STOP |

## 가설 — media-dependent (strengthened, NOT confirmed)

- media 존재(10) ↔ p3 stale, media 부재(0) ↔ p3 canonical 이라는 **상관은 3 관찰로 강화**됐다.
- 그러나 이는 **통제된 왕복 실험이 아니다**(seed→관찰→remove→재관찰의 정/역 재현 부재; §4.2 매트릭스 미충족). stale 렌더가 미디어 count에 인과적으로 종속하는지, 아니면 seeding/reboot 이력 등 다른 변수와 교락하는지 미분리다. → **media-dependent hypothesis strengthened — not confirmed.** 진단 어휘상 `OBSERVED`(root cause 미확정), `CONFIRMED` 아님.
- **[Part 2가 supersede]** Part 2(Stage 1/T1)에서 **위젯 page 구성 상태**(page 존재/추가/제거·앨범 선택)라는 변수가 드러났다. stale·canonical·page-absent는 media count의 직접 함수가 아니라 **위젯 page 구성 상태의 함수**이며, 본 절의 media-count 상관 해석은 **§Part 2 taxonomy로 대체(supersede)**한다.

## §9.6 판정 (어휘 제약)

**manual evidence observed: p3 primary-success 구조가 clear 전에(그리고 이번엔 seed도 없이) 관찰됐다.** 이는:

- `pm clear runtime PASS`가 **아니다**.
- clear의 launcher reset 영향 / first-run 분기 / stale 제거 능력 / **Phase-2 teardown(T1) 능력을 입증하지 않는다** — T1 clear teardown은 여전히 **미검증**(설계 §9.8 및 RESULT_2026-07-13 종료 NOTE에 이미 명시).
- G1은 실행 실패가 아니라 **precondition 소멸에 따른 안전 종결**이다.

gap-8의 "stale 위젯 잠김 → pm clear가 유일 수단" 전제는 **현재 device 상태에서 moot**이다(stale 잠김 부재).

## 다음 승인점 (Phase-2 = 보류, 개정 지시문 리뷰 후 별도 승인)

Phase-2(G2: PFW seed + 위젯 앨범 선택 + PFW_010/011/013/014/015/022 실측)는 아래를 반영한 **신규 승인문**이 선행돼야 한다:

- baseline = MediaStore **0** / package **218** (07-16·07-20 수용 baseline)
- seed 후 예상 총수 **5** / teardown 후 **0**
- `setup_pfwseed_f0.py`는 **PFWSEED 5건만** 검증하며 기존 미디어 10건을 요구하지 않음
- reset 후 **stale 재발 가능** (미디어 존재 구간에서 stale 렌더 관찰됐던 이력)
- `pm clear`는 "검증된 teardown"이 **아니라** 별도 실험 수단
- fixture 종료: ① 최소 1장 controlled clear-teardown 선행 검증(권장) 또는 ② 5장 직행 + teardown 잔존 위험 수용 — **사용자 선택**

## Part 2 — Phase-2 Option-A Stage 1 / T1 실행 (pm clear #1)

> Part 1의 G1 pre-gate STOP 이후, Phase-2 DRAFT를 Option A / ④ Y / ⑥ T1로 발효하고 Stage 1(1장 controlled clear-teardown 선행 검증)을 실행했다. 여기서 `pm clear`가 **1회** 호출됐다.

### 실행 시퀀스 (manual evidence observed)

| 단계 | 결과 | SHA / evidence# |
|---|---|---|
| pre-flight §3.0 | **runtime precondition matched** (F0 sole/AT-M140 · MediaStore 0 · pkg 218 · role simplemode) | p3 `0086D75E…` (01) |
| seed 1장 | PFWSEED 1/1 등록 (**Case B**: 위젯 미변경) | p3 `0086D75E…` 동일 (02) |
| 위젯 구성 (S2 최초 매핑) | `사진 추가하기` → `포토 슬라이드 쇼` 안내(checkbox 미접촉·`확인`) → `PhotoPickActivity` → 1/10 선택 → `저장` | popup `5AB37615…`(03) / picker(04·05) |
| 구성 후 p3 | **구성 shell**(21-node, `iv_album`+`cl_translucent`) — 미디어 존재 → 정상 구성(**stale 아님**) | `DE9609F6…`(06) |
| **pm clear #1** | stdout **`Success`**(guard: F0 sole+AT-M140). simplemode HOME 즉시 복귀, **first-run/mode-chooser/권한/PII 없음** | HOME `7F7987DE…`(07) |
| clear 후 홈 | **4-page → 3-page**(home_indicator 3 dots), 사진 위젯 page 제거 | 마지막 page index=2 `24581A2E…`(08) |
| teardown | `reset_pfwseed_f0.py` → MediaStore residual **0 PFWSEED** | — |
| 최종 invariants | MediaStore **0** / pkg **218** / role simplemode / **3-page** | `7D0B0FDD…`(12) |

### taxonomy (정정 — 구조만으로 stale 판별 불가)

| 상태 | 정의 | 본 실행 관측 |
|---|---|---|
| 21-node = **구성 shell** | 앨범이 선택된 사진 위젯 page | `DE9609F6`(미디어 존재→정상) |
| **stale** | 구성 shell에서 참조 미디어 소실 → 깨진 render | session-start `223A0964`(과거) |
| 20-node = **빈 page** | 사진 위젯 page 존재·앨범 미선택 | `0086D75E` |
| 3-page = **page-absent** | pm clear 후 **관찰된** 사진 위젯 page 부재 상태(launcher default 여부 = `OBSERVED`, 단정 아님) | 본 clear 후 |

### p0~p2 diff (baseline 2026-07-14 §9.3 대비)

| page | 현재(3-page) vs baseline | 판정 |
|---|---|---|
| p0 단축다이얼 | SHA `E920AEB1…` **byte-identical**(75-node, rid/text diff 0) | 무변경 |
| p1 시계/앱 | 앱그리드 rid·구조 동일; 차이 = live 날씨(baseline 미수신→수신)·시각/날짜 **dynamic only** | 구조 무변경 |
| p2 도구 | 62-node·rid 동일; 차이 = 메모리 표시값 **dynamic only** | 타일 무변경 |

→ **관찰한 HOME p0~p3 표면에서 유일한 구조 변화 = p3 사진 위젯 page 제거(4→3)**. **dump로 관찰 가능한 visible config 손실 0**(숨은 preference 보존 여부는 미검증 — 일반화 금지).

### Stage 1 / T1 판정 (어휘 제약)

- 위젯 구성 제거: `manual evidence observed`.
- **4-page canonical baseline 복원: 실패** — pm clear는 위젯 page를 page째 제거하고 **3-page(page-absent) 상태**로 전환했다(launcher default 여부 = `OBSERVED`, 단정 아님). 이전 4-page baseline은 clear로 복원되지 않았다.
- `pm clear runtime PASS`: **주장하지 않음**(단발 관찰).
- **가설**: "session-start의 4-page empty p3(`0086D75E`)는 launcher default가 아니라 선존 사용자 구성" — `OBSERVED`(p0~p2가 default 내용이라 clear에도 무변경인 것과 정합), **`CONFIRMED` 아님**(page-add→재clear 통제 재현 미실시).
- baseline 변경(§9.7-4): 시험단말 launcher가 **3-page로 변경**(위젯 page 소실). 복원 동선 미매핑. 수용 여부 = 사용자 판단.

### provenance
p0~p2 raw XML/PNG 대조는 자동화가 수행했고 사용자 최종 판정은 제공된 evidence 요약 근거다. 재대조 시 evidence 경로 참조.

## evidence·경계

- **Part 2 evidence (local-only 영속)**: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_pmclear_g2_stage1_2026-07-20/` — XML 12 + PNG 3 + `manifest.md`. raw XML/PNG는 dynamic 값(시각·날짜·날씨 위치·메모리) 미generalize → **local-only**; 본 RESULT·manifest는 일반화. PNG는 commit 후보 아님.
- Part 1 작업 dump는 세션 scratchpad. 본 RESULT는 신규 untracked이며 **staging/commit/push 0**.
- 본 결과는 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다. 다음 단계의 grounded 입력이다.
- git: 별도 세션 커밋(BUG#26510)과 무관. 본 트랙 산출물은 전부 untracked, 커밋 0.
