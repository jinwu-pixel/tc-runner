# 복합 TC 순차 실행 RUNBOOK — Engineer Mode IMS

- **단말/빌드**: ODIN2 AT-M150 / `Z0612U` (userdebug) · serial `c4324122` · **SKT / LTE / IMS 등록**
- **앱**: `com.ls.teleengineer`
- **범위**: 복합 TC 시트 21건 (7 combo × 3) **sheet 순서 순차 실행**
- **녹화**: 외부 카메라 (단말 내부 녹화 아님) → **reboot 제약 없음**. reboot 포함 TC3 전부 실행 가능
- **판정**: 3-Way (`VERIFY_PROTOCOL.md`). PASS = Way1(UI render) == Way2(모뎀 RESP log) == 의도값 ∧ (영속 scope면 Way3 reboot)
- **상태**: 사용자 "신호" 대기 중. 신호 전 write/reboot **미실행**

---

## 0. 실행 게이트 (사용자 신호 후 1회)

```powershell
$dev = "c4324122"
$root = "ODIN2 - Engineer IMS\evidence\device\combined_run"
New-Item -ItemType Directory -Force -Path $root | Out-Null

# 화면 유지 + 앱 진입 + 게이트 통과 + IMS 탭
adb -s $dev shell svc power stayon true
adb -s $dev shell input keyevent 224                       # WAKEUP
adb -s $dev shell am start -n com.ls.teleengineer/.EngineeringActivity
# "Enter Engineering Mode" 게이트 (bounds [32,504][688,600])
adb -s $dev shell input tap 360 552
Start-Sleep 1
# IMS 탭 (bounds [188,192][364,272])
adb -s $dev shell input tap 276 232
```

> 좌표는 dump로 재확인 후 탭. 버튼(`btn_read`/`btn_write`)·항목 리스트는 **고정좌표 금지 — uiautomator dump에서 bounds 추출 후 탭** (desc 길이로 y 이동).

---

## 1. 재사용 캡처 패턴 (TC마다)

### Read 캡처
```powershell
$tc="<TCID>"; $out="$root\$tc"; New-Item -ItemType Directory -Force $out | Out-Null
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\01_pre.xml"
adb -s $dev logcat -c
# [Read] 탭
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\02_read.xml"
adb -s $dev logcat -d | Select-String -CaseSensitive "QC_RIL_OEM_HOOK:|TeleEngineer:" | Set-Content "$out\03_read_hook.log"
```

### Write 캡처 (EditText는 auto-clear 안 됨 → 반드시 clear)
```powershell
adb -s $dev logcat -c
# et_detail_input focus 탭 → 기존값 제거 → 신규 입력 → 입력값 검증
adb -s $dev shell input keyevent 123          # MOVE_END
adb -s $dev shell input keyevent 67 67 67 67 67 67 67 67   # DEL ×8 (필요 수만큼)
adb -s $dev shell input text "<NEWVAL>"
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\04_input.xml"   # et_detail_input==NEWVAL 검증 후 진행
# [Write] 탭 → 앱 자동 read-back
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\05_post_write.xml"
adb -s $dev logcat -d | Select-String -CaseSensitive "QC_RIL_OEM_HOOK:|TeleEngineer:" | Set-Content "$out\06_write_hook.log"
```

**Way2 마커**: NV 항목 = `[QCRIL_JAVA] readResp OK … value=N` / EFS 항목 = `[INI_READ]`·`[INI_WRITE] /efsprofiles/overideconfig … result=0`.
**Way1 anchor**: `tv_detail_value` + `tv_detail_status`(=OK) (resource-id anchored, 헐거운 match 금지).

### Reboot 패턴 (Way3)
```powershell
adb -s $dev reboot
# (부팅 대기) → ODIN2 DataPopup 처리
adb -s $dev wait-for-device
Start-Sleep 25
adb -s $dev shell svc power stayon true
adb -s $dev shell input keyevent 224
adb -s $dev shell wm dismiss-keyguard
# OdinConfirmDataDialogActivity "사용" (있으면)  → dump로 bounds 확인 후 탭
adb -s $dev shell am start -n com.ls.teleengineer/.EngineeringActivity
adb -s $dev shell input tap 360 552   # 게이트
adb -s $dev shell input tap 276 232   # IMS 탭
```

