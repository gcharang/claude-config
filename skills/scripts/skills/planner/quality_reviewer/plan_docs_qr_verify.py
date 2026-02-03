#!/usr/bin/env python3
"""QR verification for plan-docs phase.

Single-item verification mode for parallel QR dispatch.
Each verify agent receives --qr-item and validates ONE check.

Scope: Documentation quality only -- verifying that planning knowledge is
captured in documentation fields. This is NOT code review.

In scope:
- Invisible knowledge coverage (decisions documented somewhere)
- Temporal contamination in documentation strings
- WHY-not-WHAT quality in comments
- Structural completeness of documentation{} fields
- decision_ref validity

Out of scope (verified in plan-code phase):
- Code correctness (compilation, exports, types)
- Diff format validity
- Whether planned files exist on disk

For decomposition (generating items), see plan_docs_qr_decompose.py.
"""

from skills.planner.shared.qr.types import QRState, LoopState
from skills.lib.workflow.ast import W, XMLRenderer, render
from skills.planner.shared.qr.utils import (
    get_qr_iteration,
    has_qr_failures,
    format_qr_result,
)
from skills.planner.shared.schema import get_qa_state_schema_example
from .qr_verify_base import VerifyBase


PHASE = "plan-docs"
WORKFLOW = "planner"


