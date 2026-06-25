# QA NOTES — batch10 F0 validation manifest (2026-06-25)

무단말·무커밋. `VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`(236 queued) 의 adversarial QA 결과 + 정정 이력.

## 검증 다층 (전부 무단말)

| gate | 방법 | 결과 |
|---|---|---|
| set-diff | batch10 tc_id − union(기존 manifest) | 271 = already 35 + queued **236** + review 0 |
| tc_id collision | `scratch/altbasic_tcid_collision_check.py` | cross 0 · internal 0 |
| STAGE1 canonical | `scratch/stage1_canonical_check.py` | **271/271 PASS** (validate_tc.py 는 compiled-TC 용·부적용) |
| header/구조 | byte-identical(BOM) · 18-col · 236 unique | PASS |
| provenance(결정적) | verifier literal ⊂ source YAML · selector 발명 | **236/236 grounded · 0 invented** |
| QA fan-out(에이전트) | 11 chunk × adversarial(H1 grounding/H2 selector/H3 appropriateness/H4 consistency) | **HIGH 0 · MED 3 · LOW 3** (아래) |

QA fan-out: 11/11 chunk 보고, 236 rows audited. **HIGH(발명/미근거) 0** — 결정적 provenance 와 일치.

## MED/LOW 6건 — 원인·정정

5건은 generator `entry_detail` 결손(첫 2 step 한정 + target 40자 truncation 으로 후속 네비 step·gesture
qualifier 누락 → 운영자 under-execute·false FAIL). 1건은 verifier 적합성(verify_text 오분류).

