# DRAFT — C11 gap-8 Phase-2 (G2) 실행 게이트 개정 지시문 (2026-07-20)

> **상태: 🚫 Stage 2 BLOCKED — widget page absent (2026-07-20 갱신).**
>
> 발효(Option A / ④ Y / ⑥ T1, 사용자 "권장대로 진행해") 후 **Stage 1/T1을 실행**했다(결과 = [RESULT Part 2](RESULT_MEDIA_SEED_C11_GAP8_2026-07-20.md)). pm clear #1이 **사진 위젯 page를 제거(4→3 page)**했고, 현재 device에 사진 위젯 page·`사진 추가하기` 진입점이 **부재**하다. 따라서 **Stage 2(5장 seed → 위젯 구성 → PFW_010/011/013/014/015/022 실측)는 현 상태에서 실행 불가**하다 — Case B상 seed만으로는 위젯 page가 재생성되지 않는다.
>
> **재개 조건 (전부 충족 필요)**:
> 1. 사진 위젯 **page 추가 동선**이 dump-first로 매핑됨
> 2. 해당 page-add mutation이 **별도 승인**됨
> 3. **종료 기준 재정의**: `3-page default 수용` / `4-page empty 복원` / `T2 구성 유지` 중 택1
>
> 위 3 조건 충족 전까지 seed · pm clear #2 · 위젯 mutation · staging · commit · push · 단말 접촉 **0**. 아래 §3~§8은 재개 시점의 참조 절차이며, 재개 전 §3 step 3(위젯 구성)은 위 page-add 선행 매핑으로 갱신돼야 한다. 파일명은 Stage 2가 막혀 있는 동안 `DRAFT` 유지.
>
> 근거 문서: [RESULT_MEDIA_SEED_C11_GAP8_2026-07-20.md](RESULT_MEDIA_SEED_C11_GAP8_2026-07-20.md) · [RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md](RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md) · [MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md](MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md) §9.8/§9.9

## 1. 전제 변경 (설계 §9 → 07-20 baseline로 supersede)

| 항목 | 설계 §9.4 원 전제 | 07-16·07-20 수용 baseline | 함의 |
|---|---|---|---|
| p3 위젯 | stale 21-node `223A0964…` (clear로 해소 대상) | **canonical 빈앨범 20-node `0086D75E…`** | Phase-2는 **pre-clear 없이** 현재 clean 상태에서 직접 시작. clear unlock 불필요 |
| MediaStore images | 10 | **0** | seed 후 총 미디어 = **5** (15 아님) |
| package | 219 | **218** | 사후 invariant 기준값 218 |

**PFW = Case B (RESULT_2026-07-13):** 미디어 seed만으론 p3 위젯이 `사진 추가하기` 상태 유지. PFW 6건을 열려면 **위젯에서 앨범을 명시 선택(mutating)** 해야 한다 — 이것이 Phase-2의 핵심 승인 대상.

## 2. §9.9 필수 승인 6항목 (제안값 + 사용자 결정)

| # | 항목 | 제안값 | 비고 |
|---|---|---|---|
| ① | `pm clear` | **pre-gate unlock용 0회** (p3 이미 canonical). teardown용 횟수는 §4 선택에 종속 | rollback UNKNOWN (§9.1) |
| ② | first-run confirm / simple-mode 선택 / role 복구 범위 | **불필요 예상** (clear 미실행). 예상밖 등장 시 dump 후 STOP | 임의 진행 금지 |
| ③ | SwitchMode(normal→simple) 복구 | **미허용** (normal-mode 미예상). 등장 시 dump 후 STOP | — |
| ④ | crash 시 reboot 1회 | **허용** (§9.7-2, 부팅 팝업 `취소`만) | ☐ 사용자 확인 |
| ⑤ | G1 / G2 | **G2** | — |
| ⑥ | G2 fixture 종료 = T1 / T2 | **§4 선택** (T1 권장) | ☐ 사용자 선택 |

## 3. Phase-2 (G2) 실행 절차 (제안)

각 mutating step은 **dump-first**. adb 경로는 **PowerShell 전달**(Git Bash `/sdcard`·`/data/local/tmp` mangle 회피). remote dump는 **`/data/local/tmp`만** 사용(07-20 지시).

0. **pre-flight 재검증 (fail-closed):** F0 sole + AT-M140 / MediaStore 0 / PFWSEED 0 / pkg 218 / io.appium 0 / HOME role·resolve = simplemode / **p3 canonical `0086D75E…`**. 하나라도 다르면 STOP.
1. **host seed 생성:** `gen_pfwseed_photos.py` → `output/pfwseed_photos/` 5장 (1280×720 JPEG, EXIF 0, 합성 색상+라벨, PII 0).
2. **seed 등록:** `setup_pfwseed_f0.py` → `/sdcard/DCIM/PFWSEED_C11/` push + media scan. 성공 게이트 = **PFWSEED 5/5 registered**(스크립트가 PFWSEED rows만 검증, 기존 미디어 무관). 총 미디어 0→**5**.
3. **위젯 앨범 선택 (MUTATING):** p3 `사진 추가하기` → picker 진입 → **P1~P5 5장 선택** → 저장. 수치 3종 구분(Stage 1 실측 근거): **등록 5/5**(MediaStore PFWSEED rows) · **선택 overlay 5/5**(각 사진 `v_selected`) · **picker counter `5/10`**(`tv_proportion` = 선택 5 / 최대 10; Stage 1 1장 시 `1/10` 관측). ⚠ 단, **현재 사진 위젯 page·`사진 추가하기` 부재**로 이 step은 §0 재개 조건(page 추가 매핑) 충족 전 실행 불가. 각 단계 dump-first, PII leaf 미접촉.
4. **PFW 실측:** PFW_010/011/013/014/015/022 의 focus·화살표(arrows)·rotation. **manual evidence observed** 기록만. 발화/터치 함정 주의(§4 talkback 교훈 무관하나 dump=상태교란·input tap=탐색우회 일반 주의).
5. **teardown:** §4 선택 경로 실행.
6. **사후 invariants:** MediaStore(경로별 0 또는 5) / PFWSEED / pkg 218 / p3(빈앨범 or 구성) / HOME role·resolve / remote temp 0 / mutation 범위 준수. §9.3 diff.

