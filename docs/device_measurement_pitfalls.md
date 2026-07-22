# 단말 측정 함정 모음 (횡단 자산)

> 이슈·앱·모델 무관. **호스트에서 adb로 단말을 측정할 때** 조용히 오답을 만드는 함정만 모은다.
> 정립 계기: BUG #26510 부재중 배지 검증 (2026-07-13 ~ 07-22). 이후 신규 함정 발견 시 append.
> 관련: CLAUDE.md §5.5(bat·환경 함정) · `docs/talkback_dpad_verification.md`(a11y 특이 함정)

**공통 성질**: 아래 함정은 전부 **에러를 내지 않는다.** 실패가 예외가 아니라 *그럴듯한 값*으로 나타나기 때문에,
"측정했더니 문제 없었다"가 실은 "측정 자체가 실패했다"인 경우를 만든다. 음성 결과(차이 없음)를 근거로
쓰기 전에 **계측이 살아 있다는 증거**를 먼저 확보할 것.

---

## 1. 호스트 셸 함정

### 1.1 PowerShell 다중 토큰 인용 소실 → 조용한 0 ★

```powershell
# 실패 (조용히 0행 반환)
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where `"type=3 AND is_read=0`""
```

- **증상**: 결과가 `No result found.` → 코드가 이를 "해당 행 0건"으로 집계 → **"조건에 맞는 데이터 없음 = 정상"** 오판
- **원인**: PS 5.1이 네이티브 exe로 인자를 넘길 때 내부 큰따옴표가 벗겨져, device shell이 `--where type=3` + 잔여 토큰으로 파싱
- **결정적 위험**: **단일 토큰(`type=3`)은 통과한다.** 부분 성공이라 함정을 눈치채기 어렵다
- **회피**: 다중 조건은 **Bash 도구 경유**, 또는 전 행 덤프 후 호스트에서 파싱

```bash
# 안전
adb -s $S shell "content query --uri content://call_log/calls --projection _id --where \"type=3 AND is_read=0\""
```

- **자기검증**: 술어별 카운트의 **산술 정합**을 확인한다. `A=0` + `A IS NULL` + `A=1` = `total` 이 안 맞으면 인용이 깨진 것

### 1.2 바이너리 리다이렉션 손상

```powershell
adb -s $S exec-out screencap -p > shot.png   # ✗ BOM 삽입으로 PNG 헤더 파손
```

- **증상**: 파일 크기는 정상인데 이미지 뷰어·Read 도구가 "PNG 아님"으로 거부. 헤더가 `ef bb bf ef bf bd 50 4e`
- **회피**: **Bash 경유** (`adb ... > shot.png`), 또는 `adb shell screencap -p /data/local/tmp/x.png` + `adb pull`
- **검증**: `head -c 8 shot.png | xxd` → `8950 4e47 0d0a 1a0a` 이어야 함

### 1.3 Git Bash 경로 mangling

- MSYS가 `/sdcard`·`/data/local/tmp`를 Windows 경로로 변환해 device 경로가 깨진다
- 단, `content://...` 처럼 `/`로 시작하지 않는 인자는 안전
- **회피**: device 경로가 인자에 있으면 PowerShell 사용, 또는 python `subprocess`(리스트 인자)

---

## 2. 관측 대상 함정 — "무엇을 보고 있는가"

### 2.1 DB 변경이 UI에 반영되지 않는다 ★★

- **증상**: `content insert`/`update`로 DB를 바꿨는데 **카운터·배지는 갱신되지만 목록 화면은 그대로**
- **관측 사례**: 콜로그에 행을 삽입 → 배지는 즉시 증가, 목록에는 미표시. 앱 `force-stop` 후 재기동해도 미갱신인 경우가 있었고, 다른 시점에는 정상 표시됨(앱이 자체 캐시 테이블에서 목록을 그리기 때문)
- **결과**: 화면을 보고 "이 상태에서는 이렇게 표시된다"고 판정하면 **틀린다**
- **원칙**: **카운터/DB는 adb 조작으로 검증해도 되지만, 화면의 시각 상태(굵기·배지 표시·정렬)는 반드시 UI 조작 경로로 만들어 판독한다**

### 2.2 합성 데이터가 실제 경로를 재현하지 못한다 ★★

- 리포터가 데이터를 만든 경로(툴 / 실 착신 / 복원 / 마이그레이션)를 **먼저 확정**하고, 그 삽입 방식(어떤 컬럼을 설정/미설정하는지)까지 정적 분석할 것
- **BUG #26510 실패 사례**: harness가 `content insert`에 `is_read:i:0`을 **명시** 삽입 → 실제 버그 데이터는 툴이 `is_read` **미설정**으로 넣은 `NULL`. harness가 NULL 조건을 못 만들어 30사이클 divergence 0 = **false-negative**
- **컬럼 기본값**: ContentResolver 직접 삽입 시 **미설정 컬럼은 NULL**(0 아님). 실제 telephony는 값을 채운다
- **삽입 행이 목록에 렌더링되지 않을 수 있다**(§2.1) → **표시 관련 검증은 실 착신으로**
- **UID 차이**: 앱 UID 삽입과 shell UID 삽입은 provider가 다르게 처리할 수 있다. 한쪽 결과로 다른 쪽을 일반화 금지

