# RUNSHEET — C03 QPN 터치 롱탭 mutation-risk (승인 요청, 2026-08-21)

> **상태 (2026-08-21 갱신)**
> - **D1 = 026 · 053 · 056 한정 승인됨** → 호스트 구현 완료 (설계 §11.6, 5-suite 200 passed).
>   **device 실행은 0회** — F0 2-run 은 여전히 별도 게이트다.
> - **D2 · D2-a = 미승인.** 066 · 102 · 157 · 158 · 159 · 165 는 입력 0회 유지.
> - 승인 항목 원문은 §9. 미승인 항목에 대해 §7 을 실행하지 않는다.

**역할**: Claude = 계획·근거 / 사용자 = 승인 게이트 / 실행자 = 승인 후 지정.

- 상위 설계: `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md` §5(안전)·§10·§11
- 판정 source: `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv` (설계와 충돌 시 ledger 가 사실)
- 원문: `stage1_review_mapping_batch10/ALTBASIC_QPN_{026,053,056,066,102}_canonical.yaml` — **편집 금지**
- 단말 정체 게이트: `RUNSHEET_C03_QPN_DISCOVERY_2026-08-20.md` §0 을 그대로 승계 (F0 `B06201249E0002F0` 단독)

## 0. 왜 별도 승인인가

discovery 는 5건 모두 `input_injection_status = LONGTAP_INJECTION_UNRESOLVED`,
`safety_status = PENDING_MUTATION_RISK_APPROVAL` 로 **입력 0회** 종료했다.
근거는 §5 "타일 위 short OK 전역 금지" 와 같다 — **롱탭이 short 로 오해석되면 타일이 토글된다.**
타일 롱탭은 설정 화면 이동(비파괴)이지만, 오해석 1회가 곧 단말 상태 변경이다.

## 1. 대상 5건 — 원문이 입력 축을 구분한다 (측정)

| tc | 원문 `raw_text` | 목적지 (`expected_result_raw`) | 하드키 twin | D1 거부 시 커버리지 |
|---|---|---|---|---|
| 026 | `퀵 패널 > 모바일 데이터 Long Tap` | 모바일 데이터 설정 | 없음 | **목적지 커버 0** |
| 053 | `퀵 패널 > 자동 회전 Long 탭` | 화면 자동 회전 메뉴 | **149** (drivable) | 목적지는 149 가 커버 — 터치 입력 축만 손실 |
| 056 | `퀵 패널 > 절전 모드 아이콘 Long 탭` | 절전 모드 메뉴 | 없음 | **목적지 커버 0** |
| 066 | `퀵 패널 > 핫스팟 아이콘 Long 탭` | Wi-Fi 핫스팟 설정 화면 | 없음 | **목적지 커버 0** |
| 102 | `퀵 패널 > 집중 모드 아이콘 Long 탭` | 집중 모드 설정 메뉴 | 없음 | **목적지 커버 0** |

대조군 — TILE_LONGOK 5건(drivable)의 원문은 **전부** `<타일> focus > Press OK 길게 입력` 형태다
(133/146/149/153/155). 본 5건은 `아이콘 Long 탭` 으로 focus 언급이 없다.
→ **원문이 하드키와 터치를 구분한다.** 하드키로 대체하면 053 은 149 의 중복이 되고
나머지 4건은 원문과 다른 시험이 된다. 따라서 입력 축 대체는 해법이 아니다.

## 2. mutation 위험 — tc 별로 등급이 다르다

오해석 경로: 터치 지속이 롱프레스 임계(`ViewConfiguration` 기본 500ms) 미달 → tap 처리 → 타일 토글.

| tc | 오해석 시 실제 발생 | 되돌림 | 등급 |
|---|---|---|---|
| 026 | 모바일 데이터 ON/OFF — **데이터 세션 끊김** | 재토글 | 중 |
| 053 | 화면 자동 회전 전환 | 재토글 | 저 |
| 056 | 절전 모드 진입/해제 — 백그라운드·성능 제약 변화 | 재토글 | 저 |
| 066 | **핫스팟 기동** — SSID 무선 방송·테더링 개시 (**외부 가시**) | 재토글, 기동 이력 잔존 | **고** |
| 102 | 집중 모드 세션 시작 — 앱 차단 | **검출 불가** (§6 scalar 부재) | **고** |

