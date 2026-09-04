# KR3 Carrier Requirements — 이통3사 단말 규격 인증 대응 트랙

KT · LG U+ · SKT 단말 규격서/시험절차서를 읽고, 인증 대응 TC로 옮기는 트랙.

**기존 인덱싱 요구사항 코퍼스** `새 폴더 (2)/{KT, LGU+, THOR3_SKT_Requirements}` — 148 파일 / PDF 133 / **7,475 페이지**
**G0-A.1 corpus closure** — 214 documents: ACTIVE 72 / EXCLUDED 0 / PENDING_REVIEW 142
**G0-A.2 resolver assignment** — CARRIER_INQUIRY 112 / INTERNAL_DECISION 22 / INTAKE_CAPABILITY 8
**G0-A 권위 source ledger** — ACTIVE 72 documents: LGU+ 2 / KT 4 / SKT legacy XLS 66
**개시** 2026-08-13

---

## 1. 코퍼스 현황 (측정값)

| 사업자 | 파일 | PDF | 페이지 | 규격 ↔ 시험절차 |
|---|---:|---:|---:|---|
| KT | 116 | 103 | 6,363 | 「기능 규격」 + 「기능 **SAT** 규격」 쌍 존재 (KR 폴더 SAT 11건) |
| SKT (THOR3) | 30 | 30 | 1,112 | 요구사항 PDF 코퍼스. 시험절차는 별도 G0-A ledger의 legacy XLS 66건으로 구조 수집 |
| LG U+ | 2 | 0 | — | 「기술요구서」 + 「시험절차서」 HTML 쌍 |

148-file 집계는 기존 요구사항 인덱싱 코퍼스다. 여기에
`새 폴더 (2)/SKT_시험절차서_최신/`의 66개 `.xls` workbook을 더한 214개 파일이
G0-A.1 closure 대상이다. 그중 현재 권위 입력으로 투영되는 ACTIVE registry는 72개이며,
나머지 142개는 역할·현행성 판단 전 `PENDING_REVIEW`다. `documents=72`와
`corpus_total=214`를 같은 기수로 해석하지 않는다.

SKT Excel read-only 구조 intake 결과는 66 `READABLE` / 0 `FAILED` / 66 sheets / 8,101 inclusive used rows다.
이는 workbook/sheet/used-range inventory일 뿐이며 `semantic_parse_status: NOT_ATTEMPTED`다.
SKT business-semantic TC parsing, CTF 정규화, 실행 준비도 또는 spec coverage를 뜻하지 않는다.

### G0-A source-ledger 측정 현황

| 항목 | 측정값 |
|---|---|
| G0-A.1 corpus closure | 214 documents: ACTIVE 72 / EXCLUDED 0 / PENDING_REVIEW 142 / unclassified 0 |
| G0-A.2 resolver assignment | proposal 142: CARRIER_INQUIRY 112 / INTERNAL_DECISION 22 / INTAKE_CAPABILITY 8 |
| G0-A.2 proposal basis | NORMATIVITY_UNKNOWN 112 / SHA256_DUPLICATE_IN_CORPUS 17 / UNSUPPORTED_MEDIA 8 / NON_DOCUMENT_ASSET 5 |
| G0-A.2 duplicate evidence | 8 groups / 17 proposal members |
| 권위 입력 | 72 documents / 3 relations / LGU 28 cases / 232 expected identities |
| corpus parent exact-set | 9 entries: corpus roots 4 / declared non-corpus 5 / unexpected 0 |
| 사업자별 문서 | LGU+ 2 / KT 4 / SKT legacy XLS 66 |
| SKT 구조 intake | 66 `READABLE` / 0 `FAILED` / 66 sheets / 8,101 inclusive used rows |
| SKT 의미 파싱 | `semantic_parse_status: NOT_ATTEMPTED` |
| 정적 재생성·원본 보존 | `byte_drift=0` / `source_mutation=0` |
| 기존 LGU runnable projection | 0/28 (SKT 문서 intake로 변경되지 않음) |

이 결과는 portable `static source-ledger check`의 측정값이며
`validate PASS`·`runtime PASS`·`manual evidence observed`가 아니다.

**정독 제외 16건** — `KT_5G_20260515` / `KT_5G_20260522` 두 폴더 전량은 `20260702-KR` 대비 구버전(NSA V1.2.6~1.2.9 vs V1.3.0 / SA V1.4.0~1.5.0 vs V1.6.0)이거나 sha256 동일 중복. KT 정독 대상 103 → 87 PDF.

