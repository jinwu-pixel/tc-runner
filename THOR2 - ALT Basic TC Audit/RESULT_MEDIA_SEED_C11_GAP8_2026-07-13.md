# RESULT — C11 gap-8 사진 seed S1 관찰 (2026-07-13)

## 결론

- **PFW = Case B**: 합성 사진 5장이 MediaStore에 정상 등록돼도 홈 p3 사진 액자 위젯은 계속 `사진 추가하기` 상태였다. PFW 6건을 열려면 위젯에서 앨범을 명시적으로 선택해야 한다.
- **MGN_006 = seed로 미해소**: 돋보기 UI는 seed 전 카탈로그와 node signature가 동일했고 썸네일 요소가 나타나지 않았다. 일반 MediaStore 사진 유무가 현재 썸네일 노출 조건은 아니다.
- **S2 미진입**: 앨범 선택·저장·위젯 구성 변경은 수행하지 않았다. 원복 동선이 먼저 확정돼야 한다.
- **S3 PASS**: seed 5장과 전용 디렉토리를 제거했고 MediaStore, package 수, p3 빈 앨범 구조가 사전 기준선으로 복귀했다.

본 결과는 authoring 또는 `RUNNABLE_NOW` 승격이 아니다. 다음 단계의 grounded 입력이다.

## 환경과 범위

| 항목 | 값 |
|---|---|
| 단말 | F0 `B06201249E0002F0` 단독 연결 |
| 모델 / build | AT-M140 / `RY07260601S` |
| seed | `PFWSEED_01.jpg` ~ `PFWSEED_05.jpg` |
| 파일 속성 | 각 1280x720 JPEG, EXIF 0, 합성 색상+라벨, PII 0 |
| 단말 경로 | `/sdcard/DCIM/PFWSEED_C11/` 한정 |
| 위젯 구성 조작 | 0 |
| 돋보기 촬영/썸네일 tap | 0 |

## S0 host 검증

- `gen_pfwseed_photos.py` fresh 실행: 5파일 생성.
- 파일명: `PFWSEED_{01..05}.jpg` 정확 일치.
- 크기: 5/5 = 1280x720.
- EXIF entry: 5/5 = 0.
- setup/reset 상수: serial `B06201249E0002F0`, 경로 `/sdcard/DCIM/PFWSEED_C11`, 기대 수 5 일치.
- 스크립트 3종 `py_compile` PASS.

## S1 preflight

| 게이트 | 사전 값 | 판정 |
|---|---:|---|
| adb | F0 1대만 `device` | PASS |
| package 수 | 219 | 기준선 고정 |
| MediaStore image 수 | 10 | 기준선 고정 |
| `PFWSEED` row | 0 | PASS |
| 전용 디렉토리 | 없음 | PASS |
| p3 위젯 | `사진 추가하기`, `frame_bg`, `cl_vp2`, `ll_album_add` | 빈 앨범 기준선 |

### 계측 함정과 복구

초기 기준 스크린샷을 `/sdcard/pfw_pre_baseline.png`에 생성하자 MediaStore가 이를 자동 등록하여 image 수가 10→11로 증가했다. seed 전에 해당 파일과 그 row(`_display_name=pfw_pre_baseline.png`)만 정확히 제거해 11→10, 잔존 0을 확인했다.

이후 모든 screenshot/dump 원격 임시는 `/data/local/tmp`를 사용했다. 단말 MediaStore를 관찰하는 세션에서는 `/sdcard` screencap도 mutation이 될 수 있다는 재사용 규칙이다.

## seed 등록

`setup_pfwseed_f0.py` 실행 결과:

- push: 5/5.
- MediaStore `PFWSEED` row: 5/5.
- 전체 image 수: 10→15.
- 등록 경로: 전부 `/storage/emulated/0/DCIM/PFWSEED_C11/`.
- package 수: 219 유지.

## 관찰 결과

### PFW

- HOME에서 bounded page scan으로 p3 재도달.
- seed 후에도 `사진 추가하기`와 `ll_album_add`가 존재.
- 즉 MediaStore 자동 반영 모델이 아니라 위젯 앨범 명시 선택 모델이다.
- 판정: **Case B**. `사진 추가하기` tap, picker 진입, 사진 선택, 저장은 수행하지 않음.

### MGN

- `com.hnlens.magnifying/.CameraLauncher` 실행 후 XML/screenshot 채록.
- seed 전 `mgn_main_full.xml`과 seed 후 UI node signature의 added/removed 집합이 모두 0.
- `scale_bar`, `shutter_button`, `flash_light`는 존재하나 썸네일 노드는 없음.
- 따라서 MGN_006의 `썸네일 버튼`은 일반 MediaStore 사진 seed로 출현하지 않는다. 촬영 결과나 앱 내부 상태 전제인지 별도 확인이 필요하다.
- 썸네일이 없으므로 dpad focus 재관찰은 수행하지 않음.

## S3 원복

`reset_pfwseed_f0.py` 실행 및 사후 검증:

| 항목 | 사후 값 | 결과 |
|---|---:|---|
| `PFWSEED` row | 0 | PASS |
| 전체 MediaStore image 수 | 10 | 사전과 일치 |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | PASS |
| package 수 | 219 | 사전과 일치 |
| `io.appium` package | 0 | PASS |
| p3 빈 앨범 | `사진 추가하기` 복귀 | PASS |
| p3 구조 | pre/post node 20개 exact structural match | PASS |
| 최종 화면 | `com.hnlens.simplemode/.ui.home.MainActivity` | HOME |

## 증거

local-only 디렉토리:

`THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/`

- `pfw_pre_p0..p2.xml`, `pfw_pre_baseline.png`
- `pfw_post_p0..p2.xml`, `pfw_post_seed.png`
- `mgn_post_seed.xml`, `mgn_post_seed.png`
- `pfw_reset_p0..p2.xml`

PNG는 binary evidence이므로 commit 후보가 아니다.

## 다음 게이트

S2를 열려면 다음을 먼저 만족해야 한다.

1. `사진 추가하기` 이후 picker를 선택 확정 없이 dump-only로 탐색한다.
2. 사진 선택 또는 저장 전에 위젯 앨범 해제/초기화 동선을 실측으로 확인한다.
3. 원복 동선이 확정된 경우에만 PFWSEED 선택·저장을 별도 승인한다.
4. MGN_006은 PFW S2와 묶어 자동 승격하지 않고, 썸네일 생성 조건을 별도 spec-gap/discovery로 다룬다.

## S2A — PFW picker dump-only 탐색 + 앨범 해제 동선 실측 (F0)

### 범위와 절차

- 성격은 **manual evidence observed** 수준의 `selector_discovery`이며 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.
- F0 `B06201249E0002F0` 단독 연결과 모델 `AT-M140`을 확인한 뒤 MediaStore 10건, `PFWSEED` 0건, 전용 디렉토리 없음, package 219, p3 빈 앨범 20-node 구조를 기준선으로 고정했다.
- `setup_pfwseed_f0.py`로 합성 사진 5장을 등록해 `PFWSEED` 5건/전체 15건을 확인했다. HOME에서 bounded page scan으로 p3에 도달한 뒤 매 조작 전 XML dump를 선행했다.
- 허용 조작만 수행했다: `사진 추가하기` 2회, 명시적 `취소` 1회, BACK keyevent 1회, 위젯 영역 long-press 1회. 앨범 행·사진 썸네일·`다시 보지 않기`·`확인`·완료/저장/추가·long-press 메뉴 항목 tap은 모두 0회다. 권한 팝업은 나타나지 않았다.
- 모든 원격 dump/screencap 임시는 `/data/local/tmp`만 사용했고 마지막에 `/data/local/tmp/s2a*` 잔존 0을 확인했다. `/sdcard`에는 evidence 임시파일을 쓰지 않았다.

### 관찰 — 진입 구조와 앨범 열거

`사진 추가하기` 직후 실제 사진 picker가 아니라 `com.hnlens.simplemode`의 안내 팝업이 먼저 나타났다.

