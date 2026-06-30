# RESUME — THOR2_J Call Multitask Stress

## 무엇 / 왜
THOR2_J(AT-M140, low-RAM ~2.8GB)에서 **통화 active 중 헤비앱(YouTube/Messages/LINE/YT Music) 연속 기동**의
메모리 압박 오류(앱 crash/ANR + 튕김/jank)를 정량 측정하는 무인 repro harness.
사용자(모바일 QA) 보고 = "복합 모듈 동시 실행 시 오류 잦음".

## 산출물
- `scripts/multitask_call_stress.py` — 무인 repro 루프. parse/classify 코어 TDD.
- `tests/test_multitask_call_stress.py` — 32 GREEN (실제 Phase 0 로그 fixture).
- `BUG_CallMultitask_Monitor.bat` — colleague 1-click 래퍼.
- `CHARACTERIZATION.md` — Phase 0 ground truth(harness config source).
- `BUG_LOG.md` — CMS-01 SUSPECT/OPEN + low-RAM NOTE.
- 원시 로그 = `logs/multitask_call_stress/<run_id>/iter_NNN/`.

## 단말 핀 (필수)
`-s B2700125BW000083` (동일모델 2대 연결 — 오발사 가드). 화면 잠금 = **None/Swipe 임시**(테스트 후 패턴 복원).
callee = 자동응답 회선(실행 시 `--callee`, **문서/commit에 번호 미기재**).

## 실행 (junior는 1차 수동 명령 → 2차 .bat)
```
# 오프라인 자가검증 (무단말)
venv/Scripts/python.exe scripts/multitask_call_stress.py --classify-log <saved_logcat> --apps <list>
# 대조군 먼저 (no-call)
venv/Scripts/python.exe scripts/multitask_call_stress.py --serial B2700125BW000083 --no-call -n 5
# CALL arm
venv/Scripts/python.exe scripts/multitask_call_stress.py --serial B2700125BW000083 --callee <auto> -n 5
```

## 진행 상태 (2026-06-30) — 캠페인 1차 完
- [x] Phase 0 실기 특성 파악 (신원/RAM/lmkd/앱/통화게이트/ENDCALL/신호모델/confound)
- [x] 테스트 앱 권한 사전부여 + focus 판독법(topResumedActivity) + YT 기동 확인
- [x] harness 코어 TDD 34 GREEN(위양성 1건 실데이터 수정) + 오프라인 classify-log 검증
- [x] CHARACTERIZATION/BUG_LOG/RESUME + .bat
- [x] 소규모 repro (CALL/NOCALL/CALL-fast N=5) + tests/ 1024 회귀
- [x] harness 확장(8앱 세트 + `--burst-rounds`) + fg_restart events 기반 robust
- [x] **전체 매트릭스 44 사이클** → RESULT_2026-06-30.md / BUG_LOG CMS-01 CONFIRMED
- [ ] (선택) crash/ANR 천장 재확인(8앱 r5/force-stop) · 시각 증빙 · 개발 피드백

## 핵심 결론 (CONFIRMED)
사용자 "오류" = **튕김(런치앱 evict→재시작) + jank(멈칫)**, 8앱 멀티태스킹서 **100% 재현**. **crash/ANR 아님(0/44)**.
break-point 4~8앱. 통화 = magnitude 증폭(occurrence는 버스트·low-RAM 주동인). low-RAM eviction은 설계동작=NOTE.
harness verdict: FAIL=crash/ANR · WARN-FGRESTART=튕김(events am_kill) · WARN-JANK=멈칫 · 백그라운드 evict=context.

## commit
글로벌 정책 — 작업 중 commit 금지, 명시 승인/하루 batch 시에만. broad add 금지. (현재 전부 untracked, 미stage)
