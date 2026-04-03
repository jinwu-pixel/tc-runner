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
                classified_intents=classified,
            )

        # Non-convertible classes from the row-level classifier take precedence
        if not classification.is_convertible:
            return ConversionPreview(
                tc_name=row.tc_name,
                automation_class=classification.automation_class,
                source_procedure=row.procedure,
                source_expected=row.expected_result,
                parsed_intents=all_intents,
                compiled_steps=[],
                warnings=[],
                reasons=classification.reasons,
                classified_intents=classified,
            )

        # Compile via ClassifiedIntent path (honors ExecutionMode)
        compiled_steps = []
        all_warnings = list(ir.warnings)
        for ci in classified:
            steps, warns = self.compiler.compile_classified(ci)
            compiled_steps.extend(steps)
            all_warnings.extend(warns)

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
