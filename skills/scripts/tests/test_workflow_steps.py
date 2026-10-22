"""Exhaustive step tests for all workflow-based skills.

Tests every step of every workflow with all valid parameter combinations.
Uses domain types (BoundedInt, ChoiceSet, Constant) to generate Cartesian products.
"""

import re
import sys

import pytest
from conftest import EXCLUDED, run_skill_invocation  # pyright: ignore[reportMissingImports]
from test_generation import generate_inputs  # pyright: ignore[reportMissingImports]

from skills.codebase_analysis import analyze as codebase_analysis
from skills.deepthink import subagent, think
from skills.incoherence import incoherence
from skills.lib.workflow import discover_workflows
from skills.problem_analysis import analyze as problem_analysis
from skills.refactor import explore, refactor


def _collect_test_cases():
    """Collect all test cases from registered workflows.

    Returns list of pytest.param with (workflow_name, workflow, params) and test IDs.
    """
    # discover_workflows handles import and discovery in one call
    registry = discover_workflows("skills")
    test_cases = []

    for name, workflow in sorted(registry.items()):
        if name in EXCLUDED:
            continue

        for params in generate_inputs(workflow):
            # Build readable test ID: workflow-sN-param1-param2
            # 's' prefix distinguishes step from iteration 'i' in pytest output.
            step = params["step"]
            id_parts = [name, f"s{step}"]

            # Add param variants in alphabetical order (excluding step)
            for key in sorted(params.keys()):
                if key not in ("step",):
                    value = params[key]
                    # Shorten mode values: full/quick
                    if key == "mode":
                        id_parts.append(value)
                    # Iteration: i1, i2, etc
                    elif key == "iteration":
                        id_parts.append(f"i{value}")
                    # Confidence: first letter
                    elif key == "confidence":
                        id_parts.append(value[0])
                    # Other params: key=value (truncate long values)
                    else:
                        val_str = str(value)[:20]
                        id_parts.append(f"{key}={val_str}")

            test_id = "-".join(id_parts)
            test_cases.append(pytest.param(name, workflow, params, id=test_id))

    return test_cases


@pytest.mark.parametrize(
    "workflow_name,workflow,params",
    _collect_test_cases(),
)
def test_workflow_step(workflow_name, workflow, params):
    """Test that workflow step is invocable with given params."""
    ok, msg = run_skill_invocation(workflow, params)
    assert ok, f"Step {params['step']} failed: {msg}"


def _render(monkeypatch, capsys, module, *argv: str) -> str:
    """Run module's CLI entry point with argv and return what it printed."""
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    module.main()
    return capsys.readouterr().out


def _next_steps(output: str, module_path: str, flag: str = "--step") -> list[int]:
    """Step numbers of the commands in output that invoke module_path."""
    pattern = rf"python -m {re.escape(module_path)} {flag} (\d+)"
    return [int(step) for step in re.findall(pattern, output)]


@pytest.mark.parametrize(
    "argv,target",
    [
        pytest.param(["--step", "5", "--mode", "full"], 6, id="planning-full"),
        pytest.param(["--step", "5", "--mode", "quick"], 10, id="planning-quick"),
        pytest.param(
            ["--step", "11", "--iteration", "1", "--confidence", "certain"],
            11,
            id="refinement-first-iteration-loops",
        ),
        pytest.param(
            ["--step", "11", "--iteration", "2", "--confidence", "high"],
            12,
            id="refinement-high-exits",
        ),
        pytest.param(
            ["--step", "11", "--iteration", str(think.MAX_ITERATIONS), "--confidence", "low"],
            12,
            id="refinement-cap-exits",
        ),
    ],
)
def test_deepthink_step_prints_one_command_for_its_next_step(monkeypatch, capsys, argv, target):
    out = _render(monkeypatch, capsys, think, *argv)
    assert _next_steps(out, think.MODULE_PATH) == [target]


_DEEPTHINK_FLAGS = ["--confidence", "high", "--iteration", "2"]


