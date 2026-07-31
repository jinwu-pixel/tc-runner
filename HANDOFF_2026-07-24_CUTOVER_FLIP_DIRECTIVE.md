# Cutover — canonical default flip 실행 지시서 (Codex 실행용)

**역할**: Codex = 구현 / Claude = 계획·검증. **Tier 2**(전 사용자 런타임 behavior 변경) — 스코프 임의 확대 절대 금지.

## 0. 승인 근거 (SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md`)

전 gate 충족: G0 governance/tests · G0.5 ledger · G1a normalizer/producer · G1b host gate/runtime semantics · G2 host differential · **G2 device conditional**(2026-07-24 THOR2_J 4-run, 48/48, mismatch 0, Claude 재검증 GREEN) · **Cutover = Claude review + 사용자 승인**(2026-07-24 획득).

**설계가 명시적으로 불허하는 것 (L570·L950 — 하나라도 손대면 STOP)**:
- legacy 제거 / alias branch 제거(L459)
- corpus rewrite · qa-suite cutover · 신규 device campaign

## 1. 변경 — 정확히 1곳

`src/cli.py` `--contract-mode` argparse 정의 (현 907~912):

```python
# BEFORE
        default="legacy",
        help="execution contract mode (기본: legacy)",
# AFTER
        default="canonical",
        help="execution contract mode (기본: canonical; legacy는 --contract-mode legacy)",
```

`choices=("legacy","canonical")`는 **불변** — legacy escape hatch 유지(L570).

## 2. 변경 금지 (over-reach 차단 — 각각 STOP 사유)

아래 default는 **전부 `"legacy"` 유지**:

| 파일:라인 | 대상 |
|---|---|
| `src/cli.py:280` | `getattr(args,"contract_mode","legacy")` 프로그램 호출 fallback |
| `src/action_runner.py:52` | `ActionRunner.__init__` |
| `src/tc_loader.py:25` | `load_tc` |
| `src/excel_converter.py:54` | converter |
| `src/mmi_converter/compiler.py:16` · `exporter.py:54` | producer |
| `src/reporter.py:52` | Reporter |

**이유**: 1120 baseline 테스트는 `contract_mode`를 명시하지 않는다. library default를 뒤집으면 baseline이 일제히 canonical로 바뀌어 깨진다 = 설계 **L966 STOP 조건**("original baseline test node disappears or fails"). flip은 **사용자 진입점(CLI) default 승격**이지 library 계약 변경이 아니다.

## 3. TDD (RED → GREEN)

- **RED 1**: `cli run <tc>` argv에 `--contract-mode` 미지정 → 해석된 mode == `"canonical"` (현재 legacy → RED)
- **RED 2**: `--contract-mode legacy` 명시 시 여전히 legacy로 해석 + legacy 동작(continue-policy 등) 보존 (escape hatch 회귀 잠금)
- **RED 3**: `choices` 양쪽 모두 선택 가능 유지

**테스트 수정 규칙 (중요)**:
- 기존 테스트가 **"default가 legacy임"을 단언**하고 있으면 = flip이 의도적으로 바꾸는 계약이므로 **in-place로 canonical 단언으로 갱신**(함수명 유지 = nodeid 보존).
- 기존 테스트가 **default를 건드리지 않는데 깨지면** = flip의 예상 외 blast radius → **즉시 STOP + 보고**(임의 수정 금지).
- **함수명 rename 금지**(nodeid 소실 = §4 verifier C3 RED). rename이 불가피해 보이면 STOP + 보고.

## 4. 검증 게이트

1. 전체 `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` → **전부 GREEN**(1390 + 신규). 기존 테스트 실패가 §3 두 번째 범주면 STOP.
2. **evidence_verifier로 자기증명**(도구 2번째 실사용 · Tier 2라 기계증거 필수):
   - capsule: `allowed_write_paths=[src/cli.py, tests/test_cli.py]`(실제 수정 파일과 정확 일치) · `expected_new_nodeids`=신규 테스트 · `removed_nodeids_allowed=false` · `production_invariant`={변경 안 한 default 보유 파일 중 1개 이상, 예 `src/action_runner.py`·`src/tc_loader.py`의 현재 `git hash-object`} · `pytest_min_passed`=capture한 baseline
   - `verify` → **exit 0 / exit_reason=GREEN** 확인. 1/2/3이면 STOP + bundle 보고.
   - production_invariant에 §2 금지 파일을 넣어 **"library default 무변경"을 기계적으로 증명**할 것.
3. `git status` — 변경 파일이 `src/cli.py`·`tests/test_cli.py` **정확히 2개**(+ evidence scratch). 그 외 1개라도 있으면 STOP.

## 5. 범위 밖 (Codex 미수행)

- **commit / push 금지** (별도 명시 승인)
- **문서·정책 갱신 금지** — 설계 checklist L994·CLAUDE.md §8.2 cutover row는 **Claude가 리뷰 후 처리**
- device run·corpus·producer·qa-suite 무접촉

## 6. 보고 + STOP

diff(2파일) · pytest 수치(전/후) · 갱신한 기존 테스트 목록과 범주 판단 근거 · 신규 nodeid · verifier bundle(`verifier_exit`/C0~C5/`files`) · `git status` · 새 `src/cli.py` blob.

**보고 후 STOP.** Claude가 Tier-2 재검증(flip 의미·escape hatch·blast radius) 후 cutover 종결·문서 반영·커밋 승인 흐름으로 넘어간다.
