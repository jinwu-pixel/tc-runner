# F0 literal/패턴 카탈로그 — 운영 노트 (2026-06-11 신설)

`f0_literal_catalog.csv` — ALT Basic F0 검증(batch1~3, 2026-06-10)에서 **단말 실증으로 확정된** literal·검증 패턴·구조 함정·기능 부재의 append-only 카탈로그. STAGE1/2 합성과 thor2j 검증 runner의 verifier·selector 입력으로 재사용 (§2.4 누적 원칙).

## 스키마

| 컬럼 | 의미 |
|---|---|
| id | LIT(literal) / PAT(검증 패턴) / STR(구조 함정) / FIT(단말 기능 부재) / KEY(하드키 keycode) + 일련번호 |
| kind | literal / verify_pattern / structure / device_fit / keycode |
| fact | 단말 관찰 사실 (발명 0 — 출처 = RESULT_RECOVERY 회수 문서) |
| automation_usage | STAGE2/verifier/runner 적용 지점 |
| evidence_tc / evidence_ref | 근거 TC·회수 문서 (`—` = 문서 총괄 기재, tc 미특정) |
| device_profile | 관측 단말 (serial·모델·locale·SIM) |
| build_id | 관측 시점 빌드 문자열 — 기존 40 row `UNRECORDED_AT_OBSERVATION` (Day1 채록 누락, 매핑은 아래 채록 절 참조) |
| observed_at | 관측 일자 |

**스코프 원칙**: 본 카탈로그의 모든 entry — 특히 `device_fit`(기능 부재) — 는 **보편 사실이 아니라 해당 device_profile × build_id 관측값**이다. 빌드 변경 시 FIT/STR 항목은 재검 대상이며, 타 단말 적용 시 evidence 전이 금지.

## 운영 규칙

- **append-only** — 단말 실증(manual evidence observed 이상)만 등재, 정적 추정 등재 금지
- 기존 row 정정 = 새 row 추가 + 구 row 비고 (삭제 금지)
- 검증 세션(RESULT_RECOVERY) 종료마다 수확분 추가가 표준 사이클
- F0 빌드 문자열 미기록 상태 — **batch4에서 `getprop ro.build.display.id` 채록 후 본 노트 + 신규 row의 build_id에 기재** (기존 row의 UNRECORDED는 append-only 원칙상 유지, 본 노트가 매핑 보관)

## F0 빌드 채록 (2026-06-11 batch4, manual evidence observed)

- `ro.build.display.id` = `UP1A.231005.007 release-keys` / `ro.build.version.incremental` = **`RY07260600S`** / model AT-M140 (getprop 실측)
- **매핑 (추론, 확정 아님)**: 기존 40 row의 `UNRECORDED_AT_OBSERVATION`은 **본 빌드 `RY07260600S`일 개연성이 높음** — 근거 = 관측일 2026-06-10~11 사이 F0 flash 이력 없음 (2026-06-11 flash 작업은 타 단말)이라는 **no-flash 기록에 따른 추론**. 채록 시점 build_id가 실제 기록되지 않았으므로 단정 불가. **CSV의 `UNRECORDED_AT_OBSERVATION`은 그대로 유지** (추론값으로 덮어쓰지 않음 — append-only + 무기록 사실 보존).
- batch4 이후 신규 row만 build_id에 `RY07260600S` 직접 기재 (실측 채록)

## 현재 수확 (2026-06-10 3-batch + 2026-06-11 batch4)

- 2026-06-10 batch1~3: literal 26 / verify_pattern 5 / structure 4 / device_fit 5 = 40
- 2026-06-11 batch4: literal 8 (LIT-027~034) / structure 4 (STR-005~008) / device_fit 5 (FIT-006~010) = 17 — build_id `RY07260600S` 직접 기재
- 누적 **57 entries**

## STAGE2 반영 제안 → ✅ 별도 무단말 TDD 트랙 승인 (사용자 2026-06-11) → ✅ APPLIED 2026-06-23

**결정**: 아래 5건은 **별도 무단말 TDD 트랙**으로 진행 (STAGE2_COMPILE 규칙 추가 = 정의→코드→테스트 동기, §2.3 source-of-truth). 단말 불필요 — golden_tc_set 회귀 기반. tc_prompts 편집은 §2.1 승인 게이트 이미 충족 (본 결정). 착수 시점은 별도 (batch4 commit 마감 후).

**적용 (2026-06-23)**: `tc_prompts/STAGE2_COMPILE.md` v1.1.0 — "단말 실증 기반 verifier/selector 규칙" 섹션 R1~R5 추가 (5건 1:1 매핑). golden_tc_set 회귀 3/3 PASS (편집 전/후 동일), golden 위반 0. **drift note**: 규칙은 LLM-compiler authoring 지침 — `validate_tc.py` 정적 강제는 범위 외(verifier 의미 규칙, 현 action 스키마 정적 매핑 없음·휴리스틱 강제는 drift 위험). 정적 강제 필요 시 별도 티켓.

| # | 제안 | 근거 entry | 적용 |
|---|---|---|---|
| 1 | STAGE2_COMPILE verifier 규칙에 "display/필드 판독 = resource-id 한정" 추가 | PAT-004 | R1 |
| 2 | "mutation 인접 버튼 = 정확 literal 매칭(partial 금지)" 규칙 추가 | PAT-005 | R2 |
| 3 | "화면 도달 판정 = parent-marker 소멸 게이트" 표준화 | PAT-001 | R3 |
| 4 | "토글 상태 검증 = dump checked 속성 (무접촉)" 표준화 | PAT-003 | R4 |
| 5 | status bar 텍스트류 = screenshot axis 명시 (dump 비포함) | STR-001, LIT-016 | R5 |
- 2026-08-19 C02: keycode 5 (KEY-001~005) — 물리 하드키 3-way 판별(getevent 압인 + keylayout + 주입). build_id `RY07260601S`
- 2026-08-19 C02 (2차): keycode 5 (KEY-006~010, SOS=134 는 소거법 추론·미압인) + structure 2 (STR-010 퀵패널 진입 미확정 / STR-011 QS 취소키 시작상태 의존)
- 2026-08-20 QPN 진입 게이트 해소: keycode 1 (KEY-011 adb --longpress ≠ 물리 홀드) + structure 3 (STR-012 2단 셰이드 / STR-013 진입 3경로 등가 / STR-014 focus 는 DPAD 1회 후). **STR-010 supersede**
