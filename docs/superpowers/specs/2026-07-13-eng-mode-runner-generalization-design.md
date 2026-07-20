# Engineer-Mode 런너 범용화 설계

날짜: 2026-07-13  
상태: host 구현·검증 완료. 사용자 승인으로 CLAUDE.md `applied` 반영 완료; 단말 runtime smoke는 잔여 게이트.

## 1. 목적

`ODIN2 - Engineer IMS/run_complex_0617.py`의 검증된 런타임 패턴을 앱 전용
상수와 분리해 재사용 가능한 `scripts/eng_mode_runner.py`로 제공한다.

- preflight + wrong-device 가드
- caseset 앱 1회 기동 batch
- capture 상태-게이트 후 qmdl/main pull
- adb 없는 `plan` dry-run

기존 파일은 2026-06-17 실기 결과가 참조하는 frozen evidence로 유지한다.

## 2. 경계

이번 슬라이스는 무단말이다. host-TDD와 dry-run 성공은 `runtime PASS`가 아니다.
다음 ODIN2 연결 창에서 `preflight`와 대표 `caseset` 1회 smoke를 통과한 뒤에만
단말 거동 보존을 주장한다.

비목표:

- TeleEngineer 1.0.6 V2 navigation/profile 추가
- composite-write 비결정성 수정
- call-site 안전 가드 또는 helper 통합
- applicability 매트릭스 재판정
- frozen `run_complex_0617.py`와 `eng_nav.py` 수정

## 3. 구조

### `scripts/eng_mode_profiles.py`

실행 코드가 없는 데이터 모듈이다.

- `PROFILES`: package/activity/model/tab/resource-id/라벨/popup/pull/hook/swipe/evidence 경로
- `CASESETS`: `{profile: {tcid: (tab, [(item, kind, value), ...])}}`

caseset 항목은 dict로 바꾸지 않는다. `CMB_IMS_SESSION`과 `CMB_IMS_VIDEO`의
`Traffic Port` 중복 행 순서가 실행 의미를 가진다.

### `scripts/eng_mode_runner.py`

세 층으로 나눈다.

1. PURE: XML locator, adb 출력 파서, 상태 술어, profile/caseset 검증, plan 렌더
2. DEVICE: frozen 런너의 command/session 동작을 profile lookup으로 lift
3. CLI: 기존 명령 + `plan`, `--profile`, `--out-root`, `--run-label`

`plan`과 `--help`는 device resolution보다 먼저 분기한다. import와 plan에서
`subprocess.run` 및 adb 호출은 0이어야 한다. device 명령만 dispatch 시 serial을
한 번 선택하며, `_device_ok`/preflight의 fresh connected-device 관찰은 유지한다.

## 4. 출력 경로

기존 `__file__` 상대 `ODIN2 - Engineer IMS/log/RUN_0617_complex`를 다음으로
명시화한다.

```text
<repo-root>/<profile.evidence_dir>/<run-label>/<tcid>/...
```

- 기본 evidence root: `ODIN2 - Engineer IMS/log`
- 기본 run label: `RUN_YYYYMMDD`
- 상대 `--out-root`: repo root 기준
- 절대 `--out-root`: 그대로 사용
- run label은 단일 path component만 허용

이 규칙은 스크립트를 `scripts/`로 옮겨도 증거가 앱 폴더에 누적되게 한다.

## 5. 거동 보존 계약

다음 차이는 중복이 아니라 frozen 런너의 call-site 계약이다.

| 경로 | 보존 내용 |
|---|---|
| `cmd_write` / `_sess_text` | DEL 16회. command만 mismatch abort, session만 IME dismiss |
| `cmd_mfield` / `_sess_mfield` | DEL 10회, `%s` 변환 없음, IME dismiss 유지 |
| button pause | write/read별 1.4/1.3/1.2 및 1.2/1.1/1.0 차이 유지 |
| radio locator | command exact→substring; session `rb_` 값은 rid-only |
| mfield locator | 둘 다 field text containment. command rid endswith+early break; session rid endswith+independent next |
| logging | 항목별 logcat clear 위치, hook 파일 truncation 길이 유지 |
| failure | `cmd_radio` Write 미발견 시 기존 crash 가능성 등 가드 무단 추가 금지 |

프로파일과 실행 코드가 분리되더라도 위 의미를 통합하거나 정리하지 않는다.

## 6. 검증

host-only acceptance:

1. import 중 subprocess/adb 호출 0
2. 순수 locator·parser·predicate·validator 테스트 GREEN
3. V1 profile이 frozen literal과 일치
4. 출하 caseset 전건 strict validation 통과
5. `CMB_IMS_SESSION`의 `Traffic Port` 2행 순서 보존
6. call-site DEL/IME/pause/mismatch 차이 정적 계약 통과
7. `plan CMB_IMS_SESSION`이 adb 없이 성공
8. unknown TCID가 명확한 non-zero 오류
9. `py_compile` 및 전체 `tests/` 회귀 0

device acceptance는 후속이다:

1. target serial/model/app preflight
2. 대표 caseset 1회
3. frozen 런너와 Way1/Way2 artifact 위치·형식 비교
4. capture gate + pull smoke

## 7. 문서·거버넌스

`RUNTIME_PLAYBOOK.md` §3은 새 runner를 host-verified 기본 경로로 안내하고 frozen
파일을 실기 근거로 병기한다. `CLAUDE.md` §5.3/§4.2/§8.2는 구현·host 검증 결과와
diff를 제시한 뒤 사용자 승인으로 `applied` 반영했다. 이 승격은 도구·운영 규칙의
반영 상태이며, 범용 경로의 단말 runtime smoke 완료를 뜻하지 않는다.

## 8. 후속 강화 후보

frozen 동작에서 이월한 short-value mismatch 완화, missing control crash, 잘린 XML
ParseError는 device smoke 이후 별도 슬라이스에서 다룬다. 다일 캠페인은 자정 경계의
날짜 기본값에 의존하지 말고 고정 `--run-label`을 명시한다.
