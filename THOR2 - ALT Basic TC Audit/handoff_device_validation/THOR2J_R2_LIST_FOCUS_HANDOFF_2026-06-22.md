# THOR2J HANDOFF — ALT Basic R2 list-aware focus 검증 (2026-06-22)

**무단말 작성 (정적). 실 F0 실행은 별도 승인 후.** commit/push/단말 호출 금지 상태에서 작성된 계약.

F0 cycle1(`RESULT_RECOVERY_BATCH11_2026-06-17.md`)에서 MSG_069/070/071/072/077 이 **R1 위음성**으로 NOT_GREEN. 원인: 차단/스팸·설정·앱메뉴 같은 list/scroll 화면은 컨테이너(`android:id/list` 등) 자체가 `focused=true` 이고 DPAD 시 그 노드가 불변 — 실제 이동은 자식의 `selected=true` 이동 + scroll 델타로 표현. 본 핸드오프는 그 위음성을 제거하는 **R2 list-aware 모델**과 대상 13건의 계약을 정의한다.

- **manifest (read-only)**: `VALIDATION_MANIFEST_R2_LIST_2026-06-22.csv` (**13건**, focus_model/model_confidence 컬럼 추가)
  - batch10 9: MSG_069/070/071/072/077, HDK_069, HDK_095, SST_009, CAL_335 (`stage1_review_mapping_batch10/`)
  - batch11 4: LCH_014, LCH_015, CLK_030, CLK_031 (`stage1_s2_salvage_batch11/`)
- **STAGE1 계약**: 각 yaml `audit_meta.verifier_contract.focus_model: list` + assert별 list-model `method`. (tc-runner side, transform `scratch/cycle2_list_focus_model_transform.py`로 적용 완료)
- **runner**: thor2j-tc-appium — **R2 모델 구현은 thor2j 영역(§2.5 cross-commit 금지)**. 본 문서는 계약·절차만 제공. device 세션 승인 시 작성.
- **핵심 신규**: R1(focused 노드 변경) → **R2(`has_selection_moved_from_baseline`: selected 자식 델타 ∨ scroll-index 델타, 컨테이너 focused 불변 정상)**. assert 어휘(PASS 조건)는 R1과 공유, 측정 전략만 분기.
- **KPI**: TWO_RUN_GREEN만 RUNNABLE_NOW 증가. STAGE1_DRAFT·DVR 미가산.

## 1. 단말 / 실행 규약

| 항목 | 계약 |
|---|---|
| 단말 | **F0 `B06201249E0002F0` 고정** (build RY07260601S, ko-KR). **B27 `B2700125BW000083` 미접촉** |
| run | 모든 TC **run1 / run2 독립 실행**. 상호 상태 비공유 |
| 승격 | **TWO_RUN_GREEN(run1=SINGLE_RUN_PASS ∧ run2=RUN2_PASS)만 RUNNABLE_NOW**. 단일 run PASS = 미승격 |
| 결과 어휘 | `SINGLE_RUN_PASS`/`RUN2_PASS` · `ENTRY_FAILED` · `VERIFIER_FAILED` · `CLEANUP_FAILED`(즉시 보고) · `DEVICE_FIT_SKIP`(FAIL 아님) · `MODEL_MISMATCH`(아래 §4 fallback) · `INFRA_FAILURE` |
| run 순서 | risk_rank 오름차순 (focus nav 먼저). nav flaky(더보기→차단·스팸 tap 등)는 재시도·보고 |

## 2. R2 list-aware 모델 스펙 (핵심)

list/scroll 컨테이너에서 focused 노드는 컨테이너로 **불변**이다. 이동 신호는 두 축:
1. **selected 자식 델타** — `selected="true"` 속성을 가진 자식 노드의 resource-id·text·bounds 변경.
2. **scroll-index 델타** — 리스트 first-visible-item index(또는 선택 row index)의 변경.

`has_selection_moved_from_baseline(pre, post)` = (selected 자식 변경) ∨ (scroll-index 변경). 컨테이너 focused 동일성은 판정에 **사용하지 않음**(불변이 정상).

| assert | 캡처 | PASS 조건 (list) |
|---|---|---|
| focus_move | 입력 전/후 selected 자식 + scroll index | selected 자식 또는 scroll index **변경** |
| focus_invariant | 입력 전/후 selected 자식 + scroll index | selected 자식·scroll index **동일(불변)** |
| focus_boundary_stop | 연속 입력 중 selected 자식 + scroll index 추적 | 끝단(최하단/최상단 자식) 도달 후 **불변(비루프)** |
| focus_retained | 이탈 전 selected 자식 채록 | back/취소 후 **동일 자식 selected 복귀** + 컨테이너/메뉴 부재 |

