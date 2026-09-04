# Carrier G0-A.1 Scope Closure 설계

> 상태: 사용자 확정안. 구현 전 정본이며 코드, 계약 산출물, corpus 원본은 변경하지 않는다.
>
> 작성일: 2026-08-14
>
> 선행 설계: `2026-08-13-carrier-criterion-projection-g0-design.md`

## 0. 확정 결정

G0-A.1은 **B안**으로 구현한다.

- `source_scope_v2.yaml`은 사람이 판정한 문서 분류와 그 근거의 source of truth다.
- `corpus_closure_v1.json`은 214개 corpus 파일의 경로, 크기, SHA-256 및 분류 상태를
  결정론적으로 동결하는 기계 생성 원장이다.
- 두 파일은 closure 원장에 기록되는 `source_scope_sha256`으로 결박한다.
- `source_registry_v1.json`은 `ACTIVE` 문서만 소비하며, 최초 전환 시 현재 72개 문서와
  파일 바이트가 변하지 않아야 한다.

이 분리는 사람이 관리할 판단과 기계가 증명할 content identity를 한 파일에 섞지 않는다.
동시에 분류되지 않은 파일, 무단 유입·이탈, 제자리 content 교체를 모두 fail-closed한다.

## 1. 목적과 비목표

### 1.1 목적

현재 `check_g0a.py`가 잡지 못하는 다음 두 사각지대를 폐쇄한다.

1. 최초 scope 누락: 실제 214개 중 72개만 등록한 상태도 내부 count와 맞으면 통과한다.
2. corpus 무단 유입·이탈 및 비활성 문서 교체: registry 밖 142개는 현재 hash 감시 대상이
   아니다.

완료 후 실제 corpus 파일은 정확히 하나의 상태를 가지며, 전건 content identity가 원장에
결박된다.

### 1.2 비목표

G0-A.1은 다음을 수행하지 않는다.

- 214개 문서의 규범성·역할·관계를 실제로 확정하는 후속 분류
- SKT XLS 또는 PDF/HTML의 의미 파싱
- G0-B criterion schema, evidence source, oracle requirement 변경
- corpus 파일 이동, rename, 삭제 또는 내용 변경
- 사업자 현행본 확인을 대신하는 추론
- `AGENTS.md` 정책 변경

G0-A.1 완료 어휘는 **corpus closure 내부 정합 + 회귀 고정**이다. `validate PASS`나
`runtime PASS`를 뜻하지 않는다.

## 2. 기준 corpus

`corpus_parent.path`는 repo root 상대 POSIX 경로 `새 폴더 (2)`다. 현재 직접 entry와
corpus 파일 수는 다음과 같다.

| 구분 | 값 |
|---|---:|
| parent 직접 entry | 7 |
| KT 파일 | 116 |
| LGU+ 파일 | 2 |
| SKT 시험절차서 XLS | 66 |
| THOR3 SKT 요구서 PDF | 30 |
| corpus 합계 | 214 |
| 최초 ACTIVE | 72 |
| 최초 EXCLUDED | 0 |
| 최초 PENDING_REVIEW | 142 |
| corpus 총 바이트 | 222,765,630 |

직접 entry 7개는 corpus root 4개와 non-corpus 3개의 합집합이다.

- corpus root: `KT`, `LGU+`, `SKT_시험절차서_최신`, `THOR3_SKT_Requirements`
- non-corpus: `files`, `ls_log`, `Batchuserdata_1.1_2024121914_debug.apk`

## 3. 파일과 권위

| 파일 | 권위 | 작성 방식 |
|---|---|---|
| `contracts/source_scope_v2.yaml` | 사람의 상태·현행성·제외/보류 근거 | review된 수기 변경 |
| `contracts/source_scope_schema_v2.json` | scope v2 구조 계약 | 코드와 같은 변경에서 갱신 |
| `catalog/corpus_closure_v1.json` | 214개 전건 content identity와 scope 결박 | builder가 결정론 생성 |
| `catalog/source_registry_v1.json` | ACTIVE 문서 registry | v2 ACTIVE subset에서 생성 |
| `catalog/source_relations_v1.json` | ACTIVE 문서 간 관계 | v2 relations에서 생성 |

