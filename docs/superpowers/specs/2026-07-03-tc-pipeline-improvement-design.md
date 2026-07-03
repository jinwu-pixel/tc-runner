# TC 파이프라인 개선 설계 (STAGE1/STAGE2 지시문 + prep 게이트)

- 작성일: 2026-07-03
- 입력: `THOR2 - ALT Basic TC Audit/FAILURE_TAXONOMY_2026-07-03.md` (12 category, CONFIRMED 8 / ADJUSTED 4)
- 대상: `tc_prompts/STAGE1_NORMALIZE.md` (v1.0.0), `tc_prompts/STAGE2_COMPILE.md` (v1.1.0), prep 도구·게이트, CLAUDE.md
- 성격: **설계 잠금 (§2.1 승인 대기)**. 본 문서는 분석·설계만 — tc_prompts·코드 수정 0. 반영은 항목별 승인 후.
- 스코프 원칙: 모든 제안은 **모델 불문 지시문 규칙**이다. Fable 최적화(over-fitting) 아님 — 산출물은 sonnet 실행 런북이 그대로 쓴다. 지시문은 "무엇을 판정/컴파일하라"이지 "어느 모델용"이 아니다.

---

## 0. 헤드라인 — STAGE1이 최대 레버리지이자 최소 정비 문서

STAGE2는 F0 카탈로그 환류로 **v1.1.0 (R1~R5)** 까지 강화됐다. STAGE1은 **v1.0.0 (2025-06)** 에서 멈춰 ALT 학습이 하나도 반영 안 됐다. 그런데 taxonomy 실패 물량은 STAGE1에 집중된다:

| 실패군 | 정량 | category |
|---|---|---|
| 암묵 fixture 전제 | 300/1130 (+ 강등 D1 128/581) | C2 |
| press_key 오부착 (NOT_A_KEY) | 189/620 | C3 |
| verifier 수단 부재 | 103/1130 | C2 |
| mutation-cue false-pass + strict 강등 | 20/36, D5 86/581 | C1 |
| focus_state 스키마 부재 | 전 focus TC | C4 |

STAGE1의 `expected[].type`에는 **focus_state가 없고**, `preconditions`에는 **암묵 fixture 역산 게이트가 없으며**, `normalized_intent`에는 **mutation 판정·press_key subtype 판별이 없다**. 이 세 갭이 상류 실패 물량의 대부분을 만든다.

**결론**: 개선은 STAGE1 v1.0.0 → v1.1.0 강화가 1순위. STAGE2는 R6·R7(문서/authoring 보강)에 더해 **verify_focus_moved action 어휘 정렬**(기존 schema/runner drift 복구)이 필요하다. 단 STAGE1이 새로 내는 신호의 **runnable 소비(fixture/mutation 게이트)와 list focus 런너 구현은 트랙 B**다 — 지시문 수정만으로 닫히지 않는다. (2026-07-03 적대 검토 결과 — §9 참조: "R6·R7 2건이면 충분"이라던 초안 판단은 소비자 배선을 누락했음이 확인됨.)

---

## 1. 변경 매핑 요약

