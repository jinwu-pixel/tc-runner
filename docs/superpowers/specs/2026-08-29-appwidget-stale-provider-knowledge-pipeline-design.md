# AppWidget stale-provider 지식·재현 파이프라인 설계

- 날짜: 2026-08-29
- 상태: 사용자 승인됨 (2026-08-29)
- 근거 사례: BUG 27084 / AT-M140 Launcher
- 적용 repo: `C:\Users\momen\Projects\tc-runner`
- 권위 원장: qa-suite `MIGRATION.md` 기준 관련 코드·문서의 writer는 tc-runner

## 1. 목적

BUG27084 실기에서 확인한 AppWidget stale-provider 재현 지식을 일회성 결과 문서에만 두지 않고 다음 작업에 재사용할 수 있는 구조로 흡수한다.

흡수 순서는 다음과 같다.

1. 개인 메모리와 이슈 상태에 재사용 지식을 남긴다.
2. `AGENTS.md`/`CLAUDE.md`에는 보편 진단 원칙만 추가한다.
3. 상세 Android 절차는 별도 플레이북을 단일 source로 둔다.
4. 위험한 단말 조작은 전용 fail-closed harness에서 먼저 검증한다.
5. 여러 실기 캠페인에서 재사용성이 입증된 동작만 core runner 후보로 승격한다.

이 설계는 BUG27084 수정 자체를 구현하지 않는다. Launcher source는 개발사 영역이며, 본 repo의 역할은 재현·검증·증거 누적이다.

## 2. 근거와 현재 결론 경계

### 2.1 직접 관찰

- 현재 취약 빌드: AT-M140 `RY07260901S`
- 비날씨 앱: SimpleClock 2.1.6/code216, 서명 토큰 `498de32a`
- 정방향 stale-provider 독립 구성: 동일 line 185→88 Launcher NPE `3/3`
- 개발사 절차 `pm clear → force-stop → reboot`: Launcher crash `0/3`
- 개발사 절차에서는 Weather `WeatherWidget4x1`의 widget id와 `RemoteViews`가 재부팅 전후 유지됨
- 현재 fixed build `AT-M140Z0827U_DAILY_DEV_GMS_849` 실물은 미확보

### 2.2 허용되는 결론

- 특정 Weather 앱·버전만의 결함이라는 가설은 기각한다.
- `stopped=true`는 충분조건이 아니다.
- 관찰된 직접 조건은 `Launcher DB stale record ↔ AppWidgetService widget binding 부재`다.
- 비재현 절차가 해당 내부 상태를 만들지 못하면 `runtime precondition FAIL`로 분류한다.
- exact fixed build에서 동일 상태의 역방향이 끝나기 전에는 fixed-build `runtime PASS`를 보고하지 않는다.

### 2.3 허용되지 않는 일반화

- 모든 3rd-party 위젯이 일반적인 앱 업데이트만으로 재현된다고 말하지 않는다.
- `pm clear`와 uninstall/reinstall을 동등한 package lifecycle로 취급하지 않는다.
- provider registry에 component가 존재한다는 사실만으로 widget binding이 정상이라고 판정하지 않는다.
- 현재 OTA 결과를 개발사 daily fixed build 결과로 대신하지 않는다.
- 개발사가 주장한 SEL-J 영향 범위를 직접 증거 없이 실기 확인된 것으로 보고하지 않는다.

## 3. 핵심 진단 모델

AppWidget 상태를 다음 세 층으로 분리한다.

| 층 | 권위 관찰 | 의미 |
|---|---|---|
| Package | `dumpsys package` | 앱 설치·버전·서명·UID·`stopped`·`notLaunched` |
| AppWidgetService | `dumpsys appwidget` | provider 등록과 실제 widget id binding·host·`RemoteViews` |
| Launcher | HOME role·Launcher log/crash·화면 | Launcher DB record 소비와 pending placeholder 처리 결과 |

### 3.1 provider 등록과 binding 분리

다음 필드를 독립 값으로 기록한다.

- `provider_registered`
- `provider_app_uid`
- `widget_bound`
- `widget_id`
- `host_id`
- `remote_views_present`
- `package_stopped`

앱 재설치 후 새 UID의 provider가 다시 등록돼도 과거 widget id가 `Widgets:`에 없으면 binding은 소실된 것이다.

### 3.2 state-equivalence gate

