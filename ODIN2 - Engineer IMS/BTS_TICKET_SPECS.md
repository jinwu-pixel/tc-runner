# BTS 티켓 스펙 추출 (ZenTao, 2026-06-16)

출처: `http://10.5.103.101:9080/bug-view-<ID>.html` (read-only 추출, 상태 무변경). 전부 **Resolved/Trunk**, 단 **#18582 = Active**.

## IMS / Engineer 항목

| BTS | 항목 | 상태 | 스펙·기대 | 인터페이스(NV/EFS) |
|---|---|---|---|---|
| 19410 | HD Voice Setting | Resolved | Enable→AMR-WB+AMR / Disable→AMR only | EFS `/efsprofiles/overideconfig` `[QIPCALL:ImsMediaProfileConfig] AudioProfile1` (disable=`AMR_0_102;AMR_2_101`) |
| 19425 | Session expires | Resolved | **기본 360**, 720 set→INVITE Session-Expires 반영. reset→MCFG/USIM default | NV#73842 sessionexpires. **단말 SKT 관찰=1800**(USIM/MCFG별 상이) |
| 19443 | AMR Codec ModeSet | Resolved | default AmrModeSet=0, 범위 0x01~0x100 | NV#73846 amrModeSet subfield |
| 19445 | AMR-WB Codec ModeSet | Resolved | default AmrWbModeSet=0, 동일 비트 진행 | NV#73846 **amrWbModeSet subfield (19443과 동일 NV)** |
| 25035 | Register expires | Resolved | 수동 SipReg값 REGISTER 반영(35000/36000), reset→default 60000 | EFS `[SIPConfig:StandardTimers] SipRegValue` |
| 25036 | Subscribe expires | Resolved | 수동값 SUBSCRIBE 반영(3600/3500), reset→default 600000 | EFS `[SIPConfig:StandardTimers] SipSubscribeValue` |
| 25038 | [VOLTE] refresher | Resolved | Default/UAC(0)/UAS(1), INVITE 반영 | EFS `[QIPCALL:ImsVoiceSessionTimerConfig] sessionRefresherType` |
| 25043 | [VOLTE] Voice Codec Priority | Resolved | EVS=`EVS_0_126;EVS_1_127` / AMR-WB=`AMR_1_104;AMR_4_103` / AMR-NB=`AMR_0_102;AMR_2_101` / WB-pref=`AMR_1_104;AMR_4_103;AMR_0_102;AMR_2_101`. **NOTE: KT가 EVS 거부=carrier 거동, 버그 아님** | EFS `[QIPCALL:ImsMediaProfileConfig] AudioProfile1` |
| 25049 | [VILTE] Video Codec Priority | Resolved | Default=`H263_0;H264_0;H265_0` / 단일 H263/264/265. **NOTE: reset 버튼이 default 복원 대신 config 삭제했던 이슈 → one-button MBN reset으로 수정** | EFS `[QIPCALL:ImsMediaProfileConfig] VideoProfile1` |
| 25059 | Domain | Resolved | 수동 domain→REGISTER realm. SKT=`sktelecom2`, LGU=`LGT2`(KT 미명시) | EFS `[ParamConfig:RegistrationDefaultParams] domainName` |
| 25066 | PRID | Resolved | Private User Identity REGISTER 반영. 변경+**reboot**, reset→default. default 예 `4500612345678@ims.mnc006.mcc450.3gppnetwork.org` | EFS `[ParamConfig:RegistrationDefaultParams] privateURI` |
| 19581 | RTP Timer | Resolved | SKT=10s (default 0→10 fix) | NV#73842 rtpLinkAlivenessTimer |
| 19593 | Traffic Port | Resolved | speech/video RTP 포트 | NV#73845 IMSRTPDynamicConfig |

## 비-IMS (커버리지 완성용)

| BTS | 항목 | 상태 | 스펙·기대 | 인터페이스 |
|---|---|---|---|---|
| 16232 | HSPA Setting (GENERAL/WCDMA) | Resolved | accessStratumReleaseIndicator. **기대 default=5(Rel-9)**, 옵션 Rel-99/5/6/7/8/9. self-test NV 1/2/3=Rel-5/6/7 | NV#3649. **단, 모뎀 최초 default=3 → 단말 메뉴가 5로 반영됐는지 확인 필요** |
| 18582 | LTE Protocol Feature Setting | **Active** | 메뉴 **2개 포함**: (1) ROHC `/nv/item_files/modem/lte/rrc/rohc_supported` 0→1 / (2) CDRX `/nv/item_files/modem/lte/rrc/cap/fgi` FGI#4=0·FGI#5=0. 기대=메뉴 UI 구현 | EFS 경로, Gerrit hook 48794. **단일 ID가 단말 2항목(ROHC+CDRX) 커버** |

## 교차검증·flag

- ✅ **단말 관찰 = BTS 일치**: HD OFF `AMR_0_102;AMR_2_101`, Voice EVS `EVS_0_126;EVS_1_127`/AMR-NB `AMR_0_102;AMR_2_101`, Video default `H263_0;H264_0;H265_0` 모두 일치.
- 🔗 **25049 reset 이슈 = 본 세션 발견과 동종**: "reset이 default 복원 대신 config 삭제" → 글로벌 IMS Reset이 EFS override 해제(Read=`(not configured)`)와 연결. 재검증(오프라인로깅): post-reset write는 런타임 커밋되나 1회 reboot로 환원(비영속, reset 특이)=RESET-NONPERSIST(BUG_LOG#25071). NV(RTP/Session/AMR)는 post-reset에도 Read=실제값(미하락) — 원 "(not configured)+Write 무반영" 관찰은 정정됨.
- ⚠ **16232 default 5 vs 3** 확인 필요 (단말 미Read).
- ⚠ **19425 default 360(티켓) vs 1800(단말 SKT)** — USIM/MCFG별. carrier matrix 시 유의.
- 인터페이스 정정: IMS 25xxx + 19410 = **EFS `/efsprofiles/overideconfig`** 기반(단말 메뉴는 "INI"로 표기). NV# 명시는 19425(73842)·19443/19445(73846)·19581(73842)·19593(73845)·16232(3649)뿐.
