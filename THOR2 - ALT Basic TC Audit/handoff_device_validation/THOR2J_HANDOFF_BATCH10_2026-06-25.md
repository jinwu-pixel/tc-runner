# THOR2J HANDOFF — ALT Basic batch10 KEEP_CONFIRMED F0 검증 큐 (2026-06-25)

**무단말 작성 (정적). 실 F0 실행은 별도 승인 후.** commit/push/단말 호출 금지 상태에서 작성된 계약.

batch10 = REVIEW_MAPPING 재판정(2026-06-15) **KEEP_CONFIRMED 271** STAGE1 합성 풀. 이 중 focus_state 35건은
이미 `VALIDATION_MANIFEST_BATCH11_2026-06-16.csv`(64=batch11 29 + WARN35 35)에 큐잉됨. 본 핸드오프는 **나머지
236건(set-diff)** 을 F0 2-run 검증 큐로 묶는다. **229건 `verify_text`**(네비게이션 후 화면 literal 노출 확인)
+ **7건 `focus_state`**(T1 재분류 2026-06-25 — §3·§11·QA_NOTES). selector/literal/assert 발명 0 — literal/
expectation 은 source 기반, device_value 는 **PENDING_F0**(run1 실측 확정).

- **manifest (read-only)**: `VALIDATION_MANIFEST_BATCH10_2026-06-25.csv` (**236건**, 기존 18-col byte-identical)
- **set-diff 산출**: batch10 KEEP_CONFIRMED **271** − already-manifested(focus_state) **35** = **newly-queued 236** (excluded-for-review **0**)
- **분포**: safety_class = NAVIGATION_ONLY 213 + READ_ONLY 23. verifier_type = **verify_text 229 + focus_state 7**(T1 재분류). risk_rank R1 236/236.
- **STAGE1 상태**: 전건 `export_status: STAGE1_DRAFT` · `evidence_level: STATIC_ONLY` · `validation_required: device_2run_green` (미승격)
- **source 도구(local-only, 미스테이지)**: `scratch/gen_batch10_manifest.py`(파생·idempotent), `scratch/stage1_canonical_check.py`(정적 게이트)
- **runner**: thor2j-tc-appium — **실행은 thor2j 영역(§2.5 cross-commit 금지)**. 본 문서는 계약·절차만.

## 1. 단말 / 실행 규약

| 항목 | 계약 |
|---|---|
| 단말 | **F0 `B06201249E0002F0` 고정** (build RY07260601S, ko-KR). **B27 `B2700125BW000083` 미접촉**, ODIN2 미접촉 |
| wrong-device 가드 | 실행 직전 `adb -s B06201249E0002F0 get-state`로 serial 고정 확인. tc-runner `src/adb.py` 핀은 암묵 → thor2j runner 의 UDID 상수(`altbasic_validation_batch1.py: UDID`) 재사용. serial 불일치 시 **즉시 중단** |
| run | 모든 TC **run1 / run2 독립 실행**. 상호 상태 비공유 |
| 승격 | **TWO_RUN_GREEN(run1=SINGLE_RUN_PASS ∧ run2=RUN2_PASS)만 RUNNABLE_NOW**. 단일 run PASS = 미승격 |
| 결과 어휘 | `SINGLE_RUN_PASS`/`RUN2_PASS` · `ENTRY_FAILED` · `VERIFIER_FAILED` · `CLEANUP_FAILED`(즉시 보고) · `DEVICE_FIT_SKIP`(FAIL 아님) · `LITERAL_PENDING`(아래 §3) · `INFRA_FAILURE` |
| run 순서 | manifest 행 순서(rank R1 → sheet → tc_id). sheet 클러스터(§5 sub-batch) 단위 진행 권장 |

## 2. verify_text 모델 스펙 (핵심)

batch10 큐는 **focus 모델(R1/R2)이 아니다** — 네비게이션 후 **화면에 기대 literal 이 노출되는지**를 본다.

- 각 행 `verifier_candidates` = `literal: A / B / C` (source 기대 텍스트). 다수 literal 은 **모두** 노출되어야 PASS.
- literal 은 **source paraphrase(`confidence:0.5`)** — 단말 실제 표기와 띄어쓰기/조사/축약이 다를 수 있음.
  - run1: dump/스크린샷에서 **실제 노출 literal 채록** → 기대 literal 과 의미 일치 확인 → 정확 literal 로 **PENDING_F0 확정**(§4 backfill).
  - 의미는 맞으나 표기가 다르면 `LITERAL_PENDING`(FAIL 아님) 으로 기록하고 정확 literal 환류. **발명 금지**.
