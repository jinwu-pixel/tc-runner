# Step-level Hybrid Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the MMI conversion pipeline with step-level classification, hybrid runner (manual pause/resume), shell action mapping, multi-format segmentation, and YAML export.

**Architecture:** A 3-phase pipeline extension: (1) classify each Intent with ExecutionMode + StepRole via a new StepClassifier module, then extend ActionRunner with manual pause callbacks; (2) add shell action mapping with alias registries, and upgrade the segmenter to handle numbered/mixed formats; (3) add YAML export with fail-fast runnable checking.

**Tech Stack:** Python 3.12, pytest, openpyxl, PyYAML

**Spec:** `docs/superpowers/specs/2026-04-03-step-level-hybrid-pipeline-design.md`

---

## File Structure

### New Files
- `src/mmi_converter/step_classifier.py` — Step-level classification (ExecutionMode + StepRole)
- `src/mmi_converter/shell_action_map.py` — Shell action mapping + alias registries
- `src/mmi_converter/exporter.py` — YAML export logic
- `tests/test_step_classifier.py` — StepClassifier tests
- `tests/test_shell_action_map.py` — ShellActionMap tests
- `tests/test_exporter.py` — YAML export tests

### Modified Files
- `src/mmi_converter/models.py` — Add ExecutionMode, StepRole, ClassifiedIntent
- `src/mmi_converter/procedure_parser.py` — Multi-format segmenter + metadata hints
- `src/mmi_converter/compiler.py` — Accept ClassifiedIntent, emit shell/manual_pause steps
- `src/mmi_converter/service.py` — Insert StepClassifier into pipeline
- `src/mmi_converter/__init__.py` — Export new types
- `src/action_runner.py` — StepResult extension + hybrid pause logic
- `src/tc_loader.py` — Add manual_pause to VALID_ACTIONS + permissive validation
- `src/cli.py` — Terminal manual handler + export-mmi command
- `src/reporter.py` — 3-way split (success/skipped/failed)
- `tests/test_mmi_procedure_parser.py` — Multi-format segmenter regression + new tests
- `tests/test_mmi_compiler.py` — ClassifiedIntent compilation tests
- `tests/test_mmi_service.py` — Updated pipeline integration tests

---

## Phase 1, Issue 1: Step-level Classification

### Task 1: Data Models — ExecutionMode, StepRole, ClassifiedIntent

**Files:**
- Modify: `src/mmi_converter/models.py`
- Test: `tests/test_step_classifier.py` (create)

- [ ] **Step 1: Write model tests**

```python
# tests/test_step_classifier.py
"""StepClassifier 단위 테스트."""
import pytest
from src.mmi_converter.models import (
    ExecutionMode, StepRole, ClassifiedIntent, Intent,
)


class TestClassifiedIntent:
    def test_basic_construction(self):
        intent = Intent(type="navigate", target="설정")
        ci = ClassifiedIntent(
            intent=intent,
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        assert ci.execution_mode == "UI_AUTO"
        assert ci.step_role == "ACTION"
        assert ci.confidence == 1.0
        assert ci.reasons == []

    def test_with_reasons(self):
        intent = Intent(type="navigate", target="수신 전화")
        ci = ClassifiedIntent(
            intent=intent,
            execution_mode="EXTERNAL_EVENT",
            step_role="ACTION",
            confidence=0.9,
            reasons=["external_keyword_match: '수신 전화' → EXTERNAL_EVENT"],
        )
        assert ci.execution_mode == "EXTERNAL_EVENT"
        assert len(ci.reasons) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_step_classifier.py -v`
Expected: FAIL — `ExecutionMode`, `StepRole`, `ClassifiedIntent` not defined

- [ ] **Step 3: Add types to models.py**

Add after `AutomationClass` in `src/mmi_converter/models.py`:

```python
ExecutionMode = Literal[
    "UI_AUTO",
    "SHELL_AUTO",
    "MANUAL_REQUIRED",
    "EXTERNAL_EVENT",
    "UNSUPPORTED",
]

StepRole = Literal[
    "ACTION",
    "ASSERT",
    "SETUP",
    "TEARDOWN",
]
```

Add after `ConversionPreview` class:

```python
@dataclass(slots=True)
class ClassifiedIntent:
    intent: Intent
    execution_mode: ExecutionMode
    step_role: StepRole
    confidence: float = 1.0
    reasons: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Update `__init__.py` exports**

Add `ExecutionMode`, `StepRole`, `ClassifiedIntent` to `src/mmi_converter/__init__.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_step_classifier.py -v`
Expected: PASS

- [ ] **Step 6: Run full regression**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All 106+ tests pass

- [ ] **Step 7: Commit**

```bash
git add src/mmi_converter/models.py src/mmi_converter/__init__.py tests/test_step_classifier.py
git commit -m "feat: add ExecutionMode, StepRole, ClassifiedIntent models"
```

---

### Task 2: StepClassifier Core — 3-stage Classification

**Files:**
- Create: `src/mmi_converter/step_classifier.py`
- Test: `tests/test_step_classifier.py`

- [ ] **Step 1: Write classification tests**

Append to `tests/test_step_classifier.py`:

```python
from src.mmi_converter.step_classifier import StepClassifier


@pytest.fixture
def classifier():
    return StepClassifier()


