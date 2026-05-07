# tc-runner Operating Policy v2 Proposal

**Status:** DRAFT proposal; repo-fixed at `b4552c4`; policy v2 not applied; no code change.
**Origin baseline:** origin/master = `7af206d` (proposal authoring snapshot)
**Empirical basis:** Music greenfield SMOKE_01~06 (cumulative runtime 112/112 PASS)

본 문서는 안전장치 제거 문서가 아니다. Music Phase 1에서 드러난 운영 비용(승인·audit·commit·push·memory)을 줄이기 위한 정책 초안이며, 검토 자체를 제거하지 않고 검토 시점을 일부 이동하는 제한적 최적화 제안이다.

---

## 1. Problem Statement

### 1-1. Music Phase 1 결과 (실증 근거)

| Phase | TC | Runtime | Commit |
|---|---|---|---|
| 1A | SMOKE_01 app launch | 10/10 PASS | `cd879cb` |
| 1B | SMOKE_02 home tabs | 24/24 PASS | `cd879cb` |
| 1C | SMOKE_03 first-track player surface | 12/12 PASS | `0d36c44` |
| 1D | SMOKE_04 search focus + keyboard | 13/13 PASS | `19c706c` |
| 1E | SMOKE_05 search query result | 15/15 PASS | `65f436c` |
| 1F-Retry | SMOKE_06 favorite add-remove cleanup | 38/38 PASS | `7af206d` |
| | **Cumulative** | **112/112 PASS** | |

- origin/master = `7af206d`
- PR 5 capability commit = `469a555` (`tap_content_desc` + `verify_content_desc`)
- SMOKE_06 testdata commit = `7af206d`

### 1-2. 운영 병목

- 실제 테스트보다 gate/audit/commit/push/memory 작업이 더 오래 걸림
- per-SMOKE approval chain 과도 (1 SMOKE = scope+draft+runtime+commit+push+memory = 6 승인)
- single YAML commit 정책 비용 큼 (6 SMOKE = 6 commit = 6 push = 6 audit)
- manual probe/anchor selection 병목 (앱당 첫 회 probe dump 9~11종)
- capability gap interrupt 발생 (SMOKE_06 → PR 5 → SMOKE_06 retry, 며칠 단절)
- generated artifact strict audit 반복 (catalog/, probe_*.xml, reports/ 매번 staged 검사)
- memory update 반복 (SMOKE 단위 갱신)
- delta 가치 미실증 (앱 새 버전 도착 0회, 1세대 비용 그대로 지불 중)

---

## 2. Keep (유지 정책)

다음 정책은 v2에서도 유지한다:

- src/schema/runner/capability 변경은 **별도 PR**
- persistent/high mutation runtime gate **유지**
- generated/probe/catalog/reports **commit 금지**
- fast-forward only / force 금지
- coordinate fallback 금지 (TC YAML 기준)
- capability gap 발견 시 testdata에 억지 반영 금지
- Source-of-truth Policy (schema/code/test/docs 동시 PR) 유지
- capability PR과 testdata PR **분리**
- source/schema/runner 변경과 YAML testdata 변경 **분리**

---

## 3. Core Correction: Tier 0 does not delete the 4-stage operating pattern

### 3-1. 핵심 문장

- **Tier 0 자동 진행은 4단 운영 패턴 폐기가 아니다.**
- 검증된 동일 패턴에 한해 사전 검토 일부를 batch 사후 검토로 이동하는 제한적 최적화다.
- 새 패턴 / 새 capability / 새 mutation / 새 surface / 새 cleanup이 나오면 **즉시 4단 운영 패턴으로 복원**한다.
- **검토 자체를 제거하지 않는다. 검토 시점을 일부 이동할 뿐이다.**

### 3-2. 기존 4단 운영 패턴

```
사전 보고 → 검토 → 의견 → 직시 → 진행
```

(진행은 결과 단계, 4단은 사전 보고·검토·의견·직시)

