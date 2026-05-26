# SETTINGS_SMOKE_01 — app launch scope

**Status:** SCOPE; not committed; YAML not written; runtime not executed.
**단말:** ODIN2 (AT-M150) · serial `<device_serial>` · 720x1560 @ 320dpi
**앱:** `com.android.settings` v1.0.0.1101
**probe 근거:** `ODIN2 - Settings/probe_settings_home.xml` (Phase 0, 2026-05-08)

---

## 1. 목표
- Settings 앱 cold launch 후 root 화면 진입 검증
- 정적 anchor 6개로 home 화면 정합성 확인
- read-only — toggle / permission / system write 없음

## 2. 예상 steps (YAML 작성 단계의 후보 — 본 scope에서는 합의 대상)
1. SETUP — `force-stop com.android.settings`
2. SETUP — `monkey -p com.android.settings 1` 또는 `am start -n com.android.settings/.Settings`
3. SETUP — `wait 1500ms` (foreground stabilize)
4. VERIFY — `verify_text "설정"` (헤더 anchor)
5. VERIFY — `verify_text "네트워크 및 인터넷"`
6. VERIFY — `verify_text "연결된 기기"`
7. VERIFY — `verify_text "앱"`
8. VERIFY — `verify_text "알림"`
9. VERIFY — `verify_text "배터리"`
10. CLEANUP — `force-stop com.android.settings` (상태 초기화)

총 10 step. 좌표 tap 0, 입력 0, mutation 0.

## 3. anchor 후보 (probe 실측 기반)
정적 visible text 15건 중 6건 채택:

1. `설정` — 헤더 (가장 안정)
2. `네트워크 및 인터넷` — top-level menu
3. `연결된 기기` — top-level menu
4. `앱` — top-level menu
5. `알림` — top-level menu
6. `배터리` — top-level menu (sub-label은 dynamic이지만 main label 정적)

배제 (dynamic / 통신사 customization):
- `86% - 저속 충전 중` (배터리 % dynamic)
- `26% 사용 - 94.95GB 사용 가능` (저장용량 % dynamic)
- `T 로밍` (SKT 통신사 customization, 횡 단말 비교 시 부재 가능)
- `안심 기능` / `SOS 버튼, 수신 차단` (단말 customization 가능성)

대안 anchor 후보 (예비, scope 보강 시 사용):
- `설정 검색` (검색 placeholder)
- `저장용량` (main label만, sub-label 배제)

## 4. cleanup
- `force-stop com.android.settings` 1회 — settings 종료, persistent 변경 없음
- 재부팅 / 캐시 삭제 / 권한 변경 / 계정 변경 — 없음

## 5. mutation risk
- read-only verify 한정 → mutation risk 0
- 단, dump 직후 사용자가 임의로 토글 누를 가능성 차단 위해 cleanup 1회 보장

## 6. risk
- OS / 제조사 / 통신사 label 차이 → 본 scope는 ODIN2 (AT-M150) 단말 1대 기준. 횡 단말 검증은 별도 scope
- `배터리` 등 main label은 정적이지만 sub-label dynamic — verify_text는 main label 부분만 정확 매칭 (substring 정책 그대로)
- scroll 가능성 — Phase 0 dump에서 17 texts 단일 dump 가능 확인. Runtime에서 재현 불일치 시 scroll step 추가 필요 (현재 scope는 scroll 0 가정)
- `am start -n` 권한 — 시스템 settings는 일반적으로 starting 가능, 권한 거부 발생 시 `monkey` fallback

## 7. capability
- 신규 capability: **0**
- 기존 capability로 충분:
  - force-stop (`am force-stop`)
  - launch (`am start -n` 또는 `monkey -p`)
  - wait (ms)
  - verify_text (substring match)
- gap: 없음

## 8. generated artifact policy
- probe XML: `ODIN2 - Settings/probe_*.xml` — **commit 금지**
- catalog: `ODIN2 - Settings/catalog/` — **commit 금지** (catalog build는 SMOKE_01 단계에서 수행 여부 별도 결정)
- reports: `reports/` — **commit 금지**
- commit candidate (사용자 승인 후):
  - `ODIN2 - Settings/RESUME.md`
  - `ODIN2 - Settings/MENU_TREE.md`
  - `ODIN2 - Settings/BUG_LOG.md`
  - `ODIN2 - Settings/SETTINGS_SMOKE_01_app_launch_scope.md`
  - (option, 차후 단계) `ODIN2 - Settings/SETTINGS_SMOKE_01_app_launch.yaml`

## 9. non-goals
- 하위 화면 탐색 (네트워크/연결된기기/앱 등 진입 — Phase 1+ 후보)
- 검색 입력 / 설정 변경
- 단말/OS 횡 비교
- catalog delta 자동 분류 적용
- PR 7A delta tool runtime gate 적용
- PR 8 anchor recommender 적용
- policy v2 / Tier 0 자동화 적용

## 10. decision boundary
- 본 scope 문서를 commit candidate로 보고만 함 — **현재 commit 미수행**
- YAML 작성 / runtime 실행 / catalog build / commit / push — 모두 사용자 결정(A/B/C/D) 이후
