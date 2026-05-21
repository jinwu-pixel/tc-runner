# CLAUDE.md §8.4 archive 정책 설계 — tc-runner (2026-05-21)

## 문서 정체성

- 대상 repo: **tc-runner** (`C:\Users\momen\Projects\tc-runner`)
- 대상 섹션: `CLAUDE.md` §8.2 누적 교훈 목록 + §8.4 archive 정책
- 산출물: `CLAUDE.md` §8.4 본문 교체 + `docs/claudemd_section8_archive.md` stub 신설
- 청자: Claude Code 세션 자동 load (사람 onboarding 가능)

## 배경

직전 cycle (2026-05-21 CLAUDE.md 8-section 전면 재작성, HEAD `e1c1c15`) 종료 시점에 §8.4는 placeholder 1줄로 lock:

```
### 8.4 archive 정책
§8.2 항목 50개 초과 시 별도 archive 파일로 이동 (구현 시점 결정).
```

현재 §8.2는 2 rows (`applied` × 2). 실 발동 임박은 아니나 정책 자체가 미정의 — trigger 발동 시 운영 모호. 본 cycle은 정책 lock + stub 인프라까지 활성화한다.

## 결정 매트릭스 (8점 lock)

| # | 항목 | 결정 | 비고 |
|---|---|---|---|
| 1 | trigger 임계 | rows 기준 (§8.2 row 수 > 50) | lines 기준 / 시간 기준 거부 |
| 2 | 이동 단위 | 가장 오래된 completed row 25개 | oldest-N hybrid |
| 3 | completed 정의 | `applied` / `rejected` / `superseded` | `proposed` 본문 잔류 |
| 4 | archive 파일 | 단일 누적 `docs/claudemd_section8_archive.md` | 시간 순 append-only |
| 5 | 본문 표기 | archive event row 1개를 §8.2에 신규 추가 | 안내문·counter 없음 |
| 6 | 발동 메커니즘 | trigger 도달 보고 → 사용자 명시 승인 후 발동 | §2.1·§8.3 정합 |
| 7 | 동일 날짜 다중 archive | `## YYYY-MM-DD archive #N` 또는 `## YYYY-MM-DDTHHMM archive` 허용 | heading 중복 회피 |
| 8 | completed row < 25 예외 | 자동 partial archive 금지. Claude 예외 보고 → 사용자 결정 ((a) wait / (b) partial M rows / (c) skip). partial 시 event row = `archive (partial)` / `oldest M completed rows moved (partial exception)` | 정상 발동 차단 + partial path 문구 lock |
| 9 | 동일 날짜 multi-row 정렬 | 날짜 오름차순 + 동일 날짜는 §8.2 본문 등장 순서 유지 (stable order) | day-granularity 비결정성 회피 |

## 운영 사이클

```
[세션 시작 / §8.2 갱신 직후]
   ↓
§8.2 row count 체크
   ↓
   ├─ ≤ 50 → 아무 행동 없음
   │
   └─ > 50 → completed row (applied/rejected/superseded) 수 점검
              │
              ├─ completed ≥ 25 → Claude 보고:
              │      "§8.2 rows = N (> 50). archive 발동 후보 (oldest 25 completed). 승인 필요"
              │      ↓
              │   사용자 명시 승인
              │      ↓
              │   archive 수행 (아래 5 step)
              │
              └─ completed < 25 → Claude 예외 보고:
                     "§8.2 rows = N (> 50)이나 completed row = M (< 25).
                      자동 partial archive 금지. 사용자 결정 필요."
                     ↓
                  사용자 선택지 (Claude 자체 판단 금지):
                    (a) wait (proposed → completed 전환 후 재발동)
                    (b) partial (이번에만 M rows 이동)
                    (c) skip (본 cycle archive 안 함)
                     ↓
                  사용자 명시 결정 후 진행
```

### archive 5 step (정상 발동 시)

1. §8.2에서 completed row 추출 → 날짜 오름차순 정렬 (동일 날짜는 §8.2 본문 등장 순서 유지 — stable order) → 가장 오래된 25개 선정
2. `docs/claudemd_section8_archive.md` 끝에 새 archive event heading + 25 rows append
3. §8.2 본문에서 해당 25 rows 제거
4. §8.2에 archive event 신규 row 1개 추가
   ```
   | YYYY-MM-DD | archive | oldest 25 rows moved | §8.4 | applied |
   ```
5. batch commit 대상 (글로벌 정책 §7 — 사용자 명시 승인 시점에 합류)

### partial 발동 (예외) 변형

step 1~5 동일, 다음 세 곳만 차이:

- step 1: 가장 오래된 25개 → **가장 오래된 M개 (M = 사용자 승인 시점의 completed row 수, M < 25) 선정** (stable order 동일)
- step 2: archive event heading 동일 (`## YYYY-MM-DD archive[ #N]`), table에 M rows append
- step 4: §8.2 추가 row 문구 변경
  ```
  | YYYY-MM-DD | archive (partial) | oldest M completed rows moved (partial exception) | §8.4 | applied |
  ```

## archive 파일 schema

파일: `docs/claudemd_section8_archive.md`

### 형식 (전체)

```markdown
# CLAUDE.md §8.2 Archive

`CLAUDE.md` §8.4 archive 정책에 의해 §8.2에서 이동된 누적 교훈.
스키마는 §8.2 본문과 동일. 시간 순 append-only (수정·삭제 없음).

## 2026-MM-DD archive

| 날짜 | 영역 | 근거 사례 | 반영 섹션 | 상태 |
|---|---|---|---|---|
| ... | ... | ... | ... | applied |
| (25 rows) | | | | |

## 2026-MM-DD archive #2

| 날짜 | 영역 | 근거 사례 | 반영 섹션 | 상태 |
|---|---|---|---|---|
| ... | ... | ... | ... | superseded |
| (25 rows) | | | | |
```

