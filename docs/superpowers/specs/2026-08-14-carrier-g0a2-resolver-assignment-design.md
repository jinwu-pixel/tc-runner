# Carrier G0-A.2 Resolver 재배정 설계

> 상태: 사용자 확정안. 구현 전 정본이며 코드, 계약 산출물, corpus 원본은 변경하지 않는다.
>
> 작성일: 2026-08-14
>
> 선행 설계: `2026-08-14-carrier-g0a1-scope-closure-design.md`

## 0. 확정 결정

G0-A.1이 남긴 `PENDING_REVIEW` 142건의 `blocked_on`을 실제 해소 주체로 재배정한다.

- 배정 근거는 **관측 가능한 속성만** 사용한다. 내용 판단을 하지 않는다.
- 기계는 `resolver_proposal_v1.json`에 **제안만** 생성한다. 사람이 검토해
  `source_scope_v2.yaml`에 수기 반영한다.
- checker에 자동 배정 경로를 만들지 않는다. G0-A.1 R1 원칙을 유지한다.

## 1. 목적과 비목표

### 1.1 목적

G0-A.1 baseline은 142건 전부를 `INTERNAL_DECISION`으로 seed했다. 이는 "어느 resolver인지도
아직 판정하지 않음"의 정직한 표기였으나, 그 결과 `pending_by_resolver`가 `142/0/0`으로
무정보 상태다. 후속 작업의 분기점을 만들 수 없다.

G0-A.2는 142건을 세 resolver로 갈라 다음을 가능하게 한다.

1. `CARRIER_INQUIRY` 집합 확정 → ③ 사업자 질의서의 입력
2. `INTERNAL_DECISION` 집합 확정 → 회신 없이 지금 줄일 수 있는 잔량 식별
3. `INTAKE_CAPABILITY` 집합 확정 → 파이프라인 확장 범위 산정

### 1.2 비목표

- `ACTIVE` / `EXCLUDED` 상태 판정
- `document_id` 발급, `carrier` / `role` / `media` 확정
- `currentness`의 `CURRENT` 승격
- PDF / HTML / XLS 의미 파싱
- corpus 파일 이동, rename, 삭제, 내용 변경
- 자동 supersede 또는 자동 duplicate 확정

`blocked_on`은 "이 파일의 상태를 확정하려면 **누가 답해야 하는가**"이지 "이 파일이
무엇인가"가 아니다. 두 질문을 같은 단계에서 섞지 않는다.

완료 어휘는 **G0-A.2 resolver 배정 내부 정합 + 회귀 고정**이다. `validate PASS`나
`runtime PASS`를 뜻하지 않으며, 규범성·현행성 확정을 주장하지 않는다.

## 2. 배정 규칙

### 2.1 우선순위와 basis

규칙은 상호배타이며 위에서부터 처음 일치하는 항목이 적용된다.

| 순위 | basis | 조건 | resolver |
|---|---|---|---|
| 1 | `SHA256_DUPLICATE_IN_CORPUS` | closure 원장 안에 동일 `sha256`을 가진 다른 문서가 존재 | `INTERNAL_DECISION` |
| 2 | `NON_DOCUMENT_ASSET` | 확장자가 `.ai` 또는 `.png` | `INTERNAL_DECISION` |
| 3 | `UNSUPPORTED_MEDIA` | 확장자가 `.doc`, `.docx`, `.zip` | `INTAKE_CAPABILITY` |
| 4 | `NORMATIVITY_UNKNOWN` | 위 어디에도 해당하지 않음 | `CARRIER_INQUIRY` |

확장자 비교는 소문자 정규화 후 수행한다. 규칙 2와 3의 확장자 집합은 상수로 선언하고
코드에 산재시키지 않는다.

### 2.2 우선순위 근거

**규칙 1이 규칙 3보다 앞선다.** 내용을 읽을 수 없어도 `sha256`이 같으면 DUPLICATE 판정에
파싱이 필요 없다. 현재 corpus에서 `.zip` 4건 중 중복은 0이라 실효 차이는 없으나, 순서를
명시하지 않으면 이후 읽을 수 없는 중복 파일이 `INTAKE_CAPABILITY`로 잘못 배정된다.

**규칙 2와 3을 가른다.** `.ai` / `.png` 5건은 전부 `새 폴더 (2)/KT/20260702-KR/Assets/`
하위의 아트워크다. 파서를 만들어도 규격 문서가 아니다. "읽을 수단이 없음"과 "문서가
아님"은 다른 문제이며 해소 주체도 다르다.

