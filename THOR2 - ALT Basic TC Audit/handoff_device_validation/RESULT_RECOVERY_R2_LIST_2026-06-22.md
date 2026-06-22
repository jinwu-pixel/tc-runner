# RESULT — ALT Basic R2 list-focus F0 device 검증 (2026-06-22)

단말 F0 `B06201249E0002F0` (AT-M140 THOR2, build **RY07260601S**, ko-KR). ODIN2 `c4324122` 동시 연결이나 **전 세션 무접촉**(모든 명령 `-s F0`). 순수 adb(`uiautomator dump`+`input keyevent`), Appium helper 0, **mutation-0**(DPAD+dump+back/HOME만), dump 전량 삭제(PII 위생).

## 핵심 발견 — focus 모델은 화면 의미가 아니라 **위젯이 결정**

| 위젯 | 모델 | 신호 | 실기 증거 |
|---|---|---|---|
| `ListView` (`android:id/list`) | **list** | 컨테이너가 focused 고정(불변) + `selected="true"` 자식 이동 | com.android.mms |
| `RecyclerView`/`ScrollView` | **node** | focused **행 노드** 이동(bounds 변경), `selected` 미사용 | com.android.settings · com.hnlens.clock |

오늘 STAGE1 설계의 "settings/list 화면 = list" 의미 추론이 실기에서 부분 오류로 확인됨. `device_confirm` hedge + fallback 계약이 정확히 이 오분류를 잡으라고 설계됐고, 실제로 작동.

## 직접 검증 (4 TC)

- **MSG_069** (차단 및 스팸관리, com.android.mms): focused=`android:id/list` 컨테이너 **불변**, `selected="true"` 자식 마이그레이션(차단된 번호↔문구↔메시지) **정·역재현**. 뒤로가기는 `ImageButton`[0,33][77,110] focused. → **R2 list 모델 runtime 검증 성공** (R1이면 위음성이던 자리).
- **MSG_077** (메시지 설정): 동일 패턴(뒤로가기 ImageButton → `android:id/list` + selected "SMS 사용"). list ✓.
- **CLK_030/031** (시계 스톱워치, com.hnlens.clock): focused가 이산 위젯 이동(재생 fab `clock:id/fab` ↔ 추가옵션 ImageView), `selected`는 탭 인디케이터일 뿐. → **node 확정** (device_confirm 해소).
- **com.android.settings** (홈 리스트): focused 행 bounds 변경([0,507]→[0,629]→스크롤), `selected` 없음, ScrollView 컨테이너. → **node 확정**. 홈 설정 타일도 동일 com.android.settings(별도 simple-settings ListView 없음).

## 13건 재분류

| 분류 | TC | 비고 |
|---|---|---|
| **list 유지 (5)** | MSG_069·077(직접) / MSG_070·071·072(동일 mms ListView) | 070/071/072 이동은 fixture-gated(차단 목록 비어있으면 미검증) |
| **node 정정 (5)** | CLK_030·031(직접) / CAL_335·SST_009·HDK_095(com.android.settings) | list→node 환원 필요 |
| **미검증 defer (3)** | HDK_069(연락처 더보기) / LCH_014·015(런처 앱편집) | 추가 capture 후 확정 |

## device_value 채록 (PII-free, 환류 대기)

- **MSG_069**: `container=android:id/list` · selected child `com.android.mms:id/cl_text`/`text1`(차단된 번호/문구/메시지 행) · back `ImageButton[0,33][77,110]`
- **MSG_077**: `container=android:id/list` · selected child(설정 항목 "SMS 사용" 등) · back `ImageButton`

## 정정 필요 — yaml 미적용 (§2.1 승인 대기, 다음 세션)

1. **MSG_069/077**: `device_value` PENDING_F0 → 위 채록값. focus_model=list 확정.
2. **CLK_030/031 · CAL_335 · SST_009 · HDK_095**: `focus_model` list→node, `model_confidence` 제거, method 원복(node).
3. **HDK_069 · LCH_014/015**: list + device_confirm 유지(미검증).

## NOTE

- **CLK**: Left가 "타이머 탭 이동"(TC 기대)이 아니라 재생버튼 focus 엔게이지 → TC 기대 불일치(후속 확인거리).
- **SST_009/HDK_095**: "쉬운 설정"/"심플 설정" 별도 화면 미발견. 기기 설정 = com.android.settings(node) → node 추정(직접 화면 미캡처, 추가 확인 시 확정).

## 안전 / mutation-0

전건 NAVIGATION_ONLY. 선택/ENTER/실행/설정변경 0. Appium helper 0. dump 전량 삭제. **ODIN2 c4324122 무접촉**(다른 터미널 점유).
