# THOR2_J - Settings · BUG_LOG

단말: THOR2_J (AT-M140 ja-JP) · `com.android.settings` v14

## 요약표

| ID | 기능 영역 | 상태 | 요약 | 관련 TC | 증거 |
|----|-----------|------|------|---------|------|
| —  | —         | —    | (현재 발견 없음) | — | — |

## 본문

(현재 항목 없음 — Phase 0 단계, SMOKE 미실행)

---

## 세션 결과

### 2026-05-08 Phase 0
- 실행일: 2026-05-08
- 단말: THOR2_J (AT-M140 ja-JP) B2700125BW000083
- 앱: com.android.settings v14
- 범위: home probe 1회 (ja-JP locale)
- PASS: launch + foreground 확인 (manual evidence observed)
- 신규 발견: —
- 변경·정정: —
- 다음 확인 항목: SMOKE_01 validate + runtime 진입

### 2026-05-08 SMOKE_01 + SMOKE_02
- 실행일: 2026-05-08
- 단말: THOR2_J (AT-M140 ja-JP) B2700125BW000083
- 앱: com.android.settings v14
- 범위: SMOKE_01 ROOT 6 anchor / SMOKE_02 scroll + post-scroll 2 anchor
- PASS: SMOKE_01 runtime 11/11 (20.6s), SMOKE_02 runtime 13/13 (20.0s)
- 신규 발견: —
- 변경·정정: —
- 다음 확인 항목: SMOKE_03 후보 (추가 scroll → `バッテリー` / `ストレージ` anchor 발굴), 또는 단말 횡 비교 PR 7B fixture 후보 (locale_change 시드)

### 2026-05-08 단말 횡 비교 측정 (PR 7A delta tool)
- 실행일: 2026-05-08
- 도구: `tools/synthetic_delta_measure.py`
- 입력: `ODIN2 - Settings/probe_settings_home.xml` (before, ko-KR) vs `THOR2_J - Settings/probe_settings_home.xml` (after, ja-JP)
- target: `설정` (한글 anchor)
- 결과:
  - verdict: `meaningful_delta` (정확)
  - xml_sha256.equal: false
  - visible_texts: before 17 / after 9, jaccard 0.0 (완전 turnover)
  - target.before: true / target.after: false (한글 anchor가 ja 단말에서 부재 — 단말 횡 적용 시 FAIL 시그널 정확)
- 의미: PR 7A delta tool이 locale 전환을 첫 실 사용 사례에서 정확 분류 — synthetic fixture 외 실 dump 입력에서도 동작 확인