**언어 주의**
- `[SKT-WCDMA-002] WCDMA SBSM Supplementary Service Requirements_V1.7` = **중국어** (파일명에 표시 없음)
- `[SKT-WIFI-001] Wi-Fi Access Requirements_V1.76a` = 중국어 혼재
- `[KT-WIFI-003] … _Cn` = 중국어 (EN 폴더 소재, 영문판 없음)
- SKT 폴더 내 한국어 원본 4건 — KISA-001, SKT-VT-001, SKT-WCDMA-001 V3.26/V3.27
- SKT 영문판은 **기계번역** — 요구 취지 파악용. 단말 UI 문구·메뉴명 축자 인용 금지

**파일명 오류**
- `20260702-EN/[KT-NET-003] KT LTE Technical Requirement_V3.8.0_20240429.pdf` = sha256 기준 `20260702-KR/kt LTE 기능 규격 V3.8.0(배포용)_20260429.pdf`와 **완전 동일**. 영문판 아님. 진짜 영문판 = `KT LTE Technical Requirement_v.3.8.0_en.pdf`(197p). 파일명 `_20240429` vs 문서 배포일자 `2026.04.29` 연도 불일치
- `LGU+/2026-EN/` = 파일 0건 (영문판 미수령)

**추출 조건** — KT 한글 PDF는 **목차·머리글 페이지 폰트만** ToUnicode 매핑이 없어 한글이 빠진다. 본문 페이지는 정상 추출되므로 OCR 없이 기계 인덱싱이 된다. SKT `[SKT-5G-001] §6.1` Debug Screen 필드 목록은 **이미지**(p.70~71 추출 텍스트 0) — 3사 중 필드를 텍스트로 대조할 수 있는 건 LGU+뿐.

## 2. 산출물

```
KR3_Carrier_Requirements/
├─ README.md                          이 문서
├─ ERRATA_LGU_5G_V02_00_00.md         규격 정오표 E-01~E-06 (사업자 문의용)
├─ catalog/
│  ├─ corpus_index.json                       조문 인덱스 — 135 문서 / 12,567 조문
│  ├─ CORPUS_INDEX.md                         문서 목록 (버전·페이지·언어·조문 수·중복)
│  ├─ source_registry_v1.json                 G0-A 72-document full-hash registry
│  ├─ corpus_closure_v1.json                  G0-A.1 214-document full-hash closure
│  ├─ resolver_proposal_v1.json               G0-A.2 resolver proposal와 계산 근거
│  ├─ skt_workbook_inventory_v1.json          SKT XLS 구조 intake 결과
│  ├─ source_relations_v1.json                명시적 문서 관계 3건
│  └─ lgu_legacy_expected_ledger_v1.json      LGU 28 case / 232 expected identity ledger
├─ contracts/
│  ├─ source_scope_v1.yaml                    G0-A 입력 범위·관계 선언
│  ├─ source_scope_v2.yaml                    G0-A.1 전건 상태·현행성·관계 선언
│  ├─ source_scope_schema_v2.json              source scope v2 계약
│  ├─ corpus_closure_schema_v1.json            corpus closure 계약
│  ├─ resolver_proposal_schema_v1.json         resolver proposal 계약
│  ├─ source_registry_schema_v1.json          source registry 계약
│  ├─ skt_workbook_inventory_schema_v1.json   SKT 구조 inventory 계약
│  ├─ source_relations_schema_v1.json         문서 관계 계약
│  └─ legacy_expected_ledger_schema_v1.json   LGU legacy expected 계약
├─ stage1/
│  ├─ LGU5G_*_canonical.yaml          CTF 정규화 28건
│  └─ normalization_report.md         정규화 리포트
└─ tools/
   ├─ build_source_registry.py                registry builder
   ├─ build_corpus_closure.py                 G0-A.1 full-corpus closure builder
   ├─ build_resolver_proposal.py              G0-A.2 resolver proposal builder
   ├─ build_skt_workbook_inventory.py         SKT 구조 inventory builder/acquisition 진입점
   ├─ acquire_skt_workbook_inventory.ps1      Excel COM read-only acquisition backend
   ├─ build_source_relations.py               source relations builder
   ├─ build_legacy_expected_ledger.py         LGU expected ledger builder/checker
   ├─ check_g0a.py                            portable G0-A static checker (Excel/COM 없음)
   ├─ spec_corpus_index.py                    코퍼스 인덱서 (build / search / doc / stats)
   ├─ check_stage1.py                         CTF 산출물 자기검증
   ├─ verify_step_coverage.py                 원본 HTML ↔ CTF step 수 직접 대조
   ├─ project_runnable.py                     STAGE2 B-6 blocker 사전 투영 + capability 진단
   └─ html2txt.py                             LGU+ HTML → 구조 보존 텍스트
```

