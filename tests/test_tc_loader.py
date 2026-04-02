from pathlib import Path
import pytest

from src.tc_loader import load_tc, validate_tc, TCValidationError


def test_load_tc_valid(tmp_path):
    tc_file = tmp_path / "test.yaml"
    tc_file.write_text("""
name: Wi-Fi 테스트
description: Wi-Fi 연결 확인
steps:
  - action: tap_text
    text: "설정"
  - action: wait
    seconds: 2
  - action: verify_text
    text: "연결됨"
""", encoding="utf-8")

    tc = load_tc(tc_file)
    assert tc["name"] == "Wi-Fi 테스트"
    assert tc["description"] == "Wi-Fi 연결 확인"
    assert len(tc["steps"]) == 3
    assert tc["steps"][0]["action"] == "tap_text"


def test_load_tc_missing_name(tmp_path):
    tc_file = tmp_path / "bad.yaml"
    tc_file.write_text("""
steps:
  - action: wait
    seconds: 1
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="name"):
        load_tc(tc_file)


def test_load_tc_missing_steps(tmp_path):
    tc_file = tmp_path / "bad2.yaml"
    tc_file.write_text("""
name: 빈 테스트
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="steps"):
        load_tc(tc_file)


def test_load_tc_invalid_action(tmp_path):
    tc_file = tmp_path / "bad3.yaml"
    tc_file.write_text("""
name: 잘못된 액션
steps:
  - action: fly_to_moon
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="fly_to_moon"):
        load_tc(tc_file)
