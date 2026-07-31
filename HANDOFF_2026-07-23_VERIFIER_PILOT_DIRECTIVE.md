# HANDOFF 2026-07-23 — evidence-verifier 구축 + T0-CHAR 파일럿 (Codex 지시문) · rev2

**rev2 사유**: rev1 착수 시 "애매하면 STOP" 발동. verifier 스펙에 false-GREEN 구멍 4건(C1 내용비교 부재 / C2 self-오염·모순 / C4 baseline outcome 부재 / 입력 baseline 미결박) 확정 → 아래 계약으로 잠금.

**역할**: Codex 실행 / Claude 검토·freeze. tier·게이트·재분류 판단 Codex 금지 — 애매하면 STOP + 보고.
**baseline(확인됨)**: HEAD `e615490`, origin/master `b114c01`, ahead 1, tracked/staged 변경 0, 전체 pytest **1342 passed, 1 warning**.
**근거 문서**: `RUNBOOK_DIRECTIVE_TEMPLATE.md` v2 (§0 캡슐 / §5 evidence bundle).
**목표**: 이중 게이트의 (A) 검토를 tier 무관하게 싸게 만드는 self-attesting verifier + 최소 Tier 0 파일럿 1건 실증.

**공통 금지**: commit / push / device / network / schema / deps = 전부 하드 STOP(별도 승인). 두 Phase 모두 host-only.
**환경**: pytest = `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider`. CRLF 함정(§5.5) — 파일 비교는 **git 기반(`git hash-object`, `git ls-files -s`, `git status --porcelain`)**, raw sha256 파일비교 금지.

---

## Phase 1 — evidence-verifier 구축 (TDD · Claude 풀 리뷰 = Tier 1)

> false GREEN 금지가 존재이유. 각 체크의 fail-closed와 입력 무결성이 적대적 테스트로 증명돼야 **완료**. verifier 자체 테스트는 **격리 fixture(temp git repo / fake git·pytest 출력)** 사용 — 라이브 repo 상태 의존 금지(결정론).

**산출**: `scripts/evidence_verifier.py` + `tests/test_evidence_verifier.py` (신규, 미커밋 — 리뷰 후 승인 커밋).

### 인터페이스 (2 모드)

```
evidence_verifier.py capture-baseline --out <baseline.json>
evidence_verifier.py verify --baseline <baseline.json> --capsule <capsule.json> --out <bundle.json>
```

### baseline.json (capture-baseline 산출 — 결정론, 정렬)

```
schema_version: 1
tool:      {verifier_sha256}                       # verifier 스크립트 자기 git hash-object
git:       {head_sha, upstream_sha, ahead, behind}
worktree:                                           # dirty 또는 staged인 tracked path마다
  <path>:  {worktree_blob: <hash-object>, index_blob: <staged blob|null>, head_blob: <HEAD blob|null>}
index_fingerprint: <git ls-files -s 전체 정렬 해시>  # index 완전 상태
untracked: [<path>...]                              # git status --porcelain -uall '??' 정렬
pytest:    {passed:[nodeid...], skipped:[nodeid...], xfailed:[nodeid...],
            counts:{passed,skipped,xfailed,failed,errors}}   # junit 파생
collect_nodeids: [<nodeid>...]                      # pytest --collect-only -q 정렬
```

`baseline_sha256` = sha256(baseline.json canonical bytes). baseline **내부에 자기참조 금지** — capsule이 이 값을 보유해 결박.

### capsule.json (파일럿/후속 runbook이 작성)

```
schema_version: 1
capsule_id
baseline_sha256                     # ← baseline.json 바이트 결박
head_sha                            # baseline HEAD (재확인)
verifier_sha256                     # 기대 verifier 자기해시
allowed_write_paths:   [<path>...]
expected_new_nodeids:  [<nodeid>...]
removed_nodeids_allowed: false
production_invariant:  {<path>: <git hash-object 기대값>}
pytest_min_passed:     <int>
evidence_paths:        [<정확 경로>...]   # C2 예외 — exact match만(prefix·glob 금지)
```

### 체크 · exit 계약