## 3. 도구 사용

```bash
# 코퍼스 인덱스 빌드 (1회, 약 3분; 저장 원장과 같은 Poppler 26.02.0 사용)
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py build --poppler "<Poppler 26.02.0 bin>"

# 또는 PowerShell 환경변수로 명시
$env:TC_RUNNER_POPPLER_BIN = "<Poppler 26.02.0 bin>"
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py build

# 조문 검색 — 3사 횡단
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py search "디버그"
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py search "Debug" --carrier SKT

# 문서 1건의 조문 목록
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py doc "5G SA 단말 기능 SAT"

# 통계
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/spec_corpus_index.py stats

# STAGE1 산출물 검증
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/check_stage1.py
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/verify_step_coverage.py

# STAGE2 B-6 사전 투영 (실제 컴파일 아님)
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/project_runnable.py

# G0-A.2 portable static checker (일반 실행: Excel/COM 미호출)
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/check_g0a.py --repo-root . --as-of 2026-08-14

# G0-A.2 portable artifact builders (scope 수기 반영 후 closure → proposal 순서)
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_corpus_closure.py --repo-root . --scope KR3_Carrier_Requirements/contracts/source_scope_v2.yaml --out KR3_Carrier_Requirements/catalog/corpus_closure_v1.json --as-of 2026-08-14
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_resolver_proposal.py --closure KR3_Carrier_Requirements/catalog/corpus_closure_v1.json --scope KR3_Carrier_Requirements/contracts/source_scope_v2.yaml --out KR3_Carrier_Requirements/catalog/resolver_proposal_v1.json
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_source_registry.py --repo-root . --scope KR3_Carrier_Requirements/contracts/source_scope_v2.yaml --out KR3_Carrier_Requirements/catalog/source_registry_v1.json
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_source_relations.py --scope KR3_Carrier_Requirements/contracts/source_scope_v2.yaml --registry KR3_Carrier_Requirements/catalog/source_registry_v1.json --out KR3_Carrier_Requirements/catalog/source_relations_v1.json
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py init --stage1 KR3_Carrier_Requirements/stage1 --out KR3_Carrier_Requirements/catalog/lgu_legacy_expected_ledger_v1.json

# 환경 한정 명시 실행: Windows Excel read-only SKT 구조 intake (일반 checker 실행 아님)
venv/Scripts/python.exe KR3_Carrier_Requirements/tools/build_skt_workbook_inventory.py --repo-root . --registry KR3_Carrier_Requirements/catalog/source_registry_v1.json --out KR3_Carrier_Requirements/catalog/skt_workbook_inventory_v1.json
```

인덱스는 **위치 안내용**이다. 판정 근거로 쓰기 전 원문 페이지를 확인할 것.
기본 corpus root는 실행 cwd가 아니라 repository root 기준 `새 폴더 (2)`로 해석되며,
`corpus_index.json`에는 POSIX 상대경로로 기록된다. `build`는 `--poppler` 또는
`TC_RUNNER_POPPLER_BIN`이 없거나 두 executable을 찾지 못하면 fail-closed한다.
저장된 인덱스와 다른 Poppler 버전으로 재생성하려면 먼저 별도 baseline 승인을 받는다.
`search`·`doc`·`stats`는 저장된 인덱스만 읽으므로 Poppler를 요구하지 않는다.

`verify_step_coverage.py`는 중간 scratchpad 없이 원본 LGU+ HTML을 직접 읽는다.
기본 코퍼스 위치가 다르면 `--source`, CTF 위치가 다르면 `--stage1`으로 명시한다.
`project_runnable.py`는 schema 합법 B-6 blocker와 capability 진단을 분리한다.
`MULTI_DEVICE_UNSUPPORTED`·`EXTERNAL_EVENT`·`UNSUPPORTED_STEP`은 진단이며
`runnable_reason` 또는 runnable 차단 건수에 포함하지 않는다.
`check_g0a.py`는 저장된 SKT 구조 inventory를 검증하며 Excel/COM을 호출하지 않는다.
Excel은 위에 분리한 명시적 acquisition 명령에서만 사용되고, 그 backend가
`acquire_skt_workbook_inventory.ps1`다.

같은 checker는 저장된 `corpus_index.json`을 재생성하지 않고
`corpus_msisdn_fixture_allowlist_v1.json`과 대조한다. `src.redaction.detect()`의
`kind == "MSISDN"` 결과 중 `docs[].sections[].title`만 대상으로 하며, 현재 불변식은
9 unique / 11 occurrences / 3 documents다. allowlist는 값 SHA-256과 원본 문서 SHA-256,
section 위치·title SHA-256을 함께 결박한다. 값 digest는 번호 원문의 중복 노출을 피하기
위한 것이며 10^9 수준 번호 공간에서 비밀화 수단은 아니다.