**규칙 4가 기본값이다.** 규범성과 현행성은 repo 내부 증거로 결정할 수 없다. 판단 근거가
없을 때 내부 결정으로 미루지 않고 사업자에게 넘긴다.

### 2.3 판정을 선취하지 않는다는 의미

규칙 1이 `SHA256_DUPLICATE_IN_CORPUS`로 배정하는 것은 "이 파일은 `DUPLICATE`다"가
아니라 "중복 짝이 corpus 안에 있으므로 어느 쪽을 canonical로 둘지는 내부에서 정할 수
있다"는 뜻이다. 중복군 안에서 어느 파일이 `EXCLUDED`가 되고 어느 파일이 남는지는 후속
분류가 파일 단위 근거로 정한다.

마찬가지로 규칙 2는 "이 파일은 `OUT_OF_SCOPE`다"가 아니라 "규격 문서 여부를 내부에서
판정할 수 있다"는 뜻이다.

### 2.4 기대 배정 결과

현재 corpus 기준 제안 배정은 다음과 같다.

| resolver | 건수 | KT | THOR3_SKT_Requirements |
|---|---:|---:|---:|
| `CARRIER_INQUIRY` | 112 | 83 | 29 |
| `INTERNAL_DECISION` | 22 | 21 | 1 |
| `INTAKE_CAPABILITY` | 8 | 8 | 0 |
| 계 | 142 | 112 | 30 |

basis 내역은 `NORMATIVITY_UNKNOWN` 112, `SHA256_DUPLICATE_IN_CORPUS` 17,
`UNSUPPORTED_MEDIA` 8, `NON_DOCUMENT_ASSET` 5다.

`sha256` 중복군은 8군이며 2건 군 7개와 3건 군 1개로 구성된다. 중복군에 속한 문서는
모두 `PENDING_REVIEW`이고 `ACTIVE`와 동일 해시인 문서는 0건이다.

## 3. `resolver_proposal_v1.json` 계약

### 3.1 목적

scope v2가 사람의 판단을, closure v1이 content identity를 책임진다면, proposal v1은
**기계가 계산한 배정 근거**를 책임진다. `basis`를 scope v2에 넣지 않는 이유가 여기 있다.
scope v2는 사람이 편집하는 파일이어야 하고, 계산 가능한 값을 수기 관리 대상에 섞지
않는다.

### 3.2 canonical shape

```json
{
  "closure_sha256": "<64 lowercase hex>",
  "generator": {
    "name": "build_resolver_proposal",
    "version": "1"
  },
  "proposals": [
    {
      "basis": "SHA256_DUPLICATE_IN_CORPUS",
      "blocked_on": "INTERNAL_DECISION",
      "evidence": {
        "duplicate_group_sha256": "<64 lowercase hex>",
        "duplicate_group_paths": [
          "새 폴더 (2)/KT/20260702-KR/KT 5G SA 재난문자 서비스 규격 V1.0.1_210405.pdf",
          "새 폴더 (2)/KT/KT_5G_20260522/KT 5G SA 재난문자 서비스 규격 V1.0.1_210405.pdf"
        ]
      },
      "path": "새 폴더 (2)/KT/KT_5G_20260522/KT 5G SA 재난문자 서비스 규격 V1.0.1_210405.pdf"
    }
  ],
  "schema_version": 1,
  "source_scope_sha256": "<64 lowercase hex>",
  "summary": {}
}
```

`basis`별 `evidence` 구조는 다음과 같다.

| basis | evidence 필수 키 |
|---|---|
| `SHA256_DUPLICATE_IN_CORPUS` | `duplicate_group_sha256`, `duplicate_group_paths` (2건 이상, 정렬) |
| `NON_DOCUMENT_ASSET` | `extension` |
| `UNSUPPORTED_MEDIA` | `extension` |
| `NORMATIVITY_UNKNOWN` | `{}` (빈 객체) |

`proposals`는 `PENDING_REVIEW` 문서만 담으며 `path` UTF-8 byte order로 정렬한다. JSON은
기존 `g0a_common.write_json` 계약(strict domain, UTF-8, key sort, 2-space indent, LF,
final newline)을 그대로 사용한다.

### 3.3 입력 결박

proposal은 `corpus_closure_v1.json`과 `source_scope_v2.yaml` 양쪽의 SHA-256을 기록한다.
어느 한쪽이라도 바뀌면 proposal은 stale이며 재생성해야 한다. checker는 이 결박을
검증한다.