### 3-3. 정책 해석

- Tier 0은 "scope 승인 후 무제한 자동 진행"이 **아니다**.
- Tier 0은 검증된 반복 패턴에 대한 **제한적 batch 실행 허용**이다.
- 신규성·불확실성·mutation·capability gap이 개입되면 **Tier 0 자격을 잃는다**.

---

## 4. Tier 0 Eligibility

Tier 0 허용 조건:

- **동일 app 안에서** 동일 screen-kind/action-pattern으로 3회 이상 4단 운영 패턴 PASS
- 앱 경계를 넘는 screen-kind 재사용은 **Tier 0 적용 금지** (별 결정 사안)
- 본 결정은 active corpus 정의(앱 단위)와 정합한다
- 앱 경계를 넘는 패턴 재사용 결정은 PR 6 anchor recommender 도입 후 별 결정으로 진행
- 같은 anchor 전략으로 PASS한 이력 필요
- 신규 capability 없음
- 신규 action 없음
- 신규 mutation 없음
- 신규 cleanup 없음
- unknown screen hash 없음
- unknown text/anchor 없음
- duplicate text/content-desc 없음
- unexpected delta 없음
- generated artifact policy 유지 가능
- coordinate fallback 필요 없음
- src/schema/runner 변경 필요 없음

명시:

- **"비슷해 보이는 패턴"은 Tier 0이 아니다.**
- 신규 surface 또는 신규 anchor 전략이 개입되면 Tier 0 적용 금지.
- Tier 0은 read-only 또는 검증된 반복 패턴에만 적용한다.

---

## 5. Tier 0 Sentinel

아래 조건 중 하나라도 나오면 **자동 진행을 즉시 중단**한다.

### 5-1. Sentinel 조건

- 신규 capability 필요
- 신규 action 필요
- unknown screen hash
- unknown text anchor
- duplicate text/content-desc
- cleanup 방식 불명확
- delta `insufficient` / `non_target_context`
- preflight unexpected WARN/FAIL
- runtime FAIL
- persistent state mutation
- 좌표 fallback 필요
- src/schema 변경 필요

### 5-2. Sentinel 발생 시 처리

- 현재 TC 즉시 중단
- 남은 batch 자동 진행 중단
- 4단 운영 패턴으로 복원
- sentinel 원인과 재개 조건 보고
- testdata에 억지 workaround 반영 금지

---

## 6. Batch Post-Review Requirement

Tier 0은 **검토 제거가 아니라 batch 사후 검토로 이동**하는 것이다.

Tier 0 batch 종료 시 반드시 보고:

- 실행한 TC 목록
- validate / lint / runtime 결과
- preflight / catalog / delta 변화
- 새 screen_id 여부
- anchor drift 여부
- cleanup 결과
- candidate file manifest
- commit 후보
- 사후 검토 필요 항목
- sentinel 미발생 확인

---

## 7. Tier Policy

### 7-1. Tier 0 — Read-only / validated repeated pattern

- scope 승인 1회
- draft → validate → lint → preflight → catalog → delta → runtime 자동
- batch commit 후보 등록
- batch 종료 후 종합 보고
- 예: app launch / tab navigation / known player open / search focus / known screen 재방문

### 7-2. Tier 1 — Reversible low mutation

- scope 승인
- draft / validate / lint / preflight 자동
- runtime 전 gate 1회
- cleanup clean이면 batch commit 후보
- 예: search query / force-stop cleanup으로 상태 회수 가능한 입력

### 7-3. Tier 2 — Persistent/high mutation

- scope gate
- draft report
- runtime gate
- commit gate
- push gate
- memory update
- 예: favorite add/remove / playlist create/delete / 설정 변경 / 권한 변경 / 계정·데이터 상태 변경

명시: **SMOKE_06 favorite add-remove cleanup은 Tier 2였고, 기존 방식이 맞았다.** v2에서도 동일 시나리오는 Tier 2로 분류되어야 한다.

