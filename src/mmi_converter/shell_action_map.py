from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Intent


@dataclass(slots=True)
class ShellAction:
    key: str
    command_template: str
    required_params: list[str]
    optional_params: dict[str, str] = field(default_factory=dict)
    description: str = ""


APP_ALIAS_REGISTRY = {
    "카카오톡": "com.kakao.talk",
    "유튜브": "com.google.android.youtube",
    "설정": "com.android.settings",
    "전화": "com.android.dialer",
    "카메라": "com.android.camera",
    "갤러리": "com.android.gallery3d",
    "메시지": "com.android.mms",
    "크롬": "com.android.chrome",
    "카카오뱅크": "com.kakaobank.channel",
}

PERMISSION_ALIAS_REGISTRY = {
    "카메라 권한": "android.permission.CAMERA",
    "위치 권한": "android.permission.ACCESS_FINE_LOCATION",
    "전화 권한": "android.permission.READ_PHONE_STATE",
    "마이크 권한": "android.permission.RECORD_AUDIO",
    "저장소 권한": "android.permission.READ_EXTERNAL_STORAGE",
    "연락처 권한": "android.permission.READ_CONTACTS",
    "통화 기록 권한": "android.permission.READ_CALL_LOG",
}

SETTINGS_INTENTS = {
    "Wi-Fi": "android.settings.WIFI_SETTINGS",
    "블루투스": "android.settings.BLUETOOTH_SETTINGS",
    "디스플레이": "android.settings.DISPLAY_SETTINGS",
    "소리": "android.settings.SOUND_SETTINGS",
    "배터리": "android.intent.action.POWER_USAGE_SUMMARY",
    "앱": "android.settings.APPLICATION_SETTINGS",
}

_SETTINGS_ALIASES = {
    "와이파이": "Wi-Fi", "wifi": "Wi-Fi", "wi-fi": "Wi-Fi",
    "블루투쓰": "블루투스", "bluetooth": "블루투스",
    "화면": "디스플레이", "display": "디스플레이",
    "sound": "소리", "사운드": "소리",
    "battery": "배터리",
    "application": "앱", "애플리케이션": "앱",
}

_ACTIONS: list[tuple[list[str], ShellAction]] = [
    (
        ["앱 실행", "앱 열기", "실행"],
        ShellAction(key="launch_app", command_template="am start -n {package}/{activity}",
                    required_params=["package"], optional_params={"activity": ".MainActivity"},
                    description="앱 실행"),
    ),
    (
        ["앱 종료", "강제 종료", "앱 강제 종료"],
        ShellAction(key="force_stop", command_template="am force-stop {package}",
                    required_params=["package"], description="앱 강제 종료"),
    ),
    (
        ["권한 부여", "권한 허용"],
        ShellAction(key="grant_permission", command_template="pm grant {package} {permission}",
                    required_params=["package", "permission"], description="권한 부여"),
    ),
    (
        ["권한 거부", "권한 철회"],
        ShellAction(key="revoke_permission", command_template="pm revoke {package} {permission}",
                    required_params=["package", "permission"], description="권한 철회"),
    ),
    (
        ["로그 초기화", "logcat 초기화"],
        ShellAction(key="clear_logcat", command_template="logcat -c",
                    required_params=[], description="logcat 초기화"),
    ),
    (
        ["설정 화면 진입", "설정 열기"],
        ShellAction(key="open_settings", command_template="am start -a {settings_action}",
                    required_params=["settings_action"], description="설정 화면 진입"),
    ),
]


class ShellActionMap:
    def __init__(self) -> None:
        self._keyword_map: dict[str, ShellAction] = {}
        for keywords, action in _ACTIONS:
            for kw in keywords:
                self._keyword_map[kw] = action

    def has_mapping(self, keyword: str) -> bool:
        return any(kw in keyword for kw in self._keyword_map)

    def resolve(self, intent: Intent) -> ShellAction | None:
        text = intent.target or ""
        for kw, action in self._keyword_map.items():
            if kw in text:
                return action
        return None

    def render_command(self, action: ShellAction, params: dict) -> str:
        merged = {**action.optional_params, **params}
        return action.command_template.format(**merged)

    def resolve_app_alias(self, name: str) -> str | None:
        return APP_ALIAS_REGISTRY.get(name)

    def resolve_permission_alias(self, name: str) -> str | None:
        return PERMISSION_ALIAS_REGISTRY.get(name)

    def resolve_settings_alias(self, name: str) -> str:
        normalized = _SETTINGS_ALIASES.get(name.lower(), name)
        return SETTINGS_INTENTS.get(normalized, "android.settings.SETTINGS")
