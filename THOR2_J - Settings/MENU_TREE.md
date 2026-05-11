# THOR2_J - Settings · MENU_TREE

단말: THOR2_J (AT-M140 ja-JP) · `com.android.settings` v14
업데이트: 2026-05-08 (Phase 0 home probe 1회 기준)

## HOME (settings root, 480x800 ja-JP)

probe: `THOR2_J - Settings/probe_settings_home.xml` (17909 bytes, 9 visible texts, 0 content-desc)

### 헤더 / 검색
- `設定` — 제목 헤더 (정적, anchor 강함)
- `設定を検索` — 검색 입력 placeholder (정적)

### Top-level 메뉴 (첫 화면에 보이는 항목, sub-label 포함)
| label | sub-label | 비고 |
|-------|-----------|------|
| `ネットワークとインターネット` | `モバイル、Wi-Fi、アクセス ポイント` | 정적 |
| `接続設定` | `Bluetooth、ペア設定` | 정적 (ko-KR `연결된 기기` 대응) |
| `アプリ` | `最近使ったアプリ、デフォルトのアプリ` | 정적 |
| `海外ローミング` | — | 통신사 customization (KT SIM 기준 표시) |

### Anchor 후보 (정적, 6개)
1. `設定` (length=2 → WEAK_VERIFY_TEXT, lint suppress)
2. `設定を検索` (검색바)
3. `ネットワークとインターネット`
4. `接続設定`
5. `アプリ` (length=3, lint OK)
6. `海外ローミング`

### scroll 1회 후 노출 (SMOKE_02 probe 기준)

probe: `THOR2_J - Settings/probe_settings_scrolled.xml` (23482 bytes, 13 visible texts)

| 신규 main label | sub-label | 비고 |
|-----------------|-----------|------|
| `通知` | `通知履歴、会話` | ko-KR `알림` 대응 |
| `安心機能` | `SOSボタン、安心メッセージ` | ko-KR `안심 기능` 대응 |

추가 노출 sub-label:
- `通知の読み上げ` / `電話・メッセージ発信者読み上げ` — 접근성/읽기 옵션 (ko-KR에 없는 ja 단말 customization 가능성)

### 추가 scroll 필요 (SMOKE_03 후보)
- `バッテリー` (ko-KR 배터리 대응) — scroll 1회로 미관찰
- `ストレージ` (ko-KR 저장용량 대응) — scroll 1회로 미관찰

→ 480x800 화면 + ja-JP 텍스트 길이 효과로 ROOT 메뉴를 한 화면에 다 못 넣음. SMOKE_03+ 에서 추가 scroll 가능.

### Scroll
- 첫 dump 9 visible texts — single-pass. 추가 메뉴는 scroll 필요 (Phase 1+ 후보)
- SMOKE_01은 scroll 0 가정 (현재 anchor 6개로 read-only verify 충분)

### 단말 횡 비교 (ODIN2 ko-KR vs THOR2_J ja-JP)

| ko-KR (ODIN2 17 texts) | ja-JP (THOR2_J 9 texts) | 화면 효과 |
|---|---|---|
| 17 visible | 9 visible | 480x800 + ja 텍스트 길이 → 첫 화면 노출 ↓ |
| 알림 / 배터리 / 저장용량 / 안심 기능 노출 | 미노출 | scroll 필요 |
| T 로밍 | 海外ローミング | 통신사 라벨 locale 차이 |
| 동적 sub-label (배터리%, 저장용량%) | (현재 첫 화면에 미노출) | 화면 짧아서 관찰 안 됨 |

### 비-Settings (탐색 미수행)
- 하위 화면 — Phase 1+ 후보, **현재 미탐색**
