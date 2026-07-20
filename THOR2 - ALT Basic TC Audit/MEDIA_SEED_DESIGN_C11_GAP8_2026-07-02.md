# MEDIA_SEED_DESIGN — C11 gap-8 사진 세팅 precondition 설계 (2026-07-02)

**상태: G1 clear 미실행/목적 pre-gate 자연 달성 (2026-07-16) — 사용자가 MediaStore 0·package 218을 신규 pre-clear baseline으로 수용한 뒤 fresh scan에서 p3가 이미 canonical 빈 앨범 20 nodes + 4 markers(SHA `0086D75E…C352E`)로 복귀했음을 확인했다. stale 전제가 소멸해 `pm clear`는 0회로 종료했으며 clear 영향·teardown 능력은 미검증이다. Phase-2는 새 승인 게이트가 필요하다.** 결과 = `RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md`. 대상 = C11 잔여 8건의 공통 게이트 해제.

## 1. 목적·대상

gap-9 discovery(2026-07-02, `discovery_gap9_2026-07-02/`) 확정 사실: PFW 진입 표면 = 홈 p3 사진 액자 위젯 페이지(유일 표면)이나 **빈 앨범**(`사진 추가하기`) 상태, MGN 썸네일 노드 미발견(빈 갤러리 추정). 사진이 단말에 없어 아래 8건의 실측·판정이 전부 막혀 있다.

| 대상 | 세팅 후 기대 |
|---|---|
| PFW_010/011/013/014/015/022 (6) | p3 위젯이 슬라이드쇼 상태로 전환 → focus/화살표/편집 요소 실측 → oracle 백필·authoring 가능 |
| MGN_006 | 돋보기 썸네일 노드 노출 여부 확정 → element re-scope vs spec-gap 판정 |
| MGN_005 (재관찰) | 전체 UI 상태에서 dpad focus 모델 재관찰 (현 관찰 keyevent 3회 한정) |

## 2. 원칙 (불변)

1. **세팅/원복 대칭**: 넣은 것만, 전부, 검증 가능하게 제거. 원복 검증 PASS 전 세션 종료 금지 (helper 잔존 0 불변식과 동급).
2. **기존 사용자 미디어 무접촉**: 전용 디렉토리 `/sdcard/DCIM/PFWSEED_C11/`만 생성·삭제. 삭제 명령은 이 경로 한정 — `/sdcard/DCIM` 상위 대상 조작 영구 금지. 사전/사후 media store 전체 카운트 스냅샷으로 무접촉 입증.
3. **PII 0**: 합성 이미지(단색 배경+대형 라벨 P1~P5)만. GPS/EXIF 미기록(기존 gen_gallery_photos의 GPS 분기 미사용). 카메라 셔터로 실사진 생성 금지(기존 금지 유지).
4. **serial 핀**: 전 명령 `adb -s B06201249E0002F0` (기존 스크립트는 bare adb — F0용은 핀 필수).
5. **discovery-first / fail-closed**: 위젯 UI 조작(S2)은 각 단계 dump 채록 후에만 다음 tap. **원복 경로(앨범 해제)가 채록으로 확정되지 않으면 앨범 설정을 진행하지 않는다** — 되돌릴 수 없는 상태 진입 금지.

## 3. 자산 (재사용 — 발명 0)

- 생성: `scripts/gen_gallery_photos.py` 패턴 축소판 (PIL, deterministic) → **신규 `scripts/gen_pfwseed_photos.py`**: 5장, 1280×720, 파일명 `PFWSEED_{01..05}.jpg`, EXIF 없음, 출력 `output/pfwseed_photos/`.
- 세팅: `scripts/setup_gallery_media.py` 패턴 → **신규 `scripts/setup_pfwseed_f0.py`**: `-s F0` 핀 + push `/sdcard/DCIM/PFWSEED_C11/` + 파일별 `MEDIA_SCANNER_SCAN_FILE` broadcast(기존 검증된 방식, API 29+ 동작. F0 미동작 시 S1에서 대안 실측 후 본 설계 갱신).
- 원복: `scripts/reset_gallery_media.py` 패턴 → **신규 `scripts/reset_pfwseed_f0.py`**: `rm -rf /sdcard/DCIM/PFWSEED_C11` + rescan + **잔존 0 검증 내장**(media store query `PFWSEED` 0건 확인까지가 스크립트 성공 조건).
- 신규 3종은 host-TDD 대상 아님(기존 검증 패턴의 경로/핀 변형) — 단 dry-run(생성물 로컬 확인)은 무단말 선행.

## 4. Phase 절차

