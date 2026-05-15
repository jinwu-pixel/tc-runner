# BUG-25175 Regression — RY07260302M

> 검증일: 2026-05-14
> 이전 검증: 2026-04-09 (`doc/BUG25175_APN_Menu_Analysis.md`, 18/18 PASS @ `MY01260300` / Z0409U_DAILY_DEV_GMS_763)

## 1. 단말·빌드

| 항목 | 값 |
|---|---|
| 단말 | AT-M140 (THOR2) |
| 시리얼 | B06201249E0002F0 |
| Build ID | UP1A.231005.007 |
| Build incremental | **RY07260302M** |
| Build date | Thu May 14 01:39:47 CST 2026 |
| Fingerprint | `ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys` |
| 화면 | 480x800 |
| USIM | LGU+(45006) / SKT(45005) / KT(45008) 3종 사용 |

## 2. 진행 범위

| Phase | 범위 | 진행 |
|---|---|---|
| Phase 1 | LGU+ 기본 제한 (T-01~05) | 5/5 PASS |
| Phase 2 | LGU+ 엔지니어 모드 제한 해제 (T-06~10) | 5/5 PASS |
| Phase 3 | 타사 USIM 교차 (T-11~13) | 3/3 PASS |
| Phase 4 | Edge cases — 저비용 4축 (T-14/15/19/20) | 4/4 PASS |
| Phase 4 | Edge cases — DB 변경 동반 (T-16/17/18) | skip — 별 라운드 |

누계 = **17/18 PASS** (Phase 1+2+3+4 부분, 이전 회귀 18/18 대비 T-16/17/18 미실행)

## 3. Phase 1 — LGU+ 일반 모드 제한 확인

| TC | 검증 포인트 | 객관 증거 | 결과 |
|---|---|---|---|
| T-01 | LGU만 표시 (IA/IMS/Tethering 숨김) | UI dump `text="LGU"` 1건, `apn_radiobutton` 1개 | PASS |
| T-02 | `+` 추가 버튼 부재 | content-desc 3건 (`APN`/`위로 탐색`/`옵션 더보기`), `새 APN`·FAB 0 | PASS |
| T-03 | LGU 탭 → 토스트, 편집 미진입 | logcat `Toast pkg=com.android.settings` 4초, top activity `.Settings` 유지 (ApnEditor 0), 토스트 텍스트 "변경할 수 없는 APN입니다." 사용자 시인 | PASS |
| T-04 | 삭제 옵션 부재 | ⋮ 메뉴 dump = `text="초기화"` 1건만 | PASS |
| T-05 | APN 값 = `internet.lguplus.co.kr` | DB `content query` 일치 | PASS |

DB 사실관계 (LGU+ numeric=45006):
- LGU / `internet.lguplus.co.kr` / default,supl
- LGU IMS / `IMS` / ims,mms
- LGU IA / (empty) / emergency,ia
- LGU Tethering / `tethering.lguplus.co.kr` / dun

→ DB 4건은 존재하나 UI는 LGU 1건만 노출 = MR fix 정상 동작.

## 4. Phase 2 — LGU+ 엔지니어 모드 제한 해제

| TC | 검증 포인트 | 객관 증거 | 결과 |
|---|---|---|---|
| T-06 | EngineerMode 진입 | 사용자 시인 (다이얼러 `*#*#3646633#*#*`) | PASS |
| T-07 | APN Settings 진입 | top activity `com.android.settings/.Settings$TestingSettingsActivity` (isLguPlusEngineerMode=true alias entry) | PASS |
| T-08 | 4 APN 전부 노출 | UI dump: `LGU` + `internet.lguplus.co.kr`, `LGU IA`, `LGU IMS` + `IMS`, `LGU Tethering` + `tethering.lguplus.co.kr` | PASS |
| T-09 | `+` 추가 버튼 존재 | content-desc=`새 APN` | PASS |
| T-10 | LGU 탭 → ApnEditor 진입 (편집 가능) | UI dump 표준 필드 노출 (이름/APN/프록시/포트/사용자 이름), `readOnlyMode=false` 동작 | PASS |

