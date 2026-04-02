# Android T/C 자동 실행 도구 — 설계 문서

## 개요

USB로 연결된 안드로이드 실단말에 YAML 기반 테스트 케이스(T/C)를 자동 실행하고, 결과를 실시간 터미널 출력 + HTML 리포트로 제공하는 CLI 도구.

## 범위

- **대상:** USB로 연결된 안드로이드 단말 1대 (ADB 통신)
- **비대상:** 여러 단말 동시 병렬 실행 (추후 확장 가능성만 염두)
- **비대상:** MTP 장치, 에뮬레이터 (ADB 연결 가능한 실단말만)

## 기술 스택

- **Python 3.12** — 메인 언어
- **ADB (Android Debug Bridge)** — 단말 제어 (시스템에 설치 필요)
- **PyYAML** — T/C 파일 파싱
- **openpyxl** — 엑셀 → YAML 변환
- **Jinja2** — HTML 리포트 생성

## YAML T/C 형식

```yaml
name: Wi-Fi 연결 테스트
description: Wi-Fi를 켜고 연결 상태를 확인한다
steps:
  - action: tap_text
    text: "설정"

  - action: tap_text
    text: "연결"

  - action: tap_text
    text: "Wi-Fi"

  - action: wait
    seconds: 2

  - action: verify_text
    text: "연결됨"

  - action: verify_shell
    command: "dumpsys wifi | grep 'Wi-Fi is'"
    expected: "enabled"
```

### 지원 Action 목록

| Action | 필수 파라미터 | 선택 파라미터 | 설명 |
|--------|-------------|-------------|------|
| `tap_text` | `text` | `timeout` | 화면에서 텍스트를 찾아 터치 |
| `tap_id` | `id` | `timeout` | resource-id로 요소를 찾아 터치 |
| `tap_xy` | `x`, `y` | - | 좌표 직접 터치 |
| `swipe` | `x1`, `y1`, `x2`, `y2` | `duration` | 스와이프 동작 |
| `key` | `keycode` | - | 하드키 입력 (HOME, BACK, ENTER 등) |
| `shell` | `command` | - | ADB shell 명령 실행 |
| `wait` | `seconds` | - | N초 대기 |
| `screenshot` | - | `name` | 스크린샷 저장 |
| `verify_text` | `text` | `timeout` | 화면에 특정 텍스트가 있는지 확인 (PASS/FAIL) |
| `verify_shell` | `command`, `expected` | - | shell 명령 결과에 특정 문자열 포함 확인 (PASS/FAIL) |
| `input_text` | `text` | - | 텍스트 입력 |

### 공통 파라미터

- `timeout`: 요소를 찾을 때 최대 대기 시간 (기본값 10초, YAML에서 override 가능)
- `tap_text`/`tap_id`/`verify_text`는 요소를 못 찾으면 1초 간격으로 최대 3회 재시도 후 FAIL

## 아키텍처

7개 모듈로 구성한다:

| 모듈 | 역할 |
|------|------|
| `src/cli.py` | CLI 진입점 (argparse). run, convert, devices 서브커맨드 |
| `src/adb.py` | ADB 명령 래퍼. shell, tap, swipe, key, screenshot, 연결 확인 |
| `src/ui_parser.py` | uiautomator dump XML 파싱. text/resource-id로 요소 좌표 찾기 |
| `src/action_runner.py` | YAML의 각 action을 실행하는 엔진. adb + ui_parser 호출 |
| `src/tc_loader.py` | YAML T/C 파일 로드 및 검증 |
| `src/excel_converter.py` | 엑셀 → YAML 변환 |
| `src/reporter.py` | 실시간 터미널 출력 + HTML 리포트 생성 (Jinja2) |

### 데이터 흐름

1. CLI에서 YAML T/C 파일 경로 지정
2. `tc_loader`가 YAML을 파싱하여 테스트 케이스 목록 생성
3. `action_runner`가 각 step을 순차 실행 — `adb`와 `ui_parser` 호출
4. 각 step 결과를 `reporter`에 전달 (실시간 터미널 출력)
5. 전체 완료 후 `reporter`가 HTML 리포트 생성

## CLI 인터페이스

```bash
# T/C 실행
python -m src.cli run wifi_test.yaml

# 여러 T/C 실행
python -m src.cli run tc_samples/*.yaml

# 엑셀 → YAML 변환
python -m src.cli convert tc_list.xlsx -o tc_samples/

# 연결된 단말 확인
python -m src.cli devices
```

## 엑셀 → YAML 변환

엑셀 T/C를 YAML로 변환하는 규칙:

- 엑셀 시트의 각 행이 하나의 step
- 컬럼 매핑: `Action` 열 → action 타입, `Parameter` 열 → 파라미터, `Expected` 열 → 기대 결과
- 변환 시 사용자에게 컬럼 매핑을 확인받거나, 표준 템플릿에 맞춘 엑셀 형식을 제공
- 변환 결과를 지정된 출력 디렉토리에 YAML 파일로 저장

### 표준 엑셀 템플릿 컬럼

| TC Name | Step | Action | Parameter1 | Parameter2 | Expected |
|---------|------|--------|-----------|-----------|----------|
| Wi-Fi 테스트 | 1 | tap_text | 설정 | | |
| Wi-Fi 테스트 | 2 | tap_text | Wi-Fi | | |
| Wi-Fi 테스트 | 3 | verify_text | 연결됨 | | |

- 같은 `TC Name`의 행들이 하나의 YAML T/C 파일로 묶임
- `Action` 값은 YAML action 이름과 동일
- `Parameter1`은 해당 action의 주요 파라미터 (text, id, x, command 등)
- `Parameter2`는 보조 파라미터 (y, expected, seconds 등)

## 에러 처리

- **단말 미연결:** 실행 전 `adb devices`로 연결 상태 확인, 미연결 시 명확한 에러 메시지
- **요소 못 찾음:** `tap_text`/`tap_id`/`verify_text`에서 요소를 못 찾으면 1초 간격 재시도 (최대 3회) 후 FAIL
- **타임아웃:** 각 step에 기본 타임아웃 10초 (YAML에서 override 가능)
- **step 실패 시:** 스크린샷 자동 캡처, 해당 step FAIL 기록 후 다음 T/C로 진행 (하나 실패해도 전체 중단하지 않음)
- **ADB 명령 실패:** 명령 실행 자체가 실패하면 (timeout, connection lost) 해당 step FAIL + 에러 메시지 기록

## HTML 리포트

### 리포트 내용

- **헤더:** 실행 일시, 단말 모델명 (`ro.product.model`), 안드로이드 버전 (`ro.build.version.release`)
- **요약:** 총 N개 T/C, PASS X개, FAIL Y개, 성공률
- **T/C별 상세:**
  - T/C 이름, 설명
  - 각 step: action, 파라미터, 결과 (PASS/FAIL), 소요 시간
  - 실패한 step: 스크린샷 이미지 임베드 + 에러 메시지
- **스크린샷:** Base64로 인코딩하여 HTML에 임베드 (단일 파일로 공유 가능)

### 리포트 파일

`reports/YYYYMMDD_HHMMSS_report.html` 형식으로 저장

## 의존성

| 패키지 | 용도 |
|--------|------|
| `PyYAML` | YAML T/C 파일 파싱 |
| `openpyxl` | 엑셀 → YAML 변환 |
| `Jinja2` | HTML 리포트 생성 |
| `pytest` | 테스트 |

### 시스템 요구사항

- Python 3.12 이상
- ADB (Android SDK Platform Tools) 설치 및 PATH 등록
- USB 디버깅 활성화된 안드로이드 단말
