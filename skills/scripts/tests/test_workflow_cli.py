"""render_step's render contract, which guidance authors wrap their prompt lines against."""

from skills.lib.workflow.cli import render_step
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