`source_scope_v1.yaml`은 G0-A provenance로 보존한다. G0-A.1 cutover 뒤 checker의 현재
입력은 v2이며, v1을 silently fallback하지 않는다. `discoveries`는 v2에 존재하지 않는다.

정의, schema, loader, builder, checker, artifact, 테스트, README는 하나의 consistency set으로
전환한다. 일부만 갱신한 상태는 허용하지 않는다.

## 4. `source_scope_v2.yaml` 계약

### 4.1 top-level

```yaml
schema_version: 2
corpus_parent: {}
corpus_roots: []
documents: []
relations: []
external_gaps: []
```

top-level key는 위 6개와 정확히 일치해야 한다. unknown key, YAML duplicate key, alias,
merge key, tag, 비문자 scalar, 비유한 수, invalid UTF-8을 거부한다. 파일은 UTF-8 without
BOM, LF로 저장한다. 모든 path 값은 YAML string이어야 한다. scalar 자체가 `[`, `{`, `!`,
`&`, `*` 같은 YAML indicator로 시작하면 single quote 또는 double quote로 감싼다. YAML
parse 실패와 string 이외의 path 값은 traceback 없이 `SCOPE_INVALID`로 거부한다.

### 4.2 경로 규칙

모든 저장 경로는 다음을 만족한다.

- repo root 상대 POSIX 경로
- `/`만 사용하고 `\\`를 허용하지 않음
- 절대경로, drive prefix, `..`, `.`, 빈 segment 불허
- textual duplicate와 Windows case-fold/resolved alias duplicate 모두 불허
- resolve 결과가 repo와 선언 root 안에 있어야 함
- parent, root, 문서 경로의 symlink·junction 조상 불허

v2에는 glob expansion이 없으므로 `*`, `?`, `[`, `]`는 존재할 경우 경로의 literal
character로 취급한다. 설계 논의에서 사용한 `LGU+*5G\_20260728/...` 같은 축약 표기를
glob으로 확장하지 않으며, 214개 경로를 디스크와 일치하는 정확한 POSIX literal로
열거한다. 현재 `[`·`]`를 포함한 61개 경로도 이 규칙으로 유효하다.

### 4.3 corpus parent

```yaml
corpus_parent:
  path: 새 폴더 (2)
  expected_entries: 7
  non_corpus_entries:
    - name: files
      kind: DIRECTORY
      rationale: 이전 디버깅 산출물
    - name: ls_log
      kind: DIRECTORY
      rationale: 이전 디버깅 산출물
    - name: Batchuserdata_1.1_2024121914_debug.apk
      kind: FILE
      rationale: 테스트 도구
```

checker는 parent 직접 entry의 이름과 kind가 다음 집합과 정확히 같은지 확인한다.

`basename(corpus_roots.root) ∪ non_corpus_entries.name`

`expected_entries`는 집합 크기에 대한 별도 회귀 가드다. 이름이 같아도 file↔directory가
바뀌면 실패한다. non-corpus는 corpus 파일 수와 closure hash 대상에 포함하지 않는다.

### 4.4 corpus roots

```yaml
corpus_roots:
  - root: 새 폴더 (2)/KT
    expected_total: 116
  - root: 새 폴더 (2)/LGU+
    expected_total: 2
  - root: 새 폴더 (2)/SKT_시험절차서_최신
    expected_total: 66
  - root: 새 폴더 (2)/THOR3_SKT_Requirements
    expected_total: 30
```

`expected_total`은 해당 root 아래의 **recursive regular file 수**다. 하위 directory 수는
포함하지 않는다. 모든 root는 parent의 직접 directory여야 하며 root 간 overlap을
허용하지 않는다.

### 4.5 문서 상태

모든 actual corpus file은 `documents`에 정확히 한 번 선언되고 다음 배타적 상태 중 하나를
가진다.

