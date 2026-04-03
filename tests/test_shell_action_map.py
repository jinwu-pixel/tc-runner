# tests/test_shell_action_map.py
"""ShellActionMap 단위 테스트."""
import pytest
from src.mmi_converter.shell_action_map import ShellActionMap
from src.mmi_converter.models import Intent


@pytest.fixture
def sam():
    return ShellActionMap()


class TestHasMapping:
    def test_app_launch_keywords(self, sam):
        assert sam.has_mapping("앱 실행")
        assert sam.has_mapping("앱 열기")

    def test_force_stop_keywords(self, sam):
        assert sam.has_mapping("강제 종료")

    def test_permission_keywords(self, sam):
        assert sam.has_mapping("권한 부여")
        assert sam.has_mapping("권한 철회")

    def test_logcat_keyword(self, sam):
        assert sam.has_mapping("로그 초기화")

    def test_unknown_keyword(self, sam):
        assert not sam.has_mapping("화면 캡처")


class TestResolve:
    def test_clear_logcat_no_params(self, sam):
        intent = Intent(type="navigate", target="로그 초기화")
        action = sam.resolve(intent)
        assert action is not None
        assert action.key == "clear_logcat"
        assert action.required_params == []

    def test_launch_app_with_alias(self, sam):
        intent = Intent(type="navigate", target="카카오톡 실행")
        action = sam.resolve(intent)
        assert action is not None
        assert action.key == "launch_app"


class TestRenderCommand:
    def test_clear_logcat(self, sam):
        intent = Intent(type="navigate", target="로그 초기화")
        action = sam.resolve(intent)
        cmd = sam.render_command(action, {})
        assert cmd == "logcat -c"

    def test_force_stop_with_package(self, sam):
        intent = Intent(type="navigate", target="카카오톡 강제 종료")
        action = sam.resolve(intent)
        cmd = sam.render_command(action, {"package": "com.kakao.talk"})
        assert cmd == "am force-stop com.kakao.talk"


class TestAliasRegistry:
    def test_app_alias(self, sam):
        assert sam.resolve_app_alias("카카오톡") == "com.kakao.talk"
        assert sam.resolve_app_alias("유튜브") == "com.google.android.youtube"
        assert sam.resolve_app_alias("알수없는앱") is None

    def test_permission_alias(self, sam):
        assert sam.resolve_permission_alias("카메라 권한") == "android.permission.CAMERA"
        assert sam.resolve_permission_alias("위치 권한") == "android.permission.ACCESS_FINE_LOCATION"
        assert sam.resolve_permission_alias("알수없는권한") is None

    def test_settings_alias(self, sam):
        assert "WIFI" in sam.resolve_settings_alias("Wi-Fi")
        assert "WIFI" in sam.resolve_settings_alias("와이파이")
        assert "WIFI" in sam.resolve_settings_alias("wifi")
        assert "SETTINGS" in sam.resolve_settings_alias("알수없는설정")
