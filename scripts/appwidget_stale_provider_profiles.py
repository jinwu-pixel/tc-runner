"""Data-only profiles for the AppWidget stale-provider harness."""

from __future__ import annotations


_FINGERPRINT = (
    "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys"
)
_SOURCE_BUNDLE = (
    "AT-M140 - Launcher BUG27084/evidence/"
    "20260828T221502KST_widget_generality"
)
_SOURCE_MANIFEST_SHA256 = (
    "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8"
)


def _profile(*, app: dict, ui: dict) -> dict:
    """Build one provider variant without duplicating device safety identity."""
    return {
        "model": "AT-M140",
        "fingerprint": _FINGERPRINT,
        "incremental": "RY07260901S",
        "viewport": (480, 800),
        "simple_home": "com.hnlens.simplemode",
        "general_home": "com.hnlens.launcher3",
        "general_home_activity": (
            "com.hnlens.launcher3/"
            "com.android.launcher3.uioverrides.QuickstepLauncher"
        ),
        "switch_activity": "com.hnlens.simplemode/.ui.home.SwitchModeActivity",
        "launcher_package": "com.hnlens.launcher3",
        "app": app,
        "ui": ui,
        "mode_ui": {
            "switch_to_general_resource_id": "com.hnlens.simplemode:id/rb_normal",
            "switch_to_simple_resource_id": "com.hnlens.simplemode:id/rb_simple",
            "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
            "always_allow_text": "항상 허용",
        },
        "recovery_ui": {
            "launcher_crash_titles": (
                "MIVE Home이(가) 중지됨",
                "MIVE Home이(가) 계속 중단됨",
            ),
            "title_resource_id": "android:id/alertTitle",
            "close_resource_id": "android:id/aerr_close",
        },
        "evidence_root": "AT-M140 - Launcher BUG27084/evidence",
    }


PROFILES = {
    "AT_M140_BUG27084_KNOWN_BAD_V1": _profile(
        app={
            "package": "com.winson.simpleclock",
            "provider": (
                "com.winson.simpleclock/"
                "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
            ),
            "version_name": "2.1.6",
            "version_code": 216,
            "signature_token": "498de32a",
            "source_bundle": _SOURCE_BUNDLE,
            "source_manifest_sha256": _SOURCE_MANIFEST_SHA256,
            "apk_dir": "simpleclock_apk",
            "splits": (
                (
                    "base.apk",
                    23871293,
                    "BC7CFFF4E2A441864B35B9064EA6B4E0B3D907FCAA788C4F83EAA7F0152F0B29",
                ),
                (
                    "split_config.ko.apk",
                    33177,
                    "5711AF8D4E523EC7768C6DBCE0D2E480AFA36B0AFB638B0D1A85BB5E32C94003",
                ),
                (
                    "split_config.tvdpi.apk",
                    167375,
                    "3C03AF1D7B647A389FEA8F96EAF181B34B0F0DED077A0C0B49B8ED951061C92E",
                ),
            ),
        },
        ui={
            "home_long_press": (240, 350, 1200),
            "widget_menu_text": "위젯",
            "widget_search_text": "검색",
            "provider_label": "SimpleClock",
            "widget_drag": (240, 560, 240, 240, 1200),
            "widget_remove_drag": (240, 240, 150, 70, 1200),
            "widget_education_close_resource_id": (
                "com.hnlens.launcher3:id/edu_close_button"
            ),
            "widget_drag_tip_text": "길게 터치하여 위젯을 이동하세요.",
            "provider_confirm_text": "OK",
            "provider_confirm_fallback": (346, 741),
        },
    ),
    "AT_M140_BUG27084_ACCUWEATHER_V1": _profile(
        app={
            "package": "com.accuweather.android",
            "provider": (
                "com.accuweather.android/"
                "com.accuweather.android.widgets.todaytonighttomorrow.ui."
                "TodayTonightTomorrowWidgetProvider"
            ),
            "version_name": "21.1.15-3-rc",
            "version_code": 210115003,
            "signature_token": "d4f22e39",
            "source_bundle": _SOURCE_BUNDLE,
            "source_manifest_sha256": _SOURCE_MANIFEST_SHA256,
            "apk_dir": "accuweather_apk",
            "splits": (
                (
                    "base.apk",
                    29421672,
                    "D1E0FE5245F94D9538823F7BFA79864EE6D802CFFABE11D813A5D07834A55C41",
                ),
                (
                    "split_config.armeabi_v7a.apk",
                    53779,
                    "8B5E10EF5404C646D72E097AE0882FA3756C31192C546307F45F98ED7C9E1125",
                ),
                (
                    "split_config.ko.apk",
                    74137,
                    "03D0D7B0DDCA87F4A34D47D389AAAC1ABB0EA4761C866A979618B0B76FEC2E63",
                ),
                (
                    "split_config.tvdpi.apk",
                    612677,
                    "7D3D6A8D987CD3FCB53F99C1D69A863C2F340B6B4B64A02B2FD1EBF8255E2B2A",
                ),
            ),
        },
        ui={
            "home_long_press": (240, 250, 1200),
            "widget_menu_text": "위젯",
            "widget_search_text": "검색",
            "provider_label": "AccuWeather",
            "provider_variant_text": "36시간 예보",
            "widget_drag": (240, 485, 240, 240, 1500),
            "widget_remove_drag": (297, 187, 150, 70, 1200),
            "widget_remove_selector": "36시간 예보",
            "widget_education_close_resource_id": (
                "com.hnlens.launcher3:id/edu_close_button"
            ),
            "widget_drag_tip_text": "길게 터치하여 위젯을 이동하세요.",
            "provider_confirm_required": True,
            "provider_confirm_resource_id": (
                "com.accuweather.android:id/widget_confirm_submit_button"
            ),
            "provider_confirm_text": "저장",
            "provider_confirm_fallback": (240, 736),
        },
    ),
}
