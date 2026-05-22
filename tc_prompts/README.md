# TC 변환 표준 프롬프트 세트

## 파일 구성

```
tc_prompts/
├── STAGE1_NORMALIZE.md           ← 1단계: 원본 TC → CTF 정규화
├── STAGE2_COMPILE.md             ← 2단계: CTF → 실행 TC 컴파일
├── OPERATIONAL_RULES.md          ← 공통 운영 규칙 (항상 뒤에 붙임)
├── device_profile_template.yaml  ← 단말 프로필 템플릿
├── runner_capability_template.yaml ← 러너 환경 템플릿
└── README.md                     ← 이 파일
```

## 사용법

### 1단계: 정규화

```
클로드코드에게 전달:
  1. STAGE1_NORMALIZE.md (전문)
  2. OPERATIONAL_RULES.md (전문)
  3. 원본 TC (엑셀 또는 텍스트)

결과물:
  - {tc_id}_canonical.yaml (TC당 1개)
  - normalization_report.md (시트당 1개)
```

### 2단계: 컴파일

```
클로드코드에게 전달:
  1. STAGE2_COMPILE.md (전문)
  2. OPERATIONAL_RULES.md (전문)
  3. {tc_id}_canonical.yaml (1단계 결과)
  4. device_profile.yaml (대상 단말)
  5. runner_capability.yaml (러너 환경)

결과물:
  - execution_plan.yaml
  - compiled_tc.yaml
  - validation_report.md
```

### 검증

```bash
# compiled_tc.yaml 스키마 검증
python validate_tc.py compiled_tc.yaml

# 골든 TC와 구조 비교
python validate_tc.py --dir golden_tc_set/
```

## 전체 파이프라인

```
원본 TC
  │
  ▼
[1단계] STAGE1_NORMALIZE.md + OPERATIONAL_RULES.md
  │
  ├─→ canonical_tc.yaml        (중간 표현, 실행 불가)
  └─→ normalization_report.md  (정규화 품질 리포트)
  │
  ▼
[2단계] STAGE2_COMPILE.md + OPERATIONAL_RULES.md
        + device_profile.yaml
        + runner_capability.yaml
  │
  ├─→ execution_plan.yaml      (실행 계획)
  ├─→ compiled_tc.yaml         (실행 TC)
  └─→ validation_report.md     (컴파일 품질 리포트)
  │
  ▼
[검증] validate_tc.py + tc_step_schema.json
  │
  ├─ PASS → tc-runner로 실행
  └─ FAIL → 에러 메시지로 2단계 재실행
```

## 이전 산출물과의 관계

| 파일 | 역할 | 위치 |
|------|------|------|
| tc_step_schema.json | compiled_tc.yaml 검증용 JSON Schema | 프로젝트 루트 |
| validate_tc.py | 스키마 검증 스크립트 | 프로젝트 루트 |
| golden_tc_set/ | 변환 결과 레퍼런스 (few-shot 예시) | 프로젝트 루트 |
| tc_prompts/ | 이 프롬프트 세트 | 프로젝트 루트 또는 CLAUDE.md에 인라인 |

## 단말 프로필 만드는 법

실제 단말에서:

```bash
# 기본 정보
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.display.id

# 설치된 패키지 목록
adb shell pm list packages -3

# 특정 앱의 main activity 찾기
adb shell dumpsys package com.kakao.talk | grep -A1 "android.intent.action.MAIN"

# root 가용 여부
adb shell whoami
```

결과를 `device_profile_template.yaml`에 채워서 사용하세요.
