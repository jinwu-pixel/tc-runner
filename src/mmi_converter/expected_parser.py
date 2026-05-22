from __future__ import annotations

import re

from .models import Intent


class ExpectedResultParser:
    def parse(self, expected: str) -> list[Intent]:
        text = " ".join(expected.strip().split())
        if not text:
            return []

        intents: list[Intent] = []

        # "Wi-Fi가 표시된다"
        m = re.search(r"(.+?)(가|이)\s*(표시된다|보인다|노출된다)", text)
        if m:
            intents.append(Intent(type="verify_text", target=m.group(1).strip()))
            return intents

        # "Wi-Fi 메뉴로 진입된다"
        m = re.search(r"(.+?)\s*(메뉴)?\s*(진입된다|실행된다|열린다)", text)
        if m:
            intents.append(Intent(type="verify_text", target=m.group(1).strip()))
            return intents

        # "ON 상태로 표시된다"
        if "on" in text.lower() or "켜짐" in text or "활성화" in text:
            intents.append(Intent(type="verify_text", target="켬"))

        if "off" in text.lower() or "꺼짐" in text or "비활성화" in text:
            intents.append(Intent(type="verify_text", target="끔"))

        return intents
