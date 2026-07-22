import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.action_runner import StepResult
from src.catalog_delta import validate_run_id_for_filename

SUMMARY_SCHEMA_VERSION = 2
SUMMARY_TOOL_VERSION = "runtime-report-v2"
CONTRACT_MODES = frozenset({"legacy", "canonical"})
RUN_STATUSES = frozenset({"COMPLETED", "ABORTED_FAIL_CLOSED"})


@dataclass
class TCResult:
    name: str
    description: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def is_pass(self) -> bool:
        return all(s.passed for s in self.steps)

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.steps)

    @property
    def status(self) -> str:
        has_failed = any(
            (not s.passed) and getattr(s, "manual_action", "") != "skip"
            for s in self.steps
        )
        if has_failed:
            return "failed"
        if any(getattr(s, "manual_action", "") == "skip" for s in self.steps):
            return "skipped"
        return "passed"


class Reporter:
    def __init__(
        self,
        report_dir: Path,
        run_id: Optional[str] = None,
        *,
        contract_mode: str = "legacy",
        run_status: str = "COMPLETED",
    ):
        if contract_mode not in CONTRACT_MODES:
            raise ValueError(f"unsupported contract_mode: {contract_mode!r}")
        self.report_dir = Path(report_dir)
        self.run_id = validate_run_id_for_filename(run_id) if run_id else None
        self.contract_mode = contract_mode
        self.run_status = run_status
        self.results: list[TCResult] = []
        self.device_info: dict = {}
        self.start_time: datetime = datetime.now()

    @property
    def run_status(self) -> str:
        return self._run_status

    @run_status.setter
    def run_status(self, value: str) -> None:
        if value not in RUN_STATUSES:
            raise ValueError(f"unsupported run_status: {value!r}")
        self._run_status = value

    @property
    def bundle_dir(self) -> Path:
        return self.report_dir / self.run_id if self.run_id else self.report_dir

    @property
    def screenshot_dir(self) -> Path:
        if self.run_id:
            return self.bundle_dir / "screenshots"
        return self.report_dir / "screenshots"

    def print_step(self, tc_name: str, step_index: int, result: StepResult) -> None:
        manual_action = getattr(result, "manual_action", "")
        skip_reason = getattr(result, "skip_reason", "")
        execution_mode = getattr(result, "execution_mode", "")
        paused = getattr(result, "paused", False)

        if manual_action == "skip":
            symbol = "S"
            status = f"SKIPPED: {skip_reason}"
        elif manual_action and paused:
            symbol = "M"
            status = f"MANUAL ({manual_action})"
        elif result.passed:
            symbol = "O"
            status = "PASS"
        else:
            symbol = "X"
            status = f"FAIL - {result.message}"

        mode_label = f" [{execution_mode}]" if execution_mode else ""
        print(f"  [{symbol}] Step {step_index+1}: {result.action}{mode_label} - {status}")

    def print_tc_header(self, tc_name: str) -> None:
        print(f"\n{'='*60}")
        print(f"  T/C: {tc_name}")
        print(f"{'='*60}")

    def print_tc_result(self, tc_result: TCResult) -> None:
        status = "PASS" if tc_result.is_pass else "FAIL"
        print(f"  → Result: {status} ({tc_result.total_duration:.1f}s)")

    def print_summary(self) -> None:
        summary = self.get_summary()
        print(f"\n{'='*60}")
        print(f"  SUMMARY: {summary['passed']}/{summary['total']} passed, "
              f"{summary['skipped']} skipped, {summary['failed']} failed")
        print(f"{'='*60}")

    def get_summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        return {"total": total, "passed": passed, "skipped": skipped, "failed": failed}

    def generate_html(self) -> Path:
        target_dir = self.bundle_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        template_dir = Path(__file__).parent.parent / "templates"
        if template_dir.exists() and (template_dir / "report.html").exists():
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            template = env.get_template("report.html")
        else:
            template = Environment().from_string(DEFAULT_TEMPLATE)

        for tc in self.results:
            for step in tc.steps:
                if step.screenshot_path and step.screenshot_path.exists():
                    with open(step.screenshot_path, "rb") as f:
                        step._screenshot_b64 = base64.b64encode(f.read()).decode("ascii")
                else:
                    step._screenshot_b64 = None

        summary = self.get_summary()
        html_content = template.render(
            device_info=self.device_info,
            summary=summary,
            results=self.results,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if self.run_id:
            report_path = target_dir / "report.html"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = target_dir / f"{timestamp}_report.html"
        report_path.write_text(html_content, encoding="utf-8")
        return report_path

    def write_summary_json(self) -> Path:
        """run_id 가 설정된 bundle 모드에서만 호출. summary.json 을 bundle_dir 에 기록."""
        if not self.run_id:
            raise RuntimeError("write_summary_json requires run_id (bundle mode only)")

        target_dir = self.bundle_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        summary_path = target_dir / "summary.json"

        payload = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "tool_version": SUMMARY_TOOL_VERSION,
            "run_id": self.run_id,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "contract_mode": self.contract_mode,
            "run_status": self.run_status,
            "device": dict(self.device_info or {}),
            "summary": self.get_summary(),
            "results": [self._serialize_tc(tc) for tc in self.results],
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return summary_path

    def _serialize_tc(self, tc: TCResult) -> dict:
        return {
            "name": tc.name,
            "description": tc.description,
            "passed": tc.is_pass,
            "duration_s": round(tc.total_duration, 4),
            "steps": [self._serialize_step(i, s) for i, s in enumerate(tc.steps)],
        }

    def _serialize_step(self, index: int, step: StepResult) -> dict:
        return {
            "index": index + 1,
            "action": step.action,
            "passed": step.passed,
            "duration_s": round(step.duration, 4),
            "message": step.message or "",
            "execution_mode": getattr(step, "execution_mode", "") or "",
            "manual_action": getattr(step, "manual_action", "") or "",
            "skip_reason": getattr(step, "skip_reason", "") or "",
            "paused": bool(getattr(step, "paused", False)),
            "screenshot_path": self._bundle_relative(step.screenshot_path),
        }

    def _bundle_relative(self, path: Optional[Path]) -> Optional[str]:
        if path is None:
            return None
        path = Path(path)
        bundle = self.bundle_dir.resolve()
        try:
            return path.resolve().relative_to(bundle).as_posix()
        except ValueError:
            return path.as_posix()


DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>T/C Report</title>
<style>
body{font-family:sans-serif;margin:20px;background:#f5f5f5}
.header{background:#333;color:white;padding:16px;border-radius:8px}
.summary{display:flex;gap:16px;margin:16px 0}
.card{background:white;padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.pass{color:#4caf50;font-weight:bold} .fail{color:#f44336;font-weight:bold}
table{width:100%;border-collapse:collapse;margin:8px 0}
th,td{text-align:left;padding:8px;border-bottom:1px solid #eee}
th{background:#f9f9f9}
.tc-block{background:white;padding:16px;margin:16px 0;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.screenshot{max-width:400px;margin:8px 0;border:1px solid #ddd;border-radius:4px}
</style></head><body>
<div class="header">
<h1>T/C 실행 리포트</h1>
<p>{{ timestamp }} | {{ device_info.get('model', 'Unknown') }} | Android {{ device_info.get('android_version', '?') }}</p>
</div>
<div class="summary">
<div class="card"><h3>Total</h3><p style="font-size:24px">{{ summary.total }}</p></div>
<div class="card"><h3>Passed</h3><p class="pass" style="font-size:24px">{{ summary.passed }}</p></div>
<div class="card"><h3>Failed</h3><p class="fail" style="font-size:24px">{{ summary.failed }}</p></div>
</div>
{% for tc in results %}
<div class="tc-block">
<h2>{% if tc.is_pass %}<span class="pass">✓</span>{% else %}<span class="fail">✗</span>{% endif %} {{ tc.name }}</h2>
<p>{{ tc.description }}</p>
<table><tr><th>#</th><th>Action</th><th>Result</th><th>Message</th><th>Duration</th></tr>
{% for step in tc.steps %}
<tr>
<td>{{ loop.index }}</td>
<td>{{ step.action }}</td>
<td>{% if step.passed %}<span class="pass">PASS</span>{% else %}<span class="fail">FAIL</span>{% endif %}</td>
<td>{{ step.message[:100] }}</td>
<td>{{ "%.2f"|format(step.duration) }}s</td>
</tr>
{% if step._screenshot_b64 %}
<tr><td colspan="5"><img class="screenshot" src="data:image/png;base64,{{ step._screenshot_b64 }}"></td></tr>
{% endif %}
{% endfor %}
</table>
</div>
{% endfor %}
</body></html>"""
