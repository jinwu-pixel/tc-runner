# Menu-Tree v1.2 — Settings/phone Issue-Probe Coordinate System (Design Spec)

> Status: **implementation-partial** (2026-06-05). 무단말 Task 1~6 구현 완료
> (`78279a4` ActionSafety+TCAnchorMapping+corpus audit, `cffa61c` IssueProbePoint+failure_reason).
> **Task 4 (APN/DebugScreen 단말 probe) = gated/pending** — I1·I2 선결 + 단말 승인 후 별도 트랙.
> 근거 = 2026-06-05 TC anchor read-only audit. 본 spec 의 단일 source = 본 문서; 구현 시 §2.3(source-of-truth) 준수.

## 0. Decision (Path 1 only)
- v1.2 = **Settings/phone 이슈 탐색 좌표계 단일 범위.**
- 목적 = BUG/BTS/phone-settings 계열 이슈의 **재현 경로·관찰 지점을 빠르게 좁히는 issue-probe coordinate system**. 대량 TC 자동화 커버 아님.
- **SeniorShield = non-foundational reference domain (reference-only)** — 기반 좌표계 아님(개발 중 앱). §6.
- 폐기 가정: "Settings baseline 이 코퍼스 70 TC 를 직접 덮는다" (audit: SeniorShield 39 / Settings deep-link 4파일 / 현 baseline 매핑 2~3건).

## 0.1 Locked decisions (O1–O4)
- **O1 — 1차 anchor 셋 = APN + DebugScreen.**
  - APN: 코퍼스 `APN_SETTINGS` 6회 등장 + 현 17-screen baseline gap.
  - DebugScreen/IMS/IP: BUG/BTS 이슈 탐색 효용 큼(BTS18697 등).
  - `device_info`/About: 이미 baseline 존재 → **비교 기준(comparison only)**, 신규 anchor 아님.
  - WWAN / USB / SIM / Network = **2차 후보**(P1 1차 제외).
- **O2 — sidecar 위치/명명**: `catalog/anchors/` · `catalog/probes/` 유지. 파일명에 run_id/audit_id 포함.
  - `catalog/anchors/tc_anchor_mapping_<run_id>.json`
  - `catalog/probes/<issue_id>_<run_id>.json`
- **O3 — schema v1 sidecar-only**: `MenuTreeBaseline` 본체 무변경. **schema_version=2 는 아직 열지 않음.**
- **O4 — SeniorShield reference-only**: package-track 착수 안 함. 트리거 = 앱 UI 안정화 + TC corpus 고정 + 사용자 승인.

## 1. Goals / Non-goals
**Goals**
- phone/settings 화면을 이슈 재현 좌표로 정형화: `am start` action ↔ `screen_id` ↔ `nav_path`/`fingerprint`.
- 이슈 트랙(BUG/BTS)에서 **failed_screen / observed_focus / closest_node / failure_reason** 를 빠르게 산출.
- 진입 실패 / 기능 실패 / 문서 drift / 위험 액션 **분리**.
- 입력·토글·파괴 액션 **자동 실행 없이 분류만**.
- run ledger / run_id 시계열(sidecar, append-only) 유지.

**Non-goals (v1.2)**
- 코퍼스 70 전수 자동화 커버.
- SeniorShield/앱별 package baseline(별도 package-track, 시점 미정).
- 전수 메뉴 탐색 / 전 화면 FocusGraph.
- ENTER/CENTER/tap/input/toggle 자동 실행.
- schema_version=2 bump(O3, sidecar 우선).

## 2. Settings baseline 목적 (재정의)
> **issue-probe coordinate system** — 이슈 재현 좌표. 대량 TC 커버 아님.

**우선 anchor (O1 잠금)**: **APN** + **DebugScreen(IMS/IP)**.
- 둘 다 현 17-screen seed 에 없음 → P1 1차 추가 anchor.
- 근거 트랙: BUG-25175(APN) / BTS18697(DebugScreen IMS IP) / BUG-18453(DUN IP).

**2차 후보(P1 제외)**: WWAN/data · USB composition · SIM/operator · Network(wifi/airplane).
**비교 기준(신규 anchor 아님)**: `device_info`/About — 이미 baseline 존재.

> **NOTE — DebugScreen 접근성**: DebugScreen 은 hidden/privileged(예: `com.android.phone/.settings.DebugScreen`, 코드 진입·권한 게이트 가능)일 수 있음. **anchor "후보"로 두되, deep-link 가능 여부·권한 게이트를 먼저 read-only 로 확인**한 뒤 Tier 판정. 접근 불가면 Tier B/C 또는 IssueProbePoint 로 분류.

