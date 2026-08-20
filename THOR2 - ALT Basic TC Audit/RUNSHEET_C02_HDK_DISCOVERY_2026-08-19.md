# RUNSHEET — C02 (11.Hard Key) F0 v1 discovery run (Codex 실행용, 2026-08-19)

**역할**: Codex = 단말 실행·채록 / Claude = 계획·검증 / 사용자 = 승인 게이트. (device runsheet 위임 패턴)

**본 세션 = discovery run이다. 2-run 아님 — `runtime PASS`·`RUNNABLE_NOW` 승격 주장 절대 금지.**
목적 = batch10 Part B C02 청크 29건의 ① entry 경로 확정 ② 기대 literal 실측 채록 ③ focus 거동/모델 채록
④ driver-pattern 분류 입력 확보. 이후 Claude가 driver slice 설계 → host-TDD → fresh 2-run(별도 세션)으로 승격한다.

- 계약 상위 문서: `handoff_device_validation/THOR2J_HANDOFF_BATCH10_2026-06-25.md` (§1 규약·§6 elevated-caution·§7 denylist 전부 유효 — 본 문서는 C02 discovery 델타만)
- manifest (read-only): `handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv` — `source_sheet=11.Hard Key` 29행
- canonical yaml (read-only): `stage1_review_mapping_batch10/ALTBASIC_HDK_*.yaml` — **편집 절대 금지** (backfill은 Claude 검증 후 별도 무단말 트랙)

## 0. 단말 정체 게이트 (하나라도 불일치 = 즉시 STOP)

Claude 사전 실측(2026-08-19)으로 아래 전 항목 일치 확인됨 — Codex는 **실행 직전 재확인**한다:

```bash
adb devices -l                                    # F0 단독 (타 단말/B27 B2700125BW000083 보이면 STOP)
adb -s B06201249E0002F0 shell getprop ro.product.model          # AT_M140
adb -s B06201249E0002F0 shell getprop ro.build.version.incremental   # RY07260601S
adb -s B06201249E0002F0 shell getprop persist.sys.locale        # ko-KR
adb -s B06201249E0002F0 shell "pm list packages | wc -l"        # 219
adb -s B06201249E0002F0 shell pm list packages io.appium        # 출력 없음 (잔존 0)
```

- 이후 **모든 adb 호출은 `-s B06201249E0002F0` 명시** (wrong-device 가드).
- 세션 중 USB 재연결 발생 시 본 게이트 전체 재실행 후 재개.
- pre-snapshot: `adb -s B06201249E0002F0 shell "pm list packages | sort" > /data/local/tmp/../..` 대신 호스트에 저장:
  `... > <scratchpad>/F0_pkgs_pre.txt` (219 기대).

## 1. 단말 상태 전제 (알려진 상태 — 재확인만, 복구 시도 금지)

| 항목 | 상태 | Codex 행동 |
|---|---|---|
| launcher 홈 | **3-page** (2026-07-20 pm clear로 p3 사진위젯 page 제거됨 — 복원 동선 미매핑) | 홈 관련 TC에서 4-page 전제 발견 시 `NOTE` 기록만. **복원/재구성 시도 금지** |
| screen-off | null root (dump 불가) | `input keyevent KEYCODE_WAKEUP` 후 진행 |
| MediaStore images / PFWSEED | 0 / 0 (07-20 수용 baseline) | **오염 금지** — screencap/dump 원격 저장은 `/data/local/tmp` 만 (`/sdcard` 저장 = MediaStore 자동 등록 함정, 2026-07-13 실증) |
| 부팅 데이터 팝업 | reboot 금지라 미해당이나, 만약 노출 시 | BACK 아닌 **`취소`** 로 닫기 (상태 보존, BUG-25796 계열) |
| 폴더(플립) 개폐 | 물리 조작 — adb 불가 | 홈 dump가 비정상(닫힘 표면)이면 **사용자에게 폴더 개방 요청 후 대기**, 임의 진행 금지 |
| settings task 잔존 | 이전 세션 스택 resume 함정 (divergence 제5유형) | 심플설정 계열 진입 전 BACK 루프(max 8)→HOME으로 task 정리 후 진입 |

