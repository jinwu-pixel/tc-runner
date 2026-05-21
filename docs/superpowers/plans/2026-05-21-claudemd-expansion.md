# CLAUDE.md Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace tc-runner `CLAUDE.md` with the 8-section expanded version, and create `docs/tc_patterns.md` for device/SIM/viewport-specific patterns, per spec `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md`.

**Architecture:** Documentation-only change. Single-file replacement (`CLAUDE.md`) + single new file (`docs/tc_patterns.md`). Two-phase validation — pre-flight reality check (does spec content match repo state?) then post-write cross-reference validation (do all §X.Y / file path references resolve?). Commit deferred to single batch per global commit policy.

**Tech Stack:** Markdown only. Validation via `grep` / `ls`. No build / test framework.

**Spec source:** `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md` — contains complete CLAUDE.md and `docs/tc_patterns.md` drafts. Tasks below reference spec sections rather than duplicate ~400 lines.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `CLAUDE.md` | Replace | Project instructions for Claude Code sessions (§1~§8) |
| `docs/tc_patterns.md` | Create | Device/app-specific TC patterns (split from §3.4) |
| `docs/CLAUDE.md.bak.2026-05-21.md` | Create | Backup of pre-change CLAUDE.md (recovery aid; git history is canonical) |
| `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md` | Reference only | Spec — source of content |
| `~/.claude/projects/.../memory/MEMORY.md` | Reference only | Confirm device naming priority etc. — read only |

---

## Task 1: Pre-flight reality check (spec ↔ repo drift)

**Why:** Spec was written 2026-05-21. Between spec write and plan execute, repo state may drift. Verify all file paths / tool names / status claims in spec still match reality. Catches issues before they get baked into CLAUDE.md.

**Files:**
- Read: `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md`
- Read (verify exist): paths listed below

- [ ] **Step 1: Verify §5.1 core scripts exist**

Run:
```bash
ls validate_tc.py gen_excel.py gen_yaml_tc_report.py gen_app_tc_report.py update_tcs.py
```
Expected: all 5 files listed, no "No such file".

- [ ] **Step 2: Verify §5.2 runner modules exist**

Run:
```bash
ls src/cli.py src/tc_loader.py src/ui_parser.py src/action_runner.py src/adb.py src/preflight.py src/reporter.py src/excel_converter.py src/catalog.py src/catalog_delta.py src/app_explorer.py
```
Expected: all listed.

- [ ] **Step 3: Verify §5.3 scripts exist**

Run:
```bash
ls scripts/apn_reboot_loop.py scripts/data_popup_repro_loop.py scripts/qc_ap_log_capture.py scripts/setup_preset.py scripts/lgu_consent_diag.py scripts/setup_gallery_media.py scripts/reset_gallery_media.py scripts/gen_gallery_photos.py
```
Expected: all listed.

- [ ] **Step 4: Verify §5.4 tools exist**

Run:
```bash
ls tools/git_safe_push_audit.py tools/synthetic_delta_measure.py
```
Expected: both listed.

- [ ] **Step 5: Verify §5.5 bat files exist**

Run:
```bash
ls BUG5426_APN_Monitor.bat BUG5426_APN_Monitor_py.bat QC_AP_Log_Capture.bat BUG_DataPopup_Monitor.bat doc/apply_apns_conf.bat doc/verify_apns_conf.bat doc/rollback_apns_conf.bat
```
Expected: all listed.

- [ ] **Step 6: Verify §5.6 구현됨 paths exist**

Run:
```bash
ls -d reports/lint reports/preflight reports/screenshots reports/catalog_delta output logs logs_apn "output/QC_AP log" 2>&1
ls reports/*_report.html | head -3
```
Expected: all dirs exist, at least one `*_report.html` exists.

- [ ] **Step 7: Verify §5.6 planned `reports/<run_id>/` is still planned (not implemented)**

Run:
```bash
ls reports/ | grep -E '^[0-9]{8}T[0-9]{6}Z?$' | head -5
```
Expected: empty (no `<run_id>/` subdirs at top level of reports/). If non-empty — that directory exists and §5.6 needs status update.

- [ ] **Step 8: Verify §3.1 STAGE prompt files exist**

Run:
```bash
ls tc_prompts/STAGE1_NORMALIZE.md tc_prompts/STAGE2_COMPILE.md tc_prompts/OPERATIONAL_RULES.md tc_prompts/device_profile.yaml tc_prompts/runner_capability.yaml
ls -d golden_tc_set/
```
Expected: all listed.