- 진입(`entry_method: app_launch_unresolved`)은 패키지/컴포넌트 미확정 — run1 에서 진입 경로(런처→앱→메뉴) 확정 후 환류.
- **★ 7건은 `focus_state`**(BSC_120·121 focus_retained · BSC_124 focus_absent · HDK_035~038 focus_move — T1 재분류). literal 노출이 아니라 `verifier_contract.assert`/`method`(focused=true 요소 dump 대조)로 검증 — manifest `verifier_candidates`=`[assert] expectation`, `verifier_caveat`=focus_state 절차. WARN35/R2 focus 모델과 동일 취급(§3).

## 3. 캡처 절차

1. precondition 세팅(간편/일반 모드 등 manifest `precondition` 열).
2. entry: manifest `entry_detail`(navigate/press_key 절차)로 대상 화면 진입.
3. dump = `uiautomator dump` 또는 Appium source.
4. 기대 literal 집합(`verifier_candidates`)의 화면 노출 여부 대조. 전부 present = PASS 후보.
5. literal 표기 차이/부분 노출은 `LITERAL_PENDING` + 실측 literal 채록(발명 금지). 진입 실패는 `ENTRY_FAILED`.
6. cleanup(manifest `cleanup` 열, 보통 `HOME 복귀`/`Back`) 후 다음 TC.

**focus_state 7건(`verifier_candidates`=`[assert] …`)**: literal 대조 대신 `verifier_caveat` 절차 — 입력 전/후 `focused=true` 요소(resource-id·bounds) dump 채록 → assert(move/retained/absent) 대조. device_value PENDING_F0 환류.

**★ BSC_120 · BSC_121 (focus_retained) — 단독 승격 금지**: 의도된 outcome 은 **2축**이다 — ① 드롭다운(더보기) 메뉴 목록 **닫힘(부재)** + ② 더보기 아이콘 **focused 유지**. `focus_retained` assert(② focused 유지)만으로는 ①(드롭다운 닫힘)을 관측하지 못해 **false-PASS 구멍**이 남는다(더보기 focused 인 채 드롭다운이 열려 있어도 ②는 PASS). 따라서 F0 run 시 **①·② 둘 다 확인**해야 PASS — dump 에서 드롭다운 메뉴 목록 노드 **부재** + 더보기 focused 유지. **둘 중 하나만으로 `RUNNABLE_NOW` 승격 금지**(②만 만족 시 `VERIFIER_FAILED` 또는 verifier-gap/NOTE 보고).

**★ focus-to-destination verify_text (T2, literal=focus 목적지 요소명, ~49건)**: literal 존재만으로 focus 이동을 단정하지 말 것.
> For focus-to-destination cases, record literal visibility plus focused-state when the device surface exposes it.
> If focused-state evidence contradicts the literal verifier, do not promote on literal visibility alone; report as verifier-gap / NOTE for review.

(즉 T2는 STAGE1 재분류 안 함 — device run 에서 literal-only PASS 가 focus 반증을 덮지 못하게 차단. 상세 = `QA_NOTES_BATCH10_2026-06-25.md`.)

## 4. device_value / literal backfill 포맷

run1 후 STAGE1 yaml 환류(별도 무단말 보정 — 본 round 아님):
```
entry_resolved:   <런처→앱→메뉴 확정 경로 / 패키지·컴포넌트>
literal_confirmed: [ <실측 literal 1>, <실측 literal 2>, ... ]   # 기대와 의미 일치, 정확 표기
verify_status:    PASS | LITERAL_PENDING(표기차) | NOT_PRESENT
```

## 5. device sub-batch 분할 (11 chunk, sheet-aware ~30/창)

큐 236을 1 device-창 단위(~15–32)로 분할 — 큰 sheet(Quick panel 44·Launcher 36)는 분할. **권장 그룹(조정 가능)**:

| chunk | n | sheets |
|---|---|---|
| C01 | 13 | 1.Basic principle |
| C02 | 29 | 11.Hard Key |
| C03 | 32 | 14.Quick panel (part) |
| C04 | 12 | 14.Quick panel (part) |
| C05 | 15 | 17.Safety Feature · 2.Touch lock · 23.Settings |
| C06 | 32 | 24.Launcher (part) |
| C07 | 4 | 24.Launcher (part) |
| C08 | 27 | 25.Call · 26.Message |
| C09 | 19 | 27.Contacts |
| C10 | 32 | 28.Camera · 29.Clock · 30.Voice Recorder · 31.Radio |
| C11 | 21 | 5.Magnifying glasses · 6.Pedometer · 8.Picture Frame widget · 9.Simple settings |

## 6. ★ ELEVATED-CAUTION — modal/위험 컨트롤 호출 TC (절대 confirm 금지)

