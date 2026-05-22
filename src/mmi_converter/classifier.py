from __future__ import annotations

from dataclasses import dataclass

from .models import ClassificationResult, MMIRow


MANUAL_KEYWORDS = [
    "이어폰",
    "유선 이어폰",
    "헤드셋",
    "로밍",
    "외부 단말",
    "상대 단말",
    "발신 단말",
    "수신 단말",
    "전화 발신 확인",
    "전화 수신 확인",
    "외부 발신",
    "외부 수신",
    "페어링",
    "블루투스 기기",
    "Wi-Fi AP",
    "공유기",
    "AP 연결",
    "SIM 교체",
    "USIM 교체",
    "케이블 연결",
    "충전기 연결",
    "탈착",
    "삽입",
]

AMBIGUOUS_KEYWORDS = [
    "정상 동작",
    "문제 없는지",
    "이상 없는지",
    "확인한다",
    "확인 필요",
    "정상 여부",
]

AUTO_HINT_KEYWORDS = [
    "설정",
    ">",
    "→",
    "토글",
    "선택",
    "입력",
    "back",
    "home",
    "recent",
    "메뉴 진입",
    "표시",
    "실행",
]

SEMI_AUTO_HINT_KEYWORDS = [
    "육안",
    "눈으로",
    "확인",
    "표시되는지",
    "보이는지",
    "상태 확인",
]

OUT_OF_SCOPE_KEYWORDS = [
    "fota",
    "ota 업데이트",
    "서버",
    "이슈 관리",
    "담당자",
    "메뉴트리",
]


@dataclass(slots=True)
class MMITCClassifier:
    def classify(self, row: MMIRow) -> ClassificationResult:
        text = self._merge_text(row)

        if self._contains_any(text, OUT_OF_SCOPE_KEYWORDS):
            return ClassificationResult(
                automation_class="OUT_OF_SCOPE",
                reasons=["관리성/운영성 항목으로 보임"],
                confidence=0.95,
            )

        if self._contains_any(text, MANUAL_KEYWORDS):
            return ClassificationResult(
                automation_class="MANUAL_REQUIRED",
                reasons=self._matched_keywords(text, MANUAL_KEYWORDS, prefix="수동/외부환경 키워드"),
                confidence=0.95,
            )

        if not row.procedure.strip():
            return ClassificationResult(
                automation_class="AMBIGUOUS_NL",
                reasons=["Test procedure가 비어 있음"],
                confidence=1.0,
            )

        auto_score = self._count_matches(text, AUTO_HINT_KEYWORDS)
        ambiguous_score = self._count_matches(text, AMBIGUOUS_KEYWORDS)
        semi_auto_score = self._count_matches(text, SEMI_AUTO_HINT_KEYWORDS)

        if auto_score == 0 and ambiguous_score > 0:
            return ClassificationResult(
                automation_class="AMBIGUOUS_NL",
                reasons=["절차가 모호하거나 검증 문장 중심"],
                confidence=0.8,
            )

        if auto_score > 0 and semi_auto_score > 0:
            return ClassificationResult(
                automation_class="SEMI_AUTO",
                reasons=["절차는 자동화 가능하나 기대결과 또는 판정에 육안 확인 성격이 포함됨"],
                confidence=0.75,
            )

        if auto_score > 0:
            return ClassificationResult(
                automation_class="FULL_AUTO",
                reasons=["메뉴 탐색/토글/입력/키 이벤트 패턴 감지"],
                confidence=0.8,
            )

        return ClassificationResult(
            automation_class="AMBIGUOUS_NL",
            reasons=["자동화 가능한 절차 패턴을 충분히 찾지 못함"],
            confidence=0.6,
        )

    def _merge_text(self, row: MMIRow) -> str:
        return " | ".join(
            [
                row.feature_name.lower(),
                row.functionality.lower(),
                row.precondition.lower(),
                row.procedure.lower(),
                row.expected_result.lower(),
            ]
        )

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def _count_matches(self, text: str, keywords: list[str]) -> int:
        return sum(1 for keyword in keywords if keyword.lower() in text)

    def _matched_keywords(self, text: str, keywords: list[str], prefix: str) -> list[str]:
        matched = [keyword for keyword in keywords if keyword.lower() in text]
        return [f"{prefix}: {', '.join(matched)}"] if matched else []
