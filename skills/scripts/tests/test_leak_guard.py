"""The suite's own leak guard: that it fires, on what, and that it cannot go quiet.

Nothing else notices this guard going inert -- a healthy run has no failing case, so an
assertion that stops comparing looks exactly like a clean session.

Two kinds of case. The direct ones drive `leak_guard.guard()` over scratch directories, so
proving the guard works cannot itself leak into a real checkout. The subprocess ones run a
whole inner pytest session, because the wiring they pin -- the autouse fixture, the
session-start baseline, the exit status -- only exists across a session boundary; that
session's second anchor is this checkout, and it mints nothing there.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import leak_guard
import pytest
from conftest import _git_repo, requires_unprivileged

from skills.planner.shared import resources

# Spelled out rather than imported from production. A rename of AGENT_STATE_DIRNAME,
# RUNS_NAMESPACE or DOCS_PLANS_RELATIVE must red this module -- these are the paths the
# guard promises to watch, and a test that follows the rename silently stops saying so.
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


def _skill_checkout() -> Path | None:
    """The second anchor, computed the way leak_guard computes it -- never hardcoded."""
    return resources.find_repo_root(Path(resources.__file__))


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
        lambda p: (p / AGENT_STATE).mkdir(),
        lambda p: (p / AGENT_STATE).rmdir(),
        f"removed {AGENT_STATE}",
        id="agent-state-removed",
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
        # The same shape under an EMPTY .agent-state/: the directory stops being bare,
        # which is not itself a violation, so the _runs/ level has to carry the report.
        lambda p: (p / AGENT_STATE).mkdir(),
        lambda p: (p / RUNS).mkdir(),
        f"created {RUNS}",
        id="runs-under-a-bare-agent-state",
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


@pytest.mark.parametrize("state_dir_exists", [True, False], ids=["existing", "first-one"])
def test_a_task_tracking_directory_created_mid_run_is_not_a_leak(project, state_dir_exists):
    """`.agent-state/<task-slug>/` belongs to the session task-tracking convention.

    A new one appearing while the suite runs is that convention working. Watching it would
    red the suite for someone else's file and blame the tests.

    The second case is the one a plain "did .agent-state appear" test gets wrong: when the
    directory does not exist at session start, the convention's FIRST task directory
    brings the parent into being along with it. What this feature leaves behind is a BARE
    `.agent-state/`, which the case above pins.
    """
    if state_dir_exists:
        (project / AGENT_STATE).mkdir()

    running = leak_guard.guard([project])
    next(running)

    task = project / AGENT_STATE / "state-dir-durability"
    task.mkdir(parents=True)
    _write(task / "tasks.md", "- [ ] work\n")

    with pytest.raises(StopIteration):
        next(running)


@requires_unprivileged
def test_a_directory_under_runs_it_cannot_read_fails_loudly(project):
    """The listing must not narrow itself where it is least able to say so.

    `rglob` and a bare `os.walk` both SWALLOW the PermissionError and return what they
    could reach, so every run dir below an unreadable directory drops out of both
    snapshots and compares equal. Raising fails the session loudly -- at session start for
    the real fixture's baseline, in teardown for the comparison -- which is the honest
    report: this guard could not see.
    """
    blocked = project / PLANNER_RUNS
    blocked.mkdir(parents=True)
    (blocked / "20260819-000000-ab").mkdir()
    blocked.chmod(0o000)
    try:
        with pytest.raises(PermissionError):
            leak_guard.snapshot(project)
    finally:
        blocked.chmod(0o700)


def test_the_comparison_does_not_rely_on_an_assert_statement(tmp_path):
    """`python -O` strips `assert`, and this module is not one pytest rewrites.

    A bare `assert not found` therefore vanishes under that flag and the guard reports
    nothing at all -- inert in a configuration nobody would think to re-check. Driven in a
    subprocess because the flag is an interpreter-level decision, taken before import.
    """
    project = tmp_path / "project"
    project.mkdir()
    tests_dir = Path(__file__).parent
    program = (
        "import leak_guard\n"
        "from pathlib import Path\n"
        f"project = Path({str(project)!r})\n"
        "before = leak_guard.baseline([project])\n"
        f"(project / {AGENT_STATE!r}).mkdir()\n"
        "try:\n"
        "    leak_guard.check(before)\n"
        "except AssertionError as reported:\n"
        "    print('REPORTED', reported)\n"
    )

    result = subprocess.run(
        [sys.executable, "-O", "-c", program],
        cwd=tmp_path,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(tests_dir), str(tests_dir.parent)]),
        },
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + result.stderr
    assert "REPORTED the test suite wrote into a project it must leave alone" in output, output
    assert f"created {AGENT_STATE}" in output, output


def test_every_watched_project_is_compared_and_named(tmp_path):
    """A leak into the second of two watched projects must not hide behind the first.

    The message names the project because the two anchors ordinarily dedupe to one
    checkout and differ only when the suite runs from outside it -- so when there ARE two,
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


