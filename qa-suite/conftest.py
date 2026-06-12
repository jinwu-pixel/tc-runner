# qa-suite/conftest.py — 호스트(tc-runner) bare pytest 와의 수집 격리
#
# automation/tests 는 단말용 테스트 모듈 패키지(패키지명 tests)로, tc-runner 루트의
# tests/ 패키지와 이름이 충돌한다. pytest 의 Package 수집이 __init__ 을 import 하며
# sys.modules["tests"] 를 선점해 루트 스위트 전체의 import 를 깨뜨리므로
# (qa-suite 가 알파벳 순으로 먼저 수집됨), 해당 패키지를 수집에서 제외한다.
# qa-suite 프레임워크 self-test 는 별도 진입점으로 실행한다:
#   pytest qa-suite/automation/selftest
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
collect_ignore = [os.path.join(_HERE, "automation", "tests")]