| # | 대상 | 삽입 지점 | 변경 | category | 커버 물량 | 판정 |
|---|---|---|---|---|---|---|
| S1-1 | STAGE1 | 정규화 규칙 §추가 | mutation 의미 판독 규칙 (선언 cue 매칭만으로 no-mutation 금지) | C1 | 강등 D5 86 + false-pass | 지금 확정 |
| S1-2 | STAGE1 | CTF `preconditions` + 규칙 | 암묵 fixture 역산 게이트 (공란+상태전제→의심 기본 True·blocking) | C2 | 300/1130 + D1 128 | 지금 확정 |
| S1-3 | STAGE1 | CTF `expected` 앞단 + 규칙 | verifier 실행가능성 등급 선분류 (text/presence/focus/screenshot/불가) | C2 | C_verifier 103 | 지금 확정 |
| S1-4 | STAGE1 | `normalized_intent` press_key | press_key subtype 판별 (bare noun·화면·포커스 참조 = 키 아님) | C3 | 189/620 | 지금 확정 |
| S1-5 | STAGE1 | CTF `expected[].type` enum | focus_state verifier + focus_model(node\|list) 필드 추가 | C4 | 전 focus TC | 값=단말·스키마=지금 |
| S1-6 | STAGE1 | 절대 원칙 §추가 | 자동분류 확정권한 금지 (cue=후보 슬리밍 전용, KEEP/EXCLUDE=사람 게이트) | C1 횡단 | yield 10~25% 원칙 | 지금 확정 |
| S2-1 | STAGE2 | R6 신설 | 미실측 승격 금지 (paraphrase→literal 금지, nav 후보 device_confirm) | C5 횡단 #1 | divergence 83% | 지금 확정 |
| S2-2 | STAGE2 | R7 신설 | focus_model node/list method 분기 (위젯 클래스 판별) | C4 횡단 #2 | 위음성 5/64 등 | 값=카탈로그 有 |
| P-1 | prep 도구 | 신규 게이트 | tc_id cross-batch 충돌 사전검사 (합성 선행) | C7 | 잠재 83·실 0/29 | 코드·별도 승인 |
| P-2 | CLAUDE.md §5 | workflow 운영 규칙 | 합성 agent read-only/return-only + untracked 오염 스캔 | C7 phantom | 4건 실사건 | 코드·별도 승인 |
| P-3 | prep 도구 | 단일 원장 규약 | 판정 CSV=원장·summary=재집계 스크립트 생성 (수기 집계 금지) | C1 드리프트 | 정합 4건 | 코드·별도 승인 |
| P-4 | 조립 도구 | manifest 스키마 | manifest에 result/join 컬럼 (커버리지 갭 가시화) | C12 | ±1~3 불일치 | 코드·별도 승인 |
| D-1 | CLAUDE.md §8.2 | 2026-06-16 row | tc_id 충돌 원인 서술 정정 (Excel dup→phantom, dup=latent) | C7 검증 | — | 본문·승인 게이트 |

**3 트랙 분리**: (A) STAGE1/STAGE2 지시문 편집 = S1·S2 8건 (본 설계 1차 대상) / (B) prep·게이트 코드 = P 4건 (TDD·별도 승인) / (C) CLAUDE.md 본문 = D-1 + P-2 규칙 (§8.3 승인 게이트).

---

## 2. STAGE1 변경 상세 (v1.0.0 → v1.1.0)

### S1-1. mutation 의미 판독 규칙 (C1)

- **지점**: `# 정규화 규칙` 말미 (현 9항 뒤 10항 신설)
- **문제**: 자동 clean-observe 휴리스틱이 mutation 동사 선언 매칭만으로 판정 → 결과동사가 cue-set 밖('유지된다/처리된다'·무동사 선택-적용)이면 false-pass. batch02 20/36 통과분이 직독에서 EXCLUDE/REVIEW.
- **규칙(안)**: "expected 결과문은 **상태 변화 의미를 판독**하라. 선언적 mutation 동사 목록 매칭만으로 'mutation 없음(관찰 전용)'을 판정하지 말 것. 값 유지·묵시적 상태 전이·선택→적용 패턴도 mutation으로 간주하고, 자동화 시 fixture 생성→관찰→정리(잔존 0) 사이클을 요구하라." + CTF에 step-level `mutation_risk: true|false|ambiguous` 필드 추가 검토(선택).
- **판정**: 지금 확정. 스키마 필드는 CTF 전용(validate_tc 무관).

### S1-2. 암묵 fixture 역산 게이트 (C2 — 최대 물량)

- **지점**: CTF `preconditions` 스키마 + `# 정규화 규칙` 신설
- **문제**: precondition 공란 관행 + expected가 사전 데이터/상태 존재를 암묵 가정 → 자동화 시 판정 최다 탈락(A_fixture 300/1130, 강등 D1 128/581). F0 비승격·gap-8도 공통.
- **규칙(안)**: preconditions에 `implicit_fixture_suspected: true|false` 추가. "procedure/expected를 역산해 전제 데이터(사진·연락처·녹음·알람 등)나 사전 화면 상태를 요구하면 precondition 공란이라도 `implicit_fixture_suspected: true` + `blocking: true`. safe-fixture 사이클(생성→관찰→정리, 잔존 0) 가능성을 `normalized`에 기록." (VRC 1 fixture→9 재사용, MEDIA_SEED가 실증 회수 경로.)
- **판정**: 지금 확정. 강등 원인의 ~69%(D1+D5) 중 D1 커버.

### S1-3. verifier 실행가능성 등급 선분류 (C2)