---

## 8. Commit Policy

### 8-1. 기존

- 1 SMOKE = 1 commit

### 8-2. 개선

- **risk batch commit**

예:

- Commit A: Music SMOKE_01~05 read-only/low-risk baseline
- Commit B: Music SMOKE_06 persistent mutation (Tier 2 단독)

### 8-3. 계속 분리

- capability PR
- testdata commit
- generated artifact (영구 비커밋)
- memory/docs
- src/schema/runner 변경

### 8-4. Batch commit 전 필수

- candidate file manifest 보고
- allowed path whitelist 확인
- forbidden/generated path diff guard 확인
- generated/probe/catalog/reports 미포함 확인

---

## 9. Memory Policy

### 9-1. 기존

- SMOKE마다 memory update

### 9-2. 개선

- **batch push 후 1회 memory update**

### 9-3. 예외 (즉시 update)

- capability gap 발견
- persistent mutation failure
- manual cleanup required
- source-of-truth 변경
- operating policy 변경
- Tier/sentinel 정책 변경

---

## 10. Operating Trace Gaps to Anchor

v2 proposal 안에 다음 7건을 운영 추적 사각지대 anchor로 기록한다. 각 anchor는 다음 3단 형식으로 작성한다:

- **사실**: 어떤 단계에서 사전 보고/검토/의견/직시가 우회되었는지
- **영향**: 현재까지 *관측된* known impact (단정적 "0"이 아니라 "known impact 없음" 표현 사용)
- **사후 처리**: anchor 처리만 / 1줄 사실 보고 후 anchor / 별 PR로 처리 중 어느 것

**Residual risk acknowledgement** — 운영 추적 사각지대는 관측 부족을 전제로 하므로 "영향 0 확정"은 금지한다. 본 문서는 다음 입장을 채택한다:

- Current known structural defect: none identified.
- Current known impact: none confirmed.
- Residual risk remains: trace loss, delayed rationale recovery, and repeated reconstruction cost.
- Therefore these 7 items are anchored as baseline operating trace gaps before Tier automation expands.

### 10-1. alignment commit `7633272` 진입 경위

- 사실: alignment commit 진입이 4단 패턴 기준 사전 보고/검토 단계 없이 진행
- 영향: known impact 없음 (구조적 결함 미식별, 후속 PR sequence 정합성 관측됨)
- 사후 처리: anchor 처리만 (코드/문서 변경 동반 없음, 인지 정렬만 필요)

### 10-2. PR 2 preflight 코드 진입 경위

- 사실: preflight 도입 자체 검토는 있었으나 코드 진입 시점의 사전 보고가 4단 패턴 기준 미충족
- 영향: known impact 없음 (PR 2 머지 후 `de8b696` PR 2.1 정정으로 회수 관측, manual smoke 재실행 정상)
- 사후 처리: 1줄 사실 보고 후 anchor

### 10-3. PR 1 종료 보고 12항목 처리 (alignment commit 종료 보고 흡수 여부)

- 사실: alignment commit 종료 보고가 PR 1 종료 보고에 흡수됨 — 별도 종료 보고 미산출
- 영향: known impact 없음 (PR 1 sidecar/lint 동작 정상 관측, runtime 회귀 미관측)
- 사후 처리: anchor 처리만

### 10-4. PR 2.1 (preflight package lookup / permission status 정규화) 진입 경위

- 사실: PR 2 후속 정정(package lookup / permission status) 진입이 사전 scope proposal 없이 진행
- 영향: known impact 없음 (정정 결과로 `metadata.target_app.package` lookup + `permissions.parse_status="ok"` 정렬 관측, target_app 해석 회수)
- 사후 처리: anchor 처리만

### 10-5. PR 3 catalog 진입 경위 + write API 포함 사유

