# Engineer Mode IMS — 실기 런타임 플레이북

`EXEC_RUNBOOK_복합_2026-06-16.md` 승계. 목적 = 8케이스 실기를 **빠르고 정확하게** 반복. host-verified 정식 경로 = `scripts/eng_mode_runner.py` (**device smoke pending**); `run_complex_0617.py`는 2026-06-17 frozen 실기 증거.

판정 = 3-Way: **Way1**(UI readback) ∧ **Way2**(write-hook log) ∧ **Way3**(.qmdl SIP/SDP/RRC = ground truth). **Way1·2 commit ≠ Way3 반영** — Way3는 항목·캐리어별로 다름(아래 매트릭스).

---

## 1. Override Applicability Matrix ★ (실행 전략을 사전 결정 — 불필요 reboot·재시험 제거)

| 항목 [BTS] | iface | 적용시점 | reboot영속 | Way3 신호 | SKT | LGU+ | KT |
|---|---|---|---|---|---|---|---|
| Domain [25059] | EFS | **reboot-load** | 유지 | REGISTER req-URI/realm | ✓(비routable→404) | ✓(→403) | TBD |
| PRID [25066] | EFS | **reboot-load** | 유지 | Auth username | ✓ | ✓ | TBD |
| Register Expires [25035] | EFS | **reboot-load** | 유지 | REGISTER Expires | ✓ | ✓ | TBD |
| User Agent [19420] | NV#69689 | **reboot-load** | 유지 | 모든 SIP User-Agent 헤더 | ✓(측정) | TBD | TBD |
| Subscribe Expires [25036] | EFS | **reboot-load** | 유지 | SUBSCRIBE Expires | ✓(측정) | TBD | TBD |
| SIP Timer T1 [19429] | NV#73834 | write-confirm | 유지 | 재전송 간격(손실시만 관측) | 보조축 | 보조축 | 보조축 |
| Voice Codec Priority [25043] | EFS(AudioProfile1) | **runtime** | 유지(추정) | m=audio 코덱 순서 | ✓(06-16) | ✗(EVS-first) | TBD |
| AMR ModeSet [19443] | NV#73846 | **runtime** | 환원(추정) | m=audio fmtp mode-set | ✓(06-16) | ✗ | TBD |
| AMR-WB ModeSet [19445] | NV#73846 | **runtime** | 환원(추정) | m=audio fmtp mode-set | ✓(06-16) | ✗ | TBD |
| HD Voice [19410] | EFS(AudioProfile1) | **runtime** | 유지 | m=audio AMR-WB 유무 | ✓ | △(AMR-WB 존재; C1) | TBD |
| Session Expires [19425] | NV#73842 | **runtime** | **환원** | SIP Session-Expires | TBD | ✗(3600 고정) | TBD |
| Session Refresher [25038] | EFS#25038 | **runtime** | **환원** | SIP refresher= | TBD | ✓(uac) | TBD |
| RTP Timer [19581] | NV#73842 | **runtime** | **환원** | RTP aliveness 주기(SDP 비노출) | TBD | TBD | TBD |
| Traffic Port [19593] | NV#73845 | **runtime** | 유지 | m=audio/video port | TBD | ✓speech / ✗video | TBD |
| Video Codec Priority [25049] | EFS(VideoProfile1) | **runtime** | 유지(추정) | m=video 코덱 순서 | TBD | △(H265 최우선·베이스라인無·추정) | TBD |
| IMS Reset [25071] | PDC | action+reboot | (전체 clear) | 부팅 후 전항목 default | ✓(06-16) | ✓ | 추정(캐리어무관) |
| HSPA [16232] | Diag#3649 | runtime(device) | 유지 | WCDMA AS release (WCDMA-gated) | n/a | n/a | n/a |
| Auto Answer | QcRilHook | runtime(device) | TBD | 수신호 자동응답 | n/a | n/a | n/a |
| LTE ROHC/CDRX [18582] | hook | hook(**no-op**) | — | RRC (현재 no-op 확정) | n/a | n/a | n/a |

