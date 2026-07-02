# Tele Engineer 앱 항목 ↔ BTS 이슈 매칭 + 확인 현황

- **단말/빌드**: ODIN2 AT-M150 / `Z0612U` · **앱**: `com.ls.teleengineer`
- **확인일**: 2026-06-16 (carrier = **SKT** / LTE, readback-only 관찰)
- **BTS**: ZenTao `http://10.5.103.101:9080/bug-view-<ID>.html`
- **확인 어휘**: `manual evidence observed`(Read 관찰값) · `BUG-GAP observed` · `inconclusive`(미확정)

## IMS 탭 — 앱 항목 ↔ BTS

| 앱 항목 | BTS | BTS 상태 | 인터페이스 | 2026-06-16 확인(SKT) |
|---|---|---|---|---|
| User Agent | **19420** | (미추출) | NV#69689 `ims_user_agent` | Read=`TTA-VoLTE/3.0 AT-M150S/Z0612U …SKT` ✓ |
| Subscribe Expires | 25036 | Resolved | EFS `[SIPConfig:StandardTimers] SipSubscribeValue` | Read=`(not configured)` |
| Session Expires | 19425 | Resolved | NV#73842 `sessionExpires` | Read=`1800` (BTS default 360 — USIM/MCFG별) |
| Register Expires | 25035 | Resolved | EFS `[SIPConfig:StandardTimers] SipRegValue` | Read=`(not configured)` |
| Domain | 25059 | Resolved | EFS `[ParamConfig:RegistrationDefaultParams] domainName` | Read=`(not configured)` (SKT 기대 `sktelecom2`) |
| PRID | 25066 | Resolved | EFS `[ParamConfig:RegistrationDefaultParams] privateURI` | Read=`(not configured)` |
| Video Codec Priority | 25049 | Resolved | EFS `[QIPCALL:ImsMediaProfileConfig] VideoProfile1` | Read=`H263_0;H264_0;H265_0` / radio=Default |
| Voice Codec Priority | 25043 | Resolved | EFS `…AudioProfile1` | Read=`(not configured)` / Default · **C1 검증** |
| AMR Codec ModeSet | 19443 | Resolved | NV#73846 `amrModeSet` | Read=`0 (0x00)` · **C3 검증** |
| AMR-WB Codec ModeSet | 19445 | Resolved | NV#73846 `amrWbModeSet` | Read=`0 (0x00)` · **C3 검증** |
| RTP Timer | 19581 | Resolved | NV#73842 `rtpLinkAlivenessTimer` | Read=`10` = SKT 기대값 일치 ✓ · **C2 검증** |
| Session Refresher | 25038 | Resolved | EFS `[QIPCALL:ImsVoiceSessionTimerConfig] sessionRefresherType` | Read=`Default (not configured)` / radio=Default |
| HD Voice Setting | 19410 | Resolved | EFS `…AudioProfile1` | Read=`ON` / radio=ON · **C1 검증** |
| Traffic Port | 19593 | Resolved | NV#73845 `IMSRTPDynamicConfig` | Read=Ver0 / speech `7010·7012` / video `7020·7022` |
| IMS Reset to Default | 25071 | Resolved | PDC (action) | **BUG-GAP observed** — reset 후 manual write 비영속(1회 reboot로 환원, reset 특이) · RESET-NONPERSIST |
| SIP Timer | 19429 | Resolved | NV `ims_sip_config` (T1/T2/T4/TA~TK) | 메뉴 존재 **inconclusive**(swipe-스캔 불안정), 값 미취득 |

## GENERAL 탭

| 앱 항목 | BTS | 인터페이스 | 확인 |
|---|---|---|---|
| Auto Answer (QcRilHook) | — (BTS 없음) | QcRilHook | 미Read |
| HSPA Setting | **16232** (Resolved) | NV#3649 `accessStratumReleaseIndicator` (Diag#3649) | Diag read LTE에서 미완 `…` (WCDMA 필요 추정) · **메뉴 desc "default 3" vs BTS 기대 5(Rel-9) 불일치 flag** |

## LTE 탭

| 앱 항목 | BTS | 인터페이스 | 확인 |
|---|---|---|---|
| LTE CDRX FGI | **18582** (**Active**) | EFS `…/rrc/cap/fgi` (Hook) FGI#4=0·#5=0 | Read=`FGI = (not set)` / OFF (default) |
| LTE ROHC | **18582** (**Active**) | EFS `…/rrc/rohc_supported` (Hook) 0→1 | Read=`ROHC = (not set)` / OFF (default) |

## 요약

- **앱 IMS 항목 16종 중 BTS 등록 16종 전부 매칭** (User Agent 19420은 BTS 본문 미추출 — 확인 필요).
- **오늘 Read 관찰 = 13항목**(IMS 표준/radio). Traffic Port 5필드 포함. CDRX/ROHC 포함 시 15.
- **미취득/미확정**: HSPA(Diag, WCDMA 필요), SIP Timer(메뉴 존재 inconclusive), User Agent BTS 19420 본문.
- **검증 완료(복합)**: C1(AudioProfile1 25043↔19410), C2(NV#73842 19581↔19425), C3(NV#73846 19443↔19445), BUG-GAP(25071).
- **개발 보고 후보**: ① IMS Reset 후 Write "OK" 오표기(reboot 전), ② HSPA default 3 vs 5, ③ User Agent BTS 19420 확인.

상세 값·증거 = `RESULT_2026-06-16.md`, BTS 스펙 = `BTS_TICKET_SPECS.md`.