정·역 비교의 동등성은 명령 목록이 아니라 내부 상태로 판정한다.

fixed build 비재현을 유효하게 인정하려면 다음 상태를 먼저 증명한다.

1. 취약 빌드에서 정상 binding이 존재했다.
2. Launcher data를 지우지 않은 채 과거 widget id binding이 소실됐다.
3. 앱은 동일 package/signature 조건으로 설치돼 있다.
4. 일반 HOME이 stale record를 읽는 조건이 유지됐다.
5. fixed build 적용 과정이 위 상태를 삭제하지 않았다. clean flash면 fixed build에서 상태를 다시 생성한다.

2~4를 증명하지 못하면 결과는 `runtime precondition FAIL`이다.

### 3.3 Launcher DB 증거 등급

LauncherProvider가 signature permission으로 직접 읽히지 않을 수 있으므로 증거 등급을 둔다.

| 등급 | 값 | 기준 |
|---|---|---|
| 직접 | `DIRECT_DB` | 권한 있는 dump/DB에서 stale id 확인 |
| 로그 | `LOADER_LOG` | `Widget provider not found for id=...`와 pending stack 확인 |
| 상태보존 | `PRESERVED_PREUPGRADE` | 취약 빌드에서 LOADER_LOG/동일 crash 확인 후 Launcher data 유지 업그레이드 |
| 추론 | `INFERRED_ONLY` | binding 부재와 증상만 있고 Loader/DB 근거 없음 |

fixed-build 판정은 `DIRECT_DB`, `LOADER_LOG`, `PRESERVED_PREUPGRADE` 중 하나를 요구한다. `INFERRED_ONLY` 단독은 blocker다.

## 4. 흡수 아키텍처

### 4.1 Layer A — Codex 개인 메모리

`C:\Users\momen\.codex\memories\MEMORY.md`는 생성·통합 산출물이므로 직접 편집하지 않는다. 아래 ad-hoc note를 추가해 memory consolidation 입력으로 사용한다.

```text
C:\Users\momen\.codex\memories\extensions\ad_hoc\notes\
20260829-appwidget-stale-provider-state-equivalence.md
```

메모리의 scope는 `tc-runner / Android AppWidget stale-provider diagnosis`로 제한한다. 포함할 재사용 지식은 다음과 같다.

- `pm clear`/force-stop은 AppWidget binding 제거와 동치가 아니다.
- command-equivalence보다 state-equivalence가 우선한다.
- provider registry와 widget instance를 분리해 읽는다.
- inactive HOME에서 package uninstall/reinstall이 stale Launcher record를 만들 수 있다.
- 다중 단말 연결 시 destructive 명령은 exact serial·model·fingerprint를 결박한다.
- 재현 후 안전 HOME role과 잔존 mutation을 `RESUME.md`에 남긴다.

개별 serial, 좌표, 일시적 widget id는 개인 메모리의 보편 규칙에 넣지 않고 issue evidence/profile에 둔다.

### 4.2 Layer B — repo 핵심 지침

`AGENTS.md`와 `CLAUDE.md`를 플랫폼별 명칭 차이만 유지한 채 동기 갱신한다.

추가 범위:

1. §4.1: package lifecycle 가설을 `clear`, `force-stop`, `disable`, `package replace`, `uninstall/reinstall`로 분리
2. §4.2: state-equivalence gate와 `runtime precondition FAIL` 규칙
3. §4.2: 비무선 도메인에서는 carrier를 억지 축으로 사용하지 않고 domain-relevant 독립 축을 명시하는 axis-applicability 규칙
4. §4.6: BUG27084 대표 사례 한 줄
5. §8.2: 교훈 row를 `proposed`로 추가하고 본문 반영 승인 후 `applied`로 전환

상세 좌표·package·component·widget id는 핵심 지침에 넣지 않는다.

### 4.3 Layer C — 상세 플레이북

신규 SoT:

```text
docs/appwidget_stale_provider_verification.md
```

`docs/tc_patterns.md`에는 짧은 요약과 위 문서 링크만 추가한다. 현재의 `CLAUDE.md` 단독 참조 표현은 `AGENTS.md`/`CLAUDE.md` 공통 지침 참조로 정렬한다.

플레이북 내용:

- 3층 진단 모델
- 정방향·음성 대조군 절차
- lifecycle trigger matrix
- fixed-build A/B 판정
- Google Go 회귀 축
- 단말 안전·복구
- 증거 파일 목록과 판정 어휘

