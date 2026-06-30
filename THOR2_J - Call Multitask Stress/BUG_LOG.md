# BUG_LOG — THOR2_J 통화 중 멀티태스킹 메모리 압박

단말 THOR2_J (AT-M140, serial B2700125BW000083) · KT · ja-JP · Android 14.

## 요약표

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| CMS-01 | 통화 중 멀티태스킹 (메모리) | CONFIRMED | IN_PROGRESS | 사용자 "오류"=튕김(앱 evict→재시작)+jank, 8앱서 100% 재현(crash/ANR 아님, 0/44). 통화=magnitude 증폭, break-point 4~8앱 | multitask_call_stress.py | RESULT_2026-06-30.md |
| CMS-NOTE-1 | low-RAM 백그라운드 eviction | — | NOTE | low-RAM 단말의 백그라운드(cached/empty) 앱 evict는 설계 동작 — 버그 아님 (scope 분리) | — | CHARACTERIZATION.md §2,§7 |

---

## CMS-01

- **기능 영역**: 통화(MO active) 중 멀티태스킹 메모리 압박
- **진단 상태**: CONFIRMED (전체 매트릭스 44 사이클 — 100% rate 정량 + NOCALL 대조 + break-point)
- **이슈 상태**: IN_PROGRESS
- **단말**: THOR2_J (AT-M140), low-RAM(`ro.config.low_ram=true`), ~2.8GB+zram, PSI lmkd
- **앱**: YouTube / Messages / LINE / YouTube Music (+8앱셀: Chrome / Maps / Settings / Contacts)
- **요약**: 통화 중 헤비앱 멀티태스킹 시 사용자 "오류" = **튕김(런치앱 evict→cold-restart) + 심한 jank(멈칫)**. crash 다이얼로그/ANR 아님.
- **기대 결과**: 사용자가 쓰던 앱이 전면 유지(재시작·멈칫 없음)
- **실제 결과 (매트릭스, 2026-06-30)**:
  - ★**crash/ANR = 0/44**(8앱×3라운드 고압박 포함) — 단말이 압박을 eviction으로 흡수, crash 안 함.
  - ★**튕김+jank = 8앱서 100% 재현**(jank 140~210 frames, 약 2.3~3.5s) → 작업 연속성 끊김. 4앱 0% → 8앱 100% = **break-point 4~8앱**.
  - **통화 = magnitude 증폭(정/역)**: 동일 버스트 CALL vs NOCALL — 4앱 bg_evict 2.7배(4.8 vs 1.8), 8앱 9.6 vs 6.9·jank 177 vs 142. 튕김 occurrence는 8앱서 양 arm 100%(버스트·low-RAM 주동인).
  - escalation: CALL 8앱 r1→r3 bg_evict 9.6→19.1, 튕김앱수 2.2→5.0.
- **재현 절차**: `multitask_call_stress.py --serial B2700125BW000083 --callee <auto> -n N --burst-rounds R` (CALL) vs `--no-call`. 기본 8앱 버스트.
- **증거**: `RESULT_2026-06-30.md`, `logs/multitask_call_stress/{MTX_NOCALL_r1,MTX_CALL_r1,MTX_CALL_r3,NOCALL_0630b,CALL_0630b}/`
- **관련 TC**: `scripts/multitask_call_stress.py`
- **정정 이력**: 2026-06-30 신규(Phase 0) → 소규모 SUSPECT→OBSERVED → 전체 매트릭스 OBSERVED→**CONFIRMED**(튕김/jank 100% 정량·대조·break-point; crash/ANR re-scope=미발생)

> CONFIRMED 승격 요건(§4.2/§4.3): 셀별 정량 rate + CALL vs NOCALL 대조(통화 조건 효과) + break-point threshold + 캡처 시그니처. harness 소규모 repro → 전체 매트릭스 후 갱신.

---

## 세션 결과

- 2026-06-30 Phase 0: 신원/RAM/lmkd/앱/통화게이트/ENDCALL 실측, 신호모델·confound 확정, harness 코어 TDD 32 GREEN + 오프라인 classify 검증.
