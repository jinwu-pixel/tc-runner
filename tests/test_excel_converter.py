from pathlib import Path
import yaml
from openpyxl import Workbook

from src.excel_converter import convert_excel_to_yaml


def create_test_excel(path: Path) -> None:
    """표준 템플릿 형식의 테스트 엑셀 파일을 생성한다."""
    wb = Workbook()
    ws = wb.active
    ws.append(["TC Name", "Step", "Action", "Parameter1", "Parameter2", "Expected"])
    ws.append(["Wi-Fi 테스트", 1, "tap_text", "설정", "", ""])
    ws.append(["Wi-Fi 테스트", 2, "tap_text", "Wi-Fi", "", ""])
    ws.append(["Wi-Fi 테스트", 3, "wait", "2", "", ""])
    ws.append(["Wi-Fi 테스트", 4, "verify_text", "연결됨", "", ""])
    ws.append(["콜 테스트", 1, "tap_text", "전화", "", ""])
    ws.append(["콜 테스트", 2, "input_text", "01012345678", "", ""])
    ws.append(["콜 테스트", 3, "tap_id", "com.phone:id/call_btn", "", ""])
    ws.append(["콜 테스트", 4, "verify_shell", "dumpsys telephony.registry", "", "mCallState=2"])
    wb.save(path)


def test_convert_excel_to_yaml(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    create_test_excel(xlsx)
    output_dir = tmp_path / "output"

    files = convert_excel_to_yaml(xlsx, output_dir)

    assert len(files) == 2

    # Wi-Fi 테스트 파일 확인
    wifi_file = output_dir / "Wi-Fi 테스트.yaml"
    assert wifi_file.exists()
    with open(wifi_file, "r", encoding="utf-8") as f:
        tc = yaml.safe_load(f)
    assert tc["name"] == "Wi-Fi 테스트"
    assert len(tc["steps"]) == 4
    assert tc["steps"][0] == {"action": "tap_text", "text": "설정"}
    assert tc["steps"][2] == {"action": "wait", "seconds": 2}

    # 콜 테스트 파일 확인
    call_file = output_dir / "콜 테스트.yaml"
    assert call_file.exists()
    with open(call_file, "r", encoding="utf-8") as f:
        tc = yaml.safe_load(f)
    assert tc["name"] == "콜 테스트"
    assert len(tc["steps"]) == 4
    assert tc["steps"][3] == {
        "action": "verify_shell",
        "command": "dumpsys telephony.registry",
        "expected": "mCallState=2",
    }
