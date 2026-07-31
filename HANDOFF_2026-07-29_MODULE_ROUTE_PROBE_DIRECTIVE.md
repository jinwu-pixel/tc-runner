# MODULE ROUTE PROBE 지시문 — P-1 (Codex node_repl 진단) — rev2

> **PROBE-ID: MRP-20260729-artifact-tool rev2**
>
> **성격: 단독 read-only 진단. `RB-20260728-shellrc-p0p1`의 dispatch가 아니다.**
> 본 probe는 affirmative token 0개·capsule 0개·temp root 0개·evidence root
> 0개로 수행하며, directive ID를 사용·소진하지 않는다. P0/P1의 어떤 operation도
> 실행하지 않는다. 실행 개시 = 사용자가 본 문서를 Codex 세션에 제출하는 행위.
>
> 목적: `2026-07-29-artifact-tool-module-route-amendment-design.md`(draft) §5의
> 선행 게이트. rev1 실행(2026-07-29)으로 route R1의 전반부(root 추가)는 실증
> 완료 — 남은 미지수는 **bare import 평가가 node_repl 시간예산 안에 끝나는가**
> 하나다. 결과가 RED면 amendment 구현은 착수하지 않는다.

---

## 0. 금지 (전 구간)

- repo(`c:\Users\momen\Projects\tc-runner`) 안 파일의 생성·수정·삭제 전면 금지
- npm / install / junction / 파일 복사 / 지정 외 경로의 module root 추가 금지
- pytest·python 실행 금지 (probe에 불필요)
- `js_add_node_module_dir`는 §2 지정 경로로만, **문서 전체 통산 2회 상한**
  (2회째는 §2 Step 4의 kernel-reset 재-add 분기에서만)
- JS-B2 제출 **통산 2회 상한** (2회째는 §2 Step 4 재시도 규약 충족 시에만).
  그 외 모든 JS 블록은 각 1회, 임의 재시도 금지
- RED 확정 시 개선·우회 시도 금지 — 즉시 STOP + §4 보고만
- probe 종료 후 어떤 후속 작업도 하지 않는다 (P0/P1·directive operation 포함)

## 1. Step 0 — 세션 확인

1. 세션 tool 목록에 node_repl(JS 제출)과 `js_add_node_module_dir`(또는 동등한
   module search root 추가 tool)가 존재하는지 확인한다.
   - 부재/차단 → **RED-TOOL_UNAVAILABLE**. 즉시 §4 보고 후 종료.
2. node_repl working dir을 기록한다 (변경하지 않는다).
3. **timeout 예산 확인**: node_repl tool 호출에 timeout/실행시간 파라미터가
   있는지, 있다면 기본값·최대값을 tool schema에서 확인 가능한 범위로 기록한다.
   (없거나 불명이면 "불명"으로 기록 — RED 아님.)

## 2. 절차

공통 규격: 각 code fence 내부 source만 node_repl에 제출한다. source bytes는
UTF-8, LF, 마지막 줄 뒤 trailing LF 1개다.

### Step 1 — JS-A (negative control)

**JS-A expected source SHA-256:**
`a8ed81ee65d805ac452cef3ffe5f3fece412429afc1b2d11b27c7dae28ae80fa` (360 bytes, rev1과 동일)

```js
await (async () => {
  const result = { probe: "MODULE_ROUTE_PROBE_A_NEGATIVE_CONTROL" };
  try {
    await import("@oai/artifact-tool");
    result.outcome = "UNEXPECTED_SUCCESS";
  } catch (e) {
    result.outcome = "EXPECTED_FAIL";
    result.error_message = String(e && e.message ? e.message : e);
  }
  console.log(JSON.stringify(result, null, 2));
})();
```

- `EXPECTED_FAIL` → Step 2 진행 (참고 기대 문자열
  `Module not found: @oai/artifact-tool`, 상이 시 verbatim 보고로 충분)
- `UNEXPECTED_SUCCESS` → root가 이미 search base에 잔존한다는 관측(INFO,
  RED 아님). **Step 2 생략**하고 Step 3 진행.

### Step 2 — root 추가 (Step 1이 EXPECTED_FAIL일 때만)

`js_add_node_module_dir`를 아래 경로로 1회 호출한다. 반환값·오류를 기록한다.

```text
C:\Users\momen\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules
```

- 호출 오류 또는 실패 반환 → **RED-ADDROOT_FAIL**. STOP·보고.

### Step 3 — JS-B1 (filesystem identity, import 없음)

**JS-B1 expected source SHA-256:**
`d43a62e754c3ce48e8467d17612c90f1ba5cbacaa1a36771e737afc3a3bb284c` (1083 bytes)

