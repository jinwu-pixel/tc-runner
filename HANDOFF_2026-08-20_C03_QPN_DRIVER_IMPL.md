# HANDOFF — C03/QPN driver slice v1 host-TDD 구현 지시 (Codex 실행용, 2026-08-20)

**역할**: Codex = 구현 / Claude = 설계 잠금·독립 재검증 / 사용자 = 승인 게이트.
**본 작업은 host-only. 단말 접촉 0 · git stage/commit/push 0.**

## 0. 권위 문서 (이 순서로 읽을 것)

1. **설계(유일 권위)**: `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md`
2. 근거 데이터: `THOR2 - ALT Basic TC Audit/DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`(44행, 1:1 판정 source)
   + `DISCOVERY_C03_QPN_SUMMARY_2026-08-20.md`
3. 선례 코드(컨벤션 승계 대상): `thor2j-tc-appium/runner/altbasic_c02.py` · `altbasic_c02_driver.py`
   · `tests/test_altbasic_c02.py`
4. 카탈로그 사실: `THOR2 - ALT Basic TC Audit/catalog/f0_literal_catalog.csv` `KEY-001~011` · `STR-012~014`

설계와 ledger 가 충돌하면 **ledger 가 사실, 설계가 의도**다. 충돌 발견 시 임의 조정하지 말고
보고서에 명시하고 **설계 쪽을 따르되 불일치를 기록**한다.

## 1. 산출물 (thor2j-tc-appium, 신규 3파일 + 기존 2파일 최소 수정)

| 파일 | 내용 |
|---|---|
| `runner/altbasic_c03.py` (신규) | **순수**(adb/appium import 0): 44 tc_id 고정 분류(설계 §1), 격자 지도 상수(§3), `build_qpn_plan(tc_id)`, `ensure_focus_at()` 계획 생성(§2), exact-one `tap_target`, 신규 verify 평가(`state_unchanged`·`qs_tiles_unchanged`·`settle_gate`) |
| `runner/altbasic_c03_driver.py` (신규) | adb-only executor. C02 driver 구조 승계(UDID 핀·wrong-device abort·evidence·`--dry-run`/`--run`/`--only`). **종료 시 자기 remote temp 정리 필수** |
| `tests/test_altbasic_c03.py` (신규) | 설계 §6 전수 커버, synthetic fixture only |
| `runner/altbasic_c02.py` (수정 최소) | `_assert_swipe_scope` 의 허용 disposition 을 QPN 군까지 확장. **그 외 C02 동작 변경 금지** |
| `tests/test_altbasic_c02.py` (수정 최소) | 위 확장에 따른 기존 assert 조정만 |

**공유 primitive 재사용 원칙**: `qs_stage`·`focused_desc`·`desc_present`·`text_present`·
`focused_node`·`FORBIDDEN_KEYCODES`·`_assert_no_ok`·`_assert_no_forbidden` 은 `altbasic_c02` 에서
**import 해 재사용**한다(fork 금지). C03 는 QPN 고유분만 정의한다.

## 2. 반드시 지킬 계약 (위반 = 구현 반려)

1. **조건형 anchor**: `ensure_focus_at()` 는 현재 focus 를 먼저 읽고 **이미 target 이면 키 0회**.
   unconditional key 시퀀스로 origin 을 가정하는 코드는 금지(설계 §2 — discovery 실측 함정).
2. **`QPN_POPUP_EXPOSE` OK 계약**: 011/141/043/044는 OK(23) 부재를 pure 단계에서 assert.
   175만 `pm_lite` focus verifier 뒤 짧은 OK 정확히 1회 허용하고, 팝업 내부 OK는 0회로 assert.
3. **타일 위 short OK 금지**. `QPN_TILE_LONGOK` 은 `--longpress 23` 만 사용.
4. **`state_unchanged`**: `QPN_TILE_LONGOK` 5건 각각에 대해 해당 설정 축 pre/post exact 비교를
   plan 에 포함. 축 선택은 ledger 의 `state_diff` 열 참조(발명 금지). Wi-Fi는 전체 dumpsys가 아닌
   `Wi-Fi is ...` 단일 상태행만 정규화해 비교한다.
5. **`qs_tiles_unchanged`**: 002·008·167·168 은 `sysui_qs_tiles` exact diff 0 postcondition 필수.
6. **`settle_gate`**: 화면 터치 잠금 타일은 최대 3.0초/0.5초 간격 조건형 re-dump로 gate.
   조건 충족 즉시 종료하며 **선행 고정 sleep 금지**.
7. **registry 13 은 `build_qpn_plan` 자체가 fail-closed 예외** — 무접촉 보장.
8. `FORBIDDEN_KEYCODES={134}` 전 plan 유지.
9. **`tap_target`**: 002·004·008·010·011·043·044와 043·044의 취소는 현재 dump에서
   selector 일치 clickable node가 정확히 1개일 때만 bounds 중심 tap. naked hard-coded 좌표 금지.
10. **full page2 복원 경로**: discovery 실행 이력의 target-gated 경로를 사용한다.
    무초점→DOWN×4로 비행기 모드, RIGHT×2로 위치(page2); 위치→RIGHT 터치 잠금,
    위치→DOWN 자동 회전→DOWN 데이터 절약, 터치 잠금→DOWN 절전→DOWN 방해 금지.
    무조건 시퀀스 재생은 금지하고 각 키 뒤 dump 기반 `ensure_focus_at()` 재계산을 적용한다.

## 3. TDD 절차

1. `tests/test_altbasic_c03.py` 먼저 작성 → **RED 확인**(실패 출력 기록)
2. 구현 → GREEN
3. 회귀: `cd thor2j-tc-appium && C:\Users\momen\Projects\tc-runner\venv\Scripts\python.exe -m pytest tests/test_altbasic_c01_driver.py tests/test_altbasic_c02.py tests/test_altbasic_c03.py tests/test_altbasic_c11.py tests/test_altbasic_narrow.py -q -p no:cacheprovider`
   → **C02 137 baseline 대비 회귀 0** 확인(감소 시 원인 규명 후 보고)
4. `--dry-run` 실행(단말 0): 44행 분류 출력 = 설계 §1 (drivable 31 / registry 13) 정확 일치 확인

## 4. 금지

- 단말 호출 0(adb 실행 금지 — 코드 작성만)
- canonical yaml · manifest · tc-runner 파일 **일절 수정 금지**
- git add/commit/push 0
- 지정 5파일 외 생성·수정 0
- ledger/summary 에 없는 사실의 발명(격자·literal·좌표) 금지

## 5. 보고 (구조화 반환)

1. 생성/수정 파일 경로 + 라인 수
2. RED 증거 → GREEN(신규 테스트 수 + 회귀 총계, C02 137 대비 증감)
3. `--dry-run` 44행 분류 출력 전문
4. 설계 §1 과의 일치 여부(drivable 31 / registry 13)
5. 설계 ↔ ledger 불일치 발견 시 목록
6. 스펙 이탈 여부(없으면 "스펙 이탈 0")