---

## 2. 순차 실행 표 (sheet 순서)

| # | TC ID | 항목 | 동작 | Way2 marker | PASS 기준 | reboot |
|--:|---|---|---|---|---|:--:|
| 1 | CMB_NV73842_01 | RTP Timer / Session Expires | 둘 다 Read | `[QCRIL_JAVA]` NV#73842 | RTP=10·Session=1800, status OK | — |
| 2 | CMB_NV73842_02 | 동 | Session=1810 W→RTP R→RTP=15 W→Session R | `[QCRIL_JAVA]` | 격리: Session=1810 중 RTP=10 보존, RTP=15 중 Session=1810 보존 | — |
| 3 | CMB_NV73842_03 | 동 | (RTP=15·Session=1810) **reboot**→Read→복원(10/1800) | `[QCRIL_JAVA]` | reboot 후 15·1810 영속 → 복원 | **R** |
| 4 | CMB_NV73846_01 | AMR / AMR-WB ModeSet | 둘 다 Read | `[QCRIL_JAVA]` NV#73846 | 둘 다 0(0x00) | — |
| 5 | CMB_NV73846_02 | 동 | AMR=4 W→AMR-WB R→AMR-WB=8 W→AMR R | `[QCRIL_JAVA]` | 격리: AMR=4 중 AMR-WB=0, AMR-WB=8 중 AMR=4 | — |
| 6 | CMB_NV73846_03 | 동 | (AMR=4·WB=8) **reboot**→Read→복원(0/0) | `[QCRIL_JAVA]` | reboot 후 영속 → 복원 | **R** |
| 7 | CMB_AUDIOPROFILE1_01 | HD Voice / Voice Codec | 둘 다 Read (라디오) | `[INI_READ]` AudioProfile1 | HD=ON, Voice=Default | — |
| 8 | CMB_AUDIOPROFILE1_02 | 동 | HD=OFF W→Voice R→Voice=EVS W→HD R | `[INI_WRITE]` | 커플링 일관. **★GAP후보**: EVS-only인데 HD='ON' 표기 기록 | — |
| 9 | CMB_AUDIOPROFILE1_03 | 동 | HD=ON·Voice=Default **복원 write**→Read | `[INI_WRITE]` | 복원 확인 (reboot 불요; 실패 시 IMS Reset+reboot fallback) | (opt) |
| 10 | CMB_RESET_01 | RTP(NV)·RegExp(EFS) | RTP=15 W·RegExp=36000 W→Read | `[QCRIL_JAVA]`+`[INI_WRITE]` | 둘 다 readback 일치 = 런타임 커밋 | — |
| 11 | CMB_RESET_02 | IMS Reset to Default | Reset 실행→Read→Reset후 RTP=15 재W→Read | reset status / 양 marker | Reset후 RTP=10·RegExp=(not configured); Reset후 write도 result=0+일치(no-op 아님) | — |
| 12 | CMB_RESET_03 | 동 | (Reset후 write상태) **reboot**→Read→대조 | 양 marker | Reset+reboot → RTP=10·RegExp 환원 (MBN). 대조군(reset없음)=15·36000 영속 | **R** |
| 13 | CMB_SIPTIMERS_01 | Register / Subscribe Expires | 둘 다 Read | `[INI_READ]` SIPConfig | 둘 다 (not configured) | — |
| 14 | CMB_SIPTIMERS_02 | 동 | RegExp=36000 W→SubExp R→SubExp=3600 W→RegExp R | `[INI_WRITE]` | 격리: RegExp=36000 중 SubExp 보존, 역도 | — |
| 15 | CMB_SIPTIMERS_03 | 동 | (RegExp=36000·SubExp=3600) **reboot**→Read→복원 | `[INI]` | reboot 후 영속 → IMS Reset 복원 | **R** |
| 16 | CMB_REGPARAMS_01 | Domain / PRID | 둘 다 Read | `[INI_READ]` ParamConfig | 둘 다 (not configured), SKT 기대 domain=sktelecom2 | — |
| 17 | CMB_REGPARAMS_02 | 동 | Domain=sktelecom2 W·PRID W→Read | `[INI_WRITE]` | Domain 반영. PRID는 reboot 후 반영(BTS#25066) | — |
| 18 | CMB_REGPARAMS_03 | 동 | (Domain·PRID) **reboot**→Read→복원 | `[INI]` | reboot 후 유지(PRID 반영) → 복원 | **R** |
| 19 | CMB_MEDIAPROFILE_01 | Voice / Video Codec | 둘 다 Read | `[INI_READ]` ImsMediaProfile | Voice=Default, Video=H263_0;H264_0;H265_0 | — |
| 20 | CMB_MEDIAPROFILE_02 | 동 | Voice=EVS W→Video R→Video=H.264 W→Voice R | `[INI_WRITE]` | 프로파일 격리: Voice=EVS 중 Video 보존, 역도 | — |
| 21 | CMB_MEDIAPROFILE_03 | 동 | (Voice=EVS·Video=H264) **reboot**→Read→**최종 복원(IMS Reset+reboot)** | `[INI]` | reboot 후 영속 → 전역 baseline 복원 | **R**(+복원R) |

**reboot 지점 = 6 (강제) + 9·21 복원 옵션**. TC1/TC2 14건은 reboot 없음.

---

## 2.5 실행 분할 — 비-재부팅 서브셋 (2026-06-16 사용자 결정)

**사용자 결정**: 재부팅 케이스는 사용자가 직접 손으로 수행. Claude는 **비-재부팅 케이스만 실행**.

추가 제약: `CMB_RESET_02`는 `adb reboot`이 없지만 **전역 `IMS Reset to Default`**(모든 EFS override 런타임 clear) → 내 배치 중간 실행 시 뒤 combo staged 값 파괴. ∴ **RESET combo 전체(01·02·03)는 사용자 수동**으로 분류.

### 내 배치 — 13건 (Read + 필드격리 Write, reset/reboot 없음, sheet 순서)

| 순 | TC ID | 동작 | 종료 시 staged 상태 (사용자 reboot용) |
|--:|---|---|---|
| 1 | CMB_NV73842_01 | RTP·Session Read | — |
| 2 | CMB_NV73842_02 | 필드격리 W | **RTP=15·Session=1810** |
| 3 | CMB_NV73846_01 | AMR·AMR-WB Read | — |
| 4 | CMB_NV73846_02 | 필드격리 W | **AMR=4·AMR-WB=8** |
| 5 | CMB_AUDIOPROFILE1_01 | HD·Voice Read | — |
| 6 | CMB_AUDIOPROFILE1_02 | 커플링 W (★GAP후보=EVS-only에 HD ON) | Voice=EVS |
| 7 | CMB_AUDIOPROFILE1_03 | 복원 W (reboot 없음) | HD=ON·Voice=Default |
| 8 | CMB_SIPTIMERS_01 | RegExp·SubExp Read | RegExp=(not configured) clean |
| 9 | CMB_SIPTIMERS_02 | 필드격리 W | **RegExp=36000·SubExp=3600** |
| 10 | CMB_REGPARAMS_01 | Domain·PRID Read | — |
| 11 | CMB_REGPARAMS_02 | W | **Domain=sktelecom2·PRID** |
| 12 | CMB_MEDIAPROFILE_01 | Voice·Video Read | — |
| 13 | CMB_MEDIAPROFILE_02 | 필드격리 W | **Voice=EVS·Video=H264** |

> 충돌 점검: RESET combo 제외로 `CMB_SIPTIMERS_01`의 RegExp baseline read가 clean(이전엔 RESET_01의 RegExp=36000 write가 오염). 13건 **collision-free**, 재정렬 불필요.

### 사용자 수동 — 8건 (reboot/reset)

| TC ID | pre-reboot 상태 (내 배치가 남김) | 복원 방식 |
|---|---|---|
| CMB_NV73842_03 | RTP=15·Session=1810 ✓staged | **per-field** write (RTP=10·Session=1800) — 안전 |
| CMB_NV73846_03 | AMR=4·AMR-WB=8 ✓staged | **per-field** write (0·0) — 안전 |
| CMB_SIPTIMERS_03 | RegExp=36000·SubExp=3600 ✓staged | **전역 IMS Reset+reboot** |
| CMB_REGPARAMS_03 | Domain=sktelecom2·PRID ✓staged | **전역 IMS Reset+reboot** |
| CMB_MEDIAPROFILE_03 | Voice=EVS·Video=H264 ✓staged | **전역 IMS Reset+reboot** (최종 teardown) |
| CMB_RESET_01/02/03 | (RESET_01에서 RTP=15·RegExp=36000 직접 write) | 전역 reset → reboot |

**사용자 수동 순서 권고** (staging 보존):
1. **먼저 per-field 복원 케이스**: `CMB_NV73842_03`, `CMB_NV73846_03` (복원이 NV 개별 write → 다른 combo EFS staged 미교란).
2. **다음 전역-reset 복원 EFS 케이스**: `CMB_SIPTIMERS_03` / `CMB_REGPARAMS_03` / `CMB_MEDIAPROFILE_03`. ⚠ **한 케이스의 전역 IMS Reset이 나머지 EFS combo staged 값을 전부 clear** → 두 번째 EFS 케이스부터는 reboot 직전 **해당 combo 2값 재-write** 후 진행 (또는 MEDIAPROFILE_03을 마지막 = 최종 teardown).
3. **마지막 RESET combo**(01·02·03): 전역 reset 거동 자체가 목적 → 맨 끝.

> 평범한 reboot은 normal write를 영속(Phase C/D). 전역 IMS Reset+reboot만 MBN default 환원. 영상 = 외부 카메라이므로 reboot 자유.

---

## 3. 실행 순서 위험·주의

1. **전역 IMS Reset 간섭**: combo 4(RESET)의 `IMS Reset to Default`는 **모든 EFS override를 clear**한다. sheet 순서상 RESET이 SIPTIMERS/REGPARAMS/MEDIAPROFILE보다 **앞** → 이들 combo의 TC1 시작 기대값이 모두 `(not configured)`/`Default`이므로 **clean slate로 정합**(충돌 없음). 순서 유지 OK.
2. **AudioProfile1 공유**: combo 3(AUDIOPROFILE1)·combo 7(MEDIAPROFILE)가 동일 `Voice Codec(AudioProfile1)` 접촉. combo 4 RESET이 사이에서 초기화 → combo 7은 독립 시작.
3. **PRID reboot 반영**(BTS#25066): REGPARAMS_02 PRID write는 reboot(_03) 전 미반영 정상.
4. **속도 옵션(선택)**: TC3·TC6(NV73842/NV73846 둘 다 NV·정상-write-영속)을 **1회 reboot로 병합** 가능(2건 write 후 1 reboot로 양쪽 readback). reboot 6→5. 단 doc 1:1 정합 깨짐 → 외부 리뷰 매칭 위해 **기본=strict 순서**.
5. EditText auto-clear 안 됨 / 진입 직후 focus 레이스 / 화면 timeout → §1·게이트 패턴 준수.

---

## 4. 증거 레이아웃 (이 run)

```
evidence/device/combined_run/
  <TCID>/  01_pre.xml 02_read.xml 03_read_hook.log [04_input.xml 05_post_write.xml 06_write_hook.log] [07_post_reboot.xml]
  RUN_LEDGER.md          # 21건 Way1/Way2/Way3 결과 + boot_id join
```

- 외부 카메라 영상 = 화면 거동 (사용자 보관). offline log(있으면)와 boot_id+KST/UTC로 cross-join.
- xlsx SKT 결과 갱신은 **실행 후** openpyxl 직접 편집(생성기 재실행 금지).

---

## 5. 실행 후 정리

- 최종 상태 = IMS Reset + reboot로 MBN baseline 복귀 (TC21 포함).
- `RUN_LEDGER.md` 작성 → xlsx SKT 결과/비고 갱신(직접 편집) → 사용자 보고.
- commit/push는 명시 승인 시까지 보류.
