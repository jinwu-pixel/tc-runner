# BUG #26510 수정 빌드 검증 — 수정 前 baseline (양산 Z0116_MP)

- **측정일**: 2026-07-21
- **단말**: `B2700125BW000083`
- **빌드**: `SELJY072512MZ0116` / `ro.build.date` = Fri Jan 16 02:38:52 CST 2026 / `sys_mssi_32_ago_h_ww-userdebug 14 UP1A.231005.007 release-keys`
- **앱 버전**: `com.android.dialer` 1.0.0.1414 · `com.hnlens.simplemode` 1.0.5.597 · `com.hnlens.launcher3` 9.0.1.1073
  - → 2026-07-15 `version_compare_2026-07-15/prod_115/P0_versions.txt` 양산 캡처와 **동일 버전 조합**
- **HOME role**: `com.hnlens.launcher3` (노말 모드로 전환 후 측정)
- **판정**: `BUG-GAP observed` — 수정 前 divergence **재현 확정**

---

## 1. 데이터 주입 내역

| 출처 | 방법 | 건수 |
|---|---|---|
| 실 착신 부재중 | 타 단말 발신 → 미응답 | 3 |
| 툴 삽입 | `Batchuserdata` v1.1 (`com.ben.batchuserdata`, `.MainActivity`) | 7 (타입 랜덤) |

툴은 본 세션에서 `adb install -r -g` 로 설치 (설치 전 `type=3` 0건 = 클린 baseline 확인 완료).
`WRITE_CALL_LOG` / `READ_CALL_LOG` granted=true.

## 2. call_log 전 행 덤프 (측정)

```
Row: 0 _id=1,  number=01020954744, type=3, is_read=0,    new=1, date=1784613873421
Row: 1 _id=2,  number=01029170913, type=3, is_read=0,    new=1, date=1784613884842
Row: 2 _id=3,  number=01029170913, type=3, is_read=0,    new=1, date=1784613890319
Row: 3 _id=4,  number=13626746277, type=3, is_read=NULL, new=0, date=1784520052622
Row: 4 _id=5,  number=13600877537, type=1, is_read=NULL, new=0, date=1784534736494
Row: 5 _id=6,  number=13630770374, type=1, is_read=NULL, new=0, date=1784604057574
Row: 6 _id=7,  number=13625308733, type=1, is_read=NULL, new=0, date=1784603605556
Row: 7 _id=8,  number=13626682307, type=3, is_read=NULL, new=0, date=1784598816046
Row: 8 _id=9,  number=13652254733, type=3, is_read=NULL, new=0, date=1784542908294
Row: 9 _id=10, number=13615316202, type=1, is_read=NULL, new=0, date=1784576511159
```

**행 구성**: 총 10행 = 실 착신 3 (`_id` 1–3, `is_read=0`, `new=1`) + 툴 7 (`_id` 4–10, `is_read=NULL`, `new=0`).
툴 7건 중 **부재중(type=3) 3건 / 수신(type=1) 4건** — 툴이 타입을 랜덤 삽입함(신규 관찰, 2026-07-16 문서에 없던 사실).

## 3. 술어별 카운트 (단말 SQLite 실측, `type=3` 기준)

| 술어 | 결과 | 대응 |
|---|---|---|
| `is_read = 0` | **3** | 노말 런처 쿼리 → 화면 표시 3 |
| `is_read IS NULL` | 3 | 툴 삽입분 |
| `is_read IS NOT 1` (null-safe) | **6** | 심플/미러 쿼리 → 화면 표시 6 |
| `is_read != 1` | 3 | NULL 제외 (문자 그대로면 갭 미형성) |
| `is_read <> 1` | 3 | 〃 |
| `type=3` 전체 | 6 | — |

## 4. UI 관측 (사용자 육안 + 스크린샷)

- 노말 모드 배지 = **3**
- 심플 모드 배지 = **6**
- → DB 카운트와 1:1 일치. **divergence 폭 3 = 툴이 만든 `is_read=NULL` 부재중 3건**

## 5. 미확보 항목 (정직 표기)

- **본 단말에서의 런처 SQL 원문 logcat 직접 캡처 = 미확보** (측정 승인 전 단말 종료). 대체 근거 =
  동일 빌드·동일 앱버전(launcher3 9.0.1.1073, Jan 16)에서 캡처된
  `version_compare_2026-07-15/prod_115/P1_launcher_mirror.txt`:
  `getUnreadMissedCallCount Query String: SELECT _id, type, is_read FROM calls WHERE type = ? AND is_read = ? ORDER BY date DESC`
- bugreport 미수집 (수정 前)
- AP 오프라인 로깅은 사용자가 종료 직전 ON (로그 pull은 업데이트 후 수행)

## 6. 수정 빌드 판정표

업데이트는 **데이터 보존** 방식 → 위 10행이 그대로 유지되어야 함(첫 확인 항목).

| 업데이트 後 노말/심플 | 해석 |
|---|---|
| **6 / 6** | 노말을 `IS NOT 1`(NULL=미확인)로 올려 정합 |
| **3 / 3** | 심플을 `= 0` / `!= 1`(NULL=제외)로 내려 정합 |
| **3 / 6 유지** | 미수정 |
| 행 집합 소실 (`type=3` ≠ 6) | 대조 불가 → 재주입 후 재측정 |
| 그 외 | 별도 해석 |

**주의 (baseline 파괴 요인)**: 첫 부팅 후 콜로그 목록 / 다이얼러 Recent 탭 진입 시
`is_read=0` 실 착신 3건이 bulk clear(→`is_read=1`)되어 대조군이 소실됨. 측정 완료 전 진입 금지.

## 7. 업데이트 後 측정 체크리스트

1. 지문: build display id / incremental / date + 3개 pkg versionName
2. call_log 전 행 덤프 → **10행 보존 여부 · `_id` 유지 여부**
3. 술어별 카운트 6종 재측정 (§3 동일)
4. logcat 카운터 + **런처 SQL 원문** (툴 행 `new` no-op 토글로 ContentObserver 유도)
5. AP 오프라인 로그 pull → **첫 부팅 구간 카운터 초기 로드** 파싱 (adb blind window 보완)
6. 배지 스크린샷 (홈 + 다이얼러 메인 Recent 탭 배지, **탭 진입 금지**)
7. 회귀축: 실 착신 1건 추가 → 양쪽 +1 / 개별 항목 탭 확인 → 양쪽 −1
8. 재부팅 1회 → drift 없음 확인

## 8. 측정 함정 (본 세션 실측)

- **PowerShell에서 `--where "type=3 AND is_read=0"` 은 인용부호가 소실되어 결과 0을 반환** (조용한 오답).
  다중 토큰 where 절은 **Bash 도구 경유** 또는 전 행 덤프 후 호스트측 파싱으로 계산할 것.
  단일 토큰(`type=3`)은 PowerShell에서도 통과 → 부분 성공이 오판을 부름.
- 카운터 로그는 이벤트 발생 시에만 출력 → 유휴 상태 `logcat -d` 에는 없음. no-op 쓰기로 ContentObserver 유도 필요.