### 규칙

- 본문 = 헤더 1개 + 0..N archive event block
- archive event block = `## YYYY-MM-DD archive[ #N]` heading + 25-row table
- 같은 날짜 2회 이상 발생 시 `#2`, `#3` 또는 `## YYYY-MM-DDTHHMM archive` 형식 허용 (스타일 자유, 단조 증가)
- append-only — 기존 block 수정·삭제 금지
- archive 파일 자체는 CLAUDE.md auto-load 대상 아님 (분량 부담 무관)

### stub 초기 상태 (본 cycle 산출)

```markdown
# CLAUDE.md §8.2 Archive

`CLAUDE.md` §8.4 archive 정책에 의해 §8.2에서 이동된 누적 교훈.
스키마는 §8.2 본문과 동일. 시간 순 append-only (수정·삭제 없음).

<!-- archive event 없음. 첫 발동 시 ## YYYY-MM-DD archive 추가 -->
```

## CLAUDE.md §8.4 신 본문 proposal

현 (1줄 placeholder, 교체 대상):
```
### 8.4 archive 정책
§8.2 항목 50개 초과 시 별도 archive 파일로 이동 (구현 시점 결정).
```

→ 신:
````
### 8.4 archive 정책

§8.2 row 수가 50을 초과하면 archive 발동 후보. 자동 수행 없음 — Claude는 도달 사실만 보고하고, 사용자 명시 승인 후 발동 (§2.1·§8.3 정합).

**archive 대상**:
- 가장 오래된 completed row (`applied` / `rejected` / `superseded`) 25개
- `proposed` row는 archive 안 함 (본문 잔류)

**예외 — completed row < 25**:
- 자동 partial archive 금지
- Claude는 예외 보고: 사용자가 (a) wait / (b) partial / (c) skip 결정
- partial 승인 시: M rows (M < 25) 이동, event row = `YYYY-MM-DD | archive (partial) | oldest M completed rows moved (partial exception) | §8.4 | applied`

**archive 파일**: `docs/claudemd_section8_archive.md` (단일 누적, 시간 순 append-only, schema는 §8.2와 동일)

**archive 후 §8.2**:
- 해당 25 rows 본문 제거
- archive event 자체를 §8.2의 새 row로 1줄 추가 (`날짜 | archive | oldest 25 rows moved | §8.4 | applied`)
- 별도 안내문·counter 없음

**§2.1·§8.3 정합**: archive는 본문 갱신이므로 사용자 승인 게이트 필수. 자체 판단 archive 금지.
````

## 본 cycle 산출

| 산출 | 위치 | 비고 |
|---|---|---|
| Design spec | `docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md` | 본 문서 |
| Plan | `docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md` | 다음 단계 |
| 실 구현 1 | `CLAUDE.md` §8.4 본문 교체 (1 줄 → 위 proposal) | plan 실행 단계 |
| 실 구현 2 | `docs/claudemd_section8_archive.md` stub 신설 (헤더만, 0 archive event) | plan 실행 단계 |

**즉시 archive 발동 없음**: 현재 §8.2 = 2 rows (≪ 50). 본 cycle은 정책 lock + 인프라 stub만 활성화.

## Non-goals

- §8.2 기존 row 정리·재분류 (현재 2 rows 그대로 유지)
- archive 파일 형식의 자동 검증 도구·CI gate (수동 운영)
- archive trigger 도달 자동 감지 hook (Claude가 세션 시작/§8.2 갱신 직후 row count 직접 확인하는 패턴 — 별도 자동화 도입 안 함)
- §8.4 외 다른 §8 sub-section 변경 (§8.1/§8.2/§8.3/§8.5 본문 그대로 유지)
- lines 기준 trigger·시간 기준 rolling archive (axis 거부됨)

## 검증 절차 (실 구현 단계)

1. **GATE 1 (작성)**: 본 spec → plan → CLAUDE.md §8.4 본문 교체 + stub 파일 작성
2. **GATE 2 (정합 확인)**:
   - `CLAUDE.md` lines 변화 측정 (§8.4 +N lines)
   - §8.4 본문에서 §2.1·§8.3 cross-reference 정합
   - stub 파일 frontmatter·스키마 §8.2와 동일성 점검
3. **GATE 3 (수동 PASS)**: 사용자 spec/plan/diff 리뷰 후 승인
4. **GATE 4 (commit)**: 글로벌 정책 §7 따라 사용자 명시 승인 시점 batch commit

## 위험·완화

| 위험 | 완화 |
|---|---|
| 사용자가 발동 승인 후 Claude가 stale `§8.2`를 archive (race) | archive 직전 §8.2 read 재확인, 25개 row 정확히 매칭 |
| `proposed` row가 잘못 `applied` 표기되어 archive | status 어휘 4종 lock (§8.2 본문), archive 시 status 컬럼 검증 |
| stub 파일이 commit되지 않은 채 §8.4 본문만 갱신 | 본 cycle 산출 2건 (CLAUDE.md + stub)을 same commit batch에 묶음 |
| heading `## YYYY-MM-DD archive` 충돌 (동일 날짜 2회) | 결정 #7 — `#N` 또는 `THHMM` 표기 허용 |
| `> 50`인데 completed row < 25 | 결정 #8 — 자동 partial 금지, 사용자 결정 |

## 본 cycle 메타

- 사용 스킬: `brainstorming` → (본 spec) → `writing-plans` (다음 단계)
- 결정 매트릭스 6점 + 미세 보강 2건 = 8점 lock
- 모든 결정 사용자 명시 선택, Claude 자체 판단 0
