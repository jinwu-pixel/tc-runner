# F0 literal/패턴 카탈로그 — 운영 노트 (2026-06-11 신설)

`f0_literal_catalog.csv` — ALT Basic F0 검증(batch1~3, 2026-06-10)에서 **단말 실증으로 확정된** literal·검증 패턴·구조 함정·기능 부재의 append-only 카탈로그. STAGE1/2 합성과 thor2j 검증 runner의 verifier·selector 입력으로 재사용 (§2.4 누적 원칙).

## 스키마

| 컬럼 | 의미 |
|---|---|
| id | LIT(literal) / PAT(검증 패턴) / STR(구조 함정) / FIT(단말 기능 부재) + 일련번호 |
| kind | literal / verify_pattern / structure / device_fit |
| fact | 단말 관찰 사실 (발명 0 — 출처 = RESULT_RECOVERY 회수 문서) |
| automation_usage | STAGE2/verifier/runner 적용 지점 |
| evidence_tc / evidence_ref | 근거 TC·회수 문서 (`—` = 문서 총괄 기재, tc 미특정) |
| device_profile | 관측 단말 (serial·모델·locale·SIM) |
| build_id | 관측 시점 빌드 문자열 — 현재 전 row `UNRECORDED_AT_OBSERVATION` (Day1 채록 누락) |
| observed_at | 관측 일자 |

**스코프 원칙**: 본 카탈로그의 모든 entry — 특히 `device_fit`(기능 부재) — 는 **보편 사실이 아니라 해당 device_profile × build_id 관측값**이다. 빌드 변경 시 FIT/STR 항목은 재검 대상이며, 타 단말 적용 시 evidence 전이 금지.

## 운영 규칙

- **append-only** — 단말 실증(manual evidence observed 이상)만 등재, 정적 추정 등재 금지
- 기존 row 정정 = 새 row 추가 + 구 row 비고 (삭제 금지)
- 검증 세션(RESULT_RECOVERY) 종료마다 수확분 추가가 표준 사이클
- F0 빌드 문자열 미기록 상태 — **batch4에서 `getprop ro.build.display.id` 채록 후 본 노트 + 신규 row의 build_id에 기재** (기존 row의 UNRECORDED는 append-only 원칙상 유지, 본 노트가 매핑 보관)

## 현재 수확 (2026-06-10 3-batch)

literal 26 / verify_pattern 5 / structure 4 / device_fit 5 = **40 entries**

## STAGE2 반영 제안 (승인 게이트 — tc_prompts 편집은 §2.1 사용자 승인 필요, 본 노트는 제안만)

| # | 제안 | 근거 entry |
|---|---|---|
| 1 | STAGE2_COMPILE verifier 규칙에 "display/필드 판독 = resource-id 한정" 추가 | PAT-004 |
| 2 | "mutation 인접 버튼 = 정확 literal 매칭(partial 금지)" 규칙 추가 | PAT-005 |
| 3 | "화면 도달 판정 = parent-marker 소멸 게이트" 표준화 | PAT-001 |
| 4 | "토글 상태 검증 = dump checked 속성 (무접촉)" 표준화 | PAT-003 |
| 5 | status bar 텍스트류 = screenshot axis 명시 (dump 비포함) | STR-001, LIT-016 |