| 관찰 요소 | manual evidence observed |
|---|---|
| title | `포토 슬라이드 쇼` / `com.hnlens.simplemode:id/tv_popup_title` |
| prompt | `사진 선택은 최대 10개 까지 가능하며 각각 5초 동안 표시됩니다.` / `tv_popup_prompt` |
| 안내 checkbox | `다시 보지 않기` / `check_album_prompt` + `tv_popup_prompt_again` — 사진 선택 checkbox가 아니며 미접촉 |
| 취소 | `취소` / `com.hnlens.simplemode:id/tv_cancel` |
| 진행 gate | `확인` / `com.hnlens.simplemode:id/tv_confirm` — 본 지시의 금지 tap이므로 미접촉 |

- 실제 picker는 금지된 `확인` 뒤에 있어 본 범위에서 도달하지 않았다. 따라서 **`PFWSEED_C11` 앨범 열거는 확인되지 않았다**. 이것은 앨범 부재 판정이 아니라 미도달에 따른 `fail_closed`다.
- 사진 thumbnail, 선택 checkbox/선택 개수 indicator, 앨범 행, 앨범 변경·해제·초기화 affordance는 관찰되지 않았다. 선택 모델에 대해 dump로 확정된 것은 안내문상의 최대 10개뿐이다.
- `취소`와 BACK은 각각 안내 팝업을 닫고 p3 `사진 추가하기`로 복귀했다. 명시적 close 버튼은 없었다.

### 해제·초기화 동선

- picker 내부: 실제 picker 미도달로 앨범 해제·변경·초기화 동선을 확정하지 못했다. 안내 팝업의 `취소`/BACK은 **선택 전 진입 이탈**만 입증하며, 실선택 후 앨범 해제 원복 경로의 증거가 아니다.
- p3 위젯: `cl_vp2` 영역 long-press 후 메뉴가 나타나지 않았고 XML은 직전 p3와 byte-for-byte 동일했다. menu item tap은 0회다.
- 위젯 소유 package: read-only resolver 관찰에서 Main/SwitchMode/ToolsManager/ShortcutEdit activity만 노출됐고 settings/config activity는 노출되지 않았다. 따라서 dump-only로 관찰할 소유 앱 설정 표면을 확인하지 못했다.

### 진입-이탈 무변이 확인

- `picker_entry_pre.xml`, `picker_cancel_post.xml`, `picker_back_post.xml`, `widget_longpress.xml`, `no_mutation_p3.xml`은 모두 같은 SHA-256 `0086D75E1AAFBF4049A2471E944B5533A117AF0BC0440BFADEB5002DF04C352E`였다.
- 다섯 dump 모두 20 nodes이며 `사진 추가하기`, `frame_bg`, `cl_vp2`, `ll_album_add`가 동일했다.
- picker 탐색 종료 시점에도 MediaStore 전체 15건/`PFWSEED` 5건, package 219, `io.appium` 0이었다. 사진 선택·확정·저장·위젯 구성 변경은 없었다.

### D 원복 invariants

`reset_pfwseed_f0.py`를 실행한 뒤 전항목을 재검증했다.

| invariant | 사전 | seed/관찰 중 | reset 후 | 결과 |
|---|---:|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | serial 핀 / `AT-M140` | reset의 sole-device gate PASS, `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 15 | 10 | PASS |
| `PFWSEED` row | 0 | 5 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | 합성 JPG 5개 | 없음 | PASS |
| package 수 | 219 | 219 | 219 | PASS |
| `io.appium` package | 0 | 0 | 0 | PASS |
| p3 빈 앨범 | 20 nodes + 4 markers | 동일 | baseline과 byte-for-byte 동일 | PASS |
| 최종 화면 | HOME | p3 관찰 | `com.hnlens.simplemode/.ui.home.MainActivity` HOME | PASS |

### 판정과 다음 승인점

**S2 실선택 승인 요청 불가 (`fail_closed`).** 승인 요청 가능 조건 ① `PFWSEED_C11` 앨범 열거와 ② 실선택 후 해제/초기화 동선 확정이 모두 미충족이다. 따라서 사진 선택·확정·저장으로 진행하지 않으며, PFW 6건은 re-scope/spec-gap 논의 대상으로 유지한다.

다음 승인점은 S2 실선택을 승인할지가 아니라, 우선 이 `fail_closed`를 수용해 PFW 6건을 re-scope/spec-gap으로 보낼지 결정하는 것이다. picker discovery를 계속하려면 `tv_confirm` 1회만 새로 허용하는 별도 dump-only 범위부터 다시 승인해야 하며, 그 승인도 사진·앨범 선택 승인을 포함하지 않는다.

### S2A 증거와 redaction 경계

local-only evidence: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2a/`

- 진입/팝업: `picker_entry_pre.*`, `picker_initial.*`, `picker_back_pre.*`
- 이탈/무변이: `picker_cancel_post.*`, `picker_back_post.*`, `no_mutation_p3.*`
- 해제 표면 관찰: `widget_longpress.*`
- 기준선/원복: `pre_p0.xml`, `pre_p1.xml`, `pre_p2.xml`, `pre_p3.png`, `reset_p0.xml`, `reset_p1.xml`, `reset_p3.xml`, `reset_p3.png`, `final_home.*`

XML/PNG는 local-only이고 PNG는 commit 후보가 아니다. 본 요약 MD만 redaction gate 대상으로 삼았으며 `tools/redaction_gate.py` 결과는 **PASS (1 path, 0 findings)**다.

## S2A-B — 안내 팝업 통과 + picker dump-only 탐색 (F0)

### 범위와 절차

- 성격은 **manual evidence observed** 수준의 `selector_discovery`이며 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.
- 시작 게이트에서 F0 `B06201249E0002F0` 단독 연결, `AT-M140`, MediaStore 10건, `PFWSEED` 0건, 전용 디렉토리 없음, package 219, p3 20-node/4-marker 기준선을 확인했다.
- `setup_pfwseed_f0.py`로 합성 사진 5장을 등록해 `PFWSEED` 5건/전체 15건을 확인했다.
- 선행 dump 후 허용 조작만 수행했다: `사진 추가하기` 2회, 안내 팝업 `tv_confirm` **총 1회**, picker `iv_back` 1회, 재출현 팝업 `tv_cancel` 1회, picker grid 스크롤 2회. `check_album_prompt`, 앨범 행, 사진/선택 overlay, `tv_done`(저장), 완료/추가/선택 확정 tap은 모두 0회다.
- picker 최초 채록 후 연결이 재개된 시점에 F0 단독, `AT-M140`, MediaStore 15/`PFWSEED` 5, top activity `PhotoPickActivity`를 재검증했다. 재개 dump는 중단 전 picker XML과 byte-for-byte 동일했다.
- 권한 팝업은 나타나지 않았다. 모든 원격 dump/screencap 임시는 `/data/local/tmp`만 사용했다.

### picker 구조와 앨범 열거

`tv_confirm` 1회 후 `com.hnlens.simplemode/.ui.photopick.PhotoPickActivity`에 도달했다.

| 구조 | manual evidence observed |
|---|---|
| 상단 뒤로 | `com.hnlens.simplemode:id/iv_back`, clickable |
| 선택 카운터 | `com.hnlens.simplemode:id/tv_proportion`, `0/10` |
| 선택 확정 | `com.hnlens.simplemode:id/tv_done`, text=`저장`, clickable — 미접촉 |
| 사진 grid | `com.hnlens.simplemode:id/rv_photos`, scrollable |
| 사진 cell | `com.hnlens.simplemode:id/iv_photo` 15개, clickable |
| 선택 overlay | `com.hnlens.simplemode:id/v_selected` 15개, clickable, `checkable=false`, `selected=false` |

- picker는 **앨범 목록이 아니라 전체 사진을 직접 보여주는 단일 grid**였다. 최초 화면에 합성 `PFWSEED P1`~`P5` 5장이 상단 5개 cell로 노출됐고 기존 10장과 합쳐 총 15개 cell이 열거됐다.
- 그러나 `PFWSEED_C11` 앨범명/앨범 행/앨범 selector는 XML과 screenshot 어디에도 없었다. 따라서 seed 사진의 grid 노출은 확인됐지만 **`PFWSEED_C11` 앨범 열거 조건은 미충족**이다.
- 선택 모델은 cell 위 `v_selected` overlay + 상단 `0/10` 카운터다. 15개 overlay 모두 미선택이었고, 안내문의 최대 10개와 `0/10` 제한 표시가 정합했다.
- 첫 하향 스크롤로 grid 끝을 채록했고 두 번째 동일 스크롤 후 XML이 첫 하단 dump와 byte-for-byte 같아 끝 지점을 확인했다. 상·하단 모두 앨범 변경, 전체 해제, 초기화 affordance는 없었다.
- picker의 명시적 이탈 수단은 `iv_back`뿐이었다. `tv_done`은 선택 확정/저장류 금지 버튼이므로 누르지 않았다.

