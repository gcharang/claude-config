#!/usr/bin/env python3
"""
Shared perspective definitions for solution-design skill.

Single source of truth for all perspective metadata. Used by:
  - perspective.py: Full definitions for solution generation prompts
  - design.py: Core questions for dispatch, full definitions for context

Design note: Perspectives are MODES OF REASONING, not optimization targets.
"Performance-focused" tells you WHAT to value but not HOW to think differently.
These perspectives each employ genuinely different reasoning patterns, producing
structurally different solutions regardless of domain (software, physical systems,
organizational problems, theoretical challenges).
"""

import argparse
import sys


PERSPECTIVES = {
    "minimal": {
        "title": "Minimal Intervention",
        "core_question": "What is the smallest change that addresses the root cause?",
        "rationale": (
            "We bias toward complexity. When something breaks, we're tempted to "
            "redesign, add layers, or introduce frameworks. But often the right "
            "answer is a single adjustment. Even if we ultimately choose something "
            "more comprehensive, knowing the minimal option exists provides a "
            "valuable baseline for comparison."
        ),
        "generation_heuristics": [
            "What single adjustment would resolve this?",
            "What would an experienced practitioner do in fifteen minutes?",
            "What can remain exactly as-is while still fixing the problem?",
            "If forced to ship a fix today, what would it be?",
        ],
        "output_expectations": (
            "Solutions are localized to one to three components, introduce no new "
            "abstractions or dependencies, are trivially reversible, and would be "
            "obvious to a reviewer."
        ),
    },
    "structural": {
        "title": "Structural/Comprehensive",
        "core_question": "What design change would make this class of problem impossible?",
        "rationale": (
            "Minimal fixes treat instances while structural fixes address categories. "
            "If the same bug can recur in similar code, a minimal fix is incomplete. "
            "This perspective asks what invariant should hold but doesn't, and what "
            "restructuring would enforce it."
        ),
        "generation_heuristics": [
            "What pattern does this instance belong to?",
            "What would prevent not just this occurrence but all similar ones?",
            "What would 'doing this properly' look like?",
            "What would make this bug impossible to reintroduce?",
            "What would make failures in this area survivable rather than catastrophic?",
        ],
        "output_expectations": (
            "Solutions address the root cause rather than symptoms, prevent similar "
            "issues in related areas, include appropriate validation or enforcement "
            "mechanisms, and are documented for future maintainers."
        ),
    },
    "stateless": {
        "title": "Stateless/Functional",
        "core_question": "What if we eliminated or dramatically simplified state?",
        "rationale": (
            "Many problems stem from state management: race conditions, inconsistent "
            "state, mutation-order dependencies, unexpected side effects. Pure functions "
            "and immutable structures eliminate entire bug categories. Even in non-software "
            "domains, stateless solutions (passive systems, feedforward rather than feedback "
            "control) can be more robust than stateful ones."
        ),
        "generation_heuristics": [
            "Where does mutable state live and what problems does it enable?",
            "Could this be a pure transformation from inputs to outputs with no side effects?",
            "Could we replace mutation with creation of new values rather than changing existing ones?",
            "Can we push state to the boundaries while keeping the core stateless?",
        ],
        "output_expectations": (
            "Solutions eliminate or isolate mutable state, express logic as transformations "
            "rather than procedures, make data flow explicit and traceable, and reduce or "
            "eliminate temporal coupling."
        ),
    },
    "domain": {
        "title": "Domain-Modeled",
        "core_question": "What concept from the problem domain are we failing to represent?",
        "rationale": (
            "Problems often exist when our solution doesn't match the problem's natural "
            "structure. When we model a domain correctly--using its native concepts, "
            "respecting its actual boundaries, representing its real events and states--"
            "bugs have fewer places to hide. Domain-driven design, CQRS, and event sourcing "
            "work not because they're clever patterns but because they make solutions "
            "isomorphic to their domains."
        ),
        "generation_heuristics": [
            "What domain concepts exist in reality but not in our model?",
            "Are we using primitives (strings, numbers) where domain-specific types belong?",
            "What events actually occur in this domain? What states are actually valid?",
            "Would an expert in the domain recognize our model?",
            "Are there failure modes or edge cases that should be explicitly represented?",
        ],
        "output_expectations": (
            "Solutions introduce domain concepts that clarify the system, make invalid "
            "states unrepresentable through the type system or structure, align boundaries "
            "with real domain boundaries, and use domain language consistently."
        ),
    },
    "removal": {
        "title": "Removal/Simplification",
        "core_question": "What if we removed something instead of adding?",
        "rationale": (
            "We have a strong bias toward addition. When something doesn't work, we add "
            "validation, error handling, caching, abstraction layers. But often the best "
            "solution is deletion: remove the feature that causes problems, inline the "
            "abstraction that obscures intent, eliminate the edge case that complicates "
            "everything. Simpler systems have fewer bugs."
        ),
        "generation_heuristics": [
            "What could be deleted to make the problem disappear?",
            "What abstractions add complexity without proportional benefit?",
            "Is each feature actually needed?",
            "What is the simplest system that still meets requirements?",
        ],
        "output_expectations": (
            "Solutions reduce total complexity, remove rather than add components, "
            "question whether the problem would exist if we did less, and simplify "
            "the mental model needed to understand the system."
        ),
    },
    "firstprinciples": {
        "title": "First Principles",
        "core_question": "If we derived from fundamental truths rather than convention, what solution emerges?",
        "rationale": (
            "Many solutions are 'how it's always been done' or what convention suggests. "
            "First principles reasoning strips away convention and asks what actually must "
            "be true. This often reveals solutions that are non-obvious precisely because "
            "they don't follow established patterns."
        ),
        "generation_heuristics": [
            "What are the fundamental requirements, not assumed features?",
            "Which constraints are physical or logical vs merely conventional?",
            "What would we build starting from scratch today with no legacy?",
            "What would a physicist or mathematician say about the problem structure?",
            "What does the system need to do when the ideal conditions don't hold?",
        ],
        "output_expectations": (
            "Solutions derive from actual requirements rather than assumed ones, question "
            "inherited constraints, may look unusual but can be justified from fundamentals, "
            "and often reveal that 'obvious' solutions weren't actually required."
        ),
    },
    "upstream": {
        "title": "Upstream/Prevention",
        "core_question": "What if we solved this at an earlier point in the causal chain?",
        "rationale": (
            "We often address problems where they manifest rather than where they originate. "
            "Moving upstream can be more effective: prevent bad data from entering rather "
            "than handling malformed data downstream, block heat loss rather than adding "
            "heating capacity, prevent the error condition rather than catching the exception."
        ),
        "generation_heuristics": [
            "Where does the problem originate vs where does it manifest?",
            "Could we prevent the problematic input or state from arising?",
            "What is the earliest point at which we could detect or prevent this issue?",
            "Are we handling exceptions that shouldn't exist?",
        ],
        "output_expectations": (
            "Solutions prevent rather than handle, validate at trust boundaries rather "
            "than throughout, make problematic states impossible rather than checking for "
            "them, and reduce defensive code by eliminating what it defends against."
        ),
    },
}