### 4.4 Layer D — issue 상태 원장

다음 파일을 생성·정렬한다.

```text
AT-M140 - Launcher BUG27084/BUG_LOG.md
AT-M140 - Launcher BUG27084/RESUME.md
AT-M140 - Launcher BUG27084/MENU_TREE.md
```

`BUG_LOG.md`는 현재 상태만 유지한다.

- 진단 상태: `OBSERVED`
- 이슈 상태: `IN_PROGRESS`
- 현재 blocker: exact fixed build 미확보
- 현재 root-cause 범위와 증거 bundle 링크

`RESUME.md`는 다음 세션의 안전 가드다.

- AT-M140 serial/build
- 최종 HOME role
- stale state 보존 여부
- 일반모드 전환 시 crash 가능성
- Weather data clear 등 잔존 mutation
- 다음 허용 작업과 필요한 승인

`MENU_TREE.md`는 앱 전체 메뉴트리가 아니라 이 이슈에 필요한 mode/widget topology만 기록한다.

```text
Simple HOME
  └─ SwitchModeActivity → General HOME
General HOME
  ├─ long-press → Widget picker
  └─ SwitchModeActivity → Simple HOME
```

기존 `RESULT_2026-08-28.md`에는 후속 정정 결과 링크를 추가하고, `RESULT_2026-08-29.md`/`result.json`에는 SimpleClock APK source manifest SHA와 split별 SHA를 pin한다.

### 4.5 Layer E — 전용 재현 harness

신규 파일 후보:

```text
scripts/appwidget_stale_provider_repro.py
scripts/appwidget_stale_provider_profiles.py
tests/test_appwidget_stale_provider_repro.py
```

첫 구현은 core runner action/schema를 변경하지 않는 독립 harness다.

#### CLI

```text
plan
capture
bind
arm
trigger
verify
restore
```

- 기본 command는 `plan`이며 mutation을 수행하지 않는다.
- mutating command는 exact `--serial`, `--profile`, `--expected-model`, `--expected-fingerprint`, `--execute`를 요구한다.
- live multi-cycle `campaign` command는 첫 버전에 넣지 않는다. Tier-0 multi-task 자동연속이 승격되지 않았고 device mutation은 매회 승인 대상이기 때문이다.
- 여러 단말이 연결돼 있어도 exact serial이 일치하면 해당 단말만 사용한다. serial 누락·불일치·offline·unauthorized는 fail-closed다.

#### profile

AT-M140 전용 값은 profile에 둔다.

- Simple/General HOME package와 switch activity
- 화면 크기·widget picker drag 좌표
- 확인 dialog 좌표 또는 selector
- expected Launcher package/version
- 앱 package/provider/split APK pin

좌표 실행 전 현재 activity와 480×800 viewport를 확인한다. 다른 viewport에서 좌표 fallback을 사용하지 않는다.

## 5. harness 상태기계

| 상태 | 필수 gate | 허용 다음 단계 |
|---|---|---|
| `BASELINE_CAPTURED` | serial/model/fingerprint/role/package/appwidget 동결 | `bind` |
| `BOUND_GENERAL` | General HOME, widget id·provider·RemoteViews 존재 | `arm` |
| `SAFE_SIMPLE` | Simple HOME role 확인 | uninstall/reinstall |
| `STALE_ARMED` | 동일 package/signature 설치, 과거 widget id 없음, provider registry 존재 | `trigger` |
| `TRIGGERED_BUG` | General HOME 전환 + line185/88 signature | `restore` 또는 보존 |
| `TRIGGERED_FIXED` | General HOME 렌더링·process 안정·NPE 0 + stale precondition 증명 | 회귀 축 |
| `RESTORED_SAFE` | Simple HOME 또는 clean General HOME, final mutation ledger 기록 | 종료 |

gate가 맞지 않으면 다음 mutation을 수행하지 않는다.

### 5.1 bind gate

다음을 모두 요구한다.

- target provider component 일치
- Launcher host package 일치
- widget id 존재
- `views=android.widget.RemoteViews` 존재

위젯 미배치 상태에서 단순 provider registry만 보고 `bind` 성공으로 처리하지 않는다.

### 5.2 arm gate

다음을 모두 요구한다.