| 상태 | 의미 | 상태별 필수 필드 |
|---|---|---|
| `ACTIVE` | 현재 normative input이며 registry 대상 | `document_id`, `carrier`, `role`, `media` |
| `EXCLUDED` | 증명 의무를 충족해 corpus에서 제외 | `exclusion_reason` 및 사유별 증거 |
| `PENDING_REVIEW` | 역할·현행성·관계가 아직 미확정 | `blocked_on`, `recorded_date` |

공통 필드는 `path`, `state`, `currentness`다. 상태와 무관한 필드를 임의로 추가하지 않는다.
ACTIVE가 아닌 문서에는 `document_id`를 미리 발급하지 않는다. 후속 분류에서 ACTIVE로
승격할 때 immutable ID를 발급한다.

초기 seed 규칙은 다음과 같다.

- 기존 registry 72개: `ACTIVE`
- 나머지 142개: `PENDING_REVIEW`, `blocked_on: INTERNAL_DECISION`,
  `recorded_date: 2026-08-14`
- 214개 전부: `currentness: CURRENTNESS_UNVERIFIED`
- `EXCLUDED`: 0

이는 자동 분류가 아니다. 미결 상태를 명시적으로 기록하여 unclassified를 0으로 만드는
최초 baseline이다. 새로 유입된 215번째 파일에는 이 규칙을 자동 적용하지 않는다.

### 4.6 ACTIVE

```yaml
- path: 새 폴더 (2)/LGU+/LGU+_5G_20260728/CD_20_LGU_디바이스_5G_기술요구서_V02_00_00.html
  state: ACTIVE
  document_id: LGU_REQ_5G_V02_00_00
  carrier: LGU+
  role: REQUIREMENT
  media: text/html
  currentness: CURRENTNESS_UNVERIFIED
```

carrier, role, media enum은 기존 source registry 계약과 동일하다. 기존 72개 ACTIVE의
`document_id`와 canonical registry ordering을 보존한다. 기존 discovery로 발급된 SKT
66개 ID도 v2 문서 entry에 명시해 이전 registry에 대한 순환 의존을 제거한다.

### 4.7 EXCLUDED

`exclusion_reason`과 증명 의무는 다음과 같다.

| reason | 필수 필드 | checker 증명 |
|---|---|---|
| `DUPLICATE` | `duplicate_of: <path>` | 양쪽 closure SHA-256 동일 |
| `SUPERSEDED` | `superseded_by: <document_id>` | 대상이 ACTIVE로 존재 |
| `REFERENCE_ONLY` | `rationale` | 비어 있지 않은 기록 |
| `OUT_OF_SCOPE` | `rationale` | 비어 있지 않은 기록 |

`duplicate_of`는 exact declared path이며 자기 자신, chain, cycle을 허용하지 않는다.
duplicate 대상은 `ACTIVE` 또는 더 직접적인 canonical 문서여야 한다. `SUPERSEDED` 대상은
반드시 ACTIVE document ID여야 하고, dangling ID와 EXCLUDED/PENDING target은 실패한다.

REFERENCE_ONLY와 OUT_OF_SCOPE의 사업적 타당성을 checker가 증명할 수는 없다. checker는
근거 존재와 구조만 고정하고 사람 review가 의미를 책임진다. EXCLUDED 문서도 closure
원장의 full hash 대상이다.

`NOT_RECEIVED`는 exclusion reason이 아니다. 존재하지 않는 파일은 §4.10의
`external_gaps`로 기록한다.

### 4.8 PENDING_REVIEW

```yaml
- path: 새 폴더 (2)/KT/20260702-KR/kt LTE 기능 규격 V3.8.0(배포용)_20260429.pdf
  state: PENDING_REVIEW
  blocked_on: INTERNAL_DECISION
  recorded_date: 2026-08-14
  currentness: CURRENTNESS_UNVERIFIED
```

`blocked_on` enum과 해소 책임은 다음과 같다.

| 값 | 해소 주체 |
|---|---|
| `CARRIER_INQUIRY` | 사업자 회신 |
| `INTERNAL_DECISION` | 내부 역할·범위 판정 |
| `INTAKE_CAPABILITY` | `.doc`, `.docx`, `.zip` 등 intake 기능 |

