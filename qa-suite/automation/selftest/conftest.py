# selftest conftest — automation/ 을 import 루트로 고정 (단말 호출 없는 프레임워크 self-test)
#
# 주의: automation/tests 패키지가 tc-runner 루트의 tests/ 패키지와 이름이 겹친다.
# 한 인터프리터에서 두 패키지가 같은 이름을 쓸 수 없으므로, selftest 는
#   pytest qa-suite/automation/selftest
# 처럼 경로를 명시한 호출에서만 수집·실행하고, 루트 bare pytest 혼합 수집에서는
# 자신을 제외해 기존 스위트를 보호한다.
import os
import sys

AUTOMATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _selftest_scoped(config):
    return any("selftest" in str(a) for a in config.invocation_params.args)


def pytest_configure(config):
    if _selftest_scoped(config) and AUTOMATION_DIR not in sys.path:
        sys.path.insert(0, AUTOMATION_DIR)


def pytest_ignore_collect(collection_path, config):
    if not _selftest_scoped(config):
        return True  # 혼합 수집 차단 — tests 패키지 이름 충돌 방지
    return None
