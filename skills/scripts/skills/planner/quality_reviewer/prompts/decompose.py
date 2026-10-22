"""Shared utilities for QR decomposition scripts.

Mechanical utilities and truly-generic prompts (identical across the phases).

WHY "truly-generic": the shared prompts apply identical logic regardless of phase.
Phase-specific prompts (what to absorb, what concerns to brainstorm, what severity
categories) differ fundamentally per phase.

WHY functions not class: Composition without coupling. A caller imports only the
utilities it needs. No forced inheritance hierarchy.

CRITICAL INVARIANT - Phase-Severity Alignment:
Each phase uses severity categories matching agent capabilities:
  - impl-docs: KNOWLEDGE categories only (TW cannot fix code issues)
  - impl-code: STRUCTURE + COSMETIC (Dev can fix code)
  - plan-design: DIAGRAM + subset of KNOWLEDGE
Violating this causes unrecoverable QR loops.

ORCHESTRATOR CONTRACT:
The decompose runner's get_step_guidance(step, module_path, **kwargs) returns
dispatch_step's {title: str, actions: list[str], next: str}.
"""

import json
from collections.abc import Callable
from pathlib import Path

from skills.planner.shared.builders import shell_quote
from skills.planner.shared.qr.utils import load_validated_qr_state
from skills.planner.shared.resources import render_phase_context

# =============================================================================
# SHARED PROMPTS (truly identical across the phases)
# =============================================================================

GAP_ANALYSIS_PROMPT = """\
COMPARE Step 2 (holistic concerns) vs Step 3 (structural elements):

For each CONCERN from Step 2:
  - Is it addressed by verifying specific elements from Step 3?
  - Or is it cross-cutting (spans multiple elements)?
  - Or is it about something MISSING from the plan?

For each ELEMENT from Step 3:
  - Is there a concern from Step 2 that covers it?
  - If not, what verification does this element need?

OUTPUT:
  - Concerns needing UMBRELLA items (cross-cutting)
  - Concerns mapping to SPECIFIC elements
  - Elements needing their own verification items
  - GAPS: things neither approach caught"""


ATOMICITY_RULES = """\
REVIEW each item for atomicity.

An item is ATOMIC if:
  - It tests exactly ONE thing
  - Pass/fail is unambiguous
  - It cannot be 'half passed'

NON-ATOMIC signals:
  - Contains 'and' joining distinct concerns
  - Contains 'all/each/every' over unbounded collection
  - Failure could mean multiple different problems

DECISION RULE (based on severity):
  - If non-atomic AND severity=MUST: SPLIT into specifics, KEEP umbrella
  - If non-atomic AND severity=SHOULD/COULD: KEEP as umbrella (broader coverage)

WHY severity determines splitting:
  MUST items block all iterations -- specific diagnostics justify the cost
  SHOULD/COULD items have lower stakes -- umbrella catches suffice

WHEN SPLITTING:
  - Original item becomes PARENT (keep id, e.g., qa-002)
  - New items become CHILDREN (suffixed, e.g., qa-002a, qa-002b)
  - Each child MUST have parent_id field set to parent's id
  - Children inherit parent's severity

OUTPUT: Revised item list with atomicity notes."""


COVERAGE_VALIDATION_PROMPT = """\
FINAL CHECK using Step 3 enumeration as checklist:

For EACH element enumerated in Step 3:
  [ ] At least one item would catch issues with this element

For EACH concern from Step 2:
  [ ] At least one item addresses this concern

If any unchecked: ADD items.

PREFERENCE: If uncertain whether coverage is adequate, ADD an item.
Overlapping coverage is acceptable. Gaps are not.

OUTPUT: Final item list ready for finalization."""


FINALIZE_PROMPT = """\
WRITE qr-{phase}.json to STATE_DIR:

{{
  "phase": "{phase}",
  "iteration": 1,
  "items": [/* your items from Step 7 */]
}}

Item count: whatever the content requires. No fixed caps.

After writing, run the next step to validate the file."""


# =============================================================================
# STEP DISPATCH HELPER (eliminates duplicate control flow)
# =============================================================================


