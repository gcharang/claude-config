"""Fail the suite when it writes into a real checkout instead of a tmp_path.

A test that pins `tempfile.mkdtemp` but not the project anchor reaches
`resolve_state_dir`'s project-local branch against a real repository: it mints
`.agent-state/_runs/<kind>/<run>` there, and -- where that checkout does not already
ignore `.agent-state` -- appends the ignore rule to a `.gitignore` the user authored. A
test that also lets a plan reach the terminal gate archives into `docs/plans/`. Where a
checkout's `.gitignore` is `*`, none of that appears in `git status`, so this comparison
is the only thing that can see it.

The comparison's caller is a session-scoped autouse fixture, where a skip would no-op
the whole suite at exit 0 rather than report anything. This module therefore also owns
the outcome-level backstop for that shape, `refuse_green_when_all_skipped`, which
refuses green for a session in which every collected test was skipped.

A module of its own rather than more helpers in `conftest.py`: fixtures and hooks must
live in a conftest to be discovered, but the mechanism behind them does not, and that
file is the suite-wide utility for every test module while this is one skill's
storage-layout check. It also lets `test_leak_guard.py` drive `guard()` over a scratch
directory instead of patching a private inside a hook module.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from skills.planner.orchestrator.planner import DOCS_PLANS_RELATIVE
from skills.planner.shared import resources
from skills.planner.shared.resources import AGENT_STATE_DIRNAME, RUNS_NAMESPACE


def projects_under_test() -> tuple[Path, ...]:
    """The checkouts a leaking test could reach, deduplicated and in anchor order.

    Two anchors, because two mechanisms choose a destination independently:

    - `resolve_project_root()` is where `resolve_state_dir` would mint, where the ignore
      rule would be appended, and what a marker written during a test records.
    - `find_repo_root(Path(resources.__file__))` is whichever checkout holds the skill
      source. `_save_plan_to_docs` follows the RECORDED marker rather than the live root,
      so a test that points a marker at this checkout archives here whatever the live
      anchor happens to be.

    Called once, at session start. With no repo to watch there is nothing to compare.
    """
    anchors = (
        resources.resolve_project_root()[0],
        resources.find_repo_root(Path(resources.__file__)),
    )
    return tuple(dict.fromkeys(anchor for anchor in anchors if anchor is not None))


@dataclass(frozen=True)
class Snapshot:
    """What one project looked like at one instant, in the four dimensions we can dirty.

    `bare_state` is a tri-state rather than a member of `agent_state`: absent (None),
    present and empty (True), present with something in it (False). Only the first
    transition to an EMPTY `.agent-state/` is this feature leaking -- see violations.

    `plans` and `gitignore` are None when the directory or file is absent, which is a
    different state from present-and-empty: a leaked empty `docs/plans/` is invisible to
    any comparison that conflates them.
    """

    bare_state: bool | None
    agent_state: frozenset[str]
    plans: frozenset[str] | None
    gitignore: bytes | None


def _reraise(error: OSError) -> None:
    """os.walk's onerror: turn a directory it could not read into the caller's problem."""
    raise error


def snapshot(project: Path) -> Snapshot:
    """Read `project`'s four dimensions now: names and directories, plus `.gitignore`'s bytes.

    `agent_state` covers `_runs/` itself and every directory beneath it -- every directory
    production can create below that level, including the empty ancestors a failed
    take-back leaves. `.agent-state/` itself is `bare_state`, and the rest of it is watched
    not at all: `.agent-state/<task-slug>/` belongs to the session task-tracking convention,
    and a new one appearing during a run is that convention working, not this feature
    leaking. What `bare_state` costs is bounded: a test that empties the user's
    `.agent-state/<task-slug>/` is not seen at this level, while anything under `_runs/`
    still is.

    What is deliberately NOT compared: the content of the files inside a run dir or an
    archived plan, nor a file written into a run dir that already existed. Production never
    overwrites in `docs/plans/` (a collision takes a `-2` suffix), and `_runs/` does not
    pre-exist in a checkout the suite is only reading, so every write this guard exists to
    catch shows up as a new name.

    os.walk with a re-raising onerror: `rglob` and a bare `os.walk` both SWALLOW a
    PermissionError, so one unreadable directory would silently hide everything below it --
    the guard going quiet in exactly the case it is for. Failing the session loudly is the
    point.
    """
    state = project / AGENT_STATE_DIRNAME
    runs = state / RUNS_NAMESPACE

    watched: list[Path] = []
    if runs.is_dir():
        watched.append(runs)
        for parent, directories, _ in os.walk(runs, onerror=_reraise):
            watched += [Path(parent) / name for name in directories]

    plans_dir = project / DOCS_PLANS_RELATIVE
    gitignore = project / ".gitignore"
    return Snapshot(
        bare_state=not any(state.iterdir()) if state.is_dir() else None,
        agent_state=frozenset(str(d.relative_to(project)) for d in watched),
        plans=frozenset(p.name for p in plans_dir.iterdir()) if plans_dir.is_dir() else None,
        gitignore=gitignore.read_bytes() if gitignore.is_file() else None,
    )


def violations(before: Snapshot, after: Snapshot) -> list[str]:
    """One line per difference, in both directions, worded for what actually happened.

    Removals are reported as removals rather than folded into a one-way set difference. A
    test that reaped or deleted real state has dirtied the project just as surely as one
    that created some; comparing in one direction only was how the previous guard avoided
    reporting a removal under a message that named a creation.

    An `.agent-state/` that appears EMPTY is this feature: a take-back that could not
    finish leaves exactly that. One that appears with something already in it is the
    task-tracking convention creating its first `.agent-state/<task-slug>/`, which is not
    the suite's doing and must not red it.
    """
    found = []
    if before.bare_state is None and after.bare_state is True:
        found.append(f"created {AGENT_STATE_DIRNAME}")
    elif before.bare_state is not None and after.bare_state is None:
        found.append(f"removed {AGENT_STATE_DIRNAME}")

    found += [f"created {path}" for path in sorted(after.agent_state - before.agent_state)]
    found += [f"removed {path}" for path in sorted(before.agent_state - after.agent_state)]

    if before.plans != after.plans:
        if before.plans is None:
            found.append(f"created {DOCS_PLANS_RELATIVE}/")
        elif after.plans is None:
            found.append(f"removed {DOCS_PLANS_RELATIVE}/")
        was = before.plans if before.plans is not None else frozenset()
        now = after.plans if after.plans is not None else frozenset()
        found += [f"archived {name} into {DOCS_PLANS_RELATIVE}/" for name in sorted(now - was)]
        found += [f"removed {name} from {DOCS_PLANS_RELATIVE}/" for name in sorted(was - now)]

    if before.gitignore != after.gitignore:
        if before.gitignore is None:
            found.append("created .gitignore")
        elif after.gitignore is None:
            found.append("deleted .gitignore")
        else:
            found.append("modified .gitignore")
    return found


def baseline(projects: Iterable[Path]) -> dict[Path, Snapshot]:
    """Snapshot every project, keyed by project, for a later `check`.

    Split from the comparison so the caller can take it at session start, before
    collection: a fixture's setup first runs when the first test does, by which point
    every test module has been imported and a write made at import time is already inside
    `before`.
    """
    return {project: snapshot(project) for project in projects}


def check(before: dict[Path, Snapshot]) -> None:
    """Re-read every project in `before` and raise on any difference.

    AssertionError raised rather than asserted: `python -O` strips an `assert` statement
    outright, and this module is not one pytest rewrites (rewriting covers test modules
    and conftest, not a plain import), so the statement form buys nothing here either.
    """
    found = [
        f"{project}: {line}"
        for project, was in before.items()
        for line in violations(was, snapshot(project))
    ]
    if found:
        raise AssertionError(
            "the test suite wrote into a project it must leave alone:\n  " + "\n  ".join(found)
        )


def guard(projects: Iterable[Path]) -> Iterator[None]:
    """Baseline, yield once, then check -- the two halves as one generator.

    What the sensitivity tests drive, so a case reads as "snapshot, leak, compare" in one
    object. The session fixture uses the halves directly, because its baseline is taken
    earlier than its own setup.
    """
    before = baseline(projects)
    yield
    check(before)


def refuse_green_when_all_skipped(session: pytest.Session) -> None:
    """Refuse to report green when every collected test was skipped.

    A skip raised in a session-scoped autouse fixture skips every test and exits 0. No
    source-level check survives an alias or an extracted helper; the OUTCOME does -- an
    all-skipped session cannot pass, whatever raised the skips. A deliberate `-k`
    selection made only of skipped tests (the `requires_unprivileged` set run as root,
    say) trips this too: accepted, because it fails loud.

    `session.exitstatus` is what `_pytest/main.py`'s wrap_session returns after this hook
    runs, so assigning it here IS the process exit status. An already non-green one is
    never overwritten: nothing readable here separates INTERRUPTED from a run that simply
    failed, and re-labelling an interrupt as TESTS_FAILED is the cost of guessing. No test
    pins the `exitstatus != 0` guard -- an all-skipped session that is also interrupted
    cannot be produced from inside the suite; it is kept on this argument, not on coverage.

    The `reporter is None` return and the `"skipped"` clause are load-bearing, not
    defensive. `--co` collects tests, produces no reports at all and exits 0, so without
    the `"skipped"` test every collect-only run would be failed by this. `-p no:terminal`
    unregisters the reporter, so `get_plugin` answers None and there are no stats to read
    at all.

    Two limits, neither of which reaches what this is for. Under `-p no:terminal` it
    cannot fire -- but that flag is a deliberate act, not something a skipping fixture
    produces. A session that also xfailed something is not all-skipped and stays green --
    but when the guard fixture skips, an xfail-marked test reports `skipped` like
    everything else, because the mark is consulted only for a report that is not already
    skipped.

    Categories are whatever `pytest_report_teststatus` returned. `""` is the one
    `_pytest/runner.py` gives a PASSED setup or teardown report, so it accompanies every
    skip and is not a signal on its own; call-phase outcomes come from
    `_pytest/terminal.py`'s trylast implementation, and xfail from `_pytest/skipping.py`.
    """
    if session.exitstatus != 0:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    seen = {category for category, reports in reporter.stats.items() if reports}
    if "skipped" in seen and seen <= {"skipped", "", "deselected", "warnings"}:
        # write_line calls ensure_newline itself, so this cannot land mid-progress-line.
        # The summary line keeps the colour it was given before this ran; only this line
        # says what happened.
        reporter.write_line(
            "every collected test was skipped -- refusing to report green", red=True
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
