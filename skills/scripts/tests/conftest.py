"""Pytest configuration and shared utilities for skills tests."""

from __future__ import annotations

import json
import subprocess
import sys
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


@pytest.fixture(scope="session", autouse=True)
def populate_workflow_registry():
    """Import all skills to populate workflow registry before tests run."""
    failures = import_all_skills()
    # Filter expected failures - excluded skills may not be present
    unexpected = [(mod, exc) for mod, exc in failures if not any(excl in mod for excl in EXCLUDED)]
    if unexpected:
        pytest.fail(f"Unexpected import failures: {unexpected}")


@pytest.fixture(scope="session", autouse=True)
def no_leaks_into_the_projects_the_suite_can_reach():
    """Fail if the suite wrote into a checkout it was only meant to read.

    Session-scoped teardown rather than a test: a test runs at whatever position it is
    collected at, leaving every test after it unguarded. Compared against a snapshot taken
    at session start, so state and plans that already existed -- the feature working -- do
    not red the suite.

    It NEVER skips. A skip raised in a session-scoped autouse fixture skips every test in
    the run and still exits 0, a silent no-op suite that is worse than the inert guard it
    would be reporting; pytest_sessionfinish below is the outcome-level backstop for that.
    Where there is nothing to watch, guard() simply has nothing to compare.

    Two projects are watched rather than one because two mechanisms pick a destination
    independently -- see leak_guard.projects_under_test. Removals are reported alongside
    creations, so a real /plan run whose reaper fires mid-suite in one of them would red
    the run; that is rare enough to prefer over not noticing a leak.
    """
    yield from leak_guard.guard(leak_guard.projects_under_test())


def pytest_sessionfinish(session):
    """Refuse to report green when every collected test was skipped.

    A skip raised in a session-scoped autouse fixture skips every test and exits 0. No
    source-level check survives an alias or an extracted helper; the OUTCOME does -- an
    all-skipped session cannot pass, whatever raised the skips. A deliberate `-k`
    selection made only of skipped tests (the `requires_unprivileged` set run as root,
    say) trips this too: accepted, because it fails loud.
    """
    # session.exitstatus is what _pytest/main.py's wrap_session returns after calling this
    # hook, so assigning it here IS the process exit status -- and an already non-green one
    # (INTERRUPTED, USAGE_ERROR) must never be overwritten. testscollected is set from the
    # item list after pytest_collection_modifyitems, so it is post-deselection.
    if session.exitstatus != 0 or not session.testscollected:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    # Categories are whatever pytest_report_teststatus returned. "" is the one
    # _pytest/runner.py gives a PASSED setup or teardown report, so it accompanies every
    # skip and is not a signal on its own; call-phase outcomes come from
    # _pytest/terminal.py's trylast implementation, and xfail from _pytest/skipping.py.
    seen = {category for category, reports in reporter.stats.items() if reports}
    if "skipped" in seen and seen <= {"skipped", "", "deselected", "warnings"}:
        # write_line calls ensure_newline itself, so this cannot land mid-progress-line.
        # The summary line keeps the colour it was given before this ran; only this line
        # says what happened.
        reporter.write_line(
            "every collected test was skipped -- refusing to report green", red=True
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
