# STAGE1 Settings batch02 — synthesis summary (2026-06-09)

STAGE1 CTF drafts for the **remaining 36** clean-observe `23.Settings` candidates,
after human re-adjudication. **STATIC_ONLY**. Not device-validated, not runnable.
Device 2-run green in `thor2j-tc-appium` is required before any runnable claim.

- source Excel: `doc/[THOR 2] ALT Basic Test Case_FULL.xlsx`, sheet `23.Settings` (read-only)
- decomposition: `THOR2 - ALT Basic TC Audit/settings_anchor_gap_enriched_2026-06-09.csv`
- output: `stage1_settings_batch02/` (16 KEEP YAMLs)

## Population basis (reproducible)

- `EXPORT_READY 52` = clean-observe (`mutation_suspected=False AND text_input_required=False`)
  EXPORT TCs in the 6 batch01 areas (앱 / 알림 / 위치 / 안전 및 긴급 상황 / 디지털 웰빙 및 자녀 보호 기능 / Google).
- **remaining 36** = 52 − 16 already synthesized in batch01.
- by area (36): 알림 11 · 디지털 웰빙 12 · 안전 및 긴급 상황 9 · Google 4 (앱·위치 clean-observe fully consumed in batch01).

## Adjudication outcome — KEEP 16 / EXCLUDE 10 / REVIEW 10

The automated clean-observe heuristic passed all 36, but a **human read of
procedure + expected** rejected/held 20 (see mutation-cue NOTE below).

### KEEP 16 (synthesized here)
| area | tc_ids | anchor_state |
| --- | --- | --- |
| 알림 | 144, 152, 159, 162, 164, 167 | MISSING |
| 안전 및 긴급 상황 | 888, 893 | MISSING |
| 디지털 웰빙 | 921, 932, 934, 938, 942, 944 | PARTIAL (settings_d1_wellbeing) |
| Google | 954, 958 | TARGET_REACHED (settings_d1_google) |

anchor distribution (KEEP 16): **MISSING 8 / PARTIAL 6 / TARGET_REACHED 2**.

### EXCLUDE 10 (NOT synthesized — state change / data write / wizard)
| tc_id | reason |
| --- | --- |
| 166 | 방해 금지 지속 시간 **선택 적용**(사용중지할때까지/1시간/항상확인) |
| 168 | 숨겨진 알림 표시 옵션 **선택 적용**(차단 동작 설정) |
| 853 | 의료정보 혈액형 **선택→저장** |
| 867, 868, 869 | 장기 기증자 예/아니오/알수없음 **선택→"처리된다"**(의료 데이터 write) |
| 876 | 긴급 SOS **셋업 위저드 실행** |
| 929, 930, 931 | 집중 모드 **지금 사용 활성/중지/휴식**(상태 변경) |

### REVIEW 10 (held — ambiguous verifier / sensitive / external)
| tc_id | reason |
| --- | --- |
| 140, 933 | 정렬 드롭박스 **순서 변동**, assert 곤란 |
| 154, 156 | 설정 탭 → **연락처(외부) 페이지 전환** |
| 866 | 장기 기증자 팝업 — **의료 민감**(관찰 범위 재설계 필요) |
| 875 | 긴급 SOS **민감** 동작 |
| 924 | 취침 모드 **취소 플로우**(설정 dialog 상호작용) |
| 947, 963 | 자녀 보호 기능 설정 — **외부 Family Link** 위저드 의심 |
| 965 | Firebase App Indexing — **항목명 깨짐 / verifier 모호** |

## Entry contract by anchor_state

| anchor_state | n | entry intent | rule |
| --- | --- | --- | --- |
| MISSING | 8 | `shell_candidate` + `shell_hint=UNRESOLVED` | no confirmed public deep-link; tap-nav from parent; device probe required. **No invented `android.settings.*` action.** |
| PARTIAL (wellbeing) | 6 | `navigate` | 디지털 웰빙 d1 is a **confirmed coverage-gap** (WELLBEING_SETTINGS / DIGITAL_WELLBEING_SETTINGS = "No activity found"). **No `shell_candidate`, no action.** `entry_type=tap_navigation_required`; thor2j-tc-appium tap-discovery + device validation needed. |
| TARGET_REACHED (Google) | 2 | `navigate` | Google d1 baseline-reached; leaf may route to an **external Google package** — package/action **not asserted** before device measurement. |

- No KEEP TC maps to a validated v1.2 deepen anchor (인쇄=연결된 기기, 모든 앱=앱 already done) → `deepen_anchor_link: none` for all 16.

## Verifier contract (all 16)

- On/Off controls are **not pressed**; current On/Off state is **not** fixed as expected.
- expected candidates = screen title + item labels + control **presence** only
  (`risk_note: control_presence_only` where On/Off controls exist).
- source paraphrase stays under `expected_texts_candidate` — **not** promoted to a
  confirmed on-screen literal (each step `ambiguity: true`).
- `expected_result_raw` preserves the verbatim source expected text (incl. On/Off
  defaults) for traceability, but is not used as an assertion string.

## Common guards (all 16)

`tc_class: SEMI_AUTO` · `export_status: STAGE1_DRAFT` · `evidence_level: STATIC_ONLY`
· `validation_required: device_2run_green` · `focusrule_evidence_transfer: false`
· `automation_class: SEMI_AUTO_CANDIDATE`. **Absent**: RUNNABLE_NOW, `runnable: true`,
`tc_class: FULL_AUTO`, `am start`.

## NOTE — automated mutation-cue miss (classifier follow-up, not this batch)

The static `mutation_suspected` cue set missed several genuine mutations that the
human read caught, because the result verbs fell outside the declarative cue set:

- `유지된다` (집중 모드 활성 유지 — 929/930)
- `처리된다` (장기 기증자 값 — 867-869; 예외 처리 — 944 expected line 3)
- selection-applies without a cue verb (166/168 duration/option select)

These are EXCLUDE/REVIEW by human read here. **Cue-set hardening is a separate
classifier track** (would re-touch `scripts/settings_anchor_gap.py` + its golden);
intentionally **not** mixed into this synthesis batch.

## Next

1. Review these 16 STAGE1 drafts.
2. On approval → device 2-run validation in `thor2j-tc-appium` (resolve actual entry,
   confirm leaf text, tap-discovery for the 6 wellbeing PARTIAL + 8 MISSING).
3. REVIEW 10 → separate re-design pass (observe-scope for sensitive/medical, verifier
   for sort-order, external-package handling). EXCLUDE 10 → out of STAGE1 observe scope.
