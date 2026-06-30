# CHARACTERIZATION — THOR2_J 통화 중 멀티태스킹 메모리 압박

Phase 0 실기 특성 파악 결과 (harness config의 source-of-truth).
실행일 2026-06-30 · 단말 THOR2_J (AT-M140) · 모두 실측.

> 검증 어휘: 본 문서는 `manual evidence observed` 단계 산출물. 진단 결론(`OBSERVED`/`CONFIRMED`)은
> harness 정량 측정 후 RESULT/BUG_LOG에 기록.

## 1. 단말 신원 (wrong-device 핀)

| 항목 | 값 |
|---|---|
| serial (`ro.boot.serialno`) | `B2700125BW000083` ← **모든 adb 호출 `-s` 핀 필수** |
| 동일 모델 동시 연결 | 2대 (다른 1대 `B06201249E0002F0`) — 오발사 가드 필수 |
| 모델/디바이스 | AT-M140 / thor2 (ALT, MTK MT6765) |
| OS / 빌드 | Android 14 (SDK34) / `UP1A.231005.007`, fingerprint `…/SELJY072606MZ0630:user/release-keys` |
| build.type | **user** (양산) — su 없음, 순수 non-root |
| 캐리어 / 로케일 | KT / ja-JP |

## 2. 메모리 / low-RAM (NOTE scope — 버그 아님)

| 항목 | 값 |
|---|---|
| MemTotal | 2,882,372 kB (~2.75GiB) |
| zram SwapTotal | 1,296,888 kB (~1.27GB) |
| idle MemAvailable | ~1,763,000 kB (3샘플 안정) |
| **통화 active MemAvailable** | ~1,400,000~1,470,000 kB → ★통화가 **헤드룸 ~300~360M 잠식** |
| `ro.config.low_ram` | **true** (Android low-RAM 단말 — 백그라운드 제한·공격적 lmkd) |
| lmkd | PSI 기반(`psi_partial_stall_ms=50`, `complete=350`), `kill_heaviest_task=true`, `persist.sys.lmk.reportkills=true` → **kill 이벤트 로그 캡처 가능** |

## 3. 통화 제어 (실측 확정)

| 동작 | 명령 / 게이트 | 실측 |
|---|---|---|
| MO 발신 | `am start -a android.intent.action.CALL -d tel:<callee>` → telecom → `com.android.dialer` | OFFHOOK(`mCallState=2`) ~2s |
| **통화 active 게이트** | `dumpsys telecom` **`state=ACTIVE`** | 자동응답 회선 **~6s** 답신 |
| audio mode | `dumpsys audio` mode (internal) | ★**IN_CALL로 안 바뀜 → 비신뢰 게이트** (telecom state로 판정) |
| **종료** | `input keyevent KEYCODE_ENDCALL`(6) | **mCallState=0 복귀 OK → 무인 자동화 가능** |
| Power 금지 | 측면 Power=물리 End지만 short=SLEEP(223)/long=전원팝업 | ★harness Power 키 **절대 금지** |

callee = 자동응답 테스트 회선(실행 시 `--callee`로 공급, **문서/commit에 번호 미기재**).

## 4. 테스트 앱 (권한 사전부여 완료 → 다이얼로그 confound 제거)

| 앱 | launch activity | 버전 | 상태 |
|---|---|---|---|
| YouTube | `com.google.android.youtube/.app.honeycomb.Shell$HomeActivity` | 20.25.x | 기동+영상 자동재생 ✓ |
| Messages | `com.android.mms/.ui.ConversationList` | 1.0.0.2302 | ✓ (기본 SMS) |
| LINE | `jp.naver.line.android/.activity.SplashActivity`→`.../MainActivity` | 26.10.0 | 로그인X, 프로세스 상주(부하) ✓ |
| YouTube Music | `com.google.android.apps.youtube.music/.activities.MusicActivity` | 8.25.x | ✓ |

