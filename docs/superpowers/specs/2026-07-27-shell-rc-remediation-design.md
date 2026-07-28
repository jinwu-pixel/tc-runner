# Canonical Shell RC Blocker Remediation Design

> 상태: **DESIGN DRAFT / host-only**. 2026-07-27 사용자가 방향을 승인했으며,
> 이 문서는 서면 리뷰 대기 상태다. 이 승인은 TC·코드 구현, staging, commit,
> push 또는 단말 실행 승인이 아니다.

**Goal:** canonical CLI 기본 경로에서 잘못된 `grep -c` 종료 코드 때문에 발생하는
18개 blocking assertion을 기존 `verify_shell` 계약만으로 fail-closed 교정하고,
frozen audit v1을 보존하면서 교정 전후를 재현 가능한 v2 증거로 고정한다.

**Decision:** 18개 step을 source-command RC, grep RC, 정수 count 술어를 모두
명시적으로 검사하는 `verify_shell` step으로 통일한다. 술어가 참일 때만 고유
sentinel을 stdout에 출력한다. runner·ADB·schema·normalizer·validator 계약은
변경하지 않는다.

---

## 1. Baseline and Evidence Identity

2026-07-27 설계 시작 시점의 live 상태는 다음과 같다.

| 항목 | 값 |
|---|---|
| live HEAD | `0ca6701e9574bccd5b7e6e74bda8e0ded751423e` |
| remote sync | `origin/master...HEAD = 0/0` |
| tracked / staged | clean / 0 |
| frozen inventory HEAD | `78b3ac34e9f8bacabe926172dd199342b7eb58c5` |
| frozen inventory CSV SHA-256 | `b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f` |
| frozen risk matrix SHA-256 | `81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4` |
| frozen policy v1 SHA-256 | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` |
| candidate source workbook | `tc_samples/TC_1.xlsx` |
| workbook SHA-256 / Git blob | `160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa` / `24593d11dd80a2b3711655bd0c5216ee9157dedc` |
| YAML-declared source sheets | `SS-TC 0` (1행), `SS-TC 1` (14행) |
| documented replay example | `python -m src.cli export-mmi tc_samples/TC_1.xlsx --sheet "SS-TC 1"` |
| matrix population | 692 rows = blocker 18 + advisory 74 + runtime-review 6 + default 594 |

18개 blocker와 6개 runtime-review가 속한 YAML은 frozen HEAD부터 live HEAD까지
tracked diff가 0이다. 따라서 `78b3ac3`의 row identity를 현재 교정 설계의
baseline으로 사용할 수 있다.

다음 파일은 구현 slice의 불변 대상이다.

| 파일 | SHA-256 |
|---|---|
| `src/action_runner.py` | `f56f3bc4163383496fd264fa54ce15771b25563f3d545a8632694e89f0264e4f` |
| `src/adb.py` | `c9f6a5dff5f30250ce20dc79f8867d304056a161d634033f59e55df827c7e562` |
| `src/execution_contract.py` | `b5a8601a8efd7008752f5c1b50134066082a64f8b976f1fb2270fcc76f1b21eb` |
| `tc_step_schema.json` | `7ec8a76766bec3e8ba18cdd8deedb478024edb2878ee83190907125669cc7059` |
| `validate_tc.py` | `6655a6624b660d32d5a074901936180120e0d93826c48d2a2cbee7b2ac8d2ec8` |
| `scripts/canonical_shell_rc_inventory.py` | `277e0cbbf82fad3f858cb38c211d28d9388446fd2b43ed74316f8d934c7414a9` |
| `scripts/canonical_shell_rc_risk_audit.py` | `3d9903854a8c4d4cbb64edec4b412563a3ac4626f0ad25cf2934d06d44e61d34` |
| `scripts/canonical_shell_rc_risk_policy_v1.json` | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` |

구현 게이트에서는 모든 해시를 소문자 64자리로 정규화해 비교한다.

---

## 2. Scope

### 2.1 Included

- frozen matrix의 blocking 18행을 정확히 교정
- 15개 YAML에서 target step의 `action`, `command`, `expected`만 변경
- exact target manifest와 host-only remediation verifier 및 테스트 추가
- frozen v1을 수정하지 않는 post-remediation v2 matrix/SUMMARY 생성
- runtime-review 6건의 정적 처분을 v2 증거에 기록
- RED-first 테스트, validate, full pytest, nodeid 보존, 결정론, 오염 검사

### 2.2 Excluded

- advisory 74행 교정 또는 분류 변경
- runtime-review 6행의 YAML 수정
- `src/action_runner.py`, `src/adb.py`, schema, validator, loader, normalizer 수정
- `allowed_exit_codes`, 신규 action, typed stdout assertion 도입
- `event`, `callSignals=[]`, `viewSelectionOverlay`, `rv_files` pattern 의미 개선
- legacy 제거 또는 CLI default 재변경
- producer promotion, qa-suite 또는 다른 repo 변경
- 단말 접촉, `runtime PASS` 주장
- staging, commit, push

