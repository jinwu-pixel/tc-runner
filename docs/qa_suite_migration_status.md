# qa-suite 마이그레이션 — 환경 재구성 핸드오프 + 완료 검증 런북

> 작성 2026-06-17 (tc-runner HEAD `6a02176`). 이 문서는 **원격 세션(tc-runner 커밋본만 보유)**
> 에서 실제 cross-repo 검증이 불가하여, **3 repo 가 공존하는 재구성 env / 로컬**에서 마이그레이션
> 완료 검증을 수행하기 위한 핸드오프다. 진행 시 이 문서를 SoT 로 삼고 §3 런북을 순서대로 실행한다.
>
> **§5 = 로컬 교차검증 결과 (2026-06-17 실행)** — §0~§4 는 원격 ultraplan 산출 원문, §5 는 로컬 3-repo
> env 에서 본 런북을 실제 실행한 검증 기록(추가분).

## 0. 왜 이 문서가 필요한가

이 원격 세션은 tc-runner 커밋본(895 files)만 보유하여 완료 검증이 **불가** — 두 가지 독립 사유:

- **Target 부재**: 형제 repo `qa-suite` + 권위 원장 `campaigns/manifests/provenance.csv` 가 컨테이너에 없음.
- **Source 불완전**: MIGRATION §4 인벤토리가 스캔한 로컬 working tree 의 다수 자산이 **미커밋(local-only)**
  이라 이 클론에 없음. 디스크 전수검사로 확정: `untracked 0 · ignored 0 · 삭제이력 0`
  (`git log --diff-filter=D` empty) → 부재 = "애초에 커밋된 적 없음".

```text
[원격 세션: tc-runner 커밋본만]            [재구성 env: tc-runner + thor2j + qa-suite]
  disk 전수검사 (§1) = 검증된 사실   ──→      이 문서 §3 런북을 순서대로 실행
        │                                          ▲
        └──── 커밋 → 새 env 에서 tc-runner 통해 가용 ┘
```

## 1. 재검증된 사실 (이 세션 disk 전수검사 — 커밋 상태가 아닌 실제 파일)

| 항목 | 확인값 |
|---|---|
| 커밋 자산 / untracked / ignored | 895 / 0 / 0 |
| 삭제 이력 (`git log --diff-filter=D`) | **0건** (자산 source-삭제 미착수) |
| 인벤토리 스캔 HEAD `1bca559` | 현 HEAD `6a02176` 의 ancestor (이후 4 커밋) |

**이주 진척 (커밋 기준)**: governance **4문서만** `source-deprecated` (commit `063caec`) —
`qa-suite/{ARCHITECTURE,MIGRATION,CLAUDE,analysis/CLAUDE}.md`. 자산 이주·삭제는 커밋 이력상 **0**.

**§4 인벤토리 중 이 클론에 부재 = local-only(미커밋), 원격서 검증 불가**:
`doc/`(589) · `stage1_output/` · `stage2_output/` · `tc1_converted/` ·
`ODIN2 - LTE DebugScreen BTS18596/` · `ODIN2 - WCDMA Reject BTS17126/` ·
root `HANDOFF_*.md` 3/6 (커밋된 것은 05-15·05-19·05-20) · `scratch/`(06-16 tooling) · `새 폴더 (2)/`.
→ 이 항목들은 **사용자 로컬 working tree 에만** 존재. 완료 검증은 로컬/재구성 env 필요.

**커밋본에서 확인된 블로커·불일치**:
- **PII (hard gate)**: `tc_samples/sample_call_test.yaml:14` 평문 `01012345678` (tracked).
  MIGRATION §4.2-2 redaction-lock — sanitize 전 tracked 이주 금지.
- **schema 3-ref**: `tc_step_schema.json` → `contracts/tc-step/` 이동 시 갱신 필요 3곳:
  `validate_tc.py:20` · `tests/test_lint_schema.py:5` · `tests/test_tc_loader.py:84`.
- **deprecation 불일치**: `qa-suite/automation/CLAUDE.md` 만 DEPRECATED 배너 없음
  (나머지 4 governance 문서엔 있음). 의도적 제외인지 누락인지 확인 필요.
- **§2.5 supersede 미적용**: 루트 `CLAUDE.md` 가 여전히 "cross-commit 금지"·thor2j 분기 유지
  (§8.2 06-12 row = `proposed`). 완료 시 supersede 필요(§2.1/§8.3 승인 게이트).

**병렬 작업(무간섭 대상)**: 미커밋 `CLAUDE.md`(§8.2 06-16 rows 3건) + `THOR2 - ALT Basic TC Audit/stage1_review_mapping_batch10/` YAML **35건**.

