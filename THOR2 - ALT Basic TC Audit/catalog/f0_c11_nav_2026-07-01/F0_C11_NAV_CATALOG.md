# F0 C11 navigation discovery 카탈로그 (2026-07-01)

**목적**: C11 v1 driver run1(2026-07-01) 0 RUNNABLE — v1 oracle(verifier literal=source paraphrase + navigation candidate)가
F0 실 UI와 divergent 확정. 본 카탈로그는 F0 device-assisted discovery로 **실 navigation·verifier ground truth**를 채록해
후속 oracle 재설계(무단말 authoring)를 grounded하게 한다.

- 단말: **F0 `B06201249E0002F0`** (AT-M140 THOR2, RY07260601S, ko-KR, 480×800). B27/ODIN2 미접촉.
- 방법: `uiautomator dump`(비파괴 §2.1) + `input swipe/tap`(navigation-only). driver 코드 수정 0. app launch = launcher intent(monkey `-c android.intent.category.LAUNCHER`).
- 원시 dump: `sst/sst_0..6.xml`(설정 트리 스크롤) · `sst/svc_menu.xml` · `pdm/pdm_main.xml`·`pdm/pdm_settings.xml` · `mgn/mgn.xml`.

## 환경 finding (별도)

- **io.appium 헬퍼 잔존**: run1 종료 후 `io.appium.uiautomator2.server`/`.server.test`/`io.appium.settings` 미uninstall — 핸드오프 §7 "잔존 0" 위반. (dump는 방해 안 함 — instrumentation 비활성.)
- **Git Bash `/sdcard/` 경로 mangle**: bash에서 `adb shell ... /sdcard/x.xml` → `/Files/Git/sdcard/…` 변환 → dump 유실. device 상호작용은 **PowerShell**로.
- **PowerShell 한글 desync**: `Get-Content` 기본 ANSI → mojibake. XML 분석은 **Grep(ripgrep, UTF-8)** 또는 `[IO.File]::ReadAllText(...,UTF8)`.

---

## SST 클러스터 (5) — 간편모드 홈 `설정` 타일 → `com.android.settings.Settings` (표준 scrollable)

**F0 설정 top-level 트리 (실측 22항목, 스크롤 순서)**: 설정 / 설정 검색 / 알림 / 알림 읽어주기 / 배터리 / 저장용량 /
**소리 및 진동** / **디스플레이** / **배경화면 및 스타일** / 모드 설정 / 접근성 / 보안 / 개인 정보 보호 / 위치 /
**안전 및 긴급 상황** / 비밀번호 및 계정 / 디지털 웰빙 및 자녀 보호 기능 / Google(summary=서비스 및 환경설정) / DuraSpeed / 시스템 / 휴대전화 정보.

★ **네트워크/WiFi/연결 top-level 항목 없음.** `서비스 및 환경설정`은 별도 메뉴가 아니라 **Google 행의 summary**(tap→GoogleSettingsActivity).

| TC | v1 expected | v1 nav | 실측 ground truth | 재설계 |
|---|---|---|---|---|
| SST_008 | 소리 및 진동 | press_key OK(23) | **루트에 `소리 및 진동` 존재**. OK키는 `기본 정보`(About)로 이탈 | literal✓ · nav=**tap `소리 및 진동`**(스크롤 0) |
| SST_013 | 배경화면 및 스타일 | 직접 tap | **존재**(스크롤 ~1) | literal✓ · nav=**scroll+tap** |
| SST_014 | 디스플레이 | 직접 tap | **존재**(스크롤 ~1) | literal✓ · nav=**scroll+tap** |
| SST_015 | 안심기능 | 직접 tap | top-level `안전 및 긴급 상황`(긴급 SOS, 의료 정보, 알림) — 후보 매핑 | **label backfill 후보**=안전 및 긴급 상황 (redesign 시 확인) |
| SST_012 | WiFi | 직접 tap | **설정 경로 부재** (네트워크 top-level 없음·Google summary 오인) | **re-scope**: WiFi는 Quick Panel 추정 — 설정 타일 경로로 도달 불가 |