기존 action으로 아래 계약을 정확히 표현할 수 없다고 구현 중 확인되면 범위를
늘리지 않고 STOP한다. 신규 runner/schema 계약은 별도 설계 slice다.

---

## 3. Exact Blocker Manifest

최종 target은 15개 YAML, 18개 step이다. step index는 frozen inventory의
1-based `steps[]` index다.

| # | source path # step | 기존 action | frozen class | 교정 술어 | provenance |
|---:|---|---|---|---|---|
| 1 | `ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml#24` | `verify_shell` | `COUNT_EQ_0` | count == 0 | local TC |
| 2 | `ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml#11` | `shell` | `MASKED_ASSERTION` | count == 1 | local TC |
| 3 | `exported_ss_call/SS_TC01_permission_denied.yaml#10` | `verify_shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 4 | `exported_ss_call/SS_TC01_permission_denied.yaml#11` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 5 | `exported_ss_call/SS_TC02_permission_allow_idle.yaml#11` | `shell` | `COUNT_EQ_1` | count == 1 | `TC_1.xlsx` |
| 6 | `exported_ss_call/SS_TC03_ringing_permission.yaml#15` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 7 | `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml#18` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 8 | `exported_ss_call/SS_TC05_boundary_values.yaml#9` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 9 | `exported_ss_call/SS_TC06_missed_rejected.yaml#10` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 10 | `exported_ss_call/SS_TC06_missed_rejected.yaml#11` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 11 | `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml#9` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 12 | `exported_ss_call/SS_TC09_offhook_permission_banking.yaml#20` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 13 | `exported_ss_call/SS_TC0_P0_endcall_crash.yaml#15` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |
| 14 | `exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml#24` | `verify_shell` | `COUNT_EQ_0` | count == 0 | manual |
| 15 | `exported_ss_call/SS_TC10_permission_toggle.yaml#24` | `shell` | `COUNT_EQ_1` | count == 1 | `TC_1.xlsx` |
| 16 | `exported_ss_call/SS_TC11_multi_subscription.yaml#20` | `shell` | `COUNT_EQ_1` | count == 1 | `TC_1.xlsx` |
| 17 | `exported_ss_call/SS_TC11_multi_subscription.yaml#21` | `shell` | `COUNT_LE_1` | count <= 1 | `TC_1.xlsx` |
| 18 | `exported_ss_call/SS_TC12_legacy_path.yaml#19` | `shell` | `COUNT_EQ_0` | count == 0 | `TC_1.xlsx` |

교정 후 술어 분포는 `EQ_0=13`, `EQ_1=4`, `LE_1=1`이다. frozen class의
`MASKED_ASSERTION` 1건은 기존 YAML의 무시되던 `expected: "1"`과 설명
“파일 리스트 뷰 존재 확인”에 따라 `EQ_1`로 고정한다.

15개 `TC_1.xlsx` 유래 행은 12개 파일에 분포한다. 나머지는 manual 1행과
ODIN2 local TC 2행이다.

---

## 4. Source Provenance Gate

`tc_samples/TC_1.xlsx`는 tracked source candidate로 존재하며 12개 YAML의
metadata는 이 파일의 `SS-TC 0` 또는 `SS-TC 1` sheet를 가리킨다. 기존 계획에는
같은 workbook의 `SS-TC 1` `export-mmi` replay 명령이 기록돼 있다.

설계 작성 세션에서는 spreadsheet artifact runtime이 제공되지 않아 workbook
내부 셀과 exporter round-trip을 열어 확인하지 못했다. 따라서 “workbook이
없다”는 전제는 기각됐지만, 15행이 현재 workbook에서 재생되는지는 아직
확정하지 않는다.

구현은 다음 read-only provenance reconnaissance가 GREEN이 되기 전까지
**모든 18행 편집을 STOP**한다. 부분 교정은 허용하지 않는다.

### P0 — workbook identity

- tracked path, SHA-256, Git blob이 §1 값과 일치
- sheet `SS-TC 0`, `SS-TC 1` 존재
- 12개 YAML metadata와 workbook row를 잇는 exact mapping 15개 작성
- workbook의 relevant cell value/formula/style을 읽기 전용으로 기록

### P1 — isolated replay

명령 실행은 별도 host-execution 승인 뒤에만 수행한다.

1. `export-mmi` dry-run을 `SS-TC 0`, `SS-TC 1` 각각 실행해 결과를 기록한다.
2. 실제 export는 repo 밖 temporary directory에만 기록한다.
3. exporter 코드 SHA, 전체 argv, workbook SHA를 고정한다.
4. isolated output과 tracked `exported_ss_call/`을 tc identity로 join한다.
5. target 15행의 source procedure와 emitted command 관계를 증명한다.
6. target 외 semantic delta를 보고한다.

