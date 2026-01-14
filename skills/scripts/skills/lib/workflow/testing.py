"""Test harness for skills validation.

Test Levels:
  L0: Import succeeds
  L1: Registration valid (total_steps > 0)
  L2: Invocability (subprocess call returns 0 for boundary inputs)

Usage:
  python -m skills.lib.workflow.testing --level 2
  python -m skills.lib.workflow.testing --skill decision-critic --level 2
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .core import get_workflow_registry, Workflow


@dataclass
class TestResult:
    """Single test result."""

    skill: str
    level: int
    passed: bool
    message: str = ""

    def __str__(self):
        status = "[OK]" if self.passed else "[FAIL]"
        return f"{status} {self.skill} L{self.level}: {self.message}"


def generate_boundary_inputs(workflow: Workflow) -> Iterator[dict[str, Any]]:
    """Generate single-factor boundary inputs for a workflow.

    Yields base case plus variations at parameter boundaries.
    """
    # Build base case with defaults
    base: dict[str, Any] = {"step": 1, "total_steps": workflow.total_steps}

    # Collect all params from workflow
    all_params = {}
    for step_params in workflow._params.values():
        for pspec in step_params:
            pname = pspec["name"]
            if pname not in all_params:
                all_params[pname] = pspec

    for pname, pspec in all_params.items():
        if pname in ("step", "total_steps"):
            continue
        if pspec.get("default") is not None:
            base[pname] = pspec["default"]
        elif pspec.get("choices"):
            # For scope params, try to match workflow name suffix to a choice
            # e.g. prompt-engineer-ecosystem -> scope='ecosystem'
            choices = pspec["choices"]
            if pname == "scope":
                matched = next(
                    (c for c in choices if workflow.name.endswith(f"-{c}")),
                    None,
                )
                base[pname] = matched if matched else choices[0]
            else:
                base[pname] = choices[0]
        else:
            # Provide synthetic values for non-defaulted params
            base[pname] = _synthetic_value(pname, pspec)

    # Yield base case
    yield dict(base)

    # Yield step boundaries (first and last)
    for s in (1, workflow.total_steps):
        if s != base["step"]:
            yield {**base, "step": s}

    # Yield choice boundaries
    for pname, pspec in all_params.items():
        choices = pspec.get("choices")
        if choices and len(choices) > 1:
            for choice in choices[1:]:
                yield {**base, pname: choice}


def _synthetic_value(pname: str, pspec: dict[str, Any]) -> Any:
    """Generate synthetic test value for a parameter."""
    # Common parameter names get meaningful test values
    if pname == "decision":
        return "Test decision for validation"
    if pname == "question":
        return "Test question for validation"
    if pname == "prompt":
        return "Test prompt for validation"
    if pname == "qr_status":
        return "pass"  # Gate steps require qr_status

    # Fall back to type-based defaults
    min_val = pspec.get("min")
    if min_val is not None:
        return min_val
    choices = pspec.get("choices")
    if choices:
        return choices[0]

    return "test_value"


def run_skill_invocation(workflow: Workflow, inputs: dict[str, Any]) -> tuple[bool, str]:
    """Run skill with inputs via subprocess.

    Returns:
        (True, stdout) on success
        (False, error_message) on failure
    """
    # Build command: python -m module --step N --total-steps T ...
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
            cwd=Path(__file__).parent.parent.parent.parent,  # scripts/
        )
        if result.returncode == 0:
            return True, result.stdout[:200]
        return False, result.stderr[:200] or f"Exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Timeout (30s)"
    except Exception as e:
        return False, str(e)[:200]


def test_workflow(workflow, level: int = 2) -> list[TestResult]:
    """Run tests for a Workflow object."""
    from .core import Workflow

    if not isinstance(workflow, Workflow):
        return [TestResult(str(workflow), 0, False, "Not a Workflow object")]

    results: list[TestResult] = []

    # L0: Workflow is valid
    try:
        workflow._validate()
        results.append(TestResult(workflow.name, 0, True, "Workflow valid"))
    except Exception as e:
        results.append(TestResult(workflow.name, 0, False, f"Validation failed: {e}"))
        return results

    # L1: Has steps and valid structure
    if workflow.total_steps < 1:
        results.append(TestResult(workflow.name, 1, False, "total_steps < 1"))
        return results
    results.append(
        TestResult(
            workflow.name,
            1,
            True,
            f"total_steps={workflow.total_steps}, entry={workflow.entry_point}",
        )
    )

    if level < 2:
        return results

    # L2: Invocability - test via subprocess
    for inputs in generate_boundary_inputs(workflow):
        ok, msg = run_skill_invocation(workflow, inputs)
        step = inputs.get("step", "?")
        if ok:
            results.append(TestResult(workflow.name, 2, True, f"step={step} OK"))
        else:
            results.append(TestResult(workflow.name, 2, False, f"step={step}: {msg}"))

    return results


def run_all_tests(level: int = 2) -> list[TestResult]:
    """Run tests for all registered workflows."""
    from .core import get_workflow_registry

    results: list[TestResult] = []

    # Test new Workflow skills
    for workflow in get_workflow_registry().values():
        results.extend(test_workflow(workflow, level))

    return results


def _import_all_skills() -> list[TestResult]:
    """Import all skill modules to populate registry.

    Returns TestResult for each import failure (L0 = import succeeds).
    """
    import importlib

    skill_modules = [
        "skills.decision_critic.decision_critic",
        "skills.leon_writing_style.writing_style",
        "skills.problem_analysis.analyze",
        "skills.codebase_analysis.analyze_workflow",
        "skills.deepthink.think",
        "skills.incoherence.incoherence",
        "skills.refactor.refactor",
        "skills.planner.planner",
        "skills.solution_design.design",
        "skills.prompt_engineer.optimize",
    ]

    failures: list[TestResult] = []
    for module in skill_modules:
        try:
            importlib.import_module(module)
        except Exception as e:
            # Extract skill name from module path for readable output
            skill_name = module.split(".")[-2]
            failures.append(TestResult(skill_name, 0, False, f"Import failed: {e}"))
    return failures


def main():
    """Test harness CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Skills test harness")
    parser.add_argument(
        "--level", "-l", type=int, default=2, choices=[0, 1, 2], help="Test level"
    )
    parser.add_argument("--skill", "-s", type=str, help="Test specific skill")
    args = parser.parse_args()

    # Import all skills, capturing any import failures as L0 test failures
    import_failures = _import_all_skills()

    if args.skill:
        from .core import get_workflow_registry

        workflow = get_workflow_registry().get(args.skill)

        if workflow:
            results = test_workflow(workflow, args.level)
        else:
            print(f"[FAIL] Unknown skill: {args.skill}")
            print(f"Available: {', '.join(sorted(get_workflow_registry().keys()))}")
            sys.exit(1)
    else:
        results = import_failures + run_all_tests(args.level)

    # Report
    for r in results:
        print(r)

    failed = [r for r in results if not r.passed]
    total = len(results)
    passed = total - len(failed)

    print(f"\n{passed}/{total} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
