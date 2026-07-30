# artifact-tool module route amendment — 확정 설계

> **STATUS: STAGE C IMPLEMENTED + TESTED — commit 승인 대기 (2026-07-29)**
>
> 사용자 승인 범위 = 권고안(Q2~Q4) 채택 + Stage C amendment 구현·보정·테스트.
> staging, commit, push, capsule capture, dispatch는 승인하지 않는다. 커밋과
> push는 글로벌 commit policy에 따라 각각 별도 명시 승인 후에만 수행한다.

대상: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md` (RB-20260728-shellrc-p0p1)
§1.4 module route 조항. 목표 = P0 spreadsheet inspection이 실제로 실행 가능한
module route를 fail-closed로 확보하되, `22616dd`의 분리 원칙(content-derived
invariant는 directive에 / 환경 관측은 external capsule에)을 유지한다.

---

## 1. 측정 사실 (2026-07-29 재확인, [측정])

### 1.1 모듈 실재 — 07-28 진단 유효

| 항목 | 값 |
|---|---|
| 설치 경로 | `C:\Users\momen\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\@oai\artifact-tool` |
| package.json version | `2.8.33` (floor `2.8.6` 충족) |
| type / exports | `module` / `"."` → `dist/artifact_tool.mjs` |
| entry bytes | 11,177,611 |
| entry SHA-256 | `ccdd0b4f0ba765273e26bcd9c6fe74fb906228244791d59434657a06135c4153` (07-28 값과 동일 — 1일 경과 무변동) |
| runtime dir mtime | 2026-07-28 06:52 |
| bare import (plain node, 해당 root 기준 CWD) | OK — exports 1171, `SpreadsheetFile`=function, `FileBlob`=function |

주의: 07-29 워크플로 env-probe 에이전트는 `.codex`·`AppData\Local\OpenAI\Codex`만
탐색하고 본 경로를 누락해 "미설치"로 오판했다. 본 절 값은 오케스트레이터 직접
재측정으로 확정.

### 1.2 신규 발견 — 제2 잠재 블로커: version export 부재

```
node -e "import('@oai/artifact-tool').then(m=>Object.keys(m).filter(k=>/version/i.test(k)))"
→ []   (version / VERSION / packageVersion 전부 미존재)
```

현행 Appendix A `artifactVersion()`(directive :2300-2307)은 module export 3종만
탐색 후 없으면 throw → **route를 고쳐도 exit 3**. 버전 게이트는 package.json
기반으로 전환해야 한다 (§3 D2).

### 1.3 node_repl 해석 모델 (kernel.js 정적 분석, [측정])

- search base = `NODE_REPL_NODE_MODULE_DIRS` env + working dir + `add_node_module_dir` 메시지 누적 (kernel.js:339-347, :2616-2618)
- bare specifier 해석은 search base **내부로 confinement** — 상위 디렉토리 node_modules walk escape는 무시 (:609, :621-622)
- 실패 문자열 = `Module not found: <specifier>` (:729-730) — directive :192 인용과 verbatim 일치
- Codex cua_node runtime 자체 node_modules의 `@oai`에는 `sky`만 존재 — artifact-tool 없음. 세션 working dir(tc-runner)에도 node_modules 없음 → **현행 search base로는 구조적으로 해석 불가**
- `load_workspace_dependencies`는 Claude/Codex 양 세션 모두 미노출 (07-28 확인)

### 1.4 [추론] 경계

- ~~node_repl 실세션에서 route 성립 여부 미실증~~ → **§1.5 P-1 probe로 해소**.
- `.cache\codex-runtimes\`는 캐시 성격 — runtime 갱신 시 경로 이동/소멸 가능.
  경로를 directive에 하드코딩하면 안 되는 근거 (07-28 권고 유지).

### 1.5 P-1 probe 실측 (2026-07-29, Codex node_repl 실세션 — MRP-20260729 rev1+rev2)

| 항목 | 값 |
|---|---|
| 최종 판정 | **probe GREEN** (Codex 자체판정 + Claude 재검증 일치, 독립 감사 ACCEPT_WITH_NOTES) |
| negative control (rev1) | `Module not found: @oai/artifact-tool` — kernel 정적 분석 예측과 verbatim 일치 |
| `js_add_node_module_dir` (rev1) | 지정 경로 수용, 반환 `true`, 오류 0 |
| root 지속성 (rev2) | **MCP 서버 수명 동안 잔존, kernel reset 무관** — rev2 JS-A가 `UNEXPECTED_SUCCESS` |
| cold import | rev2 ≈ **12.8s** (tool wall, 기본 30,000ms 예산 내) / rev1은 동등 작업 **>30s timeout** → 고변동 |
| cached re-import | 33~34ms |
| B1 identity | name/version/exports_dot/bytes/sha 전 항목 §1.1 기대값 일치 |
| B2/B3 | `ok:true`, exports 1171, `SpreadsheetFile`/`FileBlob` 둘 다 function, version-like export `[]` |
| node_repl timeout 파라미터 | 존재, 기본 30,000ms, 최대 불명 |
| side-effect | repo 변경 0·capsule 0·temp/evidence 0, HEAD `22616dd`=origin 0/0 유지 |

---

## 2. 확정 route 선택

| 후보 | 판정 | 근거 |
|---|---|---|
| **R1. `js_add_node_module_dir` 1회 + bare import** | **채택** | 메커니즘 kernel 실재(:2616). Appendix A의 package-name specifier 의미 보존. capsule 경로 공급으로 하드코딩 회피 |
| R2. 절대경로 파일 import | 기각 | node_repl.exe 내장 문서상 local file도 search root confinement → 성립 불확실 + exports 매핑 우회 |
| R3. `NODE_REPL_NODE_MODULE_DIRS` | 기각 | kernel 기동 시 env — 세션 내부에서 제어 불가 |
| R4. junction / 모듈 복사 | 기각 | junction은 directive 명시 금지, 복사는 filesystem 변이 + provenance 오염 |
| R5. openpyxl 등 대체 | 기각 | directive :194 범주 금지 — 본 amendment 범위 밖의 계약 변경 |

현행 directive :191은 `js_add_node_module_dir`를 불허하므로, amendment의 본질 =
**"capsule이 기록한 root 1개에 한해, fail-closed 검증 후, 정확히 1회 호출"로
좁혀서 허용**하는 조항 개정이다.

---

## 3. 설계 결정 D1~D9

**D1 — route 조항 개정 (§1.4·allowlist 5)**: 허용 route = 기존 bare-import search
root **+ capsule `module_roots[0]`를 `js_add_node_module_dir`로 필요 시 1회 추가**.
순서 고정: negative-control bare import 선행 → 실패 시에만 add 1회 → 재import
(probe rev2 실증 분기 — root가 MCP 서버 수명 동안 잔존하므로 무조건 add는
이중 호출 위험, §1.5). 임의 경로·조건 밖 추가 호출·junction·npm/install은 계속 금지.

**D2 — 버전·entry 게이트 전환 (controller preflight + Appendix A)**:
`artifactVersion()`의 module-export 탐색을 제거한다. controller preflight가
fail-closed 순서로 ① root absolute·repo 외부 ② root/package/package.json/entry
전체 path chain ordinary·non-reparse ③ package.json `name ==
"@oai/artifact-tool"` ④ `version >= 2.8.6` ⑤ `exports["."] ==
"./<capsule entry_relpath>"` ⑥ entry bytes/SHA == capsule 기록값을 검사한다.
전부 GREEN 후에만 add-root + `await import("@oai/artifact-tool")`를 허용하고,
Appendix A는 import된 API 심볼을 재확인한다. 어긋나면 workbook open 전 종료.

**D3 — capsule schema v2**: closed key set에 `module_roots` 추가 (배열, 본
directive에선 길이 1). 원소 필드:

```json
{
  "package_name": "@oai/artifact-tool",
  "root_path": "<capture 시 관측 절대경로>",
  "package_version": "2.8.33",
  "entry_relpath": "dist/artifact_tool.mjs",
  "entry_bytes": 11177611,
  "entry_sha256": "ccdd0b4f0ba765273e26bcd9c6fe74fb906228244791d59434657a06135c4153"
}
```

- `SCHEMA_VERSION` 1 → 2 (기존 capsule 0건 — 호환 부담 없음)
- capture: 신규 인자 `--module-root <path>` (본 directive 실행에선 필수) — capture가 위 필드를 직접 측정·기록
- **verify는 repo-only 유지**: out-of-repo 파일 재측정을 verify에 넣지 않는다.
  모듈 live 검증은 소비 시점의 controller preflight(D2)가 수행 — 검증 책임의
  위치만 이동하며 fail-closed 불변
- exit 매핑: capsule-vs-live 모듈 불일치(경로 소멸·sha 상이) = **exit 2**
  (입력 계약 위반, 여타 capsule mismatch와 동형) / 모듈 자체 부재·floor 미달 =
  **exit 3** (:186 현행 유지)

**D4 — 원자적 amendment slice** (`22616dd` 방식 단일 commit, §2.3 source-of-truth):

1. directive: §1.4·§2.3 문구 + allowlist 5 + Appendix A source(D1·D2) + Appendix A SHA 4곳 re-freeze (:759, :787, :2022, :2123)
2. spec `2026-07-27-shell-rc-remediation-design.md`: closed-schema 조항(:522-525) v2 갱신 (+ :546-556 verify 계약 문구 정합)
3. `scripts/dispatch_capsule.py`: schema v2 + `--module-root` capture 측정
4. `tests/test_dispatch_capsule.py`: 기존 조정 + 신규 (module_roots 검증·v2 스키마·경로 소멸 fail 케이스)
5. 본 설계 `2026-07-29-artifact-tool-module-route-amendment-design.md`:
   probe·구현 refinement·결정 상태의 source-of-truth

최종 수정 뒤 **commit 전에** spec/generator raw SHA·blob을 directive 전 소비
지점에 re-freeze한다. commit+push 후 완료 보고는 committed blob과의 일치만
재확인한다.
`SPEC_REVIEW_APPROVED` 토큰 값 = 신규 spec raw SHA-256으로 자동 재발행됨.

**D5 — P-1 probe 선행 게이트**: 구현 착수 전, Codex node_repl 실세션에서 최소
probe 1회 (§5). 실패 시 amendment 구현은 착수하지 않는다 (헛일 방지 — 07-28 권고).

**D6 — 경로 휘발성 대응**: 경로는 capsule에만 존재. capture→dispatch TTL
1800s 내 drift 확률 낮음 + Appendix A D2 검사로 drift는 결정론적 fail-closed.
runtime 갱신으로 경로가 바뀌면 새 capture로 해결 (directive 무수정).

**D7 — directive ID**: `RB-20260728-shellrc-p0p1` **유지 확정**. ID 소진 조건은
"실패 dispatch로 temp root 생성"(F3)이며 미발생. amendment는 dispatch가 아니다.
사용자가 권고안을 채택했으므로 재발행하지 않는다.

**D8 — 불변 항목**: P0 도구 배타성(artifact-tool only)·openpyxl 금지(:194)·P1
openpyxl carve-out(:195-196)·exit 의미론(위 D3 예외 외)·TTL/dispatchability·
토큰 구조(3 token + 6 identity — 값만 re-mint)·역할 분리(Codex 실행/Claude
재검증/사용자 승인) 전부 유지.

**D9 — node_repl timeout floor (신설, §1.5 실측 근거)**: 최초 import를 포함하는
node_repl 제출은 **명시 timeout 필수** — cold import가 기본 예산 30,000ms에
근접·초과하는 고변동(12.8s~>30s 실측)이므로 기본값 의존 금지. directive
문안에는 "최초 import 포함 블록 timeout ≥ 300,000ms 명시(최대 허용치 불명 시
지정 가능한 최대값)"로 고정 — campaign의 PowerShell timeout floor(≥300,000ms,
directive :1740-1747)와 정합. timeout 발생 시 fail-closed(exit 3, 부분출력
보존)이며 자동 재시도는 명시 회수 상한 안에서만.

---

## 3.5 구현 확정 refinement (2026-07-29 단계 C 구현 중 확정)

설계 D1~D9의 다음 항목이 구현 과정에서 정밀화됐다 (원칙 불변, 배치만 조정):

- **D2 검증 주체 이동**: Appendix A는 frozen self-contained source라 capsule
  값을 받을 채널이 없다. 모듈 identity fail-closed 검증(root 실재·name·
  version floor·entry bytes/SHA vs capsule)은 **controller preflight의
  `Assert-ModuleRouteBinding`**(directive §3 item 12, §5.2 exact PowerShell)이
  수행하고, Appendix A에는 **API 심볼 게이트**(`FileBlob`/`SpreadsheetFile` +
  `.load`/`.importXlsx` 4종 function 검사)만 남긴다. 버전 값은 module export가
  아니라 capsule `package_version`에서 취해 evidence `toolchain.artifact_tool`로
  간다.
- **negative-control = Appendix R 신설**: probe rev2의 A-패턴을 directive
  Appendix R(frozen JS, 자체 SHA freeze)로 승격. preflight GREEN·Appendix
  materialization 후 R 제출 → `IMPORT_FAIL`이면 add 1회 → R 재제출(최대 2회,
  2차는 `IMPORT_OK` 필수) → Appendix A 제출. R 덕분에 cold import 비용을
  Appendix A 밖에서 선지불(캐시 warm)한다.
- **ledger 결정론 유지**: probe/add는 MCP 호출이라 그 동적 결과를 PowerShell
  프로세스 경계 너머 ledger로 나를 수 없다. `HOST_PREFLIGHT.observed.
  module_route`는 **capsule 결박값 + Appendix R source SHA만** 담는 결정론
  object로 하고(Appendix C가 exact 검증), probe 동적 결과(negative-control/
  add 여부/제출 횟수/timeout)는 §8 완료 보고 전용으로 분리했다. ledger 8-phase
  순서는 불변.
- **capture 인자**: `--module-root <path>` + `--module-package <name>` 쌍
  (순서 페어링, 본 campaign은 1쌍). `entry_relpath`는 package.json
  `exports["."]`에서 파생. 모듈 측정도 repo snapshot처럼 2회 측정·drift 시
  미발행. generator `verify`는 구조 검증만(repo-only 유지 — D3 원안대로).
- **p0_workbook.json schema_version 1→2**: `artifact_tool_version` 필드 제거에
  따른 정직한 bump (Appendix A 출력·Appendix C 게이트 동기).
- **commit 전 교차감사 보정**: consumer gate가 live `exports["."]`와
  absolute/out-of-repo/non-reparse path chain을 다시 결박하고, Appendix C의
  P0 early-stop도 schema v2를 수용한다. spec/generator identity는 push 후
  보고값이 아니라 최종 수정 뒤 commit 전 directive 전 소비 지점에 freeze한다.

## 4. 파급 분석

- **identity cascade**: directive·spec·generator 3파일 모두 bytes 변경 →
  capsule `identities` 3종·§0 envelope 값 전부 재산출. 기존 capture된 capsule
  0건이므로 실 손실 없음. amendment commit은 **capture 이전**에 push까지
  완료돼야 함 (Gate 0.5가 identities == HEAD blob + 0/0 + clean 요구).
- **Appendix A SHA**: source 변경 → `8372beed…` 폐기, 신규 SHA를 4곳 동기 갱신
  (누락 시 §4.3 ledger·§6.3 대조에서 자체 검출됨 — fail-closed 유지).
- **F5(.gitattributes)**: `22616dd`에서 directive/spec/generator LF pin 기적용 —
  본 amendment에서 추가 조치 불요 (메모리 F5 항목은 stale).
- **테스트**: generator schema 고정 검사 조정 + Stage C 신규 19개 +
  commit 전 교차감사 보정 신규 9개. `pytest -q tests` 결과 **1529 passed,
  1 warning**(2026-07-29)일 때만 commit 후보.

---

## 5. P-1 probe — **완료 (probe GREEN, 2026-07-29)**

수행 문서 = `HANDOFF_2026-07-29_MODULE_ROUTE_PROBE_DIRECTIVE.md` (rev1: 단일
JS-B timeout으로 판정표 갭 발견 → rev2: B1/B2/B3 분할 후 GREEN). 결과 요약과
설계 반영 사항은 §1.5·D1·D9 참조. 본 게이트 통과로 단계 C(구현) 착수 가능 —
Stage C 착수 승인 후 구현·보정과 전체 회귀까지 완료했다.

probe 지시문 재사용 시 보완 후보(독립 감사 노트, rev3 후보·미적용): JS-A/B3
timeout 분류, kernel reset 후 JS-A 재실행 예외의 명문화, 재시도 timeout 구체값,
RED class 우선순위. 재probe 필요 시(RED-DRIFT·runtime 갱신 등) rev3로 반영.

---

## 6. 진행 순서 (전 단계 사용자 승인 게이트)

| 단계 | 내용 | 승인 | 상태 |
|---|---|---|---|
| A | 본 설계 검토·확정 | 사용자 | **완료 — 권고안 Q2~Q4 확정** |
| B | P-1 probe 실행 (Codex) | 사용자 | **완료 — probe GREEN (2026-07-29)** |
| C | amendment 구현·보정 (TDD: tests → 코드 → directive/spec 문안 → 전체 회귀) | 사용자 | **완료 — 1529 passed, 1 warning** |
| D | 원자적 commit (D4의 5 path 명시 stage, push 제외) | 사용자 "commit now" | **승인 대기** |
| E | §7.2 audit + FF push → committed identity 확인 → capture → 3-token dispatch → P0/P1 | 사용자 push/dispatch 각각 | 대기 |

## 7. 결정 기록과 다음 승인 게이트

1. ~~**Q1** P-1 probe 실행 승인~~ — **완료 (probe GREEN)**
2. **Q2** directive ID — **`RB-20260728-shellrc-p0p1` 유지 확정**
3. **Q3** capsule `module_roots` — **entry SHA-256 포함 확정**
4. **Q4** capsule schema — **`SCHEMA_VERSION = 2` 확정**

설계 미결정 항목은 없다. 다음 게이트는 D의 명시적 commit 승인이고, push와
dispatch는 그 이후에도 각각 별도 승인이다.