def render_code_milestone_scope(state_dir: str, phase: str) -> str:
    """Explicit in-scope code-milestone ids for the impl-code decompose agent.

    Structural backstop for the prose "exclude documentation-only" nudge: the
    agent is handed the literal id list from Plan.code_milestones() so a doc-only
    milestone's acceptance_criteria can't be enumerated as unsatisfiable impl-code
    QR items. Returns "" for non-impl-code phases (plan-design enumerates
    everything; impl-docs targets doc-only milestones) and whenever plan.json is
    absent or unparseable -- the static prose then stands alone (graceful degrade).
    """
    if phase != "impl-code" or not state_dir:
        return ""
    # Local import + tolerant load: do NOT use cli.plan.load_plan (it error_exit()s,
    # which would abort a prompt build).
    from skills.planner.shared.schema import Plan

    path = Path(state_dir) / "plan.json"
    if not path.exists():
        return ""
    try:
        plan = Plan.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return ""
    ids = ", ".join(ms.id for ms in plan.code_milestones()) or "(none)"
    return (
        "CODE MILESTONES IN SCOPE (enumerate items ONLY for these; "
        "documentation-only\n"
        "milestones produce no code and are verified in impl-docs, not here):\n"
        f"  {ids}"
    )


def no_scope(state_dir: str, phase: str) -> str:
    """Default scope provider: no extra in-scope enumeration.

    A phase with no scope registers this so dispatch_step always holds a callable
    scope_provider (uniform slot) -- no `if provider` special-casing.
    """
    return ""


def dispatch_step(
    step: int,
    phase: str,
    module_path: str,
    phase_prompts: dict[int, str],
    state_dir: str = "",
    scope_provider: Callable[[str, str], str] = no_scope,
) -> dict:
    """Route step to appropriate handler.

    WHY this function: The phases share one owner for the routing control flow. The
    caller supplies phase-specific content (phase_prompts); this
    function handles the common routing logic.

    Args:
        step: Current step number
        phase: Phase name
        module_path: Module path for next step command
        phase_prompts: Dict mapping step numbers to phase-specific prompt strings
                      Required keys: 1, 2, 3, 5
        state_dir: State directory path

    Returns:
        Dict with title, actions, next keys
    """
    state_dir_arg = f" --state-dir {shell_quote(state_dir)}" if state_dir else ""
    phase_arg = f" --phase {phase}"
    # Explicit code-milestone scope for impl-code (structural doc-only exclusion);
    # "" for other phases / missing plan, so the conditional injections below add
    # nothing.
    code_scope = scope_provider(state_dir, phase) if step in (1, 3) else ""

    def next_cmd(s):
        return f"uv run python -m {module_path} --step {s}{phase_arg}{state_dir_arg}"

    # Step 1: Absorb context (phase-specific)
    if step == 1:
        context_display = render_phase_context(state_dir, phase) if state_dir else ""
        return {
            "title": f"QR Decomposition Step 1: Absorb Context ({phase})",
            "actions": [
                f"PHASE: {phase}",
                "",
                phase_prompts[1],
                "",
                *([code_scope, ""] if code_scope else []),
                "PLANNING CONTEXT:",
                context_display,
                "",
                "TASK: Read and understand. Summarize in 2-3 sentences:",
                "  - What is this plan trying to accomplish?",
                "  - What does success look like for this phase?",
                "",
                "Items come in step 5; this step establishes the context they are checked against.",
            ],
            "next": next_cmd(2),
        }

    # Step 2: Holistic concerns (phase-specific)
    elif step == 2:
        return {
            "title": f"QR Decomposition Step 2: Holistic Concerns ({phase})",
            "actions": [
                "TOP-DOWN: If reviewing this phase output, what would you check?",
                "",
                phase_prompts[2],
                "",
                "OUTPUT: Bulleted list of concerns -- capture everything; step 4 maps them",
                "to items and step 5 turns the cross-cutting ones into umbrella items.",
                "",
                "These concerns will drive umbrella items in Step 5.",
            ],
            "next": next_cmd(3),
        }

    # Step 3: Structural enumeration (phase-specific)
    elif step == 3:
        return {
            "title": f"QR Decomposition Step 3: Structural Enumeration ({phase})",
            "actions": [
                "BOTTOM-UP: What EXISTS in the plan for this phase?",
                "",
                phase_prompts[3],
                "",
                *([code_scope, ""] if code_scope else []),
                "OUTPUT: Structured list of plan elements.",
                "  - Use IDs where available (DL-001, M-001, CI-001)",
                "  - Note counts (e.g., '3 decisions, 5 milestones')",
                "",
                "This enumeration becomes a completeness checklist in Step 7.",
            ],
            "next": next_cmd(4),
        }

    # Step 4: Gap analysis (shared)
    elif step == 4:
        return {
            "title": f"QR Decomposition Step 4: Gap Analysis ({phase})",
            "actions": [GAP_ANALYSIS_PROMPT],
            "next": next_cmd(5),
        }

    # Step 5: Generate items (phase-specific severity)
    elif step == 5:
        return {
            "title": f"QR Decomposition Step 5: Generate Items ({phase})",
            "actions": [
                "CREATE verification items using the UMBRELLA + SPECIFIC pattern:",
                "",
                "WHY THIS PATTERN: Overlapping coverage catches outliers that specific",
                "items miss. This intentional redundancy is a feature, not waste.",
                "",
                "UMBRELLA ITEMS (scope: '*'):",
                "  - One per cross-cutting concern from Step 4",
                "  - Broad enough to catch outliers",
                "",
                "SPECIFIC ITEMS (scope: element reference):",
                "  - One per element needing verification",
                "  - Targeted at specific element",
                "",
                "CRITICAL CONCERNS get BOTH umbrella AND specific items.",
                "",
                "FORMAT each item:",
                '  {"id": "qa-NNN", "scope": "...", "check": "...", "status": "TODO", "severity": "..."}',
                "",
                phase_prompts[5],  # Phase-specific severity guidance
                "",
                "NO FIXED COUNT - generate what the content requires.",
            ],
            "next": next_cmd(6),
        }

    # Step 6: Atomicity check (shared)
    elif step == 6:
        return {
            "title": f"QR Decomposition Step 6: Atomicity Check ({phase})",
            "actions": [ATOMICITY_RULES],
            "next": next_cmd(7),
        }

    # Step 7: Coverage validation (shared)
    elif step == 7:
        return {
            "title": f"QR Decomposition Step 7: Coverage Validation ({phase})",
            "actions": [COVERAGE_VALIDATION_PROMPT],
            "next": next_cmd(8),
        }

    # Step 8: Finalize (shared with phase substitution)
    elif step == 8:
        return {
            "title": f"QR Decomposition Step 8: Finalize ({phase})",
            "actions": [FINALIZE_PROMPT.format(phase=phase)],
            "next": next_cmd(9),
        }

    # Step 9: validate the written file (terminal)
    elif step == 9:
        return step_9_validate(state_dir, phase)

    return {"error": f"Unknown step {step}"}


