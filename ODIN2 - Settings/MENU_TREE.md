# ODIN2 - Settings · MENU_TREE

단말: ODIN2 (AT-M150) · `com.android.settings` v1.0.0.1101
업데이트: 2026-05-08 (Phase 0 home probe 1회 기준)

## HOME (settings root)

probe: `ODIN2 - Settings/probe_settings_home.xml` (29478 bytes, 17 visible texts, 0 content-desc)

### 헤더 / 검색
- `설정` — 제목 헤더 (정적, anchor 강함)
- `설정 검색` — 검색 입력 placeholder (정적)

### Top-level 메뉴 항목 (label + sub-label)
| label | sub-label | 비고 |
|-------|-----------|------|
| `네트워크 및 인터넷` | `모바일, Wi-Fi, 핫스팟` | 정적 |
| `연결된 기기` | `블루투스, 페어링` | 정적 |
| `앱` | `최근 앱, 기본 앱` | 정적 |
| `알림` | `알림 기록, 대화` | 정적 |
| `배터리` | `86% - 저속 충전 중` | sub-label **dynamic** (% + 충전 상태) |
| `저장용량` | `26% 사용 - 94.95GB 사용 가능` | sub-label **dynamic** (% + 잔여 용량) |
| `안심 기능` | `SOS 버튼, 수신 차단` | 단말 customization 가능 |
| `T 로밍` | — | 통신사 customization (SKT) |

### Anchor 후보 (정적, 6개)
1. `설정`
2. `네트워크 및 인터넷`
3. `연결된 기기`
4. `앱`
5. `알림`
6. `배터리` (sub-label은 dynamic이지만 main label은 정적)

### Dynamic / noisy texts (verify_text 후보 배제)
- `86% - 저속 충전 중` (배터리 sub-label)
- `26% 사용 - 94.95GB 사용 가능` (저장용량 sub-label)

### Scroll
- 17 visible texts 한 화면 dump 가능 (single-pass), SMOKE_01에서 scroll 불필요 추정 — runtime 단계에서 재확인

### 비-Settings (탐색 미수행)
- 하위 화면 (`네트워크 및 인터넷` / `연결된 기기` / `앱` / ...) — Phase 1+ 후보, **현재 미탐색**
