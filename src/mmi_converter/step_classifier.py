from __future__ import annotations

import re

from .models import ClassifiedIntent, ExecutionMode, Intent, StepRole


# Semantic patterns: procedure text → intent type reclassification
_SEMANTIC_PATTERNS: dict[str, list[str]] = {
    "app_launch": [r"앱\s*실행", r"앱을?\s*(열|켜|실행)", r"실행\s*한다"],
    "app_close": [r"앱\s*종료", r"종료\s*한다", r"앱을?\s*(닫|끄)"],
    "navigate_back": [r"뒤로\s*가기", r"이전\s*화면", r"뒤로\s*이동", r"뒤로\s*돌아"],
}


EXTERNAL_KEYWORDS = [
    "수신 전화", "발신 전화", "전화 수신", "전화 발신",
    "보조폰", "보조 단말", "상대 단말", "외부 단말",
]

MANUAL_KEYWORDS = [
    "이어폰 연결", "이어폰 해제", "헤드셋 연결",
    "USB 케이블 연결", "USIM 삽입", "USIM 교체", "SIM 교체",
    "충전기 연결", "충전기 분리",
]

SHELL_CANDIDATES = [
    "앱 실행", "앱 열기", "앱 종료", "강제 종료",
    "권한 부여", "권한 허용", "권한 거부", "권한 철회",
    "로그 초기화", "logcat",
]

SETUP_KEYWORDS = ["초기화", "설치", "사전 조건", "테스트 모드"]
TEARDOWN_KEYWORDS = ["초기화", "복원", "정리", "해제"]

_DEFAULT_MODE: dict[str, ExecutionMode] = {
    "navigate": "UI_AUTO",
    "press_key": "UI_AUTO",
    "wait": "UI_AUTO",
    "toggle": "UI_AUTO",
    "input_text": "UI_AUTO",
    "tap_text": "UI_AUTO",
    "tap_id": "UI_AUTO",
    "verify_text": "UI_AUTO",
    "verify_shell": "SHELL_AUTO",
    "manual_required": "MANUAL_REQUIRED",
    "app_launch": "SHELL_AUTO",
    "app_close": "SHELL_AUTO",
    "navigate_back": "UI_AUTO",
}

_DEFAULT_ROLE: dict[str, StepRole] = {
    "verify_text": "ASSERT",
    "verify_shell": "ASSERT",
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "UI_AUTO": {"SHELL_AUTO", "MANUAL_REQUIRED", "EXTERNAL_EVENT"},
    "SHELL_AUTO": {"MANUAL_REQUIRED", "EXTERNAL_EVENT"},
    "MANUAL_REQUIRED": set(),
    "EXTERNAL_EVENT": {"MANUAL_REQUIRED"},
    "UNSUPPORTED": set(),
}


