# CLAUDE.md §8.4 archive 정책 실 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLAUDE.md §8.4 archive 정책을 1줄 placeholder에서 정식 정책 본문으로 교체하고, 운영 stub 파일 `docs/claudemd_section8_archive.md`를 신설한다.

**Architecture:** 단순 docs cycle 2 files — (1) 신 stub 파일 작성 (5 lines), (2) CLAUDE.md §8.4 본문 교체 (2 lines → ~20 lines). 즉시 archive motion 없음 (§8.2 = 2 rows ≪ 50). 정책 활성화 + 인프라 stub만 lock.

**Tech Stack:** Markdown only. 코드·런타임·tests 무관. 검증은 정적 (grep / line count / cross-reference).

**Spec:** `docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md` (9점 결정 매트릭스 lock)

---

## File Structure

| 변경 | 경로 | 책임 |
|---|---|---|
| Create | `docs/claudemd_section8_archive.md` | §8.2에서 archive된 누적 교훈 단일 누적 파일 (시간 순 append-only). 본 cycle에서는 헤더만 (0 archive event) |
| Modify | `CLAUDE.md` (§8.4, lines 444–445) | placeholder 1줄 → 정식 정책 본문 ~20 lines |

§8.4 외 다른 §8 sub-section (§8.1/§8.2/§8.3/§8.5) 변경 없음. §1~§7 변경 없음.

---

## Task 1: archive stub 파일 신설

**Files:**
- Create: `docs/claudemd_section8_archive.md`

- [ ] **Step 1: 파일 신설**

Write `docs/claudemd_section8_archive.md` (절대경로: `C:\Users\momen\Projects\tc-runner\docs\claudemd_section8_archive.md`) with exactly this content:

```markdown
# CLAUDE.md §8.2 Archive

`CLAUDE.md` §8.4 archive 정책에 의해 §8.2에서 이동된 누적 교훈.
스키마는 §8.2 본문과 동일. 시간 순 append-only (수정·삭제 없음).

<!-- archive event 없음. 첫 발동 시 ## YYYY-MM-DD archive 추가 -->
```

- [ ] **Step 2: 파일 존재·내용 검증**

Run (PowerShell):

```powershell
Get-Item C:\Users\momen\Projects\tc-runner\docs\claudemd_section8_archive.md | Select-Object FullName, Length
Get-Content C:\Users\momen\Projects\tc-runner\docs\claudemd_section8_archive.md
```

Expected:
- FullName: `C:\Users\momen\Projects\tc-runner\docs\claudemd_section8_archive.md`
- Length > 0
- 내용 = 위 5 lines (마지막 줄 HTML comment 포함)

---

## Task 2: CLAUDE.md §8.4 본문 교체

**Files:**
- Modify: `CLAUDE.md` (lines 444–445, §8.4 sub-section만)

- [ ] **Step 1: 현 §8.4 위치 재확인**

Read `CLAUDE.md` lines 440–448, confirm 현 §8.4 block:

```
### 8.4 archive 정책
§8.2 항목 50개 초과 시 별도 archive 파일로 이동 (구현 시점 결정).
```

- [ ] **Step 2: Edit 수행**

Edit `CLAUDE.md` (절대경로: `C:\Users\momen\Projects\tc-runner\CLAUDE.md`):

- old_string (정확히 2 lines):

```
### 8.4 archive 정책
§8.2 항목 50개 초과 시 별도 archive 파일로 이동 (구현 시점 결정).
```

- new_string (정확히 18 lines):

```
### 8.4 archive 정책

§8.2 row 수가 50을 초과하면 archive 발동 후보. 자동 수행 없음 — Claude는 도달 사실만 보고하고, 사용자 명시 승인 후 발동 (§2.1·§8.3 정합).

**archive 대상**:
- 가장 오래된 completed row (`applied` / `rejected` / `superseded`) 25개
- 동일 날짜 multi-row 시 §8.2 본문 등장 순서 유지 (stable order)
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
```