066 은 외부에서 관측 가능한 상태를 만들고, 102 는 발생 자체를 adb 로 검출할 수 없다.
나머지 3건과 같은 등급으로 묶어 승인하지 않는다.

## 3. 주입 기전 — 선택과 근거

| 후보 | 판정 | 근거 |
|---|---|---|
| `input swipe <x> <y> <x> <y> <duration≥1000>` | **채택** | 단일 호출 원자적·self-terminating. 임계 500ms 대비 2배 여유 |
| `input motionevent DOWN` + 지연 + `UP` | 거부 | UP 호출 실패 시 **터치 DOWN 고착**. host 왕복 지연도 비결정론 |
| `input keyevent --longpress 23` | 거부 | 원문 입력 축 변경 (§1) |
| `sendevent` | 불가 | 권한 거부 (KEY-011) |

[측정: AT-M150, 명령 표면 확인 용도] `input` 이 `swipe`·`motionevent`·`draganddrop` 를 모두 지원함을 확인.

**좌표 계약**은 §5 를 그대로 승계한다 — 현재 dump 에서 대상 타일 clickable 노드가 **정확히 1개**일
때만 bounds 중심을 쓴다. 0개 / 2개 이상 / 파싱 실패 = fail-closed. **하드코딩 좌표 금지.**

## 4. stage — 타일 가용성 기준 (§3 격자 지도)

원문의 "퀵 패널" 표현을 stage 근거로 쓰지 않는다. active QS 12 배치가 기준이다.

| tc | 대상 타일 | stage |
|---|---|---|
| 026 | 모바일 데이터 | 1단(split) 가용 |
| 053 | 화면 자동 회전 | 2단 page2 |
| 056 | 절전 모드 | 2단 page2 |
| 066 · 102 | 핫스팟 · 집중 모드 | **active QS 부재** — §5 |

page2 는 transient 속성이 있으므로 `settle_gate` 를 선행한다(§4 transient 대응).

## 5. 이중 게이트 — D1 만으로 해소되지 않는 2건

066 · 102 는 대상 타일이 **active QS 에 없고 edit candidate 에만 존재**한다
(ledger `divergence` = `입력 미확정 + active precondition 불일치`, 설계 §11.1).
→ **D1 만 승인되면 실행 가능한 것은 026 · 053 · 056 세 건뿐이다.**
066 · 102 는 D2(타일 추가 mutation) 가 선행돼야 하고, 102 는 그 뒤에도 §6 때문에 남는다.

## 6. state 축 — 2 확보 / 1 부재

`state_unchanged` 는 `read_state(dev, axis)` 가 exact 비교 문자열을 반환하는 계약이다.

| tc | axis | 채널 | 상태 |
|---|---|---|---|
| 026 | `mobile_data` | `settings get global mobile_data` | 기존 축 |
| 053 | `accelerometer_rotation` | `settings get system accelerometer_rotation` | 기존 축 |
| 056 | `low_power` | `settings get global low_power` | **신규 — 확보** (scalar) |
| 066 | `hotspot` | `dumpsys tethering` → `Tether state:` 블록 정규화 | **신규 — 확보** |
| 102 | — | global/secure 에 focus-mode scalar **부재** | **부재** |

[측정: AT-M150, 채널 표면 확인 용도] `low_power` scalar 응답 확인.
`Tether state:` 는 iface 당 1행(`wlan0 - AvailableState - lastError = 0`)으로 exact 비교 가능.
**F0 포맷 동일 여부는 실행 시 확인 대상**이며, iface 집합 변동이 위양성을 만들 수 있으므로
`wifi` 축과 같이 "정확히 예상 행수" 를 강제한다.

**102 는 guard 를 만들 수 없다.** 대체 guard 를 추측으로 만들지 않는다 — §10 참조.

## 7. 실행 절차 (D1 승인 시, 026 · 053 · 056 한정)

승계 게이트: 단말 정체 게이트 → 세션 pre-snapshot(대상 축 + `sysui_qs_tiles`) → 아래를 tc 별 1회.

