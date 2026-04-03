from __future__ import annotations

from .classifier import MMITCClassifier
from .compiler import TCRunnerCompiler
from .expected_parser import ExpectedResultParser
from .models import ConversionPreview, TCIR, MMIRow
from .procedure_parser import ProcedureParser
from .step_classifier import StepClassifier


class MMIConversionService:
    def __init__(self) -> None:
        self.classifier = MMITCClassifier()
        self.procedure_parser = ProcedureParser()
        self.expected_parser = ExpectedResultParser()
        self.compiler = TCRunnerCompiler()
        self.step_classifier = StepClassifier()

    def convert_row(self, row: MMIRow, app_context: dict | None = None) -> ConversionPreview:
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
        ctx = {
            "precondition": row.precondition,
            "source_row": row,
        }
        if app_context:
            ctx["app_context"] = app_context
        classified = self.step_classifier.classify(all_intents, context=ctx)
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
                classified_intents=classified,
            )

        # Always compile via ClassifiedIntent path (honors ExecutionMode)
        compiled_steps = []
        all_warnings = list(ir.warnings)
        for ci in classified:
            steps, warns = self.compiler.compile_classified(ci)
            compiled_steps.extend(steps)
            all_warnings.extend(warns)

        # Legacy override: if legacy says non-convertible but step-level
        # classifier says automatable AND compilation produced real auto
        # steps, trust the step-level result instead.
        _AUTO_ACTIONS = {"tap_text", "tap_id", "tap_xy", "key", "shell",
                         "input_text", "swipe", "wait", "screenshot"}
        if not classification.is_convertible:
            has_auto_steps = any(
                s.get("action") in _AUTO_ACTIONS for s in compiled_steps
            )
            override = (
                tc_class_from_steps in ("FULL_AUTO", "SEMI_AUTO")
                and has_auto_steps
            )
            if override:
                all_warnings.append(
                    f"legacy_override_applied: legacy={classification.automation_class}, "
                    f"step_summary={tc_class_from_steps}"
                )
                all_warnings.append(
                    f"legacy_non_convertible_but_step_summary_{tc_class_from_steps.lower()}"
                )
            else:
                # Legacy is correct — no steps or step classifier also says non-auto
                return ConversionPreview(
                    tc_name=row.tc_name,
                    automation_class=classification.automation_class,
                    source_procedure=row.procedure,
                    source_expected=row.expected_result,
                    parsed_intents=all_intents,
                    compiled_steps=compiled_steps,
                    warnings=all_warnings,
                    reasons=classification.reasons,
                    classified_intents=classified,
                )

        final_class = self._maybe_downgrade(
            tc_class_from_steps,
            intents=intents,
            expected_intents=expected_intents,
            compiled_steps=compiled_steps,
            warnings=all_warnings,
            segments=self.procedure_parser.segmenter.split(row.procedure),
            has_expected_text=bool(row.expected_result.strip()),
        )

        return ConversionPreview(
            tc_name=row.tc_name,
            automation_class=final_class,
            source_procedure=row.procedure,
            source_expected=row.expected_result,
            parsed_intents=ir.all_intents,
            compiled_steps=compiled_steps,
            warnings=all_warnings,
            reasons=classification.reasons,
            classified_intents=classified,
        )

    def _maybe_downgrade(
        self,
        automation_class: str,
        intents: list,
        expected_intents: list,
        compiled_steps: list[dict],
        warnings: list[str],
        segments: list[str],
        has_expected_text: bool = False,
    ) -> str:
        """FULL_AUTO인데 실제 compiled 결과가 빈약하면 SEMI_AUTO로 강등한다."""
        if automation_class != "FULL_AUTO":
            return automation_class

        step_count = len(compiled_steps)
        segment_count = len(segments)

        if segment_count >= 4 and step_count <= 1:
            return "SEMI_AUTO"

        has_toggle = any(i.type == "toggle" for i in intents)
        has_input = any(i.type == "input_text" for i in intents)
        toggle_steps = sum(1 for s in compiled_steps if s.get("action") in ("tap_text",) and "토글" in s.get("text", ""))
        input_steps = sum(1 for s in compiled_steps if s.get("action") == "input_text")
        if (has_toggle or has_input) and (toggle_steps + input_steps) == 0:
            return "SEMI_AUTO"

        if has_expected_text and not any(s.get("action", "").startswith("verify") for s in compiled_steps):
            return "SEMI_AUTO"

        return automation_class
