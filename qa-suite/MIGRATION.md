# MIGRATION.md — 기존 자산 이주 체크리스트 (v2, 형제 repo 확정)

목표: tc-runner / thor2j-tc-appium 의 기존 자산을 **형제 repo
`C:\Users\momen\Projects\qa-suite`** 골격(ARCHITECTURE.md §2)으로 단계 이주.
빅뱅 금지 — "신규는 새 위치, 기존은 손댈 때 이주". 현 `tc-runner/qa-suite/` 는
staging 이며 이주 대상이 아니라 **이주 도구·규약의 검증장**이다.

## 1. 분류 기준 (1초 판정)

- 고치는 이유가 "무엇을 검증할지" → analysis/
- 누적·재탐색에 쓰는 데이터·코드 → learning/ (코드=engine, 데이터=catalogs)
- TC 변환·정적검증·산출 → synthesis/
- 고치는 이유가 "어떻게 실행할지" → automation/ (bug-repro | tc-step | appium)
- 단말×앱 검증 운영 문서(BUG_LOG/RESUME/RESULT)·캠페인 계약 → campaigns/
- 사람에게 설명하는 문서 → docs/
- 모르겠음/구버전 → archive/ (삭제 금지)

## 2. 상태 코드

- `[ ]` 미처리   `[I]` 인벤토리 완료(목적지 확정)   `[M]` 이주 완료   `[A]` archive 행
- provenance status 와의 대응 (닫힌 매핑):
  `[ ]`=—, `[I]`=`planned`/`copied`, `[M]`=`verified`/`source-deprecated`, `[A]`=`archived`.
  **`[M]` 은 verified 이후에만** — copied 상태(복사됐으나 동작 미확인)는 [I] 에 머문다.

## 3. Provenance manifest (이주 행 필수 필드)

이주(`[M]`)되는 모든 행은 `campaigns/manifests/provenance.csv` (형제 repo 생성 시
초기화)에 아래 필드를 기록한다. subtree/submodule 미사용 — 이 manifest 가 출처 추적의
단일 수단이다.

| 필드 | 정의 |
|---|---|
| source_repo | tc-runner \| thor2j-tc-appium |
| source_commit | 복사 시점 원본 repo HEAD (full hash) |
| source_path | 원본 상대경로 |
| target_path | qa-suite 상대경로 |
| source_sha256 | 원본 파일 sha256 |
| target_sha256 | 이주본 sha256 (무변환이면 source 와 동일해야 함) |
| transform_note | 무변환 = `verbatim`. 변환 시 내용 명시 (예: `rename tests→modules`, `redaction`, `encoding LF`) |
| status | `planned` / `copied` / `verified` / `source-deprecated` / `archived` (닫힌 집합) |

## 4. 인벤토리

### tc-runner (`C:\Users\momen\Projects\tc-runner`)
| 상태 | 원경로 | 유형 | 목적지 | 비고 |
|---|---|---|---|---|
| [ ] | (인벤토리 작업으로 채움) | | | |

### thor2j-tc-appium (`C:\Users\momen\Projects\thor2j-tc-appium`)
| 상태 | 원경로 | 유형 | 목적지 | 비고 |
|---|---|---|---|---|
| [ ] | (인벤토리 작업으로 채움) | | | |

## 5. 이주 규칙

1. 진행 중 캠페인 자산(Appium·alt-basic handoff 등)은 캠페인 종료 시점에 통째로 이동.
2. 이동은 복사→동작확인→provenance 기록(`copied`→`verified`)→원본 DEPRECATED 표기
   (`source-deprecated`)→다음 정리 때 삭제.
3. 경로 참조 스크립트는 이동 전 grep 으로 역참조 확인:
   `git grep -n "<파일명>"` 으로 참조처 갱신 목록 작성.
4. 주 1회 _inbox/ 트리아지: 비우거나 목적지 확정.
5. **단말×앱 폴더 분리-매핑**: `<단말명 - 앱명>/` 폴더는 BUG_LOG·MENU_TREE·RESUME·
   RESULT 시리즈를 `campaigns/<단말명 - 앱명>/` 으로 **한 폴더 유지** 이주하고,
   `catalog/` 하위만 `learning/catalogs/<단말명 - 앱명>/` 으로 분리한다
   (커밋 정책이 다름 — append-only tracked data). RESUME 의 세션 재개 운영성을 깨지 않는다.
6. **패키지 개명 규칙**: staging `automation/tests/` 패키지는 이주 시
   `automation/bug-repro/modules/` 로 개명한다 (import `tests.` → `modules.`).
   tc-step 이주 시 들어올 시험 스위트(tests/)와의 repo 내부 이름 충돌 방지.
   staging 에서는 무이동 — 개명은 형제 repo 복사 시점에 수행.
7. raw / keymap / 원본 로그 / report 류는 이주 대상이 아니다 — var/ (local-only) 에서
   새로 생성된다. 기존 산출물은 원본 repo 의 **ignored 영역 잔류** 또는 **repo 밖
   외부 local archive** 만 허용 — **tracked `archive/` 유입 금지** (redaction lock:
   raw/keymap commit 금지는 archive 경유로도 우회 불가).

## 6. 인벤토리 지시문

`docs/guides/inventory_prompt.md` 사용 (실경로·신규 목적지 enum 반영 v2).