## PDM 클러스터 (5) — `만보기` `com.hnlens.pedometer` (launcher → MainActivity)

★ **진입 모델 확정**: 메인 대시보드(오늘 걸음 수/목표/이동 거리/소모 칼로리) → **우상단 톱니 `id/imageView` @[408,44][474,110] tap → `PersonalInformationActivity`(내 정보/신체 정보)**. v1 down-chain(DPAD_DOWN×N) = 오류(메인엔 대상 필드 없음).

`PersonalInformationActivity` 실측: 내 정보 / 신체 정보 / **키**(170 cm) / **몸무게**(60 kg) / **성별**(남성) / 걸음 수 / **목표 걸음 수**(10000 보).

| TC | v1 expected | 실측 | 재설계 |
|---|---|---|---|
| PDM_041 | 키 | **키**(170 cm) | literal✓ · nav=**gear→PersonalInfo** |
| PDM_042 | 몸무게 | **몸무게**(60 kg) | literal✓ · nav=gear→PersonalInfo |
| PDM_043 | 성별 | **성별**(남성) | literal✓ · nav=gear→PersonalInfo |
| PDM_044 | 목표 걸음수 | **목표 걸음 수**(띄어쓰기 상이) | literal backfill=`목표 걸음 수` · nav=gear→PersonalInfo |
| PDM_040 | 뒤로가기 버튼 | 텍스트 아닌 **요소**(back button) | **verifier 재설계**(element/content-desc, text 아님) |

## MGN 클러스터 (2) — `돋보기` `com.hnlens.magnifying` (launcher → 프리뷰)

실측 resource-id: `preview_surface` / **`scale_bar`(줌 슬라이더)** / `zoom_in` / `zoom_out` / `shutter_button`(desc=사진) /
**`flash_light`**(text=`손전등`, desc=`Open flashlight`) / `effect`.

| TC | v1 expected | 실측 | 재설계 |
|---|---|---|---|
| MGN_001 | 줌 슬라이더 핸들 | 텍스트 아닌 **요소** — 화면 텍스트=`손전등` | **verifier=by resource-id** `com.hnlens.magnifying:id/scale_bar`(또는 zoom_in/zoom_out) 존재 |
| MGN_002 | (hardkey) | keycode 미상 → run1 fail-closed 단말 미접촉 | 설계대로 유지(no-guess) 또는 hardkey device-discovery |

---

## 재설계 함의 (무단말 authoring 후속)

**driver(thor2j §2.5) 변경 필요**:
- SST: OK-key 모델 폐기 → `소리 및 진동` tap. TAPNAV에 **scroll-to-find** 추가(디스플레이/배경화면은 스크롤 필요).
- PDM: down-chain 폐기 → **gear(id/imageView) tap → PersonalInformationActivity** 진입 후 literal 대조.
- MGN_001: text-verifier → **resource-id verifier**(scale_bar).
- PDM_040: text-verifier → element/back-button verifier.

**yaml(tc-runner) backfill**:
- PDM_044 literal `목표 걸음수`→`목표 걸음 수`.
- SST_015 literal `안심기능`→`안전 및 긴급 상황`(redesign 시 확인).

**tractability (device-touch 11 기준, 재설계 후 잠재 RUNNABLE)**:
- 명확 tractable **8**: SST_008/013/014/015 + PDM_041/042/043/044 (literal✓ 또는 단순 backfill · nav만 수정)
- verifier-model 변경 필요 **2**: PDM_040, MGN_001 (요소 기반)
- **re-scope 1**: SST_012 WiFi (설정 타일 경로 밖 — Quick Panel 추정)
- fail-closed 유지 **1**: MGN_002 (hardkey, 이번 subset엔 device-touch 아님)

→ v1 run1 **0 RUNNABLE** → grounded 재설계 시 **~8 RUNNABLE 잠재** + verifier 재설계 2 + re-scope 1. 재run은 driver 재설계 후.
