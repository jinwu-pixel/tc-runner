import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.action_runner import ActionRunner, StepResult, ManualStepAction, ManualStepContext


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="설정" resource-id="com.test:id/title"
        class="android.widget.TextView" package="com.test"
        bounds="[100,200][300,400]" />
</hierarchy>"""


# Music player favorite-style hierarchy for content-desc 테스트
CD_HIERARCHY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node bounds="[0,0][720,1560]" clickable="false">
    <node clickable="true" bounds="[520,96][616,192]">
      <node text="" content-desc="즐겨찾기" clickable="false" bounds="[544,120][592,168]" />
    </node>
    <node text="홈탭문구" content-desc="홈탭" clickable="true" bounds="[100,1500][200,1560]" />
    <node text="" content-desc="비클릭" clickable="false" bounds="[300,300][400,400]" />
  </node>
</hierarchy>"""

# tap_text vs tap_content_desc cross-cutting:
# HOME tab text="즐겨찾기" + player content-desc="즐겨찾기" 공존
CROSS_CUT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node bounds="[0,0][720,1560]" clickable="false">
    <node clickable="true" bounds="[520,96][616,192]">
      <node text="" content-desc="즐겨찾기" clickable="false" bounds="[544,120][592,168]" />
    </node>
    <node text="즐겨찾기" content-desc="" clickable="true" bounds="[100,1500][200,1560]" />
  </node>
</hierarchy>"""

DUP_CD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node clickable="true" bounds="[0,0][100,100]">
    <node content-desc="중복" clickable="false" bounds="[10,10][50,50]" />
  </node>
  <node clickable="true" bounds="[200,200][300,300]">
    <node content-desc="중복" clickable="false" bounds="[210,210][250,250]" />
  </node>
</hierarchy>"""


def make_runner(adb_mock=None):
    adb = adb_mock or MagicMock()
    return ActionRunner(adb=adb, screenshot_dir=Path("/tmp/screenshots"))


def test_wait_action():
    runner = make_runner()
    result = runner.run_step({"action": "wait", "seconds": 0.01})
    assert result.passed is True
    assert result.action == "wait"


def test_shell_action():
    adb = MagicMock()
    adb.shell.return_value = "some output"
    runner = make_runner(adb)
    result = runner.run_step({"action": "shell", "command": "echo hello"})
    assert result.passed is True
    adb.shell.assert_called_once_with("echo hello")


def test_tap_xy_action():
    adb = MagicMock()
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_xy", "x": 500, "y": 1000})
    assert result.passed is True
    adb.tap.assert_called_once_with(500, 1000)


def test_key_action():
    adb = MagicMock()
    runner = make_runner(adb)
    result = runner.run_step({"action": "key", "keycode": "HOME"})
    assert result.passed is True
    adb.key.assert_called_once_with("HOME")


def test_verify_shell_pass():
    adb = MagicMock()
    adb.shell.return_value = "Wi-Fi is enabled\n"
    runner = make_runner(adb)
    result = runner.run_step({
        "action": "verify_shell",
        "command": "dumpsys wifi",
        "expected": "enabled",
    })
    assert result.passed is True


def test_verify_shell_fail():
    adb = MagicMock()
    adb.shell.return_value = "Wi-Fi is disabled\n"
    runner = make_runner(adb)
    result = runner.run_step({
        "action": "verify_shell",
        "command": "dumpsys wifi",
        "expected": "enabled",
    })
    assert result.passed is False


def test_tap_text_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_text", "text": "설정"})
    assert result.passed is True
    adb.tap.assert_called_once_with(200, 300)


def test_tap_text_not_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "tap_text", "text": "없는텍스트"})
    assert result.passed is False


def test_verify_text_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "verify_text", "text": "설정"})
    assert result.passed is True


def test_verify_text_not_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "verify_text", "text": "없는텍스트"})
    assert result.passed is False


# ─── tap_content_desc / verify_content_desc ───

def test_tap_content_desc_clickable_leaf_taps_leaf_center():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_content_desc", "target": "홈탭"})
    assert result.passed is True
    adb.tap.assert_called_once_with(150, 1530)


def test_tap_content_desc_bubbles_to_clickable_parent_when_leaf_non_clickable():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_content_desc", "target": "즐겨찾기"})
    assert result.passed is True
    # 즐겨찾기 leaf clickable=false → parent center (568, 144)
    adb.tap.assert_called_once_with(568, 144)


def test_tap_content_desc_not_found_fails_after_retries():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "tap_content_desc", "target": "없는항목"})
    assert result.passed is False
    assert "not found" in result.message
    adb.tap.assert_not_called()


