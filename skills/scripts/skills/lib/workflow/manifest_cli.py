#!/usr/bin/env python3
"""CLI entry point for manifest generation.

Separate from registry.py to avoid module identity issues when running as __main__.

The manifest is derived from registered workflows, not manually maintained.
This tool generates the manifest file for reference and tooling compatibility.

Usage:
    python -m skills.lib.workflow.manifest_cli -o skills-manifest.json
"""

import argparse
import sys
from pathlib import Path


def main():
    """Generate skills manifest from registered workflows."""
    parser = argparse.ArgumentParser(description="Generate skills manifest from registry")
    parser.add_argument(
        "--output", "-o", type=str, default="skills-manifest.json", help="Output file"
    )
    args = parser.parse_args()

    # Import registry and skills AFTER argument parsing
    from .registry import write_manifest
    from .core import get_workflow_registry

    # Import all skills to populate registry
    _import_all_skills()

    # Generate and write manifest
    from .registry import generate_manifest
    manifest = generate_manifest()
    write_manifest(args.output)

    # Report counts
    total_skills = len(manifest["skills"])

    print(f"Generated {args.output}:")
    print(f"  - Total workflows: {total_skills}")


def _import_all_skills():
    """Import all skill modules to populate registry.

    This discovers skills by importing known modules, not by scanning.
    Add new skills here when created.
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

    for module in skill_modules:
        try:
            importlib.import_module(module)
        except Exception as e:
            print(f"Warning: Could not import {module}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
