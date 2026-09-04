# G0-A.1 Scope Closure 실행 보고서

> 실행일: 2026-08-14
>
> 판정 어휘: **corpus closure 내부 정합 + 회귀 고정**

## 1. 구현 범위

- `source_scope_v2.yaml`: 214개 exact POSIX path와 ACTIVE/EXCLUDED/PENDING_REVIEW 상태
- `corpus_closure_v1.json`: scope SHA 및 214개 path/size/SHA-256/state 원장
- strict YAML loader: duplicate key, alias, merge, custom tag, invalid UTF-8, 비문자 path 거부
- filesystem closure: parent 7 entries, root 4개, 신규/누락 파일, symlink/junction, root count 검증
- 근거 검증: DUPLICATE hash, SUPERSEDED ACTIVE target, CURRENT evidence hash
- 기존 registry/relations/checker의 v2 ACTIVE projection 및 214-source snapshot 전환
- `--as-of` 기반 pending age 계산과 G0-A.1 출력

## 2. real corpus 측정값

```text
documents=72 lgu=2 kt=4 skt_xls=66
relations=3
lgu_cases=28 lgu_expected=232
skt_workbooks=66 readable=66 failed=0 sheets=66 used_rows=8101
corpus_parent_entries=7/7
corpus_total=214 active=72 excluded=0 pending_review=142 unclassified=0
pending_by_resolver=CARRIER_INQUIRY:0,INTERNAL_DECISION:142,INTAKE_CAPABILITY:0
oldest_pending_recorded_date=2026-08-14 pending_max_age_days=0
currentness=CURRENT:0,CURRENTNESS_UNVERIFIED:214
semantic_parse_status=NOT_ATTEMPTED
byte_drift=0 source_mutation=0
```

corpus bytes는 222,765,630이다. `[`·`]` 포함 경로 61개는 literal path로 정상 폐쇄됐다.

## 3. 보존 감사

214개 원본의 구현 전·후 manifest는 동일하다.

| 항목 | SHA-256 |
|---|---|
| content manifest | `501ab0d7367c4fb96d5eef06dede5a600ac94b702661b23a23abf7c0c6cb5c49` |
| mtime manifest | `e434fcd7120755e043d90e364fd2a0532f7b9bb02a5b6fa57d7fd293e4169b4b` |

기존 G0-A artifact bytes도 동일하다.

| artifact | SHA-256 |
|---|---|
| `source_registry_v1.json` | `b672f073938acd5204a0e17ba4698b1f8782477be925479f13677bb943c95142` |
| `source_relations_v1.json` | `d02383abb2f924c90a8e8734d94bde0ad7322c26299c47f86924f1c6ab896967` |
| `skt_workbook_inventory_v1.json` | `5c90c8c06a4e95c0e4f4c8063a478d724686a3efefa0f182708a8d2081160b13` |
| `lgu_legacy_expected_ledger_v1.json` | `dfc06f3c5369f0a7f27bc063f47007f8c71fd063d7d7666ff9162b8bd62a59f5` |

신규 closure artifact SHA-256은
`a7a2ccc902326e44d1e87bc0984be999f610b6cf9ef2552656cc3f5f66dec23c`다.

## 4. TDD 및 검증

주요 RED는 다음 원인에서 확인했다.

- strict loader/closure module 부재
- v1 discovery 및 previous-ID 계약 잔존
- checker의 closure artifact·`as_of`·PENDING source state 미지원
- Windows venv의 IANA timezone database 부재
- stored closure의 빈 ACTIVE ID/잘못된 상태별 값 허용
- parent entry count 하드코딩
- 공개 schema가 runtime 조건부 필드보다 느슨한 drift
- closure summary 하위 map의 공개 schema가 runtime exact-key 계약보다 느슨한 drift

각 RED는 최소 구현 후 focused GREEN으로 전환했다. 자동 테스트는 real corpus가 아니라
synthetic fixture corpus를 사용한다.

최종 명시 selector 결과:

```text
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q -rs
222 passed, 3 skipped in 245.82s
```

skip 3건은 모두 이 Windows 호스트의 symlink 생성 권한 부재(WinError 1314)다.
Windows junction 회귀 테스트는 실행됐다.

real checker는 repo root 2회와 `C:\` 임의 CWD 1회 모두 exit 0으로 종료했고,
세 출력은 §2와 동일했다.

## 5. 해석 경계

- ACTIVE 72는 현재 registry 입력이지 72개 문서의 `CURRENT` 외부 증거 확인을 뜻하지 않는다.
- PENDING_REVIEW 142는 후속 파일별 분류 대상이다.
- SKT workbook `READABLE`은 structural intake이며 semantic parse 완료가 아니다.
- 이 결과는 `validate PASS`, `runtime PASS`, `manual evidence observed`가 아니다.
- commit, staging, push, dependency 변경은 수행하지 않는다.