def test_the_env_anchor_and_the_skill_checkout_are_both_watched(tmp_path, monkeypatch):
    """The two anchors, in anchor order, when they name different repositories.

    $CLAUDE_PROJECT_DIR is where a minted run dir would land; the skill checkout is where
    a plan follows a marker regardless of the live anchor. Watching one is watching half.
    """
    anchored = _git_repo(tmp_path / "anchored")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(anchored))
    monkeypatch.chdir(elsewhere)

    assert leak_guard.projects_under_test() == (anchored.resolve(), _skill_checkout())


def test_an_unresolvable_live_anchor_leaves_the_skill_checkout_watched(tmp_path, monkeypatch):
    """One anchor answering None must not take the other one down with it.

    A None is dropped, not carried: `snapshot(None)` would be a TypeError at session
    start, and a guard that errors in setup is a guard nobody keeps.
    """
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(outside)

    assert leak_guard.projects_under_test() == (_skill_checkout(),)


def test_one_checkout_named_twice_is_watched_once(monkeypatch):
    """The ordinary case: the suite runs inside the checkout it is testing.

    Both anchors then answer the same path, and snapshotting it twice would report every
    leak twice.
    """
    checkout = _skill_checkout()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(checkout))

    assert leak_guard.projects_under_test() == (checkout,)


def test_with_no_anchor_at_all_there_is_nothing_to_watch(tmp_path, monkeypatch):
    """No repository either way -- the suite run from an unpacked sdist, say.

    An empty tuple, not a crash and not a skip: the fixture still has to complete, and
    check() over no projects has nothing to compare.
    """
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(outside)
    monkeypatch.setattr(resources, "find_repo_root", lambda start: None)

    assert leak_guard.projects_under_test() == ()