**exit: `0=GREEN` / `1=DoD RED` / `2=입력 무효` / `3=측정·인프라 실패`.** verify는 **항상 bundle.json을 먼저 emit**(dod verdict + exit 사유 포함) 후 해당 코드로 종료.

| ID | 단계 | 규칙 | 실패 exit |
|---|---|---|---|
| **C0 input_integrity** | 선행 | baseline/capsule schema valid · `sha256(baseline.json)==capsule.baseline_sha256` · 현재 HEAD == `capsule.head_sha` == `baseline.git.head_sha` · verifier 자기 hash-object == `capsule.verifier_sha256` · allowed_write/production/evidence 전 경로 repo-relative·travers(`..`·절대) 없음 · baseline 판독 가능 | **2** |
| **C1 file_delta** | 판정 | `worktree_delta == allowed_write_paths` (worktree_delta = 현재 hash-object가 baseline blob과 다른 tracked path 집합; baseline blob = worktree[p].worktree_blob 있으면 그것, 없으면 HEAD blob) **AND** 현재 `index_fingerprint == baseline` (stage 변화 0) | **1** |
| **C2 untracked_delta** | 판정 | `added = 현재_untracked − baseline.untracked − evidence_paths(exact)` == ∅ **AND** `removed = baseline.untracked − 현재_untracked` == ∅ | **1** |
| **C3 nodeid_delta** | 판정 | `added(collect) == expected_new_nodeids` **AND** `removed(collect) == ∅` | **1** |
| **C4 pytest** | 판정 | exit 0 · `failed==0·errors==0` · `passed_now ⊇ baseline.passed`(기존 PASS 보존) · `(skipped_now−baseline.skipped)==∅ AND (xfailed_now−baseline.xfailed)==∅`(신규 skip/xfail 0) · `expected_new_nodeids ⊆ passed_now`(신규 nodeid PASS) · `counts.passed >= pytest_min_passed` | **1** |
| **C5 production_invariant** | 판정 | `production_invariant` 각 path의 현재 `git hash-object` == 기대값 | **1** |
| infra | 상시 | git subprocess 오류 · pytest 미기동 · junit 파싱 실패 · bundle IO 실패 = 측정 불능(≠ RED) | **3** |

### bundle.json (§5)

`schema_version, capsule_id, verifier_exit, exit_reason, steps[{command,cwd,exit_code}], files{path:{blob_before,blob_after}}, pytest{exit_code,counts}, nodeids{added,removed}, workspace_delta{worktree_delta,index_changed,untracked_added,untracked_removed}, dod[{id,verdict,detail}]`. 타임스탬프·out 경로는 입력 주입(Date.now류 금지 정합), 동일 입력 재실행 시 dod 집합·verifier_exit 동일.

### TDD RED 필수 (fail-closed 증명 — 격리 fixture)

- **C0**: capture 후 baseline.json 1바이트 변조 → `baseline_sha256` 불일치 → **exit 2** / capture 후 HEAD 이동(fixture commit) → **2** / capsule 경로에 `..` → **2** / verifier 자기해시 불일치 → **2**
- **C1**: 이미 dirty인 파일에 **추가 변경** 주입(경로는 그대로) → worktree_delta 포함 → allowed 밖이면 **1** / dirty 파일 **원복** → worktree_delta 포함 → **1** / 여분 파일 stage → index_fingerprint 변화 → **1** / 정상 1파일만 변경 → C1 GREEN
- **C2**: evidence_paths **exact** 산출물 출현 → 허용 / 형제 untracked 1개 주입 → **1** / baseline untracked 1개 삭제(removed) → **1**
- **C3**: 선언 외 nodeid 추가 → **1** / 기존 nodeid 1개 제거(parametrization 소실 포함) → **1**
- **C4**: 기존 PASS nodeid가 skipped로 → **1** / 신규 nodeid가 ERROR → **1** / 신규 xfail 1건 → **1**
- **infra**: git 호출 실패·pytest 미기동 fixture → **exit 3**(1/2와 구분)
- **happy**: 전 체크 통과 → **exit 0** + bundle schema valid + 결정론(2회 동일)
- **anti-vacuous**: 빈 capsule / 전부 빈 집합이 무조건 exit 0을 내지 못함(C1 allowed=∅인데 변경 존재 시 RED 등)