- [ ] **Step 9: Verify §7.1 global policy source exists**

Run:
```bash
ls ~/.claude/CLAUDE.md
```
Expected: file exists.

- [ ] **Step 10: Verify §2.5 thor2j-tc-appium repo path exists**

Run:
```bash
ls -d /c/Users/momen/Projects/thor2j-tc-appium 2>&1
```
Expected: directory exists. If missing — §2.5 needs adjustment (use "별도 repo (분기 시점에 등록)" wording).

- [ ] **Step 11: Drift report**

If any of Steps 1-10 produced unexpected output:
- Stop. Do not proceed to Task 2.
- Report exact discrepancy to user.
- Update spec inline (or get user direction on adjustment).
- Re-run drift check.

If all clean: proceed.

---

## Task 2: Backup current CLAUDE.md

**Why:** Git history is canonical, but a sibling backup file is faster to diff during early review. Low cost (one copy), high recovery value.

**Files:**
- Read: `CLAUDE.md`
- Create: `docs/CLAUDE.md.bak.2026-05-21.md`

- [ ] **Step 1: Copy current CLAUDE.md to backup path**

Run:
```bash
cp CLAUDE.md docs/CLAUDE.md.bak.2026-05-21.md
```
Expected: silent success.

- [ ] **Step 2: Verify backup matches original**

Run:
```bash
diff CLAUDE.md docs/CLAUDE.md.bak.2026-05-21.md
```
Expected: empty output (files identical).

- [ ] **Step 3: Verify backup has frontmatter / header indicating it is a backup**

The backup is a verbatim copy. No header injection needed — the filename `CLAUDE.md.bak.2026-05-21.md` self-documents. If user later prefers an inline header, add it then.

---

## Task 3: Write new CLAUDE.md (full replacement)

**Why:** Core deliverable. Content source is spec §"본문 draft" → "CLAUDE.md" subsection (the section between the ` ```` markdown` fences). Write exactly what's in spec, no improvisation.

**Files:**
- Modify (full replace): `CLAUDE.md`
- Reference: `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md`

- [ ] **Step 1: Open spec and locate `## 본문 draft` → `### CLAUDE.md` section**

Read `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md`. Find the section starting with `### CLAUDE.md` followed by ` ```` markdown` fence. The content between that fence and its closing ` ```` ` is the full new CLAUDE.md body.

- [ ] **Step 2: Overwrite CLAUDE.md with spec content**

Use the Write tool with `file_path = C:\Users\momen\Projects\tc-runner\CLAUDE.md` and `content = <exact body extracted in Step 1>`.

Do not modify, reorder, or "improve" the content. The spec is the contract.

- [ ] **Step 3: Verify file written**

Run:
```bash
wc -l CLAUDE.md
head -5 CLAUDE.md
```
Expected: ~280-360 lines (spec body); first line begins `## 1. Project Vision`.

- [ ] **Step 4: Spot-check section headers present**

Run:
```bash
grep -n "^## " CLAUDE.md
```
Expected: 8 section headers (`## 1.` through `## 8.`).

- [ ] **Step 5: Spot-check key required content**

Run:
```bash
grep -nE "(validate PASS|runtime PASS|manual evidence observed|BUG-GAP observed)" CLAUDE.md | head -10
grep -nE "(SUSPECT|OBSERVED|CONFIRMED|SPEC_GAP)" CLAUDE.md | head -10
grep -nE "(OPEN|IN_PROGRESS|RESOLVED|WONTFIX)" CLAUDE.md | head -10
grep -n "thor2j-tc-appium" CLAUDE.md
grep -n "docs/tc_patterns.md" CLAUDE.md
grep -n "BUG-25796" CLAUDE.md
grep -n "BTS18697" CLAUDE.md
```
Expected:
- PASS 4종: all 4 strings present
- 진단 결론 어휘: all 4 present
- 이슈 lifecycle 어휘: all 4 present
- `thor2j-tc-appium`: at least 1 hit
- `docs/tc_patterns.md`: at least 1 hit (in §3.4 link)
- `BUG-25796`: at least 1 hit (in §4.6)
- `BTS18697`: at least 1 hit (in §4.6)

---

## Task 4: Write docs/tc_patterns.md (new file)

**Why:** Spec §3.4 splits device/SIM/viewport specifics out of CLAUDE.md. CLAUDE.md §3.4 references this file by path — file must exist before §3.4 reference resolves.

