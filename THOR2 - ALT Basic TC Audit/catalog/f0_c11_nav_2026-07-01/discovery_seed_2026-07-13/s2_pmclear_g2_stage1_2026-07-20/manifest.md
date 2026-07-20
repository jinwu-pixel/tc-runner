# manifest — s2 pm clear G2 Option-A **Stage 1 / T1** (2026-07-20)

**경계 구분**: **raw XML/PNG = local-only** — dynamic 값(시각·날짜·날씨 위치·기온·메모리)을 미generalize 상태로 보존하며 **exact-path staging에서 제외**한다. **본 manifest = redacted commit candidate** — 해당 문자열을 일반화하고 `tools/redaction_gate.py` PASS 대상이다(상위 RESULT도 동일).

- device: F0 / AT-M140 / build `UP1A.231005.007`, capture 시 sole
- method: `uiautomator dump` + `input tap/swipe`(navigation/widget config) + `pm clear` **1회**. remote dump = `/data/local/tmp` only. adb는 PowerShell 전달.
- reference baseline: `../s2_pmclear_design/baseline_p0..p3.xml` (2026-07-14, §9.3)

## 시퀀스 + SHA-256

| # | file | 화면 | nodes | SHA-256 | 메모 |
|---|---|---|---:|---|---|
| 01 | preflight_p3_canonical | p3 사진 위젯 page(빈 상태) | 20 | `0086D75E…C352E` | `사진 추가하기`+4 markers |
| 02 | postseed_p3_caseB | seed 1장 후 p3 | 20 | `0086D75E…C352E` | **Case B** — seed로 위젯 미변경(동일 SHA) |
| 03 | popup_photoslideshow | `포토 슬라이드 쇼` 안내 팝업 | 13 | `5AB37615…4F27A` | `다시 보지 않기` checkbox **미접촉**, `확인` 진행 |
| 04 | photopickactivity | `PhotoPickActivity` | 15 | `EE5D296A…721F` | 사진 1장, counter `0/10` |
| 05 | photopick_selected_1of10 | 사진 선택 | 15 | `8D9F5BA8…F301` | `1/10`, `iv_photo`/`v_selected` selected |
| 06 | configured_widget_shell | p3 구성 shell(미디어 존재) | 21 | `DE9609F6…9394` | `iv_album`+`cl_translucent`. **미디어 존재 정상 구성 shell — stale 아님** |
| 07 | postclear_firstscreen_home | pm clear 후 첫 화면 | 52 | `7F7987DE…0A99` | simplemode HOME(p1). **first-run/mode-chooser/권한 없음** |
| 08 | postclear_lastpage_index2 | clear 후 마지막 page | 62 | `24581A2E…22DD` | index=2(도구). **home_indicator 3 dots(3-page)** |
| 09 | cur_p0 | p0 단축다이얼 | 75 | `E920AEB1…AD89` | **§9.3 baseline p0와 byte-identical** |
| 10 | cur_p1 | p1 시계/앱 | 52 | `BF6A5832…51DD` | baseline과 **구조 동일**; live 시각·날짜·날씨 dynamic diff만 |
| 11 | cur_p2 | p2 도구 | 62 | `F3F6A3A5…A2E8` | baseline과 **구조(62-node·rid) 동일**; 메모리값 dynamic diff만 |
| 12 | final_3page_home | teardown 후 HOME | 52 | `7D0B0FDD…FC67` | MediaStore 0, 3-page |

## 실행 사실

- `pm clear com.hnlens.simplemode` stdout: **`Success`** (guard: F0 sole + AT-M140).
- teardown: `reset_pfwseed_f0.py` → MediaStore residual **0 PFWSEED**.
- 최종 invariants: MediaStore **0** / PFWSEED **0** / pkg **218** / io.appium **0** / HOME role `com.hnlens.simplemode` / **3-page**.

## p0~p2 diff 요약 (baseline 2026-07-14 대비)

- p0: byte-identical (무변경).
- p1: 구조 동일 — 차이는 dynamic(baseline 캡처 시 날씨 데이터 미수신 → 07-20 수신) + 시각/날짜.
- p2: 62-node·rid 동일 — 차이는 dynamic 메모리 표시값만.
- → **관찰한 HOME p0~p3 표면에서 유일한 구조 변화 = p3 사진 위젯 page 제거(4→3)**. dump로 관찰 가능한 visible config 손실 0(숨은 preference 보존 여부는 미검증).

## 판정 어휘

- 위젯 구성 제거: `manual evidence observed`.
- 4-page canonical 복원: **실패**(page째 제거).
- `pm clear runtime PASS`: **주장 안 함**(단발 관찰).
- "4-page empty p3 = launcher default 아니라 선존 사용자 구성" 가설: **`OBSERVED`**(p0~p2가 default라 clear에도 무변경인 것과 정합), `CONFIRMED` 아님.
- taxonomy: 21-node=구성 shell / stale=shell+미디어 소실→깨진 render / 20-node=page 존재·빈 상태 / 3-page=**page-absent**(pm clear 후 관찰 상태; launcher default 여부 = `OBSERVED`, 단정 아님).
