# BUG27084 재개 상태

## 현재 안전 상태

- 대상 serial: `B06201249E00030C`
- model: `AT-M140`
- known-bad fingerprint: `ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys`
- incremental: `RY07260901S`
- 마지막 run: `20260901T152148Z`
- phase: `RESTORED_SAFE`
- HOME: Simple HOME `com.hnlens.simplemode`
- 잔존 mutation: 0
- fixed build 검증: 미수행

Session A는 host-only였으며 ADB 또는 device mutation을 실행하지 않았다. 위 상태는 `RESULT_2026-09-01.md`와 봉인된 마지막 bundle이 보고한 상태이며, Session A가 재관찰했다고 해석하지 않는다.

## 증거 상태

- legacy evidence bundle: 정확히 45개
- tracked 원장: `EVIDENCE_LEDGER.json`
- 과거 45개 bundle은 `legacy_baseline.entries`의 manifest SHA와 `bundle_tree_sha256`으로 byte-immutable하게 결박하며 재봉인하지 않는다.
- legacy bundle에는 `harness_provenance.json`이 없으므로 일반 phase, 새 child capture, `reset-fixture` 재개에 사용할 수 없다. 안전 restore만 허용한다.
- future provenance bundle은 별도 `provenance_entries`에 manifest/tree digest와 source pair를 기록한다. evidence root 자체가 없는 clean clone은 원장의 `NOTE` 경로다. root가 존재하면 두 영역 합집합 기준 누락·추가·중복 run, manifest/tree SHA 또는 source pair 불일치는 실패다.

## Session B 진입 조건

1. Session A 통합 commit OID와 handoff의 bootstrap-only `source_digest_sha256`을 clean scope에서 확인하고 device 호출 없이 host tests를 실행한다.
2. fixed profile을 pre-device Session B preparation commit으로 통합한 뒤 새 pair B의 OID/digest를 발행한다.
3. pair B에서 fresh known-bad root bundle을 먼저 capture해 campaign authority pair를 확정하고 fixed root bundle도 같은 pair에서 fresh capture한다.
4. fixed build label만 믿지 않고 artifact SHA-256, 실제 fingerprint, incremental, Launcher version/code/APK hash를 read-only로 확정한다.
5. known-bad와 fixed build 사이의 provider, lifecycle, 30초 관찰 창, 반복 수, Launcher-host binding drift를 동등하게 맞춘다.
6. 첫 device mutation 전 별도 사용자 승인을 받는다.

상세 절차와 중단 조건은 `HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md`가 권위 문서다.