## 4. Fixture 종료 선택 (§9.8 T1/T2 — 사용자 결정)

`pm clear`는 **"검증된 teardown"이 아니라 별도 실험 수단**이다.

> **⚠ 실측으로 폐기됨 (2026-07-20, Stage 1 실행 완료 — RESULT Part 2):** pm clear #1 결과 = **위젯 page 자체 제거·4→3 page 전환**. Option A step 1의 "p3 빈앨범 20-node canonical 복귀" 전제는 **성립하지 않았다**(복귀가 아니라 page 소실). 따라서 아래 A/B/C는 **실행 전 계획**이며 실제 결과가 supersede한다. teardown 종료 기준은 §0 재개 조건 3(3-page 수용 / 4-page empty 복원 / T2 유지)으로 재정의돼야 한다.

- **Option A — T1 검증 우선 (2단계, 권장) ✅ 선택됨 (2026-07-20):**
  1. 먼저 **1장 controlled**: seed 1 → 위젯 구성 → `pm clear`(F0 sole+AT-M140 guard, 1회) → ~~p3 빈앨범 canonical 복귀 확인~~ **[실측 결과: 복귀 아님 — 위젯 page 제거·3-page 전환]** → `reset_pfwseed_f0.py` → invariants.
  - **실행 완료(2026-07-20)**: 이 단계는 이미 수행됐고 clear가 위젯 page를 제거함(RESULT Part 2). "20-node 복귀" 선검증 목표는 미달성(구조가 다름).
  2. ~~선검증 성공 시에만 5장 본 실측~~ → **BLOCKED**: 위젯 page 부재로 §3 실행 불가(§0 재개 조건 필요).
  - pm clear 실측 **1회 실행됨**(1장 controlled). 5장 종료용 2회차는 미실행.
- **Option B — 5장 직행 + 잔존 위험 수용:**
  - seed 5 → 구성 → 실측 → `pm clear`(guard, 1회) teardown.
  - clear-teardown 실패(stale 지속) 시 **추가 clear 반복 금지**(§9.7-6), 잔존 stale를 NOTE로 수용·STOP·별도 논의.
  - pm clear 총 **1회**.
- **Option C — teardown 없이 종료(T2 persistent):** 5장+구성 의도 유지. **baseline 영구 변경** → 별도 명시 승인 + 후속 세션용 신규 baseline 문서 필요.

## 5. Fail-closed·중단 규율

- pre-flight 불일치 / 예상밖 화면(정보 팝업·first-run wizard·normal-mode·system setting·닫히지 않는 editor) / device sole 상실 → 즉시 STOP.
- stale 재발 시 추가 clear 반복 금지(§9.7-6).
- `pm clear`는 F0 sole+AT-M140 재확인 guard 후에만, 정확히 정해진 횟수만. 빈/실패 출력이어도 자동 재시도 0.
- PII·계정·권한·통신 화면 진입 0.

## 6. 판정 어휘 제약

- Phase-2 결과 = **manual evidence observed** only. RUNNABLE_NOW 승격·oracle authoring 자동 승인 아님(§9.8).
- `pm clear`가 실행돼도 단발 관찰이며 그 자체가 `pm clear runtime PASS` 근거 아님.
- T1 teardown 능력은 Option A 선검증 완료 전까지 **미검증**으로 표기.
- media 10=stale / 0=canonical 인과는 **미확정(OBSERVED)** — 통제 왕복 실험 아님.

## 7. evidence·hygiene

- 신규 dated evidence dir (local-only): `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_pmclear_g2_<date>/` — XML + PNG + `manifest.md`. **PNG는 commit 후보 아님.**
- version 등 IPv4-패턴(`\d+.\d+.\d+.\d+`) literal은 commit-candidate 문서에 금지 → **local-only manifest만**. commit 전 `tools/redaction_gate.py` **PASS 필수**.
- remote dump = **`/data/local/tmp`만**. `/sdcard` 잔여 금지; 생기면 sole+model 재확인 후 해당 1파일만 삭제(broad rm 금지).

## 8. 승인·실행 이력 (Stage 1 closed / Stage 2 approval invalidated and blocked)

- [x] Option **A** 채택 (④ **Y** · ⑥ **T1**) — 사용자 "권장대로 진행해" / 2026-07-20
- [x] **Stage 1 = closed (실행 완료)**: device-execution go → seed 1 → 위젯 구성 → `pm clear #1`(`Success`) → 위젯 page 제거·3-page 전환 (RESULT Part 2). ④ crash 미발생(reboot 0).
- 🚫 **Stage 2 = approval invalidated & blocked**: ⑥ 종료 기준 "빈앨범(T1) 복귀"가 실측으로 **무효화**(page 제거). 위젯 page 부재로 5장 실측 불가 → §0 재개 3조건 충족 + **신규 승인문** 선행 필요.

---
*본 문서는 Stage 1 실행 이력을 담은 DRAFT다(파일명 유지). Stage 2 재개·raw evidence staging·commit·push·단말 접촉은 별도 승인 게이트. §5 fail-closed 우선.*
