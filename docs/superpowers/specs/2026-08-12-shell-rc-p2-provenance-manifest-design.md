# Shell-RC P2 — curated authoritative + tracked provenance manifest 설계

> **STATUS: IMPLEMENTED + TESTED + COMMITTED + PUSHED (2026-08-12) —
> scope record reconciled (2026-08-13)**
>
> 최초 구현 승인은 §3의 신규 4파일, 기존 tracked 편집 0이었다. 구현 중 기계
> 게이트가 inventory 오염과 Full-access Windows의 spawn-failure simulation 문제를
> 발견했고, 각 수정은 편집 전에 별도 사용자 amendment 승인을 받았다. 최종 유효
> 범위와 승인 순서는 §8.1에 기록한다. cleanup, campaign 재실행, CLAUDE.md 편집은
> P2 구현 commit 범위에 포함되지 않았다.
>
> 방향 승인 근거 대화: campaign evidence `f3e62fe3…` 독립 재검토 후 Claude 제안
> (a) source-first / (b) curated authoritative / (c) baseline 종결 중 (b) 채택.

**선행 문서:**
- 캠페인 directive: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md`
  (`RB-20260728-shellrc-p0p1`, 완주·frozen)
- base spec: `docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md`
  (**본 P2에서 무수정** — 캠페인 identity 보존을 위해 frozen 유지)
- contract amendment: `docs/superpowers/specs/2026-08-12-shell-rc-contract-amendment-design.md`

---

## 1. 측정 근거 (campaign evidence 요약)

공식 campaign 완주 evidence (모두 Claude 독립 재검증 완료):

- evidence: `reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/PROVENANCE_EVIDENCE.json`
  raw SHA-256 `f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a`
  (319,583 B, git blob `56ff430bc59e11ccc7e40e9092de446380ac8bc2`), HEAD `99ee58b1…`,
  capsule `bda43dc6…`
- verdict: `PROVENANCE_MISMATCH` exit 1 (label/code, requested_status=measured)
- P0: **12 tracked alias / 14 source selector / 15 blocker binding 완전 reconcile**,
  blocking 0 — 관계 복원은 성공
- P1: 문서 13/14 RECONCILED. blocking 17 =
  `TARGET_STEP_JOIN candidate_count=0` ×15 (전 binding, reconcile된 문서 포함)
  + `PRODUCER_RUNNABILITY_GAP` ×2 (SS_TC01 unresolved_params/runnable)

**해석 (P2 방향 결정 근거):**
- 갭이 범주적(15/15 전건 0)이다 — workbook prose에는 blocker step의 source가
  존재하지 않는다. curated YAML의 shell-RC blocker step 15개는 수작업 authoring.
- 따라서 exit 0(재생 성공)은 현 workbook/producer 상태에서 구조적으로 불가.
- (a) source-first는 Excel cell에 shell oracle(quoting/regex 민감 코드)을
  재저작하고 immutable producer·측정 계약 전부를 재설계하는 고비용 경로이며,
  실측된 저작 방향(YAML-first)과 역행 → 기각 (장래 요구 발생 시 본 manifest가
  그대로 사양 입력이 됨 = 무손실).
- (c) baseline 단독 종결은 14 selector/15 binding 지식을 게이트 없는 문서에
  가둬 drift 재발(D2 교훈 위반) → (b)의 부분집합으로 흡수.

## 2. 결정: (b) curated authoritative + tracked provenance manifest

- curated YAML(`exported_ss_call/`)이 **authoritative artifact**.
- workbook `tc_samples/TC_1.xlsx`는 human spec — 관계는 manifest가 고정.
- `export-mmi` producer는 **skeleton 생성기(비권위)**로 역할 확정.
  `PRODUCER_RUNNABILITY_GAP`은 이 규정 하에서 결함이 아니라 예상 동작.
- evidence `f3e62fe3…`는 공식 baseline으로 본 문서 §1에 등재 (재실행 불요).

## 3. 최초 승인 산출물 (신규 4파일)

| 산출물 | 경로 (권고) | 역할 |
|---|---|---|
| provenance manifest | `provenance/ss_call_shell_rc_manifest.yaml` | 12/14/15 관계의 단일 tracked source |
| pytest 게이트 | `tests/test_provenance_manifest.py` | manifest ↔ workbook ↔ curated YAML 정합 상시 검증 |
| seeding 도구 | `scripts/gen_provenance_manifest.py` | evidence JSON → manifest 결정론 생성 (유래 증명 + 재생성 경로) |
| 본 설계문 | `docs/superpowers/specs/2026-08-12-shell-rc-p2-provenance-manifest-design.md` | 계약 기록 + baseline 등재 |

**위치 근거**: `exported_ss_call/`은 corpus 카운트 pin(16 files,
`tests/test_anchor_corpus_audit.py:36`)이 있고, `tc_samples/`는 contract drift
ledger가 legacy corpus로 수집(`tests/test_contract_drift_ledger.py`) — 양쪽 모두
yaml 추가 시 기존 게이트 파손. 최초 설계에서는 신규 `provenance/` 루트 디렉터리를
어떤 collector도 글롭하지 않는다고 판단했으나, 구현 중
`scripts/canonical_shell_rc_inventory.py`가 모든 tracked YAML을 suffix로 수집한다는
사실을 회귀 게이트가 검출했다. 이 최초 단언은 superseded되며, 편집 전 승인된
inventory scope amendment로 `provenance/`를 TC inventory에서 제외했다(§8.1).

## 4. Manifest 스키마 v1

```yaml
schema_version: 1
subject: ss_call shell-rc blocker provenance
origin:
  directive_id: RB-20260728-shellrc-p0p1
  evidence_raw_sha256: f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a
  evidence_head: 99ee58b176718805b38e3e9ed916a19beaf4a00e
  verdict: PROVENANCE_MISMATCH   # baseline 등재 (재생 불가 = 측정 사실)
