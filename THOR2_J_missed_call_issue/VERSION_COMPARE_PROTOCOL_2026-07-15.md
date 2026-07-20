# BUG #26510 — 양산 vs MR 후보 버전 비교 프로토콜 (부재중 배지 divergence 원인 격리)

- 목적: 부재중 배지 불일치의 원인이 **버전 간 카운트/알림-삭제 로직 차이**인지 통제 실험으로 확정.
- 가설(사용자): **부재중 알림 삭제 조건이 양산 버전 vs MR 후보 버전에서 다르다** → 업데이트 후에만 divergence 발현.
- 근거(선행 실측, 2026-07-15): 같은 기종 두 단말의 `loadUnreadData`(미러) 거동이 **정반대**.
  - **115 (이슈, MZ0713)**: 미러 = 54 고정, 시스템 `is_read=0`=2와 무관. force-stop→클리어→콜드 재시작에도 54 유지 = **영속 누산기(무-reconcile)**.
  - **083 (클린, MZ0710)**: 미러가 `is_read=0`을 추종. force-stop→클리어(6→4)→콜드 재시작 후 미러=4로 **재동기(reconcile/라이브 카운트)**.
  - 단순 재부팅·부팅창 클리어 둘 다 083에선 divergence 미형성(미러 재동기).
  - → 미러 카운트 로직 자체가 버전/빌드에 따라 다를 가능성. 본 프로토콜로 확정.

---

## 측정 대상 (버전별 동일 실행)

각 단말/버전에서 **미확인 부재중 N건 존재** 상태로 아래를 동일 순서 측정. 값은 전부 실측(adb/logcat).

### P0. 버전·빌드 지문
```bash
S=<serial>
adb -s $S shell getprop ro.build.display.id
adb -s $S shell getprop ro.build.date
for pkg in com.android.dialer com.hnlens.simplemode com.hnlens.launcher3; do
  echo -n "$pkg : "; adb -s $S shell dumpsys package $pkg | grep -m1 versionName | tr -d '\r'
done
```

### P1. 기준 카운트 (부재중 N건 존재, 동기 여부)
```bash
# 시스템 CallLog
adb -s $S shell "content query --uri content://call_log/calls --projection _id:number:is_read:new --where \"type=3 AND is_read=0\""
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3 AND is_read=0\"" | grep -c "Row:"   # A = is_read=0 count
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3 AND new=1\""    | grep -c "Row:"   # new=1 count
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3\""              | grep -c "Row:"   # total missed
# 런처 배지 + 미러 (no-op onChange로 재출력 유도)
adb -s $S logcat -c
adb -s $S shell "content update --uri content://call_log/calls --bind is_read:i:0 --where \"_id=<is_read=0인 id>\""
sleep 3
adb -s $S logcat -d | grep -E "getUnreadMissedCallCount:|loadUnreadData unreadCallCount"
#   Launcher getUnreadMissedCallCount: B = 노말 배지
#   com.hnlens.simplemode ... loadUnreadData unreadCallCount: C = 미러(심플·다이얼러)
```
기록: **A(is_read=0) / B(런처) / C(미러)** 및 A==B==C 여부.

### P2. 부재중 알림 존재/채널 (삭제 조건 비교의 기준)
```bash
adb -s $S shell dumpsys notification --noredact | grep -iE "GroupSummary_MissedCall|phone_missed_call|TelecomMissedCalls" | head
```
기록: 알림 그룹 존재 · 채널(`phone_missed_call` / `TelecomMissedCalls`) · flags.