def _inner_session(
    tmp_path: Path,
    body: str,
    *,
    extra_args: Sequence[str] = ("-q",),
    env_overrides: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `body` as its own pytest session with tests/conftest.py loaded as a plugin.

    A real subprocess, because what these pin is the process exit status and the hooks
    only run when a session starts and ends. `-p conftest` loads tests/conftest.py by
    module name, which resolves because tests/ has no __init__.py and PYTHONPATH carries
    both it and skills/scripts. `--rootdir` and the cwd keep the inner run out of this
    project's pytest config.

    The PYTEST_* variables are scrubbed alongside CLAUDE_PROJECT_DIR, which each case sets
    for itself: a `PYTEST_ADDOPTS=--co` in the caller's environment would otherwise turn
    every one of these into a collect-only run that passes for the wrong reason.

    `extra_args` carries `-q` by default because the assertions read the summary line. A
    case that unregisters the terminal plugin has to drop it -- that plugin is what
    registers the flag, and the inner run would exit 4 on an unrecognised argument.
    """
    inner = tmp_path / "test_inner_session.py"
    _write(inner, body)

    tests_dir = Path(__file__).parent
    scrubbed = {
        "CLAUDE_PROJECT_DIR",
        "PYTEST_ADDOPTS",
        "PYTEST_CURRENT_TEST",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "PYTEST_PLUGINS",
    }
    env = {key: value for key, value in os.environ.items() if key not in scrubbed}
    env["PYTHONPATH"] = os.pathsep.join([str(tests_dir), str(tests_dir.parent)])
    env.update(env_overrides or {})

    try:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *extra_args,
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
            timeout=120,
        )
    except subprocess.TimeoutExpired as expired:
        pytest.fail(f"the inner pytest session did not finish within {expired.timeout}s")


@pytest.mark.parametrize("when", ["in-the-test", "at-import"])
def test_a_run_dir_minted_in_a_watched_project_fails_that_session(tmp_path, when):
    """The wiring itself: autouse fixture, baseline at session start, compared in teardown.

    Every direct case above drives leak_guard's own functions, so none of them notices the
    fixture losing `autouse=True` or the stash key never being read -- the suite stays
    green and stops watching anything. This one lets a real session mint a real run dir in
    a project it was pointed at, and reads the exit status.

    The at-import case is what the session-start baseline buys: collection imports every
    test module before the first fixture setup runs, so a baseline taken in the fixture
    would already contain that directory and compare equal to itself.
    """
    watched = _git_repo(tmp_path / "watched")
    leaked = f"{PLANNER_RUNS}/20260819-000000-leak"
    mint = f"(Path(os.environ['CLAUDE_PROJECT_DIR']) / {leaked!r}).mkdir(parents=True)\n"
    body = "import os\nfrom pathlib import Path\n\n"
    if when == "at-import":
        body += f"{mint}\n\ndef test_imported_the_module():\n    assert True\n"
    else:
        body += f"\ndef test_mints_a_run_dir():\n    {mint}"
    result = _inner_session(tmp_path, body, env_overrides={"CLAUDE_PROJECT_DIR": str(watched)})

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "wrote into a project it must leave alone" in output, output
    assert leaked in output, output
    # The inner test PASSES; the session fails in teardown. Without this the assertions
    # above would also hold for a run that errored before the test ever executed.
    assert "1 passed" in result.stdout, output


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


def test_an_all_skipped_session_with_a_warning_still_cannot_report_green(tmp_path):
    """A warning is not an outcome, so it must not lift a session out of all-skipped.

    `"warnings"` is a stats category like any other, and an unknown mark or a
    DeprecationWarning out of a dependency is enough to populate it -- so without it in
    the allowed set the hook goes quiet for a suite that merely warns while skipping.
    """
    result = _inner_session(
        tmp_path,
        # An unknown mark, because the warning has to come from the inner session itself:
        # `-W` and a filter in the outer config are the caller's, not what is under test.
        "import pytest\n\n\n@pytest.mark.bogus\ndef test_nothing():\n"
        "    pytest.skip('no reason to run')\n",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "refusing to report green" in output, output
    assert "1 skipped" in result.stdout and "1 warning" in result.stdout, output


def test_a_deselection_does_not_hide_an_all_skipped_session(tmp_path):
    """`-k` leaves a `"deselected"` stat behind, and everything that RAN was skipped.

    This is what the `-k`-over-the-unprivileged-set case looks like in the stats, and it
    is the selection most likely to produce an all-skipped run by hand: without
    `"deselected"` in the allowed set the hook goes quiet for exactly that.
    """
    result = _inner_session(
        tmp_path,
        "import pytest\n\n\ndef test_skipped():\n    pytest.skip('not here')\n\n\n"
        "def test_passed():\n    assert True\n",
        extra_args=("-q", "-k", "test_skipped"),
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "refusing to report green" in output, output
    assert "1 skipped" in result.stdout and "1 deselected" in result.stdout, output


def test_a_session_that_also_passed_something_stays_green(tmp_path):
    """One ordinary skip alongside a pass is not an all-skipped session.

    The hook runs on every session in this repo, so a condition that fires on the mere
    presence of a skip would red every run with a `requires_unprivileged` test in it, run
    as root -- a louder failure than the silence it was written to catch.
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


def test_a_collect_only_session_stays_green(tmp_path):
    """`--co` collects tests, runs none of them, reports nothing and exits 0.

    An empty stats mapping is a subset of every allowed set, so it is the `"skipped" in
    seen` test alone that keeps the backstop off a collect-only run -- and this repo's own
    documented commands include one.
    """
    result = _inner_session(
        tmp_path,
        "def test_collected_but_not_run():\n    assert True\n",
        extra_args=("-q", "--co"),
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "refusing to report green" not in output, output
    assert "1 test collected" in result.stdout, output


def test_a_session_with_no_terminal_reporter_survives_the_hook(tmp_path):
    """`-p no:terminal` unregisters the reporter, and the hook reads its stats.

    Without the None guard this ends in an AttributeError raised from
    pytest_sessionfinish, which pytest reports as an INTERNALERROR -- a suite-wide crash
    caused by the guard rather than by anything it guards.
    """
    result = _inner_session(
        tmp_path,
        "import pytest\n\n\ndef test_skipped():\n    pytest.skip('not here')\n",
        extra_args=("-p", "no:terminal"),
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "INTERNALERROR" not in output, output
    assert "Traceback" not in output, output