## 2. 대상 29건 · 실행 순서 (표면 클러스터 — 앱 1회 기동 batch)

| 순서 | 클러스터 | tc_id | 유형 |
|---|---|---|---|
| A | 홈 하드키 런치 | HDK_016·019·021·022·023 | verify_text (목적지 노출) |
| B | 홈 focus nav | HDK_035·036·037·038 (**T1 focus_state**) · 041·042·046 | focus 채록 |
| C | 기기 종료 팝업 | HDK_052·053·054 | **elevated-caution** focus 순환 |
| D | 퀵패널 | HDK_050 | verify_text + focus |
| E | 메시지 앱 | HDK_055·056 | focus nav |
| F | 주소록 앱 | HDK_062·064·070 | focus nav |
| G | 심플 설정 | HDK_094·096·097·098·099·100·101·102(**caution**) | focus nav + OK 진입 |

각 TC: manifest 행 + canonical yaml의 `procedure_steps`/`expected_result_raw`/`risk_note`/`cleanup_candidate` 필독 후 실행.

## 3. keycode 표 (C01/기존 트랙 확정분 재사용 — no-guess)

| 키 | keycode | 근거 |
|---|---|---|
| Navi ↑/↓/←/→ | 19 / 20 / 21 / 22 | DPAD 표준 |
| Navi OK | 23 (DPAD_CENTER) | C11 SST 트랙 |
| 취소 키 | 4 (BACK) **가정 — run에서 검증·채록** | 미확정 |
| 홈 | 3 | C01 BSC_015 확정 |
| 최근 앱 | 187 (APP_SWITCH) | C01 BSC_014 확정 |
| 연락처 | 207 (CONTACTS) | C01 BSC_017 확정 |
| 카메라 | 27 (CAMERA) | C01 BSC_019 확정 |
| 메시지 버튼 | **미확정** — 후보 65(ENVELOPE) 1회만 시험, 실패 시 `KEYCODE_UNRESOLVED` 기록 (연타 탐색 금지) | entry_detail 정규화: device_keycode_discovery |
| 길게 누름 | `input keyevent --longpress <code>` — 미작동 시 `LONGPRESS_UNSUPPORTED` 기록, 대체 수단 발명 금지 | — |
| 퀵패널 진입 | `cmd statusbar expand-notifications` (이탈: `cmd statusbar collapse` 또는 BACK) | SST_012 트랙 |

## 4. per-TC 절차 (discovery 표준)

1. **entry**: precondition 확인(홈/해당 앱 화면) → manifest `entry_detail` 대로 진입. 진입 불가 = `ENTRY_FAILED` (임의 우회 금지).
2. **pre dump**: `adb shell uiautomator dump /data/local/tmp/ui.xml && adb pull` → `<evidence>/{tc_id}_s{n}_pre.xml`.
3. **키 입력**: 해당 step의 keyevent 실행 (짧게=1회 / 길게=--longpress).
4. **post dump**: 각 키 입력 직후 dump → `{tc_id}_s{n}_post.xml`. (스크린샷 필요 시 `screencap -p /data/local/tmp/s.png` → pull → 원격 즉시 삭제.)
5. **채록**:
   - verify_text: 기대 literal(`expected_texts_candidate`)의 화면 노출 여부 → `LITERAL_CONFIRMED` / 의미 일치·표기 차이 = `LITERAL_PENDING`(실측 표기 채록, **발명 금지**) / 미노출 = `NOT_PRESENT`.
   - focus 계열: pre/post의 `focused="true"` 노드(resource-id·text·bounds) + `selected="true"` 자식 채록.
     **focus_model 판별**: 컨테이너 `android:id/list`(ListView) focused 고정 + selected 자식 이동 = `list` / focused 노드 자체 이동(RecyclerView·ScrollView 등) = `node`. 위젯 클래스 병기.
   - divergence(스펙↔단말 불일치·요소 부재·경로 상이)는 판정하지 말고 **관찰 그대로 기록**.
6. **cleanup**: BACK×n → HOME 복귀 확인 (yaml `cleanup_candidate`). 다음 TC.

**tap 금지 원칙**: 본 discovery는 keyevent-only. tap 없이는 진행 불가한 상황 = 실행하지 말고 `DISCOVERY_BLOCKED` 기록 (fail-closed).