- 사실: 직전 합의는 read-only API 한정이었으나 PR 3에서 write API(`catalog build`) 포함 결정. 결정 시점 사전 보고/의견 단계 압축
- 영향: known impact 없음 (PR 4가 read-only invariant — sha256/mtime_ns/size pre/post 동일 — 실기 검증, 회귀 미관측)
- 사후 처리: 1줄 사실 보고 후 anchor (write API 포함 사유 보존 필요)

### 10-6. PR 4 catalog delta 진입 경위 + verdict 5종 분류

- 사실: verdict 5종(`insufficient` → `non_target_context` → `known_screen` → `changed_texts` → `new_screen`) 분류 결정이 본 sequence 5가지 failure 분류와 정합. 분류 결정 시점 의견 단계 압축
- 영향: known impact 없음 (verdict 분류 후 manual delta evidence 회수 정상 관측, `known_screen` round-trip 검증됨)
- 사후 처리: anchor 처리만

### 10-7. Music greenfield active corpus 확장 결정

- 사실: Gallery (`ODIN2 - My gallary/`) → MiniFile (`ODIN2 - minifile/`) → Music (`ODIN2 - Music/`) 확장 시 active corpus 정의(앱 단위) 확장이 별 결정 단계 없이 진행
- 영향: known impact 없음 (Music Phase 0~1F-Retry 모두 앱 단위 corpus로 정상 운영 관측, SMOKE_01~06 누적 112/112 PASS)
- 사후 처리: anchor 처리만 (본 v2 proposal §4 패치 1이 앱 단위 결정 형식 보존)

### 10-8. 목적 / 결정

- 목적: v2 도입 전 운영 추적 baseline 정리, Tier 자동화로 사각지대가 더 빠르게 누적되는 위험 차단
- 결정: 별도 운영 노트 파일을 새로 만들지 않는다. v2 proposal이 운영 노트 역할을 일부 흡수한다.

---

## 11. Adoption Order

```
1. v2 proposal 작성 + 운영 추적 사각지대 anchor    ← 본 문서
2. Git safe audit script
3. Synthetic delta measurement
4. Tier 정의 + Tier 0 조건 명문화
5. Batch commit 정책 적용
6. Anchor recommender
7. Capability prebook batch PR
```

이유:

- 운영 노트 없이 Tier부터 도입하면 사각지대가 가속됨 → §10 anchor 우선
- Tier 정의 전 synthetic delta / 동일 패턴 baseline이 필요함 → 측정 데이터로 Tier 0 조건 정량화
- anchor recommender는 효과가 크지만 PR 단위가 크므로 운영 기준 정리 후 진입

---

## 12. Automation Candidates

### 12-1. PR 6 후보 — Git safe push audit

- `tools/git_safe_push_audit.py`
- 검사 항목:
  - ahead/behind
  - HEAD..origin empty
  - staged/tracked dirty
  - forbidden/generated path guard
  - allowed path whitelist
  - candidate commit path whitelist
  - generated path diff guard
- 출력: JSON + markdown

### 12-2. PR 7 후보 — Synthetic delta measurement

- cold launch N회 반복
- xml_sha256 variability 측정
- visible_texts Jaccard 분포
- `known_screen`/`changed_texts` distribution
- delta `insufficient` / `non_target_context` 분류 기준 검증

### 12-3. PR 8 후보 — Anchor recommender

- stable text anchors 후보 추출
- content-desc-only controls 식별
- duplicate risk 평가
- mini-player false-positive risk 평가
- empty-state anchors 후보
- cleanup anchors 후보
- confidence high/medium/low 분류
- false suggestion feedback 루프

---

## 13. Non-goals

다음은 v2에서 **금지**한다:

- safety gate 전체 제거
- persistent mutation 자동 runtime
- generated artifact commit 허용
- coordinate fallback 허용
- selector DSL 대형화
- capability PR과 testdata PR 혼합
- Tier 0을 신규 패턴에 적용
- sentinel 발생 후 자동 우회
- "비슷해 보인다"는 이유로 Tier 0 확대 적용