**Files:**
- Create: `docs/tc_patterns.md`
- Reference: `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md` (the `### docs/tc_patterns.md` block)

- [ ] **Step 1: Locate spec content for tc_patterns.md**

Read spec. Find `### docs/tc_patterns.md` heading inside `## 본문 draft`. Content between its ` ```` markdown` fence and the closing fence is the full body.

- [ ] **Step 2: Write docs/tc_patterns.md**

Use Write tool with `file_path = C:\Users\momen\Projects\tc-runner\docs\tc_patterns.md` and the exact content from Step 1.

- [ ] **Step 3: Verify file exists**

Run:
```bash
ls -la docs/tc_patterns.md
wc -l docs/tc_patterns.md
head -3 docs/tc_patterns.md
```
Expected: file present, ~50-80 lines, first line begins `# TC Patterns`.

- [ ] **Step 4: Spot-check sections present**

Run:
```bash
grep -n "^## " docs/tc_patterns.md
```
Expected: 7 sections (`## 1.` through `## 7.`).

- [ ] **Step 5: Spot-check key content**

Run:
```bash
grep -n "스타일폴더 2 (AT-M140" docs/tc_patterns.md
grep -n "com.android.phone/.settings.DebugScreen" docs/tc_patterns.md
grep -n "boot_id" docs/tc_patterns.md
```
Expected: all 3 hits present.

---

## Task 5: Cross-reference & link validation

**Why:** CLAUDE.md uses many `§X.Y` references and external file paths. Any broken cross-ref means readers (Claude or human) hit dead ends. Validate before user review.

**Files:**
- Read: `CLAUDE.md`, `docs/tc_patterns.md`

- [ ] **Step 1: Find every §X.Y reference in CLAUDE.md and verify the section exists**

Run:
```bash
grep -oE "§[0-9]+\.[0-9]+" CLAUDE.md | sort -u
```
Expected: list of all `§X.Y` references. For each one, verify `^### X.Y ` heading exists:
```bash
grep -nE "^### [0-9]+\.[0-9]+ " CLAUDE.md
```
Cross-check the reference list against the actual subsection list. Every reference must have a matching subsection. Standalone `§N` (whole-section refs) also valid — confirm `## N.` heading exists.

- [ ] **Step 2: Find every file path mentioned in CLAUDE.md and verify it exists**

Run:
```bash
grep -oE '`[a-zA-Z_/\.\-]+\.(py|md|yaml|bat|json|html)`' CLAUDE.md | sort -u
```
For each path, verify existence:
```bash
ls <path>
```
Skip paths under `~/.claude/` (verified in Task 1 Step 9) and the special-cased `thor2j-tc-appium` external repo path. Backtick-wrapped placeholder paths (e.g., `<run_id>`, `<단말명> - <앱명>`) are pattern templates — skip.

Any miss = stop, fix CLAUDE.md or revisit Task 1 drift check.

- [ ] **Step 3: Verify the §3.4 → docs/tc_patterns.md link points to an existing file**

Run:
```bash
grep -n "docs/tc_patterns.md" CLAUDE.md
ls docs/tc_patterns.md
```
Expected: link is present in CLAUDE.md §3.4, target file exists.

- [ ] **Step 4: Verify §7.1 source path resolves**

Run:
```bash
grep -n '~/.claude/CLAUDE.md' CLAUDE.md
ls ~/.claude/CLAUDE.md
```
Expected: reference in §7.1, target file exists.

- [ ] **Step 5: Verify no leftover "TBD" / "TODO" / placeholder markers**

Run:
```bash
grep -nE "(TBD|TODO|FIXME|XXX|\\[TODO\\]|\\[\\?\\])" CLAUDE.md docs/tc_patterns.md
```
Expected: empty output. Any hit = remove or replace with concrete content.

- [ ] **Step 6: Verify markdown table formatting**

Run:
```bash
grep -cE "^\|" CLAUDE.md
grep -cE "^\|" docs/tc_patterns.md
```
Expected: both > 0 (multiple table rows). Visually scan CLAUDE.md for any obviously malformed tables (broken alignment, missing separator row).

---

## Task 6: User review checkpoint

**Why:** Per global commit policy and brainstorming-skill convention, user must approve substantive doc changes before they're committed.

**Files:** None (this is a manual checkpoint).

- [ ] **Step 1: Notify user that draft is in place**

