from pathlib import Path
from collections import defaultdict

import yaml
from openpyxl import load_workbook


# action별 Parameter1/Parameter2 매핑 규칙
PARAM_MAP = {
    "tap_text":     {"param1": "text"},
    "tap_id":       {"param1": "id"},
    "tap_xy":       {"param1": "x", "param2": "y"},
    "swipe":        {"param1": "x1", "param2": "y1"},  # x2,y2는 추가 컬럼 필요 — 간소화
    "key":          {"param1": "keycode"},
    "shell":        {"param1": "command"},
    "wait":         {"param1": "seconds", "param1_type": int},
    "screenshot":   {"param1": "name"},
    "verify_text":  {"param1": "text"},
    "verify_shell": {"param1": "command", "param2": "expected"},
    "input_text":   {"param1": "text"},
}


def convert_excel_to_yaml(xlsx_path: Path, output_dir: Path) -> list[Path]:
    """엑셀 T/C 파일을 YAML 파일들로 변환한다."""
    wb = load_workbook(xlsx_path, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))  # 헤더 스킵
    wb.close()

    # TC Name별로 step 그룹핑
    tc_groups = defaultdict(list)
    for row in rows:
        tc_name, step_num, action, param1, param2, expected = (
            row[0], row[1], row[2], row[3], row[4], row[5]
        )
        if not tc_name or not action:
            continue
        tc_groups[str(tc_name)].append({
            "action": str(action),
            "param1": param1,
            "param2": param2,
            "expected": expected,
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    for tc_name, raw_steps in tc_groups.items():
        steps = []
        for raw in raw_steps:
            step = _build_step(raw)
            if step:
                steps.append(step)

        tc_data = {"name": tc_name, "description": "", "steps": steps}

        out_file = output_dir / f"{tc_name}.yaml"
        with open(out_file, "w", encoding="utf-8") as f:
            yaml.dump(tc_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        created_files.append(out_file)

    return created_files


def _build_step(raw: dict) -> dict | None:
    """엑셀 행 데이터를 YAML step dict로 변환한다."""
    action = raw["action"]
    mapping = PARAM_MAP.get(action)
    if not mapping:
        return {"action": action}

    step = {"action": action}

    if "param1" in mapping and raw["param1"] is not None:
        key = mapping["param1"]
        value = raw["param1"]
        if mapping.get("param1_type") == int:
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
        step[key] = value

    if "param2" in mapping and raw.get("param2") is not None and raw["param2"] != "":
        step[mapping["param2"]] = raw["param2"]

    # verify_shell의 expected는 Expected 컬럼에서 가져옴
    if action == "verify_shell" and raw.get("expected"):
        step["expected"] = str(raw["expected"])

    return step
