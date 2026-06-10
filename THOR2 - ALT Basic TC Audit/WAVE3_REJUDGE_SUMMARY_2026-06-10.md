# Wave3 재판정 + batch05 summary — 일반 15시트 (2026-06-10)

모집단 = 후순위 게이트(Call/Radio/Keyboard 504) 제외한 일반 15시트 EXPORT 후보 **280** (unique, dup 0).

## 진입 전 의무: UNREVIEWED 211 계층 표본 검사 (wave2 잔여)

- 표본 31 (시트 비례) 직독 → **과배제 7/31 = 22.6% > 5%** → **EXCLUDE 자동 확정 금지 유지** (cue는 후보 분류 전용, KEEP/확정 EXCLUDE는 사람 판정만)
- 표본 발견 재분류: KEEP 1(Camera#38) + REVIEW 6 — wave2 CSV 반영 (UNREVIEWED 211→204)

## Wave3 결과

| 분류 | 건수 | 비율 | 성격 |
|---|---|---|---|
| **KEEP** | **13** | 4.6% | 전건 human_confirmed |
| REVIEW_QUEUE | 112 | 40.0% | human 62 + cue 후보 50 |
| EXCLUDE (확정) | 87 | 31.1% | human_confirmed만 |
| EXCLUDE_CANDIDATE_UNREVIEWED | 68 | 24.3% | KPI·통계 비합산 |

**yield 4.6%로 급락한 구조적 이유** (corpus 본질 — 무리 승격 0):
- Sub LCD 13 전건 = 폴더 물리 개폐 + Sub LCD는 uiautomator dump 불가
- Safety Feature 15 전건 = Care 메시지 자동 발송(외부 SMS) + 시간 대기
- TTS 22 중 18 = 오디오 verifier 불가 + 정각 대기
- Setup Wizard 11 = factory 초기 상태 필요
- Weather/미세먼지 = 환경(농도/네트워크) 제어 불가

KEEP 13 = 니어메디 정적 화면 3(앱정보/약관/라이선스) + Dura Speed 2 + 돋보기 2 + 만보기 2 + 포토프레임 팝업 1 + 스팸차단 3. 직독 = KEEP 후보 127 전수 + 구제 필터 35 전수(KEEP 5 회수) + EXCLUDE 표본 경유.

## batch05 합성 + handoff

- `stage1_wave3_batch05/` 13 YAML — batch04 계약 동일(cleanup_candidate/carrier_fit 포함)
- gate 전부 PASS (ID 정합·혼입 0·위험동사 0·금지토큰 0·verifier/cleanup 49/49 방식 동일)
- **신규 시트군 → 전수 리뷰 13/13 (100% > 계약 20%)**: false-promote **0/13**, 공통 결함 0 (gate 키워드 정합 1건만 문구 보정)
- handoff 13/13 → DVR_CANDIDATE. 니어메디 3건 redaction CHECK(위치/병원 정보 dump 가능)

## 누적 (Day1 종료)

| 지표 | 값 |
|---|---|
| STAGE1_DRAFT | **74** (b03 12 + b04 49 + b05 13) |
| DVR_CANDIDATE | **88** (Settings 14 + b03 12 + b04 49 + b05 13) |
| 재판정 처리 | **804** (wave1 96 + wave2 428 + wave3 280) |
| RUNNABLE_NOW | 0 — thor2j 실기 미실행 (F0 승인 대기) |

## 잔여 풀 (KPI 120/100 경로)

| 풀 | 건수 | 비고 |
|---|---|---|
| REVIEW_QUEUE 누적 | 290 (39+139+112) | **재설계 트랙이 DRAFT +46의 주 경로** (assert 분리·observe 분리·fixture 사이클) |
| EXCLUDE_CANDIDATE_UNREVIEWED | 272 (204+68) | 통계 비합산, 재검사 시 일부 회수 가능 (표본상 ~3% KEEP 잔존) |
| 후순위 게이트 | Call 126 / Radio 72 / Keyboard 306 | 발신·RF·입력 지배 — 진입은 사용자 결정 |