### 해제·초기화 동선 판정

- 현재 picker 구조에는 앨범 단위 선택·변경·해제 UI가 없다.
- 개별 `v_selected`가 재tap으로 해제되는지는 실선택 없이 dump만으로 확정할 수 없고, 전체 선택 해제/초기화 control도 없다.
- 따라서 사진을 실제 선택한 뒤 p3를 빈 앨범으로 되돌리는 역방향 동선은 **미확정**이다. `iv_back`은 선택 전 이탈만 입증하며 S2 원복 경로의 증거가 아니다.

### 안내 팝업 재출현 probe

- picker에서 `iv_back`으로 p3 복귀한 뒤 `사진 추가하기`를 다시 눌렀다.
- `포토 슬라이드 쇼` 안내 팝업이 재출현했고 `popup_pre_confirm.xml`과 `reentry_probe.xml`의 SHA-256은 모두 `5AB376159EC2DEB3E96CC3D6B7490EE4F18CB3C5AD1F78F62EEFFEE25CB4F27A`였다.
- `check_album_prompt`는 재진입 시에도 unchecked였다. 즉 `tv_confirm` 단독은 관찰한 재진입 범위에서 **비영속**이며 PFW TC의 implicit fixture mutation은 관찰되지 않았다.
- 두 번째 진입에서는 `tv_confirm`을 누르지 않고 선행 dump로 확인한 `tv_cancel`로 이탈했다.

### 진입·이탈 무변이

- `baseline_p3.xml`, `picker_entry_pre.xml`, `picker_exit_post.xml`, `reentry_cancel_post.xml`, `reset_p3.xml`은 모두 SHA-256 `0086D75E1AAFBF4049A2471E944B5533A117AF0BC0440BFADEB5002DF04C352E`로 byte-for-byte 동일했다.
- 각 p3 dump는 20 nodes이며 `사진 추가하기`, `frame_bg`, `cl_vp2`, `ll_album_add`가 동일했다.
- picker 탐색 종료 시점에도 MediaStore 전체 15건/`PFWSEED` 5건, package 219, `io.appium` 0이었다. 사진 선택·확정·저장·위젯 구성 변경은 없었다.

### E 원복 invariants

`reset_pfwseed_f0.py` 실행 후 전항목을 재검증했다.

| invariant | 사전 | seed/관찰 중 | reset 후 | 결과 |
|---|---:|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | 재연결 후 단독 `device` / `AT-M140` | reset sole-device gate PASS, `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 15 | 10 | PASS |
| `PFWSEED` row | 0 | 5 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | 합성 JPG 5개 | 없음 | PASS |
| package 수 | 219 | 219 | 219 | PASS |
| `io.appium` package | 0 | 0 | 0 | PASS |
| p3 빈 앨범 | 20 nodes + 4 markers | 진입·이탈 후 동일 | baseline과 byte-for-byte 동일 | PASS |
| 원격 임시파일 | 0 | `/data/local/tmp` 한정 | `/data/local/tmp/s2ab*` 0 | PASS |
| 최종 화면 | HOME | picker/p3 관찰 | `com.hnlens.simplemode/.ui.home.MainActivity` HOME | PASS |

### 판정과 다음 승인점

**S2 실선택 승인 요청 불가 (`fail_closed`).** ① 합성 seed 사진 5장은 direct grid에 보였지만 `PFWSEED_C11` 앨범은 열거되지 않았고, ② 실선택 후 해제/초기화 동선도 picker 구조에서 확정되지 않았다. 사진·앨범 선택이나 저장으로 진행하지 않으며 PFW 6건은 이번 picker 실측을 근거로 re-scope/spec-gap 논의 대상으로 유지한다.

다음 승인점의 **S2 실선택 가능 여부는 현재 불가**다. 진행하려면 앨범 열거 조건 또는 원복 증거 기준을 다시 정의하는 별도 설계 결정이 먼저 필요하며, 본 관찰 결과만으로 실선택 승인을 요청하지 않는다.

### S2A-B 증거와 redaction 경계

local-only evidence: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2a_b/`

- 기준선/진입: `baseline_p0.xml`, `baseline_p1.xml`, `baseline_p3.*`, `seed_p0.xml`, `seed_p1.xml`, `picker_entry_pre.*`
- 팝업/picker: `popup_pre_confirm.*`, `picker_initial.*`, `picker_resume.*`, `picker_scroll1.*`, `picker_scroll2.*`
- 이탈/재출현: `picker_exit_post.*`, `reentry_probe.*`, `reentry_cancel_post.*`
- 원복: `reset_p0.xml`, `reset_p1.xml`, `reset_p3.*`, `final_home.*`

picker PNG에는 기존 미디어 thumbnail이 포함될 수 있으므로 전량 local-only이며 PNG는 commit 후보가 아니다. XML도 raw evidence로 local-only 유지하고 본 요약 MD만 redaction gate 대상으로 삼았으며 `tools/redaction_gate.py` 결과는 **PASS (1 path, 0 findings)**다.

## S2 Phase-1 — PFWSEED 1장 역방향 실증 (F0, 2026-07-14)

### 승인 근거와 STEP 0

**사용자 설계 결정(2026-07-13)**: S2 진입 기준을 `앨범 열거`에서 S2A-B로 확인된 `grid 열거`로 재정의하고, 설계 §2-5의 원복 사전 확정 요구를 **최소 변이 순차 실증**으로 waive했다. 위젯 구성/stale 잔존 가능성은 사용자가 수용했다.

본 절은 **manual evidence observed** 수준이며 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.

| STEP 0 gate | 값 | 결과 |
|---|---|---|
| 중복 실행 | RESULT 마지막 절=`S2A-B`, Phase 절 없음 | PASS |
| evidence 충돌 | `s2_phase1/`, `s2_phase2/` 모두 부재 | PASS |
| 단말 | F0 `B06201249E0002F0` 단독 / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0 | PASS |
| 전용 디렉토리 | `/sdcard/DCIM/PFWSEED_C11` 없음 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| p3 baseline | 20 nodes + `사진 추가하기`·`frame_bg`·`cl_vp2`·`ll_album_add` | PASS |

`setup_pfwseed_f0.py` 실행 후 `PFWSEED` 5/전체 15를 확인했다. 모든 remote dump/screencap은 `/data/local/tmp`만 사용했다.

### 상태 전이 — P1 선택과 저장

1. p3 `ll_album_add` → 안내 팝업 `tv_confirm` 1회 → `PhotoPickActivity`로 진입했다. `check_album_prompt`는 unchecked로 유지했다.
2. 선택 전 picker는 `0/10`, `iv_photo` 15개, `v_selected` 15개였고 PFWSEED P1~P5가 상단 5셀임을 screenshot으로 재확인했다.
3. 첫 셀 P1 `[0,120][160,280]`만 tap했다. 선택 후 `tv_proportion=1/10`, 첫 `v_selected selected=true`, 나머지 14개 overlay `selected=false`였다. 기존 사용자 사진 셀 tap은 0회다.
4. 선행 dump 후 `tv_done`을 1회 눌렀다. p3는 20-node 빈 앨범에서 **21-node 구성 상태**로 바뀌었고 `사진 추가하기`/`ll_album_add`가 사라졌다. P1 이미지와 `vp2_main`, `iv_album`, `cl_translucent`가 나타났다.

| 구성 상태 selector | 관찰 |
|---|---|
| `com.hnlens.simplemode:id/vp2_main` | slideshow ViewPager |
| `com.hnlens.simplemode:id/iv_album` | 현재 사진 ImageView |
| `com.hnlens.simplemode:id/cl_translucent` | 전체 위젯 clickable/focusable overlay |
| `com.hnlens.simplemode:id/tv_edit` | 구성 위젯 tap 후 나타난 `편집`, clickable/focusable |
| `com.hnlens.simplemode:id/cl_album_arrows` | 좌/우 화살표 container, focusable |
| `com.hnlens.simplemode:id/iv_arrow_left` | 왼쪽 화살표, clickable |
| `com.hnlens.simplemode:id/iv_arrow_right` | 오른쪽 화살표, clickable |

