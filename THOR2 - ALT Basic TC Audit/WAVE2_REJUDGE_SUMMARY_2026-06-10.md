# Wave2 재판정 summary — Launcher/Status bar/Voice Recorder/Camera/Message/Contacts (2026-06-10)

throughput 2차 재판정. 모집단 = 6시트 EXPORT_TO_APPIUM 459행 → **unique 428** (overlap_join 중복 31행 제거).

## 결과 (2026-06-10 표기 보정 반영)

| 분류 | 건수 | 비율 | 성격 |
|---|---|---|---|
| **KEEP** | **49** | 11.4% | 전건 human_confirmed |
| REVIEW_QUEUE | 139 | 32.5% | 재설계/fixture 트랙 |
| EXCLUDE (확정) | 29 | 6.8% | human_confirmed만 |
| **EXCLUDE_CANDIDATE_UNREVIEWED** | **211** | 49.3% | cue 단독 — **미직독, 확정 아님. KPI·자동화 불가율 통계에 합산 금지. wave3 전 계층 표본 재검사 대상** |

| 시트 | unique | KEEP | KEEP id |
|---|---|---|---|
| 24.Launcher | 105 | 18 | 53,54,55,57,59,63,76,77,88,93,94,97,112,133,134,184,185,201 |
| 13.Status bar | 27 | 10 | 1, 20~28(통신사 아이콘 9종) |
| 30.Voice Recorder | 50 | 5 | 25,58,61,63,65 |
| 28.Camera | 98 | 3 | 2,6,97 |
| 26.Message | 88 | 11 | 84,100,101,102,116,117,128,143,183,186,361 |
| 27.Contacts | 60 | 2 | 122,223 |

전체 기록 = `WAVE2_REJUDGE_2026-06-10.csv` (428행, classification/reason/`judge_method`).

## 방법 + 품질 통제

1. **cue 자동 분류** (mutation/input/fixture/외부효과 cue): EXCLUDE 293 / KEEP 후보 114 / REVIEW 52 (provisional)
2. **KEEP 후보 114 전수 직독** → 21건 강등(손전등 토글·모두닫기·폴더생성·바로가기 생성 등 cue 누락 EXCLUDE 8 + 모호/fixture REVIEW)
3. **EXCLUDE 표본 20 직독** → **과배제 8/20 (40%) 발견** — '삭제/이동/녹음/저장' 단어가 메뉴 라벨·화면 이동·취소 경로·빈 상태 문구 맥락에서 오발
4. **구제 필터** (exp=노출/전환/없습니다 서술 AND mutation 결과 서술 부재 AND 강한 mutation 동사 부재) → 후보 63 전수 직독 → **KEEP 17 회수 + REVIEW 40 상향 + EXCLUDE 유지 8**
5. KEEP 49 = **전건 human_confirmed** (cue 단독 KEEP 0)

**한계 명시 (표기 보정 2026-06-10)**: cue 단독 배제 211건은 미직독이므로 확정 EXCLUDE가 아닌 `EXCLUDE_CANDIDATE_UNREVIEWED`로 분리 집계 (CSV classification 컬럼 반영). 확정 EXCLUDE는 직독 29건만. 구제 필터가 관찰형 서술을 회수했으므로 잔존분은 mutation 결과 서술 포함분이나, 오배제 잔존 0 아님 → **wave3 진입 전 이 집단 계층 표본 재검사 필수**.

## KEEP 49 주요 계약 (합성 시 반영)

- Status bar 20~28: **carrier SIM blocking precondition** (단말 장착 SIM 1종만 유효, 나머지 skip — FAIL 아님)
- Launcher 184/185: carrier별 홈 구성 — 동일 carrier pre
- Launcher 133/134, Message 116/117: 팝업 노출 observe — **확인 금지, 취소 이탈 cleanup**
- Launcher 201: long-press 메뉴 observe — 항목 탭 금지
- VR 63/65, Message 84: 빈 상태 문구 — pre '데이터 없음' blocking 명시
- Camera 2/6/97: 모드 전환 transient (카메라 설정 유지 default Off 근거) — 촬영 버튼 접촉 금지
- 전 건 app-domain: anchor MISSING / entry `app_launch_unresolved` (패키지 발명 0) — 단 Message 361은 Settings 경유

## REVIEW_QUEUE 139 주요 묶음
fixture 전제(차단 메시지/녹음 파일/연락처/대화 이력) / editor·compose 진입 no-save 설계 / transient input 검증 / RAT·물리 액세서리 환경 전제 / 전면·후면 카메라 dump 구분 불가(verifier 재설계) / assert 분리 재설계(observe+mutation 혼합)

## 다음
1. KEEP 49 → batch04 합성 (+handoff 전환 시 DVR 후보 +49)
2. 잔여 일반 시트 재판정 wave3 (~280: Basic principle 52·TTS 30·Pedometer 30 등; Call/Radio/Keyboard 504는 후순위 게이트 유지)
3. EXCLUDE cue_auto 잔여 spot-check 1회
