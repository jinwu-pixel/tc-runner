from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


AutomationClass = Literal[
    "FULL_AUTO",
    "SEMI_AUTO",
    "MANUAL_REQUIRED",
    "OUT_OF_SCOPE",
    "AMBIGUOUS_NL",
]

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

IntentType = Literal[
    "navigate",
    "tap_text",
    "tap_id",
    "toggle",
    "press_key",
    "input_text",
    "wait",
    "verify_text",
    "verify_shell",
    "manual_required",
]


@dataclass(slots=True)
class MMIRow:
    row_index: int
    no: str
    feature_name: str
    functionality: str
    precondition: str
    procedure: str
    expected_result: str
    priority: str
    sheet_name: str

    @property
    def tc_name(self) -> str:
        base_no = self.no.strip() or f"ROW{self.row_index}"
        feature = self.feature_name.strip() or "UNNAMED"
        feature = "_".join(feature.split())
        return f"{base_no}_{feature}"


@dataclass(slots=True)
class ClassificationResult:
    automation_class: AutomationClass
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_convertible(self) -> bool:
        return self.automation_class in {"FULL_AUTO", "SEMI_AUTO"}


@dataclass(slots=True)
class Intent:
    type: IntentType
    target: Optional[str] = None
    value: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass(slots=True)
class TCIR:
    tc_name: str
    description: str
    preconditions: list[str]
    intents: list[Intent]
    expected_intents: list[Intent]
    manual_requirements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_row: Optional[MMIRow] = None

    @property
    def all_intents(self) -> list[Intent]:
        return [*self.intents, *self.expected_intents]


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


@dataclass(slots=True)
class ClassifiedIntent:
    intent: Intent
    execution_mode: ExecutionMode
    step_role: StepRole
    confidence: float = 1.0
    reasons: list[str] = field(default_factory=list)