- HOME role이 Simple HOME
- uninstall 성공 RC
- install-multiple 성공 RC
- versionCode/versionName/signature가 input pin과 일치
- 과거 widget id가 `Widgets:`에서 사라짐
- 새 provider UID가 기록됨

### 5.3 trigger gate

General HOME role 전환 완료를 polling한 뒤 다음을 수집한다.

- crash buffer
- Launcher process/exit-info
- foreground window/HOME role
- screenshot
- AppWidgetService post-state

고정 sleep만으로 판정하지 않는다. polling timeout은 증거에 기록하며 timeout은 `runtime precondition FAIL` 또는 명시적인 step FAIL이다.

### 5.4 restore/preserve

- 기본은 crash loop를 멈추고 Simple HOME으로 복구한다.
- `--preserve-armed-state`는 별도 명시 옵션이며 사용자 승인과 `RESUME.md` 갱신을 요구한다.
- preserve 상태에서는 완료 문구에 현재 role과 일반모드 전환 위험을 반드시 포함한다.

## 6. 증거 bundle 계약

run id는 repo runtime bundle과 정렬해 UTC `YYYYMMDDTHHMMSSZ`를 사용하고, 각 event에 KST와 UTC를 함께 기록한다.

```text
AT-M140 - Launcher BUG27084/evidence/<run_id>/
  run.json
  events.jsonl
  inputs.json
  snapshots/
    package_*.txt
    appwidget_*.txt
    role_*.txt
    build_*.txt
    crash_*.txt
  screenshots/
  result.json
  verification.txt
  evidence_sha256.txt
```

### 6.1 `events.jsonl`

각 행은 다음을 포함한다.

- host timestamp UTC/KST
- device elapsed realtime 가능 시 값
- boot id
- phase
- command category
- redacted command
- target serial
- RC
- stdout/stderr digest
- resulting state

APK 경로·민감정보는 원문 명령 대신 digest와 logical input id로 기록한다.

### 6.2 `inputs.json`

split APK를 매 run마다 중복 복사하지 않아도 되지만 다음을 immutable pin한다.

- source evidence bundle 상대경로
- source `evidence_sha256.txt` SHA-256
- 각 split 파일명·크기·SHA-256
- package/version/signature token

source manifest나 split hash가 다르면 실행 전 fail-closed한다.

### 6.3 `result.json`

핵심 필드:

- `diagnosis_status`
- `evidence_term`
- `precondition_status`
- `provider_registered`
- `widget_bound_before`
- `widget_bound_after`
- `launcher_stale_record_evidence`
- `crash_signature_count`
- `launcher_crash_exit_count`
- `launcher_crash_exit_pids`
- `launcher_loader_record_count`
- `launcher_loop_observed`
- `launcher_loop_basis`
- `home_rendered`
- `launcher_process_stable`
- `launcher_stability_window_s`
- `final_home_role`
- `mutations_remaining`

단독 `passed: true`로 진단 의미를 압축하지 않는다.

## 7. lifecycle trigger matrix

known-bad 빌드에서 각 행을 독립 binding으로 구성한다.

| lifecycle | 목적 | 예상/현재 |
|---|---|---|
| `pm clear + force-stop + reboot` | 개발사 절차 대조 | binding 유지, `runtime precondition FAIL` 관찰됨 |
| uninstall/reinstall 동일 APK | 강한 정방향 | binding 소실, BUG-GAP 관찰됨 |
| `install-multiple -r` 동일 APK | in-place replace 영향 | 측정 필요 |
| Weather 7.7.8→7.8.2 in-place update | Play Store 유사 update | 측정 필요 |
| disable/enable | component 일시 비활성 | 측정 필요 |
| provider component 제거/rename update | 실제 missing-provider 경로 | 해당 APK 조합이 있을 때 측정 |
| data 유지 OTA | stale state 보존성 | 현재 OTA 지속 관찰, exact fixed build 필요 |

각 행은 한 변수만 변경하고 기존 Launcher/widget fixture를 새로 구성한다. 같은 widget id를 재사용한 반복 reboot는 반복 관찰로 기록하되 독립 fixture라고 부르지 않는다.

## 8. fixed-build A/B와 회귀 축

### 8.1 fixed-build 판정

fixed build에서 다음을 모두 만족해야 해당 범위의 `runtime PASS`다.

