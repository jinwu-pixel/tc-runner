# HANDOFF 2026-07-28 — Shell RC Blocker P0/P1 Provenance Reconnaissance

> **DISPATCH_STATUS: NOT_AUTHORIZED**
>
> 이 문서는 실행 지시서의 최종 초안이다. 파일 작성 승인은 받았지만 P0/P1
> 실행 승인과 design Gate 0 서면 승인은 아직 받지 않았다. 사용자가 §0의
> affirmative tokens와 external dispatch envelope를 exact하게 승인하기
> 전에는 §3 이후 preflight/P0/P1 operation을 실행하지 않는다. directive
> 작성 완료를 위한 read-only syntax/hash/Git 검증은 이 금지의 대상이 아니다.

**Directive ID:** `RB-20260728-shellrc-p0p1`

**Tier:** host-only Tier 1 reconnaissance

**역할:** Codex = 실행·evidence 작성 / Claude = 독립 재검증·P2 제안 /
사용자 = dispatch·P2·remediation 최종 승인

**방향 승인·Gate 0 서면 리뷰 대기 설계:**
`docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md`

**목표:** tracked workbook `tc_samples/TC_1.xlsx`의 `SS-TC 0`·`SS-TC 1`
source row와 shell-RC blocker 15개 step의 관계를 정확히 복원하고, 현재 public
`export-mmi` producer가 그 관계를 재생하는지 read-only/isolated 방식으로
측정한다.

**이번 지시서가 허용하지 않는 것:** workbook·YAML·Python source 수정,
remediation 구현, canonical producer harness 신규 작성, device/ADB, network,
dependency install, staging, commit, push.

모든 결과는 §8에서 STOP한다. exit 0도 P2 또는 remediation 착수 권한이 아니다.

---

## 0. External Dispatch Envelope

directive는 자기 SHA-256을 본문에 넣을 수 없다. 사용자의 후속 imperative
dispatch 메시지가 다음 세 affirmative token과 여섯 identity를 모두 exact하게
포함해야 실행 권한이 성립한다.

```text
SPEC_REVIEW_APPROVED: 492b718d4dfc3713f9c78c362c3db38af4e348336df81917aa7991ee145aaebf
AUTHORIZE_EXECUTION: RB-20260728-shellrc-p0p1
CAPSULE_SHA256: <DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>
```

| identity | dispatch가 고정할 값 |
|---|---|
| directive raw SHA-256 | 작성 완료 보고의 exact 값 |
| directive `git hash-object --no-filters` blob | 작성 완료 보고의 exact 값 |
| spec raw SHA-256 | `492b718d4dfc3713f9c78c362c3db38af4e348336df81917aa7991ee145aaebf` |
| spec `git hash-object --no-filters` blob | `4db31884e55f1c18dbfd53edd090da88d9f8b51e` |
| capsule generator raw SHA-256 | `45a1a0ebc3fdc89691f6b3106fede0771ea376a8f132866899bca655289db6bd` |
| capsule generator `git hash-object --no-filters` blob | `db170b307a323e861b8a3fc7d29ef743b109197e` |

위 token 또는 identity를 단순 인용·질문·리뷰 맥락에 넣는 것은 dispatch가
아니다. 실행 명령의 뜻으로 세 token을 명시하고 위 identity를 모두 고정해야
한다. `CAPSULE_SHA256`은 lowercase 64-hex이고
`C:\tmp\tc-runner-dispatch-capsules\<CAPSULE_SHA256>.json`을 유일한 capsule
경로로 파생한다. caller-supplied capsule path는 받지 않는다. 사용자가 “진행”만
말하거나 하나라도 누락되거나 재계산값과 다르면
dispatch가 아니며 어떤 preflight도 시작하지 않는다. dispatch 뒤 live
identity mismatch가 발견될 때만 exit 2로 STOP한다.

---

## 1. Content Invariants and External Entry Capsule

### 1.1 Git and workspace

repo-state observation은 directive 본문에 literal로 넣지 않는다. dispatch 직전
`scripts/dispatch_capsule.py capture`가 두 번의 동일한 read-only snapshot 뒤
발행한 external capsule이 유일한 entry source다. capsule은 repo 밖
`C:\tmp\tc-runner-dispatch-capsules/<lowercase-sha256>.json`의 ordinary file이고
자기 SHA/path field를 payload 안에 넣지 않는다. exact schema는 다음과 같다.

```text
capsule_type = "tc-runner.dispatch-entry"
schema_version = 2
ttl_seconds = 1800
directive_id = "RB-20260728-shellrc-p0p1"
issued_at_epoch_s / expires_at_epoch_s
repo {
  root, upstream_ref, head_sha, upstream_sha,
  ahead, behind, tracked_clean, staged_clean
}
index { entry_count, raw_stage_z_sha256 }
untracked / ignored {
  count, canonical_json_sha256, excluded_paths = []
}
module_roots = [ exactly 1 element {
  entry_bytes, entry_relpath, entry_sha256,
  package_name = "@oai/artifact-tool",
  package_version, root_path
} ]
identities {
  directive / spec / generator {
    path, raw_sha256, git_blob_no_filters
  }
}
```

`module_roots`는 §1.4 module route의 환경 관측이다. capture가
`--module-root <node_modules 절대경로> --module-package @oai/artifact-tool`
쌍으로 직접 측정한다: `root_path`는 resolve된 절대경로의 `/` 구분 표기,
`package_version`은 해당 package.json의 `version`, `entry_relpath`는
`exports["."]`에서 leading `./`를 제거한 상대경로, `entry_bytes`/`entry_sha256`은
entry file raw bytes의 측정값이다. 경로는 환경 관측이므로 directive 본문에
literal로 넣지 않는다. 이 directive의 dispatch에는 원소가 정확히 1개여야 하며
`package_version`은 floor `2.8.6` 이상이어야 한다.

`repo.root`는 `C:/Users/momen/Projects/tc-runner`,
`repo.upstream_ref`는 `origin/master`, HEAD/upstream은 동일한 lowercase
full OID, ahead/behind는 `0/0`, tracked/staged는 모두 true여야 한다. capsule
발행 시각은 두 snapshot과 map 측정이 끝난 뒤 정하고
`expires_at_epoch_s - issued_at_epoch_s == 1800`이어야 한다. entry write 전에는
`issued_at_epoch_s <= now < expires_at_epoch_s`를 두 번 검사한다. campaign
진입 뒤에는 capsule bytes와 live state를 계속 검사하지만, 진행 중 TTL 경과만으로
이미 승인된 campaign을 실패시키지 않는다.

untracked backlog는 경로 집합만 보존하면 안 된다. generator와 executor는 다음
동일 계약으로 content map을 재계산한다.

1. `git -c core.quotepath=false ls-files --others --exclude-standard -z`
   결과를 UTF-8 path로 해석한다.
2. 제외 path는 없다. capsule의 `excluded_paths`는 정확히 빈 배열이다.
3. 각 path는 모두 `Get-Item -Force` 기준 `PSIsContainer == false`이고
   `FileAttributes.ReparsePoint`가 없어야 한다. 하나라도 아니면 exit 2다.
   `file_type` literal은 정확히 `"file"`이며, 각 leaf마다
   `{file_type:"file", git_hash_object_no_filters, path}`를 만든다.
4. path는 `/` 구분자를 사용하고 case-fold하지 않는다.
5. UTF-8 path bytes 순으로 정렬한다.
6. key 순서가 위와 같은 compact JSON array로 직렬화한다.
   `ensure_ascii=false`, 공백·trailing LF 없음.
7. 그 JSON bytes의 SHA-256을 계산한다.

ignored file도 별도 canonical map으로 freeze한다. 동일 `{file_type:"file",
git_hash_object_no_filters,path}`/UTF-8 path sort/compact JSON 규칙을 쓰되 path
source는
`git -c core.quotepath=false ls-files --others --ignored --exclude-standard -z`다.
entry에는 evidence final/tmp가 존재하지 않는다.

spec, directive, generator는 tracked identity이며 capsule `identities`와 §0의
각 raw SHA/blob으로 이중 보호한다.
비허용 untracked file의 add/remove/content/file-type 변화는 exit 2다. mismatch를
현재 상태로 재-freeze하거나 파일을 원복·삭제하는 판단은 Codex가 하지 않는다.

### 1.2 Workbook and frozen audit