def test_tap_content_desc_duplicate_fails_immediately():
    adb = MagicMock()
    adb.dump_ui.return_value = DUP_CD_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "tap_content_desc", "target": "중복"})
    assert result.passed is False
    assert "duplicate" in result.message.lower()
    adb.tap.assert_not_called()


def test_tap_content_desc_no_clickable_ancestor_fails():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "tap_content_desc", "target": "비클릭"})
    assert result.passed is False
    assert "no clickable ancestor" in result.message
    adb.tap.assert_not_called()


def test_tap_content_desc_missing_target_fails():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_content_desc"})
    assert result.passed is False
    # KeyError surfaces via run_step exception path
    adb.tap.assert_not_called()


def test_verify_content_desc_present_passes():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "verify_content_desc", "target": "즐겨찾기"})
    assert result.passed is True
    assert "present" in result.message


def test_verify_content_desc_duplicate_passes():
    # presence assertion이라 duplicate도 PASS
    adb = MagicMock()
    adb.dump_ui.return_value = DUP_CD_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "verify_content_desc", "target": "중복"})
    assert result.passed is True
    assert "count=2" in result.message


def test_verify_content_desc_not_found_fails():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "verify_content_desc", "target": "없는항목"})
    assert result.passed is False
    assert "not found" in result.message


def test_verify_content_desc_missing_target_fails():
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "verify_content_desc"})
    assert result.passed is False


def test_tap_text_vs_tap_content_desc_target_separation():
    # HOME tab text="즐겨찾기" + player content-desc="즐겨찾기" 동시 존재 시
    # tap_text 는 text 노드 (HOME tab) 를 tap, tap_content_desc 는 content-desc 노드 (player)
    adb_text = MagicMock()
    adb_text.dump_ui.return_value = CROSS_CUT_XML
    runner_text = make_runner(adb_text)
    result = runner_text.run_step({"action": "tap_text", "target": "즐겨찾기"})
    assert result.passed is True
    adb_text.tap.assert_called_once_with(150, 1530)  # HOME tab center

    adb_cd = MagicMock()
    adb_cd.dump_ui.return_value = CROSS_CUT_XML
    runner_cd = make_runner(adb_cd)
    result = runner_cd.run_step({"action": "tap_content_desc", "target": "즐겨찾기"})
    assert result.passed is True
    adb_cd.tap.assert_called_once_with(568, 144)  # player parent center


def test_tap_content_desc_no_coordinate_fallback_when_not_found():
    # not_found 케이스에서 좌표 fallback 으로 tap 하지 않는다
    adb = MagicMock()
    adb.dump_ui.return_value = CD_HIERARCHY_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    runner.run_step({"action": "tap_content_desc", "target": "없는항목", "x": 500, "y": 500})
    adb.tap.assert_not_called()


EMPTY_XML = '<?xml version="1.0" encoding="UTF-8"?><hierarchy rotation="0"></hierarchy>'


def test_verify_gone_passes_when_target_absent_in_current_hierarchy():
    # snapshot-level absent — no off-screen / lazy-list guarantee
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "verify_gone", "text": "없는텍스트"})
    assert result.passed is True
    assert "is gone" in result.message


def test_verify_gone_fails_when_target_persists_through_retries():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=2, retry_interval=0)
    result = runner.run_step({"action": "verify_gone", "text": "설정"})
    assert result.passed is False
    assert "still present" in result.message


def test_verify_gone_passes_once_target_disappears_then_returns_immediately():
    # "한 번이라도 사라지면 성공" 의미 — 지속 absent 미보장
    adb = MagicMock()
    adb.dump_ui.side_effect = [SAMPLE_XML, EMPTY_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=3, retry_interval=0)
    result = runner.run_step({"action": "verify_gone", "text": "설정"})
    assert result.passed is True
    assert adb.dump_ui.call_count == 2