아래 18건은 네비게이션 중 **전원끄기/재시작/긴급전화/SOS/삭제/발신** 모달·항목에 도달한다. 전부 **노출(라벨)
확인만** 이며, 각 yaml `risk_note` 에 위험 항목 **실행 금지**가 명시됨. F0 운영자는 이 항목들에서 **어떤 위험
버튼도 탭/OK/confirm 하지 말 것** — 노출 확인 후 즉시 **Back/취소로 모달 원복**.

- 전원/재시작 창: `BSC_025`, `HDK_052`, `HDK_053`, `HDK_054`, `QPN_011`, `QPN_141`, `QPN_175`
- 긴급전화/SOS: `HDK_102`, `QPN_012`, `SFT_054`, `SST_016`
- 삭제/휴지통 항목: `CAL_341`, `LCH_153`, `LCH_154`, `MSG_075`
- 다이얼러 발신: `CAL_355`, `CAL_356`, `CAL_357`

(각 행 manifest `risk` 열에 per-TC risk_note 보존 — 운영자 필독.)

## 7. mutation 0 / 안전 (denylist — 항구)

- 전건 NAVIGATION_ONLY/READ_ONLY (네비게이션 + dump + Back/HOME). 설정변경/토글/항목 삭제·이동·실행 **0**.
- §6 elevated-caution: 위험 모달은 **Back/취소로만** 이탈.
- 위험 tap denylist(batch11/R2 재사용): `켜기`/`사용 설정`/`시작`/`전송`/`연결`/`확인`(영속)·`저장`·`삭제`·`전원 끄기`·`다시 시작`·`SOS`·다이얼러 발신·`am start` 직접 기동.
- 실행 전/후 `pm list packages` pre/post diff 0. 종료 시 `io.appium.*` helper uninstall(잔존 0).

## 8. redaction

- READ_ONLY/NAVIGATION verify_text 는 화면 **노출 literal** 만 필요. Call/Message/Contacts sheet(manifest `redaction=CHECK` 46건)는 dump 의 기존 PII(연락처/메시지/통화) 부수 채록 가능 → redaction gate 후 sidecar 만, raw/png local-only.
- 기타 sheet `redaction=not_required`.

## 9. §2.5 경계

- 본 문서 + manifest CSV + STAGE1 yaml = **tc-runner side(계약·자산)**.
- 실행 코드(entry resolver·literal 대조·dump 파서) = **thor2j-tc-appium side(구현)**. cross-commit 금지.

## 10. 산출 / 보고

- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_2026MMDD/run{1,2}/{tc_id}/` (xml+png, local-only)
- 결과 CSV: `evidence/.../results_run{1,2}.csv`
- 회수 리포트: tc-runner `RESULT_RECOVERY_BATCH10_*.md` (RUNNABLE / LITERAL_PENDING / ENTRY_FAILED 분리)
- literal/entry 확정분은 run1 후 STAGE1 yaml 환류(§4) — 별도 무단말 보정.

## 11. 정적 검증 (실행 전 통과 — 2026-06-25, 무단말·무커밋)

- set-diff: 271 KEEP_CONFIRMED = already 35 + newly-queued **236** + review 0 (check sum OK)
- tc_id collision gate: cross-batch 0 · internal 0 (`scratch/altbasic_tcid_collision_check.py`)
- STAGE1 canonical static check: **271/271 PASS** (`scratch/stage1_canonical_check.py`) — *주의: 컴파일 TC용 `validate_tc.py` 는 STAGE1 draft 에 부적용(audit_meta 미처리)*
- manifest 구조: 18-col, header **byte-identical** to 기존 manifest(BOM 포함), 236 unique tc_id, 행별 컬럼수 정합
- provenance: verifier literal 236/236 **source YAML grounded**, 발명 selector 0 (round-trip 검사)
- QA fan-out(11 chunk 에이전트 adversarial 감사, 236 rows): **HIGH 0** · MED 3 · LOW 3 → entry_detail 5건 **RESOLVED**(generator 정정·재생성), BSC_124 **T1 재분류로 RESOLVED**. 상세 = `QA_NOTES_BATCH10_2026-06-25.md`
- **T1 verifier 재분류(2026-06-25, 승인 후)**: verify_text→focus_state **7건**(BSC_120·121 focus_retained · BSC_124 focus_absent · HDK_035~038 focus_move) — WARN35 패턴, expectation=expected_result_raw substring(발명 0), device_value PENDING_F0. manifest 재생성 후 전 게이트 재통과(row **236 불변** · collision 0 · STAGE1 **271/271** · provenance 0-invented · header byte-identical). **T2 ~49건 yaml 무수정**(§3 device 가이드로 대응). 도구 `scratch/t1_focus_state_transform.py`(local-only)
- **commit/push/단말 호출 금지** (HEAD ≠ origin/master: ODIN2 ahead 1 — ALT commit 금지 상태)