| 항목 | freeze 값 |
|---|---|
| workbook path | `tc_samples/TC_1.xlsx` |
| workbook raw SHA-256 | `160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa` |
| workbook Git blob | `24593d11dd80a2b3711655bd0c5216ee9157dedc` |
| required sheets | `SS-TC 0`, `SS-TC 1` |
| frozen inventory HEAD | `78b3ac34e9f8bacabe926172dd199342b7eb58c5` |
| frozen inventory CSV | `reports/_codex_shell_inventory_v3_277e_a/66951de779d78dc6/shell_rc_inventory.csv` |
| frozen inventory CSV SHA-256 | `b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f` |
| frozen risk matrix | `reports/_codex_shell_rc_risk_3d99_a/c60be6036584ce8f/shell_rc_risk_matrix.csv` |
| frozen risk matrix SHA-256 | `81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4` |
| risk policy v1 | `scripts/canonical_shell_rc_risk_policy_v1.json` |
| risk policy v1 SHA-256 | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` |
| risk audit script | `scripts/canonical_shell_rc_risk_audit.py` |
| risk audit script SHA-256 | `3d9903854a8c4d4cbb64edec4b412563a3ac4626f0ad25cf2934d06d44e61d34` |

workbook의 `LastWriteTimeUtc.Ticks`는 entry에서 관찰해 evidence에 기록하고
종료 시 같은 값이어야 한다. 저자 세션의 mtime을 freeze 값으로 사용하지 않는다.

### 1.3 Producer actor set

HEAD 고정만으로도 tracked code identity가 정해지지만, evidence 독립 감사를 위해
아래 raw SHA-256도 모두 재확인한다.

| path | SHA-256 |
|---|---|
| `src/cli.py` | `c27fa7d5c6c4bd9f956238ef0008990e667989949bbc5743d6a37347ee71a5b0` |
| `src/execution_contract.py` | `b5a8601a8efd7008752f5c1b50134066082a64f8b976f1fb2270fcc76f1b21eb` |
| `tc_step_schema.json` | `7ec8a76766bec3e8ba18cdd8deedb478024edb2878ee83190907125669cc7059` |
| `src/mmi_converter/__init__.py` | `164bb0d498d3a7ec2172196882f2ed566fc0578c924d1445b0c4af390ca4f4a4` |
| `src/mmi_converter/classifier.py` | `f795a9e88f8f6b67a9b2358a5adf5edeccc4ba48bae2e5d1bd2153de0f0f1753` |
| `src/mmi_converter/compiler.py` | `52985f0b008d23a65ca7168777e23590ddd4b20eb22f37f1f8eede3d6c313eec` |
| `src/mmi_converter/expected_parser.py` | `17b42361351d54920c89851acac473293eff6ad2a75d3ba90854926d2e98375c` |
| `src/mmi_converter/exporter.py` | `3090015d4a045d61c0f382cc21dceffd3a13c7c8b1950119b9396e5bb18bbac6` |
| `src/mmi_converter/models.py` | `6240036685e4a64a51c16cc5a576b268c1eba3aeb55031b83ce097882a7a7227` |
| `src/mmi_converter/procedure_parser.py` | `62c66ef7e941a1a3eaeb3b7a7abe14c8f020923e33287a589f27eb1908d6618a` |
| `src/mmi_converter/row_loader.py` | `38cb421b9f7f6282df401c84dc7b06837ea61cd70b22d17547e9ed62498c39d7` |
| `src/mmi_converter/service.py` | `83015f8c79ade724ec7aa619a2fff82945192ecb41b479d344b2b9c404729f79` |
| `src/mmi_converter/shell_action_map.py` | `479b846a48bba0771d37af924ae8a38314c83033f05ef0993598f85bb7cb77be` |
| `src/mmi_converter/step_classifier.py` | `1c73bb15df6981ab9d6cc68615db0decfdaa70259c30fbdb2c5e26e89fd1f90f` |

### 1.4 Toolchain

| tool | freeze / gate |
|---|---|
| Python | `3.12.2` |
| openpyxl used internally by repo loader | `3.1.5` |
| PyYAML | `6.0.3` |
| Node | `v24.14.1` |
| Windows PowerShell | `5.1.26100.8875`, `PSEdition=Desktop` |
| process text encoding | console input/output과 `$OutputEncoding`, `PYTHONIOENCODING` 모두 UTF-8 no BOM |
| `@oai/artifact-tool` | capsule `module_roots[0]` 결박: `package_version` capture 값 exact + floor `2.8.6`, entry raw SHA-256 exact. 모듈 부재·floor 미달 = exit 3, capsule-vs-live 불일치 = exit 2 |

P0 spreadsheet inspection은 `@oai/artifact-tool`만 사용한다. runtime dependency
loader 또는 formula/style visibility가 없으면 exit 3이다. 이 directive가
허용하는 module route는 `node_repl`의 existing bare-import search root와, §3
module-route 절차가 negative-control(Appendix R) `EXPECTED_FAIL` 이후 capsule
`module_roots[0].root_path` 하나를 `js_add_node_module_dir`로 최대 1회 추가하는
것뿐이다. 임의 경로 추가, 조건 밖 반복 호출, junction, 그 외 임의 filesystem
resolution, npm/install은 승인하지 않는다. 버전 게이트는 module export가 아니라
capsule에 결박된 package.json `version`으로 판정한다 (2026-07-29 실측: 모듈에
version 계열 export가 없다). route 성립은 node_repl 실세션 probe
MRP-20260729-artifact-tool rev1+rev2 GREEN으로 사전 실증되었다. cold import는
기본 30s 예산에 근접·초과하는 고변동(12.8s~>30s 실측)이므로 Appendix R/A를
제출하는 node_repl 호출은 timeout `>= 300000ms`를 명시해야 한다.
`openpyxl`, ZIP/XML 직접 파싱, Excel GUI, LibreOffice로 대체하지 않는다.
P1의 repo `export-mmi`가 내부적으로 openpyxl을 사용하는 것은 현재 producer
계약의 측정이므로 허용한다.

---

## 2. Exact Write and Command Boundary

### 2.1 Allowed repo writes

source write path는 빈 집합이다. repo 내부에서 허용되는 file write는 ignored
evidence 1파일과 성공·실패 공용 atomic temp sibling뿐이다. 아래 두 directory는
부재할 때만 순서대로 생성할 수 있고 evidence의 `repo_intended_directories`에
기록한다.

```text
reports/canonical_shell_rc_provenance/
reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/
reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/PROVENANCE_EVIDENCE.json
reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/PROVENANCE_EVIDENCE.json.tmp
```

실행 전에 두 경로와 부모 run directory가 모두 없어야 한다. 경로는
`git check-ignore` 결과가 `reports/` rule이어야 한다. 기존 경로를 삭제하거나
덮어쓰지 않는다.

entry preflight가 끝나기 전 발생한 exit 2는 evidence를 만들지 않는다.
preflight GREEN 뒤 Appendix C가 exact bytes로 materialize·hash-verify되어
invocable하고 operation ledger가 append 가능한 이후의 exit 0/1/2/3은
status-bearing evidence를 `.tmp`에 exclusive-create하고 `fsync`한 뒤 final
JSON 이름을 no-overwrite hard link로 publish하고 final bytes/hash를 다시
검증한다.
그 이전 materialization 실패, 이후 operation-ledger append 자체 실패, 또는
assembler 자체 실패는 fileless exit 3이며 console의 exact class/message만
보고한다. exit 3 evidence는 가능한 경우 측정된 부분, exact exception
class/message, 마지막 성공 phase, command log를 보존하되
`PROVENANCE_RECONCILED`로 표기하지 않는다.

### 2.2 Allowed external temporary writes

다음 root 하나만 허용한다.

```text
C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1
```

허용 child:

```text
artifact-tool-work/
artifact-tool-work/p0_workbook.json
artifact-tool-work/p0_workbook.json.tmp
artifact-tool-work/render-SS-TC-0.png
artifact-tool-work/render-SS-TC-0.png.tmp
artifact-tool-work/render-SS-TC-1.png
artifact-tool-work/render-SS-TC-1.png.tmp
analyze_provenance.py
assemble_evidence.py
reconciliation.json
reconciliation.json.tmp
SS-TC-0/
SS-TC-1/
dry-run-SS-TC-0.combined.txt
dry-run-SS-TC-1.combined.txt
export-SS-TC-0.combined.txt
export-SS-TC-1.combined.txt
analyze.combined.txt
operation_log.ndjson
```

temp root가 entry에 이미 존재하면 exit 2다. 삭제·재사용·`--overwrite` 금지다.
실행 뒤에도 temp root를 자동 삭제하지 않고 evidence 재검토용으로 보존한다.

다음 경로는 write root가 아니라 dispatch 전에 이미 존재해야 하는 read-only
input이다.

```text
C:\tmp\tc-runner-dispatch-capsules\<CAPSULE_SHA256>.json
```

lowercase token에서 파생한 exact path만 읽고 생성·수정·mtime 변경·삭제하지
않는다. capsule root와 capsule은 link/junction/reparse point가 아닌 ordinary
directory/file이어야 한다.

### 2.3 Closed tool-call allowlist

허용 경계는 “command family”가 아니라 아래 exact operation 목록이다. 개별
read primitive까지 사후 추정해 “실행 로그”라고 부르지 않는다. executor는
§2.5의 actual phase ledger에 host preflight/materialization과 P0/P1 각 phase의
실측 tool/argv 또는 input SHA, numeric exit 또는 MCP status, observed toolchain,
first failure를 순서대로 append한다. Appendix C 내부 read-only Git은 assembler
자기검증으로 별도 표시한다. 목록 밖 operation이 1개라도 있으면 exit 2다.

1. read-only Git:
   - `git rev-parse --show-toplevel|HEAD|origin/master`
   - `git rev-list --left-right --count origin/master...HEAD`
   - `git status --short`, `git diff --quiet`, `git diff --cached --quiet`
   - `git -c core.quotepath=false ls-files --stage -z`
   - `git -c core.quotepath=false ls-files -z`
   - `git -c core.quotepath=false ls-files --others --exclude-standard -z`
   - `git -c core.quotepath=false ls-files --others --ignored --exclude-standard -z`
   - `git ls-files --error-unmatch -- <exact path>`
   - `git hash-object --no-filters -- <exact path>` 또는 `--stdin-paths`
   - `git check-ignore -v -- <exact evidence path>`
   - 모든 Git process는 `GIT_CONFIG_GLOBAL=NUL`,
     `GIT_CONFIG_SYSTEM=NUL`, `-c core.excludesFile=NUL`을 강제한다.
     user/system config와 global excludes에 따라 capsule map이 달라지는 실행은
     금지한다.
2. PowerShell identity/path primitives:
   `Resolve-Path`, `Test-Path`, `Get-Item`, `Get-ChildItem -LiteralPath`,
   `Get-FileHash -Algorithm SHA256`, `[System.IO.File]` read/hash/write,
   `[System.Diagnostics.Process]`의 위 exact read-only Git 실행,
   `[System.Security.Cryptography.SHA256]`의 canonical map hash,
   `ConvertFrom-Json`의 P0 gate 및 §5.2 identity rehydrate read,
   `ConvertTo-Json`의 ledger line write,
   `New-Item -ItemType Directory`의 §2.1/§2.2 exact parents.
   capsule `module_roots[0]`가 가리키는 외부 package.json/entry file의
   read/hash(§3 module-route fs gate)도 이 read primitive family에 속한다.
   evidence publish에는 PowerShell `Move-Item`/rename을 허용하지 않는다.
   Appendix C 내부의 exact `open(..., "xb")`/flush/`os.fsync`/`os.link`,
   final read/hash 검증, 성공 뒤 temporary unlink만 허용한다.
3. tool-version probes:
   - `venv\Scripts\python.exe -B --version`
   - `venv\Scripts\python.exe -B -c`로 openpyxl/PyYAML exact version 출력만
   - `node --version`
   - `$PSVersionTable`/console encoding read
4. write-0 host preflight에서만 다음 exact capsule verify를 1회 실행한다.
   `venv\Scripts\python.exe -B scripts/dispatch_capsule.py verify --repo
   <resolved-repo> --capsule-sha256 <dispatch-token>
   --expected-directive-id RB-20260728-shellrc-p0p1
   --expected-directive HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md
   --expected-spec
   docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md`.
   `capture`는 이 campaign의 허용 operation이 아니다.
5. module route + Appendix 제출 (모든 node_repl 호출은 timeout `>= 300000ms`
   명시):
   - Appendix R의 exact JavaScript source를 `node_repl.js`에 제출한다
     (negative control). 1차 결과가 import 실패면
     `js_add_node_module_dir`를 capsule `module_roots[0].root_path` exact
     값으로 정확히 1회 호출한 뒤 Appendix R을 다시 제출하며, 2차는 import
     성공이어야 한다 (Appendix R 제출 최대 2회). 1차가 import 성공이면 add를
     생략한다. probe 동적 결과는 §8 완료 보고에 기록한다.
   - Appendix A의 exact JavaScript source 1회를 `node_repl.js`에 제출한다.
   - 각 제출 text의 UTF-8/LF/trailing-LF SHA가 해당 Appendix freeze와 같아야
     한다. capsule 값 이외의 경로 add, 조건 밖 add 반복, junction, npm,
     network, 임의 `.mjs` 실행은 금지한다.
6. Appendix B source를 exact bytes로 external temp
   `analyze_provenance.py`에 생성하고 source SHA를 확인한 뒤 §5.7 exact argv로
   1회 실행한다. 이 script는 stdlib+PyYAML read/analyze 전용이며 `src.*`를
   import하거나 producer를 호출하지 않는다.
7. Appendix C source를 exact bytes로 external temp
   `assemble_evidence.py`에 생성하고 source SHA를 확인한 뒤 §6.3 exact argv로
   정확히 1회 실행한다.
8. `venv\Scripts\python.exe -B -m src.cli export-mmi`의 §5 exact argv 4개.

Appendix source의 외부 temp 생성, evidence `.tmp` exclusive-create와
no-overwrite hard-link publish는 directive 안의 exact bytes/path만 허용한다.
producer flag 변경, custom
canonical harness, arbitrary Python/Node/PowerShell script, ADB, network,
package manager, install, test runner, staging/commit/push는 금지한다.

Python 호출은 항상 `-B`다. repo 안 `__pycache__` 생성은 허용 write가 아니며
발견 시 exit 2다.

### 2.4 Appendix byte materialization

directive raw text를 UTF-8로 읽고 CRLF를 LF로 normalize한 뒤, exact heading
`Appendix A/B/C/R` 바로 다음 동일 언어 code fence를 각각 **정확히 1개** 찾는다.
opening/closing fence는 제외하고 body 마지막에 LF 1개를 붙인 bytes가 heading의
SHA와 같아야 한다.

- A bytes: 파일로 쓰지 않고 `node_repl.js.code`에 그대로 전달
- B bytes: `analyze_provenance.py`를 create-new로 1회 기록
- C bytes: `assemble_evidence.py`를 create-new로 1회 기록
- R bytes: 파일로 쓰지 않고 `node_repl.js.code`에 그대로 전달 (§2.3 item 5,
  최대 2회)

0개/2개 이상 fence, SHA mismatch, 기존 target file은 exit 2다. 수기 재입력,
부분 복사, formatter 적용은 금지한다.

두 file write와 hash 확인이 끝난 직후, P0 전에 다음 exact success row를
append한다. `$AppendixBSha`/`$AppendixCSha`는 방금 materialize한 file의
lowercase SHA다.

```powershell
Add-PhaseRecord ([ordered]@{
    phase = 'APPENDIX_MATERIALIZATION'
    status = 'COMPLETED'
    tool = 'PowerShell'
    cwd = $Repo
    argv = $null
    tool_input_sha256 = $null
    exit = $null
    observed = [ordered]@{
        appendix_b_source_sha256 = $AppendixBSha
        appendix_c_source_sha256 = $AppendixCSha
    }
    error_class = ''
    error_message = ''
})
```

materialization failure는 같은 field 순서로 `status='FAILED'`,
`observed=[ordered]@{}`, `error_class/error_message`를 actual nonempty 값으로
기록하고 즉시 fileless exit 3 STOP한다. Appendix C가 exact hash로 준비되지
않았으므로 evidence를 수기 생성하지 않는다.

### 2.5 Actual phase ledger

host preflight GREEN 뒤 temp root를 만든 즉시, 아래 exact function만 사용해
`operation_log.ndjson`을 create/append한다.

```powershell
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OperationLog = Join-Path $TempRoot 'operation_log.ndjson'
function Add-PhaseRecord(
    [System.Collections.Specialized.OrderedDictionary]$Record
) {
    $Line = ($Record | ConvertTo-Json -Depth 12 -Compress)
    [System.IO.File]::AppendAllText(
        $OperationLog, $Line + "`n", $Utf8NoBom
    )
}
```

각 line의 exact field는 다음과 같다.

```text
phase
status                  # COMPLETED | FAILED
tool
cwd
argv                    # process면 exact array, 아니면 null
tool_input_sha256       # node_repl/Appendix면 exact hash, 아니면 null
exit                    # spawned Python numeric; pre-invocation/control/MCP는 null
observed                # HOST_PREFLIGHT toolchain/identities, 아니면 {}
error_class             # 성공 "", 실패 nonempty
error_message           # 성공 "", 실패 nonempty
```

phase order:

```text
HOST_PREFLIGHT
APPENDIX_MATERIALIZATION
P0_ARTIFACT_CAPTURE
DRY_SS_TC_0
DRY_SS_TC_1
EXPORT_SS_TC_0
EXPORT_SS_TC_1
ANALYZE
```

full measured path는 8행 exact sequence와 전부 `COMPLETED`를 요구한다. P0의
유효한 candidate mismatch는 첫 3행 exact prefix와 전부 `COMPLETED`를 기록한
`measured` path이며 P1을 실행하지 않는다. failure path는 위 sequence의 prefix이고
마지막 1행만 `FAILED`; 성공 phase를 건너뛰거나 failure 뒤 행을 append할 수 없다.
HOST_PREFLIGHT failure는 write 0이므로 ledger/evidence 없이 exit 2다. 각 process의
`$LASTEXITCODE`, node_repl tool status, 실제 argv를 얻은 직후 다음 phase 전에
기록한다. preflight `observed`에는 Python/openpyxl/PyYAML/Node/PowerShell exact
version과 encoding, dispatch capsule payload/token/path, exact verifier
tool/argv/exit, `ttl_valid_before_first_write:true`, 그리고 §3 item 12의
`module_route` object(Appendix R source SHA + capsule `module_roots[0]` 결박
5값 — 결정론 값만)를 반드시 넣는다. probe 동적 결과는 §8 완료 보고 전용이다.
verifier는
write-0에서 실행되지만 성공 뒤 temp root를 만든 직후 이 row에 그대로
지연 기록한다.

spawned process의 `FAILED.exit`은 process 자체 nonzero뿐 아니라 process exit 0
뒤 canonical output 또는 성공 artifact hash I/O가 실패한 경우의 0도 허용한다.
후자는 controller failure이며 `error_class/error_message`가 그 실제 I/O/hash
예외를 보존한다. control/MCP phase의 exit은 성공·실패 모두 `null`이다.

`HOST_PREFLIGHT.observed.toolchain` exact object:

```json
{"console_input":"utf-8","console_output":"utf-8","node":"v24.14.1","openpyxl":"3.1.5","output_encoding":"utf-8","powershell":"5.1.26100.8875","psedition":"Desktop","pyyaml":"6.0.3","python":"3.12.2","pythonhashseed":"0","pythonioencoding":"utf-8"}
```

phase별 identity는 다음 exact contract를 따른다. `cwd`는 모든 phase에서
`C:\Users\momen\Projects\tc-runner`다.

| phase | tool | argv | tool_input_sha256 | observed 필수값 |
|---|---|---|---|---|
| `HOST_PREFLIGHT` | `PowerShell` | `null` | `null` | 위 exact `toolchain`; full `dispatch_capsule`; capsule token/path; exact nested verify tool/argv/exit; TTL bool; `module_route` object; `exit:null` |
| `APPENDIX_MATERIALIZATION` | `PowerShell` | `null` | `null` | `appendix_b_source_sha256`, `appendix_c_source_sha256`; `exit:null` |
| `P0_ARTIFACT_CAPTURE` | `node_repl.js` | `null` | Appendix A source SHA | 성공 시 `p0_workbook_sha256`, `reconciled`, post-P0 input identity 5필드; 실패 시 `{}` |
| dry/export 4개 | resolved `venv\Scripts\python.exe` absolute path | §5.3/§5.4 exact array | `null` | precheck와 launch bool; mismatch면 producer=false, precheck infra면 producer=null/check=false, launch 실패면 producer=true/launch=false |
| `ANALYZE` | resolved `venv\Scripts\python.exe` absolute path | §5.7 exact array | `null` | 위 두 bool + 성공 시 `reconciliation_sha256` |

`APPENDIX_MATERIALIZATION.observed`는 두 source SHA field만 가진 exact object다.
나머지 phase의 `observed`에 추가 측정값을 넣을 수 있으나 object여야 한다.
Appendix C는 이 ledger를 읽어 phase/tool/cwd/argv/input SHA를 template과
대조하며, command log를 사후 합성하지 않는다.

---

## 3. Entry Preflight — Write 0

아래 항목을 모두 read-only로 재계산한다.

1. §0 external envelope의 directive/spec/generator raw SHA와 Git blob,
   lowercase `CAPSULE_SHA256`
2. token에서 파생한 external capsule ordinary-file identity, canonical JSON
   bytes, exact schema와 directive/spec/generator identity binding
3. exact `dispatch_capsule.py verify` exit 0. 이 호출은 TTL을 live-state
   double-snapshot 전후로 검사하고 capsule repo/index/untracked/ignored/identity와
   현재 상태를 비교한다
4. `git rev-parse --show-toplevel`이
   `C:/Users/momen/Projects/tc-runner`와 separator-normalized exact인지
5. workbook tracked identity, raw SHA, Git blob, worktree/index == HEAD
6. workbook mtime-before
7. frozen audit 4개 hash
8. producer actor 14파일 hash
9. Python/openpyxl/PyYAML/Node/PowerShell version과 UTF-8 process encoding
10. evidence/temp 경로 부재와 evidence path ignore rule
11. first write 직전 capsule raw SHA 재검사와
    `issued_at_epoch_s <= now < expires_at_epoch_s`
12. module-route fs gate (`Assert-ModuleRouteBinding`): capsule
    `module_roots`가 정확히 1개 원소이고 `package_name`이
    `@oai/artifact-tool`이며, live filesystem에서 `root_path`가 ordinary
    directory, package.json의 `name`/`version`이 capsule 값과 exact 일치,
    `version`이 floor `2.8.6` 이상, entry file raw bytes/SHA-256이 capsule
    `entry_bytes`/`entry_sha256`과 exact 일치. 모듈 경로/파일 부재·floor
    미달은 exit 3, capsule-vs-live 값 불일치는 exit 2다.
host-side 1~12가 모두 GREEN이기 전에는 temp/evidence directory도 만들지 않는다.
identity/path mismatch는 exit 2다. host preflight GREEN 뒤 exact temp root와
evidence parent만 생성하고, Appendix B/C를 §2.4대로 materialize·hash 확인한다.
그 다음 module-route probe를 수행한다: Appendix R source를 `node_repl.js`에
제출하고 (timeout `>= 300000ms`), import 실패면 `js_add_node_module_dir`를
capsule `module_roots[0].root_path` exact 값으로 정확히 1회 호출한 뒤 Appendix
R을 재제출하며 2차는 import 성공이어야 한다 (실패 = exit 3, P0 row FAILED).
1차 import 성공이면 add를 생략한다. probe의 동적 결과(negative-control 결과,
add 호출 여부, 제출 횟수, 적용 timeout)는 §2.5 ledger가 아니라 §8 완료 보고에
기록한다 — ledger의 `module_route`는 capsule 결박값과 Appendix R source SHA만
담는 결정론 object다. probe GREEN 뒤 Appendix A를 제출한다 (timeout
`>= 300000ms`). Appendix A import, API/formula/style/region/render visibility
측정 불능은 post-preflight exit 3이며 failure evidence를 남긴다.

temp root 생성 직후 §2.5 writer를 initialize하고 아래 exact 첫 row를 append한다.

```powershell
$env:PYTHONHASHSEED = '0'
$env:PYTHONIOENCODING = 'utf-8'
Add-PhaseRecord ([ordered]@{
    phase = 'HOST_PREFLIGHT'
    status = 'COMPLETED'
    tool = 'PowerShell'
    cwd = $Repo
    argv = $null
    tool_input_sha256 = $null
    exit = $null
    observed = [ordered]@{
        dispatch_capsule = $DispatchCapsule
        dispatch_capsule_path = $CapsulePath.Replace('\', '/')
        dispatch_capsule_sha256 = $CapsuleSha256
        capsule_verify = [ordered]@{
            tool = $Python
            argv = @($CapsuleVerifyArgs)
            exit = $CapsuleVerifyExit
        }
        ttl_valid_before_first_write = $true
        module_route = [ordered]@{
            probe_source_sha256 =
                'd57734b2131cfaf548c28c68d1febbbada6236e49ed8aa21474351f3067f7e64'
            package_name =
                [string]$DispatchCapsule.module_roots[0].package_name
            package_version =
                [string]$DispatchCapsule.module_roots[0].package_version
            root_path = [string]$DispatchCapsule.module_roots[0].root_path
            entry_bytes =
                [long]$DispatchCapsule.module_roots[0].entry_bytes
            entry_sha256 =
                [string]$DispatchCapsule.module_roots[0].entry_sha256
        }
        toolchain = [ordered]@{
            console_input = 'utf-8'
            console_output = 'utf-8'
            node = 'v24.14.1'
            openpyxl = '3.1.5'
            output_encoding = 'utf-8'
            powershell = '5.1.26100.8875'
            psedition = 'Desktop'
            pyyaml = '6.0.3'
            python = '3.12.2'
            pythonhashseed = '0'
            pythonioencoding = 'utf-8'
        }
    }
    error_class = ''
    error_message = ''
})
```

---

## 4. P0 — Workbook Identity and Exact Row Mapping

### 4.1 Known target manifest

tracked YAML에는 structured `source_row`가 없다. physical row는 아래 표에서
추정하지 않고 P0가 exact하게 도출한다.

| tracked YAML | blocker step | sheet | physical row |
|---|---:|---|---|
| `exported_ss_call/SS_TC01_permission_denied.yaml` | 10, 11 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC02_permission_allow_idle.yaml` | 11 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC03_ringing_permission.yaml` | 15 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml` | 18 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC05_boundary_values.yaml` | 9 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC06_missed_rejected.yaml` | 10, 11 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml` | 9 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC09_offhook_permission_banking.yaml` | 20 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC0_P0_endcall_crash.yaml` | 15 | `SS-TC 0` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC10_permission_toggle.yaml` | 24 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC11_multi_subscription.yaml` | 20, 21 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |
| `exported_ss_call/SS_TC12_legacy_path.yaml` | 19 | `SS-TC 1` | YAML에 없음 — P0 unique join으로만 측정 |

Acceptance cardinality:

- target step mapping = 15
- distinct tracked YAML / workbook row mapping = 12
- step distribution = `SS-TC 0: 1`, `SS-TC 1: 14`
- distinct row distribution = `SS-TC 0: 1`, `SS-TC 1: 11`
- `SS_TC01`, `SS_TC06`, `SS_TC11`의 두 blocker step은 각자 같은 source row
- 각 tracked YAML의 source row candidate count = 정확히 1
- 15개 `(yaml_path, blocker_step_index)`는 모두 unique이고 step index는 1-based
- 12개 `(yaml_path, sheet, physical_row)`와 12개 `(sheet, physical_row)`는
  각각 unique
- 동일 row가 두 target step으로 fan-out하는 YAML은 위 3개뿐

0개 또는 2개 이상 candidate는 exit 1이다. filename hash나 행 순서만으로
source row를 추정하지 않는다.

각 tracked YAML의 `metadata.source`는 anchored exact grammar
`^TC_1\.xlsx / (SS-TC 0|SS-TC 1)$`를 만족해야 한다. case-fold, heuristic split,
basename fallback은 금지한다. `git ls-files` 기준 basename `TC_1.xlsx`인 tracked
file은 정확히 1개이고 resolved path가 `tc_samples/TC_1.xlsx`여야 한다.

### 4.2 Artifact-tool inspection contract

workbook은 Appendix A의 exact `FileBlob.load` +
`SpreadsheetFile.importXlsx`로 import만 하고 export/save하지 않는다. Appendix A는
각 sheet에 대해 다음 exact read를 수행한다.

- `worksheets.getItem(sheetName).getUsedRange()`
- used range의 direct `values`, `formulas`, `displayFormulas`
- header·target·carry-forward exact cell 각각의
  `workbook.inspect({kind:"region"|"computedStyle", ...})`
- `workbook.render({sheetName, range:usedAddress, scale:1, format:"png"})`

used range address, matrix shape, exact relevant-cell raw inspect NDJSON 및 SHA,
render options/range와 PNG SHA를 기록한다. inspect result가 truncation flag/marker를
보이거나 configured maxChars 경계에 도달하면 exit 3이다. direct API property
또는 deterministic formula/style/region visibility가 없으면 임의 API로
보완하지 않고 exit 3이다.

1. workbook sheet 목록에서 `SS-TC 0`, `SS-TC 1` 존재를 exact 확인한다.
2. 각 sheet used range의 실제 전체 column width × physical row 1~10의
   values/formulas를 사용해 header row를 찾는다. `A1:Z10` 고정이나 Z 이후
   column 배제는 금지한다.
3. repo `row_loader.py`의 header regex와 동일한 의미로 다음 7개 column을
   exact cell address에 매핑한다.
   - `no`
   - `feature_name`
   - `functionality`
   - `precondition`
   - `procedure`
   - `expected`
   - `priority`
4. cell에 formula가 존재하면 loader-equivalent 값은 formula text,
   아니면 direct `values` 값이다. `displayFormulas`는 이름 그대로 별도
   `display_formula_view` 증거이며 cached/displayed value라고 과대 표기하지
   않는다. 별도 supported API가 없으므로 `cached_or_displayed_value=null`로
   기록한다. 이 값에 `_normalize_header`, `_safe_str` 의미를 exact 재현한다.
   direct value는 `null|string|boolean|safe integer`만 지원한다. boolean은
   Python `True`/`False`, safe integer는 decimal string으로 변환하며 float,
   Date/object 등 Python `str()`과 exact 동등성을 보장할 수 없는 타입은 exit 3다.
5. artifact-tool이 읽은 값으로 loader의 carry-forward 규칙을 재현해 각
   physical row의 effective `feature_name`과 `functionality`를 계산한다.
6. `MMIRow.tc_name` 규칙을 그대로 적용한다. `base_no`는 trim된 `no` 또는
   `"ROW" + row_index`, `feature`는 trim된 `feature_name` 또는 `"UNNAMED"`의
   whitespace를 underscore로 바꾼 값이며 결과는
   `base_no + "_" + feature`다.
7. Appendix A는 frozen target manifest의 `yaml_tc_name`·declared sheet와
   workbook-derived name을 exact join한다. tracked YAML의 parsed
   `tc_name`·source text는 Appendix B가 P1 acceptance 전에 별도로 exact
   대조한다.
8. unique join이 성립한 12 physical row의 7개 semantic cell을 inspect한다.
9. 7개 semantic header cell도 target cell과 같은 full evidence를 가진다.
10. carry-forward가 적용된 두 column은 nearest preceding nonblank anchor부터
   target row까지의 모든 관련 cell도 기록한다.
11. 각 관련 cell의 raw `region` inspect NDJSON을 merge/topology 검토용으로
   기록한다. 이 reconnaissance는 undocumented field를 추측해 별도
   `merged_ranges` 구조를 만들거나 merge membership을 과대 주장하지 않는다.
12. header·target·carry-forward 관련 cell마다 다음을 기록한다.
    - A1 coordinate
    - artifact-tool direct `values` value
    - formula
    - display formula view
    - cached/displayed value (`null` = API 미제공)
    - exact computedStyle inspect record/NDJSON slice와 raw SHA-256
    - exact region inspect record/NDJSON slice와 raw SHA-256
      (merge/topology의 raw evidence이며 membership 판정 주장은 아님)
13. render range는 각 sheet의 exact used range, options는 위 고정값이다.
    workbook bytes는 저장·export하지 않는다.

P0에서 standalone `load_mmi_rows`를 호출하지 않는다. producer-side secondary
view는 P1 emitted `metadata.source_sheet/source_row`와 source binding으로만
검증한다. 이로써 P0 artifact-tool-only 경계를 유지한다.

### 4.3 P0 output rows

evidence `p0.mappings[]`의 각 항목은 다음 필드를 가진다.

```text
yaml_path
yaml_tc_name
blocker_step_indices
declared_source_file
declared_source_sheet
workbook_sheet
workbook_physical_row
candidate_count
join_basis
source_no
source_feature_name_raw
source_feature_name_effective
source_feature_anchor_row
source_functionality_raw
source_functionality_effective
source_functionality_anchor_row
source_precondition
source_procedure
source_expected
source_priority
cells[]
cell_region_records[]
carry_forward_cells[]
verdict
```

P0 top-level에는 `p0_blocking_reasons[]`와 `reconciled`를 둔다.
P0 cardinality와 모든 candidate count가 GREEN이기 전에는 P1을 실행하지 않는다.
Appendix A는 candidate/row-cardinality mismatch를
`p0_blocking_reasons[]`와 `reconciled:false`로 기록한다. controller는 P0 phase를
`COMPLETED`로 ledger에 남긴 뒤 Appendix C를
`--status measured --last-phase P0_ARTIFACT_CAPTURE`로 호출해 campaign exit 1
evidence를 publish하고 STOP한다. Node 예외/inspect 불능으로 바꾸어 exit 3으로
오분류하지 않는다.

Appendix A tool call이 성공한 직후 다음 exact gate를 실행한다.

```powershell
$P0Path = Join-Path $TempRoot 'artifact-tool-work\p0_workbook.json'
$P0SuccessRecord = $null
try {
    $P0Text = [System.IO.File]::ReadAllText($P0Path, $Utf8NoBom)
    $P0Gate = $P0Text | ConvertFrom-Json
    $P0Sha = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $P0Path
    ).Hash.ToLowerInvariant()
    $P0WorkbookShaCurrent = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $Workbook
    ).Hash.ToLowerInvariant()
    $P0WorkbookBlobCurrent = (
        Invoke-GitText `
            'hash-object --no-filters -- tc_samples/TC_1.xlsx' $null
    ).Trim()
    $P0WorkbookItem = Get-Item -LiteralPath $Workbook
    $P0EpochTicks = [System.Numerics.BigInteger]621355968000000000
    $P0WorkbookMtimeCurrentNs = (
        (
            [System.Numerics.BigInteger]$P0WorkbookItem.LastWriteTimeUtc.Ticks -
            $P0EpochTicks
        ) * [System.Numerics.BigInteger]100
    ).ToString()
    $P0InputIdentityValid = (
        $P0Gate.workbook_raw_sha256_before -eq
            '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa' -and
        $P0Gate.workbook_raw_sha256_after -eq
            '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa' -and
        $P0Gate.workbook_mtime_before_ns -eq
            $P0Gate.workbook_mtime_after_ns -and
        $P0WorkbookShaCurrent -eq
            '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa' -and
        $P0WorkbookBlobCurrent -eq
            '24593d11dd80a2b3711655bd0c5216ee9157dedc' -and
        $P0WorkbookMtimeCurrentNs -eq
            $P0Gate.workbook_mtime_after_ns
    )
    $P0ProducerInputIdentityValid = $true
    try {
        Assert-FrozenProducerInputs $DispatchCapsule
    } catch {
        if (Test-InputMismatchException $_.Exception) {
            $P0ProducerInputIdentityValid = $false
        } else {
            throw
        }
    }
    $P0SuccessRecord = [ordered]@{
        phase = 'P0_ARTIFACT_CAPTURE'
        status = 'COMPLETED'
        tool = 'node_repl.js'
        cwd = $Repo
        argv = $null
        tool_input_sha256 = '784fdeb72c6878b5be16ae8f08c0f52cfc1f3e82a3241824918803d14fe7eaf9'
        exit = $null
        observed = [ordered]@{
            p0_workbook_sha256 = $P0Sha
            reconciled = $P0Gate.reconciled
            input_identity_valid = $P0InputIdentityValid
            workbook_raw_sha256_current = $P0WorkbookShaCurrent
            workbook_blob_current = $P0WorkbookBlobCurrent
            workbook_mtime_current_ns = $P0WorkbookMtimeCurrentNs
            producer_input_identity_valid =
                $P0ProducerInputIdentityValid
        }
        error_class = ''
        error_message = ''
    }
    Add-PhaseRecord $P0SuccessRecord
} catch {
    if ($null -ne $P0SuccessRecord) {
        # A success-row append failure is never retried or reconstructed.
        throw
    }
    $P0Failure = $_.Exception
    Add-PhaseRecord ([ordered]@{
        phase = 'P0_ARTIFACT_CAPTURE'
        status = 'FAILED'
        tool = 'node_repl.js'
        cwd = $Repo
        argv = $null
        tool_input_sha256 = '784fdeb72c6878b5be16ae8f08c0f52cfc1f3e82a3241824918803d14fe7eaf9'
        exit = $null
        observed = [ordered]@{}
        error_class = $P0Failure.GetType().Name
        error_message = $P0Failure.Message
    })
    throw $P0Failure
}
```

위 `tool_input_sha256` literal은 Appendix A heading의 final exact 값과
같아야 한다. post-P0 `Assert-FrozenProducerInputs`는 P0 동안의 HEAD/origin,
tracked/staged, 14 actor와 workbook drift를 P1 전에 다시 차단한다.
`$P0InputIdentityValid -ne $true` 또는
`$P0ProducerInputIdentityValid -ne $true`이면 어떤 P1 command도 호출하지
않고 §6.3의 measured/P0 invocation으로 바로 가며 assembler가 exit 2로
분류한다. identity는 GREEN이지만 `reconciled -ne $true`이면 같은 measured/P0
invocation이 exit 1을 결정한다. tool call 자체가 실패하거나 성공 뒤 JSON
read/parse/hash가 실패하면 P0 row를 `FAILED`, `observed=[ordered]@{}`, actual
nonempty class/message로 append한 뒤 §6.3 infra-failure invocation으로 간다.

---

## 5. P1 — Isolated Public-Producer Replay

### 5.1 Producer mode characterization

현재 public `export-mmi` CLI는 legacy-only다.

- `MMIConversionService()`는 default legacy compiler를 사용한다.
- `YAMLExporter(...)`에 `contract_mode`를 전달하지 않는다.
- parser에 `--contract-mode` option이 없다.

따라서 이 지시서는 canonical replay를 주장하지 않는다. 임의 direct-import
canonical harness도 만들지 않는다. P1 evidence에는
`producer_entrypoint_mode: "legacy-only"`를 기록한다.

legacy output의 top-level `name`, tracked YAML의 `tc_name`, exporter filename
hash 차이는 알려진 shape 차이다. full-document byte identity 또는 filename
identity를 provenance acceptance로 사용하지 않는다.

canonical producer round-trip 필요 여부는 이번 실행 중 Codex가 판정하지
않는다. legacy-only 관찰을 evidence의 next-gate NOTE로 남기고, P2 방향은
STOP 뒤 Claude 재검증과 사용자 승인에서만 결정한다.

### 5.2 Exact PowerShell setup

문서 배치는 P1 설명을 위한 것이다. 이 code fence는 각 PowerShell process에서
정확히 1회 선언하되 `$ProcessEntryMode`를 최초 process에서는 exact `ENTRY`,
후속 process에서는 exact `RESUME`으로 치환한다. `ENTRY`는 write-0 host
preflight 안에서 temp root 생성과 §2.5 writer 초기화보다 먼저 실행하며 capsule
verifier와 TTL을 정확히 1회 수행한다. `RESUME`은 verifier/TTL을 재실행하지 않고
기존 HOST_PREFLIGHT ledger payload와 pinned external capsule만 rehydrate한다.
따라서 `$Repo/$Python/$Workbook/$TempRoot/$Utf8NoBom`과 아래 함수들은 각 process
phase 전에 정의되어 있어야 한다. `$Out0/$Out1` assignment는 directory를
생성하지 않는다.

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProcessEntryMode = '<ENTRY_OR_RESUME>'

$Repo = (Resolve-Path -LiteralPath '.').Path
$Python = (Resolve-Path -LiteralPath 'venv\Scripts\python.exe').Path
$Workbook = (Resolve-Path -LiteralPath 'tc_samples\TC_1.xlsx').Path
$TempRoot = 'C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1'
$CapsuleRoot = 'C:\tmp\tc-runner-dispatch-capsules'
$CapsuleSha256 = '<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>'
$CapsulePath = Join-Path $CapsuleRoot ($CapsuleSha256 + '.json')
$DirectiveRelative =
    'HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md'
$SpecRelative =
    'docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md'
$GeneratorRelative = 'scripts/dispatch_capsule.py'
$Out0 = Join-Path $TempRoot 'SS-TC-0'
$Out1 = Join-Path $TempRoot 'SS-TC-1'
$P0WorkbookMtimeCurrentNs = $null

$env:PYTHONHASHSEED = '0'
$env:PYTHONIOENCODING = 'utf-8'
$env:GIT_CONFIG_GLOBAL = 'NUL'
$env:GIT_CONFIG_SYSTEM = 'NUL'

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom
function Write-CanonicalOutput([string]$Path, [object[]]$Lines) {
    $Text = if ($Lines.Count -eq 0) {
        ''
    } else {
        (($Lines | ForEach-Object { [string]$_ }) -join "`n") + "`n"
    }
    [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom)
}
function Throw-InputMismatch([string]$Message) {
    throw "INPUT_MISMATCH: $Message"
}
function Test-InputMismatchException([System.Exception]$Exception) {
    return $Exception.Message.StartsWith(
        'INPUT_MISMATCH: ',
        [System.StringComparison]::Ordinal
    )
}
function Read-PinnedDispatchCapsule {
    if ($CapsuleSha256 -notmatch '^[0-9a-f]{64}$') {
        Throw-InputMismatch "capsule token is not lowercase SHA-256"
    }
    if (-not (Test-Path -LiteralPath $CapsuleRoot -PathType Container)) {
        Throw-InputMismatch "capsule root missing"
    }
    $RootItem = Get-Item -LiteralPath $CapsuleRoot
    if (
        ($RootItem.Attributes -band
            [System.IO.FileAttributes]::ReparsePoint) -ne 0
    ) {
        Throw-InputMismatch "capsule root is link/reparse point"
    }
    if (-not (Test-Path -LiteralPath $CapsulePath -PathType Leaf)) {
        Throw-InputMismatch "capsule file missing"
    }
    $CapsuleItem = Get-Item -LiteralPath $CapsulePath
    if (
        $CapsuleItem.PSIsContainer -or
        (($CapsuleItem.Attributes -band
            [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    ) {
        Throw-InputMismatch "capsule is not ordinary file"
    }
    $ActualCapsuleSha = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $CapsulePath
    ).Hash.ToLowerInvariant()
    if ($ActualCapsuleSha -ne $CapsuleSha256) {
        Throw-InputMismatch "capsule SHA mismatch"
    }
    $Capsule = (
        [System.IO.File]::ReadAllText($CapsulePath, $Utf8NoBom) |
            ConvertFrom-Json
    )
    if (
        $Capsule.schema_version -ne 2 -or
        $Capsule.capsule_type -ne 'tc-runner.dispatch-entry' -or
        $Capsule.directive_id -ne 'RB-20260728-shellrc-p0p1' -or
        $Capsule.ttl_seconds -ne 1800 -or
        ($Capsule.expires_at_epoch_s - $Capsule.issued_at_epoch_s) -ne
            1800 -or
        $Capsule.repo.root -ne 'C:/Users/momen/Projects/tc-runner' -or
        $Capsule.repo.upstream_ref -ne 'origin/master' -or
        $Capsule.repo.ahead -ne 0 -or
        $Capsule.repo.behind -ne 0 -or
        $Capsule.repo.tracked_clean -ne $true -or
        $Capsule.repo.staged_clean -ne $true -or
        @($Capsule.untracked.excluded_paths).Count -ne 0 -or
        @($Capsule.ignored.excluded_paths).Count -ne 0 -or
        $Capsule.identities.directive.path -ne $DirectiveRelative -or
        $Capsule.identities.spec.path -ne $SpecRelative -or
        $Capsule.identities.generator.path -ne $GeneratorRelative
    ) {
        Throw-InputMismatch "capsule fixed schema/binding mismatch"
    }
    if (
        $Capsule.identities.directive.raw_sha256 -ne
            '<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>' -or
        $Capsule.identities.directive.git_blob_no_filters -ne
            '<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>' -or
        $Capsule.identities.spec.raw_sha256 -ne
            '492b718d4dfc3713f9c78c362c3db38af4e348336df81917aa7991ee145aaebf' -or
        $Capsule.identities.spec.git_blob_no_filters -ne
            '4db31884e55f1c18dbfd53edd090da88d9f8b51e' -or
        $Capsule.identities.generator.raw_sha256 -ne
            '45a1a0ebc3fdc89691f6b3106fede0771ea376a8f132866899bca655289db6bd' -or
        $Capsule.identities.generator.git_blob_no_filters -ne
            'db170b307a323e861b8a3fc7d29ef743b109197e'
    ) {
        Throw-InputMismatch "capsule content identity mismatch"
    }
    return $Capsule
}
function Assert-ModuleRouteBinding([object]$Capsule) {
    function Assert-OrdinaryModulePath(
        [string]$Path,
        [string]$Label,
        [bool]$ExpectContainer
    ) {
        $PathRoot = [System.IO.Path]::GetPathRoot($Path)
        if (
            [string]::IsNullOrWhiteSpace($Path) -or
            [string]::IsNullOrEmpty($PathRoot) -or
            $PathRoot.Length -lt 3
        ) {
            Throw-InputMismatch "module path is not absolute: $Label"
        }
        $FullPath = [System.IO.Path]::GetFullPath($Path)
        $Current = $FullPath
        $LeafItem = $null
        while ($true) {
            if (-not (Test-Path -LiteralPath $Current)) {
                throw "module path unavailable: ${Label}: $FullPath"
            }
            $Item = Get-Item -Force -LiteralPath $Current
            if (
                ($Item.Attributes -band
                    [System.IO.FileAttributes]::ReparsePoint) -ne 0
            ) {
                Throw-InputMismatch (
                    "module path is link/reparse point: ${Label}: " +
                    $Current
                )
            }
            if ($null -eq $LeafItem) {
                $LeafItem = $Item
            }
            $Parent = [System.IO.Directory]::GetParent($Current)
            if ($null -eq $Parent) {
                break
            }
            $Current = $Parent.FullName
        }
        if (
            ($ExpectContainer -and -not $LeafItem.PSIsContainer) -or
            (-not $ExpectContainer -and $LeafItem.PSIsContainer)
        ) {
            Throw-InputMismatch "module path type mismatch: $Label"
        }
        return $LeafItem
    }
    $Modules = @($Capsule.module_roots)
    if ($Modules.Count -ne 1) {
        Throw-InputMismatch "capsule module_roots cardinality"
    }
    $Module = $Modules[0]
    if ($Module.package_name -ne '@oai/artifact-tool') {
        Throw-InputMismatch "capsule module package name"
    }
    if (
        $Module.entry_sha256 -notmatch '^[0-9a-f]{64}$' -or
        [long]$Module.entry_bytes -le 0
    ) {
        Throw-InputMismatch "capsule module entry fields"
    }
    $RootPath = [string]$Module.root_path
    $null = Assert-OrdinaryModulePath $RootPath 'root' $true
    $RootFull = [System.IO.Path]::GetFullPath($RootPath)
    $RepoFull = [System.IO.Path]::GetFullPath($Repo)
    $RepoPrefix = (
        $RepoFull.TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        ) + [System.IO.Path]::DirectorySeparatorChar
    )
    if (
        $RootFull.Equals(
            $RepoFull,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        $RootFull.StartsWith(
            $RepoPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        Throw-InputMismatch "module root must be outside repository"
    }
    $PackageDir = Join-Path (
        Join-Path $RootFull '@oai'
    ) 'artifact-tool'
    $ManifestPath = Join-Path $PackageDir 'package.json'
    $EntryPath = Join-Path $PackageDir (
        ([string]$Module.entry_relpath).Replace('/', '\')
    )
    $null = Assert-OrdinaryModulePath $PackageDir 'package' $true
    $null = Assert-OrdinaryModulePath $ManifestPath 'manifest' $false
    $EntryItem = Assert-OrdinaryModulePath $EntryPath 'entry' $false
    $Manifest = (
        [System.IO.File]::ReadAllText($ManifestPath, $Utf8NoBom) |
            ConvertFrom-Json
    )
    $ExportProperty = $null
    if ($null -ne $Manifest.exports) {
        $ExportProperty = $Manifest.exports.PSObject.Properties['.']
    }
    $LiveExport = if ($null -eq $ExportProperty) {
        $null
    } else {
        $ExportProperty.Value
    }
    $ExpectedExport = (
        './' + ([string]$Module.entry_relpath).Replace('\', '/')
    )
    if ([version]$Manifest.version -lt [version]'2.8.6') {
        throw "module version below floor: $($Manifest.version)"
    }
    $EntrySha = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $EntryPath
    ).Hash.ToLowerInvariant()
    if (
        $Manifest.name -cne $Module.package_name -or
        $Manifest.version -cne $Module.package_version -or
        $LiveExport -isnot [string] -or
        $LiveExport -cne $ExpectedExport -or
        [long]$EntryItem.Length -ne [long]$Module.entry_bytes -or
        $EntrySha -ne [string]$Module.entry_sha256
    ) {
        Throw-InputMismatch "module capsule-vs-live mismatch"
    }
}
$CapsuleVerifyArgs = @(
    '-B', 'scripts/dispatch_capsule.py', 'verify',
    '--repo', $Repo,
    '--capsule-sha256', $CapsuleSha256,
    '--expected-directive-id', 'RB-20260728-shellrc-p0p1',
    '--expected-directive', $DirectiveRelative,
    '--expected-spec', $SpecRelative
)
$CapsuleVerifyLines = @()
$CapsuleVerifyExit = $null
if ($ProcessEntryMode -eq 'ENTRY') {
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = $null
        $CapsuleVerifyLines = @(& $Python @CapsuleVerifyArgs 2>&1)
        $CapsuleVerifyExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
    if ($CapsuleVerifyExit -eq 2) {
        Throw-InputMismatch (
            "capsule verify input invalid: " +
            (
                ($CapsuleVerifyLines |
                    ForEach-Object { [string]$_ }) -join ' | '
            )
        )
    }
    if ($CapsuleVerifyExit -ne 0) {
        throw (
            "capsule verify infrastructure failure exit " +
            "${CapsuleVerifyExit}: " +
            (
                ($CapsuleVerifyLines |
                    ForEach-Object { [string]$_ }) -join ' | '
            )
        )
    }
    $ExpectedCapsuleVerifyOutput = (
        '{"capsule_sha256":"' + $CapsuleSha256 + '","status":"GREEN"}'
    )
    $ActualCapsuleVerifyOutput = (
        $CapsuleVerifyLines | ForEach-Object { [string]$_ }
    ) -join "`n"
    if ($ActualCapsuleVerifyOutput -ne $ExpectedCapsuleVerifyOutput) {
        Throw-InputMismatch "capsule verify stdout mismatch"
    }
    $DispatchCapsule = Read-PinnedDispatchCapsule
    $NowEpochSeconds = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if (
        $NowEpochSeconds -lt $DispatchCapsule.issued_at_epoch_s -or
        $NowEpochSeconds -ge $DispatchCapsule.expires_at_epoch_s
    ) {
        Throw-InputMismatch "capsule TTL invalid before first write"
    }
    Assert-ModuleRouteBinding $DispatchCapsule
} elseif ($ProcessEntryMode -eq 'RESUME') {
    $OperationLog = Join-Path $TempRoot 'operation_log.ndjson'
    $OperationLogItem = Get-Item -LiteralPath $OperationLog
    if (
        $OperationLogItem.PSIsContainer -or
        (($OperationLogItem.Attributes -band
            [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    ) {
        Throw-InputMismatch "resume ledger is not ordinary file"
    }
    $HostRows = @(
        [System.IO.File]::ReadAllLines($OperationLog, $Utf8NoBom) |
            ForEach-Object { $_ | ConvertFrom-Json } |
            Where-Object { $_.phase -eq 'HOST_PREFLIGHT' }
    )
    $HostRowKeys = @(
        'phase', 'status', 'tool', 'cwd', 'argv',
        'tool_input_sha256', 'exit', 'observed',
        'error_class', 'error_message'
    )
    $HostObservedKeys = @(
        'dispatch_capsule', 'dispatch_capsule_path',
        'dispatch_capsule_sha256', 'capsule_verify',
        'ttl_valid_before_first_write', 'module_route', 'toolchain'
    )
    $ModuleRouteKeys = @(
        'probe_source_sha256', 'package_name', 'package_version',
        'root_path', 'entry_bytes', 'entry_sha256'
    )
    $CapsuleVerifyKeys = @('tool', 'argv', 'exit')
    $ExpectedToolchain = [ordered]@{
        console_input = 'utf-8'
        console_output = 'utf-8'
        node = 'v24.14.1'
        openpyxl = '3.1.5'
        output_encoding = 'utf-8'
        powershell = '5.1.26100.8875'
        psedition = 'Desktop'
        pyyaml = '6.0.3'
        python = '3.12.2'
        pythonhashseed = '0'
        pythonioencoding = 'utf-8'
    }
    if (
        $HostRows.Count -ne 1 -or
        @($HostRows[0].PSObject.Properties.Name).Count -ne
            $HostRowKeys.Count -or
        (
            @($HostRows[0].PSObject.Properties.Name) -join "`n"
        ) -ne (@($HostRowKeys) -join "`n") -or
        $HostRows[0].phase -ne 'HOST_PREFLIGHT' -or
        $HostRows[0].status -ne 'COMPLETED' -or
        $HostRows[0].tool -ne 'PowerShell' -or
        $HostRows[0].cwd -ne $Repo -or
        $null -ne $HostRows[0].argv -or
        $null -ne $HostRows[0].tool_input_sha256 -or
        $null -ne $HostRows[0].exit -or
        $HostRows[0].error_class -ne '' -or
        $HostRows[0].error_message -ne '' -or
        @($HostRows[0].observed.PSObject.Properties.Name).Count -ne
            $HostObservedKeys.Count -or
        (
            @($HostRows[0].observed.PSObject.Properties.Name) -join "`n"
        ) -ne (@($HostObservedKeys) -join "`n") -or
        $HostRows[0].observed.dispatch_capsule_sha256 -ne
            $CapsuleSha256 -or
        $HostRows[0].observed.dispatch_capsule_path -ne
            $CapsulePath.Replace('\', '/') -or
        $HostRows[0].observed.ttl_valid_before_first_write -ne $true -or
        @(
            $HostRows[0].observed.capsule_verify.PSObject.Properties.Name
        ).Count -ne $CapsuleVerifyKeys.Count -or
        (
            @($HostRows[0].observed.capsule_verify.PSObject.Properties.Name) -join "`n"
        ) -ne (@($CapsuleVerifyKeys) -join "`n") -or
        $HostRows[0].observed.capsule_verify.tool -ne $Python -or
        $HostRows[0].observed.capsule_verify.exit -ne 0 -or
        @($HostRows[0].observed.capsule_verify.argv).Count -ne
            $CapsuleVerifyArgs.Count -or
        (
            @($HostRows[0].observed.capsule_verify.argv) -join "`n"
        ) -ne (@($CapsuleVerifyArgs) -join "`n") -or
        @(
            $HostRows[0].observed.module_route.PSObject.Properties.Name
        ).Count -ne $ModuleRouteKeys.Count -or
        (
            @($HostRows[0].observed.module_route.PSObject.Properties.Name) -join "`n"
        ) -ne (@($ModuleRouteKeys) -join "`n") -or
        (
            $HostRows[0].observed.toolchain |
                ConvertTo-Json -Compress
        ) -ne ($ExpectedToolchain | ConvertTo-Json -Compress)
    ) {
        Throw-InputMismatch "resume HOST_PREFLIGHT binding mismatch"
    }
    $CapsuleVerifyExit = 0
    $DispatchCapsule = $HostRows[0].observed.dispatch_capsule
    $PinnedCapsule = Read-PinnedDispatchCapsule
    if (
        ($PinnedCapsule | ConvertTo-Json -Depth 12 -Compress) -ne
        ($DispatchCapsule | ConvertTo-Json -Depth 12 -Compress)
    ) {
        Throw-InputMismatch "resume capsule payload mismatch"
    }
} else {
    Throw-InputMismatch "process entry mode must be ENTRY or RESUME"
}
function Invoke-GitText(
    [string]$Arguments,
    [object]$InputText
) {
    $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $StartInfo.FileName = 'git'
    $StartInfo.Arguments = '-c core.excludesFile=NUL ' + $Arguments
    $StartInfo.WorkingDirectory = $Repo
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.RedirectStandardInput = $true
    $StartInfo.StandardOutputEncoding = $Utf8NoBom
    $StartInfo.StandardErrorEncoding = $Utf8NoBom
    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $StartInfo
    if (-not $Process.Start()) {
        throw "git process failed to start: $Arguments"
    }
    $OutputTask = $Process.StandardOutput.ReadToEndAsync()
    $ErrorTask = $Process.StandardError.ReadToEndAsync()
    if ($null -ne $InputText) {
        $InputBytes = $Utf8NoBom.GetBytes([string]$InputText)
        $Process.StandardInput.BaseStream.Write(
            $InputBytes, 0, $InputBytes.Length
        )
        $Process.StandardInput.BaseStream.Flush()
    }
    $Process.StandardInput.Close()
    $Process.WaitForExit()
    $OutputText = $OutputTask.GetAwaiter().GetResult()
    $ErrorText = $ErrorTask.GetAwaiter().GetResult()
    if ($Process.ExitCode -ne 0) {
        throw (
            "git $Arguments exit $($Process.ExitCode): " +
            $ErrorText.Trim()
        )
    }
    if (-not [string]::IsNullOrEmpty($ErrorText)) {
        throw "git $Arguments emitted stderr: $($ErrorText.Trim())"
    }
    return $OutputText
}
function Invoke-GitQuiet([string]$Arguments) {
    $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $StartInfo.FileName = 'git'
    $StartInfo.Arguments = '-c core.excludesFile=NUL ' + $Arguments
    $StartInfo.WorkingDirectory = $Repo
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.StandardOutputEncoding = $Utf8NoBom
    $StartInfo.StandardErrorEncoding = $Utf8NoBom
    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $StartInfo
    if (-not $Process.Start()) {
        throw "git process failed to start: $Arguments"
    }
    $OutputTask = $Process.StandardOutput.ReadToEndAsync()
    $ErrorTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    $OutputText = $OutputTask.GetAwaiter().GetResult()
    $ErrorText = $ErrorTask.GetAwaiter().GetResult()
    if ($Process.ExitCode -notin @(0, 1)) {
        throw (
            "git $Arguments exit $($Process.ExitCode): " +
            $ErrorText.Trim()
        )
    }
    if (-not [string]::IsNullOrEmpty($OutputText)) {
        throw "git $Arguments emitted stdout"
    }
    if (-not [string]::IsNullOrEmpty($ErrorText)) {
        throw "git $Arguments emitted stderr: $($ErrorText.Trim())"
    }
    return $Process.ExitCode -eq 0
}
function ConvertTo-CanonicalJsonString([string]$Value) {
    $Builder = New-Object System.Text.StringBuilder
    [void]$Builder.Append('"')
    foreach ($Character in $Value.ToCharArray()) {
        $Code = [int]$Character
        switch ($Code) {
            8 { [void]$Builder.Append('\b'); continue }
            9 { [void]$Builder.Append('\t'); continue }
            10 { [void]$Builder.Append('\n'); continue }
            12 { [void]$Builder.Append('\f'); continue }
            13 { [void]$Builder.Append('\r'); continue }
            34 { [void]$Builder.Append('\"'); continue }
            92 { [void]$Builder.Append('\\'); continue }
        }
        if ($Code -lt 32) {
            [void]$Builder.Append(('\u{0:x4}' -f $Code))
        } else {
            [void]$Builder.Append($Character)
        }
    }
    [void]$Builder.Append('"')
    return $Builder.ToString()
}
function Get-FrozenPathMapIdentity([bool]$Ignored) {
    $ListArguments = if ($Ignored) {
        '-c core.quotepath=false ls-files --others --ignored --exclude-standard -z'
    } else {
        '-c core.quotepath=false ls-files --others --exclude-standard -z'
    }
    $RawPaths = Invoke-GitText $ListArguments $null
    $Paths = [System.Collections.Generic.List[string]]::new()
    foreach ($RawPath in $RawPaths.Split([char]0)) {
        if ([string]::IsNullOrEmpty($RawPath)) { continue }
        $Relative = $RawPath.Replace('\', '/')
        if ($Relative.Contains("`n") -or $Relative.Contains("`r")) {
            Throw-InputMismatch "newline-containing path is unsupported"
        }
        $Candidate = Get-Item -LiteralPath (
            Join-Path $Repo $Relative.Replace('/', '\')
        )
        if (
            $Candidate.PSIsContainer -or
            (($Candidate.Attributes -band
                [System.IO.FileAttributes]::ReparsePoint) -ne 0)
        ) {
            Throw-InputMismatch (
                "path map member is not ordinary file: $Relative"
            )
        }
        $Paths.Add($Relative)
    }
    $Utf8Comparer = [System.Collections.Generic.Comparer[string]]::Create(
        [System.Comparison[string]]{
            param([string]$Left, [string]$Right)
            $LeftBytes = $Utf8NoBom.GetBytes($Left)
            $RightBytes = $Utf8NoBom.GetBytes($Right)
            $Length = [Math]::Min($LeftBytes.Length, $RightBytes.Length)
            for ($Index = 0; $Index -lt $Length; $Index++) {
                if ($LeftBytes[$Index] -lt $RightBytes[$Index]) { return -1 }
                if ($LeftBytes[$Index] -gt $RightBytes[$Index]) { return 1 }
            }
            return $LeftBytes.Length.CompareTo($RightBytes.Length)
        }
    )
    $PathArray = $Paths.ToArray()
    [Array]::Sort($PathArray, $Utf8Comparer)
    for ($Index = 1; $Index -lt $PathArray.Length; $Index++) {
        if ($PathArray[$Index] -eq $PathArray[$Index - 1]) {
            Throw-InputMismatch (
                "duplicate path map member: $($PathArray[$Index])"
            )
        }
    }
    $HashInput = if ($PathArray.Length -eq 0) {
        ''
    } else {
        ($PathArray -join "`n") + "`n"
    }
    $HashOutput = Invoke-GitText `
        'hash-object --no-filters --stdin-paths' $HashInput
    $Hashes = @(
        $HashOutput -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrEmpty($_) }
    )
    if ($Hashes.Count -ne $PathArray.Length) {
        throw "path map hash cardinality mismatch"
    }
    $Rows = New-Object System.Collections.Generic.List[string]
    for ($Index = 0; $Index -lt $PathArray.Length; $Index++) {
        if ($Hashes[$Index] -notmatch '^[0-9a-f]{40}$') {
            throw "path map Git blob invalid: $($PathArray[$Index])"
        }
        $PathJson = ConvertTo-CanonicalJsonString $PathArray[$Index]
        $Rows.Add(
            '{"file_type":"file","git_hash_object_no_filters":"' +
            $Hashes[$Index] + '","path":' + $PathJson + '}'
        )
    }
    $CanonicalJson = '[' + ($Rows -join ',') + ']'
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $DigestBytes = $Hasher.ComputeHash(
            $Utf8NoBom.GetBytes($CanonicalJson)
        )
    } finally {
        $Hasher.Dispose()
    }
    $Digest = (
        [System.BitConverter]::ToString($DigestBytes)
    ).Replace('-', '').ToLowerInvariant()
    return [pscustomobject]@{
        count = $PathArray.Length
        canonical_json_sha256 = $Digest
    }
}
function Assert-FrozenProducerInputs([object]$ExpectedCapsule) {
    $CurrentCapsule = Read-PinnedDispatchCapsule
    if (
        ($CurrentCapsule | ConvertTo-Json -Depth 12 -Compress) -ne
        ($ExpectedCapsule | ConvertTo-Json -Depth 12 -Compress)
    ) {
        Throw-InputMismatch "dispatch capsule payload changed"
    }
    if ([string]::IsNullOrEmpty($P0WorkbookMtimeCurrentNs)) {
        $P0IdentityPath = Join-Path `
            $TempRoot 'artifact-tool-work\p0_workbook.json'
        $P0IdentityItem = Get-Item -LiteralPath $P0IdentityPath
        if (
            $P0IdentityItem.PSIsContainer -or
            (($P0IdentityItem.Attributes -band
                [System.IO.FileAttributes]::ReparsePoint) -ne 0)
        ) {
            Throw-InputMismatch "P0 identity artifact is not ordinary file"
        }
        $P0Identity = (
            [System.IO.File]::ReadAllText($P0IdentityPath, $Utf8NoBom) |
                ConvertFrom-Json
        )
        if (
            $P0Identity.workbook_raw_sha256_before -ne
                '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa' -or
            $P0Identity.workbook_raw_sha256_after -ne
                '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa' -or
            $P0Identity.workbook_mtime_before_ns -ne
                $P0Identity.workbook_mtime_after_ns
        ) {
            Throw-InputMismatch (
                "P0 identity artifact workbook binding mismatch"
            )
        }
        $P0IdentitySha = (
            Get-FileHash -Algorithm SHA256 -LiteralPath $P0IdentityPath
        ).Hash.ToLowerInvariant()
        $LedgerItem = Get-Item -LiteralPath (
            Join-Path $TempRoot 'operation_log.ndjson'
        )
        if (
            $LedgerItem.PSIsContainer -or
            (($LedgerItem.Attributes -band
                [System.IO.FileAttributes]::ReparsePoint) -ne 0)
        ) {
            Throw-InputMismatch "operation ledger is not ordinary file"
        }
        $P0LedgerRows = @(
            [System.IO.File]::ReadAllLines(
                $LedgerItem.FullName, $Utf8NoBom
            ) |
                ForEach-Object { $_ | ConvertFrom-Json } |
                Where-Object { $_.phase -eq 'P0_ARTIFACT_CAPTURE' }
        )
        if (
            $P0LedgerRows.Count -ne 1 -or
            $P0LedgerRows[0].status -ne 'COMPLETED' -or
            $P0LedgerRows[0].observed.p0_workbook_sha256 -ne
                $P0IdentitySha -or
            $P0LedgerRows[0].observed.input_identity_valid -ne $true -or
            $P0LedgerRows[0].observed.producer_input_identity_valid -ne
                $true
        ) {
            Throw-InputMismatch (
                "P0 identity artifact/ledger binding mismatch"
            )
        }
        $script:P0WorkbookMtimeCurrentNs =
            [string]$P0Identity.workbook_mtime_after_ns
    }
    $ActualHead = (Invoke-GitText 'rev-parse HEAD' $null).Trim()
    if ($ActualHead -ne [string]$ExpectedCapsule.repo.head_sha) {
        Throw-InputMismatch "producer input HEAD mismatch: $ActualHead"
    }
    $ActualOrigin = (
        Invoke-GitText 'rev-parse origin/master' $null
    ).Trim()
    if (
        $ExpectedCapsule.repo.upstream_ref -ne 'origin/master' -or
        $ActualOrigin -ne [string]$ExpectedCapsule.repo.upstream_sha
    ) {
        Throw-InputMismatch (
            "producer input origin/master mismatch: $ActualOrigin"
        )
    }
    if (-not (Invoke-GitQuiet 'diff --quiet')) {
        Throw-InputMismatch "producer input tracked diff"
    }
    if (-not (Invoke-GitQuiet 'diff --cached --quiet')) {
        Throw-InputMismatch "producer input staged diff"
    }
    $FrozenActors = [ordered]@{
        'src/cli.py' = 'c27fa7d5c6c4bd9f956238ef0008990e667989949bbc5743d6a37347ee71a5b0'
        'src/execution_contract.py' = 'b5a8601a8efd7008752f5c1b50134066082a64f8b976f1fb2270fcc76f1b21eb'
        'tc_step_schema.json' = '7ec8a76766bec3e8ba18cdd8deedb478024edb2878ee83190907125669cc7059'
        'src/mmi_converter/__init__.py' = '164bb0d498d3a7ec2172196882f2ed566fc0578c924d1445b0c4af390ca4f4a4'
        'src/mmi_converter/classifier.py' = 'f795a9e88f8f6b67a9b2358a5adf5edeccc4ba48bae2e5d1bd2153de0f0f1753'
        'src/mmi_converter/compiler.py' = '52985f0b008d23a65ca7168777e23590ddd4b20eb22f37f1f8eede3d6c313eec'
        'src/mmi_converter/expected_parser.py' = '17b42361351d54920c89851acac473293eff6ad2a75d3ba90854926d2e98375c'
        'src/mmi_converter/exporter.py' = '3090015d4a045d61c0f382cc21dceffd3a13c7c8b1950119b9396e5bb18bbac6'
        'src/mmi_converter/models.py' = '6240036685e4a64a51c16cc5a576b268c1eba3aeb55031b83ce097882a7a7227'
        'src/mmi_converter/procedure_parser.py' = '62c66ef7e941a1a3eaeb3b7a7abe14c8f020923e33287a589f27eb1908d6618a'
        'src/mmi_converter/row_loader.py' = '38cb421b9f7f6282df401c84dc7b06837ea61cd70b22d17547e9ed62498c39d7'
        'src/mmi_converter/service.py' = '83015f8c79ade724ec7aa619a2fff82945192ecb41b479d344b2b9c404729f79'
        'src/mmi_converter/shell_action_map.py' = '479b846a48bba0771d37af924ae8a38314c83033f05ef0993598f85bb7cb77be'
        'src/mmi_converter/step_classifier.py' = '1c73bb15df6981ab9d6cc68615db0decfdaa70259c30fbdb2c5e26e89fd1f90f'
    }
    foreach ($Entry in $FrozenActors.GetEnumerator()) {
        $Actual = (
            Get-FileHash -Algorithm SHA256 `
                -LiteralPath (Join-Path $Repo ([string]$Entry.Key))
        ).Hash.ToLowerInvariant()
        if ($Actual -ne [string]$Entry.Value) {
            Throw-InputMismatch (
                "producer actor hash mismatch: $($Entry.Key)"
            )
        }
    }
    $WorkbookSha = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $Workbook
    ).Hash.ToLowerInvariant()
    if ($WorkbookSha -ne
        '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa') {
        Throw-InputMismatch "producer workbook SHA mismatch"
    }
    $WorkbookBlob = (
        Invoke-GitText `
            'hash-object --no-filters -- tc_samples/TC_1.xlsx' $null
    ).Trim()
    if ($WorkbookBlob -ne
        '24593d11dd80a2b3711655bd0c5216ee9157dedc') {
        Throw-InputMismatch "producer workbook blob mismatch: $WorkbookBlob"
    }
    $WorkbookItem = Get-Item -LiteralPath $Workbook
    $EpochTicks = [System.Numerics.BigInteger]621355968000000000
    $WorkbookMtimeNs = (
        (
            [System.Numerics.BigInteger]$WorkbookItem.LastWriteTimeUtc.Ticks -
            $EpochTicks
        ) * [System.Numerics.BigInteger]100
    ).ToString()
    if ($WorkbookMtimeNs -ne $P0WorkbookMtimeCurrentNs) {
        Throw-InputMismatch (
            "producer workbook mtime mismatch: $WorkbookMtimeNs"
        )
    }
    $UntrackedIdentity = Get-FrozenPathMapIdentity $false
    if (
        $UntrackedIdentity.count -ne
            $ExpectedCapsule.untracked.count -or
        $UntrackedIdentity.canonical_json_sha256 -ne
            $ExpectedCapsule.untracked.canonical_json_sha256 -or
        @($ExpectedCapsule.untracked.excluded_paths).Count -ne 0
    ) {
        Throw-InputMismatch "producer input untracked identity mismatch"
    }
    $IgnoredIdentity = Get-FrozenPathMapIdentity $true
    if (
        $IgnoredIdentity.count -ne $ExpectedCapsule.ignored.count -or
        $IgnoredIdentity.canonical_json_sha256 -ne
            $ExpectedCapsule.ignored.canonical_json_sha256 -or
        @($ExpectedCapsule.ignored.excluded_paths).Count -ne 0
    ) {
        Throw-InputMismatch "producer input ignored identity mismatch"
    }
    foreach ($Entry in $FrozenActors.GetEnumerator()) {
        $FinalActorSha = (
            Get-FileHash -Algorithm SHA256 `
                -LiteralPath (Join-Path $Repo ([string]$Entry.Key))
        ).Hash.ToLowerInvariant()
        if ($FinalActorSha -ne [string]$Entry.Value) {
            Throw-InputMismatch (
                "producer final actor hash mismatch: $($Entry.Key)"
            )
        }
    }
    $FinalWorkbookSha = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $Workbook
    ).Hash.ToLowerInvariant()
    if ($FinalWorkbookSha -ne
        '160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa') {
        Throw-InputMismatch "producer final workbook SHA mismatch"
    }
    $FinalWorkbookBlob = (
        Invoke-GitText `
            'hash-object --no-filters -- tc_samples/TC_1.xlsx' $null
    ).Trim()
    if ($FinalWorkbookBlob -ne
        '24593d11dd80a2b3711655bd0c5216ee9157dedc') {
        Throw-InputMismatch (
            "producer final workbook blob mismatch: $FinalWorkbookBlob"
        )
    }
    $FinalWorkbookItem = Get-Item -LiteralPath $Workbook
    $FinalWorkbookMtimeNs = (
        (
            [System.Numerics.BigInteger](
                $FinalWorkbookItem.LastWriteTimeUtc.Ticks
            ) - $EpochTicks
        ) * [System.Numerics.BigInteger]100
    ).ToString()
    if ($FinalWorkbookMtimeNs -ne $P0WorkbookMtimeCurrentNs) {
        Throw-InputMismatch (
            "producer final workbook mtime mismatch: " +
            "$FinalWorkbookMtimeNs"
        )
    }
    $FinalHead = (Invoke-GitText 'rev-parse HEAD' $null).Trim()
    $FinalOrigin = (
        Invoke-GitText 'rev-parse origin/master' $null
    ).Trim()
    if (
        $FinalHead -ne [string]$ExpectedCapsule.repo.head_sha -or
        $FinalOrigin -ne [string]$ExpectedCapsule.repo.upstream_sha
    ) {
        Throw-InputMismatch "producer final HEAD/origin mismatch"
    }
    if (-not (Invoke-GitQuiet 'diff --quiet')) {
        Throw-InputMismatch "producer final tracked diff"
    }
    if (-not (Invoke-GitQuiet 'diff --cached --quiet')) {
        Throw-InputMismatch "producer final staged diff"
    }
}
function Complete-ProcessPhase(
    [string]$Phase,
    [object[]]$Argv,
    [int]$ProcessExit,
    [string]$OutputPath,
    [object[]]$Lines,
    [object]$ObservedFilePath,
    [object]$ObservedField
) {
    $ProcessFailure = if ($ProcessExit -eq 0) {
        $null
    } else {
        New-Object -TypeName System.InvalidOperationException `
            -ArgumentList "$Phase process exit $ProcessExit"
    }
    $Observed = [ordered]@{
        producer_input_identity_valid = $true
        process_launch_succeeded = $true
    }
    try {
        Write-CanonicalOutput $OutputPath $Lines
        if (
            ($null -eq $ObservedFilePath) -xor
            ($null -eq $ObservedField)
        ) {
            throw "$Phase observed file/field must be supplied together"
        }
        if (
            $ProcessExit -eq 0 -and
            $null -ne $ObservedFilePath
        ) {
            $Observed[[string]$ObservedField] = (
                Get-FileHash -Algorithm SHA256 `
                    -LiteralPath ([string]$ObservedFilePath)
            ).Hash.ToLowerInvariant()
        }
    } catch {
        $ControllerFailure = $_.Exception
        $Failure = if ($null -ne $ProcessFailure) {
            $ProcessFailure
        } else {
            $ControllerFailure
        }
        Add-PhaseRecord ([ordered]@{
            phase = $Phase
            status = 'FAILED'
            tool = $Python
            cwd = $Repo
            argv = @($Argv)
            tool_input_sha256 = $null
            exit = $ProcessExit
            observed = [ordered]@{
                producer_input_identity_valid = $true
                process_launch_succeeded = $true
            }
            error_class = $Failure.GetType().Name
            error_message = $Failure.Message
        })
        throw $Failure
    }
    Add-PhaseRecord ([ordered]@{
        phase = $Phase
        status = if ($null -eq $ProcessFailure) {
            'COMPLETED'
        } else {
            'FAILED'
        }
        tool = $Python
        cwd = $Repo
        argv = @($Argv)
        tool_input_sha256 = $null
        exit = $ProcessExit
        observed = $Observed
        error_class = if ($null -eq $ProcessFailure) {
            ''
        } else {
            $ProcessFailure.GetType().Name
        }
        error_message = if ($null -eq $ProcessFailure) {
            ''
        } else {
            $ProcessFailure.Message
        }
    })
    if ($null -ne $ProcessFailure) { throw $ProcessFailure }
}
function Invoke-CheckedPythonPhase(
    [string]$Phase,
    [object[]]$Argv,
    [string]$OutputPath,
    [object]$ObservedFilePath,
    [object]$ObservedField
) {
    try {
        Assert-FrozenProducerInputs $DispatchCapsule
    } catch {
        $InputFailure = $_.Exception
        $InputMismatch = Test-InputMismatchException $InputFailure
        $InputObserved = if ($InputMismatch) {
            [ordered]@{
                producer_input_identity_valid = $false
            }
        } else {
            [ordered]@{
                producer_input_identity_valid = $null
                producer_input_check_completed = $false
            }
        }
        Add-PhaseRecord ([ordered]@{
            phase = $Phase
            status = 'FAILED'
            tool = $Python
            cwd = $Repo
            argv = @($Argv)
            tool_input_sha256 = $null
            exit = $null
            observed = $InputObserved
            error_class = $InputFailure.GetType().Name
            error_message = $InputFailure.Message
        })
        throw $InputFailure
    }
    $PreviousErrorActionPreference = $ErrorActionPreference
    $LaunchFailure = $null
    $Lines = @()
    $ProcessExit = $null
    try {
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = $null
        $Lines = @(& $Python @Argv 2>&1)
        $ProcessExit = $LASTEXITCODE
        if ($null -eq $ProcessExit) {
            $LaunchText = (
                $Lines | ForEach-Object { [string]$_ }
            ) -join ' | '
            $LaunchFailure = New-Object `
                System.InvalidOperationException `
                -ArgumentList (
                    "native process did not report exit: $LaunchText"
                )
        }
    } catch {
        $LaunchFailure = $_.Exception
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
    if ($null -ne $LaunchFailure) {
        Add-PhaseRecord ([ordered]@{
            phase = $Phase
            status = 'FAILED'
            tool = $Python
            cwd = $Repo
            argv = @($Argv)
            tool_input_sha256 = $null
            exit = $null
            observed = [ordered]@{
                producer_input_identity_valid = $true
                process_launch_succeeded = $false
            }
            error_class = $LaunchFailure.GetType().Name
            error_message = $LaunchFailure.Message
        })
        throw $LaunchFailure
    }
    Complete-ProcessPhase `
        $Phase $Argv $ProcessExit $OutputPath $Lines `
        $ObservedFilePath $ObservedField
}
```

`$Repo`는 `C:\Users\momen\Projects\tc-runner`와 case-insensitive exact
같아야 한다. temp root는 P0 직전에 한 번 생성됐고 `$Out0`, `$Out1`은 아직
존재하지 않아야 한다.

각 PowerShell process block은 `Invoke-CheckedPythonPhase`를 정확히 1회
호출한다. 이 함수는 실행 직전 HEAD/origin, tracked/staged clean, 14 actor
hash, frozen untracked/ignored content maps와 workbook SHA/blob/mtime를
재검사한 뒤에만 process를 시작한다. 이
pre-invocation 비교 mismatch는 intended phase의 `FAILED`, `exit:null`,
`producer_input_identity_valid:false` row를 먼저 남겨 exit 2에 결속한다.
Git/process/read/hash 자체가 측정 불능이면 producer identity는 `null`,
`producer_input_check_completed:false`로 남겨 exit 3과 구분한다.
gate 뒤 native process launch 자체가 실패하면 `exit:null`,
`producer_input_identity_valid:true`, `process_launch_succeeded:false`로
구분해 exit 3에 결속한다. native stderr는 launch 실패가 아니다.
PowerShell 5.1에서 해당 invocation 동안만
`$ErrorActionPreference='Continue'`로 capture하고 `$LASTEXITCODE` numeric 존재로
launch를 판별한 뒤 즉시 원래 preference를 복원한다. process가 시작되면 결과를
`Complete-ProcessPhase`에 정확히 1회 넘기고, 이
함수가 canonical output 기록과
성공 후 관측 hash를 phase 안에서 수행한다. process nonzero 또는 그 뒤
controller I/O/hash 실패면 numeric process exit(후자의 경우 0도 가능)를 가진
ledger FAILED row가 먼저 flush된 뒤 exception이 발생한다. orchestration
boundary는 추가 phase를 실행하지 않고 §6.3을 `infra_failure`와 그 row의 exact
class/message로 1회 호출한다.
Codex tool-call 경계가 PowerShell process를 새로 만들면 §2.5 writer와 §5.2
setup/functions를 `$ProcessEntryMode = 'RESUME'`으로 exact 재선언한다.
`ENTRY`를 두 번째로 실행하거나 capsule verifier/TTL을 재실행하지 않는다.
기존 operation log는 append만 하고 truncate 또는 재구성하지 않는다.
새 process에서 null로 초기화된 P0 mtime은 첫
`Assert-FrozenProducerInputs`가 ordinary P0 JSON의 frozen SHA와 before/after
mtime을 재검증한 뒤 exact 값으로 rehydrate한다.

각 process block을 감싸는 Codex 실행 호출은 `timeout_ms >= 300000`을
명시해야 한다. 저자 환경에서 frozen untracked/ignored content-map gate만
약 102.3초가 걸렸으므로 기본 10초 timeout은 허용하지 않는다. 실행 호출은
동일한 PowerShell process를 유지한 채 50초 이하 간격으로 control/status를
yield하는 recurring wait 방식을 사용한다. timeout 때문에 process를 kill하거나
같은 phase를 새 process로 재시작하지 않는다. 실행기가 이 timeout/yield 계약을
제공할 수 없으면 temp root·ledger·P0 생성 전에
`CONTROLLER_TIMEOUT_UNSUPPORTED` infra failure(exit 3)로 STOP한다. 계약을
어기고 외부에서 kill된 실행은 ledger row 부재를 포함해 campaign evidence로
인정하지 않으며, 성공 또는 fail-closed phase 결과로 해석하지 않는다.

### 5.3 Exact dry-run argv

```powershell
$Dry0Args = @(
    '-B', '-m', 'src.cli', 'export-mmi', $Workbook,
    '--sheet', 'SS-TC 0',
    '--dry-run',
    '--include-semi'
)
$Dry1Args = @(
    '-B', '-m', 'src.cli', 'export-mmi', $Workbook,
    '--sheet', 'SS-TC 1',
    '--dry-run',
    '--include-semi'
)

Invoke-CheckedPythonPhase `
    'DRY_SS_TC_0' $Dry0Args `
    (Join-Path $TempRoot 'dry-run-SS-TC-0.combined.txt') `
    $null $null

Invoke-CheckedPythonPhase `
    'DRY_SS_TC_1' $Dry1Args `
    (Join-Path $TempRoot 'dry-run-SS-TC-1.combined.txt') `
    $null $null
```

각 exit은 0이어야 하며 stdout의 `Total: N TCs`가 존재하고 `N > 0`이어야 한다.
결합 출력은 문자열 배열을 LF로 join해 UTF-8/LF temp file에 기록하고 그
canonical SHA-256을 evidence에 저장한다. native process의 원시 stdout/stderr
bytes라고 표기하지 않는다.

### 5.4 Exact isolated-export argv

P0 GREEN과 dry-run 2개 exit 0 뒤에도 `$Out0`, `$Out1`은 존재하지 않아야
하며, 각 해당 producer invocation이 자기 fresh output directory를 만들게 한다.
controller가 미리 만들지 않는다.

```powershell
$Export0Args = @(
    '-B', '-m', 'src.cli', 'export-mmi', $Workbook,
    '--sheet', 'SS-TC 0',
    '--output-dir', $Out0,
    '--include-semi',
    '--export-unrunnable'
)
$Export1Args = @(
    '-B', '-m', 'src.cli', 'export-mmi', $Workbook,
    '--sheet', 'SS-TC 1',
    '--output-dir', $Out1,
    '--include-semi',
    '--export-unrunnable'
)

Invoke-CheckedPythonPhase `
    'EXPORT_SS_TC_0' $Export0Args `
    (Join-Path $TempRoot 'export-SS-TC-0.combined.txt') `
    $null $null

Invoke-CheckedPythonPhase `
    'EXPORT_SS_TC_1' $Export1Args `
    (Join-Path $TempRoot 'export-SS-TC-1.combined.txt') `
    $null $null
```

의도적으로 사용하지 않는 flag:

- `--only-class`: `--include-semi` 집합을 덮어쓸 수 있음
- `--skip-unrunnable`: mismatch row를 조용히 누락시킬 수 있음
- `--overwrite`: stale artifact를 숨김
- 존재하지 않는 `--contract-mode`

두 sheet는 filename collision 격리를 위해 별도 output directory를 사용한다.

### 5.5 Export integrity

1. 두 export exit은 0이어야 한다.
2. 각 output directory의 direct child는 `.yaml` file뿐이어야 한다.
3. dry-run `Total`과 같은 sheet의 exported YAML file count가 같아야 한다.
4. stdout의 `건너뜀`은 0이어야 한다.
5. 각 emitted YAML은 `metadata.source_file == "TC_1.xlsx"`,
   `metadata.source_sheet == expected sheet`, positive integer
   `metadata.source_row`를 가져야 한다.
6. 같은 `(source_sheet, source_row)`가 둘 이상의 emitted YAML에 나타나면
   exit 1이다.
7. P0에 mapping된 12 emitted YAML은 `metadata.runnable is true`이고
   `metadata.has_unresolved_params is false`여야 한다. 그렇지 않으면
   `PRODUCER_RUNNABILITY_GAP`으로 exit 1이다. `--export-unrunnable`은 전체
   capture를 위한 flag일 뿐 acceptance 우회가 아니다.
8. raw file SHA와 parsed semantic SHA를 모두 기록한다.
9. semantic SHA는 deep copy에서 `metadata.exported_at` 하나만 제거한 뒤
   `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',', ':'))`의
   UTF-8 bytes(trailing LF 없음)를 SHA-256한다.
10. inventory relative path는 `SS-TC-0/<filename>` 또는
    `SS-TC-1/<filename>` POSIX form이며 UTF-8 path bytes 순으로 정렬한다.

raw YAML SHA는 `metadata.exported_at` 때문에 run-specific이다. 이 directive는
독립 재실행 byte determinism을 주장하지 않는다. 재실행 비교가 필요할 때의
deterministic surface는 위 semantic SHA뿐이며, 재실행 자체는 별도 승인이다.

### 5.6 Reconciliation

filename으로 join하지 않는다. P0의 `(sheet, physical_row)`를 emitted YAML의
`metadata.source_sheet/source_row`와 exact join한다.

각 blocker step마다 evidence `p1.targets[]`에 다음을 기록한다.

```text
yaml_path
blocker_step_index
workbook_sheet
workbook_physical_row
emitted_yaml_path
emitted_step_index
tracked_tc_name_match
emitted_name_match
procedure_prefix_match
source_content_hash_match
tracked_step_projection
emitted_step_projection
candidate_count
verdict
```

source binding은 정확히 다음 세 조건이다.

1. `emitted.name == p0.yaml_tc_name`
2. `emitted.description == p0.source_procedure[:200]`
3. emitted basename이 frozen exporter 알고리즘
   `_make_filename(p0.yaml_tc_name, p0.source_procedure,
   p0.source_expected)` 재계산값과 exact 일치

세 번째는 legacy document에 없는 expected 입력을 producer filename의 8-hex
content-hash에 결속하는 관찰이며 독립적인 expected 원문 동등성 증명으로
과대 표기하지 않는다.

target step comparison은 `action`, `command`, `expected` 각 field의
`{present: bool, value: parsed_value}`를 비교한다. absent와 explicit null을
같게 취급하지 않는다. tracked blocker projection과 exact 동일한 emitted step을
문서 전체에서 찾고 candidate count가 1이어야 한다. whitespace collapse,
regex 유사도, alias normalization, filename heuristic은 쓰지 않는다.

15/15 target이 unique join되고 위 source binding과 step projection이 확인돼야
exit 0 후보가 된다. mapped document의 전체 ordered step projections와 hash는
`document_step_projection_report[]`에 **report-only, gating=false**로 기록한다.
legacy/canonical alias normalization이 이 reconnaissance에 정의되지 않았으므로
non-target semantic equality 또는 delta 0을 주장하거나 exit gate로 쓰지 않는다.

### 5.7 Exact analysis-only argv

Appendix B source SHA를 확인하고 P0/P1 artifact가 모두 존재한 뒤 아래 1회만
실행한다.

```powershell
$Analyzer = Join-Path $TempRoot 'analyze_provenance.py'
$P0 = Join-Path $TempRoot 'artifact-tool-work\p0_workbook.json'
$Reconciliation = Join-Path $TempRoot 'reconciliation.json'
$AnalyzeArgs = @(
    '-B', $Analyzer,
    '--repo', $Repo,
    '--p0', $P0,
    '--out0', $Out0,
    '--out1', $Out1,
    '--output', $Reconciliation
)
Invoke-CheckedPythonPhase `
    'ANALYZE' $AnalyzeArgs `
    (Join-Path $TempRoot 'analyze.combined.txt') `
    $Reconciliation 'reconciliation_sha256'
```

정상 분석은 mismatch 관찰 여부와 무관하게 analyzer exit 0이고,
`reconciliation.json.reconciled`가 campaign exit 0/1을 결정한다. producer
direct-child type·emitted YAML decode/parse/top-level 오류는 blocking reason으로
기록되어 campaign exit 1이다. verifier argument/P0 JSON 계약, log 문법,
I/O 또는 분석기 내부 오류만 analyzer exit 3이다.

---

## 6. Post-State and Evidence Contract

### 6.1 Post-state invariants

evidence final publish 직전에 다음을 재계산한다.

- capsule raw SHA와 capsule payload copy
- HEAD/origin/ahead/behind와 capsule `repo`
- tracked diff와 staged paths
- raw index fingerprint와 capsule `index`
- directive/spec/generator identity
- 제외 없는 untracked canonical map과 ignored canonical map
- tracked basename `TC_1.xlsx` candidate exact list
- workbook SHA, Git blob, mtime
- frozen audit와 producer actor hashes

entry와 하나라도 다르면 exit 2다. preflight 뒤 drift이면 측정된 temp hashes와
drift 목록을 status-bearing failure evidence로 publish한다. 허용 evidence path는
ignored라 untracked map에 나타나지 않아야 한다.

### 6.2 Canonical evidence JSON

`PROVENANCE_EVIDENCE.json`은
`json.dumps(ensure_ascii=False, sort_keys=True, separators=(',', ':'))`의 UTF-8
bytes, trailing LF 없음으로 쓴다. timestamp와 temp mtime은 포함하지 않는다.
승인된 exact repo/tool/cwd/argv를 증명하는 absolute path는 포함한다. 다음
top-level field를 정확히 가진다.

```text
schema_version
directive_id
dispatch_envelope
entry
toolchain
producer_actors
workbook
p0
p1
post_state
command_log
write_inventory
verdict
```

필수 내용:

- directive/spec/generator SHA와 blob, capsule SHA/path/issued/expires
- capsule entry payload와 독립 재계산한 Git/index/untracked/ignored identities
- artifact-tool actual version과 inspect/render result hashes
- workbook sheet/header/cell/formula/style/topology evidence
- 15 target / 12 row mapping
- exact producer argv, cwd, exit, canonical combined-output SHA
- emitted raw/semantic inventory
- target reconciliation과 non-target ordered projection report(`gating=false`)
- exact ordered command/tool-call log
- exact repo file writes, allowed directory-creation events, external
  temp-root creation event와 child file/directory write inventory
- verdict code, label, blocking reasons

array ordering도 contract다.

- `p0.mappings`: `(yaml_path UTF-8 bytes, first blocker_step_index)`
- `p1.inventories`: POSIX relative path UTF-8 bytes
- `p1.targets`: `(yaml_path UTF-8 bytes, blocker_step_index)`
- `document_step_projection_report`: yaml_path UTF-8 bytes
- `command_log`: 실제 실행 순서
- `blocking_reasons`: `(code, path, message)` Unicode codepoint order

evidence 자신의 SHA는 JSON 안에 넣지 않는다. no-overwrite hard-link publish와
final byte/hash 재검증 뒤 raw SHA-256과 Git blob을 외부 완료 보고에서 고정한다.

`command_log`의 ledger rows는 §2.5 status 의미를 그대로 쓴다. 마지막
`ASSEMBLE` row만 `status:"EVIDENCE_WRITTEN"`과 `campaign_exit`을 사용하며,
nonzero campaign verdict를 phase execution failure로 오표기하지 않는다.

### 6.3 Exact evidence assembler invocation

Appendix C는 host preflight GREEN 직후 Appendix B와 함께 exact external-temp
bytes로 생성하고 source SHA를 확인한다. P0/P1/analyzer가 모두 정상 종료하면
`--status measured`; 그 전 어느 phase든 runtime/process/IO 실패면
`--status infra_failure`다. P0 candidate mismatch도 `measured`이며
`--last-phase P0_ARTIFACT_CAPTURE`다. measured invocation은 error option 두 개를
아예 전달하지 않는다. infra failure에서만 nonempty `--error-class`와
`--error-message`로 실제 첫 실패 하나를 전달한다.

```powershell
$Assembler = Join-Path $TempRoot 'assemble_evidence.py'
$AssembleArgs = @(
    '-B', $Assembler,
    '--directive-sha', '<DISPATCH_EXACT_DIRECTIVE_RAW_SHA256>',
    '--directive-blob', '<DISPATCH_EXACT_DIRECTIVE_GIT_BLOB>',
    '--capsule-sha256', '<DISPATCH_EXACT_LOWERCASE_CAPSULE_SHA256>',
    '--appendix-a-sha', '784fdeb72c6878b5be16ae8f08c0f52cfc1f3e82a3241824918803d14fe7eaf9',
    '--appendix-b-sha', '6ab74d52b3765d6300cd4f9f90a15d5cbf2442af2b94a798006d2042264c2e5c',
    '--appendix-c-sha', '258c1c96739d782ef56040fb95fa390384752a75f9623d4a79ab07c99c72013e',
    '--status', $Status,
    '--last-phase', $LastPhase
)
if ($Status -eq 'infra_failure') {
    if ([string]::IsNullOrEmpty($ErrorClass) -or
        [string]::IsNullOrEmpty($ErrorMessage)) {
        throw 'infra_failure requires nonempty first-failure fields'
    }
    $AssembleArgs += @(
        '--error-class', $ErrorClass,
        '--error-message', $ErrorMessage
    )
} elseif ($Status -ne 'measured') {
    throw "unsupported assembler status: $Status"
}
& $Python @AssembleArgs
$CampaignExit = $LASTEXITCODE
```

angle-bracket token은 임의 placeholder가 아니다. dispatch envelope의 exact
값과 실제 first-failure 값으로만 치환한다. assembler
exit이 campaign exit이다. assembler 자체가 실패하면 console의 exact
class/message와 함께 exit 3으로 STOP하며 재실행·수기 evidence 생성은 금지한다.

---

## 7. Exit Contract

| exit | label | 의미 | final evidence |
|---:|---|---|---|
| 0 | `PROVENANCE_RECONCILED` | P0 15/12 unique + P1 source/target 15/15 관계 재현 + mapped 12 docs runnable/unresolved-free | publish |
| 1 | `PROVENANCE_MISMATCH` | 유효한 측정에서 candidate 0/2+, view 불일치, producer 누락·collision·semantic mismatch 관찰 | publish |
| 2 | `INPUT_INVALID` | envelope/capsule/TTL/HEAD/index/untracked/hash/path/sheet/tool version 입력 계약 위반 | preflight=`—`; post-preflight=publish |
| 3 | `INFRA_FAILURE` | artifact runtime·formula/style visibility·Git·IO·producer process 측정 실패 | Appendix C exact hash-verified/invocable + ledger append 가능 시 publish; materialization/ledger-append/assembler 자체 실패는 fileless |

producer process nonzero는 semantic mismatch로 강등하지 않고 exit 3이다.

모든 exit은 STOP이다.

---

## 8. Unconditional STOP and Report

다음은 어떤 결과에서도 금지한다.

- P2 방향 결정
- workbook/YAML/source 수정
- canonical harness 또는 CLI flag 구현
- remediation manifest/verifier/TDD 착수
- device/ADB
- staging/commit/push
- 기존 untracked backlog 정리·원복·삭제
- temp/evidence overwrite 또는 재실행 baseline 자동 갱신

완료 보고 형식:

```text
Directive ID:
Dispatch envelope:
Capsule SHA / path / issued / expires:
Entry HEAD / origin / ahead-behind:
Index fingerprint:
Untracked invariant count / SHA:
Workbook SHA / blob / mtime before-after:
Artifact-tool actual version:
Module route fs gate (capsule vs live):
Module route probe: negative-control / add invoked / submissions / timeout_ms:
P0 mappings: target steps / YAML rows / candidate anomalies:
P0 sheet distribution:
P1 producer mode:
P1 exact argv exits / combined-output SHA:
P1 dry-run totals / exported counts / skipped:
P1 target reconciliation:
P1 mapped docs runnable / unresolved-free:
P1 non-target projection report (gating=false):
Exit / label:
Evidence path / raw SHA / Git blob:
Tracked / staged delta:
Forbidden command count:
Next gate:
```

보고 어휘:

- P0/P1 측정 성공은 `provenance reconciled` 또는 `provenance mismatch`
- `validate PASS`, `runtime PASS`, `manual evidence observed`,
  `BUG-GAP observed`로 바꾸어 쓰지 않는다
- device 결과나 canonical runtime 의미를 주장하지 않는다

fileless exit 2/3이면 `Evidence path / raw SHA / Git blob: — / — / —`로
보고한다. exit 0이면 사용자 P2 결정 대기, exit 1이면 mismatch evidence 리뷰
대기, exit 2/3이면 입력 또는 인프라 재승인 대기 상태로 STOP한다.

---

## Appendix A — Exact artifact-tool capture source

아래 code fence 내부 source만 `node_repl.js`에 단 한 번 제출한다. source bytes는
UTF-8, LF, 마지막 `})();` 뒤 trailing LF 1개다.

**Expected source SHA-256:** `784fdeb72c6878b5be16ae8f08c0f52cfc1f3e82a3241824918803d14fe7eaf9`

```javascript
await (async () => {
  const fs = await import("node:fs/promises");
  const path = await import("node:path");
  const crypto = await import("node:crypto");
  const artifact = await import("@oai/artifact-tool");
  const { FileBlob, SpreadsheetFile } = artifact;

  const REPO = "C:/Users/momen/Projects/tc-runner";
  const WORKBOOK = `${REPO}/tc_samples/TC_1.xlsx`;
  const TEMP_ROOT =
    "C:/tmp/tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1";
  const WORK_ROOT = `${TEMP_ROOT}/artifact-tool-work`;
  const OUTPUT = `${WORK_ROOT}/p0_workbook.json`;
  const SHEETS = ["SS-TC 0", "SS-TC 1"];
  const TARGETS = [
    ["exported_ss_call/SS_TC01_permission_denied.yaml",
      "SS_TC01_permission_denied", [10, 11], "SS-TC 1"],
    ["exported_ss_call/SS_TC02_permission_allow_idle.yaml",
      "SS_TC02_permission_allow_idle", [11], "SS-TC 1"],
    ["exported_ss_call/SS_TC03_ringing_permission.yaml",
      "SS_TC03_ringing_permission", [15], "SS-TC 1"],
    ["exported_ss_call/SS_TC04_offhook_seed_recovery.yaml",
      "SS_TC04_offhook_seed_recovery", [18], "SS-TC 1"],
    ["exported_ss_call/SS_TC05_boundary_values.yaml",
      "SS_TC05_boundary_values", [9], "SS-TC 1"],
    ["exported_ss_call/SS_TC06_missed_rejected.yaml",
      "SS_TC06_missed_rejected", [10, 11], "SS-TC 1"],
    ["exported_ss_call/SS_TC07_short_call_no_false_positive.yaml",
      "SS_TC07_short_call_no_false_positive", [9], "SS-TC 1"],
    ["exported_ss_call/SS_TC09_offhook_permission_banking.yaml",
      "SS_TC09_offhook_permission_banking", [20], "SS-TC 1"],
    ["exported_ss_call/SS_TC0_P0_endcall_crash.yaml",
      "SS_TC0_P0_endcall_crash", [15], "SS-TC 0"],
    ["exported_ss_call/SS_TC10_permission_toggle.yaml",
      "SS_TC10_permission_toggle", [24], "SS-TC 1"],
    ["exported_ss_call/SS_TC11_multi_subscription.yaml",
      "SS_TC11_multi_subscription", [20, 21], "SS-TC 1"],
    ["exported_ss_call/SS_TC12_legacy_path.yaml",
      "SS_TC12_legacy_path", [19], "SS-TC 1"],
  ].map(([yaml_path, yaml_tc_name, blocker_step_indices, sheet]) => ({
    yaml_path, yaml_tc_name, blocker_step_indices, sheet,
  }));
  const HEADER_PATTERNS = [
    ["functionality", /functionality|시험\s*목적|목적/i],
    ["feature_name", /검증\s*항목/i],
    ["precondition", /pre.?condition|사전\s*조건/i],
    ["procedure", /test\s*procedure|재현\s*절차|시험\s*절차/i],
    ["expected", /expected\s*result|기대\s*결과|예상\s*로그|판정\s*기준/i],
    ["priority", /priority|우선순위/i],
    ["no", /tc\s*id|번호/i],
  ];

  const sha = (value) =>
    crypto.createHash("sha256").update(value).digest("hex");
  function normalize(value) {
    if (value instanceof Date) return value.toISOString();
    if (typeof value === "bigint") return value.toString();
    if (Array.isArray(value)) return value.map(normalize);
    if (value && typeof value === "object") {
      const result = {};
      for (const key of Object.keys(value).sort()) {
        result[key] = normalize(value[key]);
      }
      return result;
    }
    return value;
  }
  const canonicalBytes = (value) =>
    Buffer.from(JSON.stringify(normalize(value)), "utf8");
  function safeStr(value) {
    if (value === null || value === undefined) return "";
    if (value === true) return "True";
    if (value === false) return "False";
    if (typeof value === "string") return value.trim();
    if (typeof value === "number" && Number.isSafeInteger(value)) {
      return String(value);
    }
    throw new Error(
      `loader-equivalent string conversion unsupported: ${typeof value}`,
    );
  }
  const normalizeHeader = (value) =>
    safeStr(value).split(/\s+/u).filter(Boolean).join(" ");
  function loaderValue(values, formulas, row, col) {
    const formula = formulas?.[row]?.[col];
    return typeof formula === "string" && formula.startsWith("=")
      ? formula
      : values?.[row]?.[col] ?? null;
  }
  function columnName(index0) {
    let value = index0 + 1;
    let result = "";
    while (value > 0) {
      value -= 1;
      result = String.fromCharCode(65 + (value % 26)) + result;
      value = Math.floor(value / 26);
    }
    return result;
  }
  function columnNumber(name) {
    let result = 0;
    for (const char of name) {
      result = result * 26 + char.charCodeAt(0) - 64;
    }
    return result;
  }
  function expandMatrix(matrix, startRow0, startCol0, height, width) {
    const expanded = Array.from(
      { length: height },
      () => Array(width).fill(null),
    );
    for (let row = 0; row < matrix.length; row += 1) {
      for (let col = 0; col < matrix[row].length; col += 1) {
        expanded[startRow0 + row][startCol0 + col] = matrix[row][col];
      }
    }
    return expanded;
  }
  function ndjson(result, label, maxChars) {
    if (!result || typeof result.ndjson !== "string") {
      throw new Error(`${label}: deterministic ndjson unavailable`);
    }
    const lines = result.ndjson.trim().split(/\r?\n/u);
    if (
      result.ndjson.trim().length === 0 ||
      lines.some((line) => line.trim().length === 0)
    ) {
      throw new Error(`${label}: empty ndjson evidence`);
    }
    const records = [];
    for (const line of lines) {
      try {
        const record = JSON.parse(line);
        if (
          record === null ||
          typeof record !== "object" ||
          Array.isArray(record) ||
          Object.keys(record).length === 0
        ) {
          throw new Error("record is not a nonempty object");
        }
        records.push(record);
      } catch (error) {
        throw new Error(
          `${label}: invalid ndjson line: ${error?.message ?? error}`,
        );
      }
    }
    if (
      result.truncated === true ||
      result.isTruncated === true ||
      result.wasTruncated === true ||
      result.ndjson.length >= maxChars ||
      /"(?:truncated|isTruncated|wasTruncated)"\s*:\s*true/iu
        .test(result.ndjson) ||
      /\boutput\s+truncated\b/iu.test(result.ndjson)
    ) {
      throw new Error(`${label}: inspect output truncated`);
    }
    return result.ndjson;
  }
  const compareUtf8 = (left, right) =>
    Buffer.compare(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));

  if (path.resolve(nodeRepl.cwd).replaceAll("\\", "/") !== REPO) {
    throw new Error(`unexpected nodeRepl.cwd: ${nodeRepl.cwd}`);
  }
  if (
    typeof FileBlob !== "function" ||
    typeof SpreadsheetFile !== "function" ||
    typeof FileBlob.load !== "function" ||
    typeof SpreadsheetFile.importXlsx !== "function"
  ) {
    throw new Error("artifact-tool API surface unavailable");
  }
  await fs.mkdir(WORK_ROOT, { recursive: false });
  const workbookMtimeBeforeNs =
    (await fs.stat(WORKBOOK, { bigint: true })).mtimeNs.toString();
  const workbookRawShaBefore = sha(await fs.readFile(WORKBOOK));
  const workbook = await SpreadsheetFile.importXlsx(
    await FileBlob.load(WORKBOOK),
  );
  const sheetOverview = ndjson(
    await workbook.inspect({
      kind: "sheet", include: "id,name", maxChars: 20000,
    }),
    "sheet overview", 20000,
  );
  const sheetResults = [];
  const allMappings = [];

  for (const sheetName of SHEETS) {
    const sheet = workbook.worksheets.getItem(sheetName);
    const used = sheet.getUsedRange();
    const addressRaw = await used.address;
    if (typeof addressRaw !== "string") {
      throw new Error(`${sheetName}: used range address unavailable`);
    }
    const usedAddress = addressRaw.split("!").at(-1).replaceAll("$", "");
    const addressMatch = /^([A-Z]+)(\d+):([A-Z]+)(\d+)$/u.exec(usedAddress);
    if (!addressMatch) throw new Error(`${sheetName}: bad used range address`);
    const startCol0 = columnNumber(addressMatch[1]) - 1;
    const startRow0 = Number.parseInt(addressMatch[2], 10) - 1;
    const endCol = columnNumber(addressMatch[3]);
    const endRow = Number.parseInt(addressMatch[4], 10);
    const usedHeight = endRow - startRow0;
    const usedWidth = endCol - startCol0;
    const rawValues = await used.values;
    const rawFormulas = await used.formulas;
    const rawDisplayFormulas = await used.displayFormulas;
    const rectangular = (matrix) =>
      Array.isArray(matrix) &&
      matrix.length === usedHeight &&
      matrix.every((row) => Array.isArray(row) && row.length === usedWidth);
    if (!rectangular(rawValues) || !rectangular(rawFormulas) ||
        !rectangular(rawDisplayFormulas)) {
      throw new Error(`${sheetName}: value/formula matrices unavailable`);
    }
    const height = endRow;
    const width = endCol;
    const values = expandMatrix(
      rawValues, startRow0, startCol0, height, width,
    );
    const formulas = expandMatrix(
      rawFormulas, startRow0, startCol0, height, width,
    );
    const displayed = expandMatrix(
      rawDisplayFormulas, startRow0, startCol0, height, width,
    );
    if (height === 0 || width === 0) {
      throw new Error(`${sheetName}: empty used range`);
    }

    let headerRow = -1;
    for (let row = 0; row < Math.min(10, height) && headerRow < 0; row += 1) {
      for (let col = 0; col < width && headerRow < 0; col += 1) {
        const text = normalizeHeader(loaderValue(values, formulas, row, col));
        if (HEADER_PATTERNS
          .filter(([key]) => key === "procedure" || key === "functionality")
          .some(([, pattern]) => pattern.test(text))) headerRow = row;
      }
    }
    if (headerRow < 0) throw new Error(`${sheetName}: header unavailable`);
    const columnMap = {};
    for (let col = 0; col < width; col += 1) {
      const text = normalizeHeader(
        loaderValue(values, formulas, headerRow, col),
      );
      for (const [key, pattern] of HEADER_PATTERNS) {
        if (!(key in columnMap) && pattern.test(text)) columnMap[key] = col;
      }
    }
    const functionalityColumn = columnMap.functionality;
    if (Number.isInteger(functionalityColumn) &&
        functionalityColumn >= 2) {
      if (!("no" in columnMap)) columnMap.no = functionalityColumn - 2;
      if (!("feature_name" in columnMap)) {
        columnMap.feature_name = functionalityColumn - 1;
      }
    }
    const fields = [
      "no", "feature_name", "functionality", "precondition",
      "procedure", "expected", "priority",
    ];
    for (const field of fields) {
      if (!(field in columnMap)) {
        throw new Error(`${sheetName}: seven-column header missing: ${field}`);
      }
    }

    let previousFeature = "";
    let previousFunctionality = "";
    let featureAnchorRow = null;
    let functionalityAnchorRow = null;
    const rowInventory = [];
    for (let row = headerRow + 1; row < height; row += 1) {
      const field = (name) =>
        safeStr(loaderValue(values, formulas, row, columnMap[name]));
      const no = field("no");
      const rawFeature = field("feature_name");
      const rawFunctionality = field("functionality");
      const precondition = field("precondition");
      const procedure = field("procedure");
      const expected = field("expected");
      const priority = field("priority");
      if (rawFeature) {
        previousFeature = rawFeature;
        featureAnchorRow = row + 1;
      }
      if (rawFunctionality) {
        previousFunctionality = rawFunctionality;
        functionalityAnchorRow = row + 1;
      }
      if (!procedure && !expected) continue;
      const physicalRow = row + 1;
      const feature = (previousFeature || "UNNAMED")
        .split(/\s+/u).filter(Boolean).join("_");
      rowInventory.push({
        physical_row: physicalRow,
        tc_name: `${no || `ROW${physicalRow}`}_${feature}`,
        source_no: no,
        source_feature_name_raw: rawFeature,
        source_feature_name_effective: previousFeature,
        source_feature_anchor_row: featureAnchorRow,
        source_functionality_raw: rawFunctionality,
        source_functionality_effective: previousFunctionality,
        source_functionality_anchor_row: functionalityAnchorRow,
        source_precondition: precondition,
        source_procedure: procedure,
        source_expected: expected,
        source_priority: priority,
      });
    }

    const provisional = [];
    const relevantCoordinates = new Set();
    for (const field of fields) {
      relevantCoordinates.add(
        `${columnName(columnMap[field])}${headerRow + 1}`,
      );
    }
    for (const target of TARGETS.filter((item) => item.sheet === sheetName)) {
      const candidates = rowInventory.filter(
        (row) => row.tc_name === target.yaml_tc_name,
      );
      const candidate = candidates.length === 1 ? candidates[0] : null;
      const coordinates = [];
      if (candidate) {
        for (const field of fields) {
          const coordinate =
            `${columnName(columnMap[field])}${candidate.physical_row}`;
          coordinates.push(coordinate);
          relevantCoordinates.add(coordinate);
        }
        if (candidate.source_feature_anchor_row !== null) {
          relevantCoordinates.add(
            `${columnName(columnMap.feature_name)}` +
              `${candidate.source_feature_anchor_row}`,
          );
        }
        if (candidate.source_functionality_anchor_row !== null) {
          relevantCoordinates.add(
            `${columnName(columnMap.functionality)}` +
              `${candidate.source_functionality_anchor_row}`,
          );
        }
      }
      provisional.push({ target, candidates, candidate, coordinates });
    }

    for (const item of provisional) {
      const candidate = item.candidate;
      const carryCoordinates = new Set();
      if (candidate) {
        for (const [column, anchorRow] of [
          [columnMap.feature_name, candidate.source_feature_anchor_row],
          [columnMap.functionality, candidate.source_functionality_anchor_row],
        ]) {
          if (anchorRow !== null) {
            for (
              let row = anchorRow;
              row <= candidate.physical_row;
              row += 1
            ) {
              const coordinate = `${columnName(column)}${row}`;
              carryCoordinates.add(coordinate);
              relevantCoordinates.add(coordinate);
            }
          }
        }
      }
      item.carryCoordinates = [...carryCoordinates].sort(compareUtf8);
    }

    const cellEvidence = {};
    for (const coordinate of [...relevantCoordinates].sort(compareUtf8)) {
      const match = /^([A-Z]+)(\d+)$/u.exec(coordinate);
      if (!match) throw new Error(`bad coordinate: ${coordinate}`);
      let columnNumber = 0;
      for (const char of match[1]) {
        columnNumber = columnNumber * 26 + char.charCodeAt(0) - 64;
      }
      const row0 = Number.parseInt(match[2], 10) - 1;
      const col0 = columnNumber - 1;
      const styleNdjson = ndjson(
        await workbook.inspect({
          kind: "computedStyle", sheetId: sheetName,
          range: coordinate, maxChars: 16000,
        }),
        `${sheetName}!${coordinate} computedStyle`, 16000,
      );
      const regionNdjson = ndjson(
        await workbook.inspect({
          kind: "region", sheetId: sheetName,
          range: coordinate, maxChars: 16000,
        }),
        `${sheetName}!${coordinate} region`, 16000,
      );
      cellEvidence[coordinate] = {
        coordinate,
        artifact_value: values?.[row0]?.[col0] ?? null,
        formula: formulas?.[row0]?.[col0] ?? null,
        display_formula_view: displayed?.[row0]?.[col0] ?? null,
        cached_or_displayed_value: null,
        loader_value: loaderValue(values, formulas, row0, col0),
        computed_style_request: {
          kind: "computedStyle", sheetId: sheetName,
          range: coordinate, maxChars: 16000,
        },
        computed_style_ndjson: styleNdjson,
        computed_style_sha256: sha(Buffer.from(styleNdjson, "utf8")),
        region_request: {
          kind: "region", sheetId: sheetName,
          range: coordinate, maxChars: 16000,
        },
        region_ndjson: regionNdjson,
        region_sha256: sha(Buffer.from(regionNdjson, "utf8")),
      };
    }
    for (const {
      target, candidates, candidate, coordinates, carryCoordinates,
    } of provisional) {
      allMappings.push({
        yaml_path: target.yaml_path,
        yaml_tc_name: target.yaml_tc_name,
        blocker_step_indices: target.blocker_step_indices,
        declared_source_file: "TC_1.xlsx",
        declared_source_sheet: target.sheet,
        workbook_sheet: target.sheet,
        workbook_physical_row: candidate?.physical_row ?? null,
        candidate_count: candidates.length,
        join_basis: "exact sheet + computed MMIRow.tc_name",
        source_no: candidate?.source_no ?? null,
        source_feature_name_raw: candidate?.source_feature_name_raw ?? null,
        source_feature_name_effective:
          candidate?.source_feature_name_effective ?? null,
        source_feature_anchor_row:
          candidate?.source_feature_anchor_row ?? null,
        source_functionality_raw:
          candidate?.source_functionality_raw ?? null,
        source_functionality_effective:
          candidate?.source_functionality_effective ?? null,
        source_functionality_anchor_row:
          candidate?.source_functionality_anchor_row ?? null,
        source_precondition: candidate?.source_precondition ?? null,
        source_procedure: candidate?.source_procedure ?? null,
        source_expected: candidate?.source_expected ?? null,
        source_priority: candidate?.source_priority ?? null,
        cells: coordinates.map((coordinate) => cellEvidence[coordinate]),
        cell_region_records: coordinates.map((coordinate) => ({
          coordinate,
          region_request: cellEvidence[coordinate].region_request,
          region_ndjson: cellEvidence[coordinate].region_ndjson,
          region_sha256: cellEvidence[coordinate].region_sha256,
        })),
        carry_forward_cells:
          carryCoordinates.map((coordinate) => cellEvidence[coordinate]),
        verdict: candidates.length === 1 ? "UNIQUE" : "MISMATCH",
      });
    }

    const renderOptions = {
      sheetName, range: usedAddress, scale: 1, format: "png",
    };
    const renderBytes = Buffer.from(
      await (await workbook.render(renderOptions)).arrayBuffer(),
    );
    const pngMagic = Buffer.from("89504e470d0a1a0a", "hex");
    if (
      renderBytes.length <= pngMagic.length ||
      !renderBytes.subarray(0, pngMagic.length).equals(pngMagic)
    ) {
      throw new Error(`${sheetName}: non-PNG or empty render evidence`);
    }
    const renderFinal =
      `${WORK_ROOT}/render-${sheetName.replaceAll(" ", "-")}.png`;
    await fs.writeFile(`${renderFinal}.tmp`, renderBytes, { flag: "wx" });
    await fs.rename(`${renderFinal}.tmp`, renderFinal);
    sheetResults.push({
      sheet_name: sheetName,
      used_range: usedAddress,
      used_start_row: startRow0 + 1,
      used_start_column: startCol0 + 1,
      used_matrix_height: usedHeight,
      used_matrix_width: usedWidth,
      expanded_physical_height: height,
      expanded_physical_width: width,
      header_physical_row: headerRow + 1,
      column_map: columnMap,
      header_cells: fields.map((field) => ({
        field,
        ...cellEvidence[
          `${columnName(columnMap[field])}${headerRow + 1}`
        ],
      })),
      row_inventory: rowInventory,
      render_options: renderOptions,
      render_path: path.posix.relative(TEMP_ROOT, renderFinal),
      render_sha256: sha(renderBytes),
    });
  }

  allMappings.sort((left, right) => {
    const order = compareUtf8(left.yaml_path, right.yaml_path);
    return order || (
      left.blocker_step_indices[0] - right.blocker_step_indices[0]
    );
  });
  const p0BlockingReasons = [];
  if (allMappings.length !== 12) {
    p0BlockingReasons.push({
      code: "P0_CARDINALITY",
      path: "mappings",
      message: `expected=12,observed=${allMappings.length}`,
    });
  }
  for (const mapping of allMappings) {
    if (mapping.candidate_count !== 1) {
      p0BlockingReasons.push({
        code: "P0_UNIQUE_JOIN",
        path: mapping.yaml_path,
        message: `candidate_count=${mapping.candidate_count}`,
      });
    }
  }
  const uniqueRows = new Set(
    allMappings
      .filter((mapping) => mapping.candidate_count === 1)
      .map(
        (mapping) =>
          `${mapping.workbook_sheet}\u0000${mapping.workbook_physical_row}`,
      ),
  );
  if (uniqueRows.size !== 12) {
    p0BlockingReasons.push({
      code: "P0_SOURCE_ROW_UNIQUENESS",
      path: "mappings",
      message: `expected=12,observed=${uniqueRows.size}`,
    });
  }
  const rowDistribution = Object.fromEntries(
    SHEETS.map((sheetName) => [
      sheetName,
      [...uniqueRows].filter(
        (key) => key.startsWith(`${sheetName}\u0000`),
      ).length,
    ]),
  );
  if (
    rowDistribution["SS-TC 0"] !== 1 ||
    rowDistribution["SS-TC 1"] !== 11
  ) {
    p0BlockingReasons.push({
      code: "P0_ROW_DISTRIBUTION",
      path: "mappings",
      message: JSON.stringify(rowDistribution),
    });
  }
  p0BlockingReasons.sort((left, right) => (
    compareUtf8(left.code, right.code) ||
    compareUtf8(left.path, right.path) ||
    compareUtf8(left.message, right.message)
  ));
  const workbookMtimeAfterNs =
    (await fs.stat(WORKBOOK, { bigint: true })).mtimeNs.toString();
  const workbookRawShaAfter = sha(await fs.readFile(WORKBOOK));
  const output = {
    schema_version: 2,
    directive_id: "RB-20260728-shellrc-p0p1",
    workbook_path: "tc_samples/TC_1.xlsx",
    workbook_mtime_before_ns: workbookMtimeBeforeNs,
    workbook_mtime_after_ns: workbookMtimeAfterNs,
    workbook_raw_sha256_before: workbookRawShaBefore,
    workbook_raw_sha256_after: workbookRawShaAfter,
    sheet_overview_ndjson: sheetOverview,
    sheet_overview_sha256: sha(Buffer.from(sheetOverview, "utf8")),
    sheets: sheetResults,
    mappings: allMappings,
    p0_blocking_reasons: p0BlockingReasons,
    reconciled: p0BlockingReasons.length === 0,
  };
  await fs.writeFile(`${OUTPUT}.tmp`, canonicalBytes(output), { flag: "wx" });
await fs.rename(`${OUTPUT}.tmp`, OUTPUT);
})();
```

---

## Appendix B — Exact analysis-only verifier source

아래 code fence 내부 source만 external temp `analyze_provenance.py`로 만든다.
source bytes는 UTF-8, LF, 마지막 line 뒤 trailing LF 1개다.

**Expected source SHA-256:** `6ab74d52b3765d6300cd4f9f90a15d5cbf2442af2b94a798006d2042264c2e5c`

```python
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml


DIRECTIVE_ID = "RB-20260728-shellrc-p0p1"
EXPECTED_REPO = Path(r"C:\Users\momen\Projects\tc-runner")
EXPECTED_TEMP = Path(
    r"C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1"
)
SOURCE_RE = re.compile(r"^TC_1\.xlsx / (SS-TC 0|SS-TC 1)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PNG_MAGIC = bytes.fromhex("89504e470d0a1a0a")
STEP_FIELDS = ("action", "command", "expected")
P0_FIELDS = (
    "no", "feature_name", "functionality", "precondition",
    "procedure", "expected", "priority",
)
TARGETS = (
    ("exported_ss_call/SS_TC01_permission_denied.yaml", (10, 11), "SS-TC 1"),
    ("exported_ss_call/SS_TC02_permission_allow_idle.yaml", (11,), "SS-TC 1"),
    ("exported_ss_call/SS_TC03_ringing_permission.yaml", (15,), "SS-TC 1"),
    ("exported_ss_call/SS_TC04_offhook_seed_recovery.yaml", (18,), "SS-TC 1"),
    ("exported_ss_call/SS_TC05_boundary_values.yaml", (9,), "SS-TC 1"),
    ("exported_ss_call/SS_TC06_missed_rejected.yaml", (10, 11), "SS-TC 1"),
    ("exported_ss_call/SS_TC07_short_call_no_false_positive.yaml", (9,), "SS-TC 1"),
    ("exported_ss_call/SS_TC09_offhook_permission_banking.yaml", (20,), "SS-TC 1"),
    ("exported_ss_call/SS_TC0_P0_endcall_crash.yaml", (15,), "SS-TC 0"),
    ("exported_ss_call/SS_TC10_permission_toggle.yaml", (24,), "SS-TC 1"),
    ("exported_ss_call/SS_TC11_multi_subscription.yaml", (20, 21), "SS-TC 1"),
    ("exported_ss_call/SS_TC12_legacy_path.yaml", (19,), "SS-TC 1"),
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_linklike(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def sha256_file(path: Path) -> str:
    if not path.is_file() or is_linklike(path):
        raise ValueError(f"not an ordinary file: {path}")
    return sha256_bytes(path.read_bytes())


def valid_ndjson(value: object, digest: object) -> bool:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not isinstance(digest, str)
        or SHA256_RE.fullmatch(digest) is None
        or sha256_bytes(value.encode("utf-8")) != digest
    ):
        return False
    lines = value.strip().splitlines()
    if not lines or any(not line.strip() for line in lines):
        return False
    try:
        for line in lines:
            record = json.loads(line)
            if not isinstance(record, dict) or not record:
                return False
    except (json.JSONDecodeError, TypeError):
        return False
    if (
        re.search(
            r'"(?:truncated|isTruncated|wasTruncated)"\s*:\s*true',
            value,
            flags=re.IGNORECASE,
        )
        or re.search(r"\boutput\s+truncated\b", value, flags=re.IGNORECASE)
    ):
        return False
    return True


def loader_value_from_cell(cell: object) -> object:
    if not isinstance(cell, dict):
        raise ValueError("cell evidence is not object")
    required = {
        "artifact_value",
        "formula",
        "display_formula_view",
        "cached_or_displayed_value",
        "loader_value",
    }
    if not required.issubset(cell):
        raise ValueError("cell direct-value evidence keys missing")
    if cell["cached_or_displayed_value"] is not None:
        raise ValueError("cached/displayed value must remain explicit null")
    formula = cell["formula"]
    value = (
        formula
        if isinstance(formula, str) and formula.startswith("=")
        else cell["artifact_value"]
    )
    if not (
        value is None
        or isinstance(value, (str, bool))
        or (
            isinstance(value, int)
            and not isinstance(value, bool)
            and abs(value) <= 9007199254740991
        )
    ):
        raise ValueError("cell loader value type is not JS-safe")
    if cell["loader_value"] != value:
        raise ValueError("cell loader value differs from direct value/formula")
    return value


def valid_cell_evidence(cell: object, sheet_name: str) -> bool:
    try:
        loader_value_from_cell(cell)
    except ValueError:
        return False
    assert isinstance(cell, dict)
    return (
        isinstance(cell.get("coordinate"), str)
        and bool(re.fullmatch(r"[A-Z]+[1-9][0-9]*", cell["coordinate"]))
        and cell.get("computed_style_request") == {
            "kind": "computedStyle",
            "sheetId": sheet_name,
            "range": cell["coordinate"],
            "maxChars": 16000,
        }
        and cell.get("region_request") == {
            "kind": "region",
            "sheetId": sheet_name,
            "range": cell["coordinate"],
            "maxChars": 16000,
        }
        and valid_ndjson(
            cell.get("computed_style_ndjson"),
            cell.get("computed_style_sha256"),
        )
        and valid_ndjson(
            cell.get("region_ndjson"),
            cell.get("region_sha256"),
        )
    )


def valid_region_record(record: object, sheet_name: str) -> bool:
    return (
        isinstance(record, dict)
        and isinstance(record.get("coordinate"), str)
        and bool(re.fullmatch(r"[A-Z]+[1-9][0-9]*", record["coordinate"]))
        and record.get("region_request") == {
            "kind": "region",
            "sheetId": sheet_name,
            "range": record["coordinate"],
            "maxChars": 16000,
        }
        and valid_ndjson(
            record.get("region_ndjson"),
            record.get("region_sha256"),
        )
    )


def valid_render_evidence(sheet: dict[str, Any]) -> bool:
    sheet_name = sheet.get("sheet_name")
    if sheet_name not in {"SS-TC 0", "SS-TC 1"}:
        return False
    relative = f"artifact-tool-work/render-{sheet_name.replace(' ', '-')}.png"
    if sheet.get("render_path") != relative:
        return False
    if sheet.get("render_options") != {
        "sheetName": sheet_name,
        "range": sheet.get("used_range"),
        "scale": 1,
        "format": "png",
    }:
        return False
    render_path = EXPECTED_TEMP / Path(relative)
    if (
        not render_path.is_file()
        or is_linklike(render_path)
        or not isinstance(sheet.get("render_sha256"), str)
        or SHA256_RE.fullmatch(sheet["render_sha256"]) is None
    ):
        return False
    raw = render_path.read_bytes()
    return (
        len(raw) > len(PNG_MAGIC)
        and raw.startswith(PNG_MAGIC)
        and sha256_bytes(raw) == sheet["render_sha256"]
    )


def semantic_sha256(document: dict[str, Any]) -> str:
    view = copy.deepcopy(document)
    metadata = view.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("exported_at", None)
    return sha256_bytes(canonical_bytes(view))


def make_filename(tc_name: str, procedure: str, expected: str) -> str:
    safe = re.sub(r"[^\w가-힣\s-]", "", tc_name)
    safe = re.sub(r"\s+", "_", safe.strip())[:80]
    suffix = hashlib.sha256(
        f"{tc_name}{procedure}{expected}".encode("utf-8")
    ).hexdigest()[:8]
    return f"{safe}_{suffix}.yaml"


def step_projection(step: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        field: {"present": field in step, "value": step.get(field)}
        for field in STEP_FIELDS
    }


def read_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file() or is_linklike(path):
        raise ValueError(f"{path}: YAML is not ordinary file")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level YAML must be mapping")
    return value


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(
        str(right.resolve())
    )


def inventory(
    directory: Path,
    label: str,
    reasons: list[dict[str, str]],
) -> list[dict[str, Any]]:
    if not directory.is_dir() or is_linklike(directory):
        reasons.append(
            {
                "code": "PRODUCER_OUTPUT_DIR",
                "path": label,
                "message": "output directory missing or symlink",
            }
        )
        return []
    items = list(directory.iterdir())
    result = []
    for item in items:
        if is_linklike(item) or not item.is_file() or item.suffix != ".yaml":
            reasons.append(
                {
                    "code": "PRODUCER_OUTPUT_CHILD",
                    "path": f"{label}/{item.name}",
                    "message": "expected regular .yaml direct child",
                }
            )
            continue
        raw = item.read_bytes()
        try:
            document = read_mapping(item)
        except (UnicodeError, yaml.YAMLError, ValueError) as error:
            reasons.append(
                {
                    "code": "PRODUCER_YAML_INVALID",
                    "path": f"{label}/{item.name}",
                    "message": f"{type(error).__name__}: {error}",
                }
            )
            continue
        relative = f"{label}/{item.name}"
        result.append(
            {
                "relative_path": relative,
                "raw_sha256": sha256_bytes(raw),
                "semantic_sha256": semantic_sha256(document),
                "document": document,
            }
        )
    result.sort(key=lambda item: item["relative_path"].encode("utf-8"))
    return result


def add_reason(
    reasons: list[dict[str, str]],
    code: str,
    path: str,
    message: str,
) -> None:
    reasons.append({"code": code, "path": path, "message": message})


def one_count(pattern: str, text: str, label: str) -> int:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one anchored count, got {len(matches)}")
    return int(matches[0])


def column_name(index0: int) -> str:
    value = index0 + 1
    result = ""
    while value > 0:
        value -= 1
        result = chr(65 + value % 26) + result
        value //= 26
    return result


def column_number(name: str) -> int:
    result = 0
    for char in name:
        result = result * 26 + ord(char) - 64
    return result


def p0_safe_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value.strip()
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and abs(value) <= 9007199254740991
    ):
        return str(value)
    raise ValueError(f"unsupported P0 loader value type: {type(value).__name__}")


def check_sheet_internal(
    sheet: dict[str, Any],
    reasons: list[dict[str, str]],
) -> bool:
    name = sheet.get("sheet_name")
    column_map = sheet.get("column_map")
    header_row = sheet.get("header_physical_row")
    used_range = sheet.get("used_range")
    ok = True
    if (
        not isinstance(name, str)
        or not isinstance(column_map, dict)
        or set(column_map) != set(P0_FIELDS)
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in column_map.values()
        )
        or len(set(column_map.values())) != len(P0_FIELDS)
        or isinstance(header_row, bool)
        or not isinstance(header_row, int)
        or header_row <= 0
    ):
        add_reason(
            reasons, "P0_SHEET_INTERNAL", str(name),
            "column map/header contract mismatch",
        )
        return False
    address = re.fullmatch(
        r"([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)",
        used_range if isinstance(used_range, str) else "",
    )
    if address is None:
        add_reason(
            reasons, "P0_SHEET_INTERNAL", name, "used range invalid",
        )
        return False
    start_col = column_number(address.group(1))
    start_row = int(address.group(2))
    end_col = column_number(address.group(3))
    end_row = int(address.group(4))
    expected_shape = {
        "used_start_row": start_row,
        "used_start_column": start_col,
        "used_matrix_height": end_row - start_row + 1,
        "used_matrix_width": end_col - start_col + 1,
        "expanded_physical_height": end_row,
        "expanded_physical_width": end_col,
    }
    for field, expected in expected_shape.items():
        if sheet.get(field) != expected:
            add_reason(
                reasons, "P0_SHEET_INTERNAL", f"{name}:{field}",
                f"expected={expected},observed={sheet.get(field)!r}",
            )
            ok = False
    headers = sheet.get("header_cells")
    if not isinstance(headers, list):
        return False
    expected_header_coordinates = [
        f"{column_name(column_map[field])}{header_row}"
        for field in P0_FIELDS
    ]
    if (
        [cell.get("field") for cell in headers if isinstance(cell, dict)]
        != list(P0_FIELDS)
        or [
            cell.get("coordinate") for cell in headers
            if isinstance(cell, dict)
        ] != expected_header_coordinates
    ):
        add_reason(
            reasons, "P0_SHEET_INTERNAL", f"{name}:headers",
            "header field/coordinate relation mismatch",
        )
        ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--p0", type=Path, required=True)
    parser.add_argument("--out0", type=Path, required=True)
    parser.add_argument("--out1", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    expected_paths = (
        (args.repo, EXPECTED_REPO, "repo"),
        (args.p0, EXPECTED_TEMP / "artifact-tool-work" /
         "p0_workbook.json", "p0"),
        (args.out0, EXPECTED_TEMP / "SS-TC-0", "out0"),
        (args.out1, EXPECTED_TEMP / "SS-TC-1", "out1"),
        (args.output, EXPECTED_TEMP / "reconciliation.json", "output"),
    )
    for actual, expected, label in expected_paths:
        if not same_path(actual, expected):
            raise ValueError(f"{label}: unexpected path {actual}")
    temporary = args.output.with_suffix(".json.tmp")
    if args.output.exists() or temporary.exists():
        raise FileExistsError("reconciliation output already exists")

    p0 = json.loads(args.p0.read_text(encoding="utf-8"))
    if p0.get("directive_id") != DIRECTIVE_ID:
        raise ValueError("P0 directive_id mismatch")
    mappings = p0.get("mappings")
    if not isinstance(mappings, list):
        raise ValueError("P0 mappings must be list")
    mapping_by_path = {
        item.get("yaml_path"): item
        for item in mappings
        if isinstance(item, dict) and isinstance(item.get("yaml_path"), str)
    }
    reasons: list[dict[str, str]] = []
    if len(mappings) != 12 or len(mapping_by_path) != 12:
        add_reason(
            reasons, "P0_CARDINALITY", "p0.mappings",
            "expected 12 unique YAML mappings",
        )
    if (
        p0.get("reconciled") is not True
        or p0.get("p0_blocking_reasons") != []
    ):
        add_reason(
            reasons, "P0_GATE_STATE", "p0",
            "analyzer requires reconciled P0 with no blocking reasons",
        )
    sheets = p0.get("sheets")
    if not valid_ndjson(
        p0.get("sheet_overview_ndjson"),
        p0.get("sheet_overview_sha256"),
    ):
        add_reason(
            reasons, "P0_SHEET_OVERVIEW_EVIDENCE", "p0",
            "sheet overview NDJSON is empty, invalid, or hash-mismatched",
        )
    valid_sheets = (
        isinstance(sheets, list)
        and all(isinstance(item, dict) for item in sheets)
        and [item.get("sheet_name") for item in sheets]
        == ["SS-TC 0", "SS-TC 1"]
    )
    if not valid_sheets:
        add_reason(
            reasons, "P0_SHEETS", "p0.sheets",
            "expected exact ordered sheets SS-TC 0, SS-TC 1",
        )
        sheets = []
    elif any(
        not isinstance(sheet.get("header_cells"), list)
        or len(sheet["header_cells"]) != 7
        or any(
            not valid_cell_evidence(cell, sheet["sheet_name"])
            for cell in sheet["header_cells"]
        )
        or not valid_render_evidence(sheet)
        for sheet in sheets
    ):
        add_reason(
            reasons, "P0_HEADER_EVIDENCE", "p0.sheets",
            "expected seven nonempty inspect cells and a hash-matched PNG",
        )
    sheet_by_name = {
        sheet["sheet_name"]: sheet
        for sheet in sheets
        if isinstance(sheet, dict)
    }
    for sheet in sheets:
        check_sheet_internal(sheet, reasons)

    target_keys = [
        (path, index)
        for path, indices, _sheet in TARGETS
        for index in indices
    ]
    if len(target_keys) != 15 or len(set(target_keys)) != 15:
        raise ValueError("embedded target manifest is invalid")
    if any(index < 1 for _path, index in target_keys):
        raise ValueError("embedded target index is not 1-based")

    inventories = inventory(args.out0, "SS-TC-0", reasons) + inventory(
        args.out1, "SS-TC-1", reasons
    )
    inventories.sort(key=lambda item: item["relative_path"].encode("utf-8"))
    producer_counts = []
    for label, stem in (
        ("SS-TC-0", "SS-TC-0"),
        ("SS-TC-1", "SS-TC-1"),
    ):
        dry_text = (
            EXPECTED_TEMP / f"dry-run-{stem}.combined.txt"
        ).read_text(encoding="utf-8")
        export_text = (
            EXPECTED_TEMP / f"export-{stem}.combined.txt"
        ).read_text(encoding="utf-8")
        total = one_count(
            r"^Total: ([1-9][0-9]*) TCs$", dry_text,
            f"{label} dry total",
        )
        created = one_count(
            r"^  생성      : ([0-9]+)개$", export_text,
            f"{label} created",
        )
        skipped = one_count(
            r"^  건너뜀    : ([0-9]+)개$", export_text,
            f"{label} skipped",
        )
        inventory_count = sum(
            1 for item in inventories
            if item["relative_path"].startswith(f"{label}/")
        )
        producer_counts.append(
            {
                "sheet_label": label,
                "dry_total": total,
                "created": created,
                "skipped": skipped,
                "inventory_count": inventory_count,
            }
        )
        if not (
            total == created == inventory_count
            and skipped == 0
        ):
            add_reason(
                reasons, "PRODUCER_COUNT",
                label,
                f"total={total},created={created}," +
                f"inventory={inventory_count},skipped={skipped}",
            )
    emitted_by_source: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = {}
    for item in inventories:
        metadata = item["document"].get("metadata")
        if not isinstance(metadata, dict):
            add_reason(
                reasons, "EMITTED_METADATA", item["relative_path"],
                "metadata is not mapping",
            )
            continue
        sheet = metadata.get("source_sheet")
        row = metadata.get("source_row")
        if (
            metadata.get("source_file") != "TC_1.xlsx"
            or sheet not in {"SS-TC 0", "SS-TC 1"}
            or isinstance(row, bool)
            or not isinstance(row, int)
            or row <= 0
        ):
            add_reason(
                reasons, "EMITTED_SOURCE", item["relative_path"],
                "invalid source metadata",
            )
            continue
        emitted_by_source.setdefault((sheet, row), []).append(item)
    for source, items in emitted_by_source.items():
        if len(items) != 1:
            add_reason(
                reasons, "EMITTED_SOURCE_COLLISION",
                f"{source[0]}:{source[1]}",
                f"candidate_count={len(items)}",
            )

    targets: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []
    mapped_document_status: list[dict[str, Any]] = []
    mapped_source_keys: list[tuple[str, int]] = []
    for yaml_path, blocker_indices, expected_sheet in TARGETS:
        tracked = read_mapping(args.repo / Path(yaml_path))
        source = tracked.get("metadata", {}).get("source")
        match = SOURCE_RE.fullmatch(source) if isinstance(source, str) else None
        if match is None or match.group(1) != expected_sheet:
            add_reason(
                reasons, "TRACKED_SOURCE", yaml_path,
                f"invalid source: {source!r}",
            )
        mapping = mapping_by_path.get(yaml_path)
        if not isinstance(mapping, dict):
            add_reason(
                reasons, "P0_MAPPING_MISSING", yaml_path, "mapping missing",
            )
            continue
        if mapping.get("blocker_step_indices") != list(blocker_indices):
            add_reason(
                reasons, "P0_TARGET_INDICES", yaml_path,
                f"observed={mapping.get('blocker_step_indices')!r}",
            )
        if (
            mapping.get("declared_source_file") != "TC_1.xlsx"
            or mapping.get("declared_source_sheet") != expected_sheet
        ):
            add_reason(
                reasons, "P0_DECLARED_SOURCE", yaml_path,
                "declared source file/sheet mismatch",
            )
        cells = mapping.get("cells")
        carry_cells = mapping.get("carry_forward_cells")
        region_records = mapping.get("cell_region_records")
        if (
            not isinstance(cells, list)
            or len(cells) != 7
            or any(
                not valid_cell_evidence(cell, expected_sheet)
                for cell in cells
            )
            or not isinstance(carry_cells, list)
            or not carry_cells
            or any(
                not valid_cell_evidence(cell, expected_sheet)
                for cell in carry_cells
            )
            or not isinstance(region_records, list)
            or len(region_records) != 7
            or any(
                not valid_region_record(record, expected_sheet)
                for record in region_records
            )
        ):
            add_reason(
                reasons, "P0_CELL_EVIDENCE", yaml_path,
                "cell/carry/region evidence incomplete",
            )
        try:
            sheet_record = sheet_by_name[expected_sheet]
            column_map = sheet_record["column_map"]
            physical_row = mapping.get("workbook_physical_row")
            if (
                isinstance(physical_row, bool)
                or not isinstance(physical_row, int)
                or physical_row <= 0
                or not isinstance(cells, list)
                or not isinstance(carry_cells, list)
                or not isinstance(region_records, list)
            ):
                raise ValueError("mapping shape unavailable")
            expected_coordinates = [
                f"{column_name(column_map[field])}{physical_row}"
                for field in P0_FIELDS
            ]
            observed_coordinates = [
                cell.get("coordinate")
                for cell in cells if isinstance(cell, dict)
            ]
            if observed_coordinates != expected_coordinates:
                raise ValueError("semantic cell coordinates differ")
            source_fields = (
                "source_no",
                "source_feature_name_raw",
                "source_functionality_raw",
                "source_precondition",
                "source_procedure",
                "source_expected",
                "source_priority",
            )
            for cell, source_field in zip(
                cells, source_fields, strict=True
            ):
                if (
                    p0_safe_str(loader_value_from_cell(cell))
                    != mapping.get(source_field)
                ):
                    raise ValueError(
                        f"{source_field} differs from loader cell"
                    )
            region_by_coordinate = {
                record.get("coordinate"): record
                for record in region_records
                if isinstance(record, dict)
            }
            if (
                len(region_by_coordinate) != len(expected_coordinates)
                or set(region_by_coordinate) != set(expected_coordinates)
            ):
                raise ValueError("region coordinate set differs")
            cell_by_coordinate = {
                cell["coordinate"]: cell
                for cell in cells if isinstance(cell, dict)
            }
            for coordinate in expected_coordinates:
                cell = cell_by_coordinate[coordinate]
                record = region_by_coordinate[coordinate]
                for field in (
                    "region_request", "region_ndjson", "region_sha256",
                ):
                    if record.get(field) != cell.get(field):
                        raise ValueError(
                            f"{coordinate} region record differs"
                        )
            carry_by_coordinate = {
                cell.get("coordinate"): cell
                for cell in carry_cells if isinstance(cell, dict)
            }
            if len(carry_by_coordinate) != len(carry_cells):
                raise ValueError("carry coordinate duplicate")
            expected_carry_coordinates = []
            for (
                column_field, anchor_field, effective_field,
            ) in (
                (
                    "feature_name", "source_feature_anchor_row",
                    "source_feature_name_effective",
                ),
                (
                    "functionality", "source_functionality_anchor_row",
                    "source_functionality_effective",
                ),
            ):
                anchor = mapping.get(anchor_field)
                if anchor is None:
                    final_effective = ""
                    row_range = ()
                elif (
                    isinstance(anchor, bool)
                    or not isinstance(anchor, int)
                    or anchor <= 0
                    or anchor > physical_row
                ):
                    raise ValueError(f"{anchor_field} invalid")
                else:
                    final_effective = ""
                    row_range = range(anchor, physical_row + 1)
                nonblank_rows = []
                for row in row_range:
                    coordinate = (
                        f"{column_name(column_map[column_field])}{row}"
                    )
                    expected_carry_coordinates.append(coordinate)
                    if coordinate not in carry_by_coordinate:
                        raise ValueError(
                            f"carry cell missing: {coordinate}"
                        )
                    value = p0_safe_str(loader_value_from_cell(
                        carry_by_coordinate[coordinate]
                    ))
                    if value:
                        nonblank_rows.append(row)
                        final_effective = value
                if anchor is not None and nonblank_rows != [anchor]:
                    raise ValueError(
                        f"{anchor_field} is not nearest preceding nonblank"
                    )
                if final_effective != mapping.get(effective_field):
                    raise ValueError(
                        f"{effective_field} carry derivation differs"
                    )
            if set(carry_by_coordinate) != set(expected_carry_coordinates):
                raise ValueError("carry coordinate set differs")
            expected_tc_name = (
                mapping.get("source_no") or f"ROW{physical_row}"
            ) + "_" + re.sub(
                r"\s+", "_",
                mapping.get("source_feature_name_effective") or "UNNAMED",
            )
            if mapping.get("yaml_tc_name") != expected_tc_name:
                raise ValueError("MMIRow.tc_name derivation differs")
            row_inventory = sheet_record.get("row_inventory")
            row_matches = [
                row for row in row_inventory
                if isinstance(row, dict)
                and row.get("physical_row") == physical_row
            ] if isinstance(row_inventory, list) else []
            if len(row_matches) != 1:
                raise ValueError("row inventory join is not unique")
            row_record = row_matches[0]
            inventory_bindings = {
                "tc_name": "yaml_tc_name",
                "source_no": "source_no",
                "source_feature_name_raw": "source_feature_name_raw",
                "source_feature_name_effective":
                    "source_feature_name_effective",
                "source_feature_anchor_row": "source_feature_anchor_row",
                "source_functionality_raw": "source_functionality_raw",
                "source_functionality_effective":
                    "source_functionality_effective",
                "source_functionality_anchor_row":
                    "source_functionality_anchor_row",
                "source_precondition": "source_precondition",
                "source_procedure": "source_procedure",
                "source_expected": "source_expected",
                "source_priority": "source_priority",
            }
            if any(
                row_record.get(row_field) != mapping.get(mapping_field)
                for row_field, mapping_field in inventory_bindings.items()
            ):
                raise ValueError("row inventory fields differ from mapping")
        except (KeyError, TypeError, ValueError) as error:
            add_reason(
                reasons, "P0_INTERNAL_CONSISTENCY", yaml_path,
                f"{type(error).__name__}: {error}",
            )
        p0_sheet = mapping.get("workbook_sheet")
        p0_row = mapping.get("workbook_physical_row")
        if (
            mapping.get("candidate_count") != 1
            or p0_sheet != expected_sheet
            or isinstance(p0_row, bool)
            or not isinstance(p0_row, int)
            or p0_row <= 0
        ):
            add_reason(
                reasons, "P0_UNIQUE_JOIN", yaml_path,
                "candidate_count/source row invalid",
            )
            continue
        source_key = (p0_sheet, p0_row)
        mapped_source_keys.append(source_key)
        emitted_candidates = emitted_by_source.get(source_key, [])
        if len(emitted_candidates) != 1:
            add_reason(
                reasons, "P1_SOURCE_JOIN", yaml_path,
                f"{p0_sheet}:{p0_row} " +
                f"candidate_count={len(emitted_candidates)}",
            )
            continue
        emitted_item = emitted_candidates[0]
        emitted = emitted_item["document"]
        metadata = emitted.get("metadata")
        emitted_steps = emitted.get("steps")
        tracked_steps = tracked.get("steps")
        if not isinstance(metadata, dict):
            add_reason(
                reasons, "EMITTED_METADATA", yaml_path,
                "emitted metadata is not mapping",
            )
            continue
        if not isinstance(emitted_steps, list) or not all(
            isinstance(step, dict) for step in emitted_steps
        ):
            add_reason(
                reasons, "EMITTED_STEPS_INVALID", yaml_path,
                "emitted steps must be list of mappings",
            )
            continue
        if not isinstance(tracked_steps, list) or not all(
            isinstance(step, dict) for step in tracked_steps
        ):
            raise ValueError(f"{yaml_path}: tracked steps invalid")

        tc_name = mapping.get("yaml_tc_name")
        procedure = mapping.get("source_procedure")
        expected = mapping.get("source_expected")
        if not all(
            isinstance(value, str)
            for value in (tc_name, procedure, expected)
        ):
            raise ValueError(f"{yaml_path}: P0 source strings unavailable")
        if tracked.get("tc_name") != tc_name:
            add_reason(
                reasons, "TRACKED_TC_NAME", yaml_path,
                "tracked tc_name differs from P0 mapping",
            )
        tracked_name_match = tracked.get("tc_name") == tc_name
        bindings = {
            "emitted_name_match": emitted.get("name") == tc_name,
            "procedure_prefix_match":
                emitted.get("description") == procedure[:200],
            "source_content_hash_match":
                Path(emitted_item["relative_path"]).name
                == make_filename(tc_name, procedure, expected),
        }
        for field, field_match in bindings.items():
            if not field_match:
                add_reason(
                    reasons, "SOURCE_BINDING",
                    f"{yaml_path}:{field}", "exact match failed",
                )
        if metadata.get("runnable") is not True:
            add_reason(
                reasons, "PRODUCER_RUNNABILITY_GAP",
                f"{yaml_path}:runnable", "expected true",
            )
        if metadata.get("has_unresolved_params") is not False:
            add_reason(
                reasons, "PRODUCER_RUNNABILITY_GAP",
                f"{yaml_path}:has_unresolved_params", "expected false",
            )
        document_green = (
            tracked_name_match
            and all(bindings.values())
            and metadata.get("runnable") is True
            and metadata.get("has_unresolved_params") is False
        )
        mapped_document_status.append(
            {
                "yaml_path": yaml_path,
                "emitted_yaml_path": emitted_item["relative_path"],
                "tracked_tc_name_match": tracked_name_match,
                **bindings,
                "runnable": metadata.get("runnable"),
                "has_unresolved_params":
                    metadata.get("has_unresolved_params"),
                "verdict": "RECONCILED"
                if document_green else "MISMATCH",
            }
        )

        for blocker_index in blocker_indices:
            if blocker_index > len(tracked_steps):
                raise ValueError(
                    f"{yaml_path}: blocker index {blocker_index} out of range"
                )
            tracked_projection = step_projection(
                tracked_steps[blocker_index - 1]
            )
            candidate_indices = [
                index
                for index, step in enumerate(emitted_steps, start=1)
                if step_projection(step) == tracked_projection
            ]
            if len(candidate_indices) != 1:
                add_reason(
                    reasons, "TARGET_STEP_JOIN",
                    f"{yaml_path}:{blocker_index}",
                    f"candidate_count={len(candidate_indices)}",
                )
            targets.append(
                {
                    "yaml_path": yaml_path,
                    "blocker_step_index": blocker_index,
                    "workbook_sheet": p0_sheet,
                    "workbook_physical_row": p0_row,
                    "emitted_yaml_path": emitted_item["relative_path"],
                    "emitted_step_index":
                        candidate_indices[0]
                        if len(candidate_indices) == 1 else None,
                    "tracked_tc_name_match": tracked_name_match,
                    **bindings,
                    "tracked_step_projection": tracked_projection,
                    "emitted_step_projection":
                        step_projection(
                            emitted_steps[candidate_indices[0] - 1]
                        ) if len(candidate_indices) == 1 else None,
                    "candidate_count": len(candidate_indices),
                    "step_join_verdict":
                        "RECONCILED"
                        if len(candidate_indices) == 1 else "MISMATCH",
                    "verdict":
                        "RECONCILED"
                        if len(candidate_indices) == 1 and document_green
                        else "MISMATCH",
                }
            )
        tracked_projection = [
            step_projection(step) for step in tracked_steps
        ]
        emitted_projection = [
            step_projection(step) for step in emitted_steps
        ]
        projections.append(
            {
                "yaml_path": yaml_path,
                "gating": False,
                "tracked_ordered_projection": tracked_projection,
                "tracked_projection_sha256":
                    sha256_bytes(canonical_bytes(tracked_projection)),
                "emitted_ordered_projection": emitted_projection,
                "emitted_projection_sha256":
                    sha256_bytes(canonical_bytes(emitted_projection)),
            }
        )

    if len(mapped_source_keys) == 12 and len(set(mapped_source_keys)) != 12:
        add_reason(
            reasons, "P0_SOURCE_ROW_UNIQUENESS", "p0.mappings",
            "source rows repeat",
        )
    step_sheet_counts = {
        sheet: sum(
            len(indices)
            for _path, indices, target_sheet in TARGETS
            if target_sheet == sheet
        )
        for sheet in ("SS-TC 0", "SS-TC 1")
    }
    row_sheet_counts = {
        sheet: sum(
            1 for source_sheet, _row in set(mapped_source_keys)
            if source_sheet == sheet
        )
        for sheet in ("SS-TC 0", "SS-TC 1")
    }
    if step_sheet_counts != {"SS-TC 0": 1, "SS-TC 1": 14}:
        raise ValueError("embedded step sheet distribution failed")
    if (
        len(mapped_source_keys) == 12
        and row_sheet_counts != {"SS-TC 0": 1, "SS-TC 1": 11}
    ):
        add_reason(
            reasons, "P0_ROW_DISTRIBUTION", "p0.mappings",
            f"observed={row_sheet_counts!r}",
        )
    paired = {
        path for path, indices, _sheet in TARGETS if len(indices) == 2
    }
    if paired != {
        "exported_ss_call/SS_TC01_permission_denied.yaml",
        "exported_ss_call/SS_TC06_missed_rejected.yaml",
        "exported_ss_call/SS_TC11_multi_subscription.yaml",
    }:
        raise ValueError("embedded paired-path invariant failed")

    targets.sort(
        key=lambda item: (
            item["yaml_path"].encode("utf-8"),
            item["blocker_step_index"],
        )
    )
    projections.sort(key=lambda item: item["yaml_path"].encode("utf-8"))
    mapped_document_status.sort(
        key=lambda item: item["yaml_path"].encode("utf-8")
    )
    emitted_target_keys = [
        (item["emitted_yaml_path"], item["emitted_step_index"])
        for item in targets
        if item["emitted_step_index"] is not None
    ]
    if len(emitted_target_keys) != len(set(emitted_target_keys)):
        add_reason(
            reasons, "TARGET_STEP_REUSE", "targets",
            "emitted document/step pair reused",
        )
    reasons.sort(
        key=lambda item: (item["code"], item["path"], item["message"])
    )
    public_inventory = [
        {key: value for key, value in item.items() if key != "document"}
        for item in inventories
    ]
    reconciled = not reasons and len(targets) == 15
    output = {
        "schema_version": 1,
        "directive_id": DIRECTIVE_ID,
        "inventories": public_inventory,
        "producer_counts": producer_counts,
        "mapped_document_status": mapped_document_status,
        "targets": targets,
        "document_step_projection_report": projections,
        "blocking_reasons": reasons,
        "reconciled": reconciled,
        "verdict":
            "PROVENANCE_RECONCILED"
            if reconciled else "PROVENANCE_MISMATCH",
    }
    temporary.write_bytes(canonical_bytes(output))
    os.replace(temporary, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(3)
```

---

## Appendix C — Exact evidence/failure assembler source

아래 code fence 내부 source만 external temp `assemble_evidence.py`로 만든다.
source bytes는 UTF-8, LF, 마지막 line 뒤 trailing LF 1개다.

**Expected source SHA-256:** `258c1c96739d782ef56040fb95fa390384752a75f9623d4a79ab07c99c72013e`

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DIRECTIVE_ID = "RB-20260728-shellrc-p0p1"
REPO = Path(r"C:\Users\momen\Projects\tc-runner")
TEMP = Path(r"C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1")
EVIDENCE = (
    REPO / "reports" / "canonical_shell_rc_provenance"
    / DIRECTIVE_ID / "PROVENANCE_EVIDENCE.json"
)
DIRECTIVE = REPO / "HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md"
SPEC = (
    REPO / "docs" / "superpowers" / "specs"
    / "2026-07-27-shell-rc-remediation-design.md"
)
GENERATOR = REPO / "scripts" / "dispatch_capsule.py"
CAPSULE_ROOT = Path(r"C:\tmp\tc-runner-dispatch-capsules")
CAPSULE_TYPE = "tc-runner.dispatch-entry"
CAPSULE_SCHEMA_VERSION = 2
CAPSULE_TTL_SECONDS = 1800
MODULE_PACKAGE_NAME = "@oai/artifact-tool"
MODULE_VERSION_FLOOR = (2, 8, 6)
UPSTREAM_REF = "origin/master"
PHASE_ORDER = (
    "HOST_PREFLIGHT",
    "APPENDIX_MATERIALIZATION",
    "P0_ARTIFACT_CAPTURE",
    "DRY_SS_TC_0",
    "DRY_SS_TC_1",
    "EXPORT_SS_TC_0",
    "EXPORT_SS_TC_1",
    "ANALYZE",
)
TOOLCHAIN = {
    "console_input": "utf-8",
    "console_output": "utf-8",
    "node": "v24.14.1",
    "openpyxl": "3.1.5",
    "output_encoding": "utf-8",
    "powershell": "5.1.26100.8875",
    "psedition": "Desktop",
    "pyyaml": "6.0.3",
    "python": "3.12.2",
    "pythonhashseed": "0",
    "pythonioencoding": "utf-8",
}
EXPECTED_TARGETS = (
    ("exported_ss_call/SS_TC01_permission_denied.yaml", 10),
    ("exported_ss_call/SS_TC01_permission_denied.yaml", 11),
    ("exported_ss_call/SS_TC02_permission_allow_idle.yaml", 11),
    ("exported_ss_call/SS_TC03_ringing_permission.yaml", 15),
    ("exported_ss_call/SS_TC04_offhook_seed_recovery.yaml", 18),
    ("exported_ss_call/SS_TC05_boundary_values.yaml", 9),
    ("exported_ss_call/SS_TC06_missed_rejected.yaml", 10),
    ("exported_ss_call/SS_TC06_missed_rejected.yaml", 11),
    ("exported_ss_call/SS_TC07_short_call_no_false_positive.yaml", 9),
    ("exported_ss_call/SS_TC09_offhook_permission_banking.yaml", 20),
    ("exported_ss_call/SS_TC0_P0_endcall_crash.yaml", 15),
    ("exported_ss_call/SS_TC10_permission_toggle.yaml", 24),
    ("exported_ss_call/SS_TC11_multi_subscription.yaml", 20),
    ("exported_ss_call/SS_TC11_multi_subscription.yaml", 21),
    ("exported_ss_call/SS_TC12_legacy_path.yaml", 19),
)
EXPECTED_YAML_PATHS = tuple(sorted(
    {path for path, _index in EXPECTED_TARGETS},
    key=lambda value: value.encode("utf-8"),
))
SPEC_SHA = "492b718d4dfc3713f9c78c362c3db38af4e348336df81917aa7991ee145aaebf"
SPEC_BLOB = "4db31884e55f1c18dbfd53edd090da88d9f8b51e"
GENERATOR_SHA = "45a1a0ebc3fdc89691f6b3106fede0771ea376a8f132866899bca655289db6bd"
GENERATOR_BLOB = "db170b307a323e861b8a3fc7d29ef743b109197e"
WORKBOOK_SHA = "160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa"
WORKBOOK_BLOB = "24593d11dd80a2b3711655bd0c5216ee9157dedc"
ACTORS = {
    "src/cli.py": "c27fa7d5c6c4bd9f956238ef0008990e667989949bbc5743d6a37347ee71a5b0",
    "src/execution_contract.py": "b5a8601a8efd7008752f5c1b50134066082a64f8b976f1fb2270fcc76f1b21eb",
    "tc_step_schema.json": "7ec8a76766bec3e8ba18cdd8deedb478024edb2878ee83190907125669cc7059",
    "src/mmi_converter/__init__.py": "164bb0d498d3a7ec2172196882f2ed566fc0578c924d1445b0c4af390ca4f4a4",
    "src/mmi_converter/classifier.py": "f795a9e88f8f6b67a9b2358a5adf5edeccc4ba48bae2e5d1bd2153de0f0f1753",
    "src/mmi_converter/compiler.py": "52985f0b008d23a65ca7168777e23590ddd4b20eb22f37f1f8eede3d6c313eec",
    "src/mmi_converter/expected_parser.py": "17b42361351d54920c89851acac473293eff6ad2a75d3ba90854926d2e98375c",
    "src/mmi_converter/exporter.py": "3090015d4a045d61c0f382cc21dceffd3a13c7c8b1950119b9396e5bb18bbac6",
    "src/mmi_converter/models.py": "6240036685e4a64a51c16cc5a576b268c1eba3aeb55031b83ce097882a7a7227",
    "src/mmi_converter/procedure_parser.py": "62c66ef7e941a1a3eaeb3b7a7abe14c8f020923e33287a589f27eb1908d6618a",
    "src/mmi_converter/row_loader.py": "38cb421b9f7f6282df401c84dc7b06837ea61cd70b22d17547e9ed62498c39d7",
    "src/mmi_converter/service.py": "83015f8c79ade724ec7aa619a2fff82945192ecb41b479d344b2b9c404729f79",
    "src/mmi_converter/shell_action_map.py": "479b846a48bba0771d37af924ae8a38314c83033f05ef0993598f85bb7cb77be",
    "src/mmi_converter/step_classifier.py": "1c73bb15df6981ab9d6cc68615db0decfdaa70259c30fbdb2c5e26e89fd1f90f",
}
AUDIT = {
    "reports/_codex_shell_inventory_v3_277e_a/66951de779d78dc6/shell_rc_inventory.csv":
        "b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f",
    "reports/_codex_shell_rc_risk_3d99_a/c60be6036584ce8f/shell_rc_risk_matrix.csv":
        "81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4",
    "scripts/canonical_shell_rc_risk_policy_v1.json":
        "f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed",
    "scripts/canonical_shell_rc_risk_audit.py":
        "3d9903854a8c4d4cbb64edec4b412563a3ac4626f0ad25cf2934d06d44e61d34",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_linklike(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def sha256_file(path: Path) -> str:
    if not path.is_file() or is_linklike(path):
        raise ValueError(f"not an ordinary file: {path}")
    return sha256_bytes(path.read_bytes())


def object_without_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"capsule duplicate key: {key}")
        result[key] = value
    return result


def exact_object(
    value: object,
    keys: set[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} schema")
    return value


def is_non_bool_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_lower_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"[0-9a-f]{64}", value
    ) is not None


def is_lower_oid(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"[0-9a-f]{40}", value
    ) is not None


def validate_capsule_identity(
    value: object,
    *,
    label: str,
    expected_path: str,
    expected_sha: str,
    expected_blob: str,
) -> None:
    identity = exact_object(
        value,
        {"path", "raw_sha256", "git_blob_no_filters"},
        label=label,
    )
    if (
        identity["path"] != expected_path
        or identity["raw_sha256"] != expected_sha
        or identity["git_blob_no_filters"] != expected_blob
        or not is_lower_sha256(identity["raw_sha256"])
        or not is_lower_oid(identity["git_blob_no_filters"])
    ):
        raise ValueError(f"{label} binding")


def module_version_tuple(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    if not parts or any(
        not part.isdigit() or (len(part) > 1 and part[0] == "0")
        for part in parts
    ):
        raise ValueError("module version format")
    return tuple(int(part) for part in parts)


def validate_capsule_module_roots(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("capsule module_roots cardinality")
    modules = []
    for item in value:
        module = exact_object(
            item,
            {
                "entry_bytes",
                "entry_relpath",
                "entry_sha256",
                "package_name",
                "package_version",
                "root_path",
            },
            label="capsule.module_roots[]",
        )
        if (
            module["package_name"] != MODULE_PACKAGE_NAME
            or not is_non_bool_int(module["entry_bytes"])
            or module["entry_bytes"] <= 0
            or not isinstance(module["entry_relpath"], str)
            or not module["entry_relpath"]
            or "\\" in module["entry_relpath"]
            or module["entry_relpath"].startswith("/")
            or not is_lower_sha256(module["entry_sha256"])
            or not isinstance(module["package_version"], str)
            or not isinstance(module["root_path"], str)
            or not module["root_path"]
            or "\\" in module["root_path"]
        ):
            raise ValueError("capsule module_roots fields")
        if module_version_tuple(
            module["package_version"]
        ) < MODULE_VERSION_FLOOR:
            raise ValueError("capsule module version below floor")
        modules.append(module)
    return modules


def validate_dispatch_capsule_payload(
    value: object,
    *,
    capsule_sha256: str,
    directive_sha: str,
    directive_blob: str,
) -> dict[str, Any]:
    capsule = exact_object(
        value,
        {
            "capsule_type",
            "directive_id",
            "expires_at_epoch_s",
            "identities",
            "ignored",
            "index",
            "issued_at_epoch_s",
            "module_roots",
            "repo",
            "schema_version",
            "ttl_seconds",
            "untracked",
        },
        label="capsule",
    )
    if (
        not is_lower_sha256(capsule_sha256)
        or sha256_bytes(canonical_bytes(capsule)) != capsule_sha256
        or capsule["capsule_type"] != CAPSULE_TYPE
        or capsule["directive_id"] != DIRECTIVE_ID
        or not is_non_bool_int(capsule["schema_version"])
        or capsule["schema_version"] != CAPSULE_SCHEMA_VERSION
        or not is_non_bool_int(capsule["ttl_seconds"])
        or capsule["ttl_seconds"] != CAPSULE_TTL_SECONDS
        or not is_non_bool_int(capsule["issued_at_epoch_s"])
        or not is_non_bool_int(capsule["expires_at_epoch_s"])
        or capsule["issued_at_epoch_s"] < 0
        or capsule["expires_at_epoch_s"] < 0
        or capsule["expires_at_epoch_s"]
        - capsule["issued_at_epoch_s"]
        != CAPSULE_TTL_SECONDS
    ):
        raise ValueError("capsule fixed fields")
    repo = exact_object(
        capsule["repo"],
        {
            "root",
            "upstream_ref",
            "head_sha",
            "upstream_sha",
            "ahead",
            "behind",
            "tracked_clean",
            "staged_clean",
        },
        label="capsule.repo",
    )
    if (
        repo["root"] != REPO.resolve(strict=True).as_posix()
        or repo["upstream_ref"] != UPSTREAM_REF
        or not is_lower_oid(repo["head_sha"])
        or not is_lower_oid(repo["upstream_sha"])
        or repo["head_sha"] != repo["upstream_sha"]
        or not is_non_bool_int(repo["ahead"])
        or not is_non_bool_int(repo["behind"])
        or repo["ahead"] != 0
        or repo["behind"] != 0
        or repo["tracked_clean"] is not True
        or repo["staged_clean"] is not True
    ):
        raise ValueError("capsule repo binding")
    index = exact_object(
        capsule["index"],
        {"entry_count", "raw_stage_z_sha256"},
        label="capsule.index",
    )
    if (
        not is_non_bool_int(index["entry_count"])
        or index["entry_count"] < 0
        or not is_lower_sha256(index["raw_stage_z_sha256"])
    ):
        raise ValueError("capsule index fields")
    for name in ("untracked", "ignored"):
        mapping = exact_object(
            capsule[name],
            {"count", "canonical_json_sha256", "excluded_paths"},
            label=f"capsule.{name}",
        )
        if (
            not is_non_bool_int(mapping["count"])
            or mapping["count"] < 0
            or not is_lower_sha256(mapping["canonical_json_sha256"])
            or mapping["excluded_paths"] != []
        ):
            raise ValueError(f"capsule {name} fields")
    validate_capsule_module_roots(capsule["module_roots"])
    identities = exact_object(
        capsule["identities"],
        {"directive", "spec", "generator"},
        label="capsule.identities",
    )
    validate_capsule_identity(
        identities["directive"],
        label="capsule directive",
        expected_path=DIRECTIVE.relative_to(REPO).as_posix(),
        expected_sha=directive_sha,
        expected_blob=directive_blob,
    )
    validate_capsule_identity(
        identities["spec"],
        label="capsule spec",
        expected_path=SPEC.relative_to(REPO).as_posix(),
        expected_sha=SPEC_SHA,
        expected_blob=SPEC_BLOB,
    )
    validate_capsule_identity(
        identities["generator"],
        label="capsule generator",
        expected_path=GENERATOR.relative_to(REPO).as_posix(),
        expected_sha=GENERATOR_SHA,
        expected_blob=GENERATOR_BLOB,
    )
    return capsule


def dispatch_capsule_path(capsule_sha256: str) -> Path:
    if not is_lower_sha256(capsule_sha256):
        raise ValueError("capsule token is not lowercase SHA-256")
    root_lexical = Path(os.path.abspath(CAPSULE_ROOT))
    repo_resolved = REPO.resolve(strict=True)
    root_resolved = root_lexical.resolve(strict=True)
    try:
        root_resolved.relative_to(repo_resolved)
    except ValueError:
        pass
    else:
        raise ValueError("capsule root resolves inside repo")
    if (
        not root_resolved.is_dir()
        or is_linklike(root_lexical)
        or is_linklike(root_resolved)
    ):
        raise ValueError("capsule root is not ordinary directory")
    return root_resolved / f"{capsule_sha256}.json"


def read_external_dispatch_capsule(
    capsule_sha256: str,
    *,
    directive_sha: str,
    directive_blob: str,
) -> tuple[Path, dict[str, Any]]:
    path = dispatch_capsule_path(capsule_sha256)
    if not path.is_file() or is_linklike(path):
        raise FileNotFoundError("dispatch capsule missing or link/junction")
    raw = path.read_bytes()
    if sha256_bytes(raw) != capsule_sha256:
        raise ValueError("dispatch capsule raw SHA")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=object_without_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("dispatch capsule JSON") from error
    if canonical_bytes(value) != raw:
        raise ValueError("dispatch capsule is not canonical JSON")
    capsule = validate_dispatch_capsule_payload(
        value,
        capsule_sha256=capsule_sha256,
        directive_sha=directive_sha,
        directive_blob=directive_blob,
    )
    return path, capsule


def require_ordinary_repo_child(path: Path) -> None:
    repo_lexical = Path(os.path.abspath(REPO))
    candidate_lexical = Path(os.path.abspath(path))
    try:
        candidate_lexical.relative_to(repo_lexical)
    except ValueError as error:
        raise ValueError(f"protected path escapes repo: {path}") from error
    if not candidate_lexical.is_file() or is_linklike(candidate_lexical):
        raise ValueError(f"protected path is not ordinary file: {path}")
    resolved = candidate_lexical.resolve(strict=True)
    if os.path.normcase(str(resolved)) != os.path.normcase(
        str(candidate_lexical)
    ):
        raise ValueError(f"protected path resolves elsewhere: {path}")


def derive_appendix_hashes() -> dict[str, str]:
    require_ordinary_repo_child(DIRECTIVE)
    text = DIRECTIVE.read_text(encoding="utf-8").replace("\r\n", "\n")
    if "\r" in text:
        raise ValueError("directive contains unsupported lone CR")
    result = {}
    for label, language in (
        ("A", "javascript"), ("B", "python"), ("C", "python"),
        ("R", "javascript"),
    ):
        headings = list(re.finditer(
            rf"^## Appendix {label} —[^\n]*$",
            text,
            flags=re.MULTILINE,
        ))
        if len(headings) != 1:
            raise ValueError(f"Appendix {label} heading cardinality")
        start = headings[0].end()
        next_heading = re.search(
            r"^## Appendix [A-CR] —[^\n]*$",
            text[start:],
            flags=re.MULTILINE,
        )
        end = (
            start + next_heading.start()
            if next_heading is not None else len(text)
        )
        section = text[start:end]
        fences = list(re.finditer(
            rf"^```{language}\n(?P<body>.*?)^```[ \t]*$",
            section,
            flags=re.MULTILINE | re.DOTALL,
        ))
        if len(fences) != 1:
            raise ValueError(f"Appendix {label} fence cardinality")
        body = fences[0].group("body").rstrip("\n") + "\n"
        result[f"appendix_{label.lower()}_source_sha256"] = (
            sha256_bytes(body.encode("utf-8"))
        )
    return result


def valid_reason_list(value: object, *, allow_empty: bool) -> bool:
    if not isinstance(value, list) or (not allow_empty and not value):
        return False
    if any(
        not isinstance(item, dict)
        or set(item) != {"code", "path", "message"}
        or any(
            not isinstance(item[field], str) or not item[field]
            for field in ("code", "path", "message")
        )
        for item in value
    ):
        return False
    expected = sorted(
        value,
        key=lambda item: (
            item["code"], item["path"], item["message"],
        ),
    )
    return value == expected


def validate_reconciliation(value: object) -> list[str]:
    problems = []
    if not isinstance(value, dict):
        return ["reconciliation top level"]
    if value.get("schema_version") != 1:
        problems.append("reconciliation schema_version")
    if value.get("directive_id") != DIRECTIVE_ID:
        problems.append("reconciliation directive_id")
    reconciled = value.get("reconciled")
    reasons = value.get("blocking_reasons")
    if not isinstance(reconciled, bool):
        problems.append("reconciliation reconciled flag")
    if not valid_reason_list(
        reasons, allow_empty=(reconciled is True),
    ):
        problems.append("reconciliation blocking reasons")
    if (
        reconciled is True
        and (
            reasons != []
            or value.get("verdict") != "PROVENANCE_RECONCILED"
        )
    ):
        problems.append("reconciliation green verdict")
    if (
        reconciled is False
        and value.get("verdict") != "PROVENANCE_MISMATCH"
    ):
        problems.append("reconciliation mismatch verdict")

    targets = value.get("targets")
    if not isinstance(targets, list):
        problems.append("reconciliation targets")
        targets = []
    observed_target_keys = [
        (item.get("yaml_path"), item.get("blocker_step_index"))
        for item in targets if isinstance(item, dict)
    ]
    valid_target_keys = (
        len(observed_target_keys) == len(targets)
        and all(
            isinstance(path, str)
            and isinstance(index, int)
            and not isinstance(index, bool)
            for path, index in observed_target_keys
        )
    )
    if (
        not valid_target_keys
        or len(set(observed_target_keys)) != len(observed_target_keys)
        or not set(observed_target_keys).issubset(set(EXPECTED_TARGETS))
    ):
        problems.append("reconciliation target cardinality")
    if reconciled is True:
        if (
            len(targets) != 15
            or observed_target_keys != list(EXPECTED_TARGETS)
            or any(
                not isinstance(item, dict)
                or item.get("tracked_tc_name_match") is not True
                or item.get("emitted_name_match") is not True
                or item.get("procedure_prefix_match") is not True
                or item.get("source_content_hash_match") is not True
                or item.get("candidate_count") != 1
                or item.get("step_join_verdict") != "RECONCILED"
                or item.get("verdict") != "RECONCILED"
                or isinstance(item.get("emitted_step_index"), bool)
                or not isinstance(item.get("emitted_step_index"), int)
                or item["emitted_step_index"] <= 0
                for item in targets
            )
        ):
            problems.append("reconciliation green targets")

    documents = value.get("mapped_document_status")
    if not isinstance(documents, list):
        problems.append("reconciliation mapped documents")
        documents = []
    document_paths = [
        item.get("yaml_path")
        for item in documents if isinstance(item, dict)
    ]
    valid_document_paths = (
        len(document_paths) == len(documents)
        and all(isinstance(item, str) for item in document_paths)
    )
    if (
        not valid_document_paths
        or len(set(document_paths)) != len(document_paths)
        or not set(document_paths).issubset(set(EXPECTED_YAML_PATHS))
    ):
        problems.append("reconciliation document cardinality")
    if reconciled is True:
        if (
            len(documents) != 12
            or document_paths != list(EXPECTED_YAML_PATHS)
            or any(
                not isinstance(item, dict)
                or item.get("tracked_tc_name_match") is not True
                or item.get("emitted_name_match") is not True
                or item.get("procedure_prefix_match") is not True
                or item.get("source_content_hash_match") is not True
                or item.get("runnable") is not True
                or item.get("has_unresolved_params") is not False
                or item.get("verdict") != "RECONCILED"
                for item in documents
            )
        ):
            problems.append("reconciliation green documents")

    counts = value.get("producer_counts")
    if (
        not isinstance(counts, list)
        or len(counts) != 2
        or [item.get("sheet_label") for item in counts
            if isinstance(item, dict)] != ["SS-TC-0", "SS-TC-1"]
        or any(
            not isinstance(item, dict)
            or isinstance(item.get("dry_total"), bool)
            or not isinstance(item.get("dry_total"), int)
            or item["dry_total"] <= 0
            or isinstance(item.get("created"), bool)
            or not isinstance(item.get("created"), int)
            or item["created"] < 0
            or isinstance(item.get("inventory_count"), bool)
            or not isinstance(item.get("inventory_count"), int)
            or item["inventory_count"] < 0
            or isinstance(item.get("skipped"), bool)
            or not isinstance(item.get("skipped"), int)
            or item["skipped"] < 0
            for item in counts
        )
    ):
        problems.append("reconciliation producer counts")
    elif reconciled is True and any(
        item["created"] != item["dry_total"]
        or item["inventory_count"] != item["dry_total"]
        or item["skipped"] != 0
        for item in counts
    ):
        problems.append("reconciliation green producer counts")

    inventories = value.get("inventories")
    expected_inventory_count = (
        sum(item["inventory_count"] for item in counts)
        if isinstance(counts, list)
        and len(counts) == 2
        and all(
            isinstance(item, dict)
            and isinstance(item.get("inventory_count"), int)
            and not isinstance(item.get("inventory_count"), bool)
            for item in counts
        )
        else None
    )
    if (
        not isinstance(inventories, list)
        or expected_inventory_count is None
        or len(inventories) != expected_inventory_count
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("relative_path"), str)
            or re.fullmatch(
                r"SS-TC-[01]/[^/]+\.yaml", item["relative_path"]
            ) is None
            or not isinstance(item.get("raw_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["raw_sha256"]) is None
            or not isinstance(item.get("semantic_sha256"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}", item["semantic_sha256"]
            ) is None
            for item in inventories
        )
    ):
        problems.append("reconciliation inventory")

    projections = value.get("document_step_projection_report")
    projection_paths = [
        item.get("yaml_path")
        for item in projections if isinstance(item, dict)
    ] if isinstance(projections, list) else []
    valid_projection_paths = (
        isinstance(projections, list)
        and len(projection_paths) == len(projections)
        and all(isinstance(item, str) for item in projection_paths)
    )
    if (
        not isinstance(projections, list)
        or not valid_projection_paths
        or len(set(projection_paths)) != len(projection_paths)
        or not set(projection_paths).issubset(set(EXPECTED_YAML_PATHS))
        or any(
            not isinstance(item, dict)
            or item.get("gating") is not False
            for item in projections
        )
    ):
        problems.append("reconciliation projection report")
    elif reconciled is True and (
        len(projections) != 12
        or projection_paths != list(EXPECTED_YAML_PATHS)
    ):
        problems.append("reconciliation green projection report")
    return problems


def blob_id(value: bytes) -> str:
    header = f"blob {len(value)}\0".encode("ascii")
    return hashlib.sha1(header + value).hexdigest()


def git(*args: str, input_bytes: bytes | None = None) -> bytes:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_SYSTEM"] = os.devnull
    result = subprocess.run(
        ["git", "-c", f"core.excludesFile={os.devnull}", *args],
        cwd=REPO,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)}: {result.returncode}: {message}")
    if result.stderr:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)} emitted stderr: {message}")
    return result.stdout


def git_quiet(*args: str) -> bool:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_SYSTEM"] = os.devnull
    result = subprocess.run(
        ["git", "-c", f"core.excludesFile={os.devnull}", *args],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git {' '.join(args)}: {result.returncode}")
    if result.stderr:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)} emitted stderr: {message}")
    return result.returncode == 0


def path_identity(
    git_args: tuple[str, ...],
) -> dict[str, Any]:
    raw = git(*git_args)
    paths = [
        item.decode("utf-8").replace("\\", "/")
        for item in raw.split(b"\0") if item
    ]
    if any("\n" in item or "\r" in item for item in paths):
        raise ValueError("newline-containing untracked path is unsupported")
    for relative in paths:
        candidate = REPO / Path(relative)
        if (
            not candidate.is_file()
            or is_linklike(candidate)
            or candidate.is_dir()
        ):
            raise ValueError(f"untracked path is not ordinary file: {relative}")
    hashes_raw = git(
        "hash-object", "--no-filters", "--stdin-paths",
        input_bytes="".join(f"{item}\n" for item in paths).encode("utf-8"),
    )
    hashes = hashes_raw.decode("ascii").splitlines()
    if len(hashes) != len(paths):
        raise ValueError("untracked path/hash cardinality mismatch")
    rows = [
        {
            "file_type": "file",
            "git_hash_object_no_filters": digest,
            "path": relative,
        }
        for relative, digest in zip(paths, hashes, strict=True)
    ]
    rows.sort(key=lambda item: item["path"].encode("utf-8"))
    return {
        "count": len(rows),
        "canonical_json_sha256": sha256_bytes(canonical_bytes(rows)),
    }


def untracked_identity() -> dict[str, Any]:
    return path_identity(
        (
            "-c", "core.quotepath=false", "ls-files",
            "--others", "--exclude-standard", "-z",
        ),
    )


def ignored_identity() -> dict[str, Any]:
    return path_identity(
        (
            "-c", "core.quotepath=false", "ls-files",
            "--others", "--ignored", "--exclude-standard", "-z",
        ),
    )


def current_file_identity(path: Path) -> dict[str, str]:
    require_ordinary_repo_child(path)
    relative = path.relative_to(REPO).as_posix()
    raw = path.read_bytes()
    actual_blob = git(
        "hash-object", "--no-filters", "--", relative
    ).decode("ascii", "strict").strip()
    if not is_lower_oid(actual_blob):
        raise ValueError(f"invalid Git blob identity: {relative}")
    return {
        "path": relative,
        "raw_sha256": sha256_bytes(raw),
        "git_blob_no_filters": actual_blob,
    }


def snapshot(
    capsule: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    require_ordinary_repo_child(DIRECTIVE)
    require_ordinary_repo_child(SPEC)
    require_ordinary_repo_child(GENERATOR)
    index_raw = git("-c", "core.quotepath=false", "ls-files", "--stage", "-z")
    tracked_raw = git("-c", "core.quotepath=false", "ls-files", "-z")
    tracked_paths = [
        item.decode("utf-8")
        for item in tracked_raw.split(b"\0")
        if item
    ]
    workbook_basename_candidates = sorted(
        (
            item for item in tracked_paths
            if Path(item).name == "TC_1.xlsx"
        ),
        key=lambda item: item.encode("utf-8"),
    )
    ahead_behind = git(
        "rev-list", "--left-right", "--count", "origin/master...HEAD"
    ).decode("ascii").strip().split()
    workbook = REPO / "tc_samples" / "TC_1.xlsx"
    actual_actors = {path: sha256_file(REPO / path) for path in ACTORS}
    actual_audit = {path: sha256_file(REPO / path) for path in AUDIT}
    dispatch_state = {
        "repo": {
            "root": REPO.resolve(strict=True).as_posix(),
            "upstream_ref": UPSTREAM_REF,
            "head_sha":
                git("rev-parse", "HEAD").decode("ascii", "strict").strip(),
            "upstream_sha":
                git("rev-parse", UPSTREAM_REF)
                .decode("ascii", "strict").strip(),
            "ahead": int(ahead_behind[1]),
            "behind": int(ahead_behind[0]),
            "tracked_clean": git_quiet("diff", "--quiet"),
            "staged_clean": git_quiet("diff", "--cached", "--quiet"),
        },
        "index": {
            "entry_count":
                len([item for item in index_raw.split(b"\0") if item]),
            "raw_stage_z_sha256": sha256_bytes(index_raw),
        },
        "untracked": {
            **untracked_identity(),
            "excluded_paths": [],
        },
        "ignored": {
            **ignored_identity(),
            "excluded_paths": [],
        },
        "identities": {
            "directive": current_file_identity(DIRECTIVE),
            "spec": current_file_identity(SPEC),
            "generator": current_file_identity(GENERATOR),
        },
    }
    state = {
        **dispatch_state,
        "workbook": {
            "raw_sha256": sha256_file(workbook),
            "blob": blob_id(workbook.read_bytes()),
            "mtime_ns": workbook.stat().st_mtime_ns,
            "tracked_basename_candidates": workbook_basename_candidates,
        },
        "producer_actors": actual_actors,
        "frozen_audit": actual_audit,
    }
    problems = []
    capsule_state = (
        {
            key: capsule[key]
            for key in ("repo", "index", "untracked", "ignored", "identities")
        }
        if capsule is not None else None
    )
    exact_checks = (
        (
            capsule_state is not None
            and canonical_bytes(dispatch_state) == canonical_bytes(capsule_state),
            "live repository state differs from dispatch capsule",
        ),
        (state["workbook"]["raw_sha256"] == WORKBOOK_SHA, "workbook SHA"),
        (state["workbook"]["blob"] == WORKBOOK_BLOB, "workbook blob"),
        (
            state["workbook"]["tracked_basename_candidates"]
            == ["tc_samples/TC_1.xlsx"],
            "workbook tracked basename candidates",
        ),
        (actual_actors == ACTORS, "producer actor hashes"),
        (actual_audit == AUDIT, "frozen audit hashes"),
    )
    problems.extend(label for ok, label in exact_checks if not ok)
    return state, problems


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if not path.is_file() or is_linklike(path):
        raise ValueError(f"JSON input is not ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON top level must be object")
    return value


def external_inventory(
    status: str,
    last_phase: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    materialization_files = {
        "analyze_provenance.py",
        "assemble_evidence.py",
        "operation_log.ndjson",
    }
    p0_files = {
        "artifact-tool-work/p0_workbook.json",
        "artifact-tool-work/render-SS-TC-0.png",
        "artifact-tool-work/render-SS-TC-1.png",
    }
    p0_temporary_files = {
        "artifact-tool-work/p0_workbook.json.tmp",
        "artifact-tool-work/render-SS-TC-0.png.tmp",
        "artifact-tool-work/render-SS-TC-1.png.tmp",
    }
    dry0_files = {"dry-run-SS-TC-0.combined.txt"}
    dry1_files = {"dry-run-SS-TC-1.combined.txt"}
    export0_files = {"export-SS-TC-0.combined.txt"}
    export1_files = {"export-SS-TC-1.combined.txt"}
    analyze_files = {
        "reconciliation.json",
        "reconciliation.json.tmp",
        "analyze.combined.txt",
    }
    fixed = (
        materialization_files
        | p0_files
        | p0_temporary_files
        | dry0_files
        | dry1_files
        | export0_files
        | export1_files
        | analyze_files
    )
    terminal_index = PHASE_ORDER.index(last_phase)
    completed_index = (
        terminal_index if status == "measured" else terminal_index - 1
    )
    allowed_files: set[str] = set()
    allowed_dirs: set[str] = set()
    if terminal_index >= PHASE_ORDER.index("APPENDIX_MATERIALIZATION"):
        allowed_files |= materialization_files
    if terminal_index >= PHASE_ORDER.index("P0_ARTIFACT_CAPTURE"):
        allowed_files |= p0_files
        allowed_dirs.add("artifact-tool-work")
    if (
        status == "infra_failure"
        and last_phase == "P0_ARTIFACT_CAPTURE"
    ):
        allowed_files |= p0_temporary_files
    if terminal_index >= PHASE_ORDER.index("DRY_SS_TC_0"):
        allowed_files |= dry0_files
    if terminal_index >= PHASE_ORDER.index("DRY_SS_TC_1"):
        allowed_files |= dry1_files
    if terminal_index >= PHASE_ORDER.index("EXPORT_SS_TC_0"):
        allowed_files |= export0_files
        allowed_dirs.add("SS-TC-0")
    if terminal_index >= PHASE_ORDER.index("EXPORT_SS_TC_1"):
        allowed_files |= export1_files
        allowed_dirs.add("SS-TC-1")
    if terminal_index >= PHASE_ORDER.index("ANALYZE"):
        allowed_files |= analyze_files
    if not (
        status == "infra_failure" and last_phase == "ANALYZE"
    ):
        allowed_files.discard("reconciliation.json.tmp")

    required_files: set[str] = set()
    required_dirs: set[str] = set()
    if completed_index >= PHASE_ORDER.index("APPENDIX_MATERIALIZATION"):
        required_files |= materialization_files
    if completed_index >= PHASE_ORDER.index("P0_ARTIFACT_CAPTURE"):
        required_files |= p0_files
        required_dirs.add("artifact-tool-work")
    if completed_index >= PHASE_ORDER.index("DRY_SS_TC_0"):
        required_files |= dry0_files
    if completed_index >= PHASE_ORDER.index("DRY_SS_TC_1"):
        required_files |= dry1_files
    if completed_index >= PHASE_ORDER.index("EXPORT_SS_TC_0"):
        required_files |= export0_files
        required_dirs.add("SS-TC-0")
    if completed_index >= PHASE_ORDER.index("EXPORT_SS_TC_1"):
        required_files |= export1_files
        required_dirs.add("SS-TC-1")
    if completed_index >= PHASE_ORDER.index("ANALYZE"):
        required_files |= {
            "reconciliation.json",
            "analyze.combined.txt",
        }
    rows = []
    problems = []
    if not TEMP.is_dir() or is_linklike(TEMP):
        return rows, ["temp root missing or link/junction"]
    for item in TEMP.rglob("*"):
        relative = item.relative_to(TEMP).as_posix()
        if is_linklike(item):
            problems.append(f"link/junction:{relative}")
            continue
        if item.is_dir():
            if relative not in allowed_dirs:
                problems.append(f"directory:{relative}")
            rows.append({"path": relative, "type": "directory"})
            continue
        allowed_yaml = (
            (
                relative.startswith("SS-TC-0/")
                and terminal_index >= PHASE_ORDER.index("EXPORT_SS_TC_0")
            )
            or (
                relative.startswith("SS-TC-1/")
                and terminal_index >= PHASE_ORDER.index("EXPORT_SS_TC_1")
            )
        ) and relative.count("/") == 1 and relative.endswith(".yaml")
        if (
            relative not in fixed
            or relative not in allowed_files
        ) and not allowed_yaml:
            problems.append(f"file:{relative}")
        rows.append(
            {
                "path": relative,
                "type": "file",
                "raw_sha256": sha256_file(item),
                "size": item.stat().st_size,
            }
        )
    observed_files = {
        item["path"] for item in rows if item.get("type") == "file"
    }
    observed_dirs = {
        item["path"] for item in rows if item.get("type") == "directory"
    }
    for relative in sorted(
        required_files - observed_files, key=lambda item: item.encode("utf-8")
    ):
        problems.append(f"required file missing:{relative}")
    for relative in sorted(
        (
            item["path"] for item in rows
            if item.get("type") == "file"
            and item["path"] in required_files
            and item.get("size") == 0
        ),
        key=lambda item: item.encode("utf-8"),
    ):
        problems.append(f"required file empty:{relative}")
    for relative in sorted(required_dirs - observed_dirs):
        problems.append(f"required directory missing:{relative}")
    rows.sort(key=lambda item: item["path"].encode("utf-8"))
    problems.sort()
    return rows, problems


def log_inventory() -> list[dict[str, Any]]:
    result = []
    for name in (
        "dry-run-SS-TC-0.combined.txt",
        "dry-run-SS-TC-1.combined.txt",
        "export-SS-TC-0.combined.txt",
        "export-SS-TC-1.combined.txt",
        "analyze.combined.txt",
    ):
        path = TEMP / name
        result.append(
            {
                "path": name,
                "present": path.is_file(),
                "raw_sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return result


def load_phase_ledger(
    requested_status: str,
    last_phase: str,
    error_class: str,
    error_message: str,
) -> list[dict[str, Any]]:
    path = TEMP / "operation_log.ndjson"
    if not path.is_file() or is_linklike(path):
        raise ValueError("operation_log.ndjson missing or link/junction")
    rows = []
    required_fields = (
        "phase", "status", "tool", "cwd", "argv",
        "tool_input_sha256", "exit", "observed",
        "error_class", "error_message",
    )
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            raise ValueError(f"operation log blank line: {line_number}")
        value = json.loads(line)
        if (
            not isinstance(value, dict)
            or tuple(value) != required_fields
        ):
            raise ValueError(f"operation log schema: line {line_number}")
        if (
            not isinstance(value["phase"], str)
            or value["status"] not in {"COMPLETED", "FAILED"}
            or not isinstance(value["tool"], str)
            or not value["tool"]
            or not isinstance(value["cwd"], str)
            or not value["cwd"]
            or (
                value["argv"] is not None
                and (
                    not isinstance(value["argv"], list)
                    or not all(isinstance(item, str) for item in value["argv"])
                )
            )
            or (
                value["tool_input_sha256"] is not None
                and (
                    not isinstance(value["tool_input_sha256"], str)
                    or re.fullmatch(
                        r"[0-9a-f]{64}", value["tool_input_sha256"]
                    ) is None
                )
            )
            or not isinstance(value["observed"], dict)
            or not isinstance(value["error_class"], str)
            or not isinstance(value["error_message"], str)
        ):
            raise ValueError(f"operation log field type: line {line_number}")
        rows.append(value)
    if not rows:
        raise ValueError("operation log is empty")
    expected_phases = list(PHASE_ORDER)
    observed_phases = [row["phase"] for row in rows]
    if requested_status == "measured":
        measured_phases = (
            expected_phases
            if last_phase == "ANALYZE"
            else expected_phases[
                :expected_phases.index("P0_ARTIFACT_CAPTURE") + 1
            ]
        )
        if observed_phases != measured_phases:
            raise ValueError("measured operation phase sequence mismatch")
        if any(row["status"] != "COMPLETED" for row in rows):
            raise ValueError("measured operation status mismatch")
    else:
        expected_prefix = expected_phases[:expected_phases.index(last_phase) + 1]
        if observed_phases != expected_prefix:
            raise ValueError("failure operation phase prefix mismatch")
        if any(row["status"] != "COMPLETED" for row in rows[:-1]):
            raise ValueError("failure prefix contains non-completed phase")
        if not rows or rows[-1]["status"] != "FAILED":
            raise ValueError("failure ledger must end FAILED")
    for row in rows:
        is_process_phase = row["phase"] not in {
            "HOST_PREFLIGHT",
            "APPENDIX_MATERIALIZATION",
            "P0_ARTIFACT_CAPTURE",
        }
        if row["status"] == "COMPLETED":
            if row["error_class"] or row["error_message"]:
                raise ValueError(f"{row['phase']}: completed row has error")
            if row["phase"] in {
                "HOST_PREFLIGHT",
                "APPENDIX_MATERIALIZATION",
                "P0_ARTIFACT_CAPTURE",
            }:
                if row["exit"] is not None:
                    raise ValueError(
                        f"{row['phase']}: control/MCP exit must be null"
                    )
            elif (
                isinstance(row["exit"], bool)
                or not isinstance(row["exit"], int)
                or row["exit"] != 0
            ):
                raise ValueError(f"{row['phase']}: completed exit is not 0")
            if (
                is_process_phase
                and row["observed"].get(
                    "producer_input_identity_valid"
                ) is not True
            ):
                raise ValueError(
                    f"{row['phase']}: completed pre-invocation gate missing"
                )
            if (
                is_process_phase
                and row["observed"].get(
                    "process_launch_succeeded"
                ) is not True
            ):
                raise ValueError(
                    f"{row['phase']}: completed launch evidence missing"
                )
        else:
            if not row["error_class"] or not row["error_message"]:
                raise ValueError(f"{row['phase']}: failed row lacks error")
            if row["phase"] in {
                "HOST_PREFLIGHT",
                "APPENDIX_MATERIALIZATION",
                "P0_ARTIFACT_CAPTURE",
            }:
                if row["exit"] is not None:
                    raise ValueError(
                        f"{row['phase']}: failed non-process exit must be null"
                    )
            elif (
                row["exit"] is not None
                and (
                    isinstance(row["exit"], bool)
                    or not isinstance(row["exit"], int)
                )
            ):
                raise ValueError(f"{row['phase']}: failed process exit invalid")
            if (
                is_process_phase
                and row["exit"] is None
                and row["observed"] not in (
                    {
                        "producer_input_identity_valid": False,
                    },
                    {
                        "producer_input_identity_valid": True,
                        "process_launch_succeeded": False,
                    },
                    {
                        "producer_input_identity_valid": None,
                        "producer_input_check_completed": False,
                    },
                )
            ):
                raise ValueError(
                    f"{row['phase']}: pre-invocation failure evidence invalid"
                )
            if (
                is_process_phase
                and row["exit"] is not None
                and row["observed"].get(
                    "producer_input_identity_valid"
                ) is not True
            ):
                raise ValueError(
                    f"{row['phase']}: process-start gate evidence missing"
                )
            if (
                is_process_phase
                and row["exit"] is not None
                and row["observed"].get(
                    "process_launch_succeeded"
                ) is not True
            ):
                raise ValueError(
                    f"{row['phase']}: failed launch evidence invalid"
                )
    if rows[0].get("observed", {}).get("toolchain") != TOOLCHAIN:
        raise ValueError("HOST_PREFLIGHT observed toolchain mismatch")
    if requested_status == "infra_failure":
        if (
            rows[-1]["phase"] != last_phase
            or rows[-1]["error_class"] != error_class
            or rows[-1]["error_message"] != error_message
        ):
            raise ValueError("first-failure arguments differ from ledger")
    return rows


def validate_host_preflight_capsule(
    row: dict[str, Any],
    *,
    capsule_sha256: str,
    directive_sha: str,
    directive_blob: str,
) -> dict[str, Any]:
    if (
        row["phase"] != "HOST_PREFLIGHT"
        or row["status"] != "COMPLETED"
    ):
        raise ValueError("HOST_PREFLIGHT capsule evidence unavailable")
    observed = exact_object(
        row["observed"],
        {
            "dispatch_capsule",
            "dispatch_capsule_path",
            "dispatch_capsule_sha256",
            "capsule_verify",
            "ttl_valid_before_first_write",
            "module_route",
            "toolchain",
        },
        label="HOST_PREFLIGHT observed",
    )
    capsule = validate_dispatch_capsule_payload(
        observed["dispatch_capsule"],
        capsule_sha256=capsule_sha256,
        directive_sha=directive_sha,
        directive_blob=directive_blob,
    )
    capsule_module = capsule["module_roots"][0]
    module_route = exact_object(
        observed["module_route"],
        {
            "probe_source_sha256",
            "package_name",
            "package_version",
            "root_path",
            "entry_bytes",
            "entry_sha256",
        },
        label="HOST_PREFLIGHT module_route",
    )
    if (
        module_route["probe_source_sha256"]
        != derive_appendix_hashes()["appendix_r_source_sha256"]
        or module_route["package_name"] != capsule_module["package_name"]
        or module_route["package_version"]
        != capsule_module["package_version"]
        or module_route["root_path"] != capsule_module["root_path"]
        or module_route["entry_bytes"] != capsule_module["entry_bytes"]
        or module_route["entry_sha256"] != capsule_module["entry_sha256"]
    ):
        raise ValueError("HOST_PREFLIGHT module_route binding")
    verify = exact_object(
        observed["capsule_verify"],
        {"tool", "argv", "exit"},
        label="HOST_PREFLIGHT capsule_verify",
    )
    expected_verify_argv = [
        "-B", "scripts/dispatch_capsule.py", "verify",
        "--repo", str(REPO),
        "--capsule-sha256", capsule_sha256,
        "--expected-directive-id", DIRECTIVE_ID,
        "--expected-directive", DIRECTIVE.relative_to(REPO).as_posix(),
        "--expected-spec", SPEC.relative_to(REPO).as_posix(),
    ]
    capsule_path = dispatch_capsule_path(capsule_sha256)
    if (
        observed["dispatch_capsule_sha256"] != capsule_sha256
        or observed["dispatch_capsule_path"] != capsule_path.as_posix()
        or observed["ttl_valid_before_first_write"] is not True
        or observed["toolchain"] != TOOLCHAIN
        or verify["tool"] != str(
            (REPO / "venv" / "Scripts" / "python.exe").resolve(strict=True)
        )
        or verify["argv"] != expected_verify_argv
        or not is_non_bool_int(verify["exit"])
        or verify["exit"] != 0
    ):
        raise ValueError("HOST_PREFLIGHT capsule evidence mismatch")
    return capsule


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directive-sha", required=True)
    parser.add_argument("--directive-blob", required=True)
    parser.add_argument("--capsule-sha256", required=True)
    parser.add_argument("--appendix-a-sha", required=True)
    parser.add_argument("--appendix-b-sha", required=True)
    parser.add_argument("--appendix-c-sha", required=True)
    parser.add_argument(
        "--status", choices=("measured", "infra_failure"), required=True
    )
    parser.add_argument("--last-phase", choices=PHASE_ORDER, required=True)
    parser.add_argument("--error-class", default="")
    parser.add_argument("--error-message", default="")
    args = parser.parse_args()
    expected_application_args = [
        "--directive-sha", args.directive_sha,
        "--directive-blob", args.directive_blob,
        "--capsule-sha256", args.capsule_sha256,
        "--appendix-a-sha", args.appendix_a_sha,
        "--appendix-b-sha", args.appendix_b_sha,
        "--appendix-c-sha", args.appendix_c_sha,
        "--status", args.status,
        "--last-phase", args.last_phase,
    ]
    if args.status == "infra_failure":
        expected_application_args.extend([
            "--error-class", args.error_class,
            "--error-message", args.error_message,
        ])
    if sys.argv[1:] != expected_application_args:
        raise ValueError("assembler argv order/value mismatch")
    if (
        args.status == "measured"
        and (
            args.last_phase not in {"P0_ARTIFACT_CAPTURE", "ANALYZE"}
            or args.error_class
            or args.error_message
        )
    ):
        raise ValueError(
            "measured status requires P0/ANALYZE and empty error fields"
        )
    if (
        args.status == "infra_failure"
        and (not args.error_class or not args.error_message)
    ):
        raise ValueError("infra_failure requires nonempty error fields")

    if EVIDENCE.exists() or EVIDENCE.with_suffix(".json.tmp").exists():
        raise FileExistsError("evidence output already exists")
    path_chain = (
        REPO,
        REPO / "reports",
        REPO / "reports" / "canonical_shell_rc_provenance",
        EVIDENCE.parent,
    )
    if any(is_linklike(path) for path in path_chain if path.exists()):
        raise ValueError("evidence path chain contains link/junction")
    if (
        not EVIDENCE.parent.is_dir()
        or is_linklike(EVIDENCE.parent)
        or os.path.normcase(str(EVIDENCE.parent.resolve(strict=True)))
        != os.path.normcase(str(EVIDENCE.parent.absolute()))
    ):
        raise FileNotFoundError("evidence parent missing")
    if any(EVIDENCE.parent.iterdir()):
        raise ValueError("evidence parent is not empty")
    if not git_quiet("check-ignore", "-q", "--", str(EVIDENCE)):
        raise ValueError("evidence path is not ignored")

    appendix_derived = derive_appendix_hashes()
    appendix_expected = {
        key: appendix_derived[key]
        for key in (
            "appendix_a_source_sha256",
            "appendix_b_source_sha256",
            "appendix_c_source_sha256",
        )
    }
    appendix_actual = {
        "appendix_a_source_sha256":
            appendix_derived["appendix_a_source_sha256"],
        "appendix_b_source_sha256":
            sha256_file(TEMP / "analyze_provenance.py"),
        "appendix_c_source_sha256":
            sha256_file(TEMP / "assemble_evidence.py"),
    }
    appendix_arguments = {
        "appendix_a_source_sha256": args.appendix_a_sha,
        "appendix_b_source_sha256": args.appendix_b_sha,
        "appendix_c_source_sha256": args.appendix_c_sha,
    }
    invariant_problems: list[str] = []
    if (
        appendix_arguments != appendix_expected
        or appendix_actual != appendix_expected
    ):
        invariant_problems.append("appendix source hashes")
    external_rows, external_problems = external_inventory(
        args.status, args.last_phase
    )
    invariant_problems.extend(
        f"external write {item}" for item in external_problems
    )

    workbook = str(REPO / "tc_samples" / "TC_1.xlsx")
    python = str(REPO / "venv" / "Scripts" / "python.exe")
    phase_contracts = {
        "HOST_PREFLIGHT": {
            "tool": "PowerShell",
            "cwd": str(REPO),
            "argv": None,
            "tool_input_sha256": None,
        },
        "APPENDIX_MATERIALIZATION": {
            "tool": "PowerShell",
            "cwd": str(REPO),
            "argv": None,
            "tool_input_sha256": None,
        },
        "P0_ARTIFACT_CAPTURE": {
            "tool": "node_repl.js",
            "cwd": str(REPO),
            "argv": None,
            "tool_input_sha256":
                appendix_derived["appendix_a_source_sha256"],
        },
        "DRY_SS_TC_0": {
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", "-m", "src.cli", "export-mmi", workbook,
                "--sheet", "SS-TC 0", "--dry-run", "--include-semi",
            ],
            "tool_input_sha256": None,
        },
        "DRY_SS_TC_1": {
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", "-m", "src.cli", "export-mmi", workbook,
                "--sheet", "SS-TC 1", "--dry-run", "--include-semi",
            ],
            "tool_input_sha256": None,
        },
        "EXPORT_SS_TC_0": {
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", "-m", "src.cli", "export-mmi", workbook,
                "--sheet", "SS-TC 0", "--output-dir",
                str(TEMP / "SS-TC-0"), "--include-semi",
                "--export-unrunnable",
            ],
            "tool_input_sha256": None,
        },
        "EXPORT_SS_TC_1": {
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", "-m", "src.cli", "export-mmi", workbook,
                "--sheet", "SS-TC 1", "--output-dir",
                str(TEMP / "SS-TC-1"), "--include-semi",
                "--export-unrunnable",
            ],
            "tool_input_sha256": None,
        },
        "ANALYZE": {
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", str(TEMP / "analyze_provenance.py"),
                "--repo", str(REPO),
                "--p0", str(TEMP / "artifact-tool-work" /
                             "p0_workbook.json"),
                "--out0", str(TEMP / "SS-TC-0"),
                "--out1", str(TEMP / "SS-TC-1"),
                "--output", str(TEMP / "reconciliation.json"),
            ],
            "tool_input_sha256": None,
        },
    }
    phase_ledger: list[dict[str, Any]] = []
    ledger_capsule: dict[str, Any] | None = None
    try:
        phase_ledger = load_phase_ledger(
            args.status,
            args.last_phase,
            args.error_class,
            args.error_message,
        )
        for row in phase_ledger:
            expected = phase_contracts[row["phase"]]
            for field in (
                "tool", "cwd", "argv", "tool_input_sha256",
            ):
                if row[field] != expected[field]:
                    invariant_problems.append(
                        f"operation ledger {row['phase']} {field}"
                    )
            if (
                row["phase"] not in {
                    "HOST_PREFLIGHT",
                    "APPENDIX_MATERIALIZATION",
                    "P0_ARTIFACT_CAPTURE",
                }
                and row["status"] == "FAILED"
                and row["exit"] is None
                and row["observed"] == {
                    "producer_input_identity_valid": False
                }
            ):
                invariant_problems.append(
                    f"producer pre-invocation input drift {row['phase']}"
                )
        if (
            phase_ledger
            and phase_ledger[-1]["status"] == "FAILED"
            and phase_ledger[-1]["exit"] is None
            and phase_ledger[-1]["phase"] in {
                "DRY_SS_TC_0",
                "DRY_SS_TC_1",
                "EXPORT_SS_TC_0",
                "EXPORT_SS_TC_1",
                "ANALYZE",
            }
        ):
            terminal_phase = phase_ledger[-1]["phase"]
            terminal_exact = {
                "DRY_SS_TC_0": {"dry-run-SS-TC-0.combined.txt"},
                "DRY_SS_TC_1": {"dry-run-SS-TC-1.combined.txt"},
                "EXPORT_SS_TC_0": {
                    "SS-TC-0",
                    "export-SS-TC-0.combined.txt",
                },
                "EXPORT_SS_TC_1": {
                    "SS-TC-1",
                    "export-SS-TC-1.combined.txt",
                },
                "ANALYZE": {
                    "analyze.combined.txt",
                    "reconciliation.json",
                    "reconciliation.json.tmp",
                },
            }[terminal_phase]
            terminal_prefix = {
                "EXPORT_SS_TC_0": "SS-TC-0/",
                "EXPORT_SS_TC_1": "SS-TC-1/",
            }.get(terminal_phase)
            unexpected_terminal = [
                item["path"] for item in external_rows
                if (
                    item["path"] in terminal_exact
                    or (
                        terminal_prefix is not None
                        and item["path"].startswith(terminal_prefix)
                    )
                )
            ]
            if unexpected_terminal:
                invariant_problems.append(
                    "pre-launch terminal artifacts: "
                    + ",".join(unexpected_terminal)
                )
        materialization_rows = [
            row for row in phase_ledger
            if row["phase"] == "APPENDIX_MATERIALIZATION"
        ]
        if (
            materialization_rows
            and materialization_rows[0]["status"] == "COMPLETED"
            and materialization_rows[0]["observed"] != {
                "appendix_b_source_sha256":
                    appendix_derived["appendix_b_source_sha256"],
                "appendix_c_source_sha256":
                    appendix_derived["appendix_c_source_sha256"],
            }
        ):
            invariant_problems.append(
                "operation ledger APPENDIX_MATERIALIZATION observed"
            )
        ledger_capsule = validate_host_preflight_capsule(
            phase_ledger[0],
            capsule_sha256=args.capsule_sha256,
            directive_sha=args.directive_sha,
            directive_blob=args.directive_blob,
        )
    except (
        OSError, UnicodeError, json.JSONDecodeError, ValueError,
    ) as error:
        invariant_problems.append(
            f"operation ledger {type(error).__name__}: {error}"
        )

    external_capsule: dict[str, Any] | None = None
    external_capsule_path = (
        CAPSULE_ROOT / f"{args.capsule_sha256}.json"
    )
    try:
        external_capsule_path, external_capsule = (
            read_external_dispatch_capsule(
                args.capsule_sha256,
                directive_sha=args.directive_sha,
                directive_blob=args.directive_blob,
            )
        )
        if (
            ledger_capsule is not None
            and canonical_bytes(external_capsule)
            != canonical_bytes(ledger_capsule)
        ):
            invariant_problems.append(
                "external dispatch capsule differs from HOST_PREFLIGHT"
            )
    except (FileNotFoundError, ValueError) as error:
        invariant_problems.append(
            f"external dispatch capsule {type(error).__name__}: {error}"
        )
    dispatch_capsule = (
        ledger_capsule if ledger_capsule is not None else external_capsule
    )
    state, state_problems = snapshot(dispatch_capsule)
    invariant_problems.extend(state_problems)

    p0_path = TEMP / "artifact-tool-work" / "p0_workbook.json"
    reconciliation_path = TEMP / "reconciliation.json"
    completed_phases = {
        row["phase"] for row in phase_ledger
        if row["status"] == "COMPLETED"
    }
    p0 = None
    reconciliation = None
    try:
        if "P0_ARTIFACT_CAPTURE" in completed_phases:
            p0 = read_json(p0_path)
        if "ANALYZE" in completed_phases:
            reconciliation = read_json(reconciliation_path)
    except (
        OSError, UnicodeError, json.JSONDecodeError, ValueError,
    ) as error:
        invariant_problems.append(
            f"completed phase artifact {type(error).__name__}: {error}"
        )
    status = args.status
    error_class = args.error_class
    error_message = args.error_message
    if status == "measured":
        if args.last_phase == "P0_ARTIFACT_CAPTURE":
            p0_completed_rows = [
                row for row in phase_ledger
                if row["phase"] == "P0_ARTIFACT_CAPTURE"
                and row["status"] == "COMPLETED"
            ]
            early_input_invalid = (
                len(p0_completed_rows) == 1
                and (
                    p0_completed_rows[0].get("observed", {}).get(
                        "input_identity_valid"
                    ) is False
                    or p0_completed_rows[0].get("observed", {}).get(
                        "producer_input_identity_valid"
                    ) is False
                )
            )
            if (
                len(p0_completed_rows) == 1
                and p0_completed_rows[0].get("observed", {}).get(
                    "producer_input_identity_valid"
                ) is False
            ):
                invariant_problems.append(
                    "post-P0 producer input identity drift"
                )
            if p0 is None:
                invariant_problems.append(
                    "measured P0 mismatch requires P0 JSON"
                )
            else:
                mismatch_schema = (
                    p0.get("schema_version") == 2
                    and p0.get("directive_id") == DIRECTIVE_ID
                    and isinstance(p0.get("mappings"), list)
                    and len(p0["mappings"]) == 12
                    and p0.get("reconciled") is False
                    and valid_reason_list(
                        p0.get("p0_blocking_reasons"),
                        allow_empty=False,
                    )
                )
                if not mismatch_schema and not early_input_invalid:
                    invariant_problems.append(
                        "measured P0 early-stop gate schema"
                    )
            if reconciliation is not None:
                invariant_problems.append(
                    "measured P0 mismatch forbids reconciliation JSON"
                )
        elif p0 is None or reconciliation is None:
            invariant_problems.append(
                "full measured status requires P0 and reconciliation JSON"
            )
        else:
            if (
                p0.get("schema_version") != 2
                or p0.get("directive_id") != DIRECTIVE_ID
                or p0.get("reconciled") is not True
                or p0.get("p0_blocking_reasons") != []
            ):
                invariant_problems.append("full measured P0 gate schema")
            invariant_problems.extend(validate_reconciliation(reconciliation))
    if p0 is not None:
        before = p0.get("workbook_mtime_before_ns")
        after = p0.get("workbook_mtime_after_ns")
        observed = str(state["workbook"]["mtime_ns"])
        sha_before = p0.get("workbook_raw_sha256_before")
        sha_after = p0.get("workbook_raw_sha256_after")
        p0_input_identity_valid = (
            before == after
            and after == observed
            and sha_before == WORKBOOK_SHA
            and sha_after == WORKBOOK_SHA
            and state["workbook"]["raw_sha256"] == WORKBOOK_SHA
            and state["workbook"]["blob"] == WORKBOOK_BLOB
        )
        if not p0_input_identity_valid:
            invariant_problems.append("workbook P0/post-P0 identity")
        p0_sheets = p0.get("sheets")
        if (
            not isinstance(p0_sheets, list)
            or len(p0_sheets) != 2
            or any(not isinstance(item, dict) for item in p0_sheets)
        ):
            invariant_problems.append("P0 sheet artifact schema")
        else:
            for sheet in p0_sheets:
                sheet_name = sheet.get("sheet_name")
                relative = (
                    f"artifact-tool-work/"
                    f"render-{str(sheet_name).replace(' ', '-')}.png"
                )
                render_path = TEMP / relative
                if (
                    sheet_name not in {"SS-TC 0", "SS-TC 1"}
                    or sheet.get("render_path") != relative
                    or not render_path.is_file()
                    or is_linklike(render_path)
                    or sheet.get("render_sha256")
                    != sha256_file(render_path)
                ):
                    invariant_problems.append(
                        f"P0 render artifact {sheet_name}"
                    )
        completed_p0_rows = [
            row for row in phase_ledger
            if row["phase"] == "P0_ARTIFACT_CAPTURE"
            and row["status"] == "COMPLETED"
        ]
        expected_p0_observed = {
            "p0_workbook_sha256": sha256_file(p0_path),
            "reconciled": p0.get("reconciled"),
            "input_identity_valid": p0_input_identity_valid,
            "workbook_raw_sha256_current":
                state["workbook"]["raw_sha256"],
            "workbook_blob_current": state["workbook"]["blob"],
            "workbook_mtime_current_ns": observed,
            "producer_input_identity_valid": True,
        }
        if (
            completed_p0_rows
            and completed_p0_rows[0]["observed"] != expected_p0_observed
        ):
            invariant_problems.append(
                "operation ledger P0_ARTIFACT_CAPTURE observed"
            )
    if reconciliation is not None:
        completed_analyze_rows = [
            row for row in phase_ledger
            if row["phase"] == "ANALYZE"
            and row["status"] == "COMPLETED"
        ]
        if completed_analyze_rows and completed_analyze_rows[0][
            "observed"
        ] != {
            "producer_input_identity_valid": True,
            "process_launch_succeeded": True,
            "reconciliation_sha256": sha256_file(reconciliation_path),
        }:
            invariant_problems.append("operation ledger ANALYZE observed")
        if status == "measured" and args.last_phase == "ANALYZE":
            reconciliation_inventories = reconciliation.get("inventories")
            if not isinstance(reconciliation_inventories, list):
                reconciliation_inventories = []
            external_file_hashes = {
                row["path"]: row["raw_sha256"]
                for row in external_rows
                if row.get("type") == "file"
            }
            reconciliation_file_hashes = {
                item.get("relative_path"): item.get("raw_sha256")
                for item in reconciliation_inventories
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("relative_path"), str)
                    and isinstance(item.get("raw_sha256"), str)
                )
            }
            current_yaml_hashes = {
                path: digest
                for path, digest in external_file_hashes.items()
                if re.fullmatch(r"SS-TC-[01]/[^/]+\.yaml", path)
            }
            if current_yaml_hashes != reconciliation_file_hashes:
                invariant_problems.append(
                    "producer YAML inventory changed after analysis"
                )

    if invariant_problems:
        exit_code = 2
        label = "INPUT_INVALID"
    elif status == "infra_failure":
        exit_code = 3
        label = "INFRA_FAILURE"
    elif args.last_phase == "P0_ARTIFACT_CAPTURE":
        exit_code = 1
        label = "PROVENANCE_MISMATCH"
    elif reconciliation is not None and reconciliation.get("reconciled") is True:
        exit_code = 0
        label = "PROVENANCE_RECONCILED"
    else:
        exit_code = 1
        label = "PROVENANCE_MISMATCH"

    if exit_code == 2:
        blocking_reasons = [
            {
                "code": "INPUT_INVARIANT",
                "path": "post_state",
                "message": message,
            }
            for message in invariant_problems
        ]
    elif exit_code == 3:
        blocking_reasons = [
            {
                "code": "INFRA_FAILURE",
                "path": args.last_phase,
                "message": f"{error_class}: {error_message}",
            }
        ]
    elif exit_code == 1 and args.last_phase == "P0_ARTIFACT_CAPTURE":
        blocking_reasons = list(p0["p0_blocking_reasons"])
    elif exit_code == 1:
        blocking_reasons = list(reconciliation["blocking_reasons"])
    else:
        blocking_reasons = []
    blocking_reasons.sort(
        key=lambda item: (
            item["code"], item["path"], item["message"],
        )
    )

    command_log = [dict(row) for row in phase_ledger]
    command_log.append(
        {
            "phase": "ASSEMBLE",
            "tool": python,
            "cwd": str(REPO),
            "argv": [
                "-B", str(TEMP / "assemble_evidence.py"),
                *expected_application_args,
            ],
            "tool_input_sha256":
                appendix_derived["appendix_c_source_sha256"],
            "observed": {},
            "error_class": "",
            "error_message": "",
            "status": "EVIDENCE_WRITTEN",
            "campaign_exit": exit_code,
            "exit": exit_code,
        }
    )
    observed_toolchain = (
        phase_ledger[0].get("observed", {}).get("toolchain")
        if phase_ledger else None
    )
    toolchain = dict(observed_toolchain) if isinstance(
        observed_toolchain, dict
    ) else {}
    toolchain["artifact_tool"] = (
        ledger_capsule["module_roots"][0]["package_version"]
        if ledger_capsule else None
    )
    output = {
        "schema_version": 1,
        "directive_id": DIRECTIVE_ID,
        "dispatch_envelope": {
            "directive_raw_sha256": args.directive_sha,
            "directive_blob": args.directive_blob,
            "spec_raw_sha256": SPEC_SHA,
            "spec_blob": SPEC_BLOB,
            "generator_raw_sha256": GENERATOR_SHA,
            "generator_blob": GENERATOR_BLOB,
            "capsule_sha256": args.capsule_sha256,
            "capsule_path": external_capsule_path.as_posix(),
            "capsule_type": (
                dispatch_capsule.get("capsule_type")
                if dispatch_capsule is not None else None
            ),
            "capsule_schema_version": (
                dispatch_capsule.get("schema_version")
                if dispatch_capsule is not None else None
            ),
            "capsule_issued_at_epoch_s": (
                dispatch_capsule.get("issued_at_epoch_s")
                if dispatch_capsule is not None else None
            ),
            "capsule_expires_at_epoch_s": (
                dispatch_capsule.get("expires_at_epoch_s")
                if dispatch_capsule is not None else None
            ),
            **appendix_actual,
        },
        "entry": {
            "dispatch_capsule": dispatch_capsule,
        },
        "toolchain": toolchain,
        "producer_actors": state["producer_actors"],
        "workbook": {
            **state["workbook"],
            "p0_mtime_before_ns":
                p0.get("workbook_mtime_before_ns") if p0 else None,
            "p0_mtime_after_ns":
                p0.get("workbook_mtime_after_ns") if p0 else None,
        },
        "p0": p0,
        "p1": {
            "producer_entrypoint_mode":
                "legacy-only"
                if args.last_phase == "ANALYZE" else "not-executed",
            "logs": log_inventory(),
            "reconciliation": reconciliation,
        },
        "post_state": state,
        "command_log": command_log,
        "write_inventory": {
            "external_temp_root": {
                "path": str(TEMP),
                "event": "create new root after host preflight",
            },
            "external_temp": external_rows,
            "repo_intended_directories": [
                {
                    "path": "reports/canonical_shell_rc_provenance",
                    "event": "create only if absent",
                },
                {
                    "path":
                        "reports/canonical_shell_rc_provenance/"
                        + DIRECTIVE_ID,
                    "event": "create new empty run directory",
                },
            ],
            "repo_intended": [
                {
                    "path":
                        EVIDENCE.with_suffix(".json.tmp")
                        .relative_to(REPO).as_posix(),
                    "event": "exclusive temporary create",
                },
                {
                    "path": EVIDENCE.relative_to(REPO).as_posix(),
                    "event": "no-overwrite hard-link publish",
                },
            ],
        },
        "verdict": {
            "code": exit_code,
            "label": label,
            "requested_status": args.status,
            "last_phase": args.last_phase,
            "error_class": error_class,
            "error_message": error_message,
            "blocking_reasons": blocking_reasons,
        },
    }
    payload = canonical_bytes(output)
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    temporary = EVIDENCE.with_suffix(".json.tmp")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, EVIDENCE)
    if not EVIDENCE.is_file() or is_linklike(EVIDENCE):
        raise RuntimeError("published evidence is not an ordinary file")
    published = EVIDENCE.read_bytes()
    if (
        published != payload
        or hashlib.sha256(published).hexdigest() != payload_sha256
    ):
        raise RuntimeError("published evidence byte/hash mismatch")
    temporary.unlink()
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(3)
```

---

## Appendix R — Exact module-route negative-control probe source

아래 code fence 내부 source만 `node_repl.js`에 제출한다 (§2.3 item 5, 최대
2회, timeout `>= 300000ms`). source bytes는 UTF-8, LF, 마지막 `})();` 뒤
trailing LF 1개다. 1차 제출 `IMPORT_FAIL`이면 `js_add_node_module_dir`(capsule
`module_roots[0].root_path`, 정확히 1회) 뒤 재제출하고, 2차는 `IMPORT_OK` +
두 symbol `function`이어야 한다. 1차 `IMPORT_OK`면 add 없이 통과다.

**Expected source SHA-256:** `d57734b2131cfaf548c28c68d1febbbada6236e49ed8aa21474351f3067f7e64`

```javascript
await (async () => {
  const result = { probe: "RB-20260728-shellrc-p0p1 module-route" };
  try {
    const artifact = await import("@oai/artifact-tool");
    result.outcome = "IMPORT_OK";
    result.typeof_SpreadsheetFile = typeof artifact.SpreadsheetFile;
    result.typeof_FileBlob = typeof artifact.FileBlob;
  } catch (error) {
    result.outcome = "IMPORT_FAIL";
    result.error_message = String(
      error && error.message ? error.message : error,
    );
  }
  console.log(JSON.stringify(result, null, 2));
})();
```
