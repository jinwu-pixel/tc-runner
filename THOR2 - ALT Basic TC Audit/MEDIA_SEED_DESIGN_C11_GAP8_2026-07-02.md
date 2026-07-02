# MEDIA_SEED_DESIGN — C11 gap-8 사진 세팅 precondition 설계 (2026-07-02)

**상태: 설계안 — 단말 실행은 사용자 승인 후.** 대상 = C11 잔여 8건의 공통 게이트 해제.

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