`recorded_date`는 strict `YYYY-MM-DD`이며 미래 날짜를 허용하지 않는다. PENDING_REVIEW는
사람이 entry를 명시할 때만 생긴다. discovery나 신규 파일 자동 흡수 경로는 없다.

### 4.9 currentness

`currentness`는 상태와 직교하며 214개 모든 문서에 필수다.

| 값 | 의미 |
|---|---|
| `CURRENTNESS_UNVERIFIED` | 사업자 배포 목록·공문 증거가 아직 결박되지 않음 |
| `CURRENT` | 외부 증거를 보존하고 현재본임을 확인 |

`CURRENT`는 다음 구조를 필수로 한다.

```yaml
currentness: CURRENT
verified_by:
  evidence_type: CARRIER_DISTRIBUTION_LIST
  evidence_path: KR3_Carrier_Requirements/evidence/currentness/<immutable-file>
  evidence_sha256: <64 lowercase hex>
  verified_date: 2026-08-14
```

`evidence_type`은 `CARRIER_DISTRIBUTION_LIST | OFFICIAL_NOTICE`다. evidence는 repo 안의
immutable saved copy여야 하며 path containment, 존재, SHA-256을 checker가 검증한다.
외부 링크나 구두 확인만으로 CURRENT로 승격하지 않는다. `CURRENTNESS_UNVERIFIED`에는
`verified_by`를 두지 않는다.

### 4.10 external gaps

존재하지 않는 미수령 문서는 corpus closure 집합에 넣지 않는다.

```yaml
external_gaps:
  - gap_id: LGU_MISSING_NETWORK_UI_MANDATORY
    carrier: LGU+
    description: Network_UI_Mandatory 미수령
    blocked_on: CARRIER_INQUIRY
    recorded_date: 2026-08-14
```

필수 필드는 `gap_id`, `carrier`, `description`, `blocked_on`, `recorded_date`다. gap ID는
유일해야 한다. external gap count는 214 corpus total에 포함하지 않는다.

### 4.11 relations

v1 relation shape와 ID를 유지한다. source와 target document ID가 모두 ACTIVE일 때만
유효하다. PENDING/EXCLUDED 문서에 대한 추정 관계를 미리 만들지 않는다.

최초 G0-A.1에서 기존 3개 relation artifact 바이트는 불변이어야 한다. 후속 분류가 새
ACTIVE 쌍을 확정할 때 relation과 registry를 같은 consistency set에서 갱신한다.

## 5. `corpus_closure_v1.json` 계약

### 5.1 목적

scope v2가 “이 문서를 어떻게 분류했는가”를 책임진다면 closure v1은 “그 판단이 정확히
어떤 파일 bytes에 적용되었는가”를 책임진다. PENDING/EXCLUDED도 ACTIVE와 같은 수준으로
hash pin한다.

### 5.2 canonical shape

```json
{
  "corpus_parent": "새 폴더 (2)",
  "documents": [
    {
      "currentness": "CURRENTNESS_UNVERIFIED",
      "path": "새 폴더 (2)/KT/20260702-KR/kt LTE 기능 규격 V3.8.0(배포용)_20260429.pdf",
      "root": "새 폴더 (2)/KT",
      "sha256": "<64 lowercase hex>",
      "size_bytes": 0,
      "state": "PENDING_REVIEW"
    }
  ],
  "generator": {
    "name": "build_corpus_closure",
    "version": "1"
  },
  "schema_version": 1,
  "source_scope_path": "KR3_Carrier_Requirements/contracts/source_scope_v2.yaml",
  "source_scope_sha256": "<64 lowercase hex>",
  "summary": {}
}
```

실제 document entry에는 상태별 audit key를 함께 복제한다.

- ACTIVE: `document_id`
- EXCLUDED: `exclusion_reason`
- PENDING_REVIEW: `blocked_on`, `recorded_date`

scope의 상세 rationale과 verified_by 전체는 중복 저장하지 않고 `source_scope_sha256`으로
결박한다. document 배열은 UTF-8 path byte order로 정렬한다. JSON은 strict domain,
UTF-8, key sort, 2-space indent, LF, final newline의 기존 `g0a_common.write_json` 계약을
사용한다.

### 5.3 summary