## 3. Scope tiers (A/B/C)
| Tier | 정의 | 진입 | 좌표 성격 |
|---|---|---|---|
| **A** | deep-link 가능 + read-only dump 가능 | `am start -a/-n` | **auto-observable coordinate** (자동 진입·관찰 가능 — "자동 실행 보장" 아님) |
| **B** | 하드키 nav 필요, 입력/토글 없음 | DPAD(`navigation_only`, screen-scoped) | navigation-required, **read-only 아님** |
| **C** | 입력/토글/삭제/네트워크 변경 | 주로 **shell** 또는 화면 액션 | **분류만, 자동 실행 금지** (guided/manual evidence) |

- 기존 Settings baseline = Tier A 인정(재탐색 X).
- **APN 분리(보강 #2)**:
  - APN 목록/상세 **read-only dump** = **Tier A/B** (진입·관찰).
  - APN **추가/수정/저장/초기화** = **Tier C** (파괴·자동 실행 금지).
- toggle(wifi/airplane via `settings put`/`svc`) · `pm grant/revoke` · `reboot` = Tier C.
- wellbeing = Tier B 후보(파괴 아님).

## 4. 데이터 모델 — schema v1 비파괴 sidecar (O3)
> `src/menu_tree.py`(schema_version=1, `MenuTreeBaseline`) **무변경.** 신규 개념 = run_id/screen_id 조인 sidecar.
> 레이어링 불변: `src/menu_tree.py` 는 `scripts.menu_mapper` import 금지.

### 4.1 TCAnchorMapping — `catalog/anchors/tc_anchor_mapping_<run_id>.json`
1차 key = **`am start` action/component 문자열**(audit상 최고 신뢰도). nav_path/text 는 보조.

| 필드 | 의미 |
|---|---|
| `tc_file` | TC yaml 경로 |
| `entry_action` | `am start -a <action>` 또는 `-n <pkg/comp>` 원문 |
| `screen_id` | baseline 매핑 결과, **null 허용** |
| `domain` | `settings` / `app:<pkg>` / `event` / `external` |
| `match_method` | `deeplink` / `component` / `text` |
| `match_confidence` | 0–1 (deeplink=high, text=low) **필수** |
| `source_expected_texts` | **`{ source: "mmi" \| "figma" \| "tc_yaml", texts: [...] }`** (보강 #4) |
| `device_observed_texts` | baseline observed_texts(실기) |

- **expected vs observed 분리 불변**(drift 보존). `source` 를 붙여 **문서 drift(mmi/figma/tc_yaml) vs 단말 drift** 를 갈라냄.
- text 매핑 = low confidence + ambiguous 플래그(예: SeniorShield 인-앱 "설정" ≠ 시스템 Settings).
- `domain=app:<pkg>` 필드의 **존재 근거 = SeniorShield(reference-only)**: 코퍼스 도메인 편향을 모델이 표현해야 함. 필드는 두되 baseline 구축 대상은 아님(O4).

### 4.2 ActionSafety — element/step 파생 enum (물리 안전성 축)
기존 `MenuElement.kind`/`risk` + **shell command** 에서 derive(평행 taxonomy 금지).

| ActionSafety | 트리거 |
|---|---|
| `read_only` | dump/getprop/verify_shell(read) |
| `navigation_only` | DPAD/HOME/BACK/swipe, am start(진입) |
| `selection_gated` | ENTER/CENTER/tap (screen-scoped allowlist 있을 때만) |
| `input_required` | EditText(`_INPUT_CLASSES`)/input_text |
| `destructive` / `privileged_shell` | **settings put / svc / pm grant-revoke / reboot / content delete** |

> **audit 보정(보강 반영)**: 위험은 tap 보다 **shell**. shell command 를 ActionSafety 분류 1급 대상으로 둔다.

### 4.3 ActionSafety ↔ AutomationClass — **2축(보강 #3)**
- **ActionSafety = 물리 안전성** (액션이 단말 상태를 바꾸는가/되돌릴 수 있는가).
- **AutomationClass(mmi) = 자동화 운용 등급** (자동 실행을 운용해도 되는가).
- 두 축을 **합치지 말고 매핑**:

| ActionSafety | AutomationClass(권장 매핑) |
|---|---|
| `read_only` | `FULL_AUTO` |
| `navigation_only` | **`SEMI_AUTO` 후보** (FULL_AUTO 아님) |
| `selection_gated` | `SEMI_AUTO`(allowlist 충족 시) / else `MANUAL_REQUIRED` |
| `input_required` | `MANUAL_REQUIRED` |
| `destructive` / `privileged_shell` | `MANUAL_REQUIRED` / guided evidence |

- mmi_converter `_AUTO_ACTIONS`(legacy-override 휴리스틱)와 **별개**임을 명시(이전 drift 교훈).

### 4.4 FocusGraph — `catalog/focus/<screen>_<run_id>.json` — 전수 금지
- 적용 조건: **deep-link 불가 + phone/settings 이슈와 직접 연결된 화면이 확인될 때만**. SeniorShield 기준 설계 금지.
- v1.2 Settings 에선 후보 희박(wellbeing 정도, 이슈 연결 확인 시). 하드키 본격 설계는 package-track 으로 미룸.
- node = focus_id/text · edge(NavigationEdge) = from/to/key_action/guard/safety.

### 4.5 IssueProbePoint — `catalog/probes/<issue_id>_<run_id>.json`
- 이슈 재현 screen_id + 상태 + 관찰항목. **1호 사례 = 2026-06-05 privacy settle-probe(20 trial)**.

## 5. Hardkey 정책 (read-only 와 분리)
- DPAD = 상태/focus 변경 → **`navigation_only`**(read-only 아님). `DPAD_UP/DOWN/LEFT/RIGHT`+`BACK`/`HOME` 만, **screen-scoped allowlist**(전역 금지).
- `ENTER`/`DPAD_CENTER` = 기본 영구 금지(최강 게이트, screen별 selection-safe 명시 시만). `CALL/END/POWER`/input/settings put/toggle/delete = 금지.
- 현 `GuardedADB`(HOME/BACK 만)와 **별도 allowlist 모듈**(전역 확장 금지).
- key 이동마다 focus/text/fingerprint 기록.

## 6. SeniorShield — Non-foundational reference domain (reference-only)
- 코퍼스 비중 최대(39 TC)지만 **개발 중 앱** → v1.2 기반 좌표계 아님. baseline/FocusGraph/anchor 우선순위로 올리지 않음.
- 역할 = (a) 현 코퍼스 도메인 편향 설명 사례, (b) TCAnchorMapping `domain=app:<pkg>` 필요성 근거.
- 앱별 baseline = **앱 UI 안정화 + TC corpus 고정 + 사용자 승인** 후 별도 package-track(O4).

## 7. Phase / 게이트
- **P0**(완료) audit → **P1** anchor(APN+DebugScreen) seed 후보화·접근성 확인 → **P2** Tier A seed 확장(ledger 유지, full vs subset) → **P3** hardkey(별도 allowlist, 조건 충족 화면만) → **P4** input/toggle 분류만 → **P5** TC 실패 분류 부착.
- 실패 분류: `failed_screen_id·expected_nav_path·observed_focus·closest_menu_node·failure_reason`.
  - `failure_reason ∈ { unreachable, focus_mismatch, text_missing, risky_action, input_required, document_drift }`.
  - `text_missing` = `source_expected_texts` vs `device_observed_texts` 비교.
- **게이트**: 코드/단말 사전 승인 · DPAD allowlist 확장 = 별도 강한 승인 · ENTER/CENTER/input/tap = 최강 게이트 · commit/push = batch · raw XML = local carry / JSON·MD digest+ledger 만 commit 후보.

## 8. TDD task 분할 스케치 (plan 후보)
1. `ActionSafety` derive(순수, kind/risk/**shell**→enum) + test.
2. `TCAnchorMapping` emitter(순수, `am start` 파싱→sidecar json, source 포함) + test.
3. TC 코퍼스 anchor 추출 audit 재현(read-only) — P1 anchor 검증.
4. APN/DebugScreen anchor seed 확장 + 접근성 확인 + ledger run(단말 승인).
5. hardkey allowlist 모듈(가드+test, 단말 전) → FocusGraph(단말 승인, 조건 충족 화면만).
6. TC 러너 `failure_reason` 부착(연동).

## 9. Success criteria
- 메뉴트리→TC 자동화 입력 연결 구조 설명됨(TCAnchorMapping: screen_id null 허용·domain·confidence·source).
- 하드키 탐색이 read-only 안전정책과 분리됨(navigation_only, screen-scoped allowlist).
- 입력/토글/파괴 자동 실행 안 함 기준 명확(ActionSafety, shell 포함; APN 진입/편집 분리).
- run ledger/run_id 시계열 유지(sidecar, schema v1 무변경).
- 다음 구현 task 를 TDD 순서로 분해 가능(§8).

## 10. Open issues (spec 후속)
- I1. DebugScreen 실제 deep-link/권한 게이트 — P1 시작 시 read-only 확인 필요(§2 NOTE).
- I2. APN read-only dump 시 민감정보(IMS/IMSI/operator 비밀) 노출 가능 → raw carry 정책 + redaction 여부 검토.
- I3. `closest_menu_node` 산출 알고리즘(fingerprint/text 거리) — plan 단계 상세화.
- I4. SeniorShield package-track 트리거 정량 기준(O4) — 후속.

## 11. 폐기된 가정 / Non-goals 재확인
- Settings baseline 으로 코퍼스 70 전수 커버 — 폐기.
- SeniorShield 기반 좌표계/FocusGraph/anchor 우선 — 비채택(reference-only).
- 전 화면 FocusGraph — 비채택.
- schema_version=2 — v1.2 에서 열지 않음(O3).