## 2. 환경 재구성 지침 (재시작 전)

- 새 Claude Code env 를 **tc-runner · thor2j-tc-appium · qa-suite 3개를 source 로** 구성한다.
  멀티-source 구성·source/trigger/session 개념: https://code.claude.com/docs/en/claude-code-on-the-web
- 대안: 3 repo 가 한 머신에 공존하면 **로컬에서** 동일 런북을 실행한다
  (완전한 working tree·local-only 자산 포함 — local-only 잔여 검증은 로컬에서만 가능).

## 3. 완료 검증 런북 (3 repo 공존 env 에서 순서 실행)

0. 형제 `qa-suite/campaigns/manifests/provenance.csv` 로드 → `status=verified` 행 집합 **V** 확정.
1. V 의 각 `target_path` 가 qa-suite 에 실재하고, `transform_note=verbatim` 인 행은
   `target_sha256 == source_sha256` 임을 확인 (무변환 이주 무결성).
2. V 의 각 `source_path` 를 tc-runner/thor2j 원본과 대조 → 누락·드리프트 검출.
3. tc-runner **로컬 전체 working tree**(local-only 포함)에서 §4 인벤토리 잔여 자산 − V
   = **"미이주 잔여" 목록** 산출 (특히 §1 의 local-only 항목들).
4. 블로커 게이트:
   - PII `sample_call_test.yaml` sanitize 전 이주 차단.
   - `tc_step_schema.json` 이동 시 3-ref(`validate_tc.py:20`·`tests/test_lint_schema.py:5`·`tests/test_tc_loader.py:84`) fixup.
   - thor2j 하드코딩 절대경로 3건(`tools/build_overview_ppt.py`·`tools/build_weekly_ai_deck_v2.py`·`tests/mmi_pipeline/cli/test_audit.py`) 수정.
   - ALT Basic 캠페인 크로스repo 참조(thor2j `runner/altbasic_validation_batch1~5.py` → tc-runner ALT Basic manifest CSV) 동반 이동(MIGRATION 규칙 1).
   - 패키지 개명: staging `automation/tests/` → `modules/`(import `tests.`→`modules.`, MIGRATION 규칙 6).
5. governance: `qa-suite/automation/CLAUDE.md` 배너 정합 · 루트 `CLAUDE.md §2.5` supersede(승인 게이트).
6. MIGRATION 규칙 2 최종: `verified` 자산만 원본 `source-deprecated` → 다음 정리 때 삭제.
   활성 캠페인(`THOR2 - ALT Basic TC Audit/`·`THOR2_K - Settings/`, thor2j `runner/tests/tools/docs`)은
   캠페인 종료 시점까지 이주 보류(규칙 1).

## 4. 참조

- 설계·인벤토리·규칙 SoT: 형제 repo `qa-suite/{ARCHITECTURE,MIGRATION,CLAUDE}.md`
  (이 repo 의 `qa-suite/*` 는 DEPRECATED staging 사본 — 편집 금지, 읽기 참고만).
- 이주 모델: `copy → verify → provenance 기록 → source-deprecated → 삭제` (MIGRATION 규칙 2).

---

## 5. 로컬 교차검증 결과 — 이 핸드오프 실행 (2026-06-17, tc-runner HEAD `6a02176`)

> §2 가 요구한 "3 repo 공존 env" = 사용자 로컬 머신. 형제 repo `qa-suite`·`thor2j-tc-appium`
> 둘 다 로컬 git repo 로 실재 확인 → 원격이 못 한 cross-repo 검증을 로컬에서 실행함.
> 검증은 전부 **read-only**. 자산 이주·삭제·커밋 0.

### 5.1 §0~§4 문서 주장 검증 — 확인 가능 전건 일치