## 5. 안전 (denylist — 상위 handoff §6·§7 전부 유효 + C02 특기)

- **HDK_052/053/054 (기기 종료 팝업)**: `--longpress 26`(POWER)으로 팝업 열기 허용. 팝업 안에서 **DPAD 이동·dump만**. `전원 끄기`/`다시 시작`/`응급전화` 위에서 **OK(23) 절대 금지**. 이탈은 **BACK만**. BACK로 안 닫히면 dump 채록 후 사용자 호출.
- **HDK_102 (안전 및 긴급 상황)**: OK로 페이지 **진입·노출 확인까지만**. SOS/긴급전화/Emergency 항목 위에서 OK 금지.
- **HDK_022 (카메라)**: 촬영 화면 진입 확인만. **셔터/OK 금지** (촬영 = mutation).
- **HDK_098 (Wi-Fi 설정)**: 페이지 진입 확인만. **토글/연결 금지**.
- **HDK_064 (연락처 없을 때)**: 연락처 존재 시 = `PRECONDITION_MISMATCH` 기록 후 skip. **삭제 금지**.
- HDK_023 빈 대화 전제 동일 — 대화 존재 시 채록만, 삭제 금지.
- 설정값 변경·토글·저장·전송·삭제·발신·`am start` 직접 기동 = 전부 금지 (NAVIGATION_ONLY).

## 6. 종료 게이트 (전 항목 기록)

```bash
adb -s B06201249E0002F0 shell "pm list packages | sort" > <scratchpad>/F0_pkgs_post.txt
diff F0_pkgs_pre.txt F0_pkgs_post.txt        # empty = mutation 0
adb -s B06201249E0002F0 shell "ls /data/local/tmp"   # 본 세션 임시파일 잔존 0 (직접 정리)
adb -s B06201249E0002F0 shell "content query --uri content://media/external/images/media --projection _id" | wc -l  # 0 유지
# HOME 복귀 상태로 종료
```

## 7. 산출물 (신규 3종만 — 그 외 repo 파일 일절 무편집)

| 산출물 | 경로 |
|---|---|
| dumps/png (local-only, 커밋 후보 아님) | `THOR2 - ALT Basic TC Audit/catalog/f0_c02_hdk_nav_2026-08-19/` |
| per-TC ledger CSV | `THOR2 - ALT Basic TC Audit/DISCOVERY_C02_LEDGER_2026-08-19.csv` — 열: `tc_id, entry_status, entry_resolved, keycodes_used, literal_expected, literal_observed, verify_status, focus_observed, focus_model, divergence, evidence_files, note` |
| summary MD | `THOR2 - ALT Basic TC Audit/DISCOVERY_C02_HDK_SUMMARY_2026-08-19.md` — 분포·divergence 목록·driver-pattern 분류 제안·신규 함정·keycode 확정분 |

- **redaction**: 메시지/주소록 화면 dump에 기존 PII 부수 채록 가능 → raw dump는 local-only 유지, ledger/summary에는 PII 미전사 (실측 literal 중 개인정보성 문자열은 `<REDACTED>` 치환 표기).
- **git**: stage/commit/push **0**. 기존 tracked/untracked 파일 무편집. 산출 3종은 untracked로 남긴다.

## 8. 보고 (STOP 후 Claude 검증 대기)

- 결과 분포: 29건 = LITERAL_CONFIRMED n / LITERAL_PENDING n / NOT_PRESENT n / ENTRY_FAILED n / DISCOVERY_BLOCKED n / PRECONDITION_MISMATCH n / DEVICE_FIT_SKIP n
- 어휘 제약: 본 세션 실측 = `manual evidence observed` 만. `runtime PASS` / `validate PASS` / RUNNABLE 승격 표현 금지. scope 밖 관찰 = `NOTE`.
- 필수 첨부: 정체 게이트 값 / pkg pre==post / remote temp 0 / MediaStore 0 / 산출 3종 경로 / 실행 못 한 TC와 사유.
- 보고 후 **STOP** — driver slice 설계·yaml backfill·commit 전부 Claude/사용자 영역.