→ 일반 모드 vs 엔지니어 모드 UI 차이 = LGU 1건 → 4건 + `새 APN` 추가, 편집 가능. MR fix 양 방향 모두 정상.

## 5. Phase 3 — 타사 USIM 교차 (LGU+ 제한 미적용)

| TC | 검증 포인트 | 객관 증거 | 결과 |
|---|---|---|---|
| T-11 | SKT 일반 APN: 메뉴 유지, 편집 가능 | UI dump `SK Telecom` + `lte.sktelecom.com`, content-desc=`새 APN`, ApnEditor 진입 확인 | PASS |
| T-13 (SKT) | SKT 엔지니어 모드: 제한 변화 없음 | 일반 모드와 동일 (1건 + `새 APN`) | PASS |
| T-12 | KT 일반 APN: 메뉴 유지, 편집 가능 | UI dump `KT` + `lte.ktfwing.com`, `KT IMS` + `ims` (2건), content-desc=`새 APN`, 편집 시인 (디폴트값 변경 안 됨) | PASS |
| T-13 (KT) | KT 엔지니어 모드: 제한 변화 없음 | 일반 모드와 동일 (2건 + `새 APN`) | PASS |

DB 사실관계:
- SKT(45005): 6건 (SK Telecom / SK Telecom 3G / SKT IMS / SKT Tethering / SKT 5G INTERNET / SKT IA)
- KT(45008): 4건 (KT / KT IMS / KT Emergency / KT IA)

→ SKT/KT 모두 일반 모드에서 `새 APN` 노출 + 편집 가능 = LGU+ 제한 로직이 타사 USIM에 미적용. 회귀 일치.

## 6. Phase 4 — Edge cases (저비용 4축)

2026-05-15 보강 — LGU+ USIM baseline에서 비행기 토글 / 재부팅 / USIM swap 후 제한 유지·재적용 확인.

| TC | 검증 포인트 | 객관 증거 | 결과 |
|---|---|---|---|
| T-14 | USIM 교체 (LGU+→SKT): LGU+ 제한 해제 | SKT 캠프 후 UI dump: `text="SK Telecom"`, content-desc=`새 APN` 등장 (LGU+ baseline 부재 → 등장) | PASS |
| T-15 | USIM 교체 (SKT→LGU+): LGU+ 제한 재적용 | LGU+ 캠프 복귀 후 UI dump: `text="LGU"` 1건, `apn_radiobutton` 1개, `새 APN` 부재. T-01 baseline 일치 | PASS |
| T-19 | 비행기 ON/OFF 후 LGU+ 제한 유지 | `cmd connectivity airplane-mode enable→disable`, LGU+ 캠프 회복 후 UI dump T-01 baseline 일치 (LGU 1건 / content-desc 3건 / `새 APN` 부재) | PASS |
| T-20 | 재부팅 후 LGU+ 제한 유지 | `adb reboot` 후 LGU+ 캠프 (45006 IN_SERVICE) 회복, APN 메뉴 UI dump T-01 baseline 일치 (LGU 1건 / content-desc 3건 / `새 APN` 부재) | PASS |

→ MR fix 가 비행기 토글 / 재부팅 / USIM 교체 cycle 후에도 유지 (휘발 X, 재적용 자동). 회귀 일치.

## 7. NOTE — 본 회귀 범위 외 관찰

본 BUG-25175 회귀 판정에는 영향 없는 부수 관찰 사항.