### S0 — 무단말 준비 (승인 후 즉시)
스크립트 3종 작성 + 로컬 생성물 확인(5 jpg, PII 0 육안/EXIF 검사).

### S1 — seed + discovery (mutating 1종: 파일 push)
1. pre-flight: F0 sole · pkg 219 · **media store 전체 카운트 스냅샷**(`content query images/media` 총건수) · p3 dump(빈 앨범 기준선)
2. `setup_pfwseed_f0.py` → media query로 PFWSEED 5건 등록 확인
3. **discovery (non-mutating)**: ① p3 dump — 위젯 자동 반영 여부 ② 돋보기 launch dump — 썸네일 노드 노출 여부 ③ (노출 시) dpad focus 재관찰(OK/셔터 금지 유지)
4. 분기: **Case A** 위젯 자동 반영 → S3 가능(PFW 실측은 이 상태에서 dpad·OK 채록 — OK는 슬라이드쇼 뷰어 진입류 네비게이션으로 허용, 편집 확정류 tap 금지) / **Case B** 여전히 `사진 추가하기` → S2 필요 보고 후 **정지** (사용자 확인 후 S2)

### S2 — 조건부: 위젯 앨범 설정 (mutating 2종: 위젯 구성 상태)
1. `사진 추가하기` tap → picker 각 단계 dump 채록(경로 카탈로그화)
2. **원복 경로 확인 게이트**: picker/편집 UI에서 앨범 해제·사진 제거 동선이 dump로 확정된 경우에만 선택 확정 진행. 미확정 시 BACK 이탈·중단·보고
3. PFWSEED 5장 선택·확정 → p3 슬라이드쇼 상태 dump → PFW focus 실측(dpad, R3/R6 적용)
4. 역방향: 확인된 해제 동선으로 앨범 제거 → p3 `사진 추가하기` 복귀 dump

### S3 — 원복 + 검증 (무조건 수행, 실패 시에도)
1. (S2 수행 시) 위젯 앨범 해제 상태 확인 선행
2. `reset_pfwseed_f0.py` → media query PFWSEED **0건**
3. 사후 검증: media store 전체 카운트 == 사전 스냅샷 · pkg 219 == pre · p3 dump == 빈 앨범 기준선(§S1-1) · HOME 복귀
4. 산출물: seed 전/중/후 dump 일체 → `catalog/f0_c11_nav_2026-07-01/discovery_seed_<date>/`

## 5. 중단 조건 (즉시 STOP + S3)

- media scan 미동작(5건 미등록) / p3·돋보기 dump에서 예상 밖 상태 / S2 원복 동선 미확정 / 기존 미디어 카운트 변동 감지 / F0 sole 상실.

## 6. 승인 범위 분할

- **본 설계 승인 = S0~S3 관찰 사이클까지** (TC oracle 백필·driver authoring은 실측 결과 기반 **별도 slice** — 기존 C11 패턴 동일).
- 실행 형식 = sonnet 에이전트 위임(재위임 금지·runbook·오케스트레이터 재검증) — 단 **S2 진입 여부는 S1 결과 보고 후 사용자 게이트**.

## 7. 리스크·미지수 (정직 공개)

| 항목 | 내용 | 완화 |
|---|---|---|
| 위젯 소스 모델 미상 | media store 자동 vs 앨범 명시 선택 | S1 분기 설계(Case A/B) |
| 앨범 해제 동선 미채록 | S2 원복 불가 위험 | §2-5 fail-closed 게이트 |
| scan 방식 F0 호환 | SCAN_FILE broadcast 기종 차 | S1-2 등록 검증 후 진행 |
| 위젯 캐시/썸네일 잔존 | 파일 삭제 후 위젯에 stale 이미지 | S3-3 p3 기준선 대조로 검출·보고(NOTE) |

## 8. 근거

- `discovery_gap9_2026-07-02/pfw_home_p3.xml`(frame_bg·cl_vp2·ll_album_add) · `mgn_main_full.xml`(썸네일 부재) · ledger gap-8 행 · PROCESS_REVIEW R3/R4/R6.
- 스크립트 패턴: `scripts/{gen_gallery_photos,setup_gallery_media,reset_gallery_media}.py` (ODIN2 Gallery 트랙 검증 완료 자산).

## 9. pm clear 영향·복구 설계 (2026-07-14)

### 9.1 범위·비가역 경계

