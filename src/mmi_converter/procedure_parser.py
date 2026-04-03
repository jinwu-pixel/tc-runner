from __future__ import annotations

import re

from .models import Intent


KEYWORD_TO_KEYCODE = {
    "back": "BACK",
    "뒤로": "BACK",
    "home": "HOME",
    "홈": "HOME",
    "recent": "APP_SWITCH",
    "최근": "APP_SWITCH",
    "최근앱": "APP_SWITCH",
}


TOGGLE_ON_PATTERNS = [
    r"\bon\b",
    r"\b켜",
    r"\b켠다",
    r"\b켜기",
    r"\b활성화",
]
TOGGLE_OFF_PATTERNS = [
    r"\boff\b",
    r"\b끄",
    r"\b끈다",
    r"\b끄기",
    r"\b비활성화",
]


class ProcedureSegmenter:
    _split_pattern = re.compile(
        r"""
        \s*>\s*|
        \s*→\s*|
        \s*->\s*|
        \n+|
        \r\n+|
        \s+후\s+|
        \s+그리고\s+|
        \s*/\s*
        """,
        re.VERBOSE,
    )

    _numbered_prefix = re.compile(r"^\d+\.\s*")

    def split(self, text: str) -> list[str]:
        if not text:
            return []
        raw_parts = self._split_pattern.split(text)
        return [self._normalize(part) for part in raw_parts if self._normalize(part)]

    def _normalize(self, text: str) -> str:
        text = " ".join(text.strip().split())
        text = self._numbered_prefix.sub("", text).strip()
        return text


class ProcedureParser:
    def __init__(self) -> None:
        self.segmenter = ProcedureSegmenter()

    def parse(self, procedure: str) -> list[Intent]:
        segments = self.segmenter.split(procedure)
        intents: list[Intent] = []

        if not segments:
            return intents

        total = len(segments)

        for index, segment in enumerate(segments):
            lower_seg = segment.lower()
            base_extra = {
                "raw_segment": segment,
                "position": index,
                "total_segments": total,
                "source_phase": "procedure",
            }

            # 1) 키 이벤트
            key_intent = self._parse_key(segment, lower_seg)
            if key_intent:
                key_intent.extra = {**base_extra, "matched_rule": "key", "parser_confidence": 1.0, **key_intent.extra}
                intents.append(key_intent)
                continue

            # 2) 대기
            wait_intent = self._parse_wait(segment)
            if wait_intent:
                wait_intent.extra = {**base_extra, "matched_rule": "wait", "parser_confidence": 1.0, **wait_intent.extra}
                intents.append(wait_intent)
                continue

            # 3) 토글
            toggle_intent = self._parse_toggle(segment, lower_seg, previous_segments=segments[:index])
            if toggle_intent:
                toggle_intent.extra = {**base_extra, "matched_rule": "toggle", "parser_confidence": 0.8, **toggle_intent.extra}
                intents.append(toggle_intent)
                continue

            # 4) 텍스트 확인
            verify_intent = self._parse_verify(segment)
            if verify_intent:
                verify_intent.extra = {**base_extra, "matched_rule": "verify", "parser_confidence": 0.9, **verify_intent.extra}
                intents.append(verify_intent)
                continue

            # 5) 입력
            input_intent = self._parse_input(segment)
            if input_intent:
                input_intent.extra = {**base_extra, "matched_rule": "input", "parser_confidence": 0.9, **input_intent.extra}
                intents.append(input_intent)
                continue

            # 6) 기본은 navigate (fallback)
            intent = Intent(type="navigate", target=segment, extra={
                **base_extra, "matched_rule": "navigate_fallback", "parser_confidence": 0.5,
            })
            intents.append(intent)

        return intents

    def _parse_key(self, segment: str, lower_seg: str) -> Intent | None:
        for keyword, keycode in KEYWORD_TO_KEYCODE.items():
            if keyword in lower_seg:
                return Intent(type="press_key", value=keycode)
        return None

    def _parse_wait(self, segment: str) -> Intent | None:
        match = re.search(r"(\d+)\s*초", segment)
        if match:
            return Intent(type="wait", value=match.group(1))
        if "잠시" in segment:
            return Intent(type="wait", value="2")
        return None

    def _parse_toggle(self, segment: str, lower_seg: str, previous_segments: list[str]) -> Intent | None:
        if "토글" not in segment and not any(pat in lower_seg for pat in ["on", "off", "켜", "끄", "활성화", "비활성화"]):
            return None

        value = None
        if any(re.search(pattern, lower_seg) for pattern in TOGGLE_ON_PATTERNS):
            value = "on"
        elif any(re.search(pattern, lower_seg) for pattern in TOGGLE_OFF_PATTERNS):
            value = "off"

        target = self._extract_toggle_target(segment)
        if not target and previous_segments:
            target = previous_segments[-1]

        return Intent(type="toggle", target=target, value=value)

    def _extract_toggle_target(self, segment: str) -> str | None:
        cleaned = (
            segment.replace("토글", "")
            .replace("On", "")
            .replace("ON", "")
            .replace("Off", "")
            .replace("OFF", "")
            .replace("켜기", "")
            .replace("끄기", "")
            .replace("활성화", "")
            .replace("비활성화", "")
            .strip()
        )
        return cleaned or None

    def _parse_verify(self, segment: str) -> Intent | None:
        verify_markers = ["표시", "확인", "보임", "보이는지", "진입"]
        if any(marker in segment for marker in verify_markers):
            target = segment
            target = target.replace("표시 확인", "")
            target = target.replace("표시", "")
            target = target.replace("확인", "")
            target = target.replace("보이는지", "")
            target = target.replace("보임", "")
            target = target.replace("진입", "")
            target = target.strip()
            if target:
                return Intent(type="verify_text", target=target)
        return None

    def _parse_input(self, segment: str) -> Intent | None:
        if "입력" in segment:
            target = segment.replace("입력", "").strip() or None
            return Intent(type="input_text", target=target)
        return None