```js
await (async () => {
  const result = { probe: "MODULE_ROUTE_PROBE_B1_FS_IDENTITY" };
  const ROOT = "C:\\Users\\momen\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules";
  try {
    const fs = await import("node:fs/promises");
    const path = await import("node:path");
    const crypto = await import("node:crypto");
    const pkgDir = path.join(ROOT, "@oai", "artifact-tool");
    const pkgJson = JSON.parse(await fs.readFile(path.join(pkgDir, "package.json"), "utf8"));
    const entryBuf = await fs.readFile(path.join(pkgDir, "dist", "artifact_tool.mjs"));
    result.package_json = {
      name: pkgJson.name,
      version: pkgJson.version,
      exports_dot: pkgJson.exports ? pkgJson.exports["."] : null,
    };
    result.entry = {
      bytes: entryBuf.length,
      sha256: crypto.createHash("sha256").update(entryBuf).digest("hex"),
    };
  } catch (e) {
    result.error = {
      name: e && e.name ? e.name : null,
      message: String(e && e.message ? e.message : e),
    };
  }
  console.log(JSON.stringify(result, null, 2));
})();
```

- `error` 존재 (읽기 실패) → **RED-PATH_MISSING**
- 값이 §3 기대값과 불일치 → **RED-DRIFT**
- 이 단계에서 timeout → **RED-EXEC_TIMEOUT** (단계=B1 표기; fs만으로 timeout은
  예상 외 — 인프라 신호)

### Step 4 — JS-B2 (bare import 전용)

**JS-B2 expected source SHA-256:**
`6d787847d6ea8302ab2f7ad8f9345813f5ec09eaae2667f9764f8df4f2c54832` (588 bytes)

```js
await (async () => {
  console.log("IMPORT_START");
  const t0 = Date.now();
  try {
    const m = await import("@oai/artifact-tool");
    console.log(JSON.stringify({
      probe: "MODULE_ROUTE_PROBE_B2_IMPORT",
      ok: true,
      import_ms: Date.now() - t0,
      exports_count: Object.keys(m).length,
    }));
  } catch (e) {
    console.log(JSON.stringify({
      probe: "MODULE_ROUTE_PROBE_B2_IMPORT",
      ok: false,
      import_ms: Date.now() - t0,
      error_name: e && e.name ? e.name : null,
      error_message: String(e && e.message ? e.message : e),
    }));
  }
})();
```

- `ok: true` → Step 5 진행. `import_ms`를 기록한다 (참고: 동일 호스트 plain
  node 실측 2026-07-29 = 수 초 내 완료).
- `ok: false` → **RED-IMPORT_FAIL**. STOP·보고 (오류 verbatim).
- **timeout 시 재시도 규약** (모두 충족할 때만 2회째 제출 허용):
  1. 부분 출력(`IMPORT_START` 표시 여부 포함)을 verbatim 기록했고,
  2. Step 0에서 확인한 timeout 파라미터가 존재하며 기본값보다 크게 지정
     가능하고,
  3. kernel reset이 있었으면 JS-A를 재실행해 결과를 기록하고 —
     `EXPECTED_FAIL`이면 재-add(통산 2회째, 이 분기에서만 허용) 후 진행,
     `UNEXPECTED_SUCCESS`면 그대로 진행.
  위 조건에서 최대 timeout으로 JS-B2를 1회 재제출한다. 재시도 불가(파라미터
  없음/불명)이거나 2회째도 timeout → **RED-EXEC_TIMEOUT** (단계=B2, attempt
  수·부분출력·kernel reset 여부 포함 보고).

### Step 5 — JS-B3 (심볼 측정, Step 4 `ok: true`일 때만)

**JS-B3 expected source SHA-256:**
`962e8b57509ae8b8f32d1e73000765da5bac241b0456d48615bd250c67214991` (651 bytes)

```js
await (async () => {
  const result = { probe: "MODULE_ROUTE_PROBE_B3_SYMBOLS" };
  try {
    const t0 = Date.now();
    const m = await import("@oai/artifact-tool");
    result.reimport_ms = Date.now() - t0;
    result.exports_count = Object.keys(m).length;
    result.typeof_SpreadsheetFile = typeof m.SpreadsheetFile;
    result.typeof_FileBlob = typeof m.FileBlob;
    result.version_like_exports = Object.keys(m).filter((k) => /version/i.test(k));
  } catch (e) {
    result.error = {
      name: e && e.name ? e.name : null,
      message: String(e && e.message ? e.message : e),
    };
  }
  console.log(JSON.stringify(result, null, 2));
})();
```

- 두 symbol 중 하나라도 `function` 아님 → **RED-SYMBOL_MISSING**