class StepClassifier:
    def __init__(self, shell_action_map=None):
        self._shell_map = shell_action_map

    def classify(
        self, intents: list[Intent], context: dict | None = None
    ) -> list[ClassifiedIntent]:
        total = len(intents)
        results: list[ClassifiedIntent] = []

        for index, intent in enumerate(intents):
            mode, role, confidence, reasons = self._classify_one(
                intent, index=index, total=total, context=context,
            )
            results.append(ClassifiedIntent(
                intent=intent,
                execution_mode=mode,
                step_role=role,
                confidence=confidence,
                reasons=reasons,
            ))

        return results

    def summarize_tc_class(self, classified: list[ClassifiedIntent]) -> str:
        if not classified:
            return "AMBIGUOUS_NL"

        modes = [c.execution_mode for c in classified]
        total = len(modes)
        unsupported_count = sum(1 for m in modes if m == "UNSUPPORTED")

        if "MANUAL_REQUIRED" in modes or "EXTERNAL_EVENT" in modes:
            return "SEMI_AUTO"
        if unsupported_count == total:
            return "AMBIGUOUS_NL"
        if unsupported_count > 0:
            return "SEMI_AUTO"
        if all(m in {"UI_AUTO", "SHELL_AUTO"} for m in modes):
            return "FULL_AUTO"
        return "AMBIGUOUS_NL"

    def _classify_one(
        self,
        intent: Intent,
        index: int,
        total: int,
        context: dict | None,
    ) -> tuple[ExecutionMode, StepRole, float, list[str]]:
        reasons: list[str] = []
        confidence = 1.0

        # Stage 1: defaults
        mode: ExecutionMode = _DEFAULT_MODE.get(intent.type, "UNSUPPORTED")
        role: StepRole = _DEFAULT_ROLE.get(intent.type, "ACTION")

        # Stage 1.5: semantic reclassification
        # If intent is UNSUPPORTED or generic navigate, check if the raw text
        # matches a semantic pattern for a more specific intent type.
        reclassified_type = self._try_semantic_reclassify(intent)
        if reclassified_type:
            intent.type = reclassified_type
            mode = _DEFAULT_MODE.get(reclassified_type, mode)
            reasons.append(f"semantic_reclassified: {reclassified_type}")

        if mode == "UNSUPPORTED":
            reasons.append(f"default_unsupported: intent type '{intent.type}'")
            return mode, role, confidence, reasons

        # Stage 2: keyword refinement
        search_text = self._get_search_text(intent)
        mode, reasons = self._refine_mode(mode, role, search_text, reasons)

        # Stage 3: metadata confidence
        parser_conf = intent.extra.get("parser_confidence", 1.0) if intent.extra else 1.0
        matched_rule = intent.extra.get("matched_rule", "") if intent.extra else ""
        if parser_conf < 0.5 and matched_rule.endswith("_fallback"):
            confidence *= 0.6
            reasons.append(f"parser_fallback_low_confidence: {matched_rule}, conf={parser_conf}")

        # StepRole: SETUP/TEARDOWN by position
        role = self._refine_role(role, search_text, index, total)

        return mode, role, confidence, reasons

    def _try_semantic_reclassify(self, intent: Intent) -> str | None:
        """Check if intent's raw text matches a semantic pattern.

        Only reclassifies UNSUPPORTED intents or generic 'navigate' intents
        whose target text semantically describes an action (e.g. "앱 실행").
        """
        if intent.type not in ("navigate", "manual_required") and \
           _DEFAULT_MODE.get(intent.type, "UNSUPPORTED") != "UNSUPPORTED":
            return None

        search = self._get_search_text(intent)
        if not search:
            return None

        for intent_type, patterns in _SEMANTIC_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, search):
                    return intent_type
        return None

    def _get_search_text(self, intent: Intent) -> str:
        parts = []
        if intent.target:
            parts.append(intent.target)
        if intent.value:
            parts.append(intent.value)
        raw = intent.extra.get("raw_segment", "") if intent.extra else ""
        if raw:
            parts.append(raw)
        return " ".join(parts)

    def _refine_mode(
        self,
        current: ExecutionMode,
        role: StepRole,
        text: str,
        reasons: list[str],
    ) -> tuple[ExecutionMode, list[str]]:
        candidate = current
        allowed = ALLOWED_TRANSITIONS.get(current, set())

        # Priority: MANUAL > EXTERNAL > SHELL
        for kw in MANUAL_KEYWORDS:
            if kw in text and "MANUAL_REQUIRED" in allowed:
                candidate = "MANUAL_REQUIRED"
                reasons.append(f"manual_keyword_match: '{kw}'")
                return candidate, reasons

        for kw in EXTERNAL_KEYWORDS:
            if kw in text and "EXTERNAL_EVENT" in allowed:
                candidate = "EXTERNAL_EVENT"
                reasons.append(f"external_keyword_match: '{kw}'")
                return candidate, reasons

        # SHELL_AUTO: ASSERT role에서는 lexical match로 전이 차단
        if role != "ASSERT":
            for kw in SHELL_CANDIDATES:
                if kw in text:
                    if self._shell_map and self._shell_map.has_mapping(kw):
                        if "SHELL_AUTO" in allowed:
                            candidate = "SHELL_AUTO"
                            reasons.append(f"shell_mapping_confirmed: '{kw}'")
                            return candidate, reasons
                    else:
                        reasons.append(f"shell_mapping_missing: '{kw}' shell 매핑 미구현")

        return candidate, reasons

    def _refine_role(
        self,
        current: StepRole,
        text: str,
        index: int,
        total: int,
    ) -> StepRole:
        if current != "ACTION":
            return current

        is_first = index == 0
        is_last = index == total - 1

        if is_first and any(kw in text for kw in SETUP_KEYWORDS):
            return "SETUP"
        if is_last and any(kw in text for kw in TEARDOWN_KEYWORDS):
            return "TEARDOWN"
        # 중간 step은 role 변경하지 않음
        return current
