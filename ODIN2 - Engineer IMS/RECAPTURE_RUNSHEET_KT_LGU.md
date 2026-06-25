# RECAPTURE RUNSHEET — KT/LGU+ on-wire (TC01 req-URI · TC02 호 SDP)

> 목적: 다음 ODIN2 단말 세션에서 **KT/LGU+ on-wire gap 2건**을 결정적으로 재캡처하기 위한 체크리스트.
> 전체 재검증 매뉴얼 아님. 깊은 운영 규칙은 [`RUNTIME_PLAYBOOK.md`](RUNTIME_PLAYBOOK.md), 파싱법은 [`docs/qcat_parsing.md`](../docs/qcat_parsing.md) IMS 섹션 참조.
> 선행 결과 = [`RESULT_2026-06-23.md`](RESULT_2026-06-23.md). 본 세션 결과는 **신규 `RESULT_<날짜>.md`** 로 (시리즈, cross-link).

---

## 1. 완료 / 남음 (이미 닫힌 것은 재작업 안 함)

| | 상태 |
|---|---|
| SKT TC01 / TC02 / TC03 | **완결** (TC01 on-wire 5/5 · TC02 SDP mismatch 0 · TC03 기능적 원복) |
| KT/LGU+ TC03 | **기능적 원복 확인**(QShrink 재등록 정상). 값단위 default = NOTE |
| **KT/LGU+ TC01 req-URI** | ❌ 미확정 — KT 등록성공 inconclusive · LGU+ 400 귀속 미확정 → **본 세션 대상** |
| **KT/LGU+ TC02 호 SDP** | ❌ 미수집 → **본 세션 대상** |

선택(있으면 같은 세션에 추가, §9): BTS#16232 HSPA WCDMA · BTS#25071 KT RESET-NONPERSIST cycle-2 · TC03 on-wire default.

## 2. 왜 online QXDM 만 가능

USER 빌드 **offline LS `/sdcard/ls_log/modem/*.qmdl` = narrow mask → `0x156E`(on-wire SIP) 부재**("No Visible Packets").
offline 을 QXDM 에 import 해도 복구 안 됨(마스크 = 캡처시점 적용). on-wire REGISTER/INVITE/SDP 는 **online QXDM `.hdf`/`.isf`(full diag mask)** 에만 존재.

| 캡처 | 0x156E | 용도 |
|---|---|---|
| **online QXDM `.hdf`** (호스트 PC 측 로깅) | **있음** | **req-URI · SDP (본 세션)** |
| offline LS `*.qmdl` (단말 자체 로깅, 런너 `pull` 대상) | 없음(QShrink 0x1FEB 만) | 등록 state/errorCode (재확인용, 본 gap 아님) |

→ ★ **런너 `capture`/`pull` 은 단말측 offline qmdl 을 가져온다(0x156E 없음)**. 본 gap 은 **QXDM 호스트 로깅의 `.hdf`** 로만 닫힌다. 런너는 preflight·config 적용·`state` 용.

## 3. 선행조건 / 가드 (★ 시작 전 필수)

1. ★ **단말 고정** — 런너는 **CLI `-s` 없음**. serial = 환경변수 `ENG_DEV`(default `c4324122`=Z0612U, **V2 아님**). default 가 연결돼 있으면 그걸 선택하고, 모델 가드는 `AT-M150` 만 보므로 두 ODIN2 단위를 **구분 못 함** → **ENG_DEV 미설정 시 잘못된 단위 자동선택 위험**.
   ```powershell
   $env:ENG_DEV = "f2bfcc3c"        # Z0620U = V2 1.0.6  (cmd: set ENG_DEV=f2bfcc3c)
   ```
2. **preflight** — model/build/carrier/IMS/boot_id 확인 + WRONG DEVICE 가드:
   ```powershell
   venv\Scripts\python.exe "ODIN2 - Engineer IMS\run_complex_0617.py" preflight
   ```
   `model=AT-M150` · `build`=Z0620U · `carrier_net`= 해당 캐리어 확인. 아니면 **중단**.
