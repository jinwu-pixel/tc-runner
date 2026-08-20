# 메시지 앱 discovery manifest (2026-08-19) — redacted

원본 dump 8개는 **PII(수신 문자 본문·발신번호) 포함**으로 repo 밖 local-only 보관(세션 scratchpad
`pii_local_only/msg_discovery_2026-08-19/`). 본 manifest는 무-PII 요약만 보존한다.

## 확정 사실

- 물리 메시지 하드키 = **Android keycode 132 (KEYCODE_F2)** → `com.android.mms/.ui.ConversationList`.
  근거: `mtk-kpd` 스캔코드에 ENVELOPE/CONTACTS 부재, F1/F2/F3 존재 (`/system/usr/keylayout/Generic.kl`).
  동일 판독으로 131(F1)=연락처(`com.hnlens.contacts`), 133(F3)=단축버튼 편집(`ShortcutEditActivity`).
  종전 65(ENVELOPE)=Gmail 은 물리 키 경로가 아닌 프레임워크 기본앱 해석 결과.
- **F4 미시험** — `gpio-keys` 소속(볼륨과 동거) SOS 후보, denylist 원칙으로 제외.

## HDK_023 — precondition 미충족

메시지함에 기존 대화 존재(건수·내용 비전사) → 빈 상태 literal `대화가 없습니다` **미검증**.
삭제는 mutation 금지 → **fixture 필요**(062/070과 동일 계열). keycode 차단은 해소됨.
원문의 `설정 아이콘 → 검색/차단 및 스팸관리/전체 대화목록 삭제/설정` 메뉴는 **미개방** —
메뉴에 `전체 대화목록 삭제` 포함되어 별도 승인 대상(fail-closed).

## HDK_055 — focus 순환 확정 (원문 시퀀스 일치)

`메시지 작성`(`new_message_banner`) → UP → `검색`(`search`) → RIGHT → `옵션 더보기`
(ImageButton, **content-desc** `옵션 더보기`, resource-id 없음) → DOWN → `메시지 작성` 복귀.

literal 차이: 원문 `+메시지 작성` → 실제 `메시지 작성`(+ 없음) / 원문 `더보기` → 실제 content-desc
`옵션 더보기`(text 속성 부재 = **text 기반 verifier 불가, desc/element 기반 필요**).

## HDK_056 — 우측 경계 정지 확인

`옵션 더보기` focus 에서 RIGHT 추가 입력 → 동일 노드 유지(정지). 원문 기대와 일치.
literal 차이: 원문 `설정 버튼` → 실제 content-desc `옵션 더보기`.

## focus 모델

대화목록 진입 시 `android:id/list`(ListView) 컨테이너가 focused = **list 모델**
(`com.android.mms` = list 라는 기존 카탈로그와 정합, 재확인).

## 경계

`manual evidence observed` 만. 2-run 아님 — 승격 근거 아니며 backfill/driver 설계 입력.
mutation 0(keyevent+dump 만), 메뉴 미개방, 대화 삭제·발신 0.
