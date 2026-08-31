"""Data-only profiles for the AppWidget stale-provider harness."""

from __future__ import annotations


PROFILES = {
    "AT_M140_BUG27084_KNOWN_BAD_V1": {
        "model": "AT-M140",
        "fingerprint": (
            "ALT/alt_thor2/thor2:14/UP1A.231005.007/"
            "RY07260901S:user/release-keys"
        ),
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
        "app": {
            "package": "com.winson.simpleclock",
            "provider": (
                "com.winson.simpleclock/"
                "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
            ),
            "version_name": "2.1.6",
            "version_code": 216,
            "signature_token": "498de32a",
            "source_bundle": (
                "AT-M140 - Launcher BUG27084/evidence/"
                "20260828T221502KST_widget_generality"
            ),
            "source_manifest_sha256": (
                "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8"
            ),
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
        "ui": {
            "home_long_press": (240, 450, 1200),
            "widget_menu_text": "위젯",
            "widget_search_text": "검색",
            "provider_label": "SimpleClock",
            "widget_drag": (240, 560, 240, 240, 1200),
            "provider_confirm_text": "OK",
            "provider_confirm_fallback": (346, 741),
        },
        "mode_ui": {
            "switch_to_general_text": "일반모드",
            "switch_to_simple_text": "간편모드",
            "always_allow_text": "항상 허용",
        },
        "evidence_root": "AT-M140 - Launcher BUG27084/evidence",
    }
}