1. stale precondition이 state-equivalence gate를 충족
2. General HOME UI가 렌더링됨
3. Launcher process가 관찰 구간 동안 유지됨
4. crash buffer/exit-info에 line185/88 NPE 0건
5. pending widget이 안전한 placeholder로 표시되거나 stale record가 정리됨
6. 정상 Weather/SimpleClock widget update가 계속 동작

관찰 구간과 반복 분자/분모를 명시한다.

### 8.2 Google Go 회귀

개발사 수정이 TASK_20986 Google Go focus 로직을 변경하므로 다음을 별도 축으로 검증한다.

- Google Go widget의 content description과 DPAD focus 처리
- `remoteViews != null` 정상 update 경로
- non-Google widget으로 이동 시 focus background flag reset
- pending `remoteViews == null` 경로에서 NPE 없음
- 일반 widget의 tap/update/resize 기본 동작

stale-provider 방어 성공만으로 Google Go 회귀까지 통과했다고 보고하지 않는다.

### 8.3 variant 축

Launcher/UI 도메인에서는 carrier가 직접 인과축이 아니므로 carrier를 억지로 채우지 않는다.

- 앱/provider 축: Weather 계열 + 비날씨 provider
- build 축: known-bad + exact fixed
- variant 축: SEL 실기, SEL-J는 별도 실기 또는 exact Launcher binary/source 동등성 근거
- 조건 축: binding 정상 + stale binding

carrier는 `NOTE/N/A`로 남기고 진단에 적합한 축을 선택한 이유를 기록한다.

## 9. core runner 승격 게이트

첫 구현에서는 `src/`, schema, validator를 변경하지 않는다.

다음 조건을 모두 만족한 뒤 별도 설계·승인을 받아 core action 승격을 검토한다.

1. 전용 harness host tests 통과
2. AT-M140 known-bad 정방향/음성 대조군 재수행
3. exact fixed build A/B 수행
4. 최소 두 provider 또는 두 독립 캠페인에서 같은 action 요구 확인
5. 좌표/profile 실패가 fail-closed로 수집됨
6. cleanup/preserve 계약이 실기에서 검증됨

승격 후보:

- `drag_and_drop`
- `verify_shell_until`
- `capture_shell`

install/uninstall은 generic shell action으로 우회하지 않는다. 승격 시 정의·schema·loader·runner·validator·tests·`runner_capability.yaml`을 같은 변경으로 정렬한다.

## 10. 오류 처리와 안전

### 10.1 hard stop

다음은 즉시 중단한다.

- target serial 불일치/누락
- model/fingerprint mismatch
- expected HOME role 미도달
- input APK hash/signature mismatch
- widget binding 미확인
- Launcher DB clear 감지 또는 예기치 않은 data reset
- 다른 phase의 stale evidence 혼입
- screenshot/UI dump 실패가 primary verdict를 가림

### 10.2 다중 단말

`adb devices`에 여러 단말이 있어도 전용 harness는 exact serial로만 명령한다. 대상 외 단말에는 read/write 명령을 보내지 않는다. core runner의 `multi_device: false`는 그대로 유지하며 이 harness의 serial pin을 동시 실행 지원으로 해석하지 않는다.

### 10.3 승인 경계

- `capture`는 read-only다.
- `bind`, `arm`, `trigger`, `restore`, reboot, install/uninstall, data clear는 device mutation으로 매 실행 사용자 승인 대상이다.
- commit/push는 별도 승인이다.
- design 승인과 device 실행 승인을 합치지 않는다.

## 11. 시험 전략

### 11.1 host tests

fake ADB transcript로 다음을 검증한다.

- provider 등록과 widget binding 파서 분리
- old widget id 소실 검증
- version/signature/hash mismatch fail-closed
- wrong-device guard
- 여러 단말에서 exact serial 외 명령 0
- phase 순서 위반 차단
- condition polling timeout
- primary exception 보존과 cleanup error 부착
- result/manifest 결정론
- `--preserve-armed-state` 없는 teardown 생략 차단

### 11.2 device smoke

1. read-only `capture`
2. widget `bind`까지만 수행하고 복구
3. known-bad 단일 정방향
4. 개발사 절차 단일 음성 대조군
5. 승인된 n-cycle
6. exact fixed build A/B

앞 단계 증거 확인 전 다음 단계로 진행하지 않는다.

## 12. 구현 단계

### Phase 1 — 지식·상태 정렬

