# CODEX 지시문 — C03 QPN 다음 슬라이스 (2026-08-27)

**역할**: Codex = 구현·실행 / Claude = 설계 lock·독립 재검증 / 사용자 = 승인 게이트.
**규칙 source**: tc-runner root `AGENTS.md` 전 섹션 (특히 §2.1 승인 게이트 · §2.2 보고 어휘 · §7 commit 정책). 본 지시문은 AGENTS.md 를 보충하며, 충돌 시 AGENTS.md 가 우선.

**승인 상태**:
- **T1 (host-only)** — 사용자가 본 지시문을 Codex 에 전달한 시점 = T1 착수 승인.
- **T2 (F0 device 2-run)** — **별도 명시 승인 필요.** 사용자가 "2-run 실행 승인" 을 말하기 전 착수 금지.

---

## 0. T0 — 전제 게이트 (착수 전 전부 확인, 하나라도 FAIL = STOP + 보고)

1. **baseline commit 확인** — 아래가 commit 됐는지 `git status --short` 로 확인. 미커밋 = 착수 금지 (사용자 batch commit 대기):
   - thor2j (`C:\Users\momen\Projects\thor2j-tc-appium`): `runner/altbasic_c03.py` · `runner/altbasic_c03_driver.py` · `tests/test_altbasic_c03.py` (D1 슬라이스, 280 insertions)
   - tc-runner: `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md` (M) · `THOR2 - ALT Basic TC Audit/RUNSHEET_C03_QPN_LONGTAP_2026-08-21.md` (신규) · `HANDOFF_2026-08-27_CODEX_C03_QPN_DIRECTIVE.md` (신규)
2. **다른-writer 파일 접촉 금지** — thor2j 에 선존 무관 M 6 이 있다. 아래 6 파일은 읽기 외 **편집·stage 절대 금지**:
   `docs/annotation_candidate_dossier_2026-07-06.md` · `docs/recovery_honesty.md` · `testcases/focusrule/focusrule_tc_catalog.yaml` · `testcases/focusrule/tc_profiles_index.yaml` · `tests/test_recovery_feasibility_audit.py` · `tests/test_tc_quality_audit.py`
3. **5-suite GREEN 기준선**:
   `python -m pytest tests/test_altbasic_c01_driver.py tests/test_altbasic_c02.py tests/test_altbasic_c03.py tests/test_altbasic_c11.py tests/test_altbasic_narrow.py`
   → 기준선 **200 passed** (2026-08-21 D1 반영 시점). 미달 = STOP.
4. **dry-run 등가**: `python runner/altbasic_c03_driver.py --dry-run` → `drivable=34 registry=10`. 불일치 = STOP.

## 1. 문서 계약 (읽기 순서 — 전부 tc-runner 쪽)

1. `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md` — §2 조건형 anchor(고정 시퀀스 금지) · §5 안전 · §10(145 채널 조사) · §11(registry 재구조화·D1)
2. `THOR2 - ALT Basic TC Audit/RUNSHEET_C03_QPN_LONGTAP_2026-08-21.md` — §7 실행 절차 · §8 중단 조건
3. `THOR2 - ALT Basic TC Audit/RUNSHEET_C03_QPN_DISCOVERY_2026-08-20.md` §0 — 단말 정체 게이트 (F0 `B06201249E0002F0` 단독)

판정 source = `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`. **설계 문서와 충돌 시 ledger 가 사실이다.**

## 2. T1 — host-only: `uiautomator events` bounded 판별 관찰기 (설계 §10.3)

**목적**: 145 의 `could not get idle state` 가 **영구**(주기 갱신 뷰)인지 **일시**(로딩)인지 판별할 관찰 도구. 판별 결과에 따라 후속이 정반대(§10.3 표)이므로, 판별 전에 채널(Appium 등)을 고르지 않는다.

**요구 사항**:
- 위치: thor2j `runner/` — 별도 모듈 권장 (예: `runner/altbasic_c03_idle_probe.py`). driver 본체(`altbasic_c03_driver.py`) 회귀 변경 최소화.
- 기능: `adb shell uiautomator events` 를 **bounded 시간**(기본 10s, 인자화) 읽고 종료 → 이벤트 타임스탬프 파싱 → digest 반환:
  - 총 이벤트 수 / inter-event interval 분포(최소·최대·중앙값) / 마지막 이벤트 이후 경과
  - 출력은 위 raw digest 로 한정. 영구/일시 후보 분류와 후속 채널 결정은 출력 금지 — **판정은 사용자·Claude 영역**.