### Phase 1 STOP

완료 후 STOP. evidence = ① verifier 테스트 GREEN 목록 ② 전체 pytest 델타(1342→N) ③ C0~C5·infra 각 케이스가 실제로 기대 exit(0/1/2/3) 냄을 보이는 출력. **Claude 풀 독립 재검증**(각 fail-closed 재현·결정론·anti-vacuous). 승인 전 Phase 2 금지.

---

## Phase 2 — T0-CHAR-2 파일럿 (Tier 0 · Phase 1 승인 후에만)

### capsule `RB-20260723-d0-char` (freeze값 확정)

```
capsule_id:            RB-20260723-d0-char
baseline_sha256:       <capture-baseline 직후 print된 sha256(baseline.json) — Codex 채움>
head_sha:              e6154907fe462e7ef921caa45413809cd5b3c33d
verifier_sha256:       deaa7d01df674785720e9dc244a1049546f363f0   # Phase 1.1 fix 후 Tier-1 재승인 (4d54c172 폐기)
allowed_write_paths:   [tests/test_adb.py]
expected_new_nodeids:  [<--collect-only로 pin: screenshot/dump argv characterization nodeid(들)>]
removed_nodeids_allowed: false
production_invariant:  {src/adb.py: a8b5ae2410619a97d3e68dfdfbc20231a8f455a7}
pytest_min_passed:     <baseline.pytest.counts.passed + len(expected_new_nodeids); 현재 예상 1388 + N>
evidence_paths:        [scratch/rb_20260723_d0char_baseline.json, scratch/rb_20260723_d0char_capsule.json, scratch/rb_20260723_d0char_bundle.json]
```

**freeze 확정 사항 (Tier-1 재검증 후)**:
- verifier(`scripts/evidence_verifier.py` blob `deaa7d01…`, Phase 1.1 fix 반영)는 **Tier-1 재승인 완료**. 사용자 batch 커밋 전이라 untracked이나, `verifier_sha256`은 hash-object(content)라 그대로 유효. **파일럿 중 verifier 2파일 수정 금지**(수정 시 C0 → exit 2).
- baseline pytest = **1388**(1342 + verifier 테스트 46, Phase 1.1로 44→46). `pytest_min_passed`은 capture한 baseline count 기준.
- exit 계약(정정): unsafe/invalid output = **exit 2 + bundle 미기록**, bundle **IO 실패** = **exit 3 + 미기록**. GREEN 판정은 `verifier_exit==0 AND exit_reason=="GREEN"`.
- **운영 창**: capture-baseline·verify 각각 full-suite 재실행(~7분/회) → 총 ~15분. 그 사이 repo 변경 금지 — 특히 untracked backlog(~200) / verifier 2파일이 바뀌면 C2 RED 또는 exit 3. 조용한 창에서 원샷.

### Task T0-CHAR-2 — screenshot/dump exact-argv characterization

1. `capture-baseline --out scratch/rb_20260723_d0char_baseline.json` → print된 sha256을 capsule `baseline_sha256`에 기입 (verifier_sha256=`4d54c172…` 확정)
2. `tests/test_adb.py`에 characterization 추가: `screenshot()` → `/data/local/tmp/tc_runner_screenshot_tmp.png` + pinned serial argv, `dump_ui()` → `/data/local/tmp/tc_runner_ui_dump.xml` + pinned serial argv (실제 메서드명·시그니처는 `src/adb.py` 확인 후 정합, subprocess mock)
3. **expected: initial GREEN**. 처음부터 실패 = production 버그 신호 → **production 수정 없이 STOP + 보고** ("RED가 곧 GREEN" 아님)
4. 추가한 nodeid를 `--collect-only`로 확정해 capsule `expected_new_nodeids`·`pytest_min_passed`(=1386+N) 채움
5. `verify --baseline scratch/rb_20260723_d0char_baseline.json --capsule scratch/rb_20260723_d0char_capsule.json --out scratch/rb_20260723_d0char_bundle.json` → **exit 0 AND exit_reason==GREEN** 확인
6. STOP + bundle 보고 (verifier_exit·전 C0~C5 verdict·nodeids.added)