대상 assert 분포(13): focus_move 9 (MSG_069/070/071/072/077·HDK_069·LCH_014·CLK_030·CLK_031), focus_invariant 2 (HDK_095·SST_009), focus_boundary_stop 1 (CAL_335), focus_retained 1 (LCH_015).

## 3. 캡처 절차

1. dump = `uiautomator dump` 또는 Appium source.
2. **focused=true 노드 식별.** 그 노드가 list/scroll 컨테이너(`*ListView`·`*RecyclerView`·`*ScrollView`·`android:id/list` 등)면 R2 경로.
3. 컨테이너 하위에서 **`selected="true"` 자식**의 resource-id·text·bounds 추출 + **scroll-index**(first-visible 또는 선택 row) 기록.
4. 입력 전/후(또는 연속 입력 중) 위 쌍을 assert별로 대조.
5. run1에서 selector 미확정·`selected` 속성 부재 등은 §4 fallback 또는 `VERIFIER_FAILED` 정직 기록 (발명 금지).

## 4. fallback 계약 (오분류 자가보정)

list 태깅이 실제로는 node-focus일 수 있다(특히 `model_confidence: device_confirm`).

- R2 측정 우선. **selected 자식·scroll index 델타가 둘 다 부재**하지만 **focused 노드 자체가 변경**되면 → **R1(node) 모델로 폴백**하고 assert 판정. 즉 R2는 R1의 **superset** — 위음성 대신 자가보정.
- 폴백 발생 시 결과에 **양 축 모두 기록**(`selection_delta` + `focused_node_delta`) + `focus_model_effective: node` 표기. silent fail 금지.
- `model_confidence: device_confirm`(CLK_030/031) 은 run1에서 컨테이너 타입(탭 strip vs list)을 명시 확인 후 STAGE1 환류로 `list`/`node` 확정.

## 5. device_value backfill 포맷

run1 후 STAGE1 yaml `verifier_contract.device_value`(현 PENDING_F0)에 환류(별도 무단말 보정):
```
container_id:    <focused 컨테이너 resource-id>     # 불변
selected_child:  { resource_id, text, bounds }      # selected=true 자식
scroll_index:    <first-visible 또는 선택 row index>
focus_model_effective: list | node                  # fallback 발생 시 node
```

## 6. mutation 0 / 안전 (denylist — 항구)

- 전건 NAVIGATION_ONLY (DPAD 이동 + back/HOME). 선택/ENTER/실행/설정변경/항목 삭제·이동 **0**.
- LCH_014/015(앱 편집 메뉴): 반드시 **back/취소로 편집 모드 이탈** — 항목 조작·배치 변경 확정 금지.
- 실행 전/후 `pm list packages` pre/post diff 0. 종료 시 `io.appium.*` helper uninstall(잔존 0).
- 위험 tap denylist: `켜기`/`사용 설정`/`시작`/`전송`/`연결`/`확인`(영속)·`저장`·`삭제`·다이얼러 발신·`am start` 직접 기동 — batch11 §7 재사용.

## 7. redaction

- focus 검증은 **요소 id/bounds만 필요** — PII 텍스트 불요. dump의 focused/selected 노드 외 PII(차단번호·메시지·연락처)는 토큰화.
- MSG/Call sheet 계열(MSG_069~072·CAL_335)은 차단 목록 등 기존 PII 부수 채록 가능 → redaction gate 후 sidecar만, raw/png local-only.

## 8. §2.5 경계

- 본 문서 + STAGE1 yaml `focus_model` 필드 = **tc-runner side(계약)**.
- R2 측정 코드(`has_selection_moved_from_baseline`·dump 파서) = **thor2j-tc-appium side(구현)**. cross-commit 금지.

## 9. 산출 / 보고

- evidence: `thor2j-tc-appium/evidence/altbasic_r2_list_2026MMDD/run{1,2}/{tc_id}/` (xml+png, local-only)
- 결과 CSV: `evidence/.../results_run{1,2}.csv`
- 회수 리포트: tc-runner `RESULT_RECOVERY_R2_LIST_*.md` (RUNNABLE / fallback(node 확정) / NOT_GREEN 분리)
- device_value 확정분은 run1 후 STAGE1 yaml 환류(§5).

## 10. 정적 검증 (실행 전 통과)

runner syntax · manifest TC ID **13** 정합 · focus_model=list 13/13 · selected/scroll 캡처 + R1 fallback 절차 완비 · 위험 tap denylist 0 · reports/evidence local-only · **commit/push/단말 호출 금지**.