- **지점**: CTF `expected` 앞단 + `# 정규화 규칙` 신설
- **문제**: 색상·미명시 toast·진동·오디오·SubLCD·물리 LED·시각 판정·무동작 negative assert 등 verifier 수단 부재(C_verifier 103/1130)를 정규화 후반까지 끌고 가 판정 비용 낭비.
- **규칙(안)**: expected 문을 정규화 앞에서 **실행가능성 등급**으로 선분류: `text_literal` / `element_presence` / `focus_state` / `screenshot` / `infeasible`(색상·진동·오디오·물리·외부효과·시간 의존). `infeasible` 등급은 판정 비용 없이 조기 `manual_required`/`unsupported`로 분기. CTF `expected[].type`에 등급 반영.
- **판정**: 지금 확정.

### S1-4. press_key subtype 판별 (C3)

- **지점**: `normalized_intent.type` 정의 (현 `press_key` 라인) + `# 금지`
- **문제**: entry_detail 자유문을 press_key로 자동 태깅 → 30.5%(189/620)가 키 신호 자체 부재. subtype 재판정: SELECTOR_DISCOVERY 92·FOCUS_CANDIDATE 61·SCREEN_PRESENT 20·FOCUS_STATE 8·KEYCODE 6.
- **규칙(안)**: "**bare 명사·화면 이동 표현·포커스/상태 참조를 press_key로 태깅 금지.** press_key는 명시적 하드웨어 키(방향키/확인/BACK/전원 등 keycode 확정 가능)만. 그 외는 subtype으로 분류: `selector_discovery`(요소 탐색 필요)·`focus_candidate`(포커스 이동 대상)·`screen_present`(화면 도달 참조)·`focus_state`(포커스 상태 assert). 단일 명시 키(DPAD 등)는 STAGE1에서 keycode 확정 허용(무단말 확정 가능분)."
- **판정**: 지금 확정. 무단말 확정 가능분 175/620도 동시 해소.

### S1-5. focus_state를 expected 스키마에 추가 (C4)