발신/문자 기본앱 = AOSP role holder(`com.android.dialer` / `com.android.mms`). 런처 `com.hnlens.simplemode`, recents `com.hnlens.launcher3`, sub-display `com.hnlens.app.subdisplay`.

## 5. 계측 방법 (harness 핵심 — 실측으로 확정)

- **focus 판독 = `dumpsys activity activities | grep topResumedActivity=`** → `parse_top_activity`.
  `grep -m1 mFocusedApp`은 **첫 줄이 항상 null(전역 필드)** → 폐기.
- **포그라운드 재시작(튕김) = `pidof <pkg>` pid 변화** (버스트 후 app1 재진입 시 cold-restart 여부).
- ★**최강 신호 = `logcat -b events` `am_kill` / `am_proc_died` / `am_proc_start`** (adj 사유 포함):
  - `am_kill` 포맷 `[user,pid,pkg,adj,reason]` (예 `[0,24696,com.android.mms,945,empty #5]`)
  - `am_proc_start` 포맷 `[user,pid,uid,pkg,reason,{cmp}]` (★uid offset)
  - 사유 `cached`/`empty` = 백그라운드 evict = **NOTE**; `top-activity` 등 = 포그라운드.
- 보조: Choreographer `Skipped N frames`(jank/멈칫), GC thrash, crash 버퍼 FATAL, `ANR in`.

## 6. confound 제어

| confound | 처리 |
|---|---|
| keyguard(패턴 잠금)가 앱을 가림 → focus=null·즉시 evict | 화면 잠금 **None/Swipe 임시 변경**(사용자, 테스트 후 패턴 복원). 무인 루프엔 secure 잠금 자동해제 불가 |
| 권한/온보딩 다이얼로그(`GrantPermissionsActivity`)가 전면 가로챔 | `pm grant` **권한 사전부여**(harness `grant_permissions`) |
| 동일모델 2대 오발사 | serial 핀 + `assert_target`(ro.boot.serialno + AT-M140) |
| 통화 끊김 / 재부팅 | calldrop·boot_id로 **verdict 제외**(WARN, 분모 밖) |

## 7. ★핵심 발견 (실측 ground truth)

짧은 수동 버스트(통화 active + YT/MMS/LINE/YTM 연속 기동)에서:

- **FATAL 크래시·정식 ANR = 0** (crash 버퍼 비어있음, `<no ANR since boot>`).
- 실제 동작 = **백그라운드 eviction storm** — gms/webview/**Play스토어**/chrome/safetyhub/**YouTube(백그라운드로 밀린 뒤 `cached #5` kill)** 등 다수 kill, **Messages는 kill→즉시 재시작**.
- **jank** — YouTube `Skipped 65~99 frames`(≈1~1.6s 멈칫), system_server Slow dispatch 127ms.
- 통화 유지(mCallState=2), 발열 41°C 정상.

→ 이 low-RAM 단말의 "복합 실행 오류"는 **FATAL보다 (a) 포그라운드 앱 재시작(튕김) + (b) jank(멈칫)** 형태가 우세. harness verdict는 사용자 목표대로 **FAIL = 앱 crash/ANR**로 두되, 튕김(`WARN-FGRESTART`)·jank(`WARN-JANK`)·백그라운드 evict(NOTE)를 **별도 측정**하여 N사이클 발생률로 정량화. FATAL/ANR이 지속 압박에서 간헐 발생하는지는 루프가 확인.

## 8. harness 매핑

`scripts/multitask_call_stress.py` (parse/classify 코어 TDD `tests/test_multitask_call_stress.py` 32 GREEN).
verdict 폐집합: `ERROR-SETUP→WARN-REBOOT→WARN-CALLDROP→FAIL-CRASH→FAIL-ANR→WARN-REVIEW→WARN-FGRESTART→WARN-JANK→PASS`.
실패 분자 = FAIL-CRASH/FAIL-ANR. confound(setup/reboot/calldrop) = 분모 제외.
