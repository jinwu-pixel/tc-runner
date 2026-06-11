# THOR2J HANDOFF — ALT Basic validation batch5 (2026-06-11)

**무단말 작성 (정적). 실 F0 실행은 별도 승인 후.** commit/push/단말 호출 금지 상태에서 작성된 계약.

- **manifest (read-only)**: `VALIDATION_MANIFEST_BATCH5_2026-06-11.csv` (11건)
- **runner**: thor2j-tc-appium `runner/altbasic_validation_batch5.py` (b1/b3/b4 helper 재사용)
- **대상 11**: 신규 compose-entry KEEP 6 (DEFER B 재판정) + 기존 LCH 3 + PDM 2
  - MSG 191 · 202 · 203 · 205 · 210 · 296 / LCH 121 · 123 · 223 / PDM 028 · 035
- **KPI 분리 (사용자 정정 2026-06-11)**: DVR 172 = **정적 후보 누적값(재가산 금지)**. batch5 2-run 성공 시 증가하는 지표는 **RUNNABLE_NOW(현 66)** 뿐.

## 1. 단말 / 실행 규약

| 항목 | 계약 |
|---|---|
| 단말 | **F0 `B06201249E0002F0` 고정** (build RY07260600S, ko-KR). **B27 `B2700125BW000083` 미접촉** |
| run | 모든 TC **run1 / run2 독립 실행** (`--run 1` 전수 → `--run 2` 전수). 상호 상태 비공유 |
| 승격 | **TWO_RUN_GREEN(run1=SINGLE_RUN_PASS ∧ run2=RUN2_PASS)만 RUNNABLE_NOW**. 단일 run PASS = 미승격 |
| 결과 어휘 | `SINGLE_RUN_PASS`/`RUN2_PASS` · `ENTRY_FAILED` · `VERIFIER_FAILED` · **`CLEANUP_FAILED`(잔존/복귀 실패 — 즉시 보고)** · `DEVICE_FIT_SKIP`(pre/빌드 부적합, FAIL 아님) · `RISK_BLOCKED` · `INFRA_FAILURE` |
| skip ≠ fail | DEVICE_FIT_SKIP은 KPI 분모에서 제외(실행 적합 아님). FAIL(ENTRY/VERIFIER/CLEANUP)과 분리 집계 |
| RUNNABLE 산식 | RUNNABLE_NOW = 66 + (배치 TWO_RUN_GREEN 건수). DVR 미가산 |

## 2. compose 계열 (MSG 6건) — draft 무생성 계약

B-gate 근거 = **MSG_201 TWO_RUN_GREEN + draft 무생성** (`RESULT_RECOVERY_BATCH4_2026-06-11.md`).

- compose 진입 전 **대화 목록 snapshot**(`_msg_conv_snapshot`) 채록 → 이탈 후 snapshot 재채록 **전후 일치 필수**
- 이탈 후 **draft('임시') 마커 부재** 필수. 둘 중 하나라도 위반 = `CLEANUP_FAILED` + **즉시 보고(임의 삭제 금지)**
- 이탈 저장 팝업: **'저장 안 함' 계열만** tap. **'저장' 절대 금지**
- 입력/선택/첨부/발송 tap **0**. 텍스트 입력 0 (제목/본문 입력 미시행)

## 3. picker 3건 (MSG_203 / MSG_205 / LCH_121) — 캡처 정책 LOCK

| 규칙 | 내용 |
|---|---|
| 썸네일 선택 | 사진/동영상 썸네일 **선택·첨부 tap 절대 금지** (mutation·draft 오염) |
| screenshot | **local-only** — evidence png 커밋 금지 (현 redaction gate PNG 마스킹 불가) |
| commit 후보 | **redacted XML/JSON/요약만** (png 제외) |
| 권한 팝업 | 사진·미디어 접근 권한 다이얼로그 출현 시 **'허용' 누르지 않고** → `DEVICE_FIT_SKIP` (runner `_perm_popup` 감지) |
| 외부 picker | 별도 앱 전환 시 **BACK 복귀 + 원 앱(메시지/런처) focus 확인** (`_current_focus` 전후 비교). 미복귀 = `CLEANUP_FAILED` |

## 4. per-TC verifier / cleanup (manifest 동기)

