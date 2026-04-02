# run 커맨드 엑셀 직접 실행 — 설계 문서

## 개요

기존 `run` 커맨드를 확장하여 `.xlsx` 파일을 직접 지정하면 변환 → 실행 → 리포트까지 한 번에 처리한다.

## 범위

- **대상:** `src/cli.py`의 `cmd_run()` 함수 확장
- **비대상:** 기존 모듈(`excel_converter.py`, `action_runner.py`, `reporter.py`) 수정 없음
- **비대상:** 실시간 모니터링, 웹 UI (보류)

## 사용법

```bash
# 엑셀 직접 실행 — 변환 + 실행 + 리포트 한 번에
python -m src.cli run tc_list.xlsx

# 기존 YAML도 그대로 동작
python -m src.cli run tc_samples/*.yaml

# 혼합 가능
python -m src.cli run tc_list.xlsx extra_test.yaml
```

## 동작 흐름

1. `run`에 전달된 파일 목록을 확장자별로 분류 (`.xlsx` vs `.yaml`/`.yml`)
2. `.xlsx` 파일 → `convert_excel_to_yaml()`로 임시 디렉토리(`tempfile.mkdtemp()`)에 YAML 변환
3. 변환된 YAML 목록 + 직접 지정된 YAML 목록을 합침
4. 합친 목록으로 기존 실행 로직 수행 (ActionRunner, Reporter)
5. 실행 완료 후 임시 디렉토리 자동 삭제 (`shutil.rmtree()`)
6. 터미널 요약 + HTML 리포트 출력 (기존과 동일)

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/cli.py` | `cmd_run()`에 .xlsx 감지 + 임시 변환 + 정리 로직 추가 |
| `tests/test_cli.py` | 새 파일. 엑셀 입력 시 변환 → 실행 흐름 검증 |

## 기존 모듈 변경 없음

- `src/excel_converter.py` — 그대로 사용
- `src/action_runner.py` — 그대로 사용
- `src/reporter.py` — 그대로 사용
- `src/tc_loader.py` — 그대로 사용

## 에러 처리

- `.xlsx` 파일이 존재하지 않으면: 기존 에러 메시지 ("T/C 파일을 찾을 수 없습니다")
- 엑셀 변환 실패 시: 에러 메시지 출력 후 해당 파일 스킵, 나머지 파일 계속 실행
- 변환된 YAML이 0개인 경우: 다른 YAML 파일이 있으면 그것만 실행, 전체 0개면 기존 에러 처리

## 임시 파일 관리

- `tempfile.mkdtemp(prefix="tc_runner_")` 로 임시 디렉토리 생성
- 실행 완료 후 `finally` 블록에서 `shutil.rmtree()`로 삭제
- 비정상 종료(Ctrl+C 등)에도 정리되도록 `try/finally` 사용

## 의존성

추가 의존성 없음. 기존 `tempfile`, `shutil`은 Python 표준 라이브러리.
