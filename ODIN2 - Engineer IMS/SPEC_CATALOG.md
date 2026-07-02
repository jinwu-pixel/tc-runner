# ODIN2 Engineer Mode — IMS 항목 검증 카탈로그

- **단말**: ODIN2 / AT-M150 (alt_odin2, Android 14 userdebug)
- **빌드**: `AT-M150Z0612U` (= 12종 IMS Engineer 항목 Resolved·검증된 빌드 → 빌드 게이트 PASS)
- **baseband**: `MPSS.HA.1.2-00043-KD_ALL_PACK-1.104002.4`
- **엔지니어 앱**: `com.ls.teleengineer` (`/system_ext/app/TeleEngineerMode/`)
- **진입 경로**: 앱서랍 "tele engineer" → `EngineeringActivity`(게이트, "Enter Engineering Mode" 버튼) → `CategoryActivity`(탭: **GENERAL / IMS / LTE**)
- **작업**: 12종 IMS Engineer 항목 **복합 테스트** (2026-06-16 ALT_Chung 배정)
- **BTS**: `http://10.5.103.101:9080/` (ZenTao, PYO product, module SystemUI/TeleEngineerMode)
- **항목 타이틀 포맷**: `✅ <이름> (<인터페이스#>) [<BTS_ID>]` — ✅ = 실장 표시. desc에 Interface/Config-key/Default 노출.

## Carrier 종속 (사용자 명시 2026-06-16)
- 검증 순서: **SKT 우선 → KT → LGU+** 전 carrier 매트릭스.
- 현재 관찰 carrier = **SKT (45005, LTE)**. 관찰값엔 항상 carrier 병기.
- 일부 기대값 carrier별 상이: RTP timer SKT=10s / Domain sktelecom2(SKT)·LGT2(LGU) / PRID mcc450mnc006(SKT) 등.

---

## IMS 탭 — 전체 16 항목 인벤토리 (단말 ground truth, 표시 순서)

| 순 | BTS | 항목 | 인터페이스 | Config-key / NV-field | Default / Options | 배정 |
|---|---|---|---|---|---|---|
| 1 | 19420 | User Agent | NV#69689 | `ims_user_agent` · user_agent (STRING) | — | 추가 |
| 2 | 25036 | Subscribe Expires | INI | `[SIPConfig:StandardTimers] SipSubscribeValue` | ex 3600s | ✔ |
| 3 | 19425 | Session Expires | NV#73842 | `IMSVoiceDynamicConfig` · sessionExpires (UINT16) | sec | ✔ |
| 4 | 25035 | Register Expires | INI | `[SIPConfig:StandardTimers] SipRegValue` | ex 3600s | ✔ |
| 5 | 25059 | Domain | INI | `[ParamConfig:RegistrationDefaultParams] domainName` | sktelecom2(SKT)/LGT2(LGU) | ✔ |
| 6 | 25066 | PRID | INI | `[ParamConfig:RegistrationDefaultParams] privateURI` | `<user>@<domain>` | ✔ |
| 7 | 19429 | SIP Timer | NV | `ims_sip_config` · T1,T2,T4,TA~TK | — | 추가 |
| 8 | 25071 | IMS Reset to Default (PDC) | PDC | MBN default로 전체 리셋 | — | 추가 ⚠ |
| 9 | 25049 | Video Codec Priority | INI | `[QIPCALL:ImsMediaProfileConfig] VideoProfile1` | Default(H263;H264;H265)/263/264/265 | ✔ |
| 10 | 25043 | Voice Codec Priority | INI | `[QIPCALL:ImsMediaProfileConfig] AudioProfile1` | Default/EVS/AMR-WB/AMR-NB/AMR-WB pref | ✔ |
| 11 | 19443 | AMR Codec ModeSet | NV#73846 | `IMSCodecDynamicConfig` · amrModeSet (UINT32) | bitmask 0=Default/0x01~0xFF | ✔ |
| 12 | 19445 | AMR-WB Codec ModeSet | NV#73846 | `IMSCodecDynamicConfig` · amrWbModeSet (UINT32) | bitmask 0=Default/0x01~0xFF | ✔ |
| 13 | 19581 | RTP Timer | NV#73842 | `IMSVoiceDynamicConfig` · rtpLinkAlivenessTimer (UINT32) | sec (SKT=10) | ✔ |
| 14 | 25038 | Session Refresher | INI | `[QIPCALL:ImsVoiceSessionTimerConfig] sessionRefresherType` | Default/UAC(0)/UAS(1) | ✔ |
| 15 | 19410 | HD Voice Setting | INI | `[QIPCALL:ImsMediaProfileConfig] AudioProfile1` | ON=AMR-WB+AMR / OFF=AMR-NB only | ✔ |
| 16 | 19593 | Traffic Port | NV#73845 | `IMSRTPDynamicConfig` · speech/video Start·StopPort | — | 추가 |