### P2 — provenance decision

- P0/P1이 15행을 재현하면 **source-first**가 강제된다. workbook의 exact cell
  set을 먼저 freeze하고 source와 derived YAML을 같은 Tier 1 slice에서 정렬한다.
- P0/P1이 불일치하면 즉시 STOP한다. mismatch evidence를 사용자에게 보고한
  뒤에만 compiled-artifact 예외 또는 producer reconcile slice를 선택할 수 있다.
- workbook이 존재하는 현재 상태에서
  `source_debt: "TC_1.xlsx unavailable"`을 사용할 수 없다.

P0/P1의 결과나 P2 선택을 구현자가 추정하지 않는다.

---

## 5. Assertion Contract

### 5.1 Step contract

- 18행 모두 최종 `action`은 `verify_shell`이다.
- 기존 `verify_shell` 3행은 action을 유지한다.
- 기존 `shell` 15행은 `verify_shell`로 전환한다.
- 각 target의 sentinel은
  `__TC_ASSERT_OK_<sha256(source_path + "#" + step_index)[:12]>__` 형식이다.
  manifest가 계산값을 고정하며 18개 값은 서로 달라야 한다.
- 각 target의 `expected`는 자기 row의 sentinel과 정확히 같다.
- sentinel은 모든 검사와 cleanup이 성공한 마지막 경로에서만 stdout에 한 번
  출력한다.
- pre-cleanup/source/grep/final-cleanup 오류는 stderr에 각각
  `TC_ASSERT_PRE_CLEANUP_RC=<rc>`, `TC_ASSERT_SOURCE_RC=<rc>`,
  `TC_ASSERT_GREP_RC=<rc>`, `TC_ASSERT_CLEANUP_RC=<rc>`를 기록한다.
  count parse 오류는 `TC_ASSERT_COUNT_INVALID=<value>`, predicate mismatch는
  `TC_ASSERT_COUNT=<n> EXPECTED=<predicate>`를 기록하고 nonzero로 종료한다.

이 계약은 두 runtime mode에서 모두 fail-closed다.

- canonical: `rc == 0`을 먼저 확인한 뒤 stdout sentinel을 확인한다.
- explicit legacy: shell RC는 보존하지 않지만 실패 경로에 sentinel이 없으므로
  `expected` substring 검사가 실패한다.

### 5.2 Timeout contract

기존 `shell` 15행은 양 mode에서 기본 timeout 10초를 사용한다. `verify_shell`로
전환하면 양 mode의 기본 timeout은 30초가 된다. 이 10초→30초 변화는 action
전환에서 파생되는 **승인된 유일한 시간 의미 delta**다.

명시적 `timeout`으로 10초를 보존하지 않는다. 현재 runner는 같은 값을
canonical에서 ms, legacy에서 seconds로 해석하므로 하나의 값으로 양 mode의
10초를 동시에 표현할 수 없다. manifest는 15행에
`timeout_policy: "verify_shell_default_30s"`를 기록하고 target step에는
`timeout`을 새로 쓰지 않는다. 기존 `verify_shell` 3행도 기존 default 30초를
유지한다.

host test는 다음을 고정한다.

- canonical target step이 `shell_result(..., timeout_s=30.0)`을 호출
- legacy target step이 `shell(..., timeout=30)`을 호출
- 이외 timeout field delta 0

### 5.3 Source RC와 count RC 분리

`logcat ... | grep -c ...`처럼 pipeline의 마지막 RC만 소비하지 않는다.
source command 출력을 먼저 `/data/local/tmp`의 step-specific 파일에 기록하고
source RC를 독립 확인한다.

개념적 구조는 다음과 같다.

```sh
tmp="/data/local/tmp/tc_runner_rc_<row-slug>_$$.txt"
rm -f "$tmp"
pre_cleanup_rc=$?
[ "$pre_cleanup_rc" -eq 0 ] || exit "$pre_cleanup_rc"

<source-command> >"$tmp"
source_rc=$?
[ "$source_rc" -eq 0 ] || <cleanup-and-exit-source-rc>

count="$(grep -c '<frozen-pattern>' "$tmp")"
grep_rc=$?
[ "$grep_rc" -le 1 ] || <cleanup-and-exit-grep-rc>
<reject-empty-or-non-decimal-count>
<apply-EQ_0-or-EQ_1-or-LE_1>

rm -f "$tmp"
cleanup_rc=$?
[ "$cleanup_rc" -eq 0 ] || exit "$cleanup_rc"
printf '%s\n' '__TC_ASSERT_OK__'
```

위 pseudocode의 마지막 문자열은 실제 구현에서 row-specific sentinel로
치환한다.

규칙:

1. `grep -c`의 rc 0은 match 존재, rc 1은 match 부재이므로 둘 다 유효한 count
   결과다.
