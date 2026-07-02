# BUG_LOG — ODIN2 Engineer Mode IMS

- **단말**: ODIN2 AT-M150 / `AT-M150Z0612U` · **앱**: `com.ls.teleengineer` (Engineer Mode → IMS/GENERAL/LTE)
- **carrier**: SKT (45005), LTE · **방법**: readback-only (Read 비파괴, Write→re-Read 후 IMS Reset/explicit 복원)
- 상세값·증거 = `RESULT_2026-06-16.md` · BTS 스펙 = `BTS_TICKET_SPECS.md` · 매칭 = `APP_BTS_MATCH.md`

## 요약

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| BTS#25071 RESET-NONPERSIST | IMS Reset to Default | OBSERVED | OPEN | 글로벌 IMS Reset(auto-mode 전환) 후 manual write는 런타임 커밋되나 1회 reboot로 MBN default 환원(비영속). reset 없는 write는 영속 → reset 특이 | C2·C5·Phase B/C/D | offline_session_ledger.md, offline_buggap*/control2*_logcat |
| BTS#19410 HDV-EVS | HD Voice ↔ Voice Codec (AudioProfile1) | OBSERVED | OPEN | Voice Codec=EVS override 시 HD Voice가 EVS-only(AMR-WB 없음)인데 "ON" 표기 | C1 | c1_hd_after_voiceEVS.png |
| BTS#16232 HSPA-DEF | HSPA Setting (GENERAL/WCDMA) | SUSPECT | OPEN | 메뉴 desc "Default 3" vs BTS 기대 default 5(Rel-9) 불일치. 실 NV 미취득(LTE 캠프) | — | extra_HSPA_*.png |
| BTS#19429 SIP-ENUM | SIP Timer enumeration | — | NOTE | swipe-기반 항목 enumeration 불안정(16/15/12 들쭉) — SIP Timer "부재"는 스캔 아티팩트 가능성, 결손 단정 불가 | — | ims_tab2.xml |

---

## BTS#25071 RESET-NONPERSIST — IMS Reset 후 manual write 비영속 (1회 reboot로 환원)

- **기능 영역**: IMS Engineer Mode / IMS Reset to Default (PDC action)
- **진단 상태**: OBSERVED (SKT 1 carrier — reset 특이성은 control 정/역 재현으로 직접 입증, 단 n=1·모뎀층 `.qmdl` 미생성)
- **이슈 상태**: OPEN (버그 vs 의도 = 개발 판단)
- **단말 / 앱**: ODIN2 AT-M150 Z0612U / com.ls.teleengineer
- **요약**: 글로벌 IMS Reset(`deactivateConfigs(0)`+`enableAutoMode(0/1)=true`)이 config를 MBN-managed(auto)로 전환. 이 상태의 manual write는 **런타임 커밋됨**(NV `writeNvField result=0`+readback 일치 / EFS `[INI_WRITE] result=0`+readback 일치) — silent no-op 아님. 단 reset 직후 **1회 reboot 시 MBN reload가 override를 덮어** NV는 MBN default, EFS override는 `(not configured)`로 환원. reset 안 한 동일 write는 reboot survive → **비영속은 reset 특이**.
- **기대 결과**: reset 후라도 manual write가 reboot를 가로질러 유지 (또는 앱이 "reset 후 1회 reboot까지 비영속"을 명시).
- **실제 결과**: post-reset RTP Write 15 → readback 15(커밋) → reboot 후 10(MBN default). post-reset RegExp Write 36000 → readback 36000(커밋) → reboot 후 `(not configured)`. 대조 control(reset 없이): RTP 15·RegExp 36000 → reboot 후 둘 다 유지.
- **재현 절차**:
  1. IMS Reset to Default 실행 (`deactivate`+`enableAutoMode`).
  2. (reboot 없이) NV/EFS write (RTP=15 / RegExp=36000) → status OK + readback 일치(런타임 커밋 확인).
  3. **reboot** → RTP=10(MBN default) / RegExp=`(not configured)` = override 미영속.
  4. 대조: reset 없이 동일 write → reboot → 값 유지(영속). ∴ reset 특이.