summary에는 다음 안정 기수를 저장한다.

- `total`, `active`, `excluded`, `pending_review`, `unclassified`
- root별 `{active, excluded, pending_review, total}`
- `pending_by_resolver`
- `oldest_pending_recorded_date`
- `currentness`별 count

시간 경과에 따라 바뀌는 `pending_max_age_days`는 artifact에 저장하지 않는다. checker CLI가
`--as-of YYYY-MM-DD` 기준으로 계산해 출력하며 기본값은 실행일의 Asia/Seoul calendar
date다. 테스트와 acceptance 명령은 `--as-of 2026-08-14`를 명시해 결정론을 유지한다.

## 6. builder와 checker 흐름

### 6.1 load 및 구조 검증

1. `source_scope_v2.yaml`을 strict loader로 읽는다.
2. schema와 runtime validation을 모두 수행한다.
3. exact key, enum, conditional field, 날짜, path를 검증한다.
4. document ID, relation ID, gap ID와 경로의 유일성을 확인한다.

### 6.2 filesystem closure

1. repo root, parent, 4개 root를 resolve하고 containment를 확인한다.
2. symlink/junction 조상을 거부한다.
3. parent 직접 entry 이름·kind 집합을 검사한다.
4. 4개 root 아래 recursive regular file을 전수 열거한다.
5. actual file path set과 `documents.path` set의 정확한 동등성을 검사한다.
6. root별 actual/declared/expected_total을 서로 대조한다.

이 순서에서 새 215번째 파일은 어떤 상태도 자동 부여받지 않고
`SCOPE_UNCLASSIFIED`로 실패한다.

### 6.3 snapshot과 content identity

기존 G0-A read-only 검증을 72 ACTIVE에서 214 전건으로 확장한다.

1. 원본 214개의 `(sha256, mtime_ns)` before state를 수집한다.
2. scope, schema, currentness evidence와 214개 파일을 임시 snapshot tree로 복사한다.
3. 복사본 SHA가 before SHA와 같은지 확인하고 snapshot을 read-only로 바꾼다.
4. builder는 snapshot만 읽어 closure, registry, relation을 재생성한다.
5. tracked artifact와 canonical bytes를 비교한다.
6. 원본 214개와 보조 입력의 after state를 수집한다.
7. before/after 차이가 있으면 `SOURCE_MUTATION`으로 실패한다.

checker는 Excel COM, QCAT, ADB, network를 호출하지 않는다. `.xls`, `.zip`, `.doc`도 binary
bytes로 snapshot/hash만 한다.

자동 테스트는 214개 실 corpus를 복사하거나 읽지 않고 작은 synthetic fixture corpus를
사용한다. 전건 약 222.8 MB snapshot/hash 비용은 명시적인 real-corpus checker acceptance에만
발생해야 하며, 일반 KR3 test suite가 실 corpus에 의존하는 회귀를 금지한다.

### 6.4 registry와 기존 artifact 불변성

`build_source_registry.py`는 v2 `ACTIVE` entry만 소비한다. 최초 cutover acceptance에서
다음을 요구한다.

- registry documents 72
- LGU 2 / KT 4 / SKT XLS 66
- `source_registry_v1.json` 전체 bytes와 SHA-256이 G0-A baseline과 동일
- `source_relations_v1.json` 3 relations 전체 bytes와 SHA-256 동일
- SKT inventory와 LGU legacy expected ledger bytes 동일

registry schema version은 바꾸지 않는다. v2 scope가 existing SKT document IDs를
명시하므로 registry 재생성은 더 이상 `previous=registry`에 ID 배정을 의존하지 않는다.

## 7. fail-closed 오류 계약

기존 `G0AError(code, detail)` 관례를 유지한다.

