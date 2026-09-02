# BUG LOG — AT-M140 Launcher BUG27084

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| BUG27084 | Launcher / AppWidget | `OBSERVED` | `IN_PROGRESS` | Launcher DB stale widget record와 AppWidgetService binding 부재가 만날 때 line 185→88 NPE | `BUG27084-KNOWN-BAD-20260901-RCBD-V1`; fixed build 비교 미수행 | `RESULT_2026-09-01.md`; `EVIDENCE_LEDGER.json` |

## BUG27084

- 기능 영역: Launcher / AppWidget pending-widget 복구
- 진단 상태: `OBSERVED`
- 이슈 상태: `IN_PROGRESS`
- 단말: AT-M140, serial `B06201249E00030C`, known-bad incremental `RY07260901S`
- 앱: Launcher 9.0.1.1314/code1314; Weather 7.7.8/code126·7.8.2/code135; AccuWeather 21.1.15-3-rc/code210115003; SimpleClock 2.1.6/code216
- 요약: Launcher DB에 stale widget record가 남고 AppWidgetService binding이 사라진 상태에서 pending widget을 구성하면 Launcher line 185→88 NPE가 발생한다. fixed build `AT-M140Z0827U_DAILY_DEV_GMS_849`의 artifact·fingerprint는 아직 확보하지 않았다.
- 기대 결과: provider binding이 없는 stale record를 안전 placeholder로 표시하거나 제거하고 Launcher와 HOME 렌더링을 유지한다.
- 실제 결과: known-bad `RY07260901S`에서 Weather·AccuWeather·SimpleClock stale-provider 경로가 동일 NPE를 만들었다. 2026-09-01 RCBD 선택 bundle은 clean `0/10`, stale `10/10`이며, ordinal 9 첫 원시 trigger까지 포함하면 stale `10/11`이다.
- 재현 절차: 일반모드에서 3rd-party widget을 정상 배치하고 binding을 확인한다 → 간편모드로 전환한다 → provider 앱 제거·동일 APK 재설치로 AppWidgetService instance를 없앤다 → 일반모드로 돌아가 Launcher DB stale record가 pending widget 경로를 타게 한다 → line 185→88 NPE와 HOME 상태를 수집한다.
- 증거: `RESULT_2026-08-28.md` → `RESULT_2026-08-29.md` → `RESULT_2026-09-01.md`; legacy 45개 bundle은 `EVIDENCE_LEDGER.json`의 manifest 및 tree digest로 결박한다. 마지막 run `20260901T152148Z`는 `RESTORED_SAFE`, Simple HOME `com.hnlens.simplemode`, 잔존 mutation 0이다.
- 관련 TC: `BUG27084-KNOWN-BAD-20260901-RCBD-V1`; Session B known-bad/fixed fresh-pair campaign은 `HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md` 참조
- 정정 이력: `RESULT_2026-08-28.md`의 특정 Weather 한정 가설을 `RESULT_2026-08-29.md`의 SimpleClock 재현과 `RESULT_2026-09-01.md`의 RCBD 정량 결과로 정정·확장했다.

## 결론 경계

- fixed build의 exact artifact와 fingerprint가 없으므로 fixed-build `runtime PASS`/FAIL은 없다.
- 기존 45개 bundle에는 harness source provenance가 기록되지 않았다. 해당 campaign은 적응형 진단 campaign이며 단일 immutable source 반복으로 해석하지 않는다.
- Session B는 handoff의 bootstrap pair 검증 후 fixed profile을 preparation commit으로 통합하고, 새 campaign authority pair에서 known-bad와 fixed root bundle을 모두 새로 capture해야 한다.

## 세션 결과

- 실행일: 2026-09-02
- 단말: 실기 없음; ADB/device 호출 없음
- 앱: tc-runner BUG27084 host-only harness·evidence contract
- 범위: harness provenance, legacy ledger, 운영 문서, Session B fixed-build handoff
- PASS: Session A focused appwidget/contract suite `209 passed`, exit `0`; 명령은 handoff의 검증 기록 참조
- 신규 발견: fixed profile 통합은 runtime pair를 바꾸므로 Session A pair를 campaign 권위값으로 재사용할 수 없음
- 변경·정정: legacy 45개와 future provenance bundle ledger 영역 분리; 전체 bundle tree digest 추가; restore mismatch 감사 보강
- 다음 확인 항목: Session B preparation commit OID/digest 발행, 새 pair의 known-bad authority capture, fixed build 실기

## 문서와 증거

- 재개 상태: `RESUME.md`
- UI 경로: `MENU_TREE.md`
- 누적 evidence 원장: `EVIDENCE_LEDGER.json`
- 결과 연속체: `RESULT_2026-08-28.md` → `RESULT_2026-08-29.md` → `RESULT_2026-09-01.md`
- fixed-build handoff: `HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md`