### 3.4 summary

- `total`, `by_resolver`, `by_basis`
- `duplicate_group_count`, `duplicate_member_count`
- root별 `by_resolver`

시간 의존 값은 저장하지 않는다.

## 4. scope v2 반영 절차

1. builder가 `resolver_proposal_v1.json`을 생성한다.
2. 사람이 142건 제안을 검토한다. 특히 규칙 4로 떨어진 112건 중 내부 판정이 가능한
   항목이 섞여 있지 않은지 확인한다.
3. 사람이 `source_scope_v2.yaml`의 해당 `documents[].blocked_on`을 수정한다.
4. `recorded_date`는 갱신하지 않는다. 최초 기록 시점을 보존해야 aging이 의미를 가진다.
5. closure builder를 재실행해 `corpus_closure_v1.json`의 `blocked_on` 복제 값과
   `summary.pending_by_resolver`를 갱신한다.
6. checker를 실행해 전 계약을 재검증한다.

**기계가 scope v2를 직접 수정하지 않는다.** proposal과 scope가 불일치해도 그것은
오류가 아니라 사람이 제안을 기각한 결과다. checker는 둘의 일치를 강제하지 않는다.

## 5. checker 변경

### 5.1 `_EXPECTED_COUNTS`

resolver 기수를 회귀 가드에 추가한다.

```python
{
  "corpus_total": 214,
  "corpus_active": 72,
  "corpus_excluded": 0,
  "corpus_pending_review": 142,
  "corpus_unclassified": 0,
  "pending_by_resolver": {
    "CARRIER_INQUIRY": 112,
    "INTERNAL_DECISION": 22,
    "INTAKE_CAPABILITY": 8
  },
  "roots": { }
}
```

`roots` 기수는 G0-A.1 값에서 변경 없다. 상태 분포가 아니라 resolver 분포만 바뀐다.

### 5.2 추가 검증

- proposal 파일이 존재하면 canonical bytes와 재생성 결과가 동일한지 확인한다.
- proposal의 `closure_sha256` / `source_scope_sha256`이 현재 산출물과 일치하는지 확인한다.
- proposal `proposals[].path` 집합이 현재 `PENDING_REVIEW` 집합과 정확히 같은지 확인한다.
- 배정 규칙을 proposal 생성 시점과 검증 시점에 동일하게 적용해 basis가 재현되는지
  확인한다.

### 5.3 출력

```text
corpus_total=214 active=72 excluded=0 pending_review=142 unclassified=0
pending_by_resolver=CARRIER_INQUIRY:112,INTERNAL_DECISION:22,INTAKE_CAPABILITY:8
proposal_basis=NORMATIVITY_UNKNOWN:112,SHA256_DUPLICATE_IN_CORPUS:17,UNSUPPORTED_MEDIA:8,NON_DOCUMENT_ASSET:5
duplicate_groups=8 duplicate_members=17
```

## 6. 오류 계약

기존 `G0AError(code, detail)` 관례를 유지한다.

| error code | 조건 |
|---|---|
| `PROPOSAL_INVALID` | schema, key, enum, evidence 구조 위반 |
| `PROPOSAL_STALE` | `closure_sha256` 또는 `source_scope_sha256` 불일치 |
| `PROPOSAL_SET_MISMATCH` | proposal path 집합 ≠ 현재 `PENDING_REVIEW` 집합 |
| `PROPOSAL_BASIS_DRIFT` | 저장된 basis가 규칙 재적용 결과와 다름 |
| `ARTIFACT_BYTE_DRIFT` | proposal 재생성 bytes가 tracked artifact와 다름 |

모든 CLI 계약 오류는 traceback 없이 controlled exit 2다.

## 7. 테스트 계약

TDD로 진행한다. 자동 테스트는 214개 실 corpus를 복사하거나 읽지 않고 synthetic fixture
corpus를 사용한다.

### 7.1 배정 규칙

- 규칙 1~4 각각의 단독 적용
- 규칙 1이 규칙 3을 이기는 경우(읽을 수 없는 확장자이면서 중복인 파일)
- 규칙 2가 규칙 3을 이기는 경우
- 확장자 대소문자 혼용(`.AI`, `.PDF`)
- 중복군 3건 이상
- `ACTIVE` 문서와 동일 해시인 `PENDING_REVIEW`

### 7.2 proposal artifact