- memory ad-hoc note
- `AGENTS.md`/`CLAUDE.md` 보편 규칙과 §8.2 proposed row
- 상세 플레이북과 `tc_patterns` 링크
- BUG_LOG/RESUME/MENU_TREE
- RESULT/APK provenance cross-link

### Phase 2 — host-only harness

- parser/state machine/CLI/profile
- fake ADB tests
- plan/capture artifact verification

### Phase 3 — 승인된 device pilot

- known-bad 1-cycle
- negative 1-cycle
- 결과 대조 후 n-cycle 여부 결정

### Phase 4 — fixed build verification

- exact build identity
- data-preserved 또는 recreated stale state
- fixed 판정 6조건
- Google Go 회귀

### Phase 5 — core 승격 판단

- 승격 게이트 충족 시 별도 디자인
- 미충족 시 전용 harness를 정식 운영 도구로 유지

## 13. 완료 기준

본 설계의 구현은 다음을 모두 만족해야 완료로 간주한다.

- 개인 메모리와 repo SoT가 중복 없이 연결됨
- `AGENTS.md`/`CLAUDE.md` 의미 정렬
- issue folder가 다음 세션에 안전한 RESUME 상태를 제공
- harness가 plan-default·serial-required·phase-gated로 동작
- host tests가 상태 파서와 safety failure를 검증
- 증거 bundle이 event/input/result/hash provenance를 남김
- fixed build 미확보 상태를 성공으로 오인하지 않음
- core runner는 승격 조건 전까지 변경되지 않음

## 14. 명시적 비목표

- Launcher source 수정
- FTP build 업로드 자동화
- Play Store 자동 다운로드
- 첫 버전의 무인 다중-cycle 실행
- 모든 Android Launcher/AppWidget 조합 지원
- qa-suite와 tc-runner 동시 write
- 승인 없는 commit/push

## 15. 설계 결정 요약

- 채택: 단계적 흡수(A안)
- 채택: state-equivalence를 재현 판정의 핵심 gate로 사용
- 채택: 상세 절차와 core 원칙 분리
- 채택: 전용 harness 선검증, core runner 후승격
- 채택: exact serial pin으로 대상 외 단말 보호
- 채택: fixed-build A/B와 Google Go 회귀를 분리
- 보류: core action 추가
- 보류: 무인 multi-cycle
- 보류: SEL-J 일반화

## 16. 2026-09-01 실기 amendment — 일반성과 해소책 우선

### 16.1 현재 결론

- Weather 7.7.8, Weather 7.8.2, 패키지·서명이 다른 AccuWeather, 비날씨 SimpleClock 2.1.6에서 동일 `LauncherAppWidgetHostView.java:185` → `PendingAppWidgetHostView.java:88` 크래시가 관찰됐다.
- SimpleClock 정방향은 독립 binding 3개에서 3/3이다. AccuWeather와의 formal A/B는 각 셀 n=1이므로, 특정 날씨앱·버전·날씨 데이터만으로 발생한다는 가설을 지지하지 않는 수준으로 한정한다.
- 직접 관찰된 공통 축은 `Launcher DB stale widget record ↔ AppWidgetService binding 부재`이며, 진단 상태는 known-bad 정량 반복과 exact fixed build A/B 전까지 `OBSERVED`로 유지한다.

### 16.2 남은 실험의 중심

1. 예방 우회: 앱 제거·교체 전 위젯을 제거한 조건에서 stale record와 크래시가 생성되지 않는지 정·역 확인
2. 상태 정리 우회: stale widget을 개별 격리·정리할 수 있는 경로와 Launcher data clear의 영향·손실 범위 분리
3. 펌웨어 수정: exact fixed build에서 동일 stale 상태를 보존한 채 HOME 렌더링, Launcher process 안정성, line185/88 NPE 0건, 안전 placeholder 표시 또는 stale record 정리를 함께 검증
4. 정상 회귀: 수정후 Weather·SimpleClock·Google Go의 정상 bind/update/tap 경로가 유지되는지 별도 회귀 검증

### 16.3 크래시 루프 안전 복구

