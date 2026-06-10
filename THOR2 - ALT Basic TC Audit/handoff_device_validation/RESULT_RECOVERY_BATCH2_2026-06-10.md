# thor2j 실행 결과 회수 — ALT Basic validation batch2 (2026-06-10)

**원본**: `C:\Users\momen\Projects\thor2j-tc-appium\reports\ALTBASIC_BATCH2_RESULT_2026-06-10.md` + `evidence/altbasic_batch2_20260610/`
**단말**: F0 (AT_M140, **SIM = LG U+**) · B27 미접촉 · helper diff 0 · fixture 3건(CLK_035/MSG_084/VRC_061) 미접촉(승인 없음)

## RUNNABLE_NOW 승격 — TWO_RUN_GREEN 19건

본선 18: LCH 054/063/093/097 · CLK 065/068/096 · CALC 001/003/011 · CAM_097 · MSG 102/143/117 · DSP 001/005 · MGN_024 · PDM_019
annex 1: STB_025 (LGU+ 퀵패널 'U+' 텍스트 — carrier_fit CONFIRMED_LGU+)

**계층 확장 성과**: INPUT_REQUIRED 2/2 + SELECTION_GATED 1/1 모두 GREEN — NAVIGATION_ONLY 외 첫 RUNNABLE evidence. 단, n이 작아 동급 후보 일반화는 보류(추가 표본 필요).

## 비승격 5건

| tc_id | 분류 | 축 | 사유 |
|---|---|---|---|
| VRC_058 | DEVICE_FIT_SKIP | 단말 기능 | File Type/Storage 메뉴 본 빌드 부재 (clickable 2종 + HW MENU 키 + 목록 화면 3중 관찰) |
| SPM_062 | VERIFIER_FAILED | fixture 의존 의심 | 빈 차단 목록 화면에 더보기 버튼 실부재 — 차단 메시지 존재 상태 미검증 (fixture 필요) |
| STB_023 | DEVICE_FIT_SKIP | 검증 수단 | 'U+' 표기 스크린샷 확인(manual evidence observed) — dump에 systemui 미포함, 홈 axis는 screenshot 검증 설계 필요 |
| STB_024 | DEVICE_FIT_SKIP | 단말 설정 | 잠금화면 미사용 — wake 직후 홈 직행 |
| LCH_185 | DEVICE_FIT_SKIP | 단말 설정 | 간편 모드 런처 활성 — 표준 모드 구성 기대와 상이, 모드 전환=mutation 미승인 |

carrier 보류(시도 0): SKT 4 (STB_020/021/022, LCH_184) + KT 3 (STB_026/027/028) — SIM 불일치.

## 카탈로그 수확 (학습 루프 — STAGE2/메뉴트리 반영 후보)

- **literal 9건 추가**: 계산기 연산자=desc 한글(빼기/등호 등) · 스톱워치 00 분리 노드 · DuraSpeed(붙여쓰기) · '+'='추가' · 간편 설정 헤더 비표시→항목 집합 · 스팸 신고 안내 화면 · status bar 'U+' 텍스트(단 dump 비포함) · 돋보기 배율=컨트롤 판정 · 만보기 오늘/걸음/목표
- **구조 발견 4건**: launcher dump=systemui 제외(status bar 검증은 screenshot axis) · 잠금화면 미사용 단말 · 간편 모드 런처(표준 모드 TC 전제와 충돌) · 폴더폰 HW MENU 키 무효(VRC)
- **검증 패턴**: state assert = `checked="true"` dump 속성(DSP_001) — 토글 무접촉 상태 검증 표준 후보

## KPI (주간) — 2회 실측 완료

| 지표 | 목표 | 달성 |
|---|---|---|
| RUNNABLE_NOW | 20 (stretch 40) | **34** (b1 15 + b2 19) — 주간 목표 170% |
| 2-run 성공률 | stretch 판단 입력 | **34/35 시도 = 97.1%** (skip 제외) |

stretch 40 승격 판단 조건(2회 실측) 충족 — **판단은 사용자 결정**. 잔여 DVR 후보 풀 = 44 (carrier 보류 7 + fixture 4 + redaction 8 + INPUT 잔여 + 기타) — 40 도달은 batch3 1회 범위.