class TestStage1Defaults:
    """Intent.type 기반 기본 매핑."""

    def test_navigate_is_ui_auto_action(self, classifier):
        intents = [Intent(type="navigate", target="설정")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ACTION"

    def test_press_key_is_ui_auto_action(self, classifier):
        intents = [Intent(type="press_key", value="HOME")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ACTION"

    def test_verify_text_is_ui_auto_assert(self, classifier):
        intents = [Intent(type="verify_text", target="Wi-Fi")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_verify_shell_is_shell_auto_assert(self, classifier):
        intents = [Intent(type="verify_shell", target="dumpsys")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "SHELL_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_manual_required_is_manual(self, classifier):
        intents = [Intent(type="manual_required", target="이어폰 연결")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"


class TestStage2KeywordRefinement:
    """키워드 기반 ExecutionMode 재분류."""

    def test_external_keyword_overrides_ui_auto(self, classifier):
        intents = [Intent(type="navigate", target="수신 전화")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "EXTERNAL_EVENT"

    def test_manual_keyword_overrides_ui_auto(self, classifier):
        intents = [Intent(type="navigate", target="이어폰 연결 후 확인")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"

    def test_assert_role_blocks_shell_transition(self, classifier):
        """ASSERT role에서 lexical match로 SHELL_AUTO 전이 차단."""
        intents = [Intent(type="verify_text", target="logcat 확인")]
        result = classifier.classify(intents)
        # ASSERT에서 SHELL_AUTO 전이 차단 → UI_AUTO 유지
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_assert_allows_external_transition(self, classifier):
        """ASSERT role에서 EXTERNAL_EVENT 전이는 허용."""
        intents = [Intent(type="verify_text", target="수신 전화 수신 확인")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "EXTERNAL_EVENT"

    def test_manual_priority_over_external(self, classifier):
        """MANUAL_REQUIRED > EXTERNAL_EVENT 우선순위."""
        intents = [Intent(type="navigate", target="이어폰 연결 후 수신 전화")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"

    def test_shell_candidate_without_map_stays_ui(self, classifier):
        """shell_action_map 없으면 SHELL_AUTO 승격 안 함."""
        intents = [Intent(type="navigate", target="앱 실행")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert any("shell_mapping_missing" in r for r in result[0].reasons)


class TestStage3SetupTeardown:
    """위치/context 기반 StepRole 조정."""

    def test_first_step_setup_hint(self, classifier):
        intents = [
            Intent(type="navigate", target="초기화"),
            Intent(type="navigate", target="설정"),
        ]
        result = classifier.classify(intents)
        assert result[0].step_role == "SETUP"

    def test_last_step_teardown_hint(self, classifier):
        intents = [
            Intent(type="navigate", target="설정"),
            Intent(type="navigate", target="초기화"),
        ]
        result = classifier.classify(intents)
        # 중간이 아닌 마지막 step의 "초기화"
        assert result[1].step_role == "TEARDOWN"

    def test_middle_step_no_role_change(self, classifier):
        intents = [
            Intent(type="navigate", target="설정"),
            Intent(type="navigate", target="초기화"),
            Intent(type="navigate", target="확인"),
        ]
        result = classifier.classify(intents)
        # 중간 step은 role 변경하지 않고 reason만 추가
        assert result[1].step_role == "ACTION"


class TestSummarizeTcClass:
    """TC-level summary 도출."""

    def test_empty_returns_ambiguous(self, classifier):
        assert classifier.summarize_tc_class([]) == "AMBIGUOUS_NL"

    def test_all_ui_auto_is_full_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="네트워크"), "UI_AUTO", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "FULL_AUTO"

    def test_mixed_ui_shell_is_full_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="verify_shell", target="dumpsys"), "SHELL_AUTO", "ASSERT"),
        ]
        assert classifier.summarize_tc_class(classified) == "FULL_AUTO"

    def test_manual_makes_semi_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="이어폰 연결"), "MANUAL_REQUIRED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "SEMI_AUTO"

    def test_all_unsupported_is_ambiguous(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="???"), "UNSUPPORTED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "AMBIGUOUS_NL"

    def test_partial_unsupported_is_semi_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="???"), "UNSUPPORTED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "SEMI_AUTO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_step_classifier.py -v`
Expected: FAIL — `StepClassifier` not found

- [ ] **Step 3: Implement StepClassifier**

Create `src/mmi_converter/step_classifier.py`:

```python
from __future__ import annotations

from .models import ClassifiedIntent, ExecutionMode, Intent, StepRole


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
        is_middle = not is_first and not is_last

        if is_first and any(kw in text for kw in SETUP_KEYWORDS):
            return "SETUP"
        if is_last and any(kw in text for kw in TEARDOWN_KEYWORDS):
            return "TEARDOWN"
        # 중간 step은 role 변경하지 않음
        return current
```

- [ ] **Step 4: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_step_classifier.py -v`
Expected: All PASS

- [ ] **Step 5: Run full regression**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/mmi_converter/step_classifier.py tests/test_step_classifier.py
git commit -m "feat: implement StepClassifier with 3-stage classification"
```

---

### Task 3: Parser Metadata + Service Pipeline Integration

**Files:**
- Modify: `src/mmi_converter/procedure_parser.py`
- Modify: `src/mmi_converter/service.py`
- Modify: `src/cli.py` (preview output)
- Test: `tests/test_mmi_service.py`

- [ ] **Step 1: Write parser metadata test**

Add to `tests/test_mmi_procedure_parser.py`:

```python
class TestParserMetadata:
    def test_navigate_includes_raw_segment(self):
        parser = ProcedureParser()
        intents = parser.parse("설정 > 네트워크")
        assert intents[0].extra.get("raw_segment") == "설정"
        assert intents[0].extra.get("matched_rule") == "navigate_fallback"
        assert intents[0].extra.get("position") == 0
        assert intents[0].extra.get("total_segments") == 2
        assert intents[0].extra.get("source_phase") == "procedure"

    def test_key_includes_matched_rule(self):
        parser = ProcedureParser()
        intents = parser.parse("Home 키 입력")
        assert intents[0].extra.get("matched_rule") == "key"
        assert intents[0].extra.get("parser_confidence") == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_mmi_procedure_parser.py::TestParserMetadata -v`
Expected: FAIL — extra keys missing

- [ ] **Step 3: Add metadata to ProcedureParser**

In `src/mmi_converter/procedure_parser.py`, modify `parse()` to pass metadata:

```python
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
```

- [ ] **Step 4: Run parser tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_mmi_procedure_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Update service.py pipeline**

Modify `src/mmi_converter/service.py` to insert StepClassifier:

```python
from .step_classifier import StepClassifier

class MMIConversionService:
    def __init__(self) -> None:
        self.classifier = MMITCClassifier()
        self.procedure_parser = ProcedureParser()
        self.expected_parser = ExpectedResultParser()
        self.compiler = TCRunnerCompiler()
        self.step_classifier = StepClassifier()

    def convert_row(self, row: MMIRow) -> ConversionPreview:
        classification = self.classifier.classify(row)

        # Always parse and classify steps (no short-circuit)
        intents = self.procedure_parser.parse(row.procedure)
        expected_intents = self.expected_parser.parse(row.expected_result)

        ir = TCIR(
            tc_name=row.tc_name,
            description=row.functionality.strip() or row.feature_name.strip(),
            preconditions=[row.precondition.strip()] if row.precondition.strip() else [],
            intents=intents,
            expected_intents=expected_intents,
            source_row=row,
        )

        # Step-level classification
        all_intents = ir.all_intents
        classified = self.step_classifier.classify(all_intents, context={
            "precondition": row.precondition,
            "source_row": row,
        })
        tc_class_from_steps = self.step_classifier.summarize_tc_class(classified)

        if not classification.is_convertible and not all_intents:
            return ConversionPreview(
                tc_name=row.tc_name,
                automation_class=classification.automation_class,
                source_procedure=row.procedure,
                source_expected=row.expected_result,
                parsed_intents=[],
                compiled_steps=[],
                warnings=[],
                reasons=classification.reasons,
                classified_intents=[],
            )

        compiled = self.compiler.compile(ir, automation_class=tc_class_from_steps)

        final_class = self._maybe_downgrade(
            tc_class_from_steps,
            intents=intents,
            expected_intents=expected_intents,
            compiled_steps=compiled["steps"],
            warnings=compiled["metadata"]["warnings"],
            segments=self.procedure_parser.segmenter.split(row.procedure),
            has_expected_text=bool(row.expected_result.strip()),
        )

        return ConversionPreview(
            tc_name=row.tc_name,
            automation_class=final_class,
            source_procedure=row.procedure,
            source_expected=row.expected_result,
            parsed_intents=ir.all_intents,
            compiled_steps=compiled["steps"],
            warnings=compiled["metadata"]["warnings"],
            reasons=classification.reasons,
            classified_intents=classified,
        )
```

- [ ] **Step 6: Add classified_intents to ConversionPreview**

In `src/mmi_converter/models.py`, add field to `ConversionPreview`:

```python
@dataclass(slots=True)
class ConversionPreview:
    tc_name: str
    automation_class: AutomationClass
    source_procedure: str
    source_expected: str
    parsed_intents: list[Intent]
    compiled_steps: list[dict]
    warnings: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    classified_intents: list[ClassifiedIntent] = field(default_factory=list)
```

- [ ] **Step 7: Update preview output in cli.py**

In `cmd_preview_mmi()`, add step classification display after intents:

```python
if preview.classified_intents:
    print(f"  Step Classes:")
    for ci in preview.classified_intents:
        extra = f" target={ci.intent.target}" if ci.intent.target else ""
        print(f"    - [{ci.execution_mode}|{ci.step_role}] {ci.intent.type}{extra}")
```

- [ ] **Step 8: Run full test suite**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All tests pass (some service tests may need minor fixture updates for new `classified_intents` field)

- [ ] **Step 9: Fix any service test failures**

If `test_mmi_service.py` tests fail because `ConversionPreview` now has `classified_intents` as a required positional arg, the default `field(default_factory=list)` should handle it. Verify and fix if needed.

- [ ] **Step 10: Commit**

```bash
git add src/mmi_converter/procedure_parser.py src/mmi_converter/service.py \
  src/mmi_converter/models.py src/cli.py tests/test_mmi_procedure_parser.py
git commit -m "feat: integrate StepClassifier into conversion pipeline with parser metadata"
```

---

## Phase 1, Issue 2: Hybrid Runner

### Task 4: StepResult Extension + ManualStep Types

**Files:**
- Modify: `src/action_runner.py`
- Test: `tests/test_action_runner.py`

- [ ] **Step 1: Extend StepResult**

In `src/action_runner.py`, update `StepResult`:

```python
from typing import Callable, Literal, Optional

@dataclass
class StepResult:
    action: str
    passed: bool
    message: str = ""
    duration: float = 0.0
    screenshot_path: Optional[Path] = None
    execution_mode: str = ""
    manual_action: str = ""
    skip_reason: str = ""
    paused: bool = False
    pause_screenshot_path: Optional[Path] = None


@dataclass(slots=True)
class ManualStepAction:
    decision: Literal["continue", "skip", "fail"]
    reason: str = ""
    evidence_path: Optional[Path] = None


@dataclass(slots=True)
class ManualStepContext:
    tc_name: str
    step_index: int
    step: dict
    execution_mode: str
    screenshot_path: Optional[Path]
    timeout_seconds: Optional[int] = None
```

- [ ] **Step 2: Run existing tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_action_runner.py -v`
Expected: All PASS (new fields have defaults, backward compatible)

- [ ] **Step 3: Commit**

```bash
git add src/action_runner.py
git commit -m "feat: extend StepResult with manual_action fields and ManualStep types"
```

---

### Task 5: ActionRunner Hybrid Pause Logic

**Files:**
- Modify: `src/action_runner.py`
- Modify: `src/cli.py`
- Test: `tests/test_action_runner.py`

- [ ] **Step 1: Write hybrid pause test**

Add to `tests/test_action_runner.py`:

```python
from src.action_runner import ManualStepAction, ManualStepContext


class TestHybridPause:
    def test_manual_step_without_handler_fails(self):
        """no-handler → fail-fast."""
        runner = ActionRunner(adb=MockADB(), screenshot_dir=Path("/tmp"))
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "이어폰 연결"}
        result = runner.run_step(step)
        assert not result.passed
        assert "manual handler not configured" in result.message

    def test_manual_step_continue(self):
        """continue → passed=True."""
        def handler(ctx):
            return ManualStepAction(decision="continue")
        runner = ActionRunner(adb=MockADB(), screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "EXTERNAL_EVENT",
                "description": "보조폰에서 전화"}
        result = runner.run_step(step)
        assert result.passed
        assert result.manual_action == "continue"

    def test_manual_step_skip(self):
        """skip → passed=False, manual_action='skip'."""
        def handler(ctx):
            return ManualStepAction(decision="skip", reason="장비 없음")
        runner = ActionRunner(adb=MockADB(), screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "이어폰 연결"}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "skip"
        assert result.skip_reason == "장비 없음"

    def test_manual_step_fail(self):
        """fail → passed=False, manual_action='fail'."""
        def handler(ctx):
            return ManualStepAction(decision="fail")
        runner = ActionRunner(adb=MockADB(), screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test"}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "fail"
```

- [ ] **Step 2: Implement hybrid pause in ActionRunner**

Update `ActionRunner.__init__` and `run_step`:

```python
class ActionRunner:
    def __init__(self, adb: ADB, screenshot_dir: Path, max_retries: int = 3,
                 retry_interval: float = 1.0, on_manual_step=None):
        self.adb = adb
        self.screenshot_dir = screenshot_dir
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.on_manual_step = on_manual_step

    def run_step(self, step: dict, tc_name: str = "", step_index: int = 0) -> StepResult:
        action = step["action"]
        exec_mode = step.get("execution_mode", "")
        start = time.time()

        # Manual/External pause point
        if exec_mode in ("MANUAL_REQUIRED", "EXTERNAL_EVENT") or action == "manual_pause":
            return self._handle_manual_step(step, tc_name, step_index, start)

        try:
            passed, message = self._dispatch(action, step)
            duration = time.time() - start
            result = StepResult(action=action, passed=passed, message=message,
                              duration=duration, execution_mode=exec_mode)
            if not passed:
                result.screenshot_path = self._capture_failure_screenshot(action)
            return result
        except Exception as e:
            duration = time.time() - start
            result = StepResult(action=action, passed=False, message=str(e),
                              duration=duration, execution_mode=exec_mode)
            result.screenshot_path = self._capture_failure_screenshot(action)
            return result

    def _handle_manual_step(self, step, tc_name, step_index, start):
        exec_mode = step.get("execution_mode", "MANUAL_REQUIRED")
        action = step.get("action", "manual_pause")

        # Capture pre-pause screenshot
        pause_screenshot = self._capture_failure_screenshot("pre_manual")

        if not self.on_manual_step:
            duration = time.time() - start
            return StepResult(
                action=action, passed=False,
                message="manual handler not configured",
                duration=duration, execution_mode=exec_mode,
                manual_action="fail", paused=True,
                pause_screenshot_path=pause_screenshot,
            )

        ctx = ManualStepContext(
            tc_name=tc_name,
            step_index=step_index,
            step=step,
            execution_mode=exec_mode,
            screenshot_path=pause_screenshot,
            timeout_seconds=step.get("manual_timeout", 300),
        )

        result_action = self.on_manual_step(ctx)
        duration = time.time() - start

        if result_action.decision == "continue":
            return StepResult(
                action=action, passed=True,
                message=f"Manual step completed: {step.get('description', '')}",
                duration=duration, execution_mode=exec_mode,
                manual_action="continue", paused=True,
                pause_screenshot_path=pause_screenshot,
            )
        elif result_action.decision == "skip":
            return StepResult(
                action=action, passed=False,
                message=f"Skipped: {result_action.reason}",
                duration=duration, execution_mode=exec_mode,
                manual_action="skip", skip_reason=result_action.reason,
                paused=True, pause_screenshot_path=pause_screenshot,
            )
        else:  # fail
            return StepResult(
                action=action, passed=False,
                message="Manual step failed",
                duration=duration, execution_mode=exec_mode,
                manual_action="fail", paused=True,
                pause_screenshot_path=pause_screenshot,
            )
```

- [ ] **Step 3: Add manual_pause to dispatch table**

In `_dispatch`, add `"manual_pause"` handler that delegates to `_handle_manual_step` (this is a fallback for YAML-loaded steps where exec_mode isn't set but action is manual_pause):

```python
# In dispatch handlers dict:
"manual_pause": lambda step: (False, "manual_pause requires handler"),
```

- [ ] **Step 4: Add terminal manual handler to cli.py**

In `src/cli.py`, add:

```python
from src.action_runner import ManualStepAction, ManualStepContext

def _terminal_manual_handler(ctx: ManualStepContext) -> ManualStepAction:
    mode = ctx.execution_mode
    desc = ctx.step.get("description", ctx.step.get("text", ""))
    timeout = ctx.timeout_seconds or 300

    print(f"\n  !! [{mode}] 수동 개입 필요:")
    print(f"     {desc}")
    print(f"     제한 시간: {timeout}초")
    print(f"     [c] 계속  [s] 건너뛰기  [f] 실패 처리")

    while True:
        try:
            choice = input("     선택: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ManualStepAction(decision="fail")
        if choice in ("c", "continue", ""):
            return ManualStepAction(decision="continue")
        if choice in ("s", "skip"):
            reason = input("     사유: ").strip()
            return ManualStepAction(decision="skip", reason=reason)
        if choice in ("f", "fail"):
            return ManualStepAction(decision="fail")
```

Update `cmd_run` to pass the handler:

```python
runner = ActionRunner(adb=adb, screenshot_dir=screenshot_dir,
                     on_manual_step=_terminal_manual_handler)
```

- [ ] **Step 5: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/action_runner.py src/cli.py tests/test_action_runner.py
git commit -m "feat: implement hybrid runner with manual pause/resume callbacks"
```

---

### Task 6: Reporter 3-way Split + tc_loader manual_pause

**Files:**
- Modify: `src/reporter.py`
- Modify: `src/tc_loader.py`

- [ ] **Step 1: Add manual_pause to VALID_ACTIONS**

In `src/tc_loader.py`:

```python
VALID_ACTIONS = {
    "tap_text", "tap_id", "tap_xy", "swipe", "key",
    "shell", "wait", "screenshot", "verify_text",
    "verify_shell", "input_text",
    "manual_pause",
}
```

Add action-specific validation for manual_pause in `validate_tc`:

```python
if step["action"] == "manual_pause" and "description" not in step:
    raise TCValidationError(
        f"{source}: step {i+1}의 manual_pause에 'description' 필드가 필요합니다"
    )
```

- [ ] **Step 2: Update reporter summary**

In `src/reporter.py`, update `get_summary()` to include skipped count:

```python
def get_summary(self) -> dict:
    total = len(self.results)
    passed = sum(1 for r in self.results if r.is_pass)
    skipped = sum(
        1 for r in self.results
        if any(s.manual_action == "skip" for s in r.steps)
    )
    failed = total - passed - skipped
    return {"total": total, "passed": passed, "skipped": skipped, "failed": failed}
```

Update `print_step` for manual step display:

```python
def print_step(self, tc_name, step_index, result):
    if result.manual_action == "skip":
        symbol = "S"
        status = f"SKIPPED: {result.skip_reason}"
    elif result.manual_action and result.paused:
        symbol = "M"
        status = f"MANUAL ({result.manual_action})"
    elif result.passed:
        symbol = "O"
        status = "PASS"
    else:
        symbol = "X"
        status = f"FAIL - {result.message}"

    mode_label = f" [{result.execution_mode}]" if result.execution_mode else ""
    print(f"  [{symbol}] Step {step_index+1}: {result.action}{mode_label} - {status}")
```

- [ ] **Step 3: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add src/tc_loader.py src/reporter.py
git commit -m "feat: add manual_pause validation and 3-way reporter split"
```

---

## Phase 2, Issue 3: Shell Action Map

### Task 7: ShellAction Model + ShellActionMap + Alias Registries

**Files:**
- Create: `src/mmi_converter/shell_action_map.py`
- Test: `tests/test_shell_action_map.py` (create)

- [ ] **Step 1: Write shell action map tests**

```python
# tests/test_shell_action_map.py
"""ShellActionMap 단위 테스트."""
import pytest
from src.mmi_converter.shell_action_map import ShellActionMap
from src.mmi_converter.models import Intent


@pytest.fixture
def sam():
    return ShellActionMap()


class TestHasMapping:
    def test_app_launch_keywords(self, sam):
        assert sam.has_mapping("앱 실행")
        assert sam.has_mapping("앱 열기")

    def test_force_stop_keywords(self, sam):
        assert sam.has_mapping("강제 종료")

    def test_permission_keywords(self, sam):
        assert sam.has_mapping("권한 부여")
        assert sam.has_mapping("권한 철회")

    def test_logcat_keyword(self, sam):
        assert sam.has_mapping("로그 초기화")

    def test_unknown_keyword(self, sam):
        assert not sam.has_mapping("화면 캡처")


class TestResolve:
    def test_clear_logcat_no_params(self, sam):
        intent = Intent(type="navigate", target="로그 초기화")
        action = sam.resolve(intent)
        assert action is not None
        assert action.key == "clear_logcat"
        assert action.required_params == []

    def test_launch_app_with_alias(self, sam):
        intent = Intent(type="navigate", target="카카오톡 실행")
        action = sam.resolve(intent)
        assert action is not None
        assert action.key == "launch_app"


class TestRenderCommand:
    def test_clear_logcat(self, sam):
        intent = Intent(type="navigate", target="로그 초기화")
        action = sam.resolve(intent)
        cmd = sam.render_command(action, {})
        assert cmd == "logcat -c"

    def test_force_stop_with_package(self, sam):
        intent = Intent(type="navigate", target="카카오톡 강제 종료")
        action = sam.resolve(intent)
        cmd = sam.render_command(action, {"package": "com.kakao.talk"})
        assert cmd == "am force-stop com.kakao.talk"


class TestAliasRegistry:
    def test_app_alias(self, sam):
        assert sam.resolve_app_alias("카카오톡") == "com.kakao.talk"
        assert sam.resolve_app_alias("유튜브") == "com.google.android.youtube"
        assert sam.resolve_app_alias("알수없는앱") is None

    def test_permission_alias(self, sam):
        assert sam.resolve_permission_alias("카메라 권한") == "android.permission.CAMERA"
        assert sam.resolve_permission_alias("위치 권한") == "android.permission.ACCESS_FINE_LOCATION"
        assert sam.resolve_permission_alias("알수없는권한") is None

    def test_settings_alias(self, sam):
        assert "WIFI" in sam.resolve_settings_alias("Wi-Fi")
        assert "WIFI" in sam.resolve_settings_alias("와이파이")
        assert "WIFI" in sam.resolve_settings_alias("wifi")
        # fallback
        assert "SETTINGS" in sam.resolve_settings_alias("알수없는설정")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_shell_action_map.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ShellActionMap**

Create `src/mmi_converter/shell_action_map.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Intent


@dataclass(slots=True)
class ShellAction:
    key: str
    command_template: str
    required_params: list[str]
    optional_params: dict[str, str] = field(default_factory=dict)
    description: str = ""


APP_ALIAS_REGISTRY = {
    "카카오톡": "com.kakao.talk",
    "유튜브": "com.google.android.youtube",
    "설정": "com.android.settings",
    "전화": "com.android.dialer",
    "카메라": "com.android.camera",
    "갤러리": "com.android.gallery3d",
    "메시지": "com.android.mms",
    "크롬": "com.android.chrome",
    "카카오뱅크": "com.kakaobank.channel",
}

PERMISSION_ALIAS_REGISTRY = {
    "카메라 권한": "android.permission.CAMERA",
    "위치 권한": "android.permission.ACCESS_FINE_LOCATION",
    "전화 권한": "android.permission.READ_PHONE_STATE",
    "마이크 권한": "android.permission.RECORD_AUDIO",
    "저장소 권한": "android.permission.READ_EXTERNAL_STORAGE",
    "연락처 권한": "android.permission.READ_CONTACTS",
    "통화 기록 권한": "android.permission.READ_CALL_LOG",
}

SETTINGS_INTENTS = {
    "Wi-Fi": "android.settings.WIFI_SETTINGS",
    "블루투스": "android.settings.BLUETOOTH_SETTINGS",
    "디스플레이": "android.settings.DISPLAY_SETTINGS",
    "소리": "android.settings.SOUND_SETTINGS",
    "배터리": "android.intent.action.POWER_USAGE_SUMMARY",
    "앱": "android.settings.APPLICATION_SETTINGS",
}

_SETTINGS_ALIASES = {
    "와이파이": "Wi-Fi", "wifi": "Wi-Fi", "wi-fi": "Wi-Fi",
    "블루투쓰": "블루투스", "bluetooth": "블루투스",
    "화면": "디스플레이", "display": "디스플레이",
    "sound": "소리", "사운드": "소리",
    "battery": "배터리",
    "application": "앱", "애플리케이션": "앱",
}

_ACTIONS: list[tuple[list[str], ShellAction]] = [
    (
        ["앱 실행", "앱 열기", "실행"],
        ShellAction(key="launch_app", command_template="am start -n {package}/{activity}",
                    required_params=["package"], optional_params={"activity": ".MainActivity"},
                    description="앱 실행"),
    ),
    (
        ["앱 종료", "강제 종료", "앱 강제 종료"],
        ShellAction(key="force_stop", command_template="am force-stop {package}",
                    required_params=["package"], description="앱 강제 종료"),
    ),
    (
        ["권한 부여", "권한 허용"],
        ShellAction(key="grant_permission", command_template="pm grant {package} {permission}",
                    required_params=["package", "permission"], description="권한 부여"),
    ),
    (
        ["권한 거부", "권한 철회"],
        ShellAction(key="revoke_permission", command_template="pm revoke {package} {permission}",
                    required_params=["package", "permission"], description="권한 철회"),
    ),
    (
        ["로그 초기화", "logcat 초기화"],
        ShellAction(key="clear_logcat", command_template="logcat -c",
                    required_params=[], description="logcat 초기화"),
    ),
    (
        ["설정 화면 진입", "설정 열기"],
        ShellAction(key="open_settings", command_template="am start -a {settings_action}",
                    required_params=["settings_action"], description="설정 화면 진입"),
    ),
]


class ShellActionMap:
    def __init__(self) -> None:
        self._keyword_map: dict[str, ShellAction] = {}
        for keywords, action in _ACTIONS:
            for kw in keywords:
                self._keyword_map[kw] = action

    def has_mapping(self, keyword: str) -> bool:
        return any(kw in keyword for kw in self._keyword_map)

    def resolve(self, intent: Intent) -> ShellAction | None:
        text = intent.target or ""
        for kw, action in self._keyword_map.items():
            if kw in text:
                return action
        return None

    def render_command(self, action: ShellAction, params: dict) -> str:
        merged = {**action.optional_params, **params}
        return action.command_template.format(**merged)

    def resolve_app_alias(self, name: str) -> str | None:
        return APP_ALIAS_REGISTRY.get(name)

    def resolve_permission_alias(self, name: str) -> str | None:
        return PERMISSION_ALIAS_REGISTRY.get(name)

    def resolve_settings_alias(self, name: str) -> str:
        normalized = _SETTINGS_ALIASES.get(name.lower(), name)
        return SETTINGS_INTENTS.get(normalized, "android.settings.SETTINGS")
```

- [ ] **Step 4: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_shell_action_map.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mmi_converter/shell_action_map.py tests/test_shell_action_map.py
git commit -m "feat: implement ShellActionMap with alias registries"
```

---

### Task 8: Compiler ClassifiedIntent Integration

**Files:**
- Modify: `src/mmi_converter/compiler.py`
- Modify: `src/mmi_converter/service.py`
- Test: `tests/test_mmi_compiler.py`

- [ ] **Step 1: Write compiler tests for ClassifiedIntent**

Add to `tests/test_mmi_compiler.py`:

```python
from src.mmi_converter.models import ClassifiedIntent


class TestClassifiedIntentCompilation:
    def test_shell_auto_with_resolved_params(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="로그 초기화"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "shell"
        assert steps[0]["command"] == "logcat -c"

    def test_manual_required_emits_manual_pause(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="이어폰 연결"),
            execution_mode="MANUAL_REQUIRED",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "manual_pause"
        assert steps[0]["execution_mode"] == "MANUAL_REQUIRED"

    def test_external_event_emits_manual_pause(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="수신 전화"),
            execution_mode="EXTERNAL_EVENT",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert steps[0]["action"] == "manual_pause"
        assert steps[0]["execution_mode"] == "EXTERNAL_EVENT"

    def test_ui_auto_compiles_normally(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="설정"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert steps[0] == {"action": "tap_text", "text": "설정"}
```

- [ ] **Step 2: Add compile_classified to compiler**

Add method to `TCRunnerCompiler` in `src/mmi_converter/compiler.py`:

```python
from .shell_action_map import ShellActionMap

class TCRunnerCompiler:
    def __init__(self, shell_action_map: ShellActionMap | None = None):
        self._shell_map = shell_action_map or ShellActionMap()

    def compile_classified(self, ci: 'ClassifiedIntent') -> tuple[list[dict], list[str]]:
        """ClassifiedIntent → (steps, warnings)."""
        warnings: list[str] = []
        intent = ci.intent

        if ci.execution_mode in ("MANUAL_REQUIRED", "EXTERNAL_EVENT"):
            step = {
                "action": "manual_pause",
                "execution_mode": ci.execution_mode,
                "step_role": ci.step_role,
                "description": intent.target or "",
            }
            return [step], warnings

        if ci.execution_mode == "SHELL_AUTO":
            action = self._shell_map.resolve(intent)
            if action:
                params = self._extract_shell_params(intent, action)
                unresolved = [p for p in action.required_params if p not in params]
                if unresolved:
                    step = {
                        "action": "shell",
                        "command": action.command_template,
                        "execution_mode": "SHELL_AUTO",
                        "compile_status": "UNRESOLVED_PARAMS",
                        "runnable": False,
                        "_unresolved_params": unresolved,
                    }
                    warnings.append(f"unresolved_params: {unresolved} for {action.key}")
                    return [step], warnings
                cmd = self._shell_map.render_command(action, params)
                return [{"action": "shell", "command": cmd, "execution_mode": "SHELL_AUTO"}], warnings
            warnings.append(f"shell_resolve_failed: {intent.target}")

        # Default: use existing intent compilation
        compiled = self._compile_intent(intent, warnings)
        return compiled, warnings

    def _extract_shell_params(self, intent: Intent, action) -> dict:
        params = {}
        text = intent.target or ""
        # Try alias registries
        if "package" in action.required_params:
            for app_name, pkg in self._shell_map._keyword_map.items():
                pass  # handled below
            # Search for app name in target text
            for name, pkg in __import__('src.mmi_converter.shell_action_map',
                                        fromlist=['APP_ALIAS_REGISTRY']).APP_ALIAS_REGISTRY.items():
                if name in text:
                    params["package"] = pkg
                    break
        if "permission" in action.required_params:
            from .shell_action_map import PERMISSION_ALIAS_REGISTRY
            for name, perm in PERMISSION_ALIAS_REGISTRY.items():
                if name in text:
                    params["permission"] = perm
                    break
        if "settings_action" in action.required_params:
            # extract settings target from text
            params["settings_action"] = self._shell_map.resolve_settings_alias(text)
        return params
```

Note: The `_extract_shell_params` above is a simplified version. Refine as needed during implementation. Import the registries cleanly:

```python
from .shell_action_map import ShellActionMap, APP_ALIAS_REGISTRY, PERMISSION_ALIAS_REGISTRY
```

- [ ] **Step 3: Update service.py to use compile_classified**

Update `convert_row` in service.py to compile from `classified` list instead of from `ir` directly:

```python
# In convert_row, after step classification:
compiled_steps = []
all_warnings = list(ir.warnings)
for ci in classified:
    steps, warns = self.compiler.compile_classified(ci)
    compiled_steps.extend(steps)
    all_warnings.extend(warns)
```

- [ ] **Step 4: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/mmi_converter/compiler.py src/mmi_converter/service.py tests/test_mmi_compiler.py
git commit -m "feat: compiler accepts ClassifiedIntent, emits shell/manual_pause steps"
```

---

## Phase 2, Issue 4: Multi-format Segmenter

### Task 9: Format Detection + Split Strategies

**Files:**
- Modify: `src/mmi_converter/procedure_parser.py`
- Test: `tests/test_mmi_procedure_parser.py`

- [ ] **Step 1: Write multi-format segmenter tests**

Add to `tests/test_mmi_procedure_parser.py`:

```python
class TestMultiFormatSegmenter:
    def test_numbered_paren(self):
        seg = ProcedureSegmenter()
        result = seg.split("1) 앱 실행 2) 권한 거부 3) 뒤로가기")
        assert result == ["앱 실행", "권한 거부", "뒤로가기"]

    def test_numbered_dot(self):
        seg = ProcedureSegmenter()
        result = seg.split("1. 앱 실행 2. 권한 거부")
        assert result == ["앱 실행", "권한 거부"]

    def test_circled_numbers(self):
        seg = ProcedureSegmenter()
        result = seg.split("① 홈 화면 ② 설정 진입 ③ 확인")
        assert result == ["홈 화면", "설정 진입", "확인"]

    def test_menu_chain_still_works(self):
        seg = ProcedureSegmenter()
        result = seg.split("설정 > 네트워크 > Wi-Fi")
        assert result == ["설정", "네트워크", "Wi-Fi"]

    def test_mixed_numbered_and_menu(self):
        seg = ProcedureSegmenter()
        result = seg.split("1) 설정 > 네트워크 > Wi-Fi 2) 토글 On")
        assert len(result) == 4
        assert result[0] == "설정"
        assert result[1] == "네트워크"
        assert result[2] == "Wi-Fi"
        assert result[3] == "토글 On"

    def test_newline_format(self):
        seg = ProcedureSegmenter()
        result = seg.split("앱 실행\n권한 거부\n수신 전화")
        assert result == ["앱 실행", "권한 거부", "수신 전화"]

    def test_connector_after_in_parens_preserved(self):
        seg = ProcedureSegmenter()
        result = seg.split("(예: 원격제어 앱 실행 후 확인)")
        # 괄호 내부의 "후"로 분리하지 않음
        assert len(result) == 1

    def test_slash_still_works(self):
        seg = ProcedureSegmenter()
        result = seg.split("설정 / 네트워크")
        assert result == ["설정", "네트워크"]
```

- [ ] **Step 2: Implement ProcedureFormat + detection + hierarchical split**

In `src/mmi_converter/procedure_parser.py`, replace `ProcedureSegmenter`:

```python
from enum import Enum

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
        # Protect parenthesized content
        depth = 0
        protected = []
        current = []
        for char in text:
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            if depth > 0:
                current.append(char)
            else:
                current.append(char)
                # Check if we can split here (will be done by regex)
        joined = "".join(current)

        if depth > 0 or "(" in text:
            # Has parens — protect and split carefully
            segments = []
            buf = ""
            paren_depth = 0
            for char in text:
                if char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth = max(0, paren_depth - 1)
                buf += char
                if paren_depth == 0:
                    parts = self._connector_pattern.split(buf)
                    if len(parts) > 1:
                        segments.extend(parts)
                        buf = ""
            if buf:
                segments.extend(self._connector_pattern.split(buf))
            return segments if segments else [text]

        return self._connector_pattern.split(text)

    def _normalize(self, text: str) -> str:
        text = " ".join(text.strip().split())
        text = self._numbered_prefix.sub("", text).strip()
        text = self._numbered_paren_prefix.sub("", text).strip()
        text = self._circled_prefix.sub("", text).strip()
        text = re.sub(r"\(\s*\)", "", text).strip()
        return text
```

- [ ] **Step 3: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_mmi_procedure_parser.py -v`
Expected: All pass including new multi-format tests and existing regression tests

- [ ] **Step 4: Run full regression**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/mmi_converter/procedure_parser.py tests/test_mmi_procedure_parser.py
git commit -m "feat: multi-format segmenter with numbered/circled/mixed/hierarchical split"
```

---

## Phase 3, Issue 5: YAML Export

### Task 10: YAML Exporter + export-mmi CLI

**Files:**
- Create: `src/mmi_converter/exporter.py`
- Modify: `src/cli.py`
- Test: `tests/test_exporter.py` (create)

- [ ] **Step 1: Write exporter tests**

```python
# tests/test_exporter.py
"""YAML exporter 단위 테스트."""
import hashlib
import pytest
from pathlib import Path
from src.mmi_converter.exporter import YAMLExporter, check_runnable
from src.mmi_converter.models import ConversionPreview, Intent


@pytest.fixture
def exporter(tmp_path):
    return YAMLExporter(output_dir=tmp_path)


def _preview(name="TC-01_테스트", auto_class="FULL_AUTO", steps=None, warnings=None):
    return ConversionPreview(
        tc_name=name,
        automation_class=auto_class,
        source_procedure="설정 > 네트워크",
        source_expected="표시된다",
        parsed_intents=[],
        compiled_steps=steps or [{"action": "tap_text", "text": "설정"}],
        warnings=warnings or [],
    )


class TestCheckRunnable:
    def test_normal_steps_are_runnable(self):
        preview = _preview(steps=[{"action": "tap_text", "text": "설정"}])
        runnable, issues = check_runnable(preview)
        assert runnable

    def test_unresolved_params_not_runnable(self):
        preview = _preview(steps=[{
            "action": "shell", "command": "am start -n {package}",
            "compile_status": "UNRESOLVED_PARAMS",
        }])
        runnable, issues = check_runnable(preview)
        assert not runnable

    def test_empty_steps_not_runnable(self):
        preview = _preview(steps=[])
        runnable, issues = check_runnable(preview)
        assert not runnable


class TestYAMLExporter:
    def test_export_creates_file(self, exporter, tmp_path):
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=2)
        assert path.exists()
        assert path.suffix == ".yaml"

    def test_filename_has_hash(self, exporter):
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=2)
        assert "_" in path.stem  # tc_name + hash

    def test_skip_existing_without_overwrite(self, exporter, tmp_path):
        preview = _preview()
        path1 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        path2 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        assert path2 is None  # skipped

    def test_overwrite_flag(self, exporter):
        exporter.overwrite = True
        preview = _preview()
        path1 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        path2 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        assert path2 is not None
```

- [ ] **Step 2: Implement exporter**

Create `src/mmi_converter/exporter.py`:

```python
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import yaml

from .models import ConversionPreview


def check_runnable(preview: ConversionPreview) -> tuple[bool, list[str]]:
    issues = []
    if not preview.compiled_steps:
        issues.append("compiled steps가 비어 있음")
    for i, step in enumerate(preview.compiled_steps):
        if step.get("compile_status") == "UNRESOLVED_PARAMS":
            issues.append(f"Step {i+1}: unresolved params {step.get('_unresolved_params')}")
        if step.get("action") == "shell" and "{" in step.get("command", ""):
            issues.append(f"Step {i+1}: placeholder in command")
        if step.get("action") == "manual_pause" and not step.get("description"):
            issues.append(f"Step {i+1}: manual_pause missing description")
    for w in preview.warnings:
        if "shell_mapping_missing" in w:
            issues.append(f"치명 warning: {w}")
    return len(issues) == 0, issues


def _make_filename(tc_name: str, procedure: str, expected: str) -> str:
    safe = re.sub(r"[^\w가-힣\s-]", "", tc_name)
    safe = re.sub(r"\s+", "_", safe.strip())[:80]
    content_hash = hashlib.sha256(
        f"{tc_name}{procedure}{expected}".encode()
    ).hexdigest()[:4]
    return f"{safe}_{content_hash}.yaml"


class YAMLExporter:
    def __init__(self, output_dir: Path, overwrite: bool = False):
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_one(
        self,
        preview: ConversionPreview,
        source_file: str,
        source_sheet: str,
        source_row: int,
    ) -> Path | None:
        filename = _make_filename(
            preview.tc_name, preview.source_procedure, preview.source_expected,
        )
        path = self.output_dir / filename

        if path.exists() and not self.overwrite:
            return None

        runnable, _ = check_runnable(preview)

        doc = {
            "name": preview.tc_name,
            "description": preview.source_procedure[:200],
            "metadata": {
                "source_file": source_file,
                "source_sheet": source_sheet,
                "source_row": source_row,
                "automation_class": preview.automation_class,
                "runnable": runnable,
                "has_manual_steps": any(
                    s.get("action") == "manual_pause" for s in preview.compiled_steps
                ),
                "has_shell_actions": any(
                    s.get("action") == "shell" for s in preview.compiled_steps
                ),
                "has_unresolved_params": any(
                    s.get("compile_status") == "UNRESOLVED_PARAMS"
                    for s in preview.compiled_steps
                ),
                "warnings": preview.warnings[:20],
                "exported_at": datetime.now().isoformat(timespec="seconds"),
            },
            "steps": preview.compiled_steps,
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return path
```

- [ ] **Step 3: Add export-mmi CLI command**

In `src/cli.py`, add `cmd_export_mmi` and wire it up:

```python
from src.mmi_converter.exporter import YAMLExporter, check_runnable

def cmd_export_mmi(args):
    """MMI 엑셀 T/C 변환 및 YAML export."""
    xlsx_path = Path(args.xlsx_file)
    if not xlsx_path.exists():
        print(f"ERROR: {xlsx_path} not found")
        sys.exit(1)

    try:
        rows = load_mmi_rows(xlsx_path, sheet_name=args.sheet)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not rows:
        print("ERROR: No rows loaded")
        sys.exit(1)

    svc = MMIConversionService()
    previews = []
    for row in rows:
        preview = svc.convert_row(row)
        previews.append((row, preview))

    # Filter by class
    target_classes = {"FULL_AUTO"}
    if args.include_semi:
        target_classes.add("SEMI_AUTO")
    if args.only_class:
        target_classes = {args.only_class}

    filtered = [(r, p) for r, p in previews if p.automation_class in target_classes]

    if args.dry_run:
        # Preview mode
        for _, preview in filtered:
            runnable, issues = check_runnable(preview)
            status = "RUNNABLE" if runnable else "UNRUNNABLE"
            print(f"  [{status}] {preview.tc_name} [{preview.automation_class}]")
            for issue in issues:
                print(f"    ! {issue}")
        print(f"\nTotal: {len(filtered)} TCs")
        return

    # Check runnable (fail-fast)
    unrunnable = [(r, p) for r, p in filtered if not check_runnable(p)[0]]
    if unrunnable and not args.skip_unrunnable and not args.export_unrunnable:
        print(f"Export aborted: unrunnable TC {len(unrunnable)}개 발견")
        for _, p in unrunnable:
            _, issues = check_runnable(p)
            print(f"  {p.tc_name}: {'; '.join(issues)}")
        print(f"\n힌트:")
        print(f"  --skip-unrunnable         제외하고 계속 진행")
        print(f"  --export-unrunnable       placeholder 포함 export")
        sys.exit(1)

    if args.skip_unrunnable:
        filtered = [(r, p) for r, p in filtered if check_runnable(p)[0]]

    output_dir = Path(args.output_dir)
    exporter = YAMLExporter(output_dir=output_dir, overwrite=args.overwrite)

    created = 0
    skipped = 0
    for row, preview in filtered:
        path = exporter.export_one(
            preview,
            source_file=xlsx_path.name,
            source_sheet=args.sheet,
            source_row=row.row_index,
        )
        if path:
            created += 1
        else:
            skipped += 1

    print(f"\nExport 완료:")
    print(f"  생성      : {created}개")
    print(f"  건너뜀    : {skipped}개")
    print(f"  출력 디렉토리: {output_dir}")
```

Add to `main()`:

```python
# export-mmi
export_parser = subparsers.add_parser("export-mmi", help="MMI 엑셀 T/C → YAML export")
export_parser.add_argument("xlsx_file", help="MMI 엑셀 파일 경로")
export_parser.add_argument("--sheet", default="ODIN 기본기능 TC(MMI 내용추가)(4번)", help="시트명")
export_parser.add_argument("--output-dir", default="exported", help="출력 디렉토리")
export_parser.add_argument("--dry-run", action="store_true", help="미리보기만 (파일 생성 없음)")
export_parser.add_argument("--only-class", help="분류 필터")
export_parser.add_argument("--include-semi", action="store_true", help="SEMI_AUTO도 포함")
export_parser.add_argument("--skip-unrunnable", action="store_true", help="unrunnable 제외")
export_parser.add_argument("--export-unrunnable", action="store_true", help="unrunnable도 export")
export_parser.add_argument("--overwrite", action="store_true", help="기존 파일 덮어쓰기")
export_parser.set_defaults(func=cmd_export_mmi)
```

- [ ] **Step 4: Run tests**

Run: `./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/mmi_converter/exporter.py tests/test_exporter.py src/cli.py
git commit -m "feat: YAML export with fail-fast runnable checking and export-mmi CLI"
```

---

## Final: Integration Verification

### Task 11: Full Regression + TC_1.xlsx Smoke Test

- [ ] **Step 1: Run full test suite**

Run: `./venv/Scripts/python.exe -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Smoke test with TC_1.xlsx**

Run: `./venv/Scripts/python.exe -m src.cli export-mmi tc_samples/TC_1.xlsx --sheet "SS-TC 1" --dry-run`
Expected: Shows TC list with classification and runnable status

- [ ] **Step 3: Test export**

Run: `./venv/Scripts/python.exe -m src.cli export-mmi tc_samples/TC_1.xlsx --sheet "SS-TC 1" --output-dir exported --include-semi --skip-unrunnable`
Expected: Creates YAML files in `exported/` directory

- [ ] **Step 4: Verify exported YAML is loadable**

```bash
./venv/Scripts/python.exe -c "
from src.tc_loader import load_tc
from pathlib import Path
for f in Path('exported').glob('*.yaml'):
    tc = load_tc(f)
    print(f'  OK: {tc[\"name\"]}')
"
```

- [ ] **Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: integration verification and smoke test fixes"
```