| tc_id | sev | 축 | 문제 | 정정 |
|---|---|---|---|---|
| HDK_019 | med | H4 | entry_detail 이 long-press('길게') 누락 — 짧게 누르면 퀵패널 미개방 | **RESOLVED** — raw_text 전 step 반영("홈 버튼을 길게 누른다") |
| SET_610 | med | H4 | entry_detail 이 step3 '추가 옵션 Tap' 누락 — 언어 리스트 literal 은 그 화면에서만 노출 | **RESOLVED** — step3 포함 |
| LCH_146 | low | H4 | step3 '화면 최하단에서 하방향키' 누락 — 앱서랍 트리거 미도달 | **RESOLVED** — step3 포함 |
| CAL_354 | low | H4 | step3 'up>right'(더보기 아이콘) 분기 누락 | **RESOLVED** — step3 포함 |
| PFW_015 | low | H4 | raw 'Press right'(>'  focus) 40자 truncation 으로 잘림 | **RESOLVED** — cap 120, 전체 포함 |
| BSC_124 | med | H3 | verifier literal('Select box'/'Dropdown list')이 precondition/위젯명 재서술 — 실제 outcome(첫 항목 **포커스 해제**)은 verify_text 로 비관측 | **T1 재분류로 RESOLVED**(verify_text→focus_state/focus_absent, 2026-06-25) |

정정 방법: `scratch/gen_batch10_manifest.py` `entry_detail()` 를 전 step·raw_text 기반으로 교체 후
manifest 재생성. 재검증: header byte-identical 유지 · provenance 236/236 grounded(0 invented) 유지 ·
5건 entry_detail 에 누락 step/gesture 복원 확인.

## BSC_124 — 운영자 CAVEAT + STAGE1 follow-up

- **현상**: TC 의도 = 드롭다운 열람 중 돌아가기 하드키 → **첫 항목 포커스 해제**. `expected_result_raw`=
  "...포커스된 첫번째 항목이 포커스가 사라진다". 그러나 `verifier_type=verify_text`, literal=
  'Select box'/'Dropdown list'(위젯/precondition 라벨) — 동작 전·후 모두 노출되어 outcome 미관측.
- **device 운영 CAVEAT**: literal 노출 여부로 판정하지 말 것. dump 에서 **첫 항목의 `focused=true`
  속성이 back 입력 후 사라지는지**(focus_absence)를 관찰. literal 'Select box'/'Dropdown list' 은
  컨텍스트 확인용에 한정.
- **STAGE1 정정 — DONE(2026-06-25 승인 후 T1)**: BSC_124 `verifier_type: verify_text → focus_state` +
  `verifier_contract.assert: focus_absent`(WARN35 패턴) 적용 완료. expectation="포커스된 첫번째 항목이
  포커스가 사라진다"(expected_result_raw substring·발명 0), device_value PENDING_F0. manifest 의 BSC_124 행
  = `[focus_absent] …`. 위 CAVEAT 는 device run 시 focus_absent 관찰 절차로 그대로 유효.

## BSC_120 · BSC_121 — focus_retained 2축 가드 (단독 승격 금지)

- **잔존 false-PASS 위험**: 의도 outcome 은 **2축** — ① 드롭다운(더보기) 메뉴 목록 **닫힘(부재)** + ② 더보기
  focused **유지**. T1 재분류는 `focus_retained`(②)로 닫았으나, 계약상 단일 assert 라 ①(드롭다운 닫힘)은
  assert 로 직접 관측 안 됨 → 더보기 focused 인 채 드롭다운이 열려 있어도 ②만 PASS 하는 구멍.
- **가드(문서 보강, 2026-06-25)**: handoff §3 에 "**BSC_120/121 = ①·② 둘 다 확인, 둘 중 하나만으로 승격 금지**"
  명시. F0 dump 에서 드롭다운 메뉴 목록 노드 **부재** + 더보기 focused 유지 동시 확인. ② 단독 만족 =
  `VERIFIER_FAILED`/verifier-gap NOTE.
- **scope**: 본 보강은 **문서만**(handoff/QA_NOTES). yaml `verifier_contract` 무수정(단일 assert 유지).
  필요 시 후속 슬라이스에서 `method` 필드에 ①②  이중 채록 절차 명문화 가능(free-text, 단일 assert 보존) — 별도 결정.

## 비고

- entry_detail 정정은 **236행 전체**에 적용(5 flagged 외에도 다단계 네비 TC 의 step 완전성 향상).
- BSC_124 외 H3(verifier 적합성) 신규 지적 없음 — 나머지 235행 verifier 는 관측 가능 outcome.
- 본 QA·정정 전부 무단말·무커밋. manifest/handoff/본 노트 = commit-candidate(미커밋). generator·check 도구 = `scratch/`(local-only·미스테이지).

## verifier 분류 스윕 (BSC_124 일반화, read-only 2026-06-25)

BSC_124(verify_text 오분류) 일반화 — batch10 queued 236 중 **verify_text 인데 outcome 이 focus/state 변화**인
케이스 스윕(expected_result_raw/title 의 focus-change 의미). **56건 후보** → literal 이 변화를 담는지로 2-tier triage.

**전제(WARN35 scope)**: WARN35(2026-06-16)는 **literal-부재** focus TC 35건만 verify_text→focus_state 전환. 본 56건은
전부 **literal 보유** → WARN35 의도적 제외분. ∴ literal 이 focus **목적지 이름**이면 약하지만 유효(결함 아님).

| tier | 판정 | tc_id |
|---|---|---|
| **T1 — 재분류 후보 (literal 이 outcome 미포착)** 7 | literal=정적 컨텍스트/generic 지시자 → verify_text 부적합 | BSC_120·BSC_121(literal '더보기'=유지되는 아이콘, outcome=드롭다운 **닫힘**) · BSC_124(focus 해제) · HDK_035·036·037·038(literal '초점 포인트'=generic, outcome=방향 이동) |
| **T2 — note only (재분류 안 함)** ~49 | literal=focus **목적지 요소명**(약하나 유효 proxy) 또는 boundary/무반응. WARN35-scope tradeoff | 나머지(BSC_072·CAL_293/327/328/356/357·CLK_005/017·CNT_065~079·HDK_041/064·LCH_017~030/154/160/161·MGN_005/006·MSG_073~082·PDM_041~044·PFW_022·QPN_130/168/176·RAD_017·CAM_131 등) |

- **T1(7건) — 적용 완료(2026-06-25 승인 후)**: STAGE1 `verifier_type: verify_text → focus_state` +
  `verifier_contract.assert`(BSC_120·121 focus_retained / BSC_124 focus_absent / HDK_035~038 focus_move) 재분류.
  WARN35 패턴(`scratch/t1_focus_state_transform.py`, local-only) · expectation=expected_result_raw substring(발명 0) ·
  device_value PENDING_F0 · focus_model 미부여(=node default, R2 device-gate 시 확정). manifest 재생성 후 전 게이트
  재통과(row **236 불변** · collision 0 · STAGE1 271/271 · provenance 0-invented · header byte-identical). **무커밋**.
- **T2(~49)**: 재분류 **안 함**(WARN35 의도). 단 **Part B device 가이드**: run1 에서 literal 노출뿐 아니라 가능 시
  **목적지 요소의 focused-state** 채록 권장(literal 존재 ≠ focused). handoff §3 캡처 절차에 보강 권고.
- 56건 전체 raw 스윕은 read-only(편집 0). T1 재분류는 승인 후 별도 슬라이스.