Report to user:
- `CLAUDE.md` replaced (backup at `docs/CLAUDE.md.bak.2026-05-21.md`)
- `docs/tc_patterns.md` created
- Validation Tasks 1 and 5 passed
- Awaiting user review before batch commit

- [ ] **Step 2: Wait for user feedback**

Possible user responses:
- **approve** → proceed to Task 7
- **변경 요청: [내용]** → make targeted edits, re-run Task 5 validation, return here
- **rollback** → restore from `docs/CLAUDE.md.bak.2026-05-21.md`, delete `docs/tc_patterns.md`, halt

Do not proceed to commit without explicit "approve" (or equivalent "commit now").

---

## Task 7: Batch commit (only after explicit user approval)

**Why:** Global commit policy (`~/.claude/CLAUDE.md`) defers commits to daily batch. User explicit "commit now" or batch-end is the trigger.

**Files:** All changed.

- [ ] **Step 1: Pre-commit status check**

Run:
```bash
git status --short
git diff --name-only
git diff --name-only --cached
```
Expected: see `CLAUDE.md` (modified), `docs/CLAUDE.md.bak.2026-05-21.md` (untracked), `docs/tc_patterns.md` (untracked), `docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md` (untracked), `docs/superpowers/plans/2026-05-21-claudemd-expansion.md` (untracked).

If you see unexpected files in this list — STOP, report to user, do not commit (global policy: 예상 외 파일이 보이면 즉시 중단).

- [ ] **Step 2: Stage explicit paths only**

Run:
```bash
git add CLAUDE.md docs/CLAUDE.md.bak.2026-05-21.md docs/tc_patterns.md docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md docs/superpowers/plans/2026-05-21-claudemd-expansion.md
```
NEVER use `git add .` or `git add -A` or `git add docs/` (broad add forbidden).

- [ ] **Step 3: Verify staging matches intent**

Run:
```bash
git diff --name-only --cached
```
Expected: exactly the 5 paths from Step 2. No more, no less.

- [ ] **Step 4: Commit**

Run:
```bash
git commit -m "docs(claudemd): rewrite CLAUDE.md to 8-section structure, add docs/tc_patterns.md

- §1 Vision · §2 Core Principles · §3 TC Pipeline · §4 Diagnosis & Repro
- §5 Tools & Evidence · §6 단말×앱 컨벤션 · §7 Git Policy · §8 Continuous Improvement
- Split device/SIM/viewport specifics to docs/tc_patterns.md
- BUG_LOG.md vocab split: 진단 상태 (§4.4) vs 이슈 상태 (§6.3)
- Spec: docs/superpowers/specs/2026-05-21-claudemd-expansion-design.md
- Plan: docs/superpowers/plans/2026-05-21-claudemd-expansion.md

Pre-change CLAUDE.md preserved at docs/CLAUDE.md.bak.2026-05-21.md"
```

- [ ] **Step 5: Post-commit verification**

Run:
```bash
git log -1 --stat
git status --short
```
Expected: latest commit shows the 5 staged files. `git status --short` shows clean tree (modulo other untracked files unrelated to this change).

- [ ] **Step 6: Do NOT push**

Push is a separate explicit action per global policy. End plan here.

---

## Spec Coverage Self-Review

| Spec requirement | Task coverage |
|---|---|
| 단일 CLAUDE.md 전면 재작성 | Task 3 |
| `docs/tc_patterns.md` 신설 | Task 4 |
| 13건 결정 매트릭스 반영 | Task 3 (CLAUDE.md content) + Task 4 (tc_patterns content) — content drawn verbatim from spec |
| 보강 후보 10건 1:1 매핑 | Task 5 Step 5 spot-checks key strings |
| Non-goal: BUG_LOG.md 일괄 마이그레이션 | Excluded — no migration task |
| Non-goal: `reports/<run_id>/` 구조화 실제 구현 | Excluded — no implementation task |
| Risk: §6.3 어휘 변경 운영 충격 | CLAUDE.md §6.3 itself contains incremental migration note (no separate task needed) |
| Risk: §5.6 status drift | Task 1 Step 6-7 verifies |
| Risk: 사례 reference stale | Out of scope for this plan — caught by §8 trigger going forward |
| 글로벌 commit policy 준수 (batch · 명시 path · broad add 금지) | Task 7 Steps 1-3 enforce |

No gaps. No placeholders ("TBD"/"TODO") in plan body. Type/name consistency N/A (no code).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-21-claudemd-expansion.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
