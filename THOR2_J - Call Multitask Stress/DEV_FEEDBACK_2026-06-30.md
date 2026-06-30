# 개발 피드백 — THOR2_J 통화 중 멀티태스킹 작업 연속성 (CMS-01)

작성 2026-06-30 · 단말 THOR2_J (AT-M140, low-RAM ~2.8GB+zram, `ro.config.low_ram=true`, KT/ja-JP, Android14) · 측정 `scripts/multitask_call_stress.py` (44 cycle 매트릭스)

## 1줄 요약

사용자 보고 "3GB 단말, 복합 실행 시 오류 잦음"의 실체 = **멀티태스킹 중 앱 eviction→재시작(체감 "튕김") + 심한 jank(멈칫)** 으로 **사용자 작업 연속성이 끊기는 것**. **앱 crash/ANR이 아님.** 통화는 이 증상의 **severity를 키움**.

## 증상 분리 (가장 중요)

| 구분 | 내용 | 근거 |
|---|---|---|
| ✅ **CONFIRMED (실제 문제)** | 멀티태스킹 중 **launched 앱 eviction→cold-restart(튕김)** + **jank 140~210 frames(약 2.3~3.5s 멈칫)** | 8앱서 **100%/44 cycle**, 영상(`evidence/`) YouTube pid 교체 |
| ❌ **NOT REPRODUCED** | **앱 crash / ANR** | **0/44** (8앱×3라운드=24 launch/cycle 고압박 포함) |
| ℹ️ **NOTE (설계 동작)** | low-RAM 단말의 lmkd 백그라운드 eviction 자체 | OOM 방지용 정상 동작 — 끄는 대상 아님 |

→ 즉 **"앱이 죽는다(crash)"가 아니라 "쓰던 앱이 사라졌다 다시 시작된다(튕김) + 버벅인다(jank)"** 가 정확한 현상. 개발/QA 커뮤니케이션에서 이 분리가 핵심.

## 정량 근거 (CALL/NOCALL × 버스트)

| 셀 | crash/ANR | 튕김% | bg_evict avg | jank avg(max) |
|---|---|---|---|---|
| NOCALL 4app | 0 | 0% | 1.8 | 0 |
| CALL 4app | 0 | 0% | 4.8 | 29(146) |
| NOCALL 8app | 0 | **100%** | 6.9 | 142(197) |
| CALL 8app | 0 | **100%** | 9.6 | 177(198) |
| CALL 8app ×3 | 0 | **100%** | 19.1 | 179(209) |

- **break-point = 동시 헤비앱 약 5~7개**(4앱 0% → 8앱 100%).
- **통화 = magnitude 증폭**: 동일 버스트 eviction CALL이 NOCALL 대비 4앱 **2.7배**, 8앱 9.6 vs 6.9. (occurrence는 버스트크기·low-RAM이 주동인, 통화는 헤드룸 ~350M 추가 잠식으로 severity↑.)

## 시각 증빙

`evidence/demo_multitask_2026-06-30.mp4` (local-only, 번호 노출 가능 → 트리밍 후 공유): 통화 중 앱 전환 후 **YouTube 복귀 시 처음부터 재시작**(pid 28378→30098). events `am_kill …youtube…cached #5`로 확증.

## 문제 포인트 (사용자 영향)

- **작업 연속성 단절**: 사용자가 보던 앱(영상/메시지/지도)이 백그라운드에서 evict → 재진입 시 **상태 소실·cold-restart**. 짧은 멀티태스킹에도 빈발.
- **통화 시 악화**: 통화 중에는 헤드룸이 더 줄어 같은 멀티태스킹이 **더 자주/심하게** 튕김·멈칫.

## 권고 (개발) — 우선순위

> ❌ lmkd를 끄거나 약화시키는 방향 아님 (OOM/시스템 안정성 훼손). eviction 자체는 유지하되 **체감 단절을 줄이는** 쪽.

1. **중요/최근 사용 앱 보호** — 사용자가 직전에 포그라운드였던 앱(특히 미디어 재생 중)의 oom_adj 우선순위 상향 / 보호 윈도우. lmkd `kill_heaviest_task=true`가 미디어 앱(YouTube/Maps/Chrome)을 먼저 죽이는 현 동작 재검토.
2. **복귀 UX / 상태 복원** — evict 불가피 시 재진입을 빠른 resume + 상태 복원으로(스플래시·로그인·재생위치 소실 최소화). 앱별 `onSaveInstanceState`/세션 복원 점검.
3. **jank 완화** — 통화+멀티태스킹 동시 구간의 메모리 회수/스케줄링 튜닝(현 140~210 frame 드랍). 전환 시 GC thrash·SurfaceFlinger stall 점검.
4. **통화 중 헤드룸 확보** — 통화 UI/스택의 메모리 풋프린트 또는 통화 중 백그라운드 정책 조정 검토.
5. (검증축) 메모리 증설이 어려운 SKU면 **동시 헤비앱 5~7개 임계** 기준 사전 QA 게이트로 활용.

## QA 재현 방법

```
# 측정(무인): CALL vs NOCALL, 버스트/라운드 escalation
venv/Scripts/python.exe scripts/multitask_call_stress.py --serial <serial> --callee <auto-answer> -n 12 --burst-rounds 1
venv/Scripts/python.exe scripts/multitask_call_stress.py --serial <serial> --no-call -n 12 --burst-rounds 1
# 신호: WARN-FGRESTART=튕김, WARN-JANK=멈칫, FAIL-CRASH/ANR=crash/ANR. results.csv 발생률.
```
잠금=None 임시, callee=자동응답 회선, serial 핀 필수(동일모델 다대 오발사 방지). 상세 = `CHARACTERIZATION.md`.
