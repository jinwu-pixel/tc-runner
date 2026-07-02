# Engineer Mode IMS — 3-Way Ground Truth 검증 프로토콜

- **단말/빌드**: ODIN2 AT-M150 / `Z0612U` (userdebug) · **앱**: `com.ls.teleengineer`
- **목적**: Engineer Mode IMS 항목의 Read/Write 결과에 **객관적 PASS/FAIL 판정 근거**를 부여한다. 단말 UI의 `status=OK` 표시 단독으로는 모뎀 반영을 신뢰할 수 없다(§4.2 3-way).
- **확정일**: 2026-06-16 (SKT / LTE, readback-only). 근거 트레이스 = `evidence/device/rtp_timer_*_19581.log|xml`.

---

## 0. 아키텍처 사실 (왜 파일 dump가 불가능한가)

IMS 항목의 backing store(`/efsprofiles/overideconfig`, `/nv/item_files/ims/IMSVoiceDynamicConfig` 등)는 **AP 파일시스템에 마운트된 실파일이 아니다.** 모뎀 내부 EFS/NVRAM이며, 앱은 **QcRilHook(RIL OEM Hook)** 으로 AP↔모뎀 통신을 거쳐 읽고 쓴다.

- 증거: `find / -name "*overideconfig*"` 무결과.
- 결과: `cat`/`od -t x4 /nv/item_files/...` 직접 덤프 = **전부 `No such file`. 폐기.**
- 단말 메뉴가 표기하는 NV 경로/필드명은 **모뎀측 심볼**이다(예: `IMSVoiceDynamicConfig` / `rtpLinkAlivenessTimer`). AP 경로로 오해 금지.

---

## 1. 3-Way 판정축 (이 아키텍처 확정판)

| 축 | 관측원 | 도구 | PASS 조건 |
|---|---|---|---|
| **Way1 — UI 렌더** | `tv_detail_value`(Read 값) + `tv_detail_status`(OK/실패) | `uiautomator dump` | 렌더값 == 의도값 ∧ status=OK |
| **Way2 — 모뎀 RESP** | `QC_RIL_OEM_HOOK [QCRIL_JAVA] readResp OK … value=N` (+ raw hex) | `logcat -c`→동작→`logcat -d` | 모뎀 반환값 == 의도값 |
| **Way3 — 영속/격리** | reboot 후 재Read(또는 IMS Reset→MBN default) · 인접필드 불변 | dump 전/후 비교 | 비휘발 커밋 / 필드 격리 |

**PASS = Way1 == Way2 == 의도값, ∧ (영속성이 scope면 Way3).**

### 축별 핵심 주의

- **Way1**: status/value는 **persistent TextView**(Toast 아님) → dump에 잡힌다(2026-06-16 확인). 단 assert는 **resource-id anchor 필수** — `Select-String "10"` 류 헐거운 매칭 금지(bounds/id/timestamp 위양성).
- **Way2**: 이 userdebug 빌드의 `QCRIL_JAVA` 로그는 **모뎀 REQ/RESP 페이로드 + 디코드 값**을 찍는다 → 단순 전송 증명이 아니라 **모뎀 반환값 자체**가 로그에 남는다. `logcat -c`로 비우고 동작 직후 `logcat -d`, `serial=`로 트랜잭션 격리.
  - **caveat(빌드 의존)**: 이 verbose 로그는 userdebug 전제. user/production 빌드에서 마스킹되면 Way2는 **NOTE(보강)로 강등**되고 PASS는 Way1+Way3로 판정.
  - **caveat(채널 비독립)**: Way2는 UI Read와 **같은 RIL 채널** → 앱 렌더/파싱 버그는 잡지만 채널 자체 위양성은 못 잡는다. **채널 독립 커밋 증명은 Way3(reboot)** 가 담당. 완전 독립 필요 시 QXDM/diag(별도 채널, `reference_qcat_offline_diag_workflow`).
- **Way3**: reboot는 외부행위(승인 필요) + 부팅 시 ODIN2 DataPopup(`OdinConfirmDataDialogActivity`) 포커스 선점 → "사용"으로 닫고 진입.

---

## 2. Write 반영 discriminator (커밋 vs no-op 판별)

Write는 **write → 즉시 자동 read-back**을 수행한다. 따라서 "Write가 OK인데 실제 무반영"인 silent no-op이 **로그 레벨에서** 드러난다:

```
정상:   writeNvField result: 0  →  callback success=true msg=Written: X  →  readResp OK … value=X   (X==X)
BUG-GAP: callback success=true msg=Written: X  →  readResp OK … value=Y   (Y≠X)   또는  writeNvField result≠0
```

- **1차 탐지 = 로그**(reboot 불필요), **최종 확정 = reboot 후 복원 거동**.
- 본 세션 IMS Reset 후 재검증(오프라인로깅): write는 `result=0`+readback 일치 = **런타임 커밋**(no-op 아님). discriminator는 커밋 확정에 사용됨. 실제 BUG-GAP = post-reset write가 1회 reboot로 환원(비영속, reset 특이) → `IMS_RESET_04` RESET-NONPERSIST. 상세 = `evidence/device/offline_session_ledger.md` Phase B/C/D.

---

## 3. 캡처 절차 (PowerShell, 수정 확정판)

```powershell
$dev = "c4324122"; $tc = "IMS_RTP_03"; $out = "evidence\$tc"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# [Pre] 변경 전 Read 화면 + logcat clear
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\01_pre.xml"
adb -s $dev logcat -c

# --- 단말 UI: New Value 입력 → Write → (앱이 자동 read-back) ---
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\02_post_write.xml"
adb -s $dev logcat -d | Select-String -CaseSensitive "QC_RIL_OEM_HOOK:|TeleEngineer:" > "$out\03_hook.log"

# --- (영속성 scope면) reboot 후 재진입 → Read : Way3 ---
adb -s $dev shell uiautomator dump /sdcard/ui.xml; adb -s $dev pull /sdcard/ui.xml "$out\04_post_reboot.xml"
```

### 판정 규칙

- **Way1**: `02_post_write.xml`에서 `tv_detail_value` / `tv_detail_status` 노드의 `text=`를 추출(anchored).
- **Way2**: `03_hook.log`의 `readResp OK … value=N` 과 의도값 대조. (필터는 `-CaseSensitive`로 — 패키지명 `teleengineer`와 앱 로그태그 `TeleEngineer:` 구분.)
- **버튼 좌표 주의**: `btn_read`/`btn_write`는 desc 길이에 따라 y가 이동(짧은 desc → y 위로). **고정좌표 금지, dump에서 bounds 추출 후 탭.**

---

## 4. 근거 트레이스 (2026-06-16, RTP Timer[19581] / SKT)

**Read** — `evidence/device/rtp_timer_read_19581.log`:
```
[QCRIL_JAVA] readReq:  path=…/IMSVoiceDynamicConfig, nvId=73842, field=rtpLinkAlivenessTimer, type=2
[QCRIL_JAVA] readResp OK, field=rtpLinkAlivenessTimer, type=2, len=4, value=10 (0x0000000A)
TeleEngineer: RtpTimer readNvField: 10
```
UI: `tv_detail_value='10'`, `tv_detail_status='OK'`. → **Way1 10 == Way2 10 == SKT 기대 10**(fix 0→10 탑재). `manual evidence observed`.

**Write(멱등 10)** — `evidence/device/rtp_timer_write_19581.log`:
```
TeleEngineer: RtpTimer writeNvField result: 0
TeleEngineer: rtp_timer callback: success=true msg=Written: 10
[QCRIL_JAVA] readResp OK, field=rtpLinkAlivenessTimer, len=4, value=10   ← 자동 read-back 일치
```

부수: NV#73842는 `rtpLinkAlivenessTimer`(type2/len4) + `sessionExpires`(type1/len2) **두 필드 보유** → RTP↔Session 격리(C2) 전제가 로그로 명시됨.

---

## 5. 적용 범위

- 표준 Read/Write 항목(NV/EFS) 전체에 Way1+Way2 적용. RadioGroup·Traffic Port(멀티필드)·IMS Reset(action)은 Way2 로그 필드명만 항목별로 상이.
- carrier matrix(SKT→KT→LGU+) 전 구간 동일 프로토콜. carrier별 기대값 차이(예: Session Expires default 360 vs 단말 1800)는 USIM/MCFG 요인 → 값 대조 시 carrier 기대값 기준.

연관: CLAUDE.md §4.2 · `feedback_diagnostic_3way_ground_truth` · `feedback_scope_note_and_pass_blockers` · `reference_qcat_offline_diag_workflow`
