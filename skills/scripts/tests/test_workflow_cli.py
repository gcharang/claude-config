"""lib.workflow.cli: render_step's render contract and the arguments mode_main accepts."""

import sys

import pytest

from skills.lib.workflow.cli import mode_main, render_step
from skills.lib.workflow.prompts.step import format_step


def test_each_action_element_renders_on_its_own_line():
    guidance = {
        "title": "T",
        "actions": ["first half of a sentence", "second half", 3, "", "last"],
        "next": "uv run python -m skills.example --step 2",
    }

    rendered = render_step(guidance)

    expected_body = "first half of a sentence\nsecond half\n3\n\nlast"
    assert rendered == format_step(expected_body, guidance["next"], title="T")


@pytest.mark.parametrize("flag", ["--qr-iteration", "--qr-fail"])
def test_mode_main_rejects_qr_state_flags(flag, monkeypatch):
    # Iteration and fail state live in qr-{phase}.json, not on a mode script's command line.
    monkeypatch.setattr(sys, "argv", ["mode.py", "--step", "1", flag, "5"])
    with pytest.raises(SystemExit) as exc:
        mode_main(
            __file__,
            lambda step, module_path, **kw: {"title": "T", "actions": [], "next": ""},
            "test",
        )
    assert exc.value.code == 2