2. grep rc가 1보다 크면 count 술어를 평가하지 않고 실패한다.
3. count가 빈 문자열이거나 10진 정수가 아니면 실패한다.
4. `EQ_0`, `EQ_1`, `LE_1` 비교가 거짓이면 실제 count를 stderr에 기록하고
   rc 1로 실패한다.
5. source failure, grep failure, predicate mismatch 어느 경로도 sentinel을
   출력하지 않는다.
6. cleanup의 rc가 본래 실패 rc를 덮어쓰지 않게 본래 rc를 먼저 보존한다.
7. 성공 경로의 cleanup 자체가 실패하면 sentinel을 출력하지 않고 실패한다.
8. 시작 전 stale temp 제거가 실패하면 source command를 실행하지 않는다.

### 5.4 UI dump rows

Gallery와 Minifile 2행은 `/sdcard/ui.xml` 공유 파일 대신
`/data/local/tmp/tc_runner_rc_<row-slug>_$$.xml`을 사용한다.
`uiautomator dump` rc를 먼저 확인한 뒤 XML 파일에 count 술어를 적용한다.

이번 slice는 기존 oracle 의미를 보존한다.

- `grep -c`는 XML element 수가 아니라 matching line 수다.
- Gallery는 `viewSelectionOverlay` 부재만 확인한다.
- Minifile은 `rv_files` matching line 1개만 확인한다.
- 같은 파일의 count 1/2/7 이상 등 advisory 행으로 확장하지 않는다.

### 5.5 Forbidden command shapes

target 18행에서 다음은 허용하지 않는다.

- terminal `grep -c`의 rc를 곧바로 step verdict로 사용
- `|| echo 0`
- source command와 grep을 pipeline으로 연결해 source RC 상실
- 성공/실패 양 경로가 같은 sentinel을 출력
- generic `"0"` 또는 `"1"` substring을 `expected`로 사용
- `/sdcard`에 신규 임시 파일 생성

### 5.6 Host proof boundary

Windows host test는 Android `sh`, `logcat`, `uiautomator` 명령을 실행한 것으로
간주하지 않는다. host proof는 다음 세 층으로 한정한다.

1. pure predicate oracle이
   `(source_rc, grep_rc, count_text, predicate)`의 0/1/2/error truth table을 검사
2. manifest renderer가 위 oracle과 대응하는 exact shell template을 생성하고
   target YAML command가 render 결과와 문자열-equal인지 검사
3. mock ADB를 사용한 `ActionRunner` 양 mode test가
   canonical의 `rc + sentinel`과 legacy의 `sentinel-only` verdict를 검사

실제 Android shell 문법, redirection, cleanup, toybox grep 동작은 §9 Tier 2의
serial-pinned synthetic truth table에서 검증한다. host GREEN은
`runtime PASS` 또는 target command 실실행을 의미하지 않는다.

---

## 6. Host Evidence Architecture

### 6.1 Planned files

P0/P1 provenance GREEN 뒤 source-first가 성립할 때의 planned 경계는 다음과
같다. exact workbook cell set은 P0 evidence로 먼저 freeze한다.

**신규**

- `scripts/canonical_shell_rc_remediation_manifest_v1.json`
- `scripts/canonical_shell_rc_remediation_check.py`
- `tests/test_canonical_shell_rc_remediation.py`

**수정**

- `.gitattributes`
- `tc_samples/TC_1.xlsx`의 P0에서 고정한 source cell set
- §3의 YAML 15개

**read-only**

- §1의 kernel·schema·validator·inventory·risk-audit v1 파일
- advisory 74 및 runtime-review 6의 source YAML

`.gitattributes`는 신규 SHA-bound manifest와 verifier를 `text eol=lf`로
고정한다. 다른 rule은 변경하지 않는다.

manifest는 blocker 18행 각각에 다음을 저장한다.

- frozen `row_key`, `source_path`, `step_index`
- frozen `action`, `command_sha256`, `classification`
- source command, frozen grep pattern, predicate kind/value
- expected sentinel
- timeout policy
- 허용 semantic delta field
- source mapping, reconciliation status, provenance mode
- P1 mismatch 뒤 사용자가 compiled-artifact 예외를 승인한 경우에만 그
  exception ID와 bounded provenance debt

같은 manifest의 별도 `runtime_review_dispositions` 배열은 §7의 6행 각각에
다음을 저장한다.

- frozen `row_key`, `action`, `command_sha256`, `classification`
- disposition, reason, evidence

두 배열의 semantic identity SHA-256을 각각 기록한다. raw file SHA와 별도로
canonical JSON serialization SHA를 기록해 parser/render 순서 drift를 차단한다.

### 6.2 Verifier modes

verifier는 두 모드를 제공한다.

```text
verify-worktree
verify-commit --candidate-head <full-lowercase-40-hex-sha>
```

공통 baseline은 frozen HEAD `78b3ac34...`다.

`verify-worktree`:

- commit 전에 현재 YAML을 읽는다.
- `git show 78b3ac3:<path>`의 parsed YAML과 비교한다.
- manifest의 source command, pattern, predicate, row sentinel로 새 command를
  결정론적으로 render하고 candidate `command`가 그 문자열과 정확히 같은지
  확인한다. free-form 수기 변형은 수용하지 않는다.
- 정확한 18 step에서 허용된 `action`, `command`, `expected` delta만 수용한다.
- step 순서·개수, metadata, description, execution fields와 non-target step은
  semantic-equal이어야 한다.

`verify-commit`:

- 사용자 승인으로 corpus commit이 생긴 뒤 실행한다.
- baseline과 candidate commit inventory를 Git object에서 각각 재생한다.
- `(source_path, step_index)`로 692행을 join한다.
- `head_sha`, row-key의 SHA prefix, target 파일의 `source_blob` 변화는
  semantic row 비교에서 제외한다.
- file-level parsed-YAML 비교가 target 파일의 비대상 변경을 별도로 차단한다.

### 6.3 Worktree input binding

`verify-worktree` evidence는 HEAD만 기록해서 GREEN이 될 수 없다. 다음 identity를
실제 candidate input으로 기록한다.

- candidate kind = `worktree`
- candidate HEAD SHA
- allowed-write path별 `{worktree_blob, index_blob, head_blob}`
- 전체 index의 `git ls-files --stage -z` SHA-256 fingerprint
- 시작 시 존재한 비허용 untracked file 전체의
  `{path, file_type, git-hash-object-no-filters}` canonical map과 그 SHA-256
- 실행 중 새로 생기거나 내용 변경이 허용되는 untracked exact path 목록
- parsed worktree candidate inventory의 canonical serialization SHA-256
- source-first post-change isolated export의 canonical inventory SHA-256
- manifest canonical JSON SHA-256
- LF-normalized verifier source SHA-256
- approved spec SHA-256, provenance evidence SHA-256, remediation directive SHA-256

worktree blob은 `git hash-object --no-filters` 규칙으로 실제 worktree bytes를
결속한다. 신규 untracked 파일의 index/head blob은 명시적 `null`이어야 한다.
untracked map은 `git ls-files --others --exclude-standard -z`의 file leaf를
정규화·정렬해 만든다. 기존 untracked backlog의 비허용 파일은 path 추가·삭제뿐
아니라 content blob 또는 file type 변화도 exit 1이다. 승인된 spec과 두
directive는 별도 protected entry로 exact blob을 고정한다.
verifier 시작과 artifact publish 직전에 identity를 다시 계산해 하나라도 변하면
exit 3으로 rollback한다. index fingerprint는 실행 전후 완전히 같아야 하며
staging 변화는 허용하지 않는다.

`verify-commit`은 candidate kind = `commit`, candidate full SHA와 Git object
inventory SHA를 기록한다. 두 mode artifact를 서로 바꾸어 제시할 수 없다.

### 6.4 v2 output

verifier는 다음 두 파일을 atomic publish한다.

- `shell_rc_remediation_matrix.csv`
- `SUMMARY.md`

최종 누적 경로는
`reports/canonical_shell_rc_remediation/<input_digest_16>/`이며 child set은 위
두 파일만 허용한다. `input_digest_16`은 baseline inventory, candidate
inventory, allowed-path blob map, untracked invariant map, manifest semantic
SHA, post-change isolated export inventory SHA, verifier normalized SHA,
approved spec SHA, provenance evidence SHA, remediation directive SHA의
canonical 결합 SHA-256 앞 16자리다. 이 경로가 Git ignore 대상이 아니면
publish 전에 STOP한다.

각 독립 실행은
`reports/canonical_shell_rc_remediation/.staging/<run_nonce>/`의 서로 다른
ignored directory에 먼저 기록한다. 각 staging child set도 CSV/SUMMARY
2개뿐이다. CSV와 SUMMARY는 UTF-8/LF, 고정 column·row·section 순서로
직렬화하며 timestamp, absolute path, staging path, mtime을 포함하지 않는다.
두 staging 결과의 byte identity를 확인한 뒤 한 세트만 final digest
directory로 atomic rename하고 staging을 제거한다. final directory가 이미
존재하면 기존 두 파일과 byte identity가 확인될 때만 GREEN이며 overwrite하지
않는다.

성공 시 필수 수치는 다음과 같다.

| 지표 | 기대값 |
|---|---:|
| baseline rows | 692 |
| candidate rows | 692 |
| remediated target rows | 18 |
| unresolved cutover blockers | 0 |
| non-target rows | 674 |
| non-target semantic delta | 0 |
| advisory rows carried unchanged | 74 |
| runtime-review source rows carried unchanged | 6 |

18행은 `REMEDIATED_EXPLICIT_PREDICATE`로 기록한다. 674행은 frozen v1의
classification, reason code, command semantics를 유지한다.

exit contract:

- `0`: 모든 acceptance check GREEN
- `1`: 검증 가능한 계약 위반
- `2`: manifest, SHA, path, mode 등 입력 무효
- `3`: Git, YAML parse, filesystem 또는 publish 인프라 실패

exit 1은 판정 evidence를 남긴다. exit 2/3은 staging directory를 폐기하고
완성 artifact처럼 보이는 최종 파일을 남기지 않는다.

두 독립 output directory에서 CSV와 SUMMARY가 각각 byte-identical이어야 한다.

### 6.5 Frozen v1 preservation

기존 v1 script, policy 및 baseline Git object는 수정하지 않는다. v2 verifier는
v1을 대체하지 않고 baseline으로 소비한다.

다음을 모두 확인한다.

- risk-audit script SHA-256 불변
- policy v1 SHA-256 불변
- `--head 78b3ac3...` inventory replay SHA-256이
  `b0c555...80b7f`와 일치
- frozen v1 risk matrix 재생 결과가 기존 classification distribution과 일치

v2 artifact는 교정 candidate HEAD와 manifest SHA를 별도로 기록하므로 tracked
policy 안에 candidate commit SHA를 넣는 자기참조가 발생하지 않는다.

---

## 7. Runtime-Review 6 Disposition

이 slice에서는 아래 YAML을 수정하지 않는다. v2 SUMMARY에 처분만 기록한다.

| source path # step | disposition | 근거 / 다음 게이트 |
|---|---|---|
| `ODIN2 - My gallary/functional/photo/GAL_FUNC_05_photo_multi_delete_trash_flow.yaml#23` | `STATIC_ADJUDICATED_REQUIRE_ZERO` | restore teardown 계약과 마지막 `RESTORED` oracle상 no-match는 실패여야 함. 앞의 `NOT_TRASHED`가 `TRASHED` substring을 포함하는 약한 검사는 근거로 사용하지 않음 |
| `ODIN2 - My gallary/functional/photo/GAL_FUNC_12_photo_edit_save_copy.yaml#18` | `STATIC_ADJUDICATED_REQUIRE_ZERO` | 앞 count assertion 이후 copy cleanup no-match는 상태 drift |
| `ODIN2 - My gallary/functional/video/GAL_FUNC_16_video_orientation.yaml#8` | `STATIC_ADJUDICATED_OBSERVE_ONLY` | 참고 로그이며 verdict는 manual step이 담당 |
| `ODIN2 - minifile/functional/ops/MNF_FUNC_12_ops_rename.yaml#22` | `CORPUS_DESIGN_REQUIRED` | `seq` 실패 시 0회 loop가 rc 0, 중간 keyevent 실패도 은폐 가능 |
| `exported_tc1/BUG_25175_LGU_APN_menu.yaml#75` | `DEVICE_EVIDENCE_REQUIRED` | 성공한 reboot의 ADB transport 종료 rc가 환경 종속 |
| `exported_tc1/BUG_5426_airplane_reboot_apn.yaml#15` | `DEVICE_EVIDENCE_REQUIRED` | `logcat -c` 뒤 reboot transport 종료 rc가 환경 종속 |

집계는 static 3, corpus-design 1, device-evidence 2다. 실제 단말 관찰 전
`runtime PASS`로 표현하지 않는다.

---

## 8. TDD and Acceptance Gates

### Gate 0 — Written design review

- 이 문서를 사용자가 리뷰·승인
- 구현 파일 변경 0

### Gate 0.5 — Provenance reconnaissance directive

서면 spec 승인 후 P0/P1만 수행하는 host-only directive를 만들고 사용자
dispatch 승인을 받는다. 이 directive는 workbook/YAML 편집 권한을 주지 않는다.
최소 다음 값을 고정한다.

- provenance directive ID와 host-only Tier 1
- approved spec path, SHA-256, worktree blob
- entry HEAD와 `origin/master...HEAD`
- 전체 index fingerprint
- 기존 비허용 untracked map SHA와 protected spec/directive blob
- workbook path/SHA/Git blob과 source sheets
- exporter 코드 SHA, exact read-only/dry-run argv, temporary output root
- frozen inventory/risk policy/risk audit identity
- exact allowed commands와 provenance evidence path
- repo의 workbook/YAML/source write path는 빈 집합
- staging/commit/push/device 금지

provenance directive SHA-256과 approved spec SHA-256 중 하나라도 dispatch
이후 달라지면 P0/P1을 시작하지 않고 STOP한다.

### Gate P — Provenance

- §4 P0/P1 read-only reconciliation GREEN
- 결과와 evidence SHA를 보고하고 STOP
- 사용자가 P2 source-first 또는 mismatch 후 후속 방향을 별도로 결정
- 결정 전 workbook/YAML 편집 0

### Gate 0.75 — Remediation execution directive

P2 결정 뒤 exact workbook cell set과 구현 경계가 확정됐을 때만 별도 remediation
directive를 작성하고 다시 사용자 dispatch 승인을 받는다. 최소 다음을 고정한다.

