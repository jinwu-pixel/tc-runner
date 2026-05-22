# profile_generation_report.md

대상 단말: **AT-M140 (ALT thor2)** / Android 14 / SDK 34

## 1. ADB 자동 수집 성공 항목

| 섹션 | 필드 | 수집 명령 | 값 |
|------|------|-----------|-----|
| device_identity | device_id / adb_serial | `adb devices` | B06201249E00030C |
| device_identity | manufacturer / brand | `getprop ro.product.manufacturer/brand` | ALT |
| device_identity | model | `getprop ro.product.model` | AT-M140 |
| device_identity | product_name | `getprop ro.product.name` | alt_thor2 |
| device_identity | device_name | `getprop ro.product.device` | thor2 |
| device_identity | build_fingerprint | `getprop ro.build.fingerprint` | ALT/alt_thor2/thor2:14/UP1A.231005.007/... |
| software_baseline | android_version | `getprop ro.build.version.release` | 14 |
| software_baseline | sdk_int | `getprop ro.build.version.sdk` | 34 |
| software_baseline | security_patch | `getprop ro.build.version.security_patch` | 2026-03-05 |
| software_baseline | build_id | `getprop ro.build.id` | UP1A.231005.007 |
| software_baseline | build_incremental | `getprop ro.build.version.incremental` | MY01250600 |
| software_baseline | locale | `getprop persist.sys.locale` | ko-KR |
| software_baseline | timezone | `getprop persist.sys.timezone` | Asia/Seoul |
| display_profile | resolution_px | `wm size` | 480x800 |
| display_profile | density_dpi | `wm density` | 220 |
| display_profile | font_scale | `settings get system font_scale` | 1.0 |
| input_profile | primary_input_method | `settings get secure default_input_method` | com.alt.folderkeyboard/.service.KeyboardService |
| input_profile | navigation_mode | `settings get secure navigation_mode` | 0 (3-button) |
| package_registry | settings | `pm list packages` | com.android.settings |
| package_registry | phone | `pm list packages` | com.skt.prod.dialer |
| package_registry | messages | `pm list packages` | com.android.mms |
| package_registry | camera | `pm list packages` | com.hnlens.camera |
| package_registry | seniorshield | `pm list packages` | com.example.seniorshield |
| activity_hints | settings_main | `dumpsys package` resolve | com.android.settings/.homepage.SettingsHomepageActivity |
| activity_hints | phone_main | `dumpsys package` LAUNCHER | com.skt.prod.dialer/.activities.main.MainActivity |
| activity_hints | camera_main | `dumpsys package` LAUNCHER | com.hnlens.camera/com.mediatek.camera.CameraLauncher |
| activity_hints | messages_main | `dumpsys package` LAUNCHER | com.android.mms/.ui.ConversationList |
| activity_hints | seniorshield_main | `dumpsys package` LAUNCHER | com.example.seniorshield/.MainActivity |
| shell_capabilities | 전체 | `am start`, `am force-stop`, `pm grant`, `logcat -c` 실행 테스트 | 모두 성공 |
| input_profile | navigation_mode | `settings get secure navigation_mode` → 0 | 0 → 3button 매핑 (0=3button, 1=2button, 2=gesture) |

## 2. 수동 확인 필요 항목

| 필드 | 이유 |
|------|------|
| ui_profile.settings_labels (wifi, bluetooth 등) | ADB로 설정 화면 라벨 텍스트 자동 확인 불가. 실기 화면에서 확인 필요 |
| ui_profile.known_ui_variants.permission_dialog_style | 권한 팝업 스타일 ADB 판별 불가 |
| ui_profile.known_ui_variants.quick_settings_style | 퀵 설정 패널 스타일 ADB 판별 불가 |
| ui_profile.known_ui_variants.lockscreen_style | 잠금 화면 스타일 ADB 판별 불가 |
| display_profile.display_size | `settings get system display_size_forced` 미지원 |

## 3. UNKNOWN/null로 남긴 항목

| 필드 | 값 | 이유 |
|------|-----|------|
| display_profile.display_size | null | 해당 getprop/settings 명령에서 값 미반환 |
| ui_profile.settings_labels.* (6개) | null | ADB로 UI 라벨 텍스트 자동 수집 불가 |
| ui_profile.known_ui_variants.* (3개) | null | UI 스타일 자동 판별 불가 |

## 4. 이 프로필 사용 시 주의할 제약사항

- **저해상도(480x800)**: `tap_xy` 좌표를 다른 단말에서 그대로 사용하면 위치가 맞지 않음. `tap_text`/`tap_id` 우선 사용 권장
- **커스텀 런처**: 홈 화면이 `com.hnlens.simplemode`으로 AOSP/삼성 런처와 다름. 홈 화면 TC에서 텍스트/레이아웃 차이 가능
- **SKT 전화 앱**: `com.skt.prod.dialer`는 AOSP `com.android.dialer`와 별도. Activity 이름 주의
- **커스텀 카메라**: `com.hnlens.camera` (MediaTek 기반). AOSP/삼성 카메라와 UI/Activity 다름
- **userdebug 빌드**: root는 아니지만 일부 디버그 기능 사용 가능
- **외부 단말 연동 불가**: 외부 발신/수신, 멀티 디바이스 TC는 `manual_pause` + 보조폰 필요
- **pm grant/revoke 제한 가능성**: 권한 종류 및 앱 targetSdkVersion에 따라 runtime permission이 아닌 경우 grant/revoke가 실패할 수 있음

## 5. 이후 보강 권장 항목

1. `ui_profile.settings_labels` — 설정 화면 스크린샷에서 라벨 텍스트 확인 후 채우기
2. `known_ui_variants` — 권한 팝업, 퀵 설정, 잠금 화면 스크린샷 확인
3. 서드파티 앱 목록 추가 — 필요 시 `pm list packages -3`로 확장