# Ordered list for iteration
PERSPECTIVE_ORDER = [
    "minimal",
    "structural",
    "stateless",
    "domain",
    "removal",
    "firstprinciples",
    "upstream",
]


def format_perspective_full(perspective_id: str) -> str:
    """Format full perspective definition as XML for agent consumption."""
    p = PERSPECTIVES[perspective_id]
    lines = [f'<perspective id="{perspective_id}">']
    lines.append(f"  <title>{p['title']}</title>")
    lines.append(f"  <core_question>{p['core_question']}</core_question>")
    lines.append("")
    lines.append("  <rationale>")
    lines.append(f"    {p['rationale']}")
    lines.append("  </rationale>")
    lines.append("")
    lines.append("  <generation_heuristics>")
    for h in p["generation_heuristics"]:
        lines.append(f"    <heuristic>{h}</heuristic>")
    lines.append("  </generation_heuristics>")
    lines.append("")
    lines.append("  <output_expectations>")
    lines.append(f"    {p['output_expectations']}")
    lines.append("  </output_expectations>")
    lines.append("</perspective>")
    return "\n".join(lines)


def format_list() -> str:
    """Format perspective ID list."""
    lines = ["<perspectives>"]
    for p_id in PERSPECTIVE_ORDER:
        lines.append(f"  <id>{p_id}</id>")
    lines.append("</perspectives>")
    return "\n".join(lines)


def format_all() -> str:
    """Format all perspectives as XML."""
    lines = ["<perspectives>"]
    for p_id in PERSPECTIVE_ORDER:
        p = PERSPECTIVES[p_id]
        lines.append(f'  <perspective id="{p_id}">')
        lines.append(f"    <title>{p['title']}</title>")
        lines.append(f"    <core_question>{p['core_question']}</core_question>")
        lines.append(f"  </perspective>")
    lines.append("</perspectives>")
    return "\n".join(lines)


def format_summary() -> str:
    """Format perspective summaries for dispatch."""
    lines = ["<perspective_summaries>"]
    for p_id in PERSPECTIVE_ORDER:
        p = PERSPECTIVES[p_id]
        lines.append(f'  <perspective id="{p_id}">')
        lines.append(f"    <title>{p['title']}</title>")
        lines.append(f"    <core_question>{p['core_question']}</core_question>")
        lines.append(f"  </perspective>")
    lines.append("</perspective_summaries>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Shared perspective definitions for solution-design skill",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List perspective IDs")
    group.add_argument(
        "--perspective", type=str, help="Get full definition for perspective"
    )
    group.add_argument(
        "--all", action="store_true", help="Get all perspectives as XML summary"
    )
    group.add_argument(
        "--summary", action="store_true", help="Get perspective summaries for dispatch"
    )

    args = parser.parse_args()

    if args.list:
        print(format_list())
    elif args.perspective:
        if args.perspective not in PERSPECTIVES:
            sys.exit(
                f"ERROR: Unknown perspective '{args.perspective}'. "
                f"Valid: {', '.join(PERSPECTIVE_ORDER)}"
            )
        print(format_perspective_full(args.perspective))
    elif args.all:
        print(format_all())
    elif args.summary:
        print(format_summary())


if __name__ == "__main__":
    main()