- remediation directive ID와 Tier 1
- approved spec, provenance directive, provenance evidence의 exact SHA-256
- entry HEAD/upstream, index fingerprint, full untracked invariant map SHA
- exact allowed-write paths:
  `.gitattributes`, `tc_samples/TC_1.xlsx`의 frozen cell set,
  §3 YAML 15개, §6.1 신규 3파일
- exact allowed commands, RED/GREEN 순서, verifier output contract
- staging/commit/push/device 금지

remediation directive SHA-256, approved spec SHA-256, provenance evidence
SHA-256 중 하나라도 dispatch 이후 달라지면 Gate 1을 시작하지 않고 STOP한다.

### Gate 1 — RED

RED는 두 층으로 나눈다.

**Gate 1A — unit/adversarial RED**

verifier의 아직 존재하지 않는 pure predicate oracle, renderer, manifest validator,
publisher API를 import/call해 실패를 관찰한다. 최소 다음 적대 테스트를 먼저
추가한다.

1. source rc nonzero이면 sentinel 부재
2. grep rc > 1이면 sentinel 부재
3. empty/non-decimal count이면 sentinel 부재
4. `EQ_0`: 0만 성공, 1/2 실패
5. `EQ_1`: 1만 성공, 0/2 실패
6. `LE_1`: 0/1 성공, 2 실패
7. row-specific sentinel 중복 또는 계산값 불일치 거부
8. manifest target 누락·중복·path traversal 거부
9. target 외 metadata/step 변경 거부
10. target step description 또는 execution field 변경 거부
11. frozen v1 script/policy SHA drift 거부
12. 674 non-target row 중 1행 command/action/expected drift 거부
13. P1/P2 provenance가 없는 target 거부
14. partial publish 또는 독립 재실행 byte 차이 거부
15. initial stale-temp cleanup rc nonzero이면 source 미실행·sentinel 부재
16. final cleanup rc nonzero이면 sentinel 부재
17. source/grep/count/predicate/cleanup 실패의 diagnostic type이 서로 구분됨
18. canonical mock ADB는 `rc + sentinel`을, legacy mock ADB는
    `sentinel-only`를 판정
19. canonical timeout `30.0`, legacy timeout `30`, target timeout field delta 0
20. renderer 결과와 target command의 byte-for-byte equality

Gate 1A의 RED는 production YAML 상태에 의존하지 않는다. 실패 원인은 API
미구현 또는 의도적으로 주입한 위반이어야 한다.

**Gate 1B — end-to-end characterization RED**

Gate 1A의 최소 API가 GREEN이 된 뒤 frozen target YAML을 verifier에 넣는다.
정확한 18행이 legacy command shape라 거부되고, 나머지 674행은 delta 0이어야
한다. 여기서만 RED 원인이 production YAML의 legacy command shape다.

runner/schema를 수정해 RED를 피하지 않는다.

### Gate 2 — GREEN implementation

- manifest와 verifier를 최소 구현
- source-first 15행은 P0 exact workbook cell을 먼저 교정하고, P1과 같은
  exporter bytes/argv로 격리 export한 결과에서 mapped step만 derived YAML에
  반영
- local/manual 3행은 source mapping대로 YAML을 직접 교정
- exact YAML 15개에서 합계 exact 18 step만 교정
- 15개 기존 `shell`을 `verify_shell`로 전환
- 기존 `verify_shell` 3개는 action 유지
- sentinel 및 fail-closed command contract 적용

수정된 workbook이 기존 producer 계약으로 §5 command를 재생하지 못하면
compiled YAML을 독립 수기 보정하지 않고 STOP한다. 이 경우 producer reconcile은
별도 설계·승인 범위다.

### Gate 3 — Host verification

- target YAML 15/15 `validate PASS`
- `exported_ss_call/`, `ODIN2 - My gallary/functional/photo/`,
  `ODIN2 - minifile/functional/trash/`에서 target 15개를 포함한 전체 YAML
  `validate PASS`
- remediation tests 전부 통과
- full `pytest tests/` 통과
- 실행 직전 수집한 baseline nodeid loss 0
- P0 workbook cell map 15/15와 P1 isolated replay evidence가 directive의
  frozen identity와 일치
- source-first인 경우 workbook의 허용 cell만 변경되고, 비대상
  value/formula/style 및 sheet topology delta 0
- workbook candidate raw SHA-256, Git blob, exact changed-cell map 기록
- 수정된 workbook을 P1과 같은 exporter SHA/argv로 다시 isolated export
- post-change export target 15행이 candidate YAML의 mapped
  `action/command/expected`와 exact semantic-equal
- P1 pre-change export 대 post-change export의 mapped non-target semantic
  delta 0
- post-change exporter SHA, argv, workbook candidate blob, isolated output
  canonical inventory SHA를 v2 evidence에 결속