| error code | 조건 |
|---|---|
| `SCOPE_INVALID` | schema, key, enum, date, canonical path 계약 위반 |
| `SCOPE_PARENT_DRIFT` | parent 직접 entry 집합이 선언과 다름 |
| `SCOPE_PARENT_KIND_MISMATCH` | 선언한 file/directory kind가 다름 |
| `SCOPE_UNCLASSIFIED` | actual root file이 documents에 없음 |
| `SCOPE_PATH_MISSING` | documents path가 디스크에 없음 |
| `SCOPE_STATE_CONFLICT` | 한 textual/resolved 경로가 둘 이상 선언 |
| `SCOPE_TOTAL_MISMATCH` | root actual/declared/expected total 불일치 |
| `EXCLUSION_EVIDENCE_MISSING` | reason별 필수 evidence 누락 |
| `DUPLICATE_HASH_MISMATCH` | DUPLICATE 양쪽 SHA-256이 다름 |
| `SUPERSEDED_TARGET_UNKNOWN` | superseded_by가 ACTIVE에 없음 |
| `PENDING_BLOCKER_MISSING` | blocked_on 또는 recorded_date 누락 |
| `CURRENTNESS_EVIDENCE_MISSING` | CURRENT의 immutable evidence 누락·hash drift |
| `RELATION_ENDPOINT_NOT_ACTIVE` | relation 양단 중 하나가 ACTIVE가 아님 |
| `ARTIFACT_BYTE_DRIFT` | closure/registry/relation 재생성 bytes가 tracked artifact와 다름 |
| `SOURCE_MUTATION` | 검사 중 source 또는 보조 입력의 hash/mtime 변화 |

하나의 물리 파일에서 여러 오류가 동시에 가능할 때 loader/path 안전 오류를 먼저,
filesystem set 오류를 다음, evidence/relation 오류를 그다음, artifact drift를 마지막으로
보고한다. 모든 CLI 계약 오류는 traceback 없이 controlled exit 2다.

## 8. `_EXPECTED_COUNTS`와 보고

`_EXPECTED_COUNTS`는 발견 도구가 아니라 closure 이후 상태에 대한 회귀 가드다. 다음처럼
root별 상태 기수로 확장한다.

```python
{
  "corpus_total": 214,
  "corpus_active": 72,
  "corpus_excluded": 0,
  "corpus_pending_review": 142,
  "corpus_unclassified": 0,
  "roots": {
    "새 폴더 (2)/KT": {"active": 4, "excluded": 0, "pending_review": 112, "total": 116},
    "새 폴더 (2)/LGU+": {"active": 2, "excluded": 0, "pending_review": 0, "total": 2},
    "새 폴더 (2)/SKT_시험절차서_최신": {"active": 66, "excluded": 0, "pending_review": 0, "total": 66},
    "새 폴더 (2)/THOR3_SKT_Requirements": {"active": 0, "excluded": 0, "pending_review": 30, "total": 30}
  }
}
```

checker 성공 출력에는 기존 G0-A 수치와 함께 다음을 추가한다.

```text
corpus_parent_entries=7/7
corpus_total=214 active=72 excluded=0 pending_review=142 unclassified=0
pending_by_resolver=CARRIER_INQUIRY:0,INTERNAL_DECISION:142,INTAKE_CAPABILITY:0
oldest_pending_recorded_date=2026-08-14 pending_max_age_days=0
currentness=CURRENT:0,CURRENTNESS_UNVERIFIED:214
```

`documents=72`는 ACTIVE registry count라고 명시한다. `corpus_total=214`와 혼용하지 않는다.

## 9. 테스트 계약

구현은 TDD로 진행한다. 최소 회귀군은 다음을 포함한다.

### 9.1 scope parsing과 path

- v2 happy path와 exact top-level/state key
- duplicate YAML key, alias, tag, invalid UTF-8, 비유한 수 거부
- absolute/backslash/dot/dot-dot/noncanonical path 거부, glob expansion 없음
- `*`, `?`, `[`, `]` wildcard metacharacter는 저장된 literal path 문자로 처리
- textual, case-fold, resolved alias duplicate 거부
- repo/root 밖 resolve, symlink, Windows junction 거부

### 9.2 closure set

- parent direct entry 추가·삭제·rename·kind 변경
- 215번째 file 생성 시 `SCOPE_UNCLASSIFIED`
- declared file 삭제 시 `SCOPE_PATH_MISSING`
- duplicate document 선언 시 `SCOPE_STATE_CONFLICT`
- 각 root expected_total drift
- directory는 file total에 포함하지 않음