### 해제 후보 판정

#### 후보① — 구성 위젯 재진입: 범위 내 실패

- 구성 상태 `cl_translucent`를 dump-first로 1회 tap하자 picker가 아니라 p3 위에 `tv_edit`·`cl_album_arrows`·`iv_arrow_left/right`가 나타났다(21→25 nodes).
- `tv_edit`은 본 승인문의 허용 tap 목록에 없으므로 추측 tap하지 않았다. 따라서 재선택 picker `1/10` 도달, P1 재tap 해제, `0/10` 저장은 수행할 수 없었다.
- 판정: **후보①은 승인 범위 내 미완결/fail-closed**. `tv_edit`이 후속 해제 discovery의 구체적 새 승인점이다.

#### 후보② — media reset: 실패(stale/broken 위젯)

- `reset_pfwseed_f0.py`는 파일 5개를 제거하고 MediaStore를 전체 10/`PFWSEED` 0으로 복구했다.
- 그러나 reset 직후, HOME→p3 재도달 후, 추가 6초 후의 XML이 모두 구성 상태와 같은 SHA-256 `DE9609F63D6730E29FEC8548DC42EBDB7E9A5AB0AD8CCEDE59E6DEBCECFF9394`였다.
- 세 상태 모두 21 nodes, `iv_album`+`cl_translucent` 유지, `사진 추가하기`/`ll_album_add` 0이었다. baseline SHA-256은 `0086D75E1AAFBF4049A2471E944B5533A117AF0BC0440BFADEB5002DF04C352E`로 불일치한다.
- immediate screencap에는 P1이 남았고 6초 후 screencap에는 검정 영역과 붉은 잔상만 남는 partial/broken rendering이 채록됐다. 이는 설계 §7의 stale/broken reference 예측과 일치하는 NOTE다.
- 판정: **후보② 실패**. 파일/MediaStore 원복만으로 위젯 구성 상태는 초기화되지 않는다.

### Phase-1 판정과 잔존 상태

**입증된 해제 경로 = 없음.** 후보①은 `tv_edit` 추가 승인 없이는 picker에 재진입하지 못했고, 후보②는 media는 제거했지만 위젯을 빈 앨범으로 환원하지 못했다. 지시된 중단 조건에 따라 Phase-2에는 진입하지 않았으며 `pm clear`는 실행하지 않았다.

| invariant | 사전 | seed/선택 | Phase-1 종료 | 결과 |
|---|---:|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | serial pin | `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 15 | 10 | PASS |
| `PFWSEED` row | 0 | 5 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | JPG 5개 | 없음 | PASS |
| package 수 | 219 | 219 | 219 | PASS |
| `io.appium` package | 0 | 0 | 0 | PASS |
| p3 빈 앨범 | 20 nodes + 4 markers | P1 구성 21 nodes | 구성 21 nodes, 4 markers 미복귀 | **FAIL — stale 잔존** |
| remote temp | 0 | `/data/local/tmp` 한정 | `/data/local/tmp/s2p1*` 0 | PASS |
| 최종 화면 | HOME p3 baseline | HOME p3 P1 | `MainActivity` HOME p3 stale/broken | **NOTE** |

**잔존 상태 있음**: MediaStore와 전용 디렉토리는 원복됐지만 simplemode 사진 위젯 구성은 P1 참조를 보유한 채 남아 있다. 임의 `pm clear`·위젯 삭제는 금지 상태다.

### Phase-1 evidence와 redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_phase1/`

- baseline/진입: `baseline_p0.xml`, `baseline_p1.xml`, `baseline_p3.*`, `entry_pre.*`, `popup_pre_confirm.*`, `picker_pre_select.*`
- P1 mutation: `picker_post_select1.*`, `widget_1_saved.*`
- 후보①: `candidate1_widget_tap_post.*`
- 후보②: `candidate2_reset_immediate.*`, `candidate2_refresh_p0.xml`, `candidate2_refresh_p1.xml`, `candidate2_refresh_p3.*`, `candidate2_stale_t6.*`

PNG에는 기존 사용자 미디어 thumbnail 또는 stale rendering이 포함될 수 있으므로 전량 local-only이며 commit 후보가 아니다. XML도 raw evidence로 local-only 유지한다.

## S2 Phase-2 — 미진입

Phase-1에서 해제 경로가 하나도 실증되지 않아 진입 조건을 충족하지 못했다. 따라서 PFWSEED 5장 선택, `5/10` 저장, DPAD/OK focus 관찰, 5초 rotation, PFW_010/011/013/014/015/022 selector 실측은 모두 **미수행**이다. `s2_phase2/` evidence도 생성하지 않았다.

다음 승인점은 저위험 순서로 ① `tv_edit` dump-first tap을 추가 허용해 재선택 picker/0장 저장 경로를 확인하거나, ② 별도 고위험 게이트로 `pm clear` 영향을 설계하는 것이다. 현재 결과만으로 authoring 또는 `RUNNABLE_NOW` 승격을 주장하지 않는다.

변경 문서 2개(설계/RESULT)에 대한 `tools/redaction_gate.py` 결과는 **PASS (2 paths, 0 findings)**다.

## S2 Phase-1b — `tv_edit` 재선택 경로 확인 + stale 해소 (F0, 2026-07-14)

### 범위와 STEP 0

Phase-1의 21-node stale 위젯에서 `com.hnlens.simplemode:id/tv_edit`을 **dump-first, 진입당 1회** 누르는 추가 승인을 적용했다. 목적은 재선택 picker/0장 저장 경로 discovery와 stale 해소였으며, 본 절도 **manual evidence observed** 수준이다. authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.

| STEP 0 gate | 관찰 | 결과 |
|---|---|---|
| 중복 실행 | RESULT 마지막 절=`S2 Phase-2 — 미진입`, `S2 Phase-1b` 절 없음 | PASS |
| evidence 충돌 | `s2_phase1b/`, `s2_phase2/` 모두 부재 | PASS |
| 단말 | F0 `B06201249E0002F0` 단독 / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0, 전용 디렉토리 없음 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| p3 선행 상태 | 21 nodes, `iv_album`+`cl_translucent`, 빈 앨범 marker 0 | PASS |
| p3 SHA-256 | `DE9609F63D6730E29FEC8548DC42EBDB7E9A5AB0AD8CCEDE59E6DEBCECFF9394` | PASS — Phase-1 잔존값 일치 |

새 seed는 만들지 않았고 기존 사용자 사진 cell, `tv_done`, 삭제류, `pm clear`, 위젯 삭제는 전부 0회다. remote dump/screencap은 `/data/local/tmp`만 사용했다.

### `tv_edit` 도달 화면 판정

1. p3 `cl_translucent`를 누르자 Phase-1과 같은 25-node overlay가 나타났다. XML SHA-256은 `D34128FF32AE9EB33FA971E73824A4FAF261B748A3C43AF4749320015DD148F1`이며 `tv_edit`은 clickable/focusable, bounds=`[364,69][454,123]`였다.
2. 선행 dump 후 `tv_edit` bounds 중앙을 1회 눌렀다. 2초 후에도 top activity는 `com.hnlens.simplemode/.ui.home.MainActivity`, XML SHA는 동일한 `D34128F…48F1`이었다. `tv_proportion`, `rv_photos`, `tv_done`, `iv_photo`, `v_selected`, `iv_back`은 모두 0개였다.
3. 같은 진입에서 재tap하지 않고 BACK으로 overlay를 닫았다. p3는 다시 `DE9609F…9394` 21-node stale 상태였다.
4. 독립된 두 번째 `cl_translucent` 진입에서 pre-dump가 다시 `D34128F…48F1`임을 확인하고 `tv_edit`을 진입당 1회만 재시도했다. 결과는 activity·XML·selector가 첫 시도와 동일했다.

**도달 화면 판정: 없음/no-op.** 현재 stale 상태의 `tv_edit` tap은 재선택 picker나 편집기, 삭제 확인 화면으로 전이하지 않았다. 따라서 선택된 P1 재tap 해제, `0/10`, 0장 저장 가능성은 관찰할 수 없었고 해제 경로도 입증되지 않았다.

### Branch B — reboot probe

