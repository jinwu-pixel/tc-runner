# -*- coding: utf-8 -*-
"""Data-only profiles for scripts/eng_mode_runner.py."""

PROFILES = {
    "ODIN2_ENG_V1": {
        "package": "com.ls.teleengineer",
        "activity": ".EngineeringActivity",
        "gate_label": "Enter Engineering Mode",
        "expect_model": "AT-M150",
        "tabs": ("GENERAL", "IMS", "LTE"),
        "default_serial": "c4324122",
        "rid": {
            "item_title": "tv_item_title",
            "tv_detail_value": "tv_detail_value",
            "tv_detail_status": "tv_detail_status",
            "tv_top_title": "tv_top_title",
            "et_detail_input": "et_detail_input",
            "btn_read": "btn_read",
            "btn_write": "btn_write",
            "btn_reset": "btn_reset",
            "btn_back": "btn_back",
            "radio_prefix": "rb_",
            "current_value": "current_value",
            "text_key": "textKey",
            "edit_value": "editValue",
            "mfield_write": "btnWrite",
            "mfield_read": "btnRead",
            "text_value": "textValue",
        },
        "btn_labels": {"write": "Write", "read": "Read"},
        "popup_dismiss_exact": "사용",
        "reboot_popup_labels": ("사용", "확인"),
        "pull_specs": (
            ("/sdcard/ls_log/modem/", ".qmdl", "modem"),
            ("/sdcard/ls_log/main/", ".log", "main"),
        ),
        "hook_keywords": (
            "QC_RIL_OEM_HOOK",
            "TeleEngineer",
            "INI_READ",
            "INI_WRITE",
            "QCRIL_JAVA",
        ),
        "swipe_reset": (360, 420, 360, 1100, 200),
        "swipe_list_scroll": (360, 1000, 360, 420, 300),
        "swipe_detail_scroll": (360, 1000, 360, 500, 300),
        "evidence_dir": "ODIN2 - Engineer IMS/log",
    }
}


# Keep entries as ordered lists. Some cases intentionally repeat an item label.
CASESETS = {
    "ODIN2_ENG_V1": {
        "CMB_IMS_REG_A": (
            "IMS",
            [
                ("Domain", "text", "ims.mnc006.mcc450.3gppnetwork.org"),
                ("PRID", "text", "alttest@ims.mnc006.mcc450.3gppnetwork.org"),
                ("Register Expires", "text", "1200"),
            ],
        ),
        "CMB_IMS_REG_B": (
            "IMS",
            [
                ("User Agent", "text", "ALT-UA-TEST/1.0"),
                ("Subscribe Expires", "text", "3600"),
                ("SIP Timer", "mfield:Timer_T1", "500"),
            ],
        ),
        "CMB_IMS_VOICE": (
            "IMS",
            [
                ("Voice Codec Priority", "radio", "rb_voice_amr_wb_preferred"),
                ("AMR Codec ModeSet", "text", "4"),
                ("AMR-WB Codec ModeSet", "text", "8"),
                ("HD Voice Setting", "radio", "rb_hd_on"),
            ],
        ),
        "CMB_IMS_SESSION": (
            "IMS",
            [
                ("Session Expires", "text", "1810"),
                ("Session Refresher", "radio", "rb_refresher_uac"),
                ("RTP Timer", "text", "15"),
                ("Traffic Port", "mfield:speechStartPort", "50000"),
                ("Traffic Port", "mfield:speechStopPort", "50010"),
            ],
        ),
        "CMB_IMS_VIDEO": (
            "IMS",
            [
                ("Video Codec Priority", "radio", "rb_codec_h265"),
                ("Traffic Port", "mfield:videoStartPort", "50020"),
                ("Traffic Port", "mfield:videoStopPort", "50030"),
                ("RTP Timer", "text", "15"),
            ],
        ),
        "CMB_GEN_01": (
            "GENERAL",
            [("HSPA Setting", "text", "5"), ("Auto Answer", "toggle", None)],
        ),
        "CMB_LTE_01": (
            "LTE",
            [
                ("LTE ROHC", "radio", "rb_rohc_on"),
                ("LTE CDRX FGI", "radio", "rb_cdrx_off"),
            ],
        ),
    }
}
