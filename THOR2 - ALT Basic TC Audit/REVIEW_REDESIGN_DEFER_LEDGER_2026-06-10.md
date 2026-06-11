# REVIEW 재설계 DEFER ledger — 사용자 결정 대기 목록 (2026-06-10)

REVIEW_QUEUE 296 중 batch06 합성 57 제외 잔여의 분류. **본 ledger의 각 카테고리 = 트랙 D 게이트 해제 항목** — 사용자 결정/승인 후 후속 batch 모집단이 된다.

~~직독 완료 199 / 296. 미직독 97~~ → **직독 296/296 완료 (2026-06-11)**: 잔여 미직독 실측 **102** (ledger 97은 추정치 — 정정) 전수 직독 = `REVIEW_UNREAD_REJUDGE_2026-06-11.csv`.

**모집단 산식 (2026-06-11 실측 lock)**: REVIEW_QUEUE 고유 모집단 **296** = wave1 39 + wave2 145 + wave3 112 — (sheet,row) 고유 키 296/296, 중복 0. 분할 = **CSV `human_confirmed` 194 (Day2) + `cue_auto` 102 (2026-06-11 rejudge) = 296** (교집합 0). 종전 "직독 199" 보고치는 CSV 표기 194 대비 **5 과대 — 보고-표기 불일치로 정정** (199+102=301 산술 충돌의 원인). rejudge 102 내 stale 24(batch06 기합성 8 + 본 ledger 기분류 16)는 모집단 중복이 아니라 Day2 산출물과의 내용 중복임. 구성: 신규 판정 78 (REDESIGN_CANDIDATE 12 / DEFER A 19·B 4·C 22·D 7·E 6 / EXCLUDE_CONFIRMED 8) + stale 24 (batch06 기합성 8 + 본 ledger 기분류 16 — wave2/3 CSV `judge_method=cue_auto` 표기가 Day2 처리 후 미갱신). 신규 DEFER 분은 해당 카테고리 모집단에 합산 (A: STB_006·MSG 209/222/367·CNT 154/157/158/172~181·LCH_119·PFW 5/26/27 / B: MSG 202/326/393·SPM_076 / C: 폴더 drag-merge·음파그래프·toast·하이라이트·panning 등 22 / D: STB 8/9/10/32·LSC 46/48·SFT_025 / E: BSC 82/84/85/87/89/90).

## A. fixture 승인 대기 (사용자 결정)

| fixture 유형 | 대상 row | 비고 |
|---|---|---|
| 알람/타이머/세계시간 존재 (Clock) ⓑ | wave1 CLK 37, 40, 46, 49, 51, 57, 59, 60, 61, 66, 69, 89, 91 (13) | **미승인 mutation(알람)** — 생성→검증→삭제 사이클 승인 필요. **🛑 계속 보류 (사용자 2026-06-11)**: KPI 초과(RUNNABLE 66) 상태에서 mutation 위험 확대 불필요. 승인 시 +13 (batch06 CLK_092 동형) |
| VRC 녹음 파일 재사용 확장 | wave2 VRC 41, 46, 47, 60, 62, 64, 66, 73, 74, 75 (10) | **✅ 승인 (2026-06-11)** — 9건 합성 완료 `stage1_vrc_fixture_batch07/` (VRC_041은 라디오 녹음 추가 의존으로 제외 권고 채택, 본 ledger 잔류). handoff = `HANDOFF_PACKAGE_BATCH07_2026-06-11.csv` |
| 연락처 존재 (PII) | wave2 CNT 156, 159, 162, 163, 166, 167, 174, 177 + BSC 105 + LCH 67 (10) | 연락처 fixture + redaction gate 선결 ([[project_redaction_policy_task41]]) |
| 대화/차단 메시지 존재 | SPM 64, 65, 80 + MSG 127, 129, 131, 137, 375 + MSG 221, 311, 312, 453 (12) | **미승인 mutation(대화)** — 수신/차단 메시지 생성 수단 자체가 외부 의존 (테스트 회선 필요 여부 포함 결정) |
| 잠금 설정 (패턴/암호) | LSC 9, 27, 38 (3) | 잠금 설정 변경 = 고위험 — 검증 후 해제 실패 시 단말 잠김. 권장: 보류 (라벨 '암호' = redaction 키워드 위양성 회피 치환, 원문 표기는 wave CSV 보존) |
| **ⓔ 연락처 기본 계정 선택 (신설 2026-06-11)** | batch08 CNT editor-entry 7 (CNT 121/123/130/133/134/135/136) + batch4 CNT_132/137 재검증 | **batch4 발견 (STR-008)**: 신규 연락처 editor 첫 진입 = '기본 계정 선택' 다이얼로그(휴대전화/SIM 카드) — 선택 = 영속 기본값 + 확실한 rollback 부재. **🛑 보류 결정 (사용자 2026-06-11)**: 확실한 rollback 부재로 F0 승인 안 함. **batch5 manifest에서 CNT editor-entry 계열 영구 제외** (해제 = 별도 rollback 수단 확보 후 재검토) |