class PlanDocsVerify(VerifyBase):
    """QR verification for plan-docs phase."""

    PHASE = "plan-docs"

    def get_verification_guidance(self, item: dict, state_dir: str) -> list[str]:
        """Plan-docs-specific verification instructions."""
        scope = item.get("scope", "*")
        check = item.get("check", "")

        guidance = [
            "SCOPE CONSTRAINT: You are verifying DOCUMENTATION QUALITY only.",
            "  - Verify against plan.json content, NOT filesystem",
            "  - Check documentation fields, NOT code correctness",
            "  - Out of scope: compilation, exports, types, diff syntax",
            "",
        ]

        if scope == "*":
            guidance.extend([
                "MACRO CHECK - Verify across entire plan.json:",
                "",
                f"  Read plan.json:",
                f"    cat {state_dir}/plan.json | jq '.'",
                "",
            ])
        elif scope.startswith("decision:"):
            dl_id = scope.split(":")[1]
            guidance.extend([
                f"DECISION CHECK - Focus on {dl_id}:",
                "",
                f"  Extract decision:",
                f"    cat {state_dir}/plan.json | jq '.planning_context.decisions[] | select(.id == \"{dl_id}\")'",
                "",
                "  Verify this decision is documented somewhere (inline_comment,",
                "  function_block, or readme_entry with matching decision_ref).",
                "",
            ])
        elif scope.startswith("milestone:"):
            ms_id = scope.split(":")[1]
            guidance.extend([
                f"MILESTONE DOCUMENTATION CHECK - Focus on {ms_id}:",
                "",
                f"  Extract milestone documentation:",
                f"    cat {state_dir}/plan.json | jq '.milestones[] | select(.id == \"{ms_id}\") | .documentation'",
                "",
                "  Verify documentation{} fields are populated:",
                "  - module_comment for new files",
                "  - docstrings[] for functions",
                "  - function_blocks[] for non-trivial functions",
                "",
            ])
        elif scope.startswith("readme:"):
            path = scope.split(":", 1)[1]
            guidance.extend([
                f"README CHECK - Focus on {path}:",
                "",
                f"  Extract readme entry:",
                f"    cat {state_dir}/plan.json | jq '.readme_entries[] | select(.path == \"{path}\")'",
                "",
                "  Verify content captures cross-cutting invisible knowledge.",
                "",
            ])
        else:
            # Generic scope -- still constrain to plan.json
            guidance.extend([
                f"SCOPED CHECK - Scope: {scope}",
                "",
                f"  Read from plan.json (NOT filesystem):",
                f"    cat {state_dir}/plan.json | jq '.'",
                "",
                "  Find the relevant documentation section and verify.",
                "",
            ])

        # Add check-specific guidance
        if "temporal" in check.lower():
            guidance.extend([
                "TEMPORAL CONTAMINATION CHECK:",
                "  Scan for these patterns:",
                "  - CHANGE_RELATIVE: 'Added', 'Replaced', 'Changed', 'Now uses'",
                "  - BASELINE_REFERENCE: 'instead of', 'previously', 'replaces'",
                "  - LOCATION_DIRECTIVE: 'After X', 'Before Y', 'Insert'",
                "  - PLANNING_ARTIFACT: 'TODO', 'Will', 'Planned'",
                "  - INTENT_LEAKAGE: 'intentionally', 'deliberately', 'chose'",
                "",
            ])
        elif "baseline" in check.lower():
            guidance.extend([
                "BASELINE REFERENCE CHECK:",
                "  Look for references to removed/replaced code:",
                "  - 'Previously', 'Instead of', 'Replaces', 'Used to'",
                "  - 'Before this change', 'Old approach', 'Former'",
                "  Comments should stand alone without knowing prior state.",
                "",
            ])
        elif "structural completeness" in check.lower() or "json completeness" in check.lower():
            guidance.extend([
                "JSON STRUCTURAL COMPLETENESS CHECK:",
                "  Verify plan.json documentation fields are populated:",
                "  - Every milestone has documentation{} with module_comment",
                "  - Every function has a docstrings[] entry",
                "  - Every decision_log entry has reasoning field",
                "  - readme_entries[] have non-empty content",
                "",
            ])
        elif "decision_ref" in check.lower():
            guidance.extend([
                "DECISION REF VERIFICATION:",
                "  - Each decision_ref (DL-XXX) must exist in planning_context.decisions",
                "  - Extract decision_refs from code_changes[].comments",
                "  - Verify each one exists",
                "",
            ])
        elif "documentation" in check.lower() and "completeness" in check.lower():
            guidance.extend([
                "DOCUMENTATION COMPLETENESS CHECK:",
                "  Verify milestone has:",
                "  - Tier 3: module_comment for new files",
                "  - Tier 4: docstrings for ALL functions",
                "  - Tier 2: function_blocks for non-trivial functions",
                "  - Tier 1: inline_comments in code_changes",
                "",
            ])
        elif "why" in check.lower() and "what" in check.lower():
            guidance.extend([
                "WHY-NOT-WHAT VERIFICATION:",
                "  Comments should explain reasoning, not describe code.",
                "  BAD: 'Added a new function' (describes action)",
                "  GOOD: 'Mutex serializes cache access' (explains purpose)",
                "",
            ])
        elif "location directive" in check.lower():
            guidance.extend([
                "LOCATION DIRECTIVE CHECK:",
                "  Look for placement instructions:",
                "  - 'After X', 'Before Y', 'Insert at', 'At the top'",
                "  - 'Following the', 'Preceding the', 'Between'",
                "  These are planning artifacts, not permanent docs.",
                "",
            ])
        elif "planning artifact" in check.lower():
            guidance.extend([
                "PLANNING ARTIFACT CHECK:",
                "  Look for incomplete markers:",
                "  - 'TODO', 'FIXME', 'Will', 'Planned', 'Temporary'",
                "  - 'To be implemented', 'Not yet', 'Later'",
                "  Documentation should describe final state.",
                "",
            ])
        elif "reasoning chain" in check.lower() or "multi-step" in check.lower():
            guidance.extend([
                "REASONING CHAIN VERIFICATION:",
                "  Decision log entries should have multi-step chains.",
                "  BAD: 'Polling | Webhooks unreliable'",
                "  GOOD: 'Polling | 30% webhook failure -> need fallback anyway'",
                "  Look for: premise -> implication -> conclusion",
                "",
            ])
        elif "coverage" in check.lower() or "captured" in check.lower():
            guidance.extend([
                "INVISIBLE KNOWLEDGE COVERAGE CHECK:",
                "  Verify planning knowledge appears in documentation:",
                "  - Each decision in planning_context.decisions[] should have a",
                "    corresponding documentation artifact (inline_comment, function_block,",
                "    or readme_entry) that references it via decision_ref",
                "  - invisible_knowledge content should appear in readme_entries[]",
                "    or be localized to specific code via function_blocks/inline_comments",
                "",
                "  Search documentation fields for decision_refs:",
                f"    cat {state_dir}/plan.json | jq '.. | .decision_ref? // empty' | sort -u",
                "",
            ])

        return guidance


def get_step_guidance(step: int, module_path: str = None, **kwargs) -> dict:
    """Gateway normalizes input and delegates to base class."""
    module_path = module_path or "skills.planner.quality_reviewer.plan_docs_qr_verify"
    qr_item = kwargs.get("qr_item")
    state_dir = kwargs.get("state_dir", "")

    if qr_item:
        # Normalize to list (backwards compat if single string passed)
        items = qr_item if isinstance(qr_item, list) else [qr_item]
        kwargs["qr_item"] = items
        verifier = PlanDocsVerify()
        return verifier.get_step_guidance(step, module_path, **kwargs)

    return {
        "title": "Error: No Items",
        "actions": ["--qr-item required. Use: --qr-item a --qr-item b"],
        "next": "",
    }


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(
        __file__,
        get_step_guidance,
        "QR-Plan-Docs: Documentation quality validation workflow",
        extra_args=[
            (["--state-dir"], {"type": str, "help": "State directory path"}),
            (["--qr-item"], {"action": "append", "help": "Item ID (repeatable)"}),
        ],
    )