3. **캐리어별 USIM 교체** — KT 측정 시 KT USIM, LGU+ 측정 시 LGU+ USIM. **교체 후 preflight 재확인**(carrier 칸 일치). 발신마다 자기번호·캐리어 재확인(self-call/SIM-swap 가드).
4. **부팅 시 ODIN2 DataPopup** `OdinConfirmDataDialogActivity` → **'사용' 으로 dismiss** 후 진입.
5. 화면 유지 `adb -s f2bfcc3c shell svc power stayon true`. 앱 함정(EditText auto-clear · 멀티필드 IME 가림 · radio exact-text · 게이트 재진입)은 런너 내장 — [`RUNTIME_PLAYBOOK.md`](RUNTIME_PLAYBOOK.md) §5.

## 4. 재캡처 파일명 규약

| 산출물 | 경로 | commit |
|---|---|---|
| 원본 online QXDM | `ODIN2 - Engineer IMS/log/RECAP_<kt\|lgu>/<carrier>_<tc01\|tc02>.hdf` | ❌ 금지(대용량 바이너리) |
| 추출 SIP 텍스트 | `…/RECAP_<kt\|lgu>/<carrier>_<tc01\|tc02>_sip.txt` | ❌ 금지(digest-only, 재생성 가능) |
| local temp expected | `_tmp_tc01.json` / `_tmp_tc02.json` (repo root, §8) | ❌ 금지 |

예: `log/RECAP_kt/kt_tc01.hdf`, `log/RECAP_kt/kt_tc01_sip.txt`, `log/RECAP_lgu/lgu_tc02_sip.txt`.

## 5. TC01 절차 — 등록 override (reboot-load)

**입력값 (3사 동일, `RESULT_2026-06-23.md` 확정 = §8 expected 템플릿과 일치 — 적용 후 readback 으로 확인)**:
Domain=`sktelecom2`(비-routable) · PRID=`4500612345678@ims.mnc006.mcc450.3gppnetwork.org` · Register Expires=`1200` · User Agent=`ALT-test` · Subscribe Expires=`5000` · SIP Timer T1=`1000`.