def test_verify_gone_with_timeout_polls_at_500ms_interval_until_absent():
    adb = MagicMock()
    adb.dump_ui.side_effect = [SAMPLE_XML, SAMPLE_XML, EMPTY_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"))
    with patch.object(time, "sleep") as mock_sleep:
        result = runner.run_step({"action": "verify_gone", "text": "설정", "timeout": 5000})
    assert result.passed is True
    assert adb.dump_ui.call_count == 3
    # poll interval should be 0.5s between dumps
    assert any(call.args == (0.5,) for call in mock_sleep.call_args_list)


def test_verify_gone_with_timeout_returns_fail_when_target_never_disappears():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"))
    with patch.object(time, "sleep"):
        result = runner.run_step({"action": "verify_gone", "text": "설정", "timeout": 1})
    assert result.passed is False
    assert "still present" in result.message
    assert "1ms" in result.message


class TestHybridPause:
    def test_manual_step_without_handler_fails(self):
        """no-handler → fail-fast."""
        runner = make_runner()
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "이어폰 연결"}
        result = runner.run_step(step)
        assert not result.passed
        assert "manual handler not configured" in result.message

    def test_manual_step_continue(self):
        """continue → passed=True."""
        def handler(ctx):
            return ManualStepAction(decision="continue")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
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
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
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
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test"}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "fail"

    def test_manual_step_timeout(self):
        """timeout → fail with timeout reason."""
        import time as _time
        def slow_handler(ctx):
            _time.sleep(10)  # will be interrupted by timeout
            return ManualStepAction(decision="continue")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=slow_handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test", "manual_timeout": 1}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "fail"
        assert "timeout" in result.message.lower() or "timeout" in (result.skip_reason or "")

    def test_manual_step_handler_exception(self):
        """handler exception → fail gracefully."""
        def error_handler(ctx):
            raise RuntimeError("device disconnected")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=error_handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test"}
        result = runner.run_step(step)
        assert not result.passed
        assert "error" in result.message.lower() or "disconnect" in result.message.lower()


# ─── key_sequence ───

def test_key_sequence_iterates_keys_and_sleeps_between():
    adb = MagicMock()
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep") as mock_sleep:
        result = runner.run_step({
            "action": "key_sequence",
            "keys": ["KEYCODE_TAB", "KEYCODE_TAB", "KEYCODE_ENTER"],
            "delay": 0.25,
        })
    assert result.passed is True
    assert adb.key.call_count == 3
    adb.key.assert_any_call("KEYCODE_TAB")
    adb.key.assert_any_call("KEYCODE_ENTER")
    # delay sleep is called per key (3 times with 0.25)
    assert sum(1 for c in mock_sleep.call_args_list if c.args == (0.25,)) == 3


def test_key_sequence_default_delay_when_omitted():
    adb = MagicMock()
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep") as mock_sleep:
        result = runner.run_step({"action": "key_sequence", "keys": ["KEYCODE_TAB"]})
    assert result.passed is True
    # default delay = 0.5
    assert any(c.args == (0.5,) for c in mock_sleep.call_args_list)


def test_key_sequence_casts_integer_keycodes_to_string():
    adb = MagicMock()
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({"action": "key_sequence", "keys": [61, 66]})
    assert result.passed is True
    adb.key.assert_any_call("61")
    adb.key.assert_any_call("66")


# ─── verify_focus_moved (strict moved) ───

FOCUS_PRE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="A" focused="true" bounds="[100,100][200,200]" />
  <node text="B" focused="false" bounds="[300,100][400,200]" />
</hierarchy>"""

FOCUS_POST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="A" focused="false" bounds="[100,100][200,200]" />
  <node text="B" focused="true" bounds="[300,100][400,200]" />
</hierarchy>"""

FOCUS_NONE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="A" focused="false" bounds="[100,100][200,200]" />
  <node text="B" focused="false" bounds="[300,100][400,200]" />
