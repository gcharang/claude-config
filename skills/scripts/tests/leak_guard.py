"""Fail the suite when it writes into a real checkout instead of a tmp_path.

A test that pins `tempfile.mkdtemp` but not the project anchor reaches
`resolve_state_dir`'s project-local branch against a real repository: it mints
`.agent-state/_runs/<kind>/<run>` there, and appends the ignore rule to a `.gitignore`
the user authored. A test that also lets a plan reach the terminal gate archives into
`docs/plans/`. Where a checkout's `.gitignore` is `*`, none of that appears in
`git status`, so this comparison is the only thing that can see it.

A module of its own rather than more helpers in `conftest.py`: that file is the
suite-wide utility for every test module, and this is one skill's storage-layout check.
It also lets `test_leak_guard.py` drive `guard()` over a scratch directory instead of
patching a private inside a hook module.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path


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
    from skills.planner.shared import resources

    anchors = (
        resources.resolve_project_root()[0],
        resources.find_repo_root(Path(resources.__file__)),
    )
    return tuple(dict.fromkeys(anchor for anchor in anchors if anchor is not None))


@dataclass(frozen=True)
class Snapshot:
    """What one project looked like at one instant, in the three dimensions we can dirty.

    `plans` and `gitignore` are None when the directory or file is absent, which is a
    different state from present-and-empty: a leaked empty `docs/plans/` is invisible to
    any comparison that conflates them.
    """

    agent_state: frozenset[str]
    plans: frozenset[str] | None
    gitignore: bytes | None


def snapshot(project: Path) -> Snapshot:
    """Read `project`'s three dimensions now.

    `agent_state` covers `.agent-state/` and `_runs/` themselves plus every directory
    beneath `_runs/` -- the whole footprint production can create, including the empty
    ancestors a failed take-back leaves. Deliberately NOT the rest of `.agent-state/`:
    `.agent-state/<task-slug>/` belongs to the session task-tracking convention, and a
    new one appearing during a run is that convention working, not this feature leaking.
    """
    from skills.planner.orchestrator.planner import DOCS_PLANS_RELATIVE
    from skills.planner.shared.resources import AGENT_STATE_DIRNAME, RUNS_NAMESPACE

    state = project / AGENT_STATE_DIRNAME
    runs = state / RUNS_NAMESPACE
    watched = [d for d in (state, runs) if d.is_dir()]
    watched += [d for d in runs.rglob("*") if d.is_dir()]

    plans_dir = project / DOCS_PLANS_RELATIVE
    gitignore = project / ".gitignore"
    return Snapshot(
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
    """
    from skills.planner.orchestrator.planner import DOCS_PLANS_RELATIVE

    found = [f"created {path}" for path in sorted(after.agent_state - before.agent_state)]
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


def guard(projects: Iterable[Path]) -> Iterator[None]:
    """Snapshot every project, yield once, then fail on any difference.

    A generator so the caller can be a session-scoped fixture: `yield from guard(...)`
    puts the comparison in teardown, after the last test. `projects` is materialised
    first, because it is walked twice.
    """
    watched = tuple(projects)
    before = {project: snapshot(project) for project in watched}
    yield
    found = [
        f"{project}: {line}"
        for project in watched
        for line in violations(before[project], snapshot(project))
    ]
    assert not found, "the test suite wrote into a project it must leave alone:\n  " + "\n  ".join(
        found
    )