- 대상 명령은 후속 실행 게이트에서 **정확히 1회** 허용할 `adb -s B06201249E0002F0 shell pm clear com.hnlens.simplemode`다. 본 설계 회차에서는 실행하지 않았다.
- local read-only 확인값: simplemode versionName은 local-only package dump에 보존했으며 `dataDir=/data/user/0/com.hnlens.simplemode`, package flag `SYSTEM`·`PRIVILEGED`·`ALLOW_CLEAR_USER_DATA`·`ALLOW_BACKUP`을 확인했다.
- `pm clear`는 package 설치를 제거하지 않지만 dataDir의 앱 데이터·캐시를 지우고 package를 stop할 수 있다. **dataDir byte-for-byte backup/restore는 확보하지 않았다.** `ALLOW_BACKUP` flag만으로 실제 복구 가능성을 주장하지 않으며, clear 전 상태로의 완전 rollback은 UNKNOWN이다.
- 현재 HOME resolve는 `com.hnlens.simplemode/.ui.home.MainActivity`, HOME role holder는 `com.hnlens.simplemode`다. role은 system 관리 상태라 앱 dataDir 밖에 있을 것으로 예상하지만 F0 clear 후 유지 여부는 미실증이다.
- 실행 중 기존 사용자 미디어, 연락처, 메시지, 통화, 시스템 설정은 조작하지 않는다. MediaStore 10/`PFWSEED` 0을 전후 비교한다.

### 9.2 simplemode 소유 상태 인벤토리

| 사용자-가시 상태 | 소유·현재 근거 | clear 후 예상 상태 | 확인 방법 | 원복 가능성 |
|---|---|---|---|---|
| p3 사진 위젯 구성 | simplemode `cl_vp2`/`iv_album`; 현재 stale P1 21 nodes | **주가설:** 빈 앨범 default. 앱 밖 저장이면 stale 지속 | p3 dump: 20 nodes + `사진 추가하기`·`frame_bg`·`cl_vp2`·`ll_album_add`; canonical SHA `0086D75E…C352E` | 빈 앨범이면 성공. stale 지속 시 앱 밖 저장으로 판정하고 STOP; 직접 원복 경로 없음 |
| 안내 팝업 `다시 보지 않기` | simplemode `check_album_prompt`; 관찰 범위에서 unchecked·재출현 | default unchecked/재출현 예상 | 빈 p3에서 `사진 추가하기` dump-first 진입 후 checkbox 상태 확인, 즉시 취소 | leave-unchecked 가능; 저장 위치는 미확인 |
| 홈 페이지/타일 배열 p0~p3 | simplemode MainActivity/ViewPager가 렌더링; fresh SHA §9.3 | resource default 또는 초기화 배열. 현재와 동일한지는 **UNKNOWN** | p0~p3 사후 dump/png와 SHA·text·rid diff | 자동 rollback 없음. baseline 기반 수동 재구성 가능성도 UNKNOWN; 시험단말 차이는 NOTE 수용 |
| p0 단축 다이얼/편집 상태 | p0에 `단축 다이얼`·`편집`·1–99 구간 노출 | assignment가 앱 데이터면 초기화 가능 | p0 노드/label/slot diff, 실제 연락처 leaf 진입 금지 | assignment 복구 경로 미채록; 소실 시 NOTE, PII leaf 미접촉 |
| 런처 mode(simple↔normal) | `SwitchModeActivity` exported, p2 `모드 전환`; 현재 simplemode HOME | **UNKNOWN:** simple 유지/normal reset/first-run mode chooser | HOME role·top activity·첫 화면 package/layout 확인 | normal이면 execution gate에서 승인된 SwitchMode 경유 simple 복귀; UI 미확정이면 dump 후 STOP |
| ToolsManager 8항목 상태 | simplemode `ToolsManagerActivity`; 항목은 플래시·절전·시계·벨소리·잠금·정리·QR·도움 요청 | 앱 preference와 system state 경계 **UNKNOWN** | ToolsManager tap 0 dump 비교; system 설정 leaf 진입 금지 | 항목별 원복 미설계. 차이는 NOTE 또는 별도 승인 |
| 황도대 시계/시계·날씨 위젯 설정 | p1 시계/날씨 + ToolsManager `t_change_clock` | 앱 데이터면 default reset, 외부 provider면 유지/재조회 — **UNKNOWN** | p1 screenshot/text/rid와 시각·날씨 surface 비교 | 설정 동선 미채록; 차이는 NOTE, 별도 승인 전 조작 금지 |
| badge/외부 공급 데이터 | p1 메시지 badge·날씨 등은 타 package/system 데이터와 결합 | launcher cache는 reset되나 원 데이터는 유지 예상 | p1 settle 후 재채록, 외부 앱 leaf 미접촉 | 통상 재조회 예상이나 미실증; 지속 차이는 NOTE |
| 기본 HOME role | `cmd role` holder와 HOME resolver 모두 simplemode | 유지 예상, **미실증** | clear 직후/재기동 후 role holder + resolve-activity 대조 | 소실 시 system chooser/role 복구는 execution gate의 별도 승인 분기 |
| package/MediaStore | system privileged package 1개, MediaStore 10 | package 유지, MediaStore 무변 예상 | pkg 219, simplemode 설치, MediaStore 10/`PFWSEED` 0 | 변동 시 즉시 STOP; media 원복 명령 실행 금지 |