- overlay를 BACK으로 닫은 직후 p3는 21 nodes, SHA `DE9609F…9394`였다. F0 단독을 다시 확인한 뒤 승인된 `adb reboot`를 수행했다.
- 부팅 완료 후 HOME에 `모바일 데이터 사용` 안내가 나타났다. BACK에는 닫히지 않았지만 명시적 `취소`로 닫혔고 `데이터 사용`은 누르지 않았다. 시스템 설정 변경은 수행하지 않았다.
- bounded page scan으로 p3에 재도달하자 21 nodes, `frame_bg`+`cl_vp2`+`iv_album`+`cl_translucent`가 남고 `사진 추가하기`/`ll_album_add`는 0이었다. synthetic P1 stale rendering도 계속 보였다.
- 재부팅 후 XML SHA-256은 `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC`였다. 재부팅 전과의 유일한 XML 차이는 page scan이 만든 RecyclerView `focused=false`→`true` 1개이며, `focused` 값을 정규화하면 byte-for-byte 동일하다.
- 추가 6초 후에도 XML SHA는 `223A096…D98EC`, nodes/markers와 stale rendering은 동일했다.

**reboot 판정: stale 영속.** reboot는 위젯을 빈 앨범 20-node baseline으로 환원하지 않았다.

### 해제·Phase-2 판정

**입증된 해제 경로 = 없음, stale 해소 = 실패.** `tv_edit`은 현재 stale 상태에서 no-op이고 reboot에도 구성 상태가 영속했다. Phase-2 진입 조건을 충족하지 못했으므로 재seed, PFWSEED 5장 선택/저장, DPAD/OK focus 관찰, 5초 rotation은 모두 미수행이며 `s2_phase2/`도 생성하지 않았다.

다음 승인점은 별도 고위험 게이트인 `pm clear` 영향 설계 또는 위젯 삭제/재구성 동선이다. 둘 다 이번 승인 범위에서는 실행하지 않았다.

### 종료 invariants와 잔존 상태

| invariant | STEP 0 | Phase-1b 종료 | 결과 |
|---|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | 단독 `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 10 | PASS |
| `PFWSEED` row | 0 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | 없음 | PASS |
| package 수 | 219 | 219 | PASS |
| `io.appium` package | 0 | 0 | PASS |
| p3 빈 앨범 | 기대 baseline 20 nodes + 4 markers가 아닌 stale 21 nodes | reboot+6초 후에도 stale 21 nodes, 빈 앨범 marker 미복귀 | **FAIL — stale 지속** |
| 실험 remote temp | 0 | `/data/local/tmp/s2p1b*` 0 | PASS |
| `/data/local/tmp` 기타 항목 | 감사 범위 밖 | 기존 `dalvik-cache/`, `mock_apps.json`만 관찰·무접촉 | NOTE |
| 최종 화면 | HOME p3 stale | `MainActivity` HOME p3 stale | **NOTE — 잔존 상태 있음** |

MediaStore/seed/package 불변식은 유지됐지만 p3 baseline은 복구되지 않았다. 최종 F0 p3는 synthetic P1 참조를 가진 21-node stale 위젯이며, 이후 F0 세션은 빈 앨범 20-node 가정을 사용할 수 없다.

### Phase-1b evidence와 redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_phase1b/` (XML 14 + PNG 14 = 28 files)

- STEP 0/overlay: `step0_stale_current.*`, `overlay_post_widget_tap.*`, `tv_edit_post.*`, `back_after_tv_edit_noop.*`
- 독립 재시도: `overlay_retry_pre_tv_edit.*`, `tv_edit_retry_post.*`, `pre_reboot_stale.*`
- reboot: `post_reboot_home_initial.*`, `post_reboot_popup_back.*`, `post_reboot_popup_settle.*`, `post_reboot_mobile_data_cancel.*`, `post_reboot_page_scan_1.*`, `post_reboot_page_scan_2_p3.*`, `post_reboot_p3_plus6s.*`

PNG에는 boot/home 화면 또는 stale synthetic image가 포함되므로 전량 local-only이며 commit 후보가 아니다. XML도 raw evidence로 local-only 유지한다.

Phase-1b 반영 후 변경 문서 2개(설계/RESULT)에 대한 `tools/redaction_gate.py` 결과는 **PASS (2 paths, 0 findings)**다. staging/commit/push는 수행하지 않았다.

## S2 Phase-1c — re-seed probe: healthy 상태 `tv_edit` 검증 + stale 해소 (F0, 2026-07-14)

### 범위와 STEP 0

Phase-1b의 stale 상태 `tv_edit` no-op에서 참조 미디어 소실이라는 confound를 제거하기 위해, 기승인된 seed/reset과 `tv_edit` 조합만으로 re-seed probe를 수행했다. 본 절은 **manual evidence observed** 수준이며 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.

| STEP 0 gate | 관찰 | 결과 |
|---|---|---|
| 중복 실행 | RESULT 마지막 절=`S2 Phase-1b`, `S2 Phase-1c` 절 없음 | PASS |
| evidence 충돌 | `s2_phase1c/`, `s2_phase2/` 모두 부재 | PASS |
| 단말 | F0 `B06201249E0002F0` 단독 / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0, 전용 디렉토리 없음 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| p3 stale 구조 | 21 nodes, `iv_album`+`cl_translucent`, 빈 앨범 marker 0 | PASS |
| p3 SHA-256 | reboot 계열 `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC` | PASS |
| focus 정규화 | `focused=true`→`false` 정규화 후 Phase-1b `DE9609F6…9394`와 동일 | PASS |

모든 remote dump/screencap은 `/data/local/tmp`만 사용했다. 기존 사용자 사진 cell, `tv_done`, 삭제류, `pm clear`, 위젯 삭제는 전부 0회다.

### re-seed rendering과 참조 모델 판정

`setup_pfwseed_f0.py`로 합성 사진 5장을 다시 등록해 MediaStore 전체 15/`PFWSEED` 5를 확인했다.

- re-seed 직후 p3 XML은 21 nodes, SHA `223A0964…D98EC`로 구조 변화가 없었고 screenshot에는 검정 영역과 좁은 붉은 잔상만 보였다.
- 한 rotation 주기를 넘긴 6초 후 XML은 계속 `223A0964…D98EC`였지만 screenshot에는 synthetic P1 전체 rendering이 다시 나타났다.
- 반대로 실험 종료 reset 직후와 6초 후 screenshot은 같은 SHA-256 `664FE8456F2FEF568CBF17808F2400732AB48172AF70FAD7321D837632C6864E`의 broken rendering으로 유지됐다.

**참조 모델 판정 = path/file 기반.** 동일 경로의 P1 파일이 있을 때 rotation 후 rendering이 치유되고, 파일 제거 후 같은 관찰 시간에는 치유되지 않은 대비가 관찰됐다. 이는 내부 구현 소스 검증이 아니라 본 지시문의 rendering 기준에 따른 manual evidence 판정이다.

### healthy-media 상태 `tv_edit` 판정

1. P1 rendering이 복구된 p3에서 `cl_translucent`를 dump-first로 누르자 25-node overlay가 나타났다. `tv_edit`·`cl_album_arrows`·`iv_arrow_left/right`가 있었고 XML SHA-256은 `E0A2364CB3D6F0F3ECEBF5963E4F5228ACDD30ED90E36BC9572FABADAE6C4597`였다.
2. 선행 dump 후 `tv_edit` bounds 중앙을 진입당 1회 눌렀다. 2초 후에도 top activity는 `com.hnlens.simplemode/.ui.home.MainActivity`, XML SHA는 동일한 `E0A2364…C4597`이었다. picker selector `tv_proportion`, `rv_photos`, `tv_done`, `iv_photo`, `v_selected`, `iv_back`은 모두 0개였다.
3. 같은 진입에서 재tap하지 않고 BACK으로 닫았다. p3는 다시 `223A0964…D98EC` 21-node 구성 상태였다.
4. 독립 두 번째 진입에서 overlay pre-dump가 다시 `E0A2364…C4597`임을 확인하고 `tv_edit`을 1회만 재시도했다. activity·XML·selector 결과는 첫 시도와 동일했다.

**`tv_edit` 판정 = healthy-media에서도 no-op/무기능.** 참조 파일 존재와 P1 rendering 복구 후에도 화면 전이가 없었으므로 “미디어 소실 때문에만 no-op” 가설은 기각된다. 재선택 picker, 선택 P1 해제, `0/10`, 0장 저장은 도달하지 못했다.

### 해제·Phase-2 판정