# =============================================================================
# STEP 9: TERMINAL VALIDATION
# =============================================================================


def step_9_validate(state_dir: str, phase: str) -> dict:
    """Step 9 (terminal): check the written file and its parent links."""
    title = f"QR Decomposition Step 9: Validate ({phase})"
    qr_state = load_validated_qr_state(state_dir, phase)
    if qr_state is None:
        return {
            "title": title,
            "actions": [
                f"BLOCKING ERROR: qr-{phase}.json is missing or fails schema validation.",
                "",
                "Return to Step 8, rewrite the file, then re-run this step's command.",
            ],
            "next": "",
        }
    items = qr_state.get("items", [])
    item_ids = {i["id"] for i in items}
    orphans = [
        i for i in items
        if i.get("status") == "TODO" and i.get("parent_id") and i.get("parent_id") not in item_ids
    ]
    # Orphans block workflow - data corruption must not propagate
    if orphans:
        return {
            "title": title,
            "actions": [
                "BLOCKING ERROR: Orphan items detected",
                "",
                f"Found {len(orphans)} orphan items (parent_id references missing parent):",
                f"  {[i['id'] for i in orphans]}",
                "",
                "These items have parent_id but parent does not exist.",
                "Return to Step 6 and fix atomicity splits to ensure parent items exist.",
                "",
                "WORKFLOW HALTED - fix parent_id references before continuing.",
            ],
            "next": "",  # Terminal error
        }
    return {
        "title": title,
        "actions": [
            f"qr-{phase}.json passes schema validation and every parent_id names an existing item.",
            "",
            "Your complete response must be exactly: PASS",
        ],
        "next": "",
    }
