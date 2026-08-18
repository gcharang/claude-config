"""Pytest configuration and shared utilities for skills tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import leak_guard
import pytest

# Skills excluded from testing (not in git or incompatible). None currently.
EXCLUDED: set[str] = set()

# All skill modules to import for registry population
SKILL_MODULES = [
    "skills.decision_critic.decision_critic",
    "skills.problem_analysis.analyze",
    "skills.codebase_analysis.analyze",
    "skills.deepthink.think",
    "skills.incoherence.incoherence",
    "skills.refactor.refactor",
    "skills.planner.orchestrator.planner",
    "skills.prompt_engineer.optimize",
]


def write_qr(state_dir: Path, phase: str, items: list[dict], *, iteration: int = 1) -> None:
    """Write qr-{phase}.json into state_dir (shared QR-state test helper).

    Single source for the qr-{phase}.json shape so a schema change is one edit;
    the four test modules that wrote this file by hand now bridge to here.
    iteration is keyword-only to keep call sites self-documenting.
    """
    (Path(state_dir) / f"qr-{phase}.json").write_text(
        json.dumps({"phase": phase, "iteration": iteration, "items": items})
    )


def write_verify(
    state_dir: Path, results: list[tuple[str, str, str]], *, iteration: int = 1
) -> None:
    """Write verify.json into state_dir (final-verification test helper).

    results is a list of (check, status, summary) triples. Mirrors what
    cli/verify.py writes, so gate tests can set a precise iteration / fail-set
    without paying the subprocess cost of the recorder.
    """
    (Path(state_dir) / "verify.json").write_text(
        json.dumps(
            {
                "iteration": iteration,
                "results": [{"check": c, "status": s, "summary": m} for c, s, m in results],
            }
        )
    )


def import_all_skills() -> list[tuple[str, Exception]]:
    """Import all skill modules to populate workflow registry.

    Returns list of (module_path, exception) for any import failures.
    """
    import importlib

    failures = []
    for module in SKILL_MODULES:
        try:
            importlib.import_module(module)
        except Exception as e:
            failures.append((module, e))
    return failures


def run_skill_invocation(workflow, inputs: dict[str, Any]) -> tuple[bool, str]:
    """Run skill with inputs via subprocess.

    Returns:
        (True, stdout) on success
        (False, error_message) on failure
    """
    # Build command: python -m module --step N ...
    module_path = workflow._module_path or f"skills.{workflow.name}.{workflow.name}"
    cmd = [sys.executable, "-m", module_path]
    for k, v in inputs.items():
        arg_name = k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                cmd.append(f"--{arg_name}")
        elif v is not None:
            cmd.extend([f"--{arg_name}", str(v)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent,  # skills/scripts/
        )
        if result.returncode == 0:
            return True, result.stdout[:200]
        return False, result.stderr[:200] or f"Exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Timeout (30s)"
    except Exception as e:
        return False, str(e)[:200]


# chmod is a no-op for uid 0, so as root a permission-dependent test either passes without
# exercising the branch it names or fails DID-NOT-RAISE -- meaningless either way (Docker CI
# commonly runs as root).
requires_unprivileged = pytest.mark.skipif(
    os.geteuid() == 0, reason="chmod-based permission tests are meaningless as root"
)


def _git_repo(path: Path) -> Path:
    """A real repo, not a fake .git dir: check-ignore needs one and find_repo_root must find one."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    return path


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """Isolate the temp branch and guarantee the project anchor resolves to nothing.

    A precondition for any test that reaches step 1 without a --state-dir: both anchors
    must be neutralised, not just the env var, because resolve_project_root falls back to
    the cwd and pytest's own cwd is inside this checkout. Without it such a test mints
    .agent-state/_runs/<kind>/ in the real repository and, in a checkout that does not
    already ignore .agent-state, appends the rule to its .gitignore -- which the session
    leak guard then reports, one whole suite run later.

    tempfile.tempdir is patched rather than TMPDIR because gettempdir() caches on first
    call. Pinning tempfile.mkdtemp alone is not enough either: the session parent is
    mkdir'd directly, so that would still leave <real tmp>/cc-<session> behind.
    """
    fallback = tmp_path / "tmp"
    fallback.mkdir()
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(fallback))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(nowhere)
    return fallback


@pytest.fixture(scope="session", autouse=True)
def populate_workflow_registry():
    """Import all skills to populate workflow registry before tests run."""
    failures = import_all_skills()
    # Filter expected failures - excluded skills may not be present
    unexpected = [(mod, exc) for mod, exc in failures if not any(excl in mod for excl in EXCLUDED)]
    if unexpected:
        pytest.fail(f"Unexpected import failures: {unexpected}")


_LEAK_BASELINE = pytest.StashKey[dict[Path, leak_guard.Snapshot]]()


def pytest_sessionstart(session):
    """Record what the projects the suite can reach looked like before anything ran.

    The baseline has to exist before collection, so this conftest imports the planner
    package eagerly -- a break in that import now fails collection outright (exit 4)
    rather than one fixture.
    """
    session.config.stash[_LEAK_BASELINE] = leak_guard.baseline(leak_guard.projects_under_test())


@pytest.fixture(scope="session", autouse=True)
def no_leaks_into_the_projects_the_suite_can_reach(request):
    """Fail if the suite wrote into a checkout it was only meant to read.

    Session-scoped teardown rather than a test: a test runs at whatever position it is
    collected at, leaving every test after it unguarded. The comparison stays here so a
    leak is reported as an ERROR after the last test, but the baseline is taken in
    pytest_sessionstart, which runs before collection: this fixture's own setup does not
    run until the first test does, by which time every test module has been imported and
    a write made at import time would already be part of the baseline.

    It NEVER skips. A skip raised in a session-scoped autouse fixture skips every test in
    the run and still exits 0, a silent no-op suite that is worse than the inert guard it
    would be reporting; pytest_sessionfinish below is the outcome-level backstop for that.
    Where there is nothing to watch, check() simply has nothing to compare.

    Two projects are watched rather than one because two mechanisms pick a destination
    independently -- see leak_guard.projects_under_test. Removals are reported alongside
    creations, so a real /plan run whose reaper fires mid-suite in one of them would red
    the run; that is rare enough to prefer over not noticing a leak.
    """
    yield
    leak_guard.check(request.config.stash[_LEAK_BASELINE])


def pytest_sessionfinish(session):
    """Outcome-level backstop for a skip that reached every test.

    A hook has to live in a conftest to be discovered; what it depends on inside pytest,
    and why each of its guards is there, is stated once in leak_guard.
    """
    leak_guard.refuse_green_when_all_skipped(session)
