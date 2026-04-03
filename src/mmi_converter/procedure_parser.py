from __future__ import annotations

import re
from enum import Enum

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


class ProcedureFormat(Enum):
    MENU_CHAIN = "menu_chain"
    NUMBERED_PAREN = "numbered_paren"
    NUMBERED_DOT = "numbered_dot"
    CIRCLED = "circled"
    NEWLINE = "newline"
    MIXED = "mixed"


class ProcedureSegmenter:
    _menu_pattern = re.compile(r"\s*[>→]\s*|\s*->\s*")
    _numbered_paren_pattern = re.compile(r"(?:^|\s)\d+\)\s*")
    _numbered_dot_pattern = re.compile(r"(?:^|\s)\d+\.\s+")
    _circled_pattern = re.compile(r"[①-⑳]\s*")
    _connector_pattern = re.compile(r"\s+후\s+|\s+그리고\s+|\s+이후\s+")
    _slash_pattern = re.compile(r"\s*/\s*")
    _numbered_prefix = re.compile(r"^\d+\.\s*")
    _numbered_paren_prefix = re.compile(r"^\d+\)\s*")
    _circled_prefix = re.compile(r"^[①-⑳]\s*")

    def split(self, text: str) -> list[str]:
        if not text:
            return []
        fmt = self._detect_format(text)
        raw = self._split_by_format(text, fmt)
        return [self._normalize(part) for part in raw if self._normalize(part)]

    def _detect_format(self, text: str) -> ProcedureFormat:
        has_arrow = bool(re.search(r"[>→]|->", text))
        has_num_paren = bool(re.search(r"\d+\)\s*\S", text))
        has_num_dot = bool(re.search(r"\d+\.\s+\S", text))
        has_circled = bool(re.search(r"[①-⑳]", text))
        non_empty_lines = sum(1 for line in text.split("\n") if line.strip())
        has_newlines = non_empty_lines >= 2

        signals = sum([has_arrow, has_num_paren, has_num_dot, has_circled])
        if signals >= 2:
            return ProcedureFormat.MIXED
        if has_num_paren:
            return ProcedureFormat.NUMBERED_PAREN
        if has_num_dot:
            return ProcedureFormat.NUMBERED_DOT
        if has_circled:
            return ProcedureFormat.CIRCLED
        if has_arrow:
            return ProcedureFormat.MENU_CHAIN
        if has_newlines:
            return ProcedureFormat.NEWLINE
        return ProcedureFormat.MIXED

    def _split_by_format(self, text: str, fmt: ProcedureFormat) -> list[str]:
        if fmt == ProcedureFormat.MENU_CHAIN:
            parts = self._menu_pattern.split(text)
        elif fmt == ProcedureFormat.NUMBERED_PAREN:
            parts = self._numbered_paren_pattern.split(text)
        elif fmt == ProcedureFormat.NUMBERED_DOT:
            parts = self._numbered_dot_pattern.split(text)
        elif fmt == ProcedureFormat.CIRCLED:
            parts = self._circled_pattern.split(text)
        elif fmt == ProcedureFormat.NEWLINE:
            parts = text.split("\n")
        else:
            # MIXED: hierarchical
            parts = self._split_mixed(text)

        # Post-process: connectors at paren depth 0, then slash
        result = []
        for part in parts:
            sub = self._split_connectors_safe(part)
            for s in sub:
                result.extend(self._slash_pattern.split(s))
        return result

    def _split_mixed(self, text: str) -> list[str]:
        # Level 1: outer structure (numbered/circled/newline)
        outer = re.split(r"(?:^|\s)\d+\)\s*|\d+\.\s+|[①-⑳]\s*|\n+", text)
        # Level 2: menu chains inside each piece
        result = []
        for piece in outer:
            if ">" in piece or "→" in piece or "->" in piece:
                result.extend(self._menu_pattern.split(piece))
            else:
                result.append(piece)
        return result

    def _split_connectors_safe(self, text: str) -> list[str]:
        """괄호 depth 0에서만 연결어로 분리."""
        if "(" not in text:
            return self._connector_pattern.split(text)

        # Has parens — collect tokens at depth-0 and paren-enclosed blocks separately,
        # then only split depth-0 tokens on connectors.
        tokens: list[tuple[bool, str]] = []  # (is_depth0_text, chunk)
        buf = ""
        paren_depth = 0
        for char in text:
            if char == "(" and paren_depth == 0:
                if buf:
                    tokens.append((True, buf))
                    buf = ""
                paren_depth = 1
                buf = char
            elif char == "(" :
                paren_depth += 1
                buf += char
            elif char == ")" and paren_depth == 1:
                buf += char
                tokens.append((False, buf))
                buf = ""
                paren_depth = 0
            elif char == ")":
                paren_depth = max(0, paren_depth - 1)
                buf += char
            else:
                buf += char
        if buf:
            tokens.append((True, buf))

        # Now split only depth-0 tokens on connectors, keep paren blocks intact
        result = []
        for is_depth0, chunk in tokens:
            if is_depth0:
                result.extend(self._connector_pattern.split(chunk))
            else:
                result.append(chunk)
        return result if result else [text]

    def _normalize(self, text: str) -> str:
        text = " ".join(text.strip().split())
        text = self._numbered_prefix.sub("", text).strip()
        text = self._numbered_paren_prefix.sub("", text).strip()
        text = self._circled_prefix.sub("", text).strip()
        text = re.sub(r"\(\s*\)", "", text).strip()
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