</hierarchy>"""


def test_verify_focus_moved_passes_when_pre_and_post_bounds_differ():
    adb = MagicMock()
    adb.dump_ui.side_effect = [FOCUS_PRE_XML, FOCUS_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_TAB"},
        })
    assert result.passed is True
    assert "[100,100][200,200]" in result.message
    assert "[300,100][400,200]" in result.message
    adb.key.assert_called_once_with("KEYCODE_TAB")


def test_verify_focus_moved_fails_when_bounds_same():
    adb = MagicMock()
    adb.dump_ui.side_effect = [FOCUS_PRE_XML, FOCUS_PRE_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_TAB"},
        })
    assert result.passed is False
    assert "did not move" in result.message


def test_verify_focus_moved_fails_when_pre_focus_missing():
    adb = MagicMock()
    adb.dump_ui.side_effect = [FOCUS_NONE_XML, FOCUS_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_TAB"},
        })
    assert result.passed is False
    assert "before trigger" in result.message


def test_verify_focus_moved_fails_when_post_focus_missing():
    adb = MagicMock()
    adb.dump_ui.side_effect = [FOCUS_PRE_XML, FOCUS_NONE_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_TAB"},
        })
    assert result.passed is False
    assert "after trigger" in result.message


def test_verify_focus_moved_fails_when_trigger_action_fails():
    adb = MagicMock()
    # FOCUS_PRE_XML 무한 공급 — tap_text가 '없는텍스트' 못 찾고 실패
    adb.dump_ui.return_value = FOCUS_PRE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({
        "action": "verify_focus_moved",
        "trigger_action": "tap_text",
        "trigger_step": {"target": "없는텍스트"},
    })
    assert result.passed is False
    assert "Trigger action failed" in result.message
    # post-dump should not run when trigger fails — only pre-dump + tap_text retries
    adb.tap.assert_not_called()


def test_verify_focus_moved_does_not_mutate_trigger_step():
    adb = MagicMock()
    adb.dump_ui.side_effect = [FOCUS_PRE_XML, FOCUS_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    trigger_step = {"key": "KEYCODE_TAB"}
    with patch.object(time, "sleep"):
        runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": trigger_step,
        })
    # caller's trigger_step dict must not be mutated with 'action' key
    assert "action" not in trigger_step


# ─── verify_focus_moved: list 모델 (컨테이너 focused 고정 + selected 자식 이동) ───
# ListView 계열은 컨테이너가 focused="true"로 고정이고 하이라이트 항목이
# selected="true"로 이동한다. 컨테이너 bounds는 pre/post 동일 — selected 자식
# bounds만 이동한다 (reference_alt_focus_widget_model, F0 실측 com.android.mms=list).

LIST_PRE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node class="android.widget.ListView" resource-id="android:id/list"
        focused="true" bounds="[0,0][720,1560]">
    <node text="A" selected="false" bounds="[0,0][720,200]" />
    <node text="B" selected="true" bounds="[0,200][720,400]" />
    <node text="C" selected="false" bounds="[0,400][720,600]" />
  </node>
</hierarchy>"""

LIST_POST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node class="android.widget.ListView" resource-id="android:id/list"
        focused="true" bounds="[0,0][720,1560]">
    <node text="A" selected="false" bounds="[0,0][720,200]" />
    <node text="B" selected="false" bounds="[0,200][720,400]" />
    <node text="C" selected="true" bounds="[0,400][720,600]" />
  </node>
</hierarchy>"""

LIST_NO_SELECTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node class="android.widget.ListView" focused="true" bounds="[0,0][720,1560]">
    <node text="A" selected="false" bounds="[0,0][720,200]" />
    <node text="B" selected="false" bounds="[0,200][720,400]" />
  </node>
</hierarchy>"""


def test_verify_focus_moved_list_passes_when_selection_bounds_differ():
    adb = MagicMock()
    adb.dump_ui.side_effect = [LIST_PRE_XML, LIST_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "focus_model": "list",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_DPAD_DOWN"},
        })
    assert result.passed
    adb.key.assert_called_once_with("KEYCODE_DPAD_DOWN")


def test_verify_focus_moved_list_fails_when_selection_bounds_same():
    adb = MagicMock()
    adb.dump_ui.side_effect = [LIST_PRE_XML, LIST_PRE_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "focus_model": "list",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_DPAD_DOWN"},
        })
    assert not result.passed
    assert "did not move" in result.message


def test_verify_focus_moved_list_fails_when_pre_selection_missing():
    adb = MagicMock()
    adb.dump_ui.side_effect = [LIST_NO_SELECTION_XML, LIST_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "focus_model": "list",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_DPAD_DOWN"},
        })
    assert not result.passed
    assert "before trigger" in result.message


def test_verify_focus_moved_list_fails_when_post_selection_missing():
    adb = MagicMock()
    adb.dump_ui.side_effect = [LIST_PRE_XML, LIST_NO_SELECTION_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "focus_model": "list",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_DPAD_DOWN"},
        })
    assert not result.passed
    assert "after trigger" in result.message


def test_verify_focus_moved_node_model_on_list_fails_because_container_fixed():
    # 설계 근거 회귀: list 화면을 node 모델(기본)로 검증하면 컨테이너 focused가
    # 고정이라 위음성 FAIL — focus_model: list 가 필요한 이유 (batch11 cycle1 5/64).
    adb = MagicMock()
    adb.dump_ui.side_effect = [LIST_PRE_XML, LIST_POST_XML]
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), retry_interval=0)
    with patch.object(time, "sleep"):
        result = runner.run_step({
            "action": "verify_focus_moved",
            "trigger_action": "key",
            "trigger_step": {"key": "KEYCODE_DPAD_DOWN"},
        })
    assert not result.passed
    assert "did not move" in result.message
