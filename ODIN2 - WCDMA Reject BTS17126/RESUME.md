# RESUME — ODIN2 WCDMA Reject (BTS-17126) 검증 사이클

세션 재개 시 이 파일부터 읽고 현재 위치 파악.

---

## 현재 Phase

**Phase 1 시도 → 사용자 부재 진입 → Offline 분석/문서화 사이클로 전환 (2026-05-28)**
**→ 2026-05-29 세션 재개: PC 재부팅 후 read-only 환경 sanity 완료 (A2 adb shell hang 회복). Phase 1 트리거 미진입 — 승인 대기.**

- Phase 1 실기 검증 진입 시도 = 일부 진행 (logcat capture 4MB)
- 실기 검증 본 트리거 시퀀스 (비행기 OFF → PDP retry → DebugScreen 캡처) = **미수행**
- 사용자 새 goal: 단말 실기 조작 중단, offline 문서화 끝까지 진행 → **본 사이클은 단말 비파괴 read-only 자료 + 메모리 + 본 repo 문서 기반 분석으로 종료**
- 다음 세션 = 사용자 복귀 후 Phase 1 실기 트리거 + 결과 분석

## 진행 결과 요약 (본 사이클)

| 단계 | 상태 | 산출 |
|---|---|---|
| Phase 0 skeleton | 완료 | `BUG_LOG.md` / `MENU_TREE.md` / `RESUME.md` / `RESULT_2026-05-28.md` / `TC_SUITE.md` |
| 단말 연결 확인 | 완료 | AT_M150 / ODIN2 / transport_id:21 (adb devices PASS) |
| adb logcat main buffer | **부분 완료** | `doc/BTS17126/logcat_v2.txt` (4 MB UTF-8) — DebugScreen launch 2건 (19:06:36 / 19:08:23), reject cause 키워드 0건 |
| adb logcat radio buffer | **미수집** | hang (QXDM DIAG 채널 점유 의심) |
| adb shell (dumpsys / getprop / uiautomator) | **hang** | 모든 `adb shell <cmd>` 호출 응답 없음 — Start-Process 격리해도 동일 |
| QXDM HDF | 사용자 측 캡처 완료 | `doc/BTS17126/Test_05-28.19-09-20-776.hdf` (136 MB binary, Claude parse 불가) |
| 사용자 측 logcat adblog01.txt | 0 bytes (캡처 실패) | 단말 측 capture 미동작 추정 |
| PDF (원본 2건) | **unreadable** | Read tool 접근 실패 (bracket path 추정), poppler 없음 → 메모리 기반 진행 |

## 환경 고정 상태 (2026-05-29 read-only sanity 확정 — 단말 조작 없음)

| 항목 | 값 (관찰) | 상태 |
|---|---|---|
| adb shell | `echo alive` 즉시 응답 / `logcat -d` 정상 | ✅ **hang 회복** (2026-05-28 전부 hang → 재부팅 후 정상) |
| 검증 빌드 | build date **Wed May 27 2026** / `alt_odin2-userdebug 14 UKQ1.240227.001` (incremental 20240901) | ◐ 0527 date 확정 / **vendor daily zip ID 미확정** (YanLijie 확인 항목) |
| baseband | `MPSS.HA.1.2-00043-KD_ALL_PACK-1.104002.4` | ✅ 신규 확인 |
| 이전 라운드 빌드 | `test_AT-M150Z0409U_DAILY_DEV_GMS_774_without_persist.zip` | 비교 baseline |
| 단말 | ODIN2 / AT_M150 (transport_id 1) | ✅ |
| SIM | KT USIM — `gsm.sim.state=LOADED`, operator numeric 45008 | ✅ CONFIRMED (이전 ASSUMPTION) · `reference_wcdma_test_sim.md` |
| 잘못된 APN | `test.com` — preferapn `current=1`, numeric=45008 | ✅ default 확정 (이전 ASSUMPTION) |
| RAT | WCDMA-only allowed: `UMTS\|HSDPA\|HSUPA\|HSPA\|HSPA+` (LTE/NR 없음) | ✅ 이미 WCDMA 캠프 |
| 캡처 환경 | QXDM 0x713A / 0x1544 (HDF) + adb logcat | QCAT 등 후처리 도구 없이 HDF parse 불가 |
| airplane | OFF (`airplane_mode_on=0`) | 현재 |
| 화면 | Awake / `mDreamingLockscreen=false` | ✅ unlock 상태 |

## 현재 무선 live state (2026-05-29 관찰)