NV 경로 prefix = `/nv/item_files/ims/`. (GENERAL 탭: Auto Answer(QcRilHook), HSPA Setting(Diag#3649)[16232]. LTE 탭: 미조사 — 금일 scope 밖.)

---

## Backing store 그룹 (★복합 테스트 간섭 분석)

| Store | 담는 항목 | 간섭 위험 |
|---|---|---|
| **NV#73842** `IMSVoiceDynamicConfig` | RTP Timer[19581], Session Expires[19425] | 동일 NV파일 복수 필드 — 한 항목 변경/리셋이 다른 필드에 영향 가능 |
| **NV#73846** `IMSCodecDynamicConfig` | AMR ModeSet[19443], AMR-WB ModeSet[19445] | 동일 NV파일 |
| **NV#73845** `IMSRTPDynamicConfig` | Traffic Port[19593] | 단독 |
| **NV#69689** `ims_user_agent` | User Agent[19420] | 단독 |
| **NV** `ims_sip_config` | SIP Timer[19429] | 단독 |
| **INI `[QIPCALL:ImsMediaProfileConfig] AudioProfile1`** | **Voice Codec Priority[25043] + HD Voice Setting[19410]** | ★**동일 키 동시 기록 — 충돌 1순위 검증 대상** |
| **INI `[QIPCALL:ImsMediaProfileConfig] VideoProfile1`** | Video Codec Priority[25049] | 단독 |
| **INI `[QIPCALL:ImsVoiceSessionTimerConfig]`** | Session Refresher[25038] | 단독 |
| **INI `[SIPConfig:StandardTimers]`** | Subscribe Expires[25036], Register Expires[25035] | 동일 섹션 |
| **INI `[ParamConfig:RegistrationDefaultParams]`** | Domain[25059], PRID[25066] | 동일 섹션 (registration 영향) |
| **PDC** | IMS Reset to Default[25071] | 전체 MBN 리셋 — 격리/복원용 |

---

## BTS 티켓 상세 추출

### #26116 TeleEngineerMode (우산 / 전달 APK)
- 엔지니어 모드 전달 APK 자체 (`tele_engineer_mode-1.0.4 → 1.0.5.apk`). "all test items have BTS#ID marked".
- Z0612U엔 이미 integrated(`/system_ext/app/`). 2026-06-08 Chung Z0603U+1.0.5 1차 확인 "눈에 띄는 차이 없음"(비디오).

### #19581 [IMS] RTP Timer
- **스펙**: RTP alive timer NV#73842 `IMSVoiceDynamicConfig.rtpLinkAlivenessTimer`. SKT USIM 기대값 **10초**.
- **수정**: 모뎀 하드코딩 default `0`→`10`, byte 정렬, item명 case-insensitive (Gerrit 72921). IMS one-button full reset → MBN 리로드.
- **Resolved**: AT-M150Z0612U (6/12), WangYanfei 검증 OK.
- **단말 관찰**: 예정 (SKT 캠프 완료 — 값 확인 단계).

### (나머지 11종 BTS 본문) — 추출 예정
단말 인벤토리로 인터페이스/키/기본값은 확보됨. BTS 본문은 수정이력·기대거동 보강용으로 필요 시 개별 추출.