| tc_id | entry | verifier (presence) | cleanup |
|---|---|---|---|
| MSG_191 | compose>더보기>빠른 답장 | 팝업/목록 **컨테이너 presence**(문구 내용 비단정) | 취소/BACK + draft 무생성 |
| MSG_202 | compose>'+'>제목 | 제목 입력창 생성(EditText 증가, 입력 0) | BACK + draft 무생성 |
| MSG_203 | compose>'+'>앨범 | 사진 picker **컨테이너 전환**(콘텐츠 비단정) | 선택 0 BACK + focus 복귀 + draft 무생성 |
| MSG_205 | compose>'+'>동영상 | 동영상 picker 컨테이너 전환 | 선택 0 BACK + focus 복귀 + draft 무생성 |
| MSG_210 | compose>'+'>오디오 | 벨소리/오디오 선택 메뉴 노출(오디오 파일 picker 미진입) | BACK + draft 무생성 |
| MSG_296 | 메인 더보기 + compose 더보기 | 각 메뉴 항목 집합 **중복 0** | BACK + draft 무생성 |
| LCH_121 | 홈>슬라이드쇼>편집 | 사진 선택 picker 컨테이너 전환 | 선택 0 BACK (구성 무변경) |
| LCH_123 | 홈>앱추가 버튼 | **앱 아이콘 집합 presence**(LIT-007, 헤더 의존 금지) | BACK/HOME |
| LCH_223 | 앱서랍>검색 '시' | 기준 앱 '시계' 매칭 presence(전수 비단정) | **검색어 clear + 앱 미실행(focus=런처)** |
| PDM_028 | 만보기 메인 | **'오늘' 표기 presence**(값 비단정) | HOME |
| PDM_035 | 만보기(below-fold 스크롤) | **'어제' 표기 presence**(값 비단정) | HOME |

> verifier literal/ resource-id는 **무단말 합성 — run1 1차 관찰로 확정 후 고정** (LCH_123 앱추가 desc=LIT-013, picker 컨테이너 id, 빠른 답장 팝업 id 등). run1에서 미확정 시 `ENTRY_FAILED`/`VERIFIER_FAILED` 정직 기록 후 보정 사이클.

## 5. helper 생명주기 (mutation 0 입증)

- 실행 전: `adb -s F0 shell pm list packages | sort > evidence/altbasic_batch5_20260611_pkg_pre.txt`
- 실행 후: `... > ..._pkg_post.txt`
- 종료 시: Appium uiautomator2 helper(`io.appium.*`, `io.appium.uiautomator2.server*`) **uninstall**
- **pre == post diff 0 필수** (잔존 패키지 0). 불일치 = 보고
- 잔존 0 추가 확인: m4a/draft/알람/연락처/홈 배치 — 전부 생성 0 (본 배치 mutation 설계 없음)

## 6. 금지 사항 (denylist — 항구)

- fixture·계정·알람·연락처·대화·사진·녹음 **생성 0**
- 위험 tap denylist: `저장`(='저장 안 함' 제외) · `전송`/`발송`/`보내기` · `허용`(권한) · `동의`/`확인`(영속 변경) · `삭제`(본 배치 teardown 없음) · 사진/동영상 썸네일 선택 · 연락처 기본 계정 선택 · `am start`로의 컴포넌트 직접 기동(런처 경유만)
- ⓔ 연락처 기본 계정 / ⓑ 알람 fixture = **계속 보류** (본 배치 미포함)

## 7. 산출 / 보고

- evidence: `thor2j-tc-appium/evidence/altbasic_batch5_20260611/run{1,2}/{tc_id}/` (png+xml, **local-only**)
- 결과 CSV: `evidence/altbasic_batch5_20260611/results_run{1,2}.csv`
- 회수 리포트: thor2j `reports/ALTBASIC_BATCH5_RESULT_2026-06-11.md` + tc-runner `RESULT_RECOVERY_BATCH5_2026-06-11.md`
- 카탈로그: 신규 literal/구조/fit 발견 시 `catalog/f0_literal_catalog.csv` append (build RY07260600S 직접 기재)
- STAGE2/STAGE1 반영은 **무단말 트랙 분리** 유지 (CATALOG_NOTES 5건 등)

## 8. 정적 검증 (실행 전 통과 — §아래)

runner syntax · TC ID 11 manifest 정합 · 위험 tap denylist 0 · verifier/cleanup 누락 0 · reports/evidence local-only · **commit/push/단말 호출 금지**.