### 9.3 상태와 근거

- ACTIVE 조건부 필드와 immutable ID uniqueness
- 네 exclusion reason의 필수 증거
- DUPLICATE equal/unequal SHA와 self/chain/cycle
- SUPERSEDED ACTIVE/dangling/non-ACTIVE target
- PENDING blocked_on/date 누락 및 future date
- CURRENT verified_by missing/path missing/hash drift
- relation ACTIVE/비ACTIVE endpoint
- external gap exact shape와 ID uniqueness

### 9.4 artifact와 read-only

- closure canonical bytes와 두 번 생성 byte identity
- scope SHA 변경 시 closure drift
- PENDING/EXCLUDED file in-place 교체 시 drift
- source mutation during builder detection
- snapshot만 builder에 전달되는지 확인
- arbitrary CWD 실행
- stored artifact missing/extra/noncanonical/stale fail-closed
- initial registry/relation/inventory/legacy ledger byte identity

실제 test selector는 다음과 같이 범위를 정확히 표기한다.

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q
```

repo root 전체 pytest와 혼용하지 않는다. platform privilege로 symlink 생성이 불가능하면
그 테스트만 명시 skip할 수 있으나 Windows junction regression은 실행되어야 한다.

## 10. 수용 기준

G0-A.1 구현 acceptance는 다음을 모두 만족해야 한다.

1. parent direct entry `7/7 MATCH`
2. actual/declared/closure documents `214/214/214`
3. `ACTIVE 72`, `EXCLUDED 0`, `PENDING_REVIEW 142`, `unclassified 0`
4. `INTERNAL_DECISION 142`, oldest pending date `2026-08-14`
5. 214개 source before/after hash·mtime drift 0
6. closure artifact 두 번 생성 byte-identical
7. 기존 registry 72와 네 G0-A artifact의 canonical bytes 불변
8. repo root와 arbitrary CWD checker controlled exit 0
9. 명시 selector의 KR3 test suite 성공
10. corpus 원본, AGENTS, dependency, 다른 repo 변경 0

acceptance 보고는 “G0-A.1 corpus closure 내부 정합 + 회귀 고정”으로 한정한다. 사업자
현행성, normative role, semantic parse 완료를 주장하지 않는다.

## 11. 후속 경계

G0-A.1 뒤의 1차 분류는 142개 PENDING_REVIEW를 파일 단위로 판정한다.

- KT 구버전 16개도 폴더 일괄 제외하지 않는다.
- KT EN 38개는 hash 동일 1개만 DUPLICATE 후보이며 나머지는 역할 판단 대상이다.
- SKT 요구서 30개 안의 같은 규격 ID/version pair도 file별 SUPERSEDED 근거를 요구한다.
- 역할·규범성 확정 문서는 ACTIVE로 승격하고 document ID와 관계를 함께 추가한다.
- 사업자 회신 대기는 `blocked_on: CARRIER_INQUIRY`로 전환한다.
- parser 미지원만 남은 문서는 `INTAKE_CAPABILITY`로 전환한다.

모든 상태·resolver 전환은 `source_scope_v2.yaml`, `corpus_closure_v1.json`, root별 상태
기수와 `_EXPECTED_COUNTS`, 관련 테스트를 같은 consistency set에서 갱신한다. 따라서 초기
`INTERNAL_DECISION: 142` acceptance가 후속 분류로 깨지는 것은 예정된 계약 전환이며,
부분 갱신 상태만 회귀 실패로 취급한다.

G0-B는 LGU+ 28 TC/232 expected의 criterion re-derive 설계로 병행할 수 있지만, G0-A.1
cutover 이전에 source scope 완료를 주장하지 않는다. `oracle_status`는 계속 projection
파생 값이며 source CTF에 저장하지 않는다.

focus 계약의 검증 모집단은 LGU 232가 아니다. 후속 G0-B에서 `focus_transition`은 THOR2
ALT Basic의 `focus_state` 55개를 검증 모집단으로 사용하고, 그중 explicit list-model
migration 8개를 별도 migration acceptance로 보고한다.