- UI mode switch가 Launcher 재크래시 주기보다 느려 실패하는 경우에만 `restore --direct-home-role-recovery --execute`를 허용한다.
- 실행 전 exact device identity, 현재 General HOME role, `home_role:general` mutation 원장, `android:id/alertTitle`의 exact allowlist 제목(`MIVE Home이(가) 중지됨`, `MIVE Home이(가) 계속 중단됨`), `android:id/aerr_close`를 모두 요구한다.
- 변경은 `cmd role add-role-holder --user 0 android.app.role.HOME com.hnlens.simplemode` 후 `KEYCODE_HOME`로 한정하며 대화상자 tap·Launcher data clear·앱 설치/제거를 포함하지 않는다.
- 성공은 HOME role, resumed activity, UI hierarchy의 exact `com.hnlens.simplemode` package 3-way 일치로만 판정한다. 일치하지 않으면 mutation 원장을 남기고 fail-closed한다.
- direct role write 후 3-way가 실패해 `home_role:unverified`가 남은 run을 기본 restore로 재시도해도, fresh 3-way 일치 전에는 HOME mutation 원장을 제거하거나 `RESTORED_SAFE`를 선언하지 않는다.
- 본 경로는 실험 지속을 위한 안전 인프라이며 BUG27084 해소책이나 fixed-build 검증 결과로 계수하지 않는다.

### 16.4 AccuWeather 정·역 A/B 실기 반영 (2026-09-01)

- `AT_M140_BUG27084_ACCUWEATHER_V1` 프로파일을 추가했다. package/version/signature, `accuweather_apk` split 4개, source manifest, `36시간 예보` 카드와 exact provider component를 pin한다.
- config activity의 `저장` 버튼은 exact resource-id로 self-verify한 뒤 tap한다. provider variant가 preview에 없거나 removal 시작점이 exact widget selector bounds 밖이면 mutation 전에 fail-closed한다.
- A `20260901T060745Z`: 위젯 ID 50 UI 제거와 binding 소멸을 먼저 증명한 뒤 동일 APK uninstall/reinstall. 일반 HOME 10초 안정, line185/88 신규 signature 0, `NO_TRIGGER_OBSERVED`, 최종 `RESTORED_SAFE`/mutation 0.
- B `20260901T061739Z`: 위젯 ID 51을 Launcher에 남긴 채 동일 lifecycle. stale precondition `PASS`, 일반 HOME에서 신규 signature 1, `TRIGGERED_BUG`, `BUG-GAP observed`, 최종 Simple HOME `RESTORED_SAFE`.
- 두 bundle manifest는 독립 재검증을 통과했고 events target serial은 AT-M140 단일값이다. 이 결과는 예방 우회가 SimpleClock뿐 아니라 다른 날씨앱·서명의 AccuWeather에서도 성립함을 직접 지지한다.
- 결론 경계는 유지한다. 두 provider A/B는 특정 Weather 앱 전용 결함이라는 설명을 약화하지만, 각 formal 셀이 n=1이고 B는 단일 crash 뒤 10초 내 회복했으며 stale 증거도 `INFERRED_ONLY`다. 따라서 field crash loop 재현, 발생률, 모든 3rd-party 위젯에 대한 보편성은 주장하지 않는다.

### 16.5 정량 반복과 loop 증거 게이트

- fixed build 비교 전에 known-bad의 SimpleClock·AccuWeather A/B 각 셀을 독립 fixture **n=5**로 반복한다. 발생률이 불안정하거나 판정 경계이면 n=10으로 확장한다.
- 매 cycle은 신규 run_id와 신규 widget ID를 사용한다. 이전 Launcher record를 재사용한 연속 trigger는 독립 시행으로 세지 않는다.
- 관찰 창 기본값은 30초다. 창 종료 시 active-boot baseline 대비 BUG27084 signature 수와 exact launcher package의 신규 `ApplicationExitInfo reason=4 (APP CRASH)` PID를 함께 집계한다.
- `launcher_loop_observed`는 같은 관찰 창에서 BUG27084 signature가 2건 이상이거나 exact launcher APP CRASH exit가 2건 이상일 때만 true다. 단일 crash 후 회복은 crash 재현으로만 계수한다.
- exact old widget ID의 phase-new `Widget provider not found for id=<id>` delta를 별도 집계한다. 0이면 stale-record evidence는 계속 `INFERRED_ONLY`이며, fixed 판정의 직접 근거로 승격하지 않는다.
- known-bad와 fixed build는 provider, lifecycle, 관찰 창, 독립 fixture 수를 맞춘다. known-bad 1/1 대 fixed 0/1은 수정 효과의 근거로 사용하지 않는다.