---

## 14. Acceptance Criteria

본 문서가 아래 기준을 만족해야 한다:

- [ ] 다음 greenfield 앱에서 사용자 승인 횟수 50% 이상 절감 가능
- [ ] generated artifact strict separation 유지
- [ ] persistent mutation safety 유지
- [ ] capability gap은 계속 별도 PR
- [ ] memory update는 batch 단위
- [ ] sentinel 발생 시 4단 운영 패턴 복원
- [ ] batch 사후 보고로 검토 trace 보존
- [ ] Tier 0 적용 조건이 모호하지 않음 (앱 경계 단위 명시 포함)
- [ ] candidate file manifest로 batch commit rollback 리스크를 줄임
- [ ] 운영 추적 사각지대 7건 anchor가 문서 안에 포함됨

---

## Appendix A. Tier 분류 기준 요약

| 항목 | Tier 0 | Tier 1 | Tier 2 |
|---|---|---|---|
| mutation | 없음 | reversible (force-stop으로 회수) | persistent (in-app storage) |
| 신규성 | 없음 (3회 이상 PASS 이력) | 있을 수 있음 | 있음 |
| capability | 검증된 것만 | 검증된 것만 | 검증된 것만 (gap 시 별도 PR) |
| scope 승인 | 1회 | 1회 | 1회 |
| runtime gate | 자동 | 1회 | 1회 |
| commit | batch 후보 | batch 후보 (cleanup clean 시) | 단독 commit |
| memory update | batch 후 | batch 후 | 즉시 |
| 예시 | SMOKE_01~04 (재방문) | SMOKE_05 search query | SMOKE_06 favorite |

## Appendix B. Music SMOKE_01~06 Tier 분류 (소급 적용 시)

| TC | 실제 처리 | v2 Tier 분류 (소급) |
|---|---|---|
| SMOKE_01 app launch | 4단 패턴 | Tier 0 (재방문 시) |
| SMOKE_02 home tabs | 4단 패턴 | Tier 0 (재방문 시) |
| SMOKE_03 first-track player | 4단 패턴 | Tier 0 (재방문 시) |
| SMOKE_04 search focus | 4단 패턴 | Tier 1 (IME mutation, BACK으로 회수) |
| SMOKE_05 search query | 4단 패턴 | Tier 1 (query mutation, force-stop으로 회수) |
| SMOKE_06 favorite add/remove | 4단 패턴 | **Tier 2 (persistent mutation, 본래대로 4단 유지)** |

명시: 본 분류는 *Music v1.0.2604231952 + AT-M150 + 검증된 anchor 전략* 조합 한정. 같은 SMOKE라도 새 capability/surface/cleanup이 개입하면 Tier 자격 재평가 필요.

---

## Appendix C. Commit Scope (this proposal)

본 proposal 문서를 commit하는 시점에 적용되는 단독 범위:

### Commit candidate

- `docs/tc_runner_operating_policy_v2_proposal.md` (only)

### Excluded from this commit

- `docs/tc_template.yaml` (사전부터 untracked, 별도 결정)
- `docs/tc_writing_guide.md` (사전부터 untracked, 별도 결정)
- generated / probe / catalog / reports artifacts (영구 비커밋 정책)
- Music probe / catalog / report outputs (영구 비커밋 정책)

### Pre-commit verification

- staged file은 `docs/tc_runner_operating_policy_v2_proposal.md` 1개만 허용
- 기존 untracked `docs/tc_template.yaml` / `docs/tc_writing_guide.md`는 본 commit에 포함하지 않음
- src/schema/runner/tests 변경 0
- generated 산출물 staged 0
- ahead/behind 사전 audit 통과 (fast-forward only, force 금지)

### Adoption note

본 commit은 *proposal 문서를 repo에 고정하는 행위*에 한정한다. **policy v2 정책의 실제 운영 적용은 별도 결정**(승인 옵션 B)이며 본 commit과 분리된다.