### Phase 2 DoD = verifier 판정 (사람 체크박스 아님)

C0 통과 · C1 `{tests/test_adb.py}` · C2 evidence_paths 외 오염 0 · C3 added==선언·removed==∅ · C4 exit0·passed≥1342·신규 skip/xfail 0 · C5 `src/adb.py` hash-object 불변 · **verifier_exit==0** → Tier 0 GREEN.

---

## Claude 검토 계약

- **Phase 1** = Tier 1 → 풀 독립 재검증(C0~C5·infra fail-closed 재현, 결정론, anti-vacuous, exit 0/1/2/3 경계).
- **Phase 2** = Tier 0 → `bundle.verifier_exit==0` **AND** `exit_reason==GREEN` 확인 + 불변식 1개 spot-check(`src/adb.py` hash-object 불변). exit 2/3이면 GREEN 아님 — 입력·인프라 정정 후 재실행.

## 산출물 위치

- `scripts/evidence_verifier.py`, `tests/test_evidence_verifier.py` (신규·미커밋 — 리뷰 후 승인 커밋)
- `scratch/rb_20260723_d0char_{baseline,capsule,bundle}.json` (파일럿 evidence, local)

---

## Phase 1.1 — verifier micro-fix (승인됨 · Tier 1 · Phase 2 재실행 선행)

**근거**: Phase 2 capture가 `_parse_collect_output`의 nodeid 전체 정규화 때문에 백슬래시 param id를 손상시켜 JUnit 매핑 실패(exit 3). 독립 확인된 실트리거: `test_adb.py::test_adb_rejects_non_none_serial_containing_whitespace[\t]`, `[1-device\n-False]`, `test_catalog_delta.py::...[bad\id]`. fail-closed(exit 3)로 멈춰 false-GREEN 없음.

### 수정 (정확히 1곳 — 그 외 변경 금지)

`scripts/evidence_verifier.py` `_parse_collect_output` line 594:

```python
# BEFORE
        nodeids.append(_normalize_git_path(line))
# AFTER — module 경로만 정규화, param id는 verbatim 보존
        rest = line[len(module):]
        nodeids.append(_normalize_git_path(module) + rest)
```

- **다른 `_normalize_git_path` 호출(376/393/426/438/531/539)은 파일 경로라 정상 — 손대지 말 것.**
- `_nodeid_key`는 무변경(module→dotted, param=parts[-1] 보존이 이미 정상).

### 적대 테스트 (RED→GREEN, 둘 다)

1. **단위**: `_parse_collect_output`에 `tests\test_x.py::test_p[\t]`(Windows 구분자 + 백슬래시 param) 입력 → `tests/test_x.py::test_p[\t]`(module만 `/`, param `\t` 보존) 반환 assert.
2. **통합**: `_make_repo`의 tests_source에 백슬래시 param 파라미터라이즈드 테스트(예: `@pytest.mark.parametrize('v', ['\t', 'a\b'])`) 포함 → `capture-baseline` **exit 0**(수정 전 exit 3 회귀 잠금).

### 알려진 한계 (NOTE, 이번 미수정)

param id에 `::`가 포함되면 `_nodeid_key`의 `split("::")`가 과분할. 현 suite에 해당 없음 → 별도 티켓. 이번 스코프 밖.

### Phase 1.1 완료 조건 · 후속

- 전체 pytest: 1386 + 신규 적대 테스트 → **exit 0**, nodeid 소실 0
- 새 `git hash-object scripts/evidence_verifier.py` = **새 verifier blob** → Phase 2 capsule의 `verifier_sha256`을 이 값으로 교체(4d54c172 폐기)
- **Claude Tier-1 재승인** 필요(재정독 delta + 독립 probe 재실행 + 백슬래시 param 신규 probe). 승인 후 Phase 2 재실행.
- STOP after Phase 1.1: 수정 diff + 적대 테스트 결과 + 새 verifier blob 보고.