권한 확인 전 본문 파생물 31개는 Git에 넣지 않고 primary checkout의 local carry로
유지한다. clean clone에서 아래 경로가 **부재한 경우에만** 해당 real-data 테스트는
`local-carry artifact absent: <path>` 사유로 skip한다. 파일이나 디렉터리가 존재하지만
내용이 비었거나 손상됐거나 계약과 다르면 skip하지 않고 실패한다. `check_g0a.py`는
local-carry 3종 중 하나라도 없으면 계속 fail-closed(exit 2)한다.

| local-carry 경로 | 파일 수 | bytes | SHA-256 | 재생성·검증 경로 |
|---|---:|---:|---|---|
| `KR3_Carrier_Requirements/catalog/corpus_index.json` | 1 | 1,308,034 | `EB1B3F13BCF9AA3DE583C644CF35E3EB4F94375653327FFDDA9DBD8C471F0055` | `spec_corpus_index.py build --poppler "<Poppler 26.02.0 bin>"` |
| `KR3_Carrier_Requirements/catalog/lgu_legacy_expected_ledger_v1.json` | 1 | 183,433 | `DFC06F3C5369F0A7F27BC063F47007F8C71FD063D7D7666FF9162B8BD62A59F5` | `build_legacy_expected_ledger.py init --stage1 KR3_Carrier_Requirements/stage1 --out KR3_Carrier_Requirements/catalog/lgu_legacy_expected_ledger_v1.json` |
| `KR3_Carrier_Requirements/stage1/` | 29 | 273,617 | tree `EE5FA40EDDC24F3F5BE48B54CAD1BAF1E4D5DB33884C4404EA1288762CFD4DB6` | 결정론적 재생성 CLI 없음; `check_stage1.py`와 `verify_step_coverage.py`는 검증 전용 |

`stage1/` tree digest는 모든 regular file 29개(28 canonical YAML +
`normalization_report.md`)를 재귀 열거하고 POSIX 상대경로 오름차순으로 정렬한
`{"files":[{"path", "sha256", "size"}, ...], "schema_version":1}`을 대상으로 한다.
각 file SHA-256은 대문자이며 canonical JSON은 UTF-8,
`ensure_ascii=false`, key 정렬, 구분자 `(',', ':')`, 마지막 LF 1개 조건이다. 표의
`bytes`는 file size 합계다. stage1에는 결정론적 생성기가 없으므로 검증 명령을
재생성 명령으로 간주하지 않는다. local carry 원본은 삭제·이동하지 않는다.

KR3 commit 후보의 content review는 전화번호·serial·IMEI·절대경로 수동 패턴 스캔과
위 exact fixture 대조로 수행한다. `tools/redaction_gate.py`는 menu-tree Task 4.2의
redacted probe 산출물 전용이므로 carrier 원문 파생 index의 범용 pre-commit gate로
사용하지 않는다.

`source_scope_v2.yaml`은 사람이 관리하는 분류 계약이고 `corpus_closure_v1.json`은
214개 경로·크기·SHA-256과 scope SHA를 결박한 기계 생성 원장이다.
`resolver_proposal_v1.json`은 closure 전체의 hash·extension에서 계산한 제안이며 scope를
쓰거나 자동 반영하지 않는다. 사람이 proposal과 다른 `blocked_on`을 선택해도 허용하지만,
proposal은 당시 closure/scope bytes에 결박되므로 scope 편집 후 closure, proposal 순서로
재생성해야 한다. 신규 파일은 자동으로
PENDING 처리되지 않고 `SCOPE_UNCLASSIFIED`로 실패한다. `pending_max_age_days`는 artifact에
저장하지 않고 checker의 `--as-of 2026-08-14` 기준으로 계산한다.

자동 테스트는 작은 synthetic fixture corpus만 사용한다. 실제 214-file snapshot/hash는
명시적인 real-corpus checker acceptance에서만 수행한다.

checker의 안정 출력에는 다음 세 줄이 포함된다.

```text
corpus_msisdn_fixtures=9/9 occurrences=11/11 documents=3/3
proposal_basis=NORMATIVITY_UNKNOWN:112,SHA256_DUPLICATE_IN_CORPUS:17,UNSUPPORTED_MEDIA:8,NON_DOCUMENT_ASSET:5
duplicate_groups=8 duplicate_members=17
```