## 3. 판정 기준

2026-07-29 Claude 호스트 실측 기대값 (plain node 기준):

| 항목 | 기대값 | 판정 단계 |
|---|---|---|
| `package_json.name` | `@oai/artifact-tool` | B1 |
| `package_json.version` | `2.8.33` | B1 |
| `package_json.exports_dot` | `./dist/artifact_tool.mjs` | B1 |
| `entry.bytes` | `11177611` | B1 |
| `entry.sha256` | `ccdd0b4f0ba765273e26bcd9c6fe74fb906228244791d59434657a06135c4153` | B1 |
| `ok` | `true` | B2 |
| `typeof_SpreadsheetFile` / `typeof_FileBlob` | `function` / `function` | B3 |
| `version_like_exports` | `[]` (version export 부재가 정상 — 게이트는 package.json 기준) | B3 |
| `exports_count` | `1171` (참고치 — sha 일치 시 정보성) | B2/B3 |

**GREEN** = Step 1 정상 분기 (`EXPECTED_FAIL`→add 또는 `UNEXPECTED_SUCCESS`)
∧ B1 전항 기대값 일치 ∧ B2 `ok: true` ∧ B3 두 symbol `function`.

**RED 분류**:

| class | 조건 | 의미 |
|---|---|---|
| RED-TOOL_UNAVAILABLE | Step 0 tool 부재/차단 | route R1 불성립 — 설계 재검토 |
| RED-ADDROOT_FAIL | Step 2 호출 오류/실패 반환 | route R1 전반부 불성립 — 설계 재검토 |
| RED-PATH_MISSING | B1 읽기 실패 | cache 이동/소멸 — 경로 재탐색 필요 |
| RED-DRIFT | B1 값 기대 불일치 | 모듈 갱신됨 — 재측정 후 기대값 갱신 (route는 성립 가능) |
| RED-EXEC_TIMEOUT | B1 timeout, 또는 B2 재시도 규약 소진 후 timeout | B1=인프라 신호 / B2=import 평가가 시간예산 초과 — amendment 설계 재검토 (P0 실행성 직결) |
| RED-IMPORT_FAIL | B2 `ok: false` | route R1 후반부 불성립 — 설계 재검토 |
| RED-SYMBOL_MISSING | B3 symbol이 function 아님 | API 상이 — 설계 재검토 |

## 4. 보고 형식

아래 항목을 순서대로, JSON·오류·부분 출력은 **verbatim** 붙여넣기로 보고한다.
파일 산출물은 만들지 않는다 (return-only).

1. Step 0: tool 존재 여부 + working dir + timeout 파라미터(기본/최대 또는 "불명")
2. Step 1: JS-A 출력 verbatim (+ 재실행했다면 그 출력도)
3. Step 2: 호출 여부(생략 시 사유)·반환값·오류 + **add 통산 호출 수**
4. Step 3: JS-B1 출력 verbatim
5. Step 4: JS-B2 attempt별 결과 verbatim (부분 출력·`IMPORT_START` 표시 여부·
   kernel reset 발생 여부·적용한 timeout 값 포함)
6. Step 5: JS-B3 출력 verbatim (미도달 시 사유)
7. 자체 판정: `probe GREEN` 또는 `probe RED-<class>` 1줄 (+ 단계 표기)
8. 제출한 각 JS source의 SHA-256 자체 산출값 (expected와 일치 여부)

보고 후 종료. 후속 판단(기대값 갱신·amendment 착수·재probe)은 Claude 재검증과
사용자 승인 영역이다.

## 5. Revision history

| rev | 날짜 | 내용 |
|---|---|---|
| rev1 | 2026-07-29 | 초판 (JS-A + 단일 JS-B). Codex 1회 실행: Step 0~2 정상 (negative control `Module not found: @oai/artifact-tool` verbatim·add 반환 `true`), Step 3 단일 JS-B가 tool boundary timeout(`js execution timed out; kernel reset`)으로 무출력 종료. timeout·UNEXPECTED_SUCCESS·add 실패 분기가 판정표에 없어 Codex가 fail-closed로 RED-TOOL_UNAVAILABLE 준용 후 STOP |
| rev2 | 2026-07-29 | JS-B를 B1(fs)/B2(import 전용+`IMPORT_START` 마커+`import_ms`)/B3(심볼)으로 3분할해 timeout 지점 판별 가능화. RED-ADDROOT_FAIL·RED-EXEC_TIMEOUT 신설, UNEXPECTED_SUCCESS=INFO 분기·kernel reset 재-add(통산 2회 상한)·B2 재시도 규약(통산 2회 상한, timeout 파라미터 확대 가능 시에만) 추가. JS-A SHA 불변 |
