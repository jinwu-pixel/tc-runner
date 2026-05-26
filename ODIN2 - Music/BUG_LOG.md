# ODIN2 - Music · BUG_LOG

| ID | 기능 영역 | 상태 | 요약 | 관련 TC | 증거 |
|----|----------|------|------|---------|------|

> Phase 0~1A 진행. 발견된 버그 없음.

## NOTE (2026-04-30)
- delta verdict `changed_texts` jaccard=1.0 / added=removed=[] 가 같은 cold-launch에서 발생.
  텍스트 set 동일하지만 xml_sha256/screen_id 다름 → UI 구조 미세 변화 또는 prebuilt id 변동.
  버그 아님. PR 4 verdict 분류 알고리즘 evidence 로 의미 있음. SMOKE_02 작성 시 동일 패턴 반복되는지 확인 필요.
- BT 오디오 연결 해제 상태에서 player surface 진입 후 `media_session state=ERROR(7), error="블루투스 오디오가 연결 해제됨"`이 관찰됨.
  SMOKE_03은 playback 지속 검증이 아니라 player surface 진입 검증으로 제한한다.
  앱 버그가 아니라 단말 환경(BT 라우팅 부재) 부수효과로 분류. 향후 BT 연결 또는 헤드셋 환경에서 재확인 시 별도 evidence 수집 가능.

## 세션 결과
- 실행일: 2026-04-30
- 단말: ODIN2 (AT-M150) <device_serial>
- 앱: com.mive.music v1.0.2604231952
- 범위: Phase 0 preflight seed (Step 1~10)
- PASS: —
- 신규 발견: —
- 변경·정정: —
- 다음 확인 항목: Phase 1 SMOKE 5건 작성 대상 식별

## 세션 결과
- 실행일: 2026-05-11
- 단말: ODIN2 (AT-M150) <device_serial>
- 앱: com.mive.music v1.0.2604231952
- 범위: Phase 1C SMOKE_03 runtime (player surface 진입 검증, mutation 0)
- PASS: MUSIC_SMOKE_03 runtime 12/12 (22.5s)
- 신규 발견: —
- 변경·정정: Phase 1C runtime gate closed (RESUME.md 갱신)
- 다음 확인 항목: SMOKE_04 후보 검토 또는 PR 7B locale_change synthetic fixture scope

## 세션 결과
- 실행일: 2026-05-11
- 단말: ODIN2 (AT-M150) <device_serial>
- 앱: com.mive.music v1.0.2604231952
- 범위: Phase 1D SMOKE_04 runtime (IME focus 검증, mutation LOW)
- PASS: MUSIC_SMOKE_04 runtime 13/13 (13.8s, 단말 wake + dismiss-keyguard 후 재실행)
- 신규 발견: —
- 변경·정정: Phase 1D 섹션 RESUME.md 신규 추가
- 운영 NOTE: 단말 long-idle 후 monkey LAUNCHER 만으로는 wake 보장 안 됨 (첫 시도 Step 4 FAIL → wake + dismiss-keyguard 후 PASS). yaml precondition "keyguard 해제 상태" 만족 책임은 단말 운영 영역
- 다음 확인 항목: SMOKE_05 후보 보고 (검색 query 입력 — search history risk 분류 필요)