완료 어휘는 **G0-A.2 resolver 배정 내부 정합 + 회귀 고정**이다. 이는 문서의 규범성·
현행성 확정, 자동 duplicate/supersede 판정, `validate PASS` 또는 `runtime PASS`를 뜻하지 않는다.

## 4. STAGE1 정규화 현황

LGU+ 시험절차서 110항목 중 **단말 개입이 존재하는 28항목**을 CTF로 정규화 (상세 → `stage1/normalization_report.md`).

| tc_class | 건수 |
|---|---:|
| `FULL_AUTO` | **0** |
| `SEMI_AUTO` | 18 |
| `MANUAL_REQUIRED` | 8 |
| `AMBIGUOUS_NL` | 2 |

step 196 (auto 90 / manual 59 / ambiguous 47) · risk flag 84.

**FULL_AUTO 0** — 판정 사슬 전체가 단말 화면 안에서 닫히는 항목이 없다. 사업자 인증 시험은 단말 표시가 아니라 망 프로토콜 준수를 검증하므로 판정 근거가 NAS/RRC/SIP/APDU에 놓이는 것이 정상이며, **액션 자동화 + 모뎀 로그 판정** 조합이 실제 형태다.

정적 확인(2026-08-13) — `check_stage1.py` 종료코드 0(28건·196 step 구조/숫자/source_trace),
`verify_step_coverage.py` 종료코드 0(원본 HTML 196 ↔ CTF 196, 불일치 0),
`project_runnable.py` 종료코드 0(schema 합법 blocker 기준 runnable 후보 0/28:
`FIXTURE_REQUIRED` 28 · `MUTATION_UNMANAGED` 26 · `INFEASIBLE_VERIFIER` 23).
이는 실제 STAGE2 컴파일이나 `validate PASS`·`runtime PASS`를 의미하지 않는다.

## 5. 규격 정오표

`ERRATA_LGU_5G_V02_00_00.md` — LGU+ V02_00_00 (2026-07-06) 대상 6건. **상태 `OPEN`, 사업자 회신 대기.**

| ID | 요약 |
|---|---|
| E-01 | 절차서 19.1.2가 지목한 요구서 절 번호 오류 (7.12.1 → 7.13.1) |
| E-02 | Debug Screen 필드 목록 상충 — Cell ID 정의·Vendor/gNB ID·SSB RSRP 범위·TA |
| E-03 | 절차서 내 하위 절 번호 중복 (6.7.1/6.7.2가 두 시험에 중복 부여) |
| E-04 | 10장 목차 ↔ 본문 번호 불일치 + 10.4 결번 |
| E-05 | 판정기준의 타 시험 참조가 리넘버링 전 번호 (3.4·3.5·11.6·11.7) |
| E-06 | 판정기준 내용 모순 — 포트 번호 뒤바뀜·대기 기준 상충·전제 불성립 |

E-01·E-02 회신 전에는 **19.1을 STAGE2로 넘길 수 없다** (판정 필드 집합 미확정).

## 6. 미수령 문서

정규화 중 판정 근거가 외부 문서로 위임된 것이 확인된 항목.

| 문서 | 필요 이유 |
|---|---|
| `[66] LGU_디바이스_Network_UI_Mandatory` | Indicator·안테나바 표시 규격 (2.1·2.2 판정) |
| `CD_01 LGU 디바이스 LTE 기술요구서` | 발신 번호별 ESCV 매핑 (11.3·11.5 판정) |
| `CD_02 LGU_디바이스_VoLTE_기술요구서` | VoLTE 패킷 송수신 판정 (11.2·11.4 판정) |
| LGU+ 5G 영문판 | `LGU+/2026-EN/` 폴더 0건 |

## 7. 트랙 규칙

- 본 폴더는 **3사 인증 대응 규격 트랙** — 단말×앱 폴더 컨벤션(`<단말명> - <앱명>/`) 적용 대상이 아니며 `KDDI_Requirements/`와 같은 규격 트랙 계열
- 절 번호를 TC ID 단독 키로 쓰지 않는다 (E-03 — 절차서 내 번호 중복). TC ID = `LGU5G_<장>_<항>_<slug>`
- 10장 항목은 번호가 아닌 **제목으로 지시**한다 (E-04 정본 확정 전까지)
- SKT 영문판에서 UI 문구를 축자 인용하지 않는다 (기계번역)
- 인덱스 검색 결과는 원문 페이지 확인 후 사용한다
- `새 폴더 (2)` parent에 비-carrier 산출물을 무등록으로 추가하지 않는다. 이동할 수 없는 기존 자산은 소유 트랙과 보존 사유를 `source_scope_v2.yaml`의 `non_corpus_entries`에 먼저 등록해야 한다.