**입증된 해제 경로 = 없음, stale 해소 = 실패.** `tv_edit`이 healthy-media에서도 독립 2회 no-op이므로 0장 저장을 통한 빈 앨범 환원 조건을 충족하지 못했다.

따라서 조건부 Phase-2에는 진입하지 않았다. PFWSEED 5장 선택/저장, DPAD/OK focus 관찰, 화살표/편집 요소 추가 실측, 5초 rotation 비교는 모두 미수행이며 `s2_phase2/`도 생성하지 않았다.

### 실패 경로 reset과 종료 invariants

`reset_pfwseed_f0.py`로 re-seed 5장을 제거했다. MediaStore/디렉토리는 원복됐지만 위젯 구성은 환원되지 않았다.

| invariant | STEP 0 | re-seed 중 | Phase-1c 종료 | 결과 |
|---|---:|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | serial pin | 단독 `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 15 | 10 | PASS |
| `PFWSEED` row | 0 | 5 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | 합성 JPG 5개 | 없음 | PASS |
| package 수 | 219 | 219 | 219 | PASS |
| `io.appium` package | 0 | 0 | 0 | PASS |
| p3 빈 앨범 | stale 21 nodes | P1 rendering 일시 치유, 구조는 21 nodes | SHA `223A0964…D98EC`, 21 nodes, 빈 앨범 marker 0 | **FAIL — stale/broken 지속** |
| 실험 remote temp | 0 | `/data/local/tmp` 한정 | `/data/local/tmp/s2p1c*` 0 | PASS |
| `/data/local/tmp` 기타 항목 | 감사 범위 밖 | 무접촉 | 기존 `dalvik-cache/`, `mock_apps.json`만 관찰 | NOTE |
| 최종 화면 | HOME p3 stale | HOME p3 구성 | `MainActivity` HOME p3 stale/broken | **NOTE — 잔존 상태 있음** |

최종 F0 p3는 synthetic P1 참조를 가진 21-node stale 위젯이다. MediaStore와 seed 디렉토리는 원복됐지만 빈 앨범 20-node baseline은 복구되지 않았으므로, 후속 F0 세션은 기존 baseline 가정을 사용할 수 없다.

### Phase-1c evidence와 redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_phase1c/` (XML 11 + PNG 11 = 22 files)

- STEP 0/re-seed: `step0_stale_current.*`, `reseed_render_immediate.*`, `reseed_render_t6.*`
- healthy `tv_edit`: `healthy_overlay_pre_tv_edit.*`, `healthy_tv_edit_post.*`, `healthy_back_after_noop1.*`, `healthy_overlay_retry_pre_tv_edit.*`, `healthy_tv_edit_retry_post.*`
- reset: `pre_reset_seeded_stale.*`, `reset_immediate_stale.*`, `reset_stale_t6.*`

PNG에는 stale synthetic rendering이 포함되므로 전량 local-only이며 commit 후보가 아니다. XML도 raw evidence로 local-only 유지한다.

Phase-1c 반영 후 변경 문서 2개(설계/RESULT)에 대한 `tools/redaction_gate.py` 결과는 **PASS (2 paths, 0 findings)**다. staging/commit/push는 수행하지 않았다. **후속 진행에는 `pm clear` 영향 또는 위젯 삭제·재구성에 대한 별도 고위험 설계 승인이 필요하다.**

## S2 Phase-1d — STEP 0 중단: F0 sole 상실 (2026-07-14)

### STEP 0 경과

본 시도는 ShortcutEdit/ToolsManager의 dump-only 표면 probe를 시작하기 위한 감사였으며 **manual evidence observed** 수준이다. activity 진입 전 F0 sole 상실 중단 조건이 성립해 probe 본문에는 진입하지 않았다.

| STEP 0 gate | 관찰 | 결과 |
|---|---|---|
| 중복 실행 | 시작 시 RESULT 마지막 절=`S2 Phase-1c`, `S2 Phase-1d` 절/`s2_phase1d/` 없음 | PASS |
| 단말/모델 | 시작 시 F0 `B06201249E0002F0` 단독 / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| 최초 UI dump | 화면 sleep으로 `null root node`; black screenshot만 채록 | RETRY — 상태 불일치 판정 아님 |
| HOME 재개 | wake/HOME 후 p1 42 nodes, 첫 page scan 후 p2 62 nodes 채록 | PASS |
| p3 stale SHA 재검증 | 두 번째 page scan 명령 시 F0 `device not found` | **STOP — sole 상실** |

F0는 중단 후 read-only `adb devices` 확인에서 다시 단독 `device`로 나타났지만, 중도 sole 상실 중단 조건이 이미 성립했으므로 재접촉·재개하지 않았다.

### component/activity probe 결과

| 대상 | 정확한 component/exported | `am start` | 화면 관찰 |
|---|---|---:|---|
| ShortcutEdit | 미확정 — `dumpsys package` 전 중단 | 0 | 미탐색 |
| ToolsManager | 미확정 — `dumpsys package` 전 중단 | 0 | 미탐색 |
| SwitchMode | 의도적 제외 | 0 | 접촉 금지 준수 |

화면 항목 tap, activity 내부 scroll, 편집/제거 affordance tap은 모두 0회다. `am start` 자체도 0회이므로 simplemode activity 진입으로 인한 구성 mutation은 없다.

### 무변이·판정 경계

- p3 최종 SHA는 이번 시도에서 재검증하지 못했다. 마지막 확정값은 Phase-1c의 21-node stale SHA `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC`이다.
- 이번 시도에서 확인된 마지막 화면은 p2 page scan dump이며, 연결 상실 뒤 HOME p3 복귀·MediaStore/package/tmp 최종 재검증은 중단 규율상 수행하지 않았다.
- 따라서 **표면 발견도, 미발견/진입 불가도 판정할 수 없다.** simplemode 저위험 표면이 소진됐다고 결론 내릴 근거가 없고 `pm clear` 설계(A) 또는 종결(B/C) fork로도 아직 이동하지 않는다.

재개 승인점은 `s2_phase1d/` partial evidence 기존재를 허용하고 STEP 0부터 다시 감사한 뒤 ShortcutEdit/ToolsManager dump-only probe를 수행하는 것이다. 새 승인 전 activity 접촉은 금지한다.

### partial evidence와 redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_phase1d/` (XML 2 + PNG 3 = 5 files)

- sleep 실패: `step0_stale.png`
- wake/HOME p1: `step0_stale_awake.*`
- 첫 page scan p2: `step0_page_scan_1.*`

PNG는 local-only이며 commit 후보가 아니다. XML도 raw evidence로 local-only 유지한다. 변경 문서 2개에 대한 redaction gate 결과는 **PASS (2 paths, 0 findings)**이며 staging/commit/push는 수행하지 않았다.

### 재개 (2026-07-14)

사용자가 `s2_phase1d/` partial 5파일 기존재를 허용하고 재개를 승인했다. 신규 evidence는 모두 `resume_` prefix로 채록했으며 기존 파일은 덮어쓰지 않았다. 본 결과는 **manual evidence observed** 수준이고 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다.

#### 재개 STEP 0

- 시작 시 RESULT 마지막 절은 위 `S2 Phase-1d — STEP 0 중단`이고 별도 재개 절은 없었으며, partial evidence는 XML 2 + PNG 3으로 일치했다.
- 최초 sole gate에서는 `f2bfcc3c`가 F0와 함께 연결돼 45초 동안 `adb devices`만 polling하고 단말별 접촉 0으로 대기했다. 사용자 분리 확인 후 F0 `B06201249E0002F0` 단독과 `AT-M140`을 재확인했다.
- MediaStore 전체 10/`PFWSEED` 0, package 219, `io.appium` 0이었다.
- HOME p1에서 bounded page scan으로 p3에 도달했다. p3는 SHA-256 `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC`, 21 nodes, `iv_album`+`cl_translucent`, 빈 앨범 marker 0이며 Phase-1c와 byte-for-byte 동일했다.

#### component/exported 확정

`dumpsys package com.hnlens.simplemode`의 Activity Resolver Table과 system APK `AndroidManifest.xml` read-only 추출로 다음을 확정했다. manifest 확인용 local APK 임시는 검사 직후 제거했다.

