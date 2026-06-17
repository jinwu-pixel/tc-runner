# QCAT .qmdl 파싱 — 단축 방법 (revisable)

모뎀 `.qmdl` diag 로그를 QCAT으로 파싱할 때의 속도/안정 방법. **더 좋은 방법이 생기면 본 문서를 개정한다** (§8.2 ledger에 근거 row). 실행 정본 = `scripts/qcat_fast_extract.ps1`. 본 문서는 *왜 그렇게 하는지* + 코드 맵.

관련 메모리/문서: `reference_qcat_fast_extraction`, `reference_qcat_offline_diag_workflow`(재부팅 가로지르는 분석·acl_deny 판별자), `reference_ims_sip_qcat_verification`(SIP 0x156E), `project_bts15068_antbar`(첫 적용).

## 병목 = OpenLog 전수 인덱싱
QCAT `OpenLog`는 파일의 **모든 패킷을 인덱싱**한다 → 이것이 floor. BTS15068 실측(QCAT 6.30.121):

| 파일 | 패킷수 | OpenLog | 비고 |
|---|---|---|---|
| 155 MB qmdl | 1,311,322 | **147–157 s** | 86%가 `0x1FEB` Extended Debug (QSR4 압축, 동반 `.qdb`/`diag_qsr4_guid_list.xml`로 디코드) — 우리가 안 써도 open 시 전부 디코드 |
| 40 MB qmdl | 185,662 | **18 s** | open floor는 패킷수에 비례 |

`PacketFilter`는 **출력 시점** 필터 → open 비용은 못 줄인다.

## 3대 단축 원칙
1. **filter-FIRST** — `SaveAsText` 전에 `PacketFilter.SetAll($false)` → 필요한 `Set(0x..,$true)` → `Commit()`. 안 하면 40초 구간이 **564 MB**로 폭주. 필터 시 KB~수 MB, SaveAsText 0.5–0.8 s.
2. **ISF 캐시 (핵심)** — qmdl을 **1회만** open(~floor) 한 뒤 `SaveAsISF`(브로드 코드 superset 필터)로 작은 `.isf` 생성. 이후 모든 재질의는 **ISF 재오픈 0.2 s + 추출 <1 s** (~740× ↑). ISF 경로 데이터 = qmdl 경로와 동일(무손실, RSRP 일치 검증). 같은 캡처 반복 분석의 정답.
3. **단일 COM 활성화 + 포그라운드** — 아래 함정 참조. query마다 New-Object 금지, 한 번 열고 같은 객체로 `closeFile`+`OpenLog`(ISF) 재사용.

## 함정 (영구 주의)
- **DirectPlay 모달 = 0x80080005의 진짜 원인**: `QCAT.exe` 첫 기동 시 Windows "기능: DirectPlay 설치" 모달이 떠 launch를 **블록** → `New-Object`가 `0x80080005 CO_E_SERVER_EXEC_FAILURE`(~120 s 타임아웃) 실패. 백그라운드/비대화형 세션은 모달 응답 불가 → 항상 실패. **해소: 모달 "건너뛰기"(파싱엔 DirectPlay 불요) 또는 DirectPlay 1회 설치(관리자). 반드시 포그라운드 + 넉넉한 timeout(≥300 s).** ("DCOM cooldown"은 오진이었음.)
- **PowerShell 반환값 오염**: retry 함수에서 진행 메시지를 `Write-Output`으로 찍으면 함수 반환값에 섞여 `$q`가 String이 됨 → 전 단계 `MethodNotFound`. `Write-Host` 사용.
- **타임스탬프 = UTC** (KST = UTC + 9 h).
- **`SetTimeWindowAbsolute`는 6.30 SaveAsText에 무효** (출력이 전 로그 범위) → packet filter + 파서에서 타임스탬프 후필터.

## 코드 맵 (자주 쓰는 LTE/IMS)
| 코드 | 패킷 | 용도 |
|---|---|---|
| `0xB193` | LTE ML1 Serving Cell Meas Response | RSRP/RSRQ ground truth — `Inst Measured RSRP`, `Inst RSRQ`, per-antenna `Inst RSRP Rx[0]/Rx[1]` (ANTBAR/AVG 검증의 원천) |
| `0xB15B` | LTE LL1 RX Antenna Info | per-antenna 정보 |
| `0xB0EC` | LTE NAS EMM State | 등록/이탈 |
| `0xB0C0` | LTE RRC OTA | RRC/RAT |
| `0x156E` | IMS/SIP | SIP REGISTER↔resp Call-ID 매칭 (IMS 검증) |
| `0x7001` / `0x4179` | UMTS Call Flow / WCDMA PN Search | WCDMA 전환 |

## 사용
```powershell
# 첫 터치: 재사용 ISF 캐시 생성 + 추출 (느린 qmdl 1회)
scripts\qcat_fast_extract.ps1 -Qmdl <q.qmdl> -Isf <cache.isf> -MakeIsf -Codes 0xB193,0xB15B -Out lte_meas.txt
# 이후 같은 캡처 재질의 (sub-second): ISF만 지정
scripts\qcat_fast_extract.ps1 -Isf <cache.isf> -Codes 0xB0EC -Out emm.txt
```

## 향후 개선 후보
- DirectPlay 1회 설치 후 백그라운드/headless 파싱 가능해지면 워크플로 agent에서 qmdl 파싱 위임.
- open floor(패킷수 비례) 단축: qmdl 바이너리 시간 슬라이스(HDLC 프레이밍 파싱) — 복잡, 미검증.
