import base64
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.action_runner import StepResult


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


class Reporter:
    def __init__(self, report_dir: Path):
        self.report_dir = report_dir
        self.results: list[TCResult] = []
        self.device_info: dict = {}
        self.start_time: datetime = datetime.now()

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
        passed = sum(1 for r in self.results if r.is_pass)
        skipped = sum(
            1 for r in self.results
            if any(getattr(s, "manual_action", "") == "skip" for s in r.steps)
        )
        failed = total - passed - skipped
        return {"total": total, "passed": passed, "skipped": skipped, "failed": failed}

    def generate_html(self) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)

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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_content = template.render(
            device_info=self.device_info,
            summary=summary,
            results=self.results,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        report_path = self.report_dir / f"{timestamp}_report.html"
        report_path.write_text(html_content, encoding="utf-8")
        return report_path


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
