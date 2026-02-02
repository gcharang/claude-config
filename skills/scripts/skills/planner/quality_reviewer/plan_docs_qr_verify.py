#!/usr/bin/env python3
"""QR verification for plan-docs phase.

Single-item verification mode for parallel QR dispatch.
Each verify agent receives --qr-item and validates ONE check.

Modes:
- --qr-item: Single item verification (for parallel dispatch)
- Default (legacy): Sequential 6-step full verification (deprecated)

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

        guidance = []

        if scope == "*":
            # Macro check
            guidance.extend([
                "MACRO CHECK - Verify across entire plan.json:",
                "",
                f"  Read plan.json:",
                f"    cat {state_dir}/plan.json | jq '.'",
                "",
            ])
        elif scope.startswith("code_change:"):
            cc_id = scope.split(":")[1]
            guidance.extend([
                f"CODE CHANGE CHECK - Focus on {cc_id}:",
                "",
                f"  Extract code_change:",
                f"    cat {state_dir}/plan.json | jq '.milestones[].code_changes[] | select(.id == \"{cc_id}\")'",
                "",
            ])
        elif scope.startswith("milestone:"):
            ms_id = scope.split(":")[1]
            guidance.extend([
                f"MILESTONE CHECK - Focus on {ms_id}:",
                "",
                f"  Extract milestone:",
                f"    cat {state_dir}/plan.json | jq '.milestones[] | select(.id == \"{ms_id}\")'",
                "",
            ])
        else:
            guidance.extend([
                f"SCOPED CHECK - Scope: {scope}",
                "",
                "  Read the relevant section from plan.json.",
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
