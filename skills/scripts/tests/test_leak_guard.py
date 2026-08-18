"""The suite's own leak guard: that it fires, on what, and that it cannot go quiet.

Nothing else notices this guard going inert -- a healthy run has no failing case, so an
assertion that stops comparing looks exactly like a clean session. Every case below drives
`leak_guard.guard()` over a scratch directory, so proving the guard works cannot itself
leak into a real checkout.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import leak_guard
import pytest

AGENT_STATE = ".agent-state"
RUNS = f"{AGENT_STATE}/_runs"
PLANNER_RUNS = f"{RUNS}/planner"
PLANS = "docs/plans"


@pytest.fixture
def project(tmp_path):
    """Stands in for a checkout: the guard reads paths and bytes, never git."""
    root = tmp_path / "project"
    root.mkdir()
    return root


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# Each case is (what the project already held, what the suite did to it, the line the
# guard must produce). Every branch in violations() needs one: the guard reports both
# directions, and a deleted branch is silent rather than wrong.
LEAKS = [
    pytest.param(
        lambda p: (p / PLANNER_RUNS).mkdir(parents=True),
        lambda p: (p / PLANNER_RUNS / "20260819-000000-ab").mkdir(),
        f"created {PLANNER_RUNS}/20260819-000000-ab",
        id="run-dir-minted",
    ),
    pytest.param(
        lambda p: None,
        lambda p: (p / AGENT_STATE).mkdir(),
        f"created {AGENT_STATE}",
        id="bare-agent-state",
    ),
    pytest.param(
        # The take-back-failure shape in a checkout that already keeps task-tracking state
        # under .agent-state/ -- only the _runs/ level below it is new.
        lambda p: (p / AGENT_STATE / "some-task").mkdir(parents=True),
        lambda p: (p / RUNS).mkdir(),
        f"created {RUNS}",
        id="runs-left-behind",
    ),
    pytest.param(
        lambda p: (p / PLANNER_RUNS / "20200101-000000-old").mkdir(parents=True),
        lambda p: (p / PLANNER_RUNS / "20200101-000000-old").rmdir(),
        f"removed {PLANNER_RUNS}/20200101-000000-old",
        id="run-dir-reaped",
    ),
    pytest.param(
        lambda p: None,
        lambda p: (p / PLANS).mkdir(parents=True),
        f"created {PLANS}/",
        id="plans-dir-created-empty",
    ),
    pytest.param(
        lambda p: (p / PLANS).mkdir(parents=True),
        lambda p: (p / PLANS).rmdir(),
        f"removed {PLANS}/",
        id="plans-dir-removed",
    ),
    pytest.param(
        lambda p: (p / PLANS).mkdir(parents=True),
        lambda p: _write(p / PLANS / "2026-08-19-thing.md", "# plan\n"),
        f"archived 2026-08-19-thing.md into {PLANS}/",
        id="plan-archived",
    ),
    pytest.param(
        lambda p: _write(p / PLANS / "2026-08-19-thing.md", "# plan\n"),
        lambda p: (p / PLANS / "2026-08-19-thing.md").unlink(),
        f"removed 2026-08-19-thing.md from {PLANS}/",
        id="plan-removed",
    ),
    pytest.param(
        lambda p: _write(p / ".gitignore", "node_modules/\n"),
        lambda p: _write(p / ".gitignore", f"node_modules/\n/{AGENT_STATE}/\n"),
        "modified .gitignore",
        id="gitignore-appended",
    ),
    pytest.param(
        lambda p: None,
        lambda p: _write(p / ".gitignore", f"/{AGENT_STATE}/\n"),
        "created .gitignore",
        id="gitignore-created",
    ),
    pytest.param(
        lambda p: _write(p / ".gitignore", "node_modules/\n"),
        lambda p: (p / ".gitignore").unlink(),
        "deleted .gitignore",
        id="gitignore-deleted",
    ),
]


@pytest.mark.parametrize(("prepare", "leak", "expected"), LEAKS)
def test_the_guard_reports_each_way_a_project_can_be_dirtied(project, prepare, leak, expected):
    """One case per line violations() can produce, asserted on the line itself.

    Asserting only "it failed" would let any branch be replaced by any other and still
    pass, and the message is what tells whoever hits this which test to go and look at.
    """
    prepare(project)
    running = leak_guard.guard([project])
    next(running)

    leak(project)

    with pytest.raises(AssertionError) as caught:
        next(running)
    assert expected in str(caught.value)


def test_a_project_the_suite_only_read_reports_nothing(project):
    """The guard runs on every session, so a false positive would red every run."""
    (project / PLANNER_RUNS / "20200101-000000-old").mkdir(parents=True)
    _write(project / PLANS / "2026-01-01-existing.md", "# plan\n")
    _write(project / ".gitignore", "node_modules/\n")

    running = leak_guard.guard([project])
    next(running)

    with pytest.raises(StopIteration):
        next(running)


def test_a_task_tracking_directory_created_mid_run_is_not_a_leak(project):
    """`.agent-state/<task-slug>/` belongs to the session task-tracking convention.

    A new one appearing while the suite runs is that convention working. Watching it would
    red the suite for someone else's file and blame the tests.
    """
    (project / AGENT_STATE).mkdir()

    running = leak_guard.guard([project])
    next(running)

    task = project / AGENT_STATE / "state-dir-durability"
    task.mkdir()
    _write(task / "tasks.md", "- [ ] work\n")

    with pytest.raises(StopIteration):
        next(running)


def test_every_watched_project_is_compared_and_named(tmp_path):
    """Two anchors are watched, so a leak into the second must not hide behind the first.

    The message names the project because the two are ordinarily different checkouts, and
    "a run dir appeared" is not actionable without saying where.
    """
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    running = leak_guard.guard([first, second])
    next(running)

    (second / AGENT_STATE).mkdir()

    with pytest.raises(AssertionError) as caught:
        next(running)
    assert f"{second}: created {AGENT_STATE}" in str(caught.value)
    assert str(first) not in str(caught.value)


def test_no_project_to_watch_completes_rather_than_skipping():
    """The guard's caller is a session-scoped autouse fixture: a skip there skips the
    whole run and exits 0, so "nothing to watch" must be an ordinary completion.

    Trapped explicitly. A Skipped raised inside a test SKIPS that test rather than failing
    it, so an unguarded call here would report as a quiet `s` in the summary -- the exact
    outcome this pins against.
    """
    running = leak_guard.guard([])
    try:
        # Both calls inside the trap: guard() is a generator, so its body -- setup as well
        # as teardown -- runs at a next(), and a skip raised from either one would
        # otherwise escape past this test rather than into it.
        next(running)
        with pytest.raises(StopIteration):
            next(running)
    except pytest.skip.Exception as skipped:
        pytest.fail(f"the guard skipped instead of completing: {skipped}")


def _inner_session(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Run `body` as its own pytest session with tests/conftest.py loaded as a plugin.

    A real subprocess, because what these pin is the process exit status and the hook only
    runs once a session ends. `-p conftest` loads tests/conftest.py by module name, which
    resolves because tests/ has no __init__.py and is on the path. `--rootdir` and the cwd
    keep the inner run out of this project's pytest config; that cwd is not a repo and the
    run mints nothing, so the inner leak guard has nothing to report either.
    """
    inner = tmp_path / "test_inner_session.py"
    _write(inner, body)

    tests_dir = Path(__file__).parent
    env = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
    env["PYTHONPATH"] = os.pathsep.join([str(tests_dir), str(tests_dir.parent)])

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "conftest",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(tmp_path / "basetemp"),
            "--rootdir",
            str(tmp_path),
            str(inner),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_an_all_skipped_session_cannot_report_green(tmp_path):
    """The outcome-level backstop for a skip that reaches every test.

    A skip raised in the session-scoped autouse guard skips the whole run and exits 0. No
    check on the fixture's source survives an alias; this one reads the result instead.
    """
    result = _inner_session(
        tmp_path, "import pytest\n\n\ndef test_nothing():\n    pytest.skip('no reason to run')\n"
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "refusing to report green" in output, output
    # Without this the test would also pass on a session that collected nothing or errored
    # out, neither of which is the state the hook exists to catch.
    assert "1 skipped" in result.stdout, output


def test_a_session_that_also_passed_something_stays_green(tmp_path):
    """One ordinary skip alongside a pass is not an all-skipped session.

    The hook runs on every session in this repo, so a condition that fires on the mere
    presence of a skip would red every run with a `requires_unprivileged` test in it --
    a louder failure than the silence it was written to catch.
    """
    result = _inner_session(
        tmp_path,
        "import pytest\n\n\ndef test_skipped():\n    pytest.skip('not here')\n\n\n"
        "def test_passed():\n    assert True\n",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "refusing to report green" not in output, output
    assert "1 passed" in result.stdout and "1 skipped" in result.stdout, output