- **지점**: CTF `expected[].type` enum (현 `verify_text | verify_shell | manual_required | unsupported`)
- **문제**: STAGE1 스키마에 focus_state verifier 개념이 없어 focus TC가 verify_text로 왜곡 정규화 → STAGE2/F0에서 재작업(WARN35 35건, cycle2 list-focus 13건). 위젯 focus 모델이 STAGE1→STAGE2→F0 관통 최대 반복 실패원(횡단 #2).
- **규칙(안)**: `expected[].type`에 `focus_state` 추가 + `focus_model: node | list | device_confirm` 필드. assert 유형(focus_move·invariant·boundary_stop·retained·created·position·absent)은 STAGE1에서 계약만, device_value는 `PENDING_F0`. 위젯 클래스가 소스에서 미상이면 `device_confirm` hedge.
- **판정**: 스키마·계약 = 지금 확정 / device_value = 단말 확정. `reference_alt_focus_widget_model`(com.android.mms=list, settings·clock=node) 참조.

### S1-6. 자동분류 확정권한 금지 원칙 (C1 횡단)

- **지점**: `# 절대 원칙` (현 9항 뒤 신설)
- **문제**: 자동 cue/휴리스틱/host 모델의 오류율이 양방향 모두 높음(false-pass 55.6%·과배제 40%·false-KEEP 46.7%). 확정 권한 부여가 반복 사고원.
- **규칙(안)**: "자동 cue·휴리스틱 판정은 **후보 슬리밍 전용**이다. KEEP/확정 EXCLUDE는 사람 직독 또는 단말 실증 게이트를 거쳐야 한다. 용량 계획은 자동분류 수가 아닌 **직독 확정 yield(10~25%)** 기준으로 산정하라."
- **판정**: 지금 확정. cross-cutting root(미실측 승격 금지)의 STAGE1 발현.

---

## 3. STAGE2 변경 상세 (v1.1.0 → v1.2.0)

### S2-1. 미실측 승격 금지 — R6 신설 (C5, 횡단 #1)

- **지점**: `# 단말 실증 기반 verifier/selector 규칙` 말미 (R5 뒤 R6)
- **문제**: paraphrase를 literal verifier로, navigation 가설을 확정으로 승격 → C11 v1 run1 divergence 83%(device-touch 11/12 전건 실패). 컴파일 시점 단말 대조 부재가 원인.
- **규칙(안) R6**: "**verifier literal·selector·navigation 목적지는 단말 run1 discovery로 실측 확정된 값만 확정 컴파일한다.** 소스의 paraphrase(기대문 표현)를 literal로 승격 금지 — 미실측 값은 `device_value: PENDING_F0` + `literal_outcome: LITERAL_PENDING`으로 두고 backfill 대상 표기. 화면 도달 판정도 단말 대조 전에는 `device_confirm` hedge + R3 parent-marker 소멸 게이트 병용."
- **판정**: 지금 확정. R1~R5와 동일하게 authoring 지침(validate_tc 정적 강제 아님).

### S2-2. focus_model node/list 분기 — R7 신설 (C4, 횡단 #2)

- **지점**: R6 뒤 R7
- **문제**: focus verifier를 node 일률 가정 → R1 위음성 5/64. 위젯 클래스가 focus 이동 표현을 결정.
- **규칙(안) R7**: "focus verifier는 **위젯 클래스로 method 분기**한다. ListView(`android:id/list`)=list(컨테이너 focused 고정 + `selected` 자식 이동) / RecyclerView·ScrollView=node(focused 행 이동). 클래스 미확인 시 `focus_model: device_confirm` hedge + fallback 계약. 근거 = `reference_alt_focus_widget_model`(com.android.mms=list, com.android.settings·clock=node)."
- **판정**: 지금 확정. 값 근거는 카탈로그 확보됨.

---

## 4. prep·게이트·도구 (트랙 B — 코드·별도 승인)

| # | 변경 | 근거 | 기존 자산 |
|---|---|---|---|
| P-1 | tc_id cross-batch 충돌 사전검사를 합성 워크플로 **선행 게이트**로 정식 편입 | C7 (batch11 4건 gate 포착) | `scratch/altbasic_tcid_collision_check.py` 존재 → `scripts/` 승격 |
| P-2 | 합성 agent **read-only/return-only** 제약 + 실행 후 **untracked 오염 스캔** 필수 | C7 phantom (batch11 4건 batch10 dir 오염) | CLAUDE.md §5 workflow 운영 규칙 신설 (§8.2 2026-06-16 proposed) |
| P-3 | 판정 CSV = 단일 원장, summary 수치 = **재집계 스크립트 생성** (수기 집계·추정치 병기 금지, judge_method 컬럼 자동/사람 분리) | C1 드리프트 (정합 4건) | 신규 도구 |
| P-4 | manifest에 **result/join 컬럼** 반영 (chunk-N vs 구현 vs 결과 자동 reconcile) | C12 (±1~3 불일치·annex manifest 밖 실행) | manifest 생성기 확장 |

트랙 B는 각 항목이 TDD 코드 변경(§2.1)이라 **항목별 개별 승인**. 지시문(트랙 A) 반영과 독립 진행 가능.

---

## 5. CLAUDE.md 정정 (트랙 C — §8.3 승인 게이트)

### D-1. §8.2 2026-06-16 row 인과 정정 (C7 검증 발견)

- **현 서술**: "tc_id `ALTBASIC_<PREFIX>_<excel_row3>` 비단사 + Excel sheet 내 중복 TC ID(83건)로 cross-batch tc_id 충돌(batch11 4건)"
- **검증 결과(C7 ADJUSTED)**: batch11 실충돌 4건(CALC_027/028·SST_010/011)의 **실제 원인은 워크플로 agent phantom side-effect**(동일 4건을 batch10 dir에 오기록)이지 Excel dup 발현이 아니다. 근거 3중: (a) 충돌 row_key가 KEEP_CONFIRMED 271행에 부재, (b) 충돌 sheet(Calculator·Simple settings)가 Excel dup 4 sheet에 미포함, (c) `s2_correct_phantom.py` + batch11 summary "충돌 0(phantom 삭제 후)". **최종 실충돌 = 0/29. Excel dup 83건은 latent 구조 위험(실발현 0).**
- **정정(안)**: 2026-06-16 row를 두 사건으로 분리 서술 — (1) phantom side-effect(실사건, agent 제약 필요) (2) Excel dup 비단사(잠재 위험, 검사 도구 유지). 현 압축 서술이 두 사건을 혼착.
- **파급**: `altbasic_tcid_collision_check.py` docstring·P-2 규칙도 동일 혼착 → 함께 정정.

---

## 6. 레버리지 순위 (반영 권장 순서)

1. **S1-2 + S1-4** (fixture 역산 + press_key subtype) — 상류 최대 물량(300 + 189). 무단말 확정.
2. **S1-1 + S1-6** (mutation 판독 + 자동분류 확정권한 금지) — false-pass·강등 억제, cross-cutting root의 STAGE1 발현.
3. **S2-1** (미실측 승격 금지 R6) — divergence 83% 차단, cross-cutting root의 STAGE2 발현.
4. **S1-5 + S2-2** (focus_state 스키마 + node/list 분기) — 횡단 #2, 값 근거 확보됨.
5. **S1-3** (verifier 실행가능성 등급) — 판정 비용 절감.
6. **트랙 B (P-1~4) + D-1** — 도구·정합·정정 (코드·본문 별도 승인).

---

## 7. 검증·리스크

- **validate_tc/golden 영향 통제됨**: STAGE1 변경은 CTF 스키마(validate_tc 무관, 메모리 확정)로 compiled-TC 정적 검증에 무영향. STAGE2 R6·R7은 R1~R5와 동일 authoring 지침(정적 강제 아님). golden 3건 회귀 = **실증 완료(2026-07-03, 3/3 PASS)**. 단 focus_state는 CTF `expected` 표면을 넓히는 변경이므로 후속 CTF 합성에서 스키마 정합은 golden/fixture로 지속 통제.
- **over-fitting/과잉제약 리스크 낮음(0 아님)**: 8건 전부 판정/컴파일 규칙(모델 불문)이고 Fable 특화 표현은 없다. 다만 프롬프트 규칙은 항상 과잉 제약 리스크가 있어 적대 검토 후 완화(mutation 대칭·fixture blocking carve-out·원칙8 스코프)했다. **consumer path 없는 신호(mutation_risk·implicit_fixture_suspected·feasibility)는 본 트랙에서 advisory로 명시 제한**했다 — runnable 소비는 트랙 B. focus_state는 CTF 표면을 넓히므로 도메인 특화 리스크는 fixture/golden 회귀로 통제. 산출 지시문은 sonnet 실행 런북이 그대로 사용.
- **~~loader/runner 무변경 정합~~ (정정)**: 초안의 이 주장은 **list focus 모델에 대해 falsified**. 런너 `verify_focus_moved`는 node 전용(focused 노드 bounds 이동)이라 list 모델(컨테이너 focused 고정+selected 자식)은 실행 수단이 없다. 트랙 A는 list를 device_confirm/PENDING로 hedge(runnable 승격 금지)하고, list 런너 verifier는 **트랙 B**로 분리. runner_capability.yaml에 verify_focus_moved 어휘를 추가한 것은 신규 기능이 아니라 기존 런너/schema와의 문서 drift 복구다.
- **버전**: STAGE1 v1.0.0 → v1.1.0(변경 로그: ALT F0 taxonomy 환류 S1-1~6), STAGE2 v1.1.0 → v1.2.0(R6·R7 추가). §2.3 source-of-truth — 지시문·문서만 변경, loader/runner 무변경(트랙 A는 authoring 규칙이라 정합).
- **미해결(단말 필요)**: focus_model device_value(S1-5)·nav 목적지 literal(S2-1 backfill)은 F0 2-run 대상. taxonomy open_questions 12건은 설계 blocker 아님(개선 규칙은 "미확정 시 hedge"를 내장).

---

## 8. 다음 단계

트랙 A(S1·S2)는 **Option C로 반영 완료**(§9). 트랙 B·C는 독립 승인. 트랙 B는 §9의 검토 발견을 요구사항으로 착수.

---

## 9. 적대 검토 결과 + Option C 반영 (2026-07-03)

트랙 A 편집 직후 독립 4렌즈 적대 검토(workflow `wf_f567f082-5c3`, agent 4·오류 0) → **MAJOR 7 / MINOR 12 / NIT 4**. MAJOR가 한 방향으로 수렴: **STAGE1이 새로 만든 신호를 STAGE2·런너가 소비할 경로가 없다.** load-bearing 3건은 오케스트레이터가 파일:라인으로 재검증(전부 사실):

| 결함 | 검증 | 처리 |
|---|---|---|
| G1. focus_state 컴파일 타깃 부재 — `verify_focus_moved`가 tc_step_schema.json:83·action_runner.py:293에 존재하나 STAGE2·runner_capability 어휘에 부재(grep 0) → focus_state가 verify_text로 폴백(WARN35 재생산) | 확인 | **트랙 A 반영**: verify_focus_moved를 STAGE2 Step2·compiled enum·runner_capability에 추가(drift 복구) + R7에 컴파일 매핑 명시 |
| G2. list focus 런너 미구현 — `_verify_focus_moved`는 node 전용(focused 노드 bounds 이동, ui_parser.py:47), list(컨테이너 focused 고정)는 항상 위음성 FAIL | 확인 | **트랙 A**: list=device_confirm/PENDING hedge, runnable 승격 금지 / **트랙 B**: list verifier 런너 구현 |
| G3. STAGE2가 mutation_risk·implicit_fixture_suspected·feasibility 0회 참조 → 최대 레버리지 S1-1·S1-2가 runnable 판정에서 무력화 | 확인 | **트랙 A**: 신호를 advisory로 명시 / **트랙 B**: runnable gate 소비 규칙(pipeline semantics 변경) |

**Option C 반영(트랙 A 완료분)**: 위 G1(어휘 정렬)·G2 hedge·G3 advisory 명시 + MINOR/NIT 정정(R6 근거 10/12=83% 분리 표기·R7 'R1 5/64'→'cycle1 5/64'·원칙8 KEEP/EXCLUDE orphan 제거·mutation 대칭·fixture blocking carve-out·feasibility→type 매핑·device_value STAGE2 소유 명시·focus_state 3층위 주석) + 설계 §0/§7 falsified claim 정정. golden 3/3 재확인.

**트랙 B 추가 요구사항 (본 검토 발견 = 착수 입력)**:
- **B-5. list focus verifier 런너 구현** — `selected` 자식 추적 + scroll-index. `verify_focus_moved`를 node/list 겸용으로 확장하거나 신규 action. (G2)
- **B-6. STAGE2 runnable gate에 STAGE1 신호 소비** — implicit_fixture_suspected+blocking → SETUP 필수/runnable:false, mutation_risk → fixture 정리 사이클 강제, feasibility infeasible → 조기 UNSUPPORTED. compiled_tc.yaml preconditions/step 스키마에 소비 필드 추가. (G3)
- 기존 P-1~4(§4)와 함께 트랙 B 항목별 승인.

## 10. 트랙 B 진행 — B-5 반영 완료 (2026-07-03, TDD)

**B-5. list focus verifier 런너 구현** — G2 해소. TDD(RED→GREEN)로 반영, 커밋 미실행·승인 대기.

| 층위 | 변경 | 검증 |
|---|---|---|
| 런너 | `src/ui_parser.py` `find_selected_node` 추가 · `src/action_runner.py` `_verify_focus_moved`에 `focus_model` 분기(list=selected 자식 bounds, 기본 node) | test_ui_parser 3 RED→GREEN · test_action_runner 4 RED→GREEN(2 회귀 문서 포함) |
| schema | `tc_step_schema.json` step에 `focus_model` enum[node,list] 등록 | 전체 pytest 1032 passed |
| 프롬프트 | STAGE2 R7 = list 확정 컴파일 전환(미지원/트랙 B → focus_model:list, runnable 허용 + device-confirm-once) · compiled enum `focus_model` · 버전 1.3.0 | golden 3/3 PASS |
| 프로파일 | `runner_capability.yaml` verify_focus_moved 양 모델 지원 표기 · runner_version 1.4.0 | 잔여 list-미지원 hedge grep 0 |
| STAGE1 | list hedge 전환(미지원/트랙 B → 지원 + device-confirm-once) · 버전 1.2.0 | focus_model 5층위 정합 |

**정확성 경계(honest)**: 런너 로직은 unit-test GREEN(합성 dump)이고 list 모델(컨테이너 focused 고정 + selected 자식)은 `reference_alt_focus_widget_model`의 F0 실측 근거. 그러나 **실기 list TC의 runtime PASS는 미수행** — 커스텀 어댑터가 `selected`를 dump에 미노출할 가능성 때문에 R7이 **device-confirm-once**(첫 실기 selected 확인)를 요구한다. 즉 list는 runnable-eligible이나 첫 회차 확인 전까지 PENDING backfill 대상.

**잔여 트랙 B**: B-6(runnable gate 신호 소비, G3 미해소 — mutation/fixture/feasibility는 여전히 advisory) · P-1~4 · D-1(트랙 C).

*생성: 2026-07-03. 입력 taxonomy = workflow `wf_8c990ba1-181`. 검토 = `wf_f567f082-5c3`. 트랙 A = Option C 반영 완료(커밋 `6ba591f`). 트랙 B = B-5 반영 완료(커밋 미실행·승인 대기).*