- canonical bytes와 두 번 생성 byte identity
- closure 또는 scope 변경 시 `PROPOSAL_STALE`
- `PENDING_REVIEW` 추가·삭제 시 `PROPOSAL_SET_MISMATCH`
- basis 값 조작 시 `PROPOSAL_BASIS_DRIFT`
- evidence 필수 키 누락

### 7.3 자동 배정 금지

- proposal 생성이 `source_scope_v2.yaml`을 수정하지 않음
- proposal과 scope의 `blocked_on`이 달라도 checker가 실패하지 않음
- 신규 파일은 여전히 `SCOPE_UNCLASSIFIED`이며 proposal 경로로 흡수되지 않음

selector는 다음과 같이 정확히 표기한다.

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q
```

## 8. 수용 기준

1. proposal 142건, 규칙 재적용 시 basis 100% 재현
2. `pending_by_resolver` = `CARRIER_INQUIRY:112, INTERNAL_DECISION:22, INTAKE_CAPABILITY:8`
3. `duplicate_groups=8`, `duplicate_members=17`
4. corpus 214건 상태 분포 불변 (`ACTIVE 72 / EXCLUDED 0 / PENDING_REVIEW 142`, `unclassified 0`)
5. `source_registry_v1.json`, `source_relations_v1.json`, `skt_workbook_inventory_v1.json`,
   `lgu_legacy_expected_ledger_v1.json` bytes 불변
6. corpus 214건 content/mtime drift 0
7. proposal 두 번 생성 byte-identical
8. repo root와 arbitrary CWD checker controlled exit 0
9. 명시 selector KR3 test suite 성공
10. corpus 원본, `AGENTS.md`, dependency, 다른 repo 변경 0

## 9. 조사 중 확인된 주의 사항

후속 분류가 잘못된 전제를 쓰지 않도록 기록한다.

### 9.1 파일명의 언어 표시가 내용을 보장하지 않는다

```
[ba92305c…] 새 폴더 (2)/KT/20260702-EN/[KT-NET-003] KT LTE Technical Requirement_V3.8.0_20240429.pdf
            새 폴더 (2)/KT/20260702-KR/kt LTE 기능 규격 V3.8.0(배포용)_20260429.pdf
```

EN 폴더의 영문명 파일이 KR 원본과 byte-identical이다. KT EN 38건의 역할을 폴더명이나
파일명으로 판정해서는 안 된다.

### 9.2 carrier 축이 파일 위치로 결정되지 않는다

```
[b61e77e3…] 새 폴더 (2)/KT/20260702-EN/[KISA-001] Easy Spam Report Service Requirement_V4.0_En.pdf
            새 폴더 (2)/THOR3_SKT_Requirements/[KISA-001] Easy Spam Report Service Requirement_V4.0.pdf
```

KISA 공통 규격이 KT 폴더와 SKT 폴더에 동일 바이트로 존재한다. `ACTIVE` 승격 시
`carrier` enum에 사업자 공통을 표현할 값이 없다. G0-A.2 범위가 아니며 승격 단계에서
결정한다.

### 9.3 버전 군집은 스크리닝 신호이지 판정이 아니다

파일명 정규화로 동일 규격 다중 버전군을 추출할 수 있으나, 정규화 방식에 따라 같은
규격이 다른 군으로 갈린다. 자동 supersede 판정을 금지하고 파일 단위 근거를 사람이
붙인다. G0-A.1 설계 §11의 파일 단위 원칙과 같다.

## 10. 후속 경계

G0-A.2 이후 순서는 다음과 같다.

1. `INTERNAL_DECISION` 22건 해소 — 회신 없이 지금 줄일 수 있는 잔량
2. ③ 사업자 질의서 생성 — `CARRIER_INQUIRY` 112건 기반
3. `INTAKE_CAPABILITY` 8건 — 파이프라인 확장 여부 결정

③ 질의서는 112건 파일 목록을 그대로 보내지 않는다. **배포 목록 요청** 형태
("2026년 인증 대상 규격 목록과 각 현행 버전")가 효율적이며, 회신 자체가 G0-A.1 설계
§4.9의 `evidence_type: CARRIER_DISTRIBUTION_LIST` 증거가 되어 112건의 `currentness`를
한 번에 승격시킬 수 있다.

G0-B는 LGU+ 28 TC / 232 expected의 criterion re-derive 설계로 병행 가능하다. G0-A.2는
G0-B의 선행 조건이 아니다.