### P3. ★알림 삭제 거동 (사용자 핵심 가설) — 자연 조작 우선
부재중 알림을 **스와이프 삭제**(또는 전체 지우기)한 직후 재측정.
```bash
adb -s $S logcat -c
# (수동) 알림 그림자에서 부재중 알림 스와이프 dismiss
sleep 2
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3 AND is_read=0\"" | grep -c "Row:"  # A'
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3 AND new=1\""    | grep -c "Row:"  # new'
adb -s $S logcat -d | grep -E "getUnreadMissedCallCount:|loadUnreadData unreadCallCount|updateBadgeCount|CANCEL_ALL_MISSED"
```
기록: 삭제가 **is_read를 1로 클리어하는가(A→A')**, **new를 0으로 만드는가**, **런처(B')·미러(C') 반응**.
→ 버전 차이의 핵심: 양산과 MR에서 이 삭제→is_read/미러 반영이 **다른지**.

### P4. 미러 reconcile 판별자 (영속 누산기 vs 라이브 카운트)
```bash
adb -s $S shell am force-stop com.hnlens.simplemode        # 미러 BLIND
adb -s $S shell "content update --uri content://call_log/calls --bind is_read:i:1 --bind new:i:0 --where \"_id IN (<k개>)\""  # blind 중 클리어
adb -s $S shell "monkey -p com.hnlens.simplemode -c android.intent.category.LAUNCHER 1"   # 콜드 재시작
sleep 4
adb -s $S logcat -c
adb -s $S shell "content update ... (no-op onChange)"
adb -s $S logcat -d | grep -E "getUnreadMissedCallCount:|loadUnreadData unreadCallCount"
```
기록: 콜드 재시작 후 미러가 **is_read=0로 재동기(reconcile)** 인지 **이전 값 고정(persistent)** 인지.
→ 115=persistent / 083=reconcile 로 갈렸던 그 판별자. 양산·MR 각각 어느 쪽인지 확정.

### P5. 개별 탭 확인 (정상 확인 경로, 참고)
콜로그 볼드 항목 1개 탭 → is_read 0→1, 런처·미러 각 −1 동기 여부.

---

## 비교표 (실측 채움)

| 항목 | 083 MZ0710 (클린·reference) | **양산 115 (Jan 16, 실측)** | **MR후보=MZ0710 (115 업뎃후, 실측)** |
|---|---|---|---|
| build 라벨 | SELJY072606MZ0710 | (Jan 16, 라벨 미확보) | **SELJY072606MZ0710** |
| build.date | Fri Jul 10 2026 | **Fri Jan 16 2026** | **Fri Jul 10 2026** |
| dialer ver | 1.0.0.1645 | **1.0.0.1414** | **1.0.0.1645** |
| simplemode ver | 1.0.5.858 | **1.0.5.597** | **1.0.5.858** |
| launcher3 ver | 9.0.1.1347 | **9.0.1.1073** | **9.0.1.1347** |
| P1 A/B/C (동기?) | 9/9/9→6/6/6→4/4/4 (항상 동기) | **5/5/5 (동기, 유저 확인 배지=5)** | **5/5/5 (동기, 배지=5)** |
| fresh 착신 기록 | is_read=0 | **is_read=0, new=1** | (업뎃前 5건 보존) |
| 미러 쿼리 실측 | is_read 라이브 | is_read 라이브 | **`cursor count:5` = is_read 라이브** |
| Dialer updateBadgeCount | — | **push=new(12) → success:false** | (미재측정) |
| **P4 미러 성격** | **reconcile (라이브 추종)** | **reconcile (5→blind clear 3→미러 3)** | **live 쿼리 확인(로그 cursor count)** |
| 결론 | divergence 미형성 | **divergence 미형성** | **divergence 미형성 — 데이터 보존됐는데도 동기** |

**★ 핵심 발견**: MR후보로 올린 **MZ0710에서 divergence 재현 안 됨**. Jan→MZ0710 in-place 업데이트(구 미러 DB·미확인 5건 완전 보존)에도 미러가 **is_read=0 라이브 쿼리**(로그 `UnReadDataHelper.getUnreadMissedCallCount cursor count: 5`) → 런처와 동기. **이슈는 MZ0710이 아니라 MZ0713 특정.**

**이슈 원본 MZ0713 (초기화됨·라이브 증거 소실, 이전 실측만)**: 미러 P4 = **persistent(54 고정, is_read=0=2 무관)**. 런처=is_read=0(2). versionName 미확보(단말 초기화로 확보 불가).

**핵심 diff 축 (양산 확정 → MR에서 어디가 바뀌나)**:
- 양산: 미러(`UnReadDataHelper.getUnreadMissedCallCount`)가 **is_read=0 라이브 쿼리** → 런처와 항상 동기.
- 이슈 MZ0713: 미러(`loadUnreadData`)가 **영속 store**(54) → 런처(is_read=0=2)와 어긋남.
- → **MR 후보에서 미러가 is_read-라이브 → 영속-누산으로 바뀌는지**가 divergence 근본 원인 후보 1순위.
- 보조 축: fresh 착신의 is_read 초기값, 콜로그 조회의 is_read 클리어 여부, updateBadgeCount(new) 성공 여부.

---

## 판정 논리

- 양산 P4=reconcile & MR 후보 P4=persistent → **MR 후보에서 미러 카운트 로직이 영속-누산으로 바뀜** = divergence 근본 원인 확정.
- 또는 P3 삭제→is_read 거동이 버전 간 다르면(예: MR에서만 삭제 시 is_read 클리어) → **알림 삭제 조건 차이**가 트리거(사용자 가설 직접 입증).
- 둘 다 동일하면 → 버전 차이 아님, 다른 상태 요인(누적 데이터/DB 마이그레이션) 재검토.

## 운영 주의
- 115(이슈 본체)는 divergence 라이브 증거 → **재부팅·초기화 금지**(무-reconcile은 콜드 재시작까지만 검증). P0(versionName) 확보만 read-only로.
- 083은 synthetic 부재중 유지(reference). 
- MR 업데이트 전 양산 상태를 반드시 먼저 캡처(업데이트 후 되돌릴 수 없음).