@pytest.mark.parametrize(
    "module,extra,visited",
    [
        pytest.param(
            think,
            ["--mode", "full", *_DEEPTHINK_FLAGS],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            id="think-full",
        ),
        pytest.param(
            think,
            ["--mode", "quick", *_DEEPTHINK_FLAGS],
            [1, 2, 3, 4, 5, 10, 11, 12],
            id="think-quick",
        ),
        pytest.param(subagent, [], [1, 2, 3, 4, 5, 6, 7], id="subagent"),
    ],
)
def test_deepthink_walk_from_step_1_visits_each_step_once_in_order(
    monkeypatch, capsys, module, extra, visited
):
    steps = [1]
    while len(steps) <= len(visited):
        out = _render(monkeypatch, capsys, module, "--step", str(steps[-1]), *extra)
        targets = _next_steps(out, module.MODULE_PATH)
        if not targets:
            break
        steps.extend(targets)
    assert steps == visited


@pytest.mark.parametrize(
    "step,targets",
    [
        pytest.param(3, [8], id="exploration-dispatch"),
        pytest.param(9, [12], id="deep-dive-dispatch"),
        pytest.param(17, [20], id="reconcile-dispatch"),
        pytest.param(15, [14, 16], id="resolution-loop"),
        pytest.param(20, [17, 21], id="reconcile-collect"),
    ],
)
def test_incoherence_invoke_after_targets(monkeypatch, capsys, step, targets):
    out = _render(monkeypatch, capsys, incoherence, "--step-number", str(step))
    invoke_after = re.search(r"^<invoke_after>$.*?^</invoke_after>$", out, re.M | re.S)
    assert invoke_after is not None
    steps = _next_steps(invoke_after.group(), incoherence.MODULE_PATH, "--step-number")
    assert sorted(steps) == targets


@pytest.mark.parametrize(
    "module,cap,work",
    [
        pytest.param(
            problem_analysis,
            problem_analysis.MAX_ITERATIONS,
            problem_analysis.INVESTIGATE_INSTRUCTIONS,
            id="problem_analysis-investigate",
        ),
        pytest.param(
            codebase_analysis,
            codebase_analysis.MAX_DEEPEN_ITERATIONS,
            codebase_analysis.build_deepen_body(codebase_analysis.MAX_DEEPEN_ITERATIONS),
            id="codebase_analysis-deepen",
        ),
    ],
)
def test_last_iteration_under_the_cap_renders_its_work_then_routes_to_step_4(
    monkeypatch, capsys, module, cap, work
):
    argv = ["--step", "3", "--iteration", str(cap), "--confidence", "medium"]
    out = _render(monkeypatch, capsys, module, *argv)
    assert work in out
    assert _next_steps(out, module.MODULE_PATH) == [4]


@pytest.fixture
def conventions_dir(monkeypatch, tmp_path):
    """Point explore.CONVENTIONS_DIR at a temporary conventions file."""
    (tmp_path / "cat.md").write_text("# Conventions\n\n## 1. Naming\nbody\n\n## 2. Errors\nbody\n")
    monkeypatch.setattr(explore, "CONVENTIONS_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize("step", [1, 5])
@pytest.mark.parametrize(
    "ref", ["cat.md:1-2", "cat.md:40-45"], ids=["starts-off-heading", "starts-past-end"]
)
def test_explore_exits_naming_a_category_ref_that_does_not_start_at_a_heading(
    monkeypatch, capsys, conventions_dir, step, ref
):
    with pytest.raises(SystemExit) as exited:
        _render(monkeypatch, capsys, explore, "--step", str(step), "--category", ref)
    assert ref in str(exited.value.code)


def test_explore_step_5_reports_under_the_category_its_ref_starts_at(
    monkeypatch, capsys, conventions_dir
):
    out = _render(monkeypatch, capsys, explore, "--step", "5", "--category", "cat.md:6-7")
    assert 'category="Errors"' in out


def test_refactor_step_1_hands_the_scope_it_extracts_to_step_2(monkeypatch, capsys):
    out = _render(monkeypatch, capsys, refactor, "--step", "1")
    commands = re.findall(rf"python -m {re.escape(refactor.MODULE_PATH)} --step 2 [^\"]*", out)
    assert commands
    assert all("--scope $SCOPE" in command for command in commands)
