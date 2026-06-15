# CLAUDE.md — qa-suite 모노리포 공통 규약 (v2, 형제 repo 확정)

이 저장소에서 Claude Code 는 아래 규약을 따른다. 영역별 세부 규약은
analysis/CLAUDE.md, automation/CLAUDE.md 를 추가로 읽는다.
규약과 사용자 지시가 충돌하면 사용자에게 확인을 요청한다.

> **배치 상태**: 최종 위치는 형제 repo `C:\Users\momen\Projects\qa-suite`.
> 현 `tc-runner/qa-suite/` 는 **staging** — 문서 개정·프레임워크 selftest, 그리고
> **사용자 승인된 framework smoke** (FRAMEWORK_SMOKE_ONLY 기록, 산출물 ignored 영역)
> 만 수행. 자산 이주·신규 자산 추가 금지. learning/synthesis/contracts/campaigns/var 는
> 목표 구조이며 staging 에는 아직 없다 (형제 repo 생성 시 적용, ARCHITECTURE.md §2).

## 0. 환경

- 호스트: Windows + Git Bash (MINGW64).
  adb shell 에 /sdcard 같은 절대경로 인자를 직접 주지 말 것(MSYS 변환).
  단일따옴표 on-device 명령으로 감쌀 것.
- 대상 단말: user 빌드 전제(THOR2/THOR2-J 등). root 필요 동작 금지.
- 한국어로 소통, 코드 주석도 한국어. 파일은 LF 고정(CRLF 금지),
  단 .bat 파일만 CRLF.

## 1. 파일 배치 규칙 (가장 중요 — 새 파일은 반드시 제자리에)

| 만들려는 것 | 위치 (목표 구조) |
|---|---|
| 결과·증거 계약 (summary schema, 어휘 4축, redaction) | contracts/ |
| TC 입력 포맷 계약 (tc-step 스키마 / appium 포맷) | contracts/tc-step/ · contracts/appium/ [2026-06-15] |
| 커밋 경로 정책 (push audit 소비) | contracts/repo-policy/ [2026-06-15] |
| 버그 분석 문서 | analysis/bugs/BUG-XXXXX.md (TEMPLATE.md 복사) |
| 정적 TC 파생물 (엑셀 기원 파서·분류 산출물) | analysis/tc-catalog/ — 단말 관측 데이터(learning/catalogs)와 경계 상이 |
| 원천자료 (Figma 추출물, 스펙 PDF, 엑셀 원본) | analysis/sources/ |
| 탐색·anchor·delta 코드 | learning/engine/ |
| 화면·selector·실패원인 카탈로그 (append-only **커밋 데이터**) | learning/catalogs/<단말명 - 앱명>/ |
| STAGE 지시문·프로파일·정적검증·실행 TC·golden·비권위 샘플 | synthesis/{stage1,stage2,validators,export,golden,examples}/ |
| 버그 재현 모듈·하니스 래퍼 | automation/bug-repro/ |
| TC step 실행기 | automation/tc-step/ |
| Appium 캠페인 코드 | automation/appium/ |
| 단말×앱 검증 운영 문서 (BUG_LOG/MENU_TREE/RESUME/RESULT) | campaigns/<단말명 - 앱명>/ |
| 캠페인 계약 (TWO_RUN_GREEN 등)·provenance manifest | campaigns/manifests/ |
| redacted 검증 결과 | campaigns/results/ |
| — campaigns/** 공통 | **모든 커밋 후보 residual-scan PASS 필수** (게이트 구현 전 = local carry only) |
| 실행 산출물 (logs/report/raw/keymap) | var/ — **local-only, 커밋 영구 금지** |
| repo-ops 도구 (push audit 등 — QA 도메인 아님) | tools/ [2026-06-15] |
| 지침서·보고서 양식·사내 통합 자료 | docs/ |
| 용도 불명/구버전 | archive/ (삭제 금지, 격리만) |
| 분류 애매한 신규 유입물 | _inbox/ (주기 트리아지 대상) |

- 어디 둘지 판단이 안 서면 _inbox/ 에 두고 사용자에게 보고한다.
  임의의 새 최상위 폴더를 만들지 않는다.
- learning/catalogs 는 재생성물이 아니다 — audit/정리 도구가 generated 로
  오분류해 stage 거부·삭제하지 않도록 한다 (tc-runner §8.2 2026-05-22 교훈).

## 2. 입력 SoT — 트랙 한정

- **automation/bug-repro 의 유일 입력은 analysis/bugs/BUG-XXXXX.md** 다.
  문서가 없거나 "판정 시그니처"가 비었거나 "미해결 질문"이 남아 있으면
  bug-repro 모듈을 구현하지 않는다. 문서에 질문을 기록하고 보고.
- 본 규칙은 bug-repro 트랙 한정이다 — synthesis(입력: 원본 TC+프로파일+golden),
  learning(입력: 단말 탐색 관찰) 에는 적용하지 않는다 (ARCHITECTURE.md §4).
- 실행 프레임워크 3개(bug-repro / tc-step / appium)는 병존하며, 결속은
  contracts/ 의 결과 스키마 수준에서만 한다 (ARCHITECTURE.md §5).

## 3. 정직한 측정 (전 영역 공통)

- 확실하지 않으면 FAIL 이 아니라 WARN + 아티팩트. 사람이 확정한다.
- 판정 신호는 프로세스/디스플레이 귀속 필수. 광역 grep 금지.
- 인프라 실패(adb 불통·산출물 부재·계약 불일치)는 PASS/FAIL 로 위장하지 않고
  INFRA_FAILURE 로 닫는다 (fail-closed).
- 새 FAIL 신호 추가 시 정상 시나리오 캘리브레이션(오탐률 측정)을 먼저 제안.
- PASS/FAIL 부풀리기 금지. 자동화 한계(미검증 부분)는 결과 보고에 명시.

## 4. 변경 절차

- 비자명한 설계 변경은 구현 전 계획을 채팅으로 제시하고 승인받는다.
- python 은 `python -m py_compile`, bash 는 `bash -n` 으로 문법 확인 후 전달.
- 커밋 메시지 프리픽스: `contracts:` / `analysis:` / `learning:` / `synthesis:` /
  `automation:` / `campaigns:` / `docs:` / `chore:`.
- commit / push 는 글로벌 정책(batch + 명시 승인) 종속.

## 5. 단말 사용 규칙

- 단말을 점유하는 작업(Appium 세션, ADB 하니스)은 동시에 하나만.
  다른 세션/터미널이 단말을 쓰는 중인지 확실치 않으면 사용자에게 확인.