### 2.3 로그는 이벤트가 있을 때만 남는다

- 카운터류 로그는 **변경 이벤트 시에만** 출력. 유휴 상태에서 `logcat -d`를 떠도 값이 없다
- **회피**: 값을 바꾸지 않는 **no-op 쓰기**로 ContentObserver를 깨운다

```bash
adb -s $S logcat -c
adb -s $S shell 'content update --uri <uri> --bind <컬럼>:i:<현재값> --where "_id=<더미 id>"'
adb -s $S shell 'sleep 3'
adb -s $S logcat -d | grep -E "<시그니처>"
```

- **주의**: 프로브 컬럼이 측정 대상 술어에 포함되지 않는지 확인할 것(관측자 효과)
- **버퍼 유실**: 로그량이 많은 앱은 짧은 창에서도 evict된다. `logcat -c` 직후 조작 → 즉시 `-d`

### 2.4 동일 문자열을 여러 프로세스가 출력한다

- 같은 로그 문자열을 두 앱이 모두 찍는 경우, **태그·PID로 구분하지 않으면 A의 값을 B의 값으로 오독**
- 검증 사례: `getUnreadMissedCallCount cursor count:` 를 런처와 간편모드 앱이 모두 출력

---

## 3. UI 조작 함정

### 3.1 좌표 탭 연속 실행 금지 ★

- **증상**: 첫 탭으로 화면이 전환되어 레이아웃이 바뀌면 **두 번째 탭이 빗나가고**, 그 상태로 측정하면 한 사이클이 통째로 무효
- 실제 사례: 탭바 좌표를 연속 탭 → 키패드 화면이 탭바를 덮어 두 번째 탭이 허공. 그 상태의 DB를 "탭 전환 후"로 기록할 뻔함
- **위험**: 좌표에 따라 **발신 버튼·차단 등 파괴적 액션**이 있을 수 있다
- **원칙**: 탭 사이에 **스크린샷으로 화면 상태를 확인**한 뒤 다음 좌표를 정한다. 화면 확인 없이 블라인드 탭 금지

### 3.2 앱이 어느 화면으로 열리는지 보장되지 않는다

- 다이얼러류는 **마지막 사용 탭을 복원**한다. `am start`가 항상 같은 화면을 주지 않는다
- **회피**: 실행 후 `dumpsys window | grep mCurrentFocus` + 스크린샷으로 확인 후 진행

### 3.3 관측 행위가 상태를 바꾼다

- 목록 조회·알림 정리·항목 탭이 **읽음 처리 등 상태 변경을 유발**할 수 있다
- **원칙**: 측정 순서를 "비파괴 → 파괴" 로 배치. baseline 스냅샷을 **화면을 열기 전에** 확보
- a11y 계열: `uiautomator dump`가 TalkBack을 일시 억제한다(`docs/talkback_dpad_verification.md`)

---

## 4. 캡처 함정

### 4.1 가상 디스플레이는 screencap이 안 된다

- 폴더형 단말의 외부 화면은 virtual display(예: `LocalLsPresentation`)로 잡히고 `screencap -d <id>` 가 **0바이트**를 반환
- display id는 `dumpsys display`의 `DisplayViewport`/`DisplayDeviceInfo`에서 확인(내부 화면이 0, 외부가 1이 아닐 수 있음)
- **회피**: 해당 표면은 **육안 확인**으로 대체하고 `manual evidence observed`로 표기

### 4.2 0바이트 캡처를 증거로 남기지 말 것

- 실패한 캡처 파일은 즉시 삭제하고, "캡처 불가"라는 사실을 문서에 문장으로 남긴다

---

## 5. 측정 전 체크리스트

```
□ 시리얼 핀 고정 (adb -s <serial>) — 다중 단말 연결 시 오조작 방지
□ 빌드 지문 기록 (ro.build.version.incremental + 관련 앱 versionName)
□ baseline 스냅샷을 화면 열기 전에 확보
□ 술어 카운트의 산술 정합 확인 (인용 소실 자기검증)
□ 계측 민감도 증명 — 값이 실제로 움직이는 것을 한 번 보여준 뒤 음성 결과를 신뢰
□ 파괴적 조작은 마지막에 배치, 가역 여부 사전 확인
□ 실패 캡처·손상 파일 정리
```

## 6. 누적 규칙

- 새 함정 발견 시 **증상 / 원인 / 회피 / 근거 사례** 4항목으로 append
- 특정 이슈에서만 성립하는 내용은 여기 넣지 말고 해당 이슈 RESULT에 남긴다 — 이 문서는 **이슈 무관**이 조건