### 9.3 사전 전면 baseline (read-only, local-only)

evidence: `catalog/f0_c11_nav_2026-07-01/discovery_seed_2026-07-13/s2_pmclear_design/`

| page | SHA-256 | nodes | 비교 anchor |
|---|---|---:|---|
| p0 | `E920AEB14039CB7F6B1D92259AFFF14B35FBAAC19756CFD491B49D0166F9AD89` | 75 | 단축 다이얼 1–99, `편집` |
| p1 | `017D0AA48B80938E01380859507C28E3A86A8DAB5D0422E25F2F3021ADF9D1D0` | 42 | 시계/날씨, 갤러리·라디오·설정·전화·메시지·카메라 |
| p2 | `0673178EC225A9F1156445C9311F537029E9887C645F6C621306B7E3F290E76A` | 62 | 상태/빠른도구, 모든 앱·모드 전환·돋보기 |
| p3 | `223A09640B1FEC1790347555A5BC8318DDC08D910E8C3B5FEA300F11956D98EC` | 21 | stale `iv_album`+`cl_translucent`, 빈 앨범 marker 0 |

현재 keyguard는 `deviceHasKeyguard=true`지만 `showing=false`, `occluded=false`, `SCREEN_STATE_ON`이며 unlocked/statusbar screenshot을 별도 채록했다. package 전체 dump와 `dumpsys activity top`도 local-only로 보존했다.

### 9.4 후속 실행 절차

> **2026-07-16 pre-gate NOTE:** G1 실행 전에 MediaStore가 반복 0건으로 관찰됐고 사용자가 갤러리·휴지통 모두 빈 상태를 수동 확인했다. 이전 full package 목록이 없어 219→218 누락 package는 특정할 수 없었으나 사용자는 MediaStore 0과 package 218을 모두 신규 pre-clear baseline으로 수용했다. 이후 fresh p0~p3 scan에서 p3가 clear 전에 canonical 빈 앨범 SHA로 자연 복귀한 것이 확인돼 stale 21-node precondition 불일치로 STOP했다. clear 명령은 호출하지 않았다.

1. **pre-gate 재검증:** `adb devices`에서 F0 단독, `AT-M140`, MediaStore 10/`PFWSEED` 0, pkg 219/`io.appium` 0, HOME role/resolve, p3 SHA `223A0964…D98EC`, remote temp 0. 하나라도 다르면 STOP.
2. **clear 1회:** 위 명령을 정확히 1회 실행하고 stdout `Success`를 원문 채록한다. 실패/빈 출력이어도 자동 재시도하지 않는다.
3. **런처 상태 폴링:** 1초 간격 bounded top-activity poll(최대 15초). simplemode HOME이 자동 복귀하지 않으면 HOME keyevent 1회만 허용하고 즉시 dump/png를 채록한다.
4. **first screen discovery:** 어떤 화면이든 tap 전 dump. package, activity, text/rid, keyguard, HOME role을 기록한다. 화면 항목 조작은 아래 승인 분기에 한정한다.
5. **사후 전면 채록:** simplemode HOME 확보 후 p0~p3를 bounded page scan으로 재채록하고 §9.3과 diff한다. MediaStore/package/role/tmp도 재확인한다.

### 9.5 first-run/예상 시나리오 분기

| 시나리오 | dump-first 처리 |
|---|---|
| simplemode HOME 즉시 복귀 | 항목 tap 0으로 p0~p3 사후 채록 진행 |
| 정보성 팝업, BACK/취소 가능 | checkbox(`다시 보지 않기`) 미접촉, BACK/취소로 닫고 채록 |
| first-run wizard가 HOME을 gate | 각 화면 dump; 실행 게이트가 명시적으로 허용한 `다음/시작/확인` 중 launcher 초기화에 필수인 최소 control만 1회씩 사용. 계정·권한·통신·PII 화면은 STOP |
| mode chooser/simple-normal 선택 | `simple` 선택만 execution gate에서 허용. 라벨/효과가 불명확하면 tap 0·STOP |
| default HOME chooser/role 소실 | simplemode 선택/role 복구는 별도 명시 승인 항목. 다른 launcher 선택 금지 |
| normal mode로 복귀 | `com.hnlens.simplemode/.ui.home.SwitchModeActivity`를 dump-first로 열고 simple 복귀 최소 동선만 execution gate에서 허용 |
| 닫히지 않는 팝업/예상 밖 editor·system setting | screenshot/dump 후 HOME/BACK 가능한 범위로 이탈, STOP |

