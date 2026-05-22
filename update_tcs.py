"""SS-01~17 YAML에 execution_type, manual_detail 필드 추가"""
import yaml, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# TC별 매핑 정의
MAPPING = {
    "SS-01": ("AUTO",           "NONE"),
    "SS-02": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-03": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-04": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-05": ("MANUAL_LOCAL",   "BUTTON_TOUCH"),
    "SS-06": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-07": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-08": ("MANUAL_LOCAL",   "BUTTON_TOUCH"),
    "SS-09": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
    "SS-10": ("MANUAL_LOCAL",   "APP_INSTALL"),
    "SS-11": ("EXTERNAL_EVENT", "CALL_RECEIVE|BUTTON_TOUCH"),
    "SS-12": ("EXTERNAL_EVENT", "CALL_RECEIVE|BUTTON_TOUCH"),
    "SS-13": ("EXTERNAL_EVENT", "CALL_RECEIVE|BUTTON_TOUCH"),
    "SS-14": ("MANUAL_LOCAL",   "BUTTON_TOUCH"),
    "SS-15": ("MANUAL_LOCAL",   "APP_INSTALL|CALL_PLACE"),
    "SS-16": ("MANUAL_LOCAL",   "BUTTON_TOUCH"),
    "SS-17": ("EXTERNAL_EVENT", "CALL_RECEIVE"),
}

tc_dir = Path("stage2_output/new_tcs")

for f in sorted(tc_dir.glob("SS-*.yaml")):
    text = f.read_text(encoding="utf-8")
    tc = yaml.safe_load(text)
    tc_id = tc["tc_name"]

    if tc_id not in MAPPING:
        print(f"  SKIP  {tc_id} — 매핑 없음")
        continue

    exec_type, detail = MAPPING[tc_id]

    # 이미 있으면 스킵
    meta = tc.get("metadata", {})
    if "execution_type" in meta and "manual_detail" in meta:
        print(f"  EXISTS {tc_id}")
        continue

    # warnings: 뒤에 삽입 (metadata 블록 내부)
    lines = text.split("\n")
    insert_idx = None
    in_metadata = False
    for i, line in enumerate(lines):
        if line.startswith("metadata:"):
            in_metadata = True
            continue
        if in_metadata:
            # metadata 블록 끝 감지 (들여쓰기 없는 라인)
            if line and not line.startswith(" ") and not line.startswith("\t"):
                insert_idx = i
                break
    if insert_idx is None:
        insert_idx = len(lines)

    new_lines = [
        f"  execution_type: {exec_type}",
        f"  manual_detail: \"{detail}\"",
    ]
    lines = lines[:insert_idx] + new_lines + lines[insert_idx:]

    f.write_text("\n".join(lines), encoding="utf-8")
    print(f"  OK     {tc_id}: execution_type={exec_type}, manual_detail={detail}")

print("\n완료")