1. 퀵패널 진입 (§3 진입 시퀀스). 053 · 056 은 2단 page2 + `settle_gate`
2. 대상 타일 clickable 노드 **exact-one** 확인 → bounds 중심 `(cx, cy)` 산출. 불일치 = STOP
3. axis pre-snapshot (`read_state`)
4. `input swipe cx cy cx cy 1200`
5. **`state_unchanged(axis)`** — 최우선 gate (§4.1 판별력 순서)
6. `qs_stage == none` — 퀵패널 이탈
7. `mCurrentFocus` 관찰 — **보고서 기록만**, gate 판정·driver backfill 금지
8. `literal_probe(<원문 literal>)` — 미확보 = `LITERAL_PENDING` (**FAIL 아님**, 목적지 dump 를 evidence 로 남김)
9. BACK 복귀 → `qs_tiles` post 확인

`--dry-run` 등가 확인을 device 실행 전에 선행한다.

## 8. 중단 조건 (해제 금지)

- `state_unchanged` FAIL = `runtime mutation FAIL` → **전체 run 즉시 중단**. 개별 FAIL 로 격하하지 않는다. 재실행 전 원인 규명 필수
- 동일 tc 입력 **3회째 반복 금지** (discovery `세 번째 입력 반복 금지` 승계)
- 예상 외 화면 도달 시 임의 복구 입력 금지 — BACK 1회 후 STOP, 상태 채록
- `FORBIDDEN_KEYCODES = {134}` (SOS) 유지. 전원/재시작/긴급전화/발신/삭제 경로 금지

## 9. 승인 요청 항목

| # | 요청 | 해소 대상 | 위험 요약 |
|---|---|---|---|
| **D1** | 터치 롱탭 입력(`input swipe` 동일좌표 1200ms) 실행 승인 — **승인됨 2026-08-21 (026·053·056 한정)** | 026 · 053 · 056 **실행 가능** / 066 · 102 부분 | 오해석 시 토글 — 3건 모두 재토글 복원 가능, `state_unchanged` 로 즉시 포착 |
| **D2** | `sysui_qs_tiles` 타일 추가 mutation + 복원 승인 | 066 · 102 · 157 / 158 · 159 · 165 부분 | active QS 구성 변경. 복원은 pre-snapshot exact 복귀 |
| **D2-a** | (D2 후속) 타일 short OK 전역 금지 개별 예외 | 158 · 159 · 165 | launch 형 여부 **실측 근거 없음** — 예외 승인 전 확인 필요 |

**승인 경위** — D1 은 등급 분리 승인이 가능하다 — 026 · 053 · 056(저·중)만 승인하고 066 · 102(고)는 보류해도
D1 의 실행 범위(§5 에 따라 어차피 3건)는 동일하다. 권고 = **026 · 053 · 056 한정 D1 승인**,
D2 는 별건으로 판단. **사용자가 이 권고대로 승인했다 (2026-08-21).**

## 10. 승인해도 남는 것 (정직 표기)

- **102** — scalar guard 부재. D1 · D2 가 모두 승인돼도 `registry` 유지가 기본값이며,
  비-scalar guard 를 별도 설계하지 않는 한 승격 대상이 아니다
- **158 · 159 · 165** — D2 만으로는 실행 불가. D2-a 가 추가로 필요하고, 그 전에 launch 형 실측이 선행
- **145** — 본 문서 범위 밖. 계층 채널 결정 (설계 §10)
- **122 · 012 · 163** — 종결 사유 (adb 재현 불가 / 실행 금지). 결정 대상 아님

## 11. D1 구현 반영 (2026-08-21)

승인 직후 호스트 측만 구현했다. **단말 입력은 여전히 0회다.**

| 변경 | 내용 |
|---|---|
| disposition | `QPN_TILE_TOUCH_LONGTAP` 신설 — 026 · 053 · 056. drivable 31→34 / registry 13→10 |
| plan step | `touch_longpress` — `desc_prefix` selector + `duration_ms ≥ 1000` 강제 |
| selector | `find_clickable_bounds` 에 `desc_prefix` 추가 (타일 desc 상태 suffix 대응) |
| state 축 | `low_power` 추가 (`settings get global low_power`) |
| 계약 assert | 본 disposition plan 에 **하드키 OK 존재 시 build 거부** (입력 축 보존) |
| activity gate | **두지 않음** — discovery `NOT_EXECUTED` 라 실측 activity 부재. 첫 run 후 backfill = 사용자 승인 영역 |

**검증**: 5-suite **200 passed** · dry-run `drivable=34 registry=10` · device 실행 0회.

§7 절차는 F0 연결 시 그대로 유효하다. `--only ALTBASIC_QPN_026,ALTBASIC_QPN_053,ALTBASIC_QPN_056`
로 부분 실행이 가능하다.