- `mVoiceRegState=1(OUT_OF_SERVICE)` / `mDataRegState=1(OUT_OF_SERVICE)`
- RIL = UMTS(voice) / HSPA(data)
- CS/PS WWAN = `NOT_REG_SEARCHING`, `rejectCause=0`, EMERGENCY only
- SIM = KT(45008) / camped cell = WCDMA **SKT(45005)**

**해석**:
- 현재 시점 **live SM reject 없음** (rejectCause=0, PS 미부착)
- KT 3G 종료로 주변 WCDMA = SKT뿐 → KT 미인증 USIM이 SKT 셀 캠프하나 미등록
- **Phase 1 핵심 = PS attach → PDP activation 도달 여부**
- QXDM 0x713A 에 `SM_ACTIVATE_PDP_CONTEXT_REJECT` 미발생 시 → `NOTE: trigger unavailable / environment-limited`

## Phase 1 준비 메모 (2026-05-29)

- **QXDM ↔ adb shell 충돌**: QXDM 실행 시 DIAG 채널 재점유 → adb shell hang 재발 가능성. 이번 회복도 QXDM 미실행 덕.
- **권장 캡처 순서**:
  1. QXDM HDF capture start (사용자 측)
  2. trigger / retry window 수행 (비행기 OFF → PDP retry)
  3. QXDM stop
  4. adb dumpsys / logcat / uiautomator capture
- DebugScreen SM Cause persist 전제(TC-09) → QXDM stop 후 UI 캡처해도 값 보존.

## 본 사이클 사용자 결정 (재확인용)

1. 빌드: 0527 로 진행 (정확 ID 후속 확인)
2. TC-06 NAS_CIRCUIT_AND_PACKET_SWITCHED:
   - 트리거 후보 = reject cause #3
   - 트리거 가능 여부 PENDING
   - 가능 시 PASS 기준 = OTA cause #3 / QMI 또는 framework cause #3 / DebugScreen cause #3 일치 (3-way)
   - 불가능 시 `NOTE: trigger unavailable / environment-limited`
3. TC-09 logcat: broad capture, 특정 함수명 의존 X
4. PASS 어휘: §2.2 4종 (validate / runtime / manual evidence / BUG-GAP)
5. 환경 제약 (Combined SIM 한계 / TC-06 트리거 불가 / KT 미인증 scope) = `NOTE` 분리
6. commit / push 없음 (§7 글로벌 정책)
7. **사용자 부재 시 단말 flash / APN 변경 / USIM 조작 / QXDM 캡처 실행 금지** (2026-05-28 추가)

## Phase별 진입 순서

| Phase | 내용 | 진입 조건 | 본 사이클 상태 |
|---|---|---|---|
| 0 | 문서 skeleton + 환경 확정 | — | 완료 |
| 0+ | offline 분석/문서화 | 단말 부재 / 단말 hang 등 | **본 사이클 진입** — 완료 후 종료 |
| 1 | TC-04 SM Reject + TC-09 Resume | 0527 빌드 flash + APN profile 적용 + QXDM 캡처 준비 완료 + adb shell 응답 정상 | 시도 중단 → 다음 세션 |
| 2 | TC-05 Persistence | Phase 1 종료 | PENDING |
| 3 | TC-01 / 02 / 07 / 08 회귀 | Phase 1~2 종료 | PENDING |
| 4 | TC-03 Combined / TC-06 NAS_CS_PS | Phase 1~3 종료 + 환경 제약 항목 결정 | PENDING |
| 5 | TC-10 E2E 통합 | Phase 1~4 결과 종합 | PENDING |

## 다음 세션 진입 시 우선 작업

`CHECKLIST_NEXT_SESSION.md` 참조. 요약:

1. 빌드 정확 ID 확인 결과 RESUME.md 환경 표 갱신
2. **단말 adb shell hang 원인 해소** (QXDM 도구 닫고 재시도, 또는 단말 reboot 한 번)
3. 캡처 환경 정상 확인 (`adb shell echo alive` 등)
4. APN profile / WCDMA 캠프 / USIM 상태 재확인
5. Phase 1 (TC-04 + TC-09) 트리거 시퀀스 진입
6. 본 사이클 산출물 (HDF + logcat_v2 + 본 문서들) 비교 baseline 으로 활용

## 비고

- 본 사이클 결과 = `RESULT_2026-05-28.md` (Phase 0+ 분석 부분 추가)
- 증거 매트릭스 = `EVIDENCE_MATRIX.md`
- 수집 명령 = `COLLECTION_COMMANDS.md`
- 미해결 질문 = `OPEN_QUESTIONS.md`
- 단말 실기 조작 / QXDM 트리거는 다음 세션 사용자 신호 후 진입