- [ ] **Step 3: 교체 후 §8.4 grep 검증**

Run (Grep tool):
- pattern: `^### 8\.4 archive 정책`
- path: `CLAUDE.md`
- output_mode: `content`
- `-n`: true

Expected: 1 match line 444 (또는 인접). §8.4 시작 line 확인.

Run (Grep tool):
- pattern: `^### 8\.5 개선 훅`
- path: `CLAUDE.md`
- output_mode: `content`
- `-n`: true

Expected: 1 match. §8.5 시작 line이 §8.4 신 본문 다음 위치 (≈ 444+20 = 464 부근).

§8.4 본문이 위 new_string과 일치하는지 read로 cross-check (lines 444–464 부근).

---

## Task 3: 정합 cross-check + 사용자 batch commit 승인 요청

**Files:**
- Read-only: `CLAUDE.md`, `docs/claudemd_section8_archive.md`

- [ ] **Step 1: cross-reference 정합 확인**

Run (Grep tool) — §2.1 / §8.3 reference 점검:
- pattern: `§2\.1` / `§8\.3`
- path: `CLAUDE.md`
- output_mode: `content`
- `-n`: true

Expected: 신 §8.4 본문에 §2.1 / §8.3 모두 명시 (line 444+2 부근, line 444+19 부근). §2.1 본문 자체는 lines 32–46 부근, §8.3 본문은 lines 436–442 부근 — 변경 없음 확인.

- [ ] **Step 2: archive 파일 schema vs §8.2 schema 일치 검증**

Run (Read tool) — §8.2 본문 column header read:
- `CLAUDE.md` lines 429–433 부근

Expected (§8.2 header):
```
| 날짜 | 영역 | 근거 사례 | 반영 섹션 | 상태 |
|---|---|---|---|---|
```

archive stub 파일에는 본 cycle에서 table column 표기 없음 (헤더 + 안내문 + comment만). 첫 발동 시점에 §8.2 schema 그대로 복사할 수 있도록 stub 안내문이 "스키마는 §8.2 본문과 동일" 명시함을 read로 확인.

- [ ] **Step 3: line count delta 측정**

Run (PowerShell):

```powershell
(Get-Content C:\Users\momen\Projects\tc-runner\CLAUDE.md | Measure-Object -Line).Lines
(Get-Content C:\Users\momen\Projects\tc-runner\docs\claudemd_section8_archive.md | Measure-Object -Line).Lines
```

Expected:
- CLAUDE.md: 직전 449 lines → ~467 lines (delta = +18, 신 §8.4 17 lines + 빈 줄 1 = +18; tolerance ±2)
- archive stub: ~5 lines

- [ ] **Step 4: git status 확인 (예상 외 파일 없음)**

Run (Bash):

```bash
git status --short -- CLAUDE.md docs/claudemd_section8_archive.md docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md
```

Expected (정확히 4 entries):
```
 M CLAUDE.md
?? docs/claudemd_section8_archive.md
?? docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md
?? docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md
```

다른 파일이 같이 modified/staged로 나오면 본 cycle 범위 외 — 사용자에게 즉시 보고하고 commit 보류.

- [ ] **Step 5: 사용자에게 batch commit 승인 요청 (보고 형식 §7)**

사용자에게 다음 정보 제공 후 명시 승인 대기:

1. **Changed files** (4건):
   - Modified: `CLAUDE.md` (§8.4 lines 444–445 교체, +18 lines)
   - Created: `docs/claudemd_section8_archive.md` (5 lines)
   - Created: `docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md` (spec)
   - Created: `docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md` (본 plan)
2. **Staged files** (commit 직전 명시 path stage 예정, broad add 없음):
   ```
   git add CLAUDE.md docs/claudemd_section8_archive.md docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md
   ```