## B. compose-entry 연쇄 (MSG_201 검증 게이트)

**✅ 게이트 해제 (2026-06-11 batch4)**: MSG_201 TWO_RUN_GREEN + **draft 무생성** (대화 list 전후 일치 + '임시' 마커 부재, 양 run 재현 — `RESULT_RECOVERY_BATCH4_2026-06-11.md`). 차단 사유(compose 진입=draft 오염 우려) 해제.
**처리**: 해제 마킹만 — **RUNNABLE 승격 0**, 아래 17건은 재판정 대기 (개별 직독→5필드→합성→2-run 전체 사이클).
모집단 17 = MSG 191, 203, 205, 207, 208, 210, 218, 266, 296, 297, 298, 372, 455 (13) + rejudge 신규 MSG 202, 326, 393 + SPM_076 (4) — 단 207/208(연락처 첨부)은 A-3 연락처 fixture 종속, 297/298/372(사진 첨부)는 갤러리 사진 fixture 종속 (이중 게이트 잔존).

## C. verifier 미실증 (screenshot/toast 판정 패턴 단말 실증 후)

| 패턴 | 대상 row |
|---|---|
| screenshot 시각 판정 (색상/크기/레이아웃) | wave3 BSC 130, 134, 137, 141, 142, 143, 147, 150, 151, 153, 155 (Landscape 팝업 텍스트 크기 — 폴더폰 landscape 지원 자체도 미확인) + wave1 CLK 76, 77, 78 (색상) + MGN 42 (pinch 확대) + LCH 197, 198, 204 + STB 18, 19 |
| toast 캡처 | LCH 108, 109, 127, 128 (+ pre 미충족 시 홈 배치 mutation 위험 동반) + CALC 49 + WTH 9, 10 |

## D. 시스템 상태 조작 pre (관찰 전용 원칙과 충돌 — 별도 승인 또는 수동 트랙)

WTH 36, 40 (데이터/위치 off) · NMD 44 (인터넷 차단) · SFT 38 (물리키 설정 off = 본 mutation이 검증 대상) · LCH 186 (집중모드), 200 (절전모드), 203 (알림 수신) · STB 7 (방해금지 — **F0 미탑재 DEVICE_FIT**), 12 (통화 중), 13, 14, 15 (RAT 의존 — carrier 보류 풀 연계), 30 (이어폰 hardware)

## E. 바인딩 미결 (generic 'Basic principle' — 리스트 앱 바인딩 사용자 결정)

BSC 80, 83, 95, 97 (Multi Selection — long-tap 선택모드, SELECTION_GATED 실증 패턴이나 대상 리스트 앱 미지정) + BSC 107, 108 (타이틀 검색 — 대상 앱 미지정). 후보 바인딩: VRC 목록(A-2 승인 시) 또는 차단 문구 목록.

## F. 기타 모호/잔존 위험 (개별 사유)

CALC 19 (비결정 assert), 41 (기록 삭제 전제), 43 (42 near-dup), 45 (proc↔exp 불일치 의심 — 원문 재확인), 46, 47 (표시 옵션 잔존 불확실) · CLK 67 (무반응 dump-diff verifier), 79 (입력 잔존 불확실) · CAM 23 (촬영물 전제), 65 (편도 전환 잔존 — 026이 superset), 69 (pinch), 95, 96 (전면 조합 — 098 검증 후), 116 (화면분할 device-fit 의문) · CNT 125 (빈 저장 tap — '저장' 실행 허용 여부 사용자 결정), 138 (카메라 chain — 137 검증 후), 192 (모호) · NMD 7, 12 (검색결과 없음 — 환경 conditional, skip 확률 높음) · TTS 2 (toggle-off 시 노출 불명), 4, 6 (확인 = persist) · PDM 4, 8, 12, 15 (값 변경 — 원복 사이클 승인 필요), 23, 25 (빈 입력 + 확인 — 저장 trigger 불확실) · LCH 58 (이동 시도 gesture), 113, 120, 122 (포토 슬라이드쇼 사진 fixture/시간 의존), 183 (carrier 3종 — carrier 보류 풀), MSG 119 외 차단문구 삭제류 127 (A-4 종속), 336 외 — 표기 생략분은 wave CSV 분류 유지

## 권장 우선순위 (다음 단말/합성 사이클)

1. **A-2 VRC 사이클 재사용 확장** — 실증 완료 사이클의 저위험 확장, 승인 즉시 +10
2. **A-1 알람 fixture 승인** — CLK 라벨 검증류 +13, batch06 CLK 패턴과 동형
3. **B compose 연쇄** — ✅ 게이트 해제 (2026-06-11) → 17건 재판정이 다음 합성 사이클 1순위 (단, 207/208·297/298/372는 fixture 이중 게이트)
4. **ⓔ CNT 기본 계정 fixture** — 사용자 결정 대기 (batch08 CNT 7 + CNT_132/137 의존)
5. C/D/E는 단말 실증(스크린샷 판정·toast)·수동 트랙·바인딩 결정 후