- `.gitattributes`가 manifest와 verifier 두 경로만 `text eol=lf`로 고정
- §1 read-only 파일 SHA-256 전부 불변
- v1 replay 불변
- `verify-worktree` exit 0
- `verify-worktree` bundle의 candidate kind, per-path
  `{worktree_blob,index_blob,head_blob}`, index fingerprint, candidate inventory
  SHA가 재계산값과 일치
- 기존 비허용 untracked file의 path/file-type/content map은 pre/post 동일하고,
  허용 신규 untracked path 외 add/remove/overwrite 0
- 독립 2회 v2 artifact byte-identical
- 두 output root가 exact digest 경로이고 각 child set이 CSV/SUMMARY 2개뿐이며
  해당 root가 Git ignore 대상
- 정확한 allowed-write set 외 tracked delta 0
- pre/post untracked 집합에서 예상한 신규 3파일 외 증감 0
- `untracked_contamination_scan.py`는 nonblank exact `--protected`와 exact
  `--allow`를 사용해 exit 0

Gate 3 GREEN 뒤에도 `runtime PASS`를 주장하지 않는다.

### Gate 4 — STOP before commit

host 결과와 exact diff를 보고하고 STOP한다. commit은 사용자 별도 승인이다.

### Gate 5 — Post-commit v2 evidence

사용자가 corpus commit을 승인한 경우에만:

1. 생성된 full SHA를 `verify-commit --candidate-head`에 전달
2. tracked/staged clean 확인
3. v2 matrix/SUMMARY 독립 2회 byte identity 확인
4. commit의 workbook을 동일 exporter SHA/argv로 isolated re-export해 target
   15행 equality와 non-target delta 0 재확인
5. §6.4 수치 확인
6. 결과 보고 후 device·push 전에 다시 STOP

candidate SHA는 manifest에 사전 내장하지 않으므로 별도 evidence commit이
필수는 아니다. 결과 문서를 tracked artifact로 승격할지는 별도 승인 범위다.

---

## 9. Device Follow-up

현재 설계·host 구현에는 단말이 필요 없다.

host freeze 후 별도 Tier 2 승인으로만 다음을 수행한다.

- SeniorShield 16행: 앱과 precondition이 준비된 serial-pinned 대상 단말
- ODIN2 Gallery/Minifile 2행: 해당 앱이 준비된 ODIN2 단말
- 각 술어에 대해 0/1/2 count와 source-error synthetic truth table
- 실제 TC legacy-explicit 대 canonical-default differential
- runtime-review reboot 2건은 해당 TC의 대상 단말에서 rc/stderr/timeout/
  reconnect를 별도 측정

임의로 연결된 단말 한 대는 충분한 증거가 아니다.

---

## 10. Tier and STOP Rules

| 구간 | Tier | 허용 범위 |
|---|---|---|
| 본 문서 | Tier 0 design | spec 1파일 |
| host remediation | Tier 1 | 신규 verifier/manifest/test + `.gitattributes` + P0 exact workbook cells + exact YAML 15 |
| device differential | Tier 2 | 별도 serial-pinned 승인 |
| commit / push | hard gate | 각각 별도 사용자 승인 |

다음 중 하나가 발생하면 즉시 STOP한다.

- P1/P2 provenance 미결정
- workbook 비대상 cell/formula/style 또는 sheet topology delta
- target 18 또는 YAML 15의 집합 불일치
- manifest blocker 18 또는 runtime-review disposition 6의 semantic identity drift
- advisory 74 또는 runtime-review 6 command 변경
- 비대상 YAML semantic delta
- 기존 action으로 fail-closed 계약 표현 불가
- kernel/schema/validator/inventory/risk-audit v1 hash 변화
- blocker 잔존, 신규 blocker/advisory/runtime-review 발생
- validate, pytest, nodeid, 결정론 또는 오염 게이트 RED
- 단말 증거가 있어야만 host 판정을 진행할 수 있는 상황
- staging, commit, push 또는 device 권한 필요

---

## 11. Rejected Alternatives

### Typed stdout predicate

`verify_shell.stdout_assert: {type: integer, op: eq, value: 0}` 같은 계약은
장기적으로 가장 명확하다. 그러나 schema·normalizer·validator·loader·runner·
producer·tests를 같은 slice에서 정렬해야 한다. advisory 74를 다룰 별도 contract
slice 후보이며 이번 18행 교정에는 과도하다.

### `allowed_exit_codes`

grep rc 1을 허용해도 source failure와 no-match를 구분하지 못하고 `EQ_1`/`LE_1`
cardinality를 집행하지 못한다. false GREEN 가능성 때문에 채택하지 않는다.

### Exact-row preflight denylist

canonical 실행을 즉시 차단하는 containment는 가능하지만 assertion 결함을
교정하지 않는다. 이미 exact target과 bounded corpus patch가 가능하므로
채택하지 않는다.