- **증거**: `evidence/device/offline_session_ledger.md` Phase B/C/D + `offline_buggap_logcat.txt`·`offline_buggap_postreboot_logcat.txt`·`offline_control2_pre_logcat.txt`·`offline_control2_postreboot_logcat.txt`. hook: NV=`[QCRIL_JAVA]`, EFS=`[INI_READ/INI_WRITE] /efsprofiles/overideconfig`.
- **관련 TC**: Phase 2 C2(NV#73842 격리) · C5(IMS Reset) · Phase B/C/D control.
- **연결**: BTS#25049("reset이 default 복원 대신 config 삭제→수정") 동종 / #25066·#19581("reboot 필요") 정합.
- **CONFIRMED 승격 잔여요건 (§4.2)**: KT/LGU+ 2 carrier × 2 조건 + auto-mode 직접 관측 + `.qmdl` 모뎀층 독립확인. 현 SKT 단일·n=1·RIL 채널 비독립 → OBSERVED.
- **정정 이력**: 2026-06-16 오프라인로깅+영상 재검증 — 이전 "silent no-op(Write 무반영)" 정정: write는 런타임 커밋됨, 실제 성격=reset-induced persistence loss(비영속). 원 pre-reboot "무반영" 관찰은 입력 아티팩트(EditText auto-clear 안 됨·focus 레이스) 추정.

## BTS#19410 HDV-EVS — HD Voice ON 표기 vs EVS-only 프로파일

- **기능 영역**: IMS / HD Voice Setting ↔ Voice Codec Priority (EFS `…AudioProfile1` 동일키)
- **진단 상태**: OBSERVED
- **이슈 상태**: OPEN
- **단말 / 앱**: ODIN2 AT-M150 Z0612U / com.ls.teleengineer
- **요약**: Voice Codec Priority=EVS Write 시 HD Voice Read가 `ON (custom: EVS_0_126;EVS_1_127)`. BTS#19410 정의(HD Voice ON = AMR-WB+AMR)와 불일치 — AMR-WB 없는 EVS-only 프로파일인데 "ON".
- **기대 결과**: HD Voice ON ⇔ AMR-WB+AMR 프로파일.
- **실제 결과**: EVS-only override 시에도 ON 표기. 앱이 `(custom: …)`로 disclose하나 ON/OFF 이진 표기가 Voice Codec override 시 의미 모호.
- **재현 절차**: C1 Step1 — Voice Codec=EVS Write → HD Voice Read=`ON (custom: EVS_0_126;EVS_1_127)`. (공유키 일관성·데이터 무손상은 OK — GAP은 표기 의미.)
- **증거**: `evidence/device/c1_hd_after_voiceEVS.png`.
- **관련 TC**: Phase 2 C1 (AudioProfile1 25043↔19410).
- **정정 이력**: —

## BTS#16232 HSPA-DEF — 메뉴 default 3 vs BTS 기대 5

- **기능 영역**: GENERAL / HSPA Setting (WCDMA, NV#3649 accessStratumReleaseIndicator)
- **진단 상태**: SUSPECT (메뉴 텍스트 불일치 관찰, 실 NV 미취득)
- **이슈 상태**: OPEN
- **요약**: 단말 메뉴 desc `"Default: 3 (for SKT, KT & LGU)"` ↔ BTS#16232 기대 default `5 (Rel-9)`. Diag read는 SKT/LTE 상태에서 미완(`…`) — WCDMA 캠프 필요.
- **기대 결과**: accessStratumReleaseIndicator default = 5 (Rel-9).
- **실제 결과**: 메뉴 desc는 3 명기. 실 NV 값 미취득.
- **재현 절차 (잔여)**: WCDMA 캠프(KT 미인증 USIM) → HSPA Setting Diag read로 실값 확인. (`reference_wcdma_test_sim` 참조.)
- **증거**: `evidence/device/extra_HSPA_{Setting,detail,read}.png` (메뉴 desc + Diag read 미완), RESULT §BTS 커버리지 마감.
- **관련 TC**: —
- **정정 이력**: —

## BTS#19429 SIP-ENUM — SIP Timer enumeration 불안정 (NOTE)

- **기능 영역**: IMS / SIP Timer (NV `ims_sip_config`)
- **진단 상태**: — · **이슈 상태**: NOTE (이슈 아님 — 도구 신뢰도)
- **요약**: swipe-기반 IMS 항목 enumeration이 16/15/12로 들쭉, post-reboot 스캔은 직접 조작 확인된 Video/Voice Codec·IMS Reset까지 누락. SIP Timer "부재"는 스캔 아티팩트 가능성 높음 — 실제 결손 단정 불가.
- **잔여**: 수동 저속 스크롤 enumeration으로 IMS 항목 완전성 재확인 (Phase 1 커버리지 신뢰도 보강).
- **증거**: `ims_tab2.xml`(초기 덤프 desc 1회 포착, 타이틀 클립).
- **정정 이력**: 초기 OBSERVED(부재) → `inconclusive` 하향 (2026-06-16, swipe-scan 불안정 root 확인).

---

## 세션 결과 (2026-06-16)

- **실행일**: 2026-06-16 · **단말**: ODIN2 AT-M150 Z0612U · **앱**: com.ls.teleengineer
- **범위**: IMS 탭 SKT baseline 관찰(Phase 1) + 복합 Write 검증 readback-only(Phase 2 C1~C3·C5)
- **manual evidence observed**: IMS 13항목 현재값 + Traffic Port 5필드.
- **신규 발견**: RESET-NONPERSIST(BUG-GAP observed) · HDV-EVS(GAP, OBSERVED) · HSPA-DEF(SUSPECT) · SIP-ENUM(NOTE).
- **격리 검증 OK**: C1 AudioProfile1 공유키 일관 / C2 NV#73842 필드 격리 / C3 NV#73846 subfield 격리.
- **변경·정정**: 없음 (Write 후 IMS Reset/explicit 복원, baseline 청결).
- **다음 확인 항목**: ① RESET-NONPERSIST CONFIRMED 승격(KT/LGU+ 매트릭스 + auto-mode 직접 관측 + `.qmdl`) ② HSPA WCDMA read ③ SIP Timer 수동 enumeration ④ User Agent BTS#19420 본문 확인.