### 9.6 사후 판정·성공 기준

**primary success = p3가 빈 앨범 20 nodes + 4 markers로 복귀**하고 canonical SHA가 원 baseline `0086D75E1AAFBF4049A2471E944B5533A117AF0BC0440BFADEB5002DF04C352E`와 일치하는 것. page scan에 따른 `focused` 값만 다른 경우 정규화 비교를 병기한다.

| 비교 | 판정 |
|---|---|
| p3 primary success + p0~p2 동일 | clear 성공/PASS |
| p3 primary success + p0~p2 차이 | clear 목적 성공, 타 페이지 변화는 diff 표와 NOTE. mode/role 이상이면 별도 실패 분기 |
| p3 20 nodes이나 marker/SHA 불일치 | 구조 미확정, STOP·spec-gap 보고 |
| p3 stale 21 nodes 지속 | `pm clear` 무효: 상태가 launcher data 밖에 저장된 것으로 판정, 즉시 STOP. 재설치/위젯 삭제 등 최후 수단은 새 설계 필요 |
| MediaStore/package/role 예상 밖 변동 | 영향 범위 위반, 즉시 STOP·복구 분기 |

### 9.7 실패 모드·복구 계획

1. **wizard HOME gate:** §9.5 최소 단계만 진행. 승인되지 않은 control이 필요하면 STOP.
2. **launcher crash loop/blank:** HOME 1회 후에도 지속하면 reboot 1회. 부팅 팝업은 `취소`만 사용하고 simplemode top/role을 다시 확인한다. 재발 시 STOP.
3. **normal mode reset:** execution gate에 포함된 SwitchMode simple 복귀만 시도. 실패 시 STOP.
4. **타일·단축 다이얼·시계 설정 소실:** §9.3 diff로 정확히 NOTE. 자동 app-data rollback은 없으며 시험단말 수용 여부를 사용자에게 재판정 요청한다.
5. **HOME role 소실:** system chooser/role 복구는 명시 승인 시에만 수행. 임의 `cmd role add-role-holder` 금지.
6. **p3 stale 지속:** 추가 clear 반복 금지. launcher 외 저장소 가설로 종료하고 최후 수단을 별도 논의한다.

### 9.8 Phase-2·fixture 종료 연계 옵션

후속 실행 게이트는 아래 중 하나를 명시적으로 선택해야 한다.

- **G1 — clear/검증만 (권장):** primary success에서 빈 p3로 종료하고 Phase-2는 별도 승인. 영향 범위를 가장 먼저 고정한다.
- **G2 — clear 성공 시 Phase-2 연속:** PFWSEED 5장 setup → picker에서 P1~P5만 `5/10` 선택/저장 → PFW_010/011/013/014/015/022 focus·화살표·rotation 실측. primary success가 아니면 Phase-2 진입 금지.
- G2의 **fixture 종료 정책**도 함께 고정한다.
  - **T1 clean teardown (권장):** 실측 후 media가 존재하는 상태에서 검증된 `pm clear`를 두 번째 1회 실행해 위젯 구성을 제거 → 빈 p3 확인 → `reset_pfwseed_f0.py` → MediaStore 10/`PFWSEED` 0/full invariants.
  - **T2 persistent fixture:** PFWSEED 5장과 구성 위젯을 의도적으로 유지. 이는 baseline 영구 변경이므로 별도 명시 승인과 후속 세션용 새 baseline 문서가 필요하다.

어느 옵션도 oracle authoring 또는 `RUNNABLE_NOW` 승격을 자동 승인하지 않는다. 모든 실행 결과는 `manual evidence observed`로 남기며 oracle 백필은 기존 §6의 별도 slice다.

### 9.9 실행 게이트 필수 승인 항목

승인문에는 최소한 ① `pm clear` 1회, ② first-run 최소 confirm/simple-mode 선택/role 복구 허용 범위, ③ SwitchMode 복구 허용 여부, ④ crash 시 reboot 1회, ⑤ G1 또는 G2, ⑥ G2라면 T1 또는 T2를 명시한다. 누락 항목은 fail-closed로 실행하지 않는다.