**표기 (측정 vs 추정 구분)**: ✓반영 / ✗미반영 / △부분 = **실측값**. `(측정)`·`(06-16)` = 출처 명시 실측. **`(추정)` = 미측정·추론, 검증 필요**(예: NV#73846 환원은 NV#73842 유추 — 단 NV#73845는 반대로 '유지'였으므로 불확실; Voice/Video Codec 유지는 HD/EFS 일반화 추론; Video LGU+ ✓는 pre-override 베이스라인 미캡처; IMS Reset KT는 캐리어무관 기계라 추론). `TBD` = 미측정. **추정 셀을 사실로 간주해 재검증 생략 금지.** 근거 = 2026-06-17 LGU+ 실기 + 06-16 SKT.

---

## 2. 실행 규칙 (매트릭스에서 도출 — 이게 시간을 줄인다)

1. **등록 케이스(REG_A/B)** = `reboot-load`. → **write → reboot → capture**. airplane 토글 재등록으론 **미반영**(기존 config로 재등록). 여러 등록 케이스는 가능하면 **reboot 1회 공유**(REG_A 도메인이 비routable이면 등록 실패하므로 REG_B와 별 reboot).
2. **호 케이스(VOICE/SESSION/VIDEO)** = `runtime`. → **발신 직전 runtime 기재, reboot 금지**. reboot가 NV#73842(Session/RTP)·EFS#25038(Refresher)을 **환원**시키므로 reboot 후 호출하면 그 값들이 default로 빠진다(이번 run의 낭비 reboot 원인). **음성 1콜 = VOICE+SESSION 동시 검증**(같은 INVITE SDP에 코덱·Session-Expires·port·refresher 다 실림), **영상 1콜 = VIDEO**.
3. **RESET** = teardown 최후. IMS Reset → reboot → 전항목 default 환원 확인 + IMS 정상 복구. **GEN 원복**(HSPA=3, Auto Answer 원상태)은 reset이 안 건드리므로 별도 수행.
4. **C1 커플링**: Voice Codec ↔ HD Voice = AudioProfile1 동일키 **last-write-wins**. HD만 순수 검증하려면 Voice Codec을 같이 주지 말 것.

**권장 1-run 순서**(reboot 2~3회 목표 — 미측정, batch/순서 효과는 ODIN2 재연결 시 측정): preflight → (REG_B write→reboot→capture) → (REG_A write→reboot→capture) → 호 케이스(VOICE+SESSION write→음성콜, VIDEO write→영상콜, **reboot 없음**) → RESET(reset→reboot→GEN 원복).

---

## 3. 런너 사용 (`scripts/eng_mode_runner.py`)

`scripts/eng_mode_runner.py`가 프로파일 기반 정식 경로다. 기존
`run_complex_0617.py`는 2026-06-17 실기 RESULT/RUN_LEDGER가 참조하는 frozen
증거이므로 수정하지 않는다. 기본 프로파일은 `ODIN2_ENG_V1`; 증거는 repo root의
`ODIN2 - Engineer IMS/log/RUN_YYYYMMDD/` 아래에 누적된다.

> 현재 범용 경로는 host-TDD/dry-run 완료, **device smoke pending**이다. smoke 전
> `runtime PASS` 또는 frozen 런너와의 단말 거동 동등성을 주장하지 않는다.

```
python scripts/eng_mode_runner.py plan <TCID>       # adb 0 dry-run: 순서·kind·target rid 검증
python scripts/eng_mode_runner.py preflight         # 단말ID·캐리어·IMS·boot_id·로그경로 기록 + WRONG DEVICE 가드
python scripts/eng_mode_runner.py caseset <TCID>    # 케이스 전 설정을 앱 1회 기동 안에서 batch (force-stop 없음)
                                  #   항목별 Way1(readback, stdout)+Way2(hook → cs_<item>_hook.log) 분리 캡처. CASESETS는 scripts/eng_mode_profiles.py
python scripts/eng_mode_runner.py capture <TCID> <tag> <reg|call|any> [timeout]
                                  # 상태-게이트: 등록/통화 도달까지 폴링 후 qmdl+main pull, 캐리어/UTC
python scripts/eng_mode_runner.py reboot
python scripts/eng_mode_runner.py pull <TCID> [tag]
                                  # state/write/read/radio/mfield는 단건 보조. 세부 인자는 <command> --help 참조
```
- 프로파일/출력 override는 명령 앞에 둔다: `--profile ODIN2_ENG_V1 --out-root <path> --run-label <label>`. 다일 캠페인은 자정 분절 방지를 위해 고정 `--run-label`을 필수로 지정한다.
- **caseset 증거 granularity**: 항목별 Way1=stdout `item=값`, Way2=`cs_<item>_hook.log`(항목당 logcat clear→write→hook). 단건 명령과 동급 귀속. (caseset 자체엔 reboot/call 트리거 없음 — 적용시점 매트릭스대로 등록계는 별도 reboot, 호계는 caseset 후 발신.)
- 발신: `adb shell am start -a android.intent.action.CALL -d tel:<번호>` (영상=`--ei android.telecom.extra.START_CALL_WITH_VIDEO_STATE 3`), 종료 `input keyevent 6`. **발신 전 preflight로 자기번호·캐리어 재확인**(self-call·SIM swap 방지).
- pull은 항상 런너(python subprocess) — bash `adb pull /sdcard/...`는 **MSYS 경로변환 버그**(`C:/Program Files/Git/sdcard/...`)로 실패.

## 4. QCAT SIP/SDP 추출 (inline PowerShell — `-File`은 분류기 차단, 반드시 inline)

```powershell
$qcat = New-Object -ComObject QCAT6.Application
$f = $qcat.PacketFilter; $f.SetAll($false); $f.Set(0x156E,$true); $f.Commit()
# (선택) 다중 이벤트 qmdl에서 트리거 윈도우만: $qcat.SetTimeWindowAbsolute("2026-06-17 06:34:00","2026-06-17 06:35:00")  # UTC
$qcat.Process($qmdl,$out,$false,$false)   # 200MB qmdl→ SIP만 수~30KB. LastError 점검
```
- **PacketFilter가 크기 문제를 이미 해결**(전체 파싱 불필요). "No Visible Packets" = qmdl에 해당 SIP **아직 없음**(조기 pull) → `capture` 상태-게이트로 회피.
- 검증 포인트: REGISTER req-URI/Expires/Authorization username · SUBSCRIBE Expires · m=audio(rtpmap AMR-WB/16000 유무=HD, fmtp mode-set, port) · m=video(H26x 순서, port) · Session-Expires/refresher. **AP logcat callProfile(audioCodecAttribute=null)은 비권위**.

## 5. App-trap (런너에 내장 — 재발견 금지)
① EditText auto-clear 안 됨 → focus→clear(123+DEL)→입력검증 후 Write. ② 멀티필드 NV 에디터(Traffic Port·SIP Timer)는 **Write 버튼이 소프트키보드에 가림** → 입력 후 **IME dismiss(keyevent 111) + 재dump로 버튼 좌표 갱신**. ③ off-screen 필드는 dump에 없음 → scroll-to-field. ④ 라디오 옵션은 **exact-text 우선**(부분매칭 충돌, 예 'H.265' ⊂ 'Default (...,H.265)'). ⑤ 게이트 재진입 = `am force-stop` 후 relaunch(caseset은 1회만). ⑥ 부팅 시 ODIN2 DataPopup '사용'으로 dismiss. ⑦ `svc power stayon true`.

## 6. 검증 윈도우 / 캐리어 규율
- reboot 후 로깅은 IMS 등록 완료(200 OK) 또는 최종 실패까지 유지(`capture reg`가 폴링).
- **시작 시 preflight**로 단말 model(AT-M150)·engineer app·캐리어 고정. **발신마다 캐리어 재확인** — SIM 교체/자기번호 발신을 가드가 flag. 결과 기재 시 **실행 시점 캐리어 칸**에 기록(SKT/LGU+/KT 혼동 금지).
