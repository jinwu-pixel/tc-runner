# Dual TC Approach Design: Manual YAML + Semantic Mapping

## Problem

TC_1.xlsx의 절차 텍스트("앱 실행", "권한 거부" 등)는 **테스터를 위한 지시문**이지 실제 UI 요소 텍스트가 아니다. 현재 MMI 변환기는 이를 그대로 `tap_text` 액션으로 변환하여 실제 앱에서 FAIL이 발생한다.

예: `"앱 실행"` → `tap_text("앱")` → 화면에 "앱"이라는 요소 없음 → FAIL

## Solution: 두 가지 접근법 병행

### 접근법 1: 앱별 수동 TC YAML

**대상:** SeniorShield(시니어쉴드) 앱  
**패키지:** `com.example.seniorshield`

`app_analysis.txt`에서 파악된 실제 UI 구조 기반으로 5개 TC YAML 작성:

| TC | 시나리오 | 주요 액션 |
|----|---------|----------|
| TC_SS_01 | 앱 실행 + 메인화면 확인 | shell am start → verify_text ×5 |
| TC_SS_02 | 가족에게 바로 연락하기 진입 | tap_text → verify_text ×4 |
| TC_SS_03 | 전체 감지 기록 보기 진입 | tap_text → verify_text ×3 |
| TC_SS_04 | 보이스피싱 대응 연습 진입 | tap_text → verify_text ×3 |
| TC_SS_05 | 전체 화면 순회 (end-to-end) | shell → tap ×4 → verify ×N → key BACK |

모든 YAML은 `exported_tc1/` 디렉토리에 저장.

### 접근법 2: 시맨틱 매핑 파이프라인 개선

절차 텍스트의 **의미(semantic)**를 파악하여 올바른 ADB 액션으로 변환.

#### 2.1 새로운 Intent 타입 추가 (`models.py`)

```python
# 기존: navigate, tap_text, tap_id, toggle, press_key, input_text, wait,
#       verify_text, verify_shell, manual_required
# 추가:
"app_launch"       # "앱 실행", "앱을 실행한다"
"app_close"        # "앱 종료", "앱을 닫는다"
"navigate_back"    # "뒤로가기", "이전 화면으로"
```

#### 2.2 시맨틱 패턴 (`step_classifier.py`)

`_SEMANTIC_PATTERNS` dict를 추가하여 절차 텍스트의 의미를 분류:

```python
_SEMANTIC_PATTERNS = {
    "app_launch": [r"앱\s*실행", r"앱을?\s*(열|켜|실행)", r"실행\s*한다"],
    "app_close":  [r"앱\s*종료", r"종료\s*한다", r"앱을?\s*닫"],
    "navigate_back": [r"뒤로\s*가기", r"이전\s*화면", r"뒤로\s*이동"],
}
```

#### 2.3 컴파일러 핸들러 (`compiler.py`)

새 intent 타입에 대한 컴파일 핸들러 추가:

- `app_launch` → `shell("am start -n {package}/.MainActivity")`
- `app_close` → `shell("am force-stop {package}")`
- `navigate_back` → `key("BACK")`

#### 2.4 앱 컨텍스트 전달

`convert_row(row, app_context=None)` 시그니처에 optional app_context dict 추가:

```python
app_context = {
    "package_name": "com.example.seniorshield",
    "main_activity": ".MainActivity",
}
```

## 파일 영향 범위

| 파일 | 변경 내용 |
|------|----------|
| `src/mmi_converter/models.py` | IntentType에 3개 타입 추가 |
| `src/mmi_converter/step_classifier.py` | 시맨틱 패턴 dict + classify에서 패턴 매칭 |
| `src/mmi_converter/compiler.py` | compile_classified에 3개 핸들러 추가 |
| `src/mmi_converter/service.py` | app_context 파라미터 전달 |
| `exported_tc1/*.yaml` | SeniorShield TC YAML 5개 |
| `tests/test_mmi_compiler.py` | 시맨틱 매핑 테스트 |
| `tests/test_step_classifier.py` | 시맨틱 분류 테스트 |

## 설계 원칙

1. **기존 동작 유지**: 새 패턴에 매칭되지 않는 텍스트는 기존 로직 그대로
2. **app_context는 optional**: 제공되지 않으면 시맨틱 매핑 중 패키지 필요한 것은 fallback
3. **패턴 우선순위**: 시맨틱 패턴 → 기존 키워드 매칭 → fallback