| 주장 | 검증 방법 | 결과 |
|---|---|---|
| HEAD `6a02176` / 삭제이력 0 | `git log --diff-filter=D` | ✓ 0건 |
| 인벤토리 HEAD `1bca559` = ancestor +4 | `git merge-base --is-ancestor` / `rev-list --count` | ✓ ancestor, +4 |
| governance 4문서만 source-deprecated (`063caec`) | `git show --stat` | ✓ 4파일 각 +3줄, 자산 이주/삭제 0 |
| PII `sample_call_test.yaml:14` 평문 | grep | ✓ `01012345678` |
| schema 3-ref (`validate_tc:20`·`test_lint_schema:5`·`test_tc_loader:84`) | grep | ✓ 3곳 일치 |
| §2.5 cross-commit 미supersede (proposed) | `CLAUDE.md` L110 + §8.2 06-12 | ✓ "cross-commit 금지" 잔존, row=`proposed` |
| `automation/CLAUDE.md`만 DEPRECATED 배너 없음 | deprecat grep (5 문서) | ✓ 0 vs 2/2/6/2 |
| local-only 자산 클론 부재 | disk 존재 vs `git ls-files`/`check-ignore` | ✓ doc/·scratch/·ODIN2 2종=untracked, stage1/2_output·tc1_converted=**gitignored** (전부 tracked=0) |
| thor2j 하드코딩 절대경로 3건 | grep (3 파일) | ✓ 파일별 1 hit |
| altbasic runner1~5 ↔ tc-runner manifest 참조 | grep docstring | ✓ 각 runner가 `VALIDATION_MANIFEST_BATCHn` read-only 참조 명시 |
| qa-suite provenance.csv 권위원장 + SoT 3문서 | ls / 행 집계 | ✓ 84행(verified 72·copied 8·source-deprecated 4), ARCHITECTURE/MIGRATION/CLAUDE 실재 |

### 5.2 adversarial 보강 (문서가 안 짚은 누락 위험 — 직접 확인)

- **PII 전수**: tracked 평문 휴대폰 패턴 매치 **8건 = 전부 동일 더미 `01012345678`**(순차 1~8, 실 고객정보 아님).
  분포 = 플래그된 `sample_call_test.yaml` 1 / 테스트 픽스처 3(`test_excel_converter`·`test_mmi_compiler`×2) /
  플랜문서 `docs/superpowers/plans/2026-04-02-tc-runner.md` 2 / `qa-suite/MIGRATION.md`가 게이트를 *설명*하는 2.
  → **추가 실PII 없음.** 문서의 단일 파일 플래그가 이주-데이터 타겟으로 정확. 단 redaction-lock 은 보수적 게이트라
  더미여도 sanitize 전 tracked 이주 차단 유효(심각도 LOW). **주의**: 테스트 픽스처 3건도 동일 더미 보유 — 해당
  테스트 이주 시 함께 검토.
- **이미 끝난 이주분 무결성 (verified 72)**: `target_missing 0` · `source_missing 0` ·
  **sha256 72/72 sound** (71 raw 일치 + 1 = `contracts/tc-step/tc_step_schema.json` 은 ledger 가 git-blob/LF
  정규화 sha 기록 → LF 정규화 시 recorded == qa-suite target == tc-runner source, 셋 다 byte-identical 확인).
  → qa-suite 로 간 코드 슬라이스 **드리프트·손상 0**, 원본 미삭제(소스측 무손상).

### 5.3 판정 — GREEN (게이트 유지)

**현재 = 안전한 중간 단계**: qa-suite 가 검증된 72 자산 수령(무결), tc-runner 소스 삭제 0, governance 4건만 배너.
**파괴적 동작 아직 0.**

- **(A) 핸드오프 문서 저장/커밋** — 비파괴, 안전. 단일 파일 stage 라 정책 클린. 커밋은 명시 승인 필요(글로벌 정책).
- **(B) 실제 이주 실행(§3)** — §3 은 *검증* 런북이지 bulk-move 아님. 실 source-deprecation/삭제(규칙 2/6)는
  다음 게이트 뒤로 유지: PII sanitize · schema 3-ref fixup · thor2j 절대경로 3 · altbasic runner 동반이동(규칙1) ·
  §2.5 supersede(§8.3 승인) · **gitignored 3종(stage1/2_output·tc1_converted)은 클론 안 따라옴 → 별도 복사 필요**.

**병렬 작업 격리 확인**: 미커밋 `CLAUDE.md`(§8.2) + batch10 35 YAML(ALT Basic prep) + ODIN2 tele engineer(타 터미널)
무간섭. 단일 파일 커밋으로 격리 가능.

**durability 플래그**: qa-suite sibling repo 는 **remote 미설정·push 0** — 로컬 커밋해도 거긴 로컬뿐. 이주 영속성은
추후 remote 확보에 의존.

### 5.4 검증 환경

- 실행 머신: 사용자 로컬 (win32), 3 repo 형제 폴더 공존
  (`C:\Users\momen\Projects\{tc-runner,qa-suite,thor2j-tc-appium}`).
- 도구: `git` (ancestry·diff-filter·ls-files·check-ignore) · `grep` · `python` sha256 (provenance 전수 대조).
- 미실행(다음 게이트): §3 런북 3~6(미이주 잔여 산출·블로커 fixup·source-deprecation), `copied` 8행 검증,
  local-only 자산 대 V 차집합.