- fail-closed: adb 실패·파싱 불가 = 오류 종료(비 0 exit). **0 이벤트 = "관찰 무이벤트"로 오류와 구분** 표기.
- **TDD 선행**: 합성 이벤트 스트림 fixture 단위 테스트 먼저. **T1 구간 device 호출 0회** (실 관찰은 T2 동반 1건).
- 비파괴 원칙: 관찰기는 읽기 전용 — 어떤 input 주입도 하지 않는다.

**T1 완료 보고**: 신규 테스트 목록 + passed 수 / 5-suite 총계 / dry-run `34/10` 무변화 / device 호출 0회 확인.

## 3. T2 — F0 device 2-run (사용자 명시 승인 후에만)

**범위**: drivable 34 전건 run1/run2 (`--run 1` / `--run 2`, 독립). D1 3건(026 · 053 · 056)은 RUNSHEET §7 절차를 따르되, `mCurrentFocus` 는 보고서 기록만 하고 gate 판정·driver backfill 에 쓰지 않는다 (`--only ALTBASIC_QPN_026,ALTBASIC_QPN_053,ALTBASIC_QPN_056` 부분 실행 가능).

**게이트 순서**:
1. 단말 정체 게이트 — F0 `B06201249E0002F0` **단독 연결**, `adb devices` serial 일치. 불일치 = STOP (wrong-device).
2. `--dry-run` 재확인 (`34/10`).
3. 세션 pre-snapshot — 대상 state 축 + `sysui_qs_tiles`.
4. run1 → 결과 채록 → run2. **run1 결과로 run2 절차를 바꾸지 않는다** (독립성).
5. D1 3건은 `state_unchanged(axis)` 가 **최우선 gate**. FAIL = `runtime mutation FAIL` → **전체 run 즉시 중단** (개별 FAIL 격하 금지). 재실행 전 원인 규명 필수.
6. 동반 1건 — 145 목적지 도달 후 T1 관찰기 실행(비파괴), digest 를 evidence 로 저장.

**중단 조건 (RUNSHEET §8 전부 승계, 해제 금지)**:
- 동일 tc 입력 3회째 반복 금지
- 예상 외 화면 도달 시 임의 복구 입력 금지 — BACK 1회 후 STOP, 상태 채록
- `FORBIDDEN_KEYCODES = {134}` (SOS). 전원/재시작/긴급전화/발신/삭제 경로 금지
- `hotspot`/`Tether state:` 축은 "정확히 예상 행수" 강제 — F0 포맷이 AT-M150 실측과 다르면 STOP + 채록 (추측 정규화 금지)

**evidence**: driver 의 기존 evidence 출력 관례를 그대로 승계. 신규 경로가 필요하면 임의 신설하지 말고 보고 후 결정. `LITERAL_PENDING` 은 **FAIL 아님** — 목적지 dump 를 evidence 로 남긴다.

**activity gate backfill 금지**: D1 3건은 discovery `NOT_EXECUTED` 라 실측 activity 가 없다. 첫 run 에서 관찰된 activity 는 **보고서에 기록만** 하고 driver 에 backfill 하지 않는다 — backfill 은 사용자 승인 영역 (RUNSHEET §11).

## 4. 금지 (전 구간 공통)

- **commit / push 금지** — 사용자 명시 승인 전. broad add (`git add .` / `-A` / 디렉토리) 영구 금지. stage 는 명시 path 만.
- 원문 편집 금지: `stage1_review_mapping_batch10/ALTBASIC_QPN_*_canonical.yaml`
- **미승인 트랙 착수 금지**: D2 (타일 추가 mutation) · D2-a (타일 short OK 개별 예외) · 102 비-scalar guard 설계 · 145 Appium 채널 채택
- 066 · 102 · 157 · 158 · 159 · 165 = **입력 0회 유지**. registry 10건 = device 무접촉.
- 하드코딩 좌표 금지 — clickable **exact-one** 계약 유지 (0개/2개 이상/파싱 실패 = fail-closed)
- 1회 관찰 시퀀스를 driver 상수로 승격 금지 (설계 §2)

## 5. 보고 형식

- PASS 어휘 4종 한정 (AGENTS.md §2.2): `validate PASS` / `runtime PASS` / `manual evidence observed` / `BUG-GAP observed`. 단독 `PASS` 금지. scope 밖 관찰은 `NOTE`.
- T2 완료 보고: run1/run2 per-tc 결과표 · `TWO_RUN_GREEN` 목록 · D1 3건 state pre/post 값 · 145 관찰 digest 요약 · 중단 발생 시 §8 채록 원문.
- 측정과 추론 구분 표기 (`[측정]` / `[추론]`).