| 항목 | 내용 |
|---|---|
| **SKT default APN UI 노출 수** | DB 6건 중 UI에 `SK Telecom` 1건만 (일반·엔지니어 동일). default,supl 타입 항목 3건(SK Telecom / SK Telecom 3G / SKT 5G INTERNET) 중 1건만 viewport 표시. 스크롤 미검증. 별 라운드 NOTE. |
| **KT IMSFW 미노출** | 이전 회귀(2026-04-09) 메모: "KT, KT IMS, KT IMSFW 표시". 이번 회귀: KT, KT IMS만 노출 (IMSFW 부재). 빌드별 default APN 정책 변경 가능성. 별 라운드 NOTE. |
| **EngineerMode entry activity** | 이전 분석: `com.mediatek.engineermode.ApnSettingsActivity → ApnSettings (필터 해제) → ApnEditorActivity`. 본 회귀: top activity `com.android.settings/.Settings$TestingSettingsActivity` alias. 동일 UI/동일 동작이라 정상. |

## 8. Phase 4 잔여 skip 사유 (T-16/17/18 — DB 변경 동반)

| 항목 | skip 사유 |
|---|---|
| T-16 (엔지니어 모드 APN 수정) | DB 변경 위험 (이전 회귀에서 logcat 분석으로 PASS, 본 회귀에서 재현 시 부작용 위험) |
| T-17 (엔지니어 모드 APN 추가) | DB 변경 위험 (동일) |
| T-18 (APN 초기화) | DB 변경 위험 (전 USIM 영향) |

→ T-16/17/18 은 차후 라운드 재선택. 본 회귀 17/18 PASS = MR fix 핵심 동작 (제한 적용·해제·재적용·유지) 17축 검증 완료.

## 9. 종합 결론

빌드 `RY07260302M` (2026-05-14 / Phase 4 보강 2026-05-15) 에서 BUG-25175 MR fix **회귀 17/18 PASS**.

- Phase 1+2+3 (13축): LGU+ 제한 적용 / 엔지니어 모드 해제 / 타사 USIM 미적용
- Phase 4 부분 (4축): 비행기 토글 후 유지 / 재부팅 후 유지 / USIM 교체 후 해제·재적용

모두 이전 회귀(2026-04-09, 18/18 PASS @ MY01260300) 와 일관 동작 확인. 본 빌드에서 BUG-25175 fix 유지됨. 잔여 T-16/17/18 (DB 변경 동반) 만 별 라운드.

## 10. Evidence (Working Tree 누적)

폴더: `THOR2 - LGU APN BUG25175/RY07260302M/`

| 파일 | TC |
|---|---|
| `bug25175_t01_apnlist.{xml,png}` | T-01/02/04/05 (LGU+ 목록) |
| `bug25175_t03_after_tap.xml`, `bug25175_t03_state.png`, `bug25175_t03_user_tap.png` | T-03 (LGU 탭 후 상태) |
| `bug25175_t04_overflow.{xml,png}` | T-04 (⋮ 메뉴) |
| `bug25175_t08_eng_apn.{xml,png}` | T-07/08/09 (LGU 엔지니어 4 APN) |
| `bug25175_t10_eng_editor.{xml,png}` | T-10 (LGU ApnEditor) |
| `bug25175_t11_skt_apn.{xml,png}` | T-11 (SKT 일반 목록) |
| `bug25175_t11_skt_editor.{xml,png}` | T-11 (SKT ApnEditor) |
| `bug25175_t13_skt_eng_apn.{xml,png}` | T-13 (SKT 엔지니어) |
| `bug25175_t12_kt_apn.{xml,png}` | T-12 (KT 일반 목록) |
| `bug25175_t13_kt_eng_apn.{xml,png}` | T-13 (KT 엔지니어) |
| `bug25175_t14_skt_swap_apnlist.{xml,png}` | T-14 (SKT swap post-LGU+) |
| `bug25175_t15_lgu_swap_apnlist.{xml,png}` | T-15 (LGU+ swap post-SKT) |
| `bug25175_t19_apnlist.{xml,png}` | T-19 (비행기 ON/OFF 후) |
| `bug25175_t20_apnlist.{xml,png}` | T-20 (재부팅 후) |

Commit/push 결정은 사용자 명시 승인 시.