workbook:
  path: tc_samples/TC_1.xlsx
  raw_sha256: <seed 시 실측 pin>
mappings:            # 정확히 12개
  - yaml_path: exported_ss_call/SS_TC01_permission_denied.yaml
    yaml_tc_name: SS_TC01_permission_denied
    source_sheet: SS-TC 1
    source_selectors:          # 합계 정확히 14개
      - source_no: TC-01
        functionality_effective: <seed 시 evidence 값>
        workbook_physical_row: 2        # 관측 (selector 아님 — 계약 유지)
        source_content_hash: <loader 산출 row 필드의 canonical hash>
    blocker_bindings:          # 합계 정확히 15개
      - blocker_step_index: 10
        source_no: TC-01
        step_projection:
          action: verify_shell
          command: "<curated YAML step의 exact command>"
          expected: "<exact expected>"
```

- 12 mapping의 확정 내역(evidence 실측): SS_TC01(TC-01@r2, s10·s11) /
  SS_TC02(TC-02@r3, s11) / SS_TC03(TC-03@r4, s15) / SS_TC04(TC-04@r5, s18) /
  SS_TC05(TC-05A@r6·TC-05B@r7·TC-05C@r8, s9:TC-05A) / SS_TC06(TC-06@r9, s10·s11) /
  SS_TC07(TC-07@r10, s9) / SS_TC09(TC-09@r12, s20) / SS_TC0_P0(T/C-01@r2 [SS-TC 0], s15) /
  SS_TC10(TC-10@r13, s24) / SS_TC11(TC-11@r14, s20·s21) / SS_TC12(TC-12@r15, s19)
- `source_content_hash` canonical 정의: loader가 산출한 MMIRow의
  (no, feature_name, functionality, precondition, procedure, expected, priority)
  7필드를 `\x1f` 구분 결합한 UTF-8 bytes의 SHA-256. seeding 도구와 게이트가
  **같은 함수를 공유**한다 (§2.3 source-of-truth).

## 5. pytest 게이트 설계

**핵심 원칙: workbook 읽기는 production loader
`src.mmi_converter.row_loader.load_mmi_rows()`를 직접 import (read-only).**
campaign D2의 교훈 — 측정이 loader 실동작과 어긋나면 부정합이 늦게 터진다 —
에 따라 loader 의미론(헤더 fallback·feature_name/priority 공유·carry-forward)을
재구현하지 않고 원본을 소비한다.

| 검사 | 내용 | 실패 시 |
|---|---|---|
| G1 스키마·기수 | manifest 파싱, mapping 12/selector 14/binding 15 exact, selector `(sheet, source_no, functionality_effective)` 전역 유일 | RED |
| G2 workbook 결박 | `tc_samples/TC_1.xlsx` 존재 + raw SHA == pin | RED |
| G3 source row 정합 | sheet별 `load_mmi_rows()` 산출에서 selector conjunction으로 row 해석 → `source_content_hash` 재계산 == manifest | RED |
| G4 curated 정합 | yaml_path 존재(tracked) + `name`==yaml_tc_name + blocker_step_index 범위 내 + step의 (action, command, expected) == step_projection exact | RED |
| G5 baseline 등재 | origin 블록 형식·evidence SHA 64-hex·verdict 문자열 고정 | RED |

- workbook 편집 → G2/G3 RED, curated blocker step 편집 → G4 RED,
  manifest 훼손 → G1 RED. **어느 쪽이 변해도 게이트가 관계 재검토를 강제**한다.
- 게이트는 순수 host-only·read-only·결정론 (단말·network·시계 의존 0).

## 6. Seeding 절차

`scripts/gen_provenance_manifest.py`:
- 입력: evidence JSON 경로 (`--evidence`, gitignored 파일이므로 인자로만 결박)
- evidence `p0.mappings`(12/14/15) + `p1.reconciliation.targets[].tracked_step_projection`
  → manifest를 **결정론 직렬화**(키 정렬, 타임스탬프·경로 비의존)로 출력
- `workbook.raw_sha256`은 seed 시점 실측 pin
- 동일 evidence 입력 → byte-identical 출력 (2회 실행 대조를 검증 절차에 포함)
- manifest는 seed 후 **tracked source로 승격** — 이후 갱신은 사람이 게이트 RED를
  보고 심의해 수정 (자동 재생성으로 덮지 않음; 도구는 유래 증명·재검토 보조)

## 7. RED/GREEN 계획 (TDD)

1. RED: manifest 부재 상태에서 게이트 테스트 작성 → 전건 실패 확인
2. seed 실행 2회 → byte-identical 확인 → manifest 배치 → GREEN
3. 변조 RED 4종 (임시 사본에서): workbook row 1셀 변조 → G3 RED /
   curated step command 변조 → G4 RED / manifest binding 1건 삭제 → G1 RED /
   workbook pin 불일치 → G2 RED
4. 전체 `pytest tests/` 회귀 0 (corpus 카운트 pin 16 유지 포함)

## 8. Scope / Immutables

**최초 허용**: §3 표의 신규 4파일만. 기존 tracked 파일 편집 0.

### 8.1 Implementation-discovered, pre-edit amendment approvals

최초 범위 밖 필요 변경은 발견 즉시 정지·보고한 뒤, 다음 두 amendment를 각각
사용자가 **수정 전에 승인**한 후에만 적용했다.

1. **Inventory scope amendment** (`진행해` 승인):
   `scripts/canonical_shell_rc_inventory.py`와
   `tests/test_canonical_shell_rc_inventory.py`를 허용했다. 변경은
   `provenance/` 제외, 현재 HEAD tracked YAML pin `615 → 619`, 제외 회귀 테스트로
   한정했다.
2. **Full-access dispatch test-simulation amendment**
   (`P2 FULL-ACCESS DISPATCH TEST-SIMULATION AMENDMENT APPROVED`):
   `tests/test_dispatch_capsule.py`만 허용했다. 두 git spawn-failure 테스트의
   `PATH=""` simulation을 `subprocess.run`의 직접 `FileNotFoundError` monkeypatch로
   교체했다. 제품 capsule generator와 기술 계약은 변경하지 않았다.

따라서 최종 유효 commit 범위는 **신규 4 + 후속 승인 tracked 3 = 정확히 7경로**다.
commit `4c484d53e4227933b43fffad3f1846435a70c995`는 이 7경로만 포함하며,
전체 회귀는 `1545 passed, 1 warning`이었다.

**Immutable**: workbook, `exported_ss_call/*.yaml`, `src/mmi_converter/`(import만
허용·수정 금지), 캠페인 문서 전체(directive·2026-07-27 spec·amendment specs),
controller·capsule generator, campaign temp/evidence roots.

**구현 당시 금지**: stage, commit, push, campaign 재실행, cleanup, CLAUDE.md 편집
(§5.3 도구 등록·§8.2 row는 별도 §8.3 승인 게이트). stage, commit, push는 구현
검증 뒤 별도 명시 승인을 받아 완료했다. campaign 재실행, cleanup, CLAUDE.md 편집은
위 commit에 포함하지 않았다.

## 9. 후속 (본 P2 범위 밖)

- CLAUDE.md §5.3에 seeding 도구·게이트 등록 + §8.2 row (§8.3 게이트)
- campaign roots cleanup + 완주 run 아카이브 (`20260812-final`) — 별도 승인
- 2026-08-11 amendment doc §9 이력 rewrite 정정 — 당시 값 보존 + superseded
  주석 추가 (2026-08-13 기록 정정 batch)
- qa-suite 이주 시 manifest·게이트 동반 이동 (설계 v2 provenance manifest 개념과 정렬)