| 대상 | 정확한 component | manifest exported | 진입 결과 |
|---|---|---:|---|
| ShortcutEdit | `com.hnlens.simplemode/.ui.shortcutbutton.ShortcutEditActivity` | `true` | explicit start 성공 후 Settings 루트 redirect |
| ToolsManager | `com.hnlens.simplemode/.ui.toolsmanager.ToolsManagerActivity` | `true` | activity 정상 진입 |
| SwitchMode | `com.hnlens.simplemode/.ui.home.SwitchModeActivity` | `true` | 제외 규율에 따라 start 0 |

#### ShortcutEdit 관찰

- activity 진입 직전 F0 sole을 재확인했다.
- explicit start는 성공했지만 3초 후 top activity는 `com.android.settings/.Settings`였다. dump는 55 nodes, SHA-256 `48EFA5BF68703670AB9A49ADBCC58DF64ED272609D0F906EB980EF28631EACF1`이다.
- 화면은 설정 검색, 네트워크 및 인터넷, 연결된 기기, 해외 로밍, 앱 등 Android Settings 루트 일반 항목이었다. 사진 액자/위젯/홈 페이지 구성/타일 편집/제거 관련 text·rid는 없었다.
- 화면 항목 tap과 scroll은 0회다. BACK 1회로 p3에 복귀했고 XML은 SHA `223A0964…D98EC`, 21 nodes로 재개 pre와 동일했다.

#### ToolsManager 관찰

- activity 진입 직전 F0 sole을 다시 확인했다.
- `ToolsManagerActivity`에 정상 진입했고 top activity도 해당 component였다. dump는 20 nodes, SHA-256 `CBF004313EBD83299C57F77360B4FE770C9FEE8D3855776DF42C49EE41A4C166`이다.
- 화면 제목은 `바로가기 메뉴`이며 플래시, 절전 모드, 황도대 시계, 벨소리 모드, 잠금 화면 암호화, 정리 가속, QR 코드, 도움 요청 8항목이 노출됐다.
- 관련 rid는 `t_touch`, `t_bettery`, `t_change_clock`, `t_silent_mode`, `t_lock_setting`, `t_clean_up`, `t_qr_code`, `t_sos`다. scrollable node는 0이고 사진 액자/위젯/홈 구성·제거/타일 편집 요소는 없었다.
- 항목 tap은 0회다. BACK 1회로 p3에 복귀했고 XML은 재개 pre와 byte-for-byte 동일했다.

#### 무변이와 최종 invariants

| invariant | 재개 전 | 두 activity 관찰 후 | 결과 |
|---|---:|---:|---|
| F0 / 모델 | 단독 `device` / `AT-M140` | 단독 `device` / `AT-M140` | PASS |
| MediaStore image 총수 | 10 | 10 | PASS |
| `PFWSEED` row | 0 | 0 | PASS |
| `/sdcard/DCIM/PFWSEED_C11` | 없음 | 없음 | PASS |
| package / `io.appium` | 219 / 0 | 219 / 0 | PASS |
| p3 stale | SHA `223A0964…D98EC`, 21 nodes | 같은 SHA, pre와 byte-for-byte 동일 | PASS — 무변이 |
| 빈 앨범 marker | 0 | 0 | NOTE — stale 지속 |
| remote temp | `/data/local/tmp` 한정 | `/data/local/tmp/resume_*` 0 | PASS |
| 최종 화면 | HOME p3 | `MainActivity` HOME p3 stale | PASS |

#### 판정과 다음 fork

**표면 미발견, simplemode 저위험 표면 소진 확정.** ShortcutEdit은 관련 editor가 아니라 Settings 루트로 redirect됐고 ToolsManager는 일반 도구 바로가기만 제공했다. 두 activity 어디에도 위젯/사진 액자 구성·제거 또는 홈 편집 affordance가 없으므로 새 1-tap 승인점은 발생하지 않았다.

따라서 다음 결정은 ① `pm clear`의 영향 범위·복구 계획을 먼저 설계하는 A안, 또는 ②/③ stale 위젯을 수용하고 S2/PFW slice를 종결·재범위화하는 B/C fork다. 이번 재개에서는 `pm clear`, 위젯 삭제, SwitchMode, 화면 항목 tap을 모두 0회로 유지했다.

#### 재개 evidence와 redaction 경계

`s2_phase1d/` 신규분: `resume_*.xml` 8 + `resume_*.png` 8 = 16 files. 기존 partial 5파일과 합쳐 디렉터리 총계는 XML 10 + PNG 11 = 21 files다.

- p3 재검증: `resume_current_screen.*`, `resume_page_scan_1.*`, `resume_p3_stale_pre.*`
- ShortcutEdit: `resume_shortcutedit_entry.*`, `resume_shortcutedit_back1.*`
- ToolsManager: `resume_toolsmanager_entry.*`, `resume_toolsmanager_back1.*`
- 종료: `resume_final_p3.*`

PNG는 local-only이며 commit 후보가 아니다. XML도 raw evidence로 local-only 유지한다. 변경 문서 2개에 대한 redaction gate 결과는 **PASS (2 paths, 0 findings)**이며 staging/commit/push는 수행하지 않았다.

## pm clear 설계 (사전 채록)

### 범위·STEP 0

Phase-1d에서 simplemode 저위험 표면 소진이 확정돼 `pm clear com.hnlens.simplemode`의 영향·복구를 설계했다. 본 회차는 **read-only baseline + 설계 산출만** 수행했으며 `pm clear`, tap, 설정 변경, seed mutation은 모두 0회다.

| gate | 관찰 | 결과 |
|---|---|---|
| RESULT/design 중복 | Phase-1d 재개 완료, §9/본 절/evidence 부재 | PASS |
| F0 / 모델 | `B06201249E0002F0` 단독 / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0, 전용 dir 없음 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| p3 stale | SHA `223A0964…D98EC`, 21 nodes, `iv_album`+`cl_translucent`, 빈 앨범 marker 0 | PASS |

### read-only package/HOME 인벤토리

- simplemode versionName은 local-only package dump에 보존했으며 dataDir `/data/user/0/com.hnlens.simplemode`, `SYSTEM`·`PRIVILEGED`·`ALLOW_CLEAR_USER_DATA`·`ALLOW_BACKUP`을 확인했다.
- current HOME resolve=`com.hnlens.simplemode/.ui.home.MainActivity`, HOME role holder=`com.hnlens.simplemode`.
- keyguard는 존재하지만 현재 `showing=false`, `occluded=false`, 화면 ON인 unlocked 상태다.

| 상태 | clear 후 예상 | 확인 | 원복 가능성/경계 |
|---|---|---|---|
| p3 stale 사진 구성 | 빈 앨범 default가 주가설 | 20 nodes + 4 markers + SHA `0086D75E…C352E` | stale 지속 시 clear 무효·STOP |
| `다시 보지 않기` flag | unchecked/default 예상 | 빈 p3 popup dump | leave-unchecked 가능, storage 미확인 |
| p0~p3 배열/타일 | default reset 또는 동일 — UNKNOWN | page별 SHA/text/rid diff | 자동 rollback 없음, 소실 NOTE |
| simple/normal mode | UNKNOWN | top activity/layout/role | normal이면 승인된 SwitchMode만 |
| ToolsManager 상태 | app/system 경계 UNKNOWN | tap 0 dump 비교 | 항목별 복구 미설계 |
| 시계·날씨·황도대 설정 | provider/app 경계 UNKNOWN | p1 및 ToolsManager 비교 | 차이 NOTE, 별도 승인 |
| HOME role | 유지 예상, 미실증 | role holder + HOME resolver | role 복구는 execution gate 별도 항목 |

### fresh 전면 baseline

| page | SHA-256 | nodes | anchor |
|---|---|---:|---|
| p0 | `E920AEB14039CB7F6B1D92259AFFF14B35FBAAC19756CFD491B49D0166F9AD89` | 75 | 단축 다이얼·편집 |
| p1 | `017D0AA48B80938E01380859507C28E3A86A8DAB5D0422E25F2F3021ADF9D1D0` | 42 | 시계/날씨·주요 타일 |
| p2 | `0673178EC225A9F1156445C9311F537029E9887C645F6C621306B7E3F290E76A` | 62 | 상태/빠른도구·모드 전환 |
| p3 | `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC` | 21 | stale 사진 위젯 |

### UNKNOWN 목록과 설계 판정