3. **제안 commit message**:
   ```
   docs: lock CLAUDE.md §8.4 archive policy + add stub

   §8.4 archive 정책 (rows>50 trigger, oldest 25 completed,
   single-file append-only, user approval gate) lock + 운영 stub
   docs/claudemd_section8_archive.md 신설 (0 archive event).
   현재 §8.2 = 2 rows이므로 즉시 archive motion 없음.

   spec: docs/superpowers/specs/2026-05-21-claudemd-archive-policy-design.md
   plan: docs/superpowers/plans/2026-05-21-claudemd-archive-policy.md

   Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
   ```
4. **tests / checks 결과**: docs-only cycle, runtime tests 무관. 정합 cross-check Step 1~4 PASS 확인 보고.
5. **Non-goals 준수 점검**: §8.4 외 §8 sub-section 변경 0, §1~§7 변경 0, §8.2 기존 row 정리 0, archive 자동 감지 hook 0.
6. **final `git status`**: commit 후 별도 read-only 호출로 보고.

승인 어휘 = "지금 commit" / "commit now" / "batch commit 진행" 중 명시 1건. 모호 응답 = commit 진행 금지, 재확인.

---

## 후속 작업 (본 plan 범위 외)

- §8.2가 50 rows 초과까지 자연 누적 (예측 불가, 학습 cycle 반복 시 수년 단위 가능)
- 첫 archive 발동 시 본 정책 실효성 검증 — 동일 날짜 multi-row stable order 케이스 / partial exception 케이스 등 운영 사례 §8.2에 1줄 row로 누적
- archive 파일 자체의 분량 가드 (§8.4가 archive 파일을 또 archive 하지 않음 — 분량 부담 무관 정책 결정 #4 lock)

---

## Self-review 결과

**1. Spec coverage:**
- 결정 #1 (rows > 50 trigger) → Task 2 Step 2 new_string 본문에 명시
- 결정 #2 (oldest 25 completed) → Task 2 Step 2 new_string "**archive 대상**"
- 결정 #3 (completed 정의) → Task 2 Step 2 new_string "completed row (`applied` / `rejected` / `superseded`)"
- 결정 #4 (단일 누적 archive 파일) → Task 1 신설 + Task 2 new_string "**archive 파일**"
- 결정 #5 (archive event row 1개만 본문 표기) → Task 2 Step 2 new_string "**archive 후 §8.2**"
- 결정 #6 (보고 → 사용자 명시 승인 후 발동) → Task 2 Step 2 new_string "**§2.1·§8.3 정합**" 절
- 결정 #7 (동일 날짜 multi-archive heading `#N` / `THHMM`) → 본 cycle stub은 0 event이므로 §8.4 본문에는 미수록, spec에만 lock. 첫 archive 발동 시 적용 — Acceptable (placeholder 아님, 운영 시점 결정 사항)
- 결정 #8 (partial exception path) → Task 2 Step 2 new_string "**예외 — completed row < 25**" 절
- 결정 #9 (stable order) → Task 2 Step 2 new_string "동일 날짜 multi-row 시 §8.2 본문 등장 순서 유지 (stable order)"

→ 모든 결정 9건 cover. 갭 0.

**2. Placeholder scan:** "TBD" / "TODO" / "later" / "appropriate error handling" / "similar to Task N" — 본 plan 내 0건.

**3. Type consistency:**
- schema column 5개: 날짜 / 영역 / 근거 사례 / 반영 섹션 / 상태 → §8.2 본문, archive stub 안내문, 신 §8.4 본문 event row 예시 모두 일관
- archive 파일 경로: `docs/claudemd_section8_archive.md` → Task 1 + Task 2 + Task 3 모두 동일
- archive event row 표현: 정상 = `archive | oldest 25 rows moved`, partial = `archive (partial) | oldest M completed rows moved (partial exception)` → spec·plan 일관

→ 정합 OK. fix 0.
