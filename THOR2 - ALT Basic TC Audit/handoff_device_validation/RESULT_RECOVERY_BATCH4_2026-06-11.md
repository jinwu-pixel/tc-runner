# thor2j 실행 결과 회수 — ALT Basic validation batch4 (2026-06-11)

**원본**: `C:\Users\momen\Projects\thor2j-tc-appium\reports\ALTBASIC_BATCH4_RESULT_2026-06-11.md` + `evidence/altbasic_batch4_20260611/`
**단말**: F0 (build **RY07260600S** 채록 — 카탈로그 build_id 스코프 확정) · B27 미접촉 · helper diff 0 (pre 218 == post 218) · 미승인 mutation(알람 생성/대화 삭제/모드 전환/연락처 계정 선택) 미접촉
**구성 (2층)**: 본선 22 (KPI 집계) + 비본선 3 (VRC fixture SETUP/TEARDOWN 인프라 ×2, CALC_009 매트릭스 annex ×1 — 비집계)

## RUNNABLE_NOW 승격 — TWO_RUN_GREEN 14건

CALC_013 · CLK_106 · CLK_038 · PDM_011 · MSG_336 · **MSG_201** · VRC 8 (046/047/060/064/066/073/074/075)

- **VRC fixture 재사용(ⓐ) 실증**: 1 fixture → 9건 검증 사이클 양 run 완결 (생성→검증→삭제→빈 목록, 잔존 0 — fs `*.m4a` 0건 교차 확인)
- **MSG_201 compose 게이트(ⓓ) GREEN**: 무입력 이탈 시 draft 무생성 (대화 list 전후 일치, 양 run) → **DEFER B 17건(13+4) 차단 사유 해제 마킹** — RUNNABLE 승격 0, 개별 전체 사이클 (직독→5필드→합성→2-run) 대상
- 14건 중 first-pass GREEN 3 (CALC_013/CLK_038/VRC_075), 나머지 11 = 관찰-보정 사이클 후 GREEN (원 보고서 † 표 참조 — 정직 표기)

## 비승격 8건 (DEVICE_FIT_SKIP — 양 run 재현, F0 RY07260600S 관측 한정)

| tc_id | 사유 | 카탈로그 |
|---|---|---|
| TTS_003 | 정각 알림 진입점 부재 — **단, run1 "설정 8항목" 근거는 재부팅 후 반증** → 최종 근거 = 접근성 내부 전수 부재 | FIT-006 + **STR-005**(설정 list 세션 상태 의존) |
| CALC_048 | 라이선스/설정 진입점 부재 (메인 clickable 전수) | FIT-007 |
| CLK_082 | 타이머 '라벨' 부재 (값 설정 후 노출 가능성 미배제 NOTE) | FIT-008 |
| NMD_005 | 위치정보 고지 팝업 — 동의=mutation 금지, BACK 비영속 | LIT-034 |
| LCH_212 | 홈 폴더 부재 (생성=mutation 금지) | FIT-010 |
| VRC_062 | default 필터='모든 녹음' — '음성 녹음 default' pre 미충족 | FIT-009 |
| CNT_132/137 | **'기본 계정 선택' 다이얼로그** — 영속 기본값·rollback 부재, 선택 0회 | **STR-008** |

## annex — CALC_009: OBSERVED → **CONFIRMED (F0 RY07260600S 한정)**

연속 5 + **재부팅 후** 5 + run2 5 = **15/15 전체삭제** (기대 '12'=한자리 삭제). 제품 공통 단정은 타 빌드 비교 전 보류 (NOTE). 개발 문의 패키지 충분 — formula id 판독 + 스크린샷 15장 + 재부팅 직교 조건.

## 신규 게이트/결정 대기

1. **fixture 승인 ⓔ (신설)**: CNT 기본 계정 '휴대전화' 1회 선택 — 영속 설정·확실한 rollback 부재. **batch08 CNT editor-entry 7건 + CNT_132/137 재검증 전부 의존.** 승인 전 batch5 manifest에서 CNT editor-entry 계열 제외
2. **DEFER B 17건**: 해제 마킹 후 재판정 대기 (ledger 갱신 2026-06-11)
3. 재부팅 포함 TC 표준 전처리: 부팅 데이터 팝업 ('취소'=상태 보존, mobile_data 전후 검증) — STR-006

## 카탈로그 수확 (batch4) — +17 rows, 누적 57

- **LIT-027~034** (8): VRC 행 구조 id 한정 · 파일명 패턴/필터 4종 · 재생창 직접 노출('트림'=편집) · rename 팝업 취소/확인 · 선택모드 '선택 옵션'/'닫기' · MSG '첨부' desc(+'추가' 오매칭 사례) · MSG 차단 동선/enabled verifier · 니어메디2 진입+고지 팝업
- **STR-005~008** (4): 설정 list 세션 상태 의존(부재 단정 금지) · 부팅 데이터 팝업(BACK 비영속·'취소' 보존) · 설정 스크롤 위치 복원(최상단 복귀 필수) · CNT 계정 다이얼로그 게이트
- **FIT-006~010** (5): TTS 진입점·계산기 라이선스·타이머 라벨·VRC default 필터·홈 폴더
- 전부 build_id `RY07260600S` 직접 기재 (기존 40 rows UNRECORDED 매핑은 CATALOG_NOTES 채록 절)

## KPI 갱신 (2026-06-11, 4-batch)

| 지표 | 목표 | 달성 |
|---|---|---|
| RUNNABLE_NOW | 20 (stretch 40) | 52 + 14 = **66 (stretch 165%)** |
| 2-run **실행 적합 건 조건부 성공률** | — | 66/68 = **97.1%** (분모 = device-fit-skip 제외 실행 적합 68 = GREEN 66 + FAIL 2; FAIL 2 = SPM_062 · CALC_009→CONFIRMED 전환으로 BUG 트랙 이관) |
| 본선 투입 회수율 (전체) | — | 66/87 = **75.9%** (분모 = 본선 누적 87 = GREEN 66 + DEVICE_FIT_SKIP 19 + FAIL 2 — 단말/빌드 부적합분 포함) |
| DVR 누적 | 100/주 | 166 (166%) — 검증 대기 풀 = batch08 12 (CNT 7은 ⓔ 게이트) + 잔여 재고 |
