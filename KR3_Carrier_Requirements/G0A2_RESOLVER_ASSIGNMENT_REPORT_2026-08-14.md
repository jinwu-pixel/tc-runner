# G0-A.2 Resolver Assignment Report — 2026-08-14

## 결론

완료 어휘는 **G0-A.2 resolver 배정 내부 정합 + 회귀 고정**이다.

- corpus 상태: ACTIVE 72 / EXCLUDED 0 / PENDING_REVIEW 142 / unclassified 0
- resolver: CARRIER_INQUIRY 112 / INTERNAL_DECISION 22 / INTAKE_CAPABILITY 8
- proposal basis: NORMATIVITY_UNKNOWN 112 / SHA256_DUPLICATE_IN_CORPUS 17 /
  UNSUPPORTED_MEDIA 8 / NON_DOCUMENT_ASSET 5
- duplicate evidence: 8 groups / 17 proposal members

이는 규범성·현행성 확정, 자동 duplicate/supersede 판정, `validate PASS`, `runtime PASS`
또는 `manual evidence observed`를 뜻하지 않는다.

## 계약과 반영 경계

`resolver_proposal_v1.json`은 closure 전체의 SHA-256·확장자에서 계산한 기계 제안이다.
builder와 checker에는 `source_scope_v2.yaml` 쓰기 경로가 없다. 사람이 proposal과 다른
`blocked_on`을 선택하는 것은 허용하며, checker는 파일별 proposal/scope resolver 일치를
강제하지 않는다.

proposal은 `corpus_closure_v1.json`과 `source_scope_v2.yaml`의 exact canonical bytes에
hash-bound된다. 수기 반영 순서는 다음과 같다.

1. baseline proposal 생성·검토
2. scope의 PENDING `blocked_on`만 수기 반영
3. closure 재생성
4. final proposal 재생성
5. checker consistency-set 검증

## 적용 근거

첫 일치 규칙은 다음 순서로 고정했다.

1. 동일 SHA-256 group → `SHA256_DUPLICATE_IN_CORPUS` / `INTERNAL_DECISION`
2. `.ai`, `.png` → `NON_DOCUMENT_ASSET` / `INTERNAL_DECISION`
3. `.doc`, `.docx`, `.zip` → `UNSUPPORTED_MEDIA` / `INTAKE_CAPABILITY`
4. 나머지 → `NORMATIVITY_UNKNOWN` / `CARRIER_INQUIRY`

root별 결과는 KT 83/21/8, THOR3_SKT_Requirements 29/1/0이다
(CARRIER_INQUIRY / INTERNAL_DECISION / INTAKE_CAPABILITY 순서).

## Cutover 증거

pre-cutover:

- source 214개 / 222,765,630 bytes
- scope SHA-256: `ec339116662709187acd59c8a441dcb5818016edddd272dd5a085cd019957c48`
- closure SHA-256: `a7a2ccc902326e44d1e87bc0984be999f610b6cf9ef2552656cc3f5f66dec23c`

post-cutover:

- scope SHA-256: `4cae416d0b285907542a47bfc6eb184bc963ab1df6dc3bf86ab097a75c8d9c3e`
- closure SHA-256: `23086d2ca77d1a9c1e83d53150382ca46e57d75c3b1803ce12ddbd195eceffa0`
- proposal SHA-256: `8b0e3bda5a0c246464dfbb7eb31dfc3f000e34b0fc4e930d23323d7ff9b1692e`
- proposal size: 40,079 bytes
- proposal 두 번 생성: byte-identical
- scope 변경: PENDING `blocked_on` scalar 120개만 변경
- `recorded_date=2026-08-14`: 142/142 유지
- source content/mtime drift: 0/214
- registry/relations 임시 rebuild: tracked bytes와 동일
- inventory/ledger hash·size drift: 0

보존 artifact SHA-256:

| artifact | SHA-256 | bytes |
|---|---|---:|
| `source_registry_v1.json` | `b672f073938acd5204a0e17ba4698b1f8782477be925479f13677bb943c95142` | 35,970 |
| `source_relations_v1.json` | `d02383abb2f924c90a8e8734d94bde0ad7322c26299c47f86924f1c6ab896967` | 1,186 |
| `skt_workbook_inventory_v1.json` | `5c90c8c06a4e95c0e4f4c8063a478d724686a3efefa0f182708a8d2081160b13` | 43,646 |
| `lgu_legacy_expected_ledger_v1.json` | `dfc06f3c5369f0a7f27bc063f47007f8c71fd063d7d7666ff9162b8bd62a59f5` | 183,433 |

## 자동 검증 경계

자동 테스트는 synthetic fixture만 사용한다. real 214-file corpus는 checker acceptance와
별도 hash/mtime 보존 감사에서만 읽는다.

- 구현 전 baseline: 222 passed / 3 skipped
- proposal builder·stored contract: 15 passed / 1 skipped
- checker integration: 50 passed / 1 skipped
- full KR3 selector 및 real checker acceptance: Task 5에서 기록

platform skip은 Windows symlink 생성 권한 또는 optional `jsonschema` 미설치에 한정한다.
dependency는 변경하지 않았다.

## 명령

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements\tools\build_corpus_closure.py --repo-root . --scope KR3_Carrier_Requirements\contracts\source_scope_v2.yaml --out KR3_Carrier_Requirements\catalog\corpus_closure_v1.json --as-of 2026-08-14
venv\Scripts\python.exe KR3_Carrier_Requirements\tools\build_resolver_proposal.py --closure KR3_Carrier_Requirements\catalog\corpus_closure_v1.json --scope KR3_Carrier_Requirements\contracts\source_scope_v2.yaml --out KR3_Carrier_Requirements\catalog\resolver_proposal_v1.json
venv\Scripts\python.exe KR3_Carrier_Requirements\tools\check_g0a.py --repo-root . --as-of 2026-08-14
```

checker 안정 출력:

```text
pending_by_resolver=CARRIER_INQUIRY:112,INTERNAL_DECISION:22,INTAKE_CAPABILITY:8
proposal_basis=NORMATIVITY_UNKNOWN:112,SHA256_DUPLICATE_IN_CORPUS:17,UNSUPPORTED_MEDIA:8,NON_DOCUMENT_ASSET:5
duplicate_groups=8 duplicate_members=17
```