1. clear가 simple/normal mode 또는 first-run wizard를 어떻게 초기화하는지.
2. p0 단축 다이얼, 페이지 순서, 타일 custom state의 실제 저장 위치와 수동 복구 가능성.
3. ToolsManager와 황도대 시계 등 항목 중 app data와 system setting의 경계.
4. HOME role이 예상대로 유지되는지와 chooser 재출현 여부.
5. `ALLOW_BACKUP` package의 실제 backup/restore 가능성 — 이번 회차에는 backup을 만들지 않아 full rollback 불가.
6. p3 위젯 구성이 dataDir 밖에도 복제돼 clear 후 stale가 남는지.

§9는 clear 1회, top-activity polling, first-run/role/SwitchMode/crash 분기, p0~p3 사후 diff, p3 primary success, Phase-2 G1/G2와 fixture T1/T2를 fail-closed 절차로 고정했다. **실행은 별도 승인 전 금지**다.

### 종료 불변성

| invariant | 종료값 | 결과 |
|---|---|---|
| F0 / 모델 | 단독 `B06201249E0002F0` / `AT-M140` | PASS |
| MediaStore / seed | 전체 10 / `PFWSEED` 0 / 전용 dir 없음 | PASS |
| package / helper | 219 / `io.appium` 0 | PASS |
| p3 | SHA `223A0964…D98EC`, 21 nodes, `iv_album`+`cl_translucent`, 빈 앨범 marker 0 | PASS — stale 불변 |
| remote temp | `/data/local/tmp/s2pm_design*` 0 | PASS |
| 최종 화면 | simplemode `MainActivity` HOME p3 | PASS |
| mutation | `pm clear` 0 / 화면 tap 0 / 설정 변경 0 | PASS |

### evidence와 redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_pmclear_design/`

- p0~p3: `baseline_p0.*`, `baseline_p1.*`, `baseline_p2.*`, `baseline_p3.*`
- 현재 lock/status: `keyguard_status_unlocked.png`
- ownership/runtime: `package_dump_full.txt`, `activity_top_full.txt`
- index: `baseline_manifest.md`

PNG·raw dumps는 local-only이며 commit 후보가 아니다. 변경 문서 2개의 redaction gate는 **PASS (2 paths, 0 findings)**였으며 staging/commit/push는 수행하지 않았다.

### G1 pre-gate baseline drift (2026-07-16)

- `pm clear` 실행 전 MediaStore image 총수가 세 차례 0건으로 반복 관찰됐다. 사용자가 단말 갤러리와 휴지통 모두 빈 상태임을 수동 확인했으므로, 기존 10건은 G1 명령과 무관한 **pre-existing media loss NOTE**로 격리한다.
- 사용자는 소실 사실을 기록하고 MediaStore 0건을 신규 pre-clear baseline으로 진행하도록 승인했다. PFWSEED 보충, 사진 선택, 위젯 구성 재시도는 수행하지 않았다.
- 같은 pre-gate에서 package 수는 218로 반복돼 설계 기준 219와 불일치했다. 보존된 evidence에는 simplemode 단일 package dump만 있고 과거 full package 목록이 없어 누락 package 식별은 불가능했다.
- F0 단독·`AT-M140`, simplemode HOME role/resolve, `PFWSEED` 0, 전용 dir 없음, `io.appium` 0, remote temp 0은 관찰 범위에서 유지됐다.
- 판정은 **runtime precondition FAIL(package count drift)**이다. `pm clear` 실행 0회, G1 evidence 생성 0, seed mutation 0이며 package 218 재기준을 사용자가 별도 승인하기 전 clear는 금지한다.

## pm clear G1 실행

### 승인·재기준

사용자는 2026-07-16에 MediaStore 10→0 소실(단말 갤러리·휴지통 모두 빈 상태)과 package 219→218 drift를 pre-existing NOTE/신규 pre-clear baseline으로 수용하고 G1 계속을 승인했다. 기존 full package 목록은 없어 누락 package는 특정하지 못했다. PFWSEED 보충·사진 선택·위젯 구성 재시도는 0회다.

### clear stdout·first-screen 판정

| 항목 | 결과 |
|---|---|
| `pm clear com.hnlens.simplemode` 호출 | **0회** |
| stdout 원문 | — (명령 미호출) |
| top-activity polling / first-run 처리 | — (clear 미실행) |
| SwitchMode / role 복구 / reboot | 0회 / 0회 / 0회 |

fresh pre-clear p3가 이미 canonical 빈 앨범으로 복귀해 STEP 0의 stale 21-node 전제가 불일치했다. 목적이 명령 전에 달성된 상태에서 launcher data를 지우는 것은 불필요한 mutation이므로 fail-closed로 clear를 생략했다.

### fresh p0~p3 대조

비교 기준은 §9.3의 2026-07-14 baseline이며, 아래 변화는 모두 clear 전에 관찰됐다.

| page | baseline → fresh | rid/text diff | 판정 |
|---|---|---|---|
| p0 | 75→75 nodes, SHA `E920AEB1…AD89` 동일 | rid 0 / text 0 | byte-for-byte 동일 |
| p1 | 42→52 nodes, `017D0AA4…D1D0`→`BB819C25…03C0` | rid 12 / text 12 | weather-exception 3 rid가 live weather 9 rid로 교체; 날짜·시각·기온·상태 dynamic 변화 |
| p2 | 62→62 nodes, `0673178E…E76A`→`2ABED9B2…1CF1` | rid 0 / text 2 | memory 표시 `30.87 MB`→`152.03 MB` dynamic 변화 |
| p3 | 21→20 nodes, stale `223A0964…D98EC`→canonical `0086D75E…C352E` | rid 5 / text 1 | `cl_translucent`/stale surface 소멸, `사진 추가하기`+4 markers 복귀 |

p3 fresh XML은 20 nodes이며 `사진 추가하기`, `frame_bg`, `cl_vp2`, `ll_album_add`가 각각 존재하고 `cl_translucent`는 없다. canonical SHA와 byte-for-byte 일치한다.

### §9.6 판정

**manual evidence observed: p3 primary-success 구조가 clear 전에 자연 복귀했다.** 이는 `pm clear runtime PASS`가 아니며 clear의 launcher reset 영향, first-run 분기, stale 제거 능력 또는 Phase-2 teardown 능력을 입증하지 않는다. G1은 실행 실패가 아니라 precondition 소멸에 따른 안전 취소다.

### 종료 invariants

| invariant | 종료값 | 결과 |
|---|---|---|
| F0 / 모델 | 단독 `B06201249E0002F0` / `AT-M140` | 일치 |
| MediaStore / seed | 사용자 수용 baseline 0 / `PFWSEED` 0 / 전용 dir 없음 | NOTE — pre-existing media loss |
| package / helper | 사용자 수용 baseline 218 / `io.appium` 0 | NOTE — missing package 미식별 |
| HOME role / resolve | `com.hnlens.simplemode` / `.ui.home.MainActivity` | 유지 |
| p3 | 20 nodes + 4 markers, SHA `0086D75E…C352E` | primary-success 구조 observed |
| remote temp | `/data/local/tmp` entry 0 | 정리 확인 |
| 최종 화면 | simplemode HOME p3 빈 앨범 | 확인 |
| mutation | `pm clear` 0 / seed 0 / 사진 선택 0 / 설정 변경 0 | 범위 준수 |

### NOTE·다음 승인점

- 기존 미디어 10건 소실과 package 1건 감소는 clear 전에 발생했으므로 G1 효과로 귀속하지 않는다.
- p1 weather surface와 p2 memory text 변화는 동적 외부 상태이며 clear 전 관찰이라 G1 판정 blocker가 아니다.
- G1 clear가 실제 실행되지 않아 기존 `G2+T1`의 T1(clear teardown)은 검증되지 않았다. 다음 선택은 ① 최소 1장 controlled fixture로 clear teardown을 먼저 검증하는 새 gate(권장), ② teardown 실패 잔존 위험을 다시 수용하고 G2+T1을 한 창에서 실행, ③ p3 자연 복귀 상태로 S2 종료다.

### evidence·redaction 경계

local-only: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_pmclear_g1/` — XML 6 + PNG 6 + `manifest.md` 1. PNG는 commit 후보가 아니다. 본 결과는 authoring 또는 `RUNNABLE_NOW` 승격 근거가 아니다. 변경 문서 2개의 redaction gate는 **PASS (2 paths, 0 findings)**였으며 staging/commit/push는 0이다.