> ⚠ **CASES 드리프트 — `caseset` 금지(또는 덮어쓰기 필수)**: 런너 `CASES` dict([run_complex_0617.py:350](run_complex_0617.py#L350))는 **06-17 값**을 담고 있어 본 baseline 과 다름 — Domain=`ims.mnc006…`(≠`sktelecom2`) · PRID=`alttest@…`(≠`4500612345678@…`) · User Agent=`ALT-UA-TEST/1.0`(≠`ALT-test`) · SubExp=`3600`(≠`5000`) · SIP T1=`500`(≠`1000`). `caseset CMB_IMS_REG_A/REG_B` 를 쓰면 **digest 가 req-URI/UA 등에서 false MISMATCH**. → 아래 **단건 명령으로 baseline 값 직접 적용**(또는 caseset 후 위 5개 텍스트 필드 덮어쓰기). RegExp 1200 만 동일.

1. **호스트 QXDM** full diag mask 로 로깅 시작(0x156E 포함). 단말 USB 연결 확인.
2. **6필드 적용 (단건 = baseline 값)** — `write <tcid> <tab> <항목substr> <값>` / `mfield <tcid> <tab> <항목substr> <fieldkey> <값>`:
   ```powershell
   $P = "ODIN2 - Engineer IMS\run_complex_0617.py"
   venv\Scripts\python.exe $P write  TC01 IMS "Domain" "sktelecom2"
   venv\Scripts\python.exe $P write  TC01 IMS "PRID" "4500612345678@ims.mnc006.mcc450.3gppnetwork.org"
   venv\Scripts\python.exe $P write  TC01 IMS "Register Expires" "1200"
   venv\Scripts\python.exe $P write  TC01 IMS "User Agent" "ALT-test"
   venv\Scripts\python.exe $P write  TC01 IMS "Subscribe Expires" "5000"
   venv\Scripts\python.exe $P mfield TC01 IMS "SIP Timer" "Timer_T1" "1000"
   ```
   각 항목 Way1 readback 이 위 입력값과 일치하는지 확인(`read TC01 IMS "<항목>"`). 적용 모델 = **reboot-load**(airplane 토글 재등록으론 미반영).
3. **reboot** → 부팅 후 DataPopup '사용' dismiss. ★ **QXDM 로깅이 reboot 가로질러 유지/재개** 되는지 확인(REGISTER 가 부팅 직후 나감).
   ```powershell
   venv\Scripts\python.exe $P reboot
   ```
4. REGISTER + **최종 응답까지 대기**(SKT=404 / LGU+=400 / KT=?). 도달 판정 = 런너 `state`:
   ```powershell
   venv\Scripts\python.exe $P state
   ```
5. **QXDM 로깅 중지 → `.hdf` 저장**(§4 경로) → §7 추출 → §8 digest.

## 6. TC02 절차 — 호 override (runtime, reboot 금지)

**입력값 (3사 동일)**: Session-Expires=`50000` · Traffic Port speech=`50000–50010`(**video 미설정**) · Voice Codec=AMR-WB priority + HD Voice ON · AMR ModeSet=`4`(M2)/AMR-WB ModeSet=`8`(M3) · Video Codec=H.265 priority.

> ⚠ **CASES 드리프트**: `CMB_IMS_SESSION` 은 Session Expires=`1810`(≠`50000`), `CMB_IMS_VIDEO` 는 video port `50020–50030` 설정(본 baseline=**video port 미설정** → SKT on-wire default 7020). 나머지(Voice AMR-WB pref·AMR MS 4·AMR-WB MS 8·HD on·Refresher uac·speech port 50000–50010·H265)는 일치. → 아래 단건으로 baseline 적용(video port 는 설정하지 않음).

1. **호스트 QXDM** 로깅 시작.
2. **호 필드 적용 (단건 = baseline 값)** — ★ **reboot 금지**(reboot 가 NV#73842 Session/RTP·EFS#25038 Refresher 를 환원 → 발신 직전 runtime 기재):
   ```powershell
   $P = "ODIN2 - Engineer IMS\run_complex_0617.py"
   venv\Scripts\python.exe $P radio  TC02 IMS "Voice Codec Priority" "rb_voice_amr_wb_preferred"
   venv\Scripts\python.exe $P write  TC02 IMS "AMR Codec ModeSet" "4"
   venv\Scripts\python.exe $P write  TC02 IMS "AMR-WB Codec ModeSet" "8"
   venv\Scripts\python.exe $P radio  TC02 IMS "HD Voice Setting" "rb_hd_on"
   venv\Scripts\python.exe $P write  TC02 IMS "Session Expires" "50000"
   venv\Scripts\python.exe $P radio  TC02 IMS "Session Refresher" "rb_refresher_uac"
   venv\Scripts\python.exe $P mfield TC02 IMS "Traffic Port" "speechStartPort" "50000"
   venv\Scripts\python.exe $P mfield TC02 IMS "Traffic Port" "speechStopPort" "50010"
   venv\Scripts\python.exe $P radio  TC02 IMS "Video Codec Priority" "rb_codec_h265"
   ```
   (video port 는 미설정 = baseline. RTP Timer 15 는 SDP 비노출이라 선택.)
3. **발신 전 preflight 재확인**(자기번호·캐리어). **음성콜**(VOICE+SESSION 동시 = 같은 INVITE SDP) + **영상콜**(VIDEO):
   ```powershell
   adb -s f2bfcc3c shell am start -a android.intent.action.CALL -d tel:01020954744
   # 영상: ... -d tel:01020954744 --ei android.telecom.extra.START_CALL_WITH_VIDEO_STATE 3
   # 종료: adb -s f2bfcc3c shell input keyevent 6
   ```
   (DUT 발신 타겟 = `01020954744`. 호 도달 판정 = 런너 `state` 의 `mCallState=2`/OFFHOOK.)
4. INVITE(SDP) 캡처 확인 후 **QXDM 중지 → `.hdf` 저장** → §7 → §8.

## 7. QCAT 추출 (0x156E SIP-only)

★ **FOREGROUND 실행** — 백그라운드/detached 는 COM `0x80080005`(첫 기동 DirectPlay 모달이 QCAT 런치 블록 → Skip 또는 1회 설치). 타임스탬프 = UTC(KST=UTC+9).

```powershell
& "scripts\qcat_fast_extract.ps1" -Qmdl "ODIN2 - Engineer IMS\log\RECAP_kt\kt_tc01.hdf" -Codes 0x156E -Out "ODIN2 - Engineer IMS\log\RECAP_kt\kt_tc01_sip.txt"
```
- `.hdf` 도 `-Qmdl` 인자로(OpenLog 가 .hdf/.isf/.qmdl 처리). `-Codes 0x156E` = SIP-only(대용량→수~40KB).
- 여러 호/세그면 같은 `.hdf` 에 다 들어감(SaveAsText 전체). "No Visible Packets" = 조기 캡처(REGISTER/INVITE 전) → QXDM 재로깅.
- fallback(스크립트 차단 시) = inline COM(`PacketFilter.SetAll($false); Set(0x156E,$true); Commit; Process`) — [`RUNTIME_PLAYBOOK.md`](RUNTIME_PLAYBOOK.md) §4.

## 8. digest (편의 채점 — local temp expected)

`ims_sip_digest.py` 는 **쉘 glob 미확장**(argparse 가 경로 그대로 open) → **명시 파일** 또는 PowerShell `(Get-ChildItem <pat>).FullName` 확장. 따옴표 wildcard 금지.

**세션 시 local temp 생성**(아래 템플릿 복사, **커밋 금지**) 후:
```powershell
venv\Scripts\python.exe "scripts\ims_sip_digest.py" "ODIN2 - Engineer IMS\log\RECAP_kt\kt_tc01_sip.txt" --expected _tmp_tc01.json
venv\Scripts\python.exe "scripts\ims_sip_digest.py" "ODIN2 - Engineer IMS\log\RECAP_kt\kt_tc02_sip.txt" --expected _tmp_tc02.json
```

### `_tmp_tc01.json` (REGISTER — 가짜 override 값, SKT 5/5 가 검증한 5필드)
```json
{
  "register": {
    "req_uri": "sip:sktelecom2",
    "expires": "1200",
    "user_agent": "ALT-test",
    "auth_username": "4500612345678@ims.mnc006.mcc450.3gppnetwork.org",
    "realm": "sktelecom2"
  }
}
```
- `register_results`(404/400/?) 는 캐리어별 → **불포함**(§10 표로 판독). SubExp(5000)·SIP T1(1000)은 404/400 즉시거부 시 SUBSCRIBE/재전송 미발생 = 구조적 미관측(NOTE).

### `_tmp_tc02.json` (INVITE SDP — 고신뢰 부분일치만)
```json
{
  "invite": {
    "session_expires": "50000",
    "audio_codecs": "AMR-WB",
    "video_codecs": "H.265",
    "framerate": "24"
  }
}
```
- 부분일치: `session_expires` "50000" ⊂ "50000;refresher=uac" → PASS. **제외(→digest 표 수동판독)**: `audio_port`(speech 50000–50010 range — 부분일치로 정밀검증 불가) · fmtp `mode-set`(=2/3) · `video_res`(orientation 가변) · `video_port`(미설정=default 7020 정상).

## 9. 선택 번들 (주 gap 과 분리 — 있으면 같은 세션에 추가)

- **(a) BTS#16232 HSPA WCDMA** — KT 미인증 USIM 으로 **WCDMA 캠프** → Diag NV#3649(`accessStratumReleaseIndicator`) 실값 read → menu desc "3" / BTS 기대 "5(Rel-9)" 와 대조.
- **(b) BTS#25071 KT RESET-NONPERSIST cycle-2** — IMS Reset → HD OFF write → reboot → 음성콜 SDP(AMR-WB 잔존 = **미적용**) → 재 HD OFF write → reboot → SDP(AMR-NB only = **적용**). 정/역 = SKT/KT 동일(캐리어무관) 확정 보강.
- **(c) TC03 on-wire default** — reset+reboot 후 online QXDM 재등록 default 읽기(caririer별 실 홈도메인·default Session-Expires). 값단위 default 복귀 NOTE 해소용.

## 10. 캐리어 해석 표 (applicability matrix — MISMATCH 읽는 법)

| 필드 | 적용 | KT/LGU+ MISMATCH 해석 |
|---|---|---|
| req-URI · Expires · UA · Auth username/realm | reboot-load | 3사 **반영 기대** → MISMATCH 면 override-load 실패(조사) |
| Voice Codec priority · AMR/AMR-WB mode-set · Session-Expires | runtime | **LGU+ MISMATCH = 프로파일 우선(기대된 결과, 버그 아님)**. SKT 는 반영 |
| Traffic Port(speech) · Refresher · Video Codec priority | runtime | LGU+ 반영(speech port·uac·H265). video port 미설정=default 정상 |

register 결과코드 기대: **SKT 404 cause 4006** / **LGU+ 400** / **KT TBD**(본 세션 확정 대상). 상세 = [`RUNTIME_PLAYBOOK.md`](RUNTIME_PLAYBOOK.md) Override Applicability Matrix.

## 11. 결과 갱신 체크리스트 (세션 후)

- [ ] `RESULT_<날짜>.md` 신규 — KT/LGU+ TC01 req-URI · TC02 SDP 실측, `RESULT_2026-06-23.md` cross-link(시리즈).
- [ ] `RUNTIME_PLAYBOOK.md` Applicability Matrix — KT(·LGU+) `TBD` → 실측값(✓/✗/△, 출처 명시).
- [ ] `BUG_LOG.md` — BTS#25071 cycle-2 수행 시 승격 검토(§4.2 매트릭스).
- [ ] 대용량 `.hdf`/`.qmdl`/`.isf`·파생 `_sip.txt`·`_tmp_*.json` = **commit 금지**. RESULT/PLAYBOOK/BUG_LOG md 만 명시 path stage.

---

### 부록 — 무단말 sanity (digest/expected 메커니즘 확인 / 커밋 0)
```powershell
# §8 tc01 템플릿을 _tmp_tc01.json 으로 복사 후:
venv\Scripts\python.exe "scripts\ims_sip_digest.py" "ODIN2 - Engineer IMS\log\SKTTC01\_sip_seg1.txt" --expected _tmp_tc01.json
```
실측(2026-06-25): exit 0, `req_uri`/`expires`/`user_agent`/`realm` **4필드 PASS** + REGISTER 결과 `NOT_FOUND cause 4006 ×3`(§10 SKT 기대 일치).
★ `auth_username` 만 **MISMATCH** — 디스크의 `SKTTC01` 은 **06-17 런**(PRID `4500512345678@ims.mnc005…`)이고 §8 템플릿은 **06-23 표준값**(`4500612345678@ims.mnc006…`)이라 **capture-버전 차이**(템플릿 결함 아님 / KT·LGU+ 는 §5 단건으로 06-23 값을 적용하므로 5/5 됨). 06-17 자본으로 5/5 를 보려면 template auth_username 을 `4500512345678@ims.mnc005.mcc450.3gppnetwork.org` 로 바꿔 확인. 확인 후 `_tmp_*.json` 삭제.
