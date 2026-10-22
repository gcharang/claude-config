#!/usr/bin/env python3
"""
Incoherence Detector - Step-based incoherence detection workflow

STEPS below defines the steps; main() maps each step to its phase and agent type.

Resolution is interactive - user answers AskUserQuestion prompts inline.
No manual file editing required.
"""

import argparse
import shlex

from skills.lib.workflow.ast.nodes import (
    CurrentActionNode,
    ElementNode,
    InvokeAfterNode,
    StepHeaderNode,
)
from skills.lib.workflow.ast.renderer import (
    XMLRenderer,
    render_current_action,
    render_invoke_after,
    render_step_header,
)
from skills.lib.workflow.core import (
    StepDef,
    Workflow,
)
from skills.lib.workflow.prompts import parallel_constraint, pin_cwd

MODULE_PATH = "skills.incoherence.incoherence"


def _invoke_line(cmd: str) -> str:
    """Render a cwd-pinned sub-agent invoke line for an AGENT PROMPT block.

    pin_cwd makes the command cwd-independent, so a spawned agent whose cwd has
    drifted still resolves the `skills` package; a relative
    working-dir=".claude/skills/scripts" fails with "No module named 'skills'". No
    quoteattr: render_current_action emits actions verbatim, so the
    \\"...\\" / {var} placeholders must survive unescaped.
    """
    return f'  Start: <invoke cmd="{pin_cwd(cmd)}" />'


def _next_step_cmd(target: int, thoughts: str = "") -> str:
    cmd = f"uv run python -m {MODULE_PATH} --step-number {target}"
    return f"{cmd} --thoughts {shlex.quote(thoughts)}" if thoughts else cmd


def _render_branches(branches: list[tuple[str, int] | tuple[str, int, str]]) -> str:
    """Render an <invoke_after> holding one <branch when="..."> command per condition.

    A branch's optional third element is the --thoughts value its command passes.
    Built from ElementNode because InvokeAfterNode's two branches are labelled
    if_pass/if_fail, which name a QR verdict rather than these loop conditions.
    """
    return XMLRenderer().render_element(
        ElementNode(
            "invoke_after",
            {},
            [
                ElementNode(
                    "branch",
                    {"when": condition},
                    [ElementNode("invoke", {"cmd": pin_cwd(_next_step_cmd(target, *thoughts))}, [])],
                )
                for condition, target, *thoughts in branches
            ],
        )
    )


DIMENSION_CATALOG = """
ABSTRACT DIMENSION CATALOG
==========================

Choose dimensions from this catalog based on Step 1 info sources.

CATEGORY A: SPECIFICATION VS BEHAVIOR
  - README/docs claim X, but code does Y
  - API documentation vs actual API behavior
  - Examples in docs that don't actually work
  Source pairs: Documentation <-> Code implementation

CATEGORY B: INTERFACE CONTRACT INTEGRITY
  - Type definitions vs actual runtime values
  - Schema definitions vs validation behavior
  - Function signatures vs docstrings
  Source pairs: Type/Schema definitions <-> Runtime behavior

CATEGORY C: CROSS-REFERENCE CONSISTENCY
  - Same concept described differently in different docs
  - Numeric constants/limits stated inconsistently
  - Intra-document contradictions
  Source pairs: Document <-> Document

CATEGORY D: TEMPORAL CONSISTENCY (Staleness)
  - Outdated comments referencing removed code
  - TODO/FIXME comments for completed work
  - References to renamed/moved files
  Source pairs: Historical references <-> Current state

CATEGORY E: ERROR HANDLING CONSISTENCY
  - Documented error codes vs actual error responses
  - Exception handling docs vs throw/catch behavior
  Source pairs: Error documentation <-> Error implementation

CATEGORY F: CONFIGURATION & ENVIRONMENT
  - Documented env vars vs actual env var usage
  - Default values in docs vs defaults in code
  Source pairs: Config documentation <-> Config handling code

CATEGORY G: AMBIGUITY & UNDERSPECIFICATION
  - Vague statements that could be interpreted multiple ways
  - Missing thresholds, limits, or parameters
  - Implicit assumptions not stated explicitly
  Detection method: Ask "could two people read this differently?"

CATEGORY H: POLICY & CONVENTION COMPLIANCE
  - Architectural decisions (ADRs) violated by implementation
  - Style guide rules not followed in code
  - "We don't do X" statements violated in codebase
  Source pairs: Policy documents <-> Implementation patterns

CATEGORY I: COMPLETENESS & DOCUMENTATION GAPS
  - Public API endpoints with no documentation
  - Functions/classes with no docstrings
  - Magic values/constants without explanation
  Detection method: Find code constructs, check if docs exist

CATEGORY J: COMPOSITIONAL CONSISTENCY
  - Claims individually valid but jointly impossible
  - Numeric constraints that contradict when combined
  - Configuration values that create impossible states
  - Timing/resource constraints that cannot all be satisfied
  Detection method: Gather related claims, compute implications, check for contradiction
  Example: timeout=30s, retries=10, max_duration=60s -> 30*10=300 != 60  # noqa: RUF003

CATEGORY K: IMPLICIT CONTRACT INTEGRITY
  - Names/identifiers promise behavior the code doesn't deliver
  - Function named validateX() that doesn't actually validate
  - Error messages that misrepresent the actual error
  - Module/package names that don't match contents
  - Log messages that lie about what happened
  Detection method: Parse names semantically, infer promise, compare to behavior
  Note: LLMs are particularly susceptible to being misled by names

CATEGORY L: DANGLING SPECIFICATION REFERENCES
  - Entity A references entity B, but B is never defined anywhere
  - FK references table that has no schema (e.g., api_keys.tenant_id but no tenants table)
  - UI/API mentions endpoints or types that are not specified
  - Schema field references enum or type with no definition
  Detection method:
    1. Extract DEFINED entities (tables, APIs, types, enums) with locations
    2. Extract REFERENCED entities (FKs, type usages, API calls) with locations
    3. Report: referenced but not defined = dangling reference
  Source pairs: Any specification -> Cross-file entity registry
  Note: Distinct from I (code-without-docs). L is SPEC-without-SPEC.

CATEGORY M: INCOMPLETE SPECIFICATION DEFINITIONS
  - Entity is defined but missing components required for implementation
  - Table schema documented but missing fields that other docs reference
  - API endpoint defined but missing request/response schema
  - Proto/schema has fields but lacks types others expect
  Detection method:
    1. For each defined entity, extract CLAIMED components
    2. Cross-reference with EXPECTED components from consuming docs
    3. Report: expected but not claimed = incomplete definition
  Source pairs: Definition document <-> Consumer documents
  Example: rules table shows (id, name, enabled) but API doc expects 'expression' field

SELECTION RULES:
- Select ALL categories relevant to Step 1 info sources
- Typical selection is 5-8 dimensions
- G, H, I, K are especially relevant for LLM-assisted coding
- J requires cross-referencing multiple claims (more expensive)
- L, M are critical for design-phase docs and specs-to-be-implemented
  Select when docs describe systems that need to be built
"""


def format_incoherence_output(step, phase, agent_type, guidance, thoughts=""):
    """Format output using AST builder API."""
    parts = []
    title = f"INCOHERENCE [{phase}] [{agent_type}]"
    parts.append(
        render_step_header(
            StepHeaderNode(
                title=title,
                script="incoherence",
                step=step,
            )
        )
    )
    parts.append("")

    if thoughts:
        parts.append(f"<context>\n{thoughts}\n</context>")
        parts.append("")

    if step == 1:
        parts.append("""<xml_format_mandate>
Do the action in <current_action>, then run the <invoke_after> command. When
<invoke_after> holds <branch> elements, run the command of the branch whose
"when" condition holds.
</xml_format_mandate>""")
        parts.append("")

    parts.append(render_current_action(CurrentActionNode(guidance["actions"])))
    parts.append("")

    next_text = guidance.get("next", "")
    is_workflow_complete = (
        step >= WORKFLOW.total_steps or next_text.strip().upper() == "WORKFLOW COMPLETE."
    )
    is_subagent_terminal = "SUB-AGENT TASK COMPLETE" in next_text.upper()

    if is_workflow_complete:
        parts.append("WORKFLOW COMPLETE - Present report to user.")
    elif is_subagent_terminal:
        parts.append("SUB-AGENT TASK COMPLETE - Return results to parent agent.")
    elif branches := guidance.get("branches"):
        parts.append(_render_branches(branches))
    else:
        target = guidance.get("next_step") or step + 1
        parts.append(render_invoke_after(InvokeAfterNode(cmd=_next_step_cmd(target))))
        if next_text:
            parts.append(f"NEXT: {next_text}")

    return "\n".join(parts)


STEPS = {
    1: {
        "title": "CODEBASE SURVEY",
        "actions": [
            "CODEBASE SURVEY",
            "",
            "Gather MINIMAL context (README first 50 lines, CLAUDE.md, dir listing).",
            "Do NOT read detailed docs, source code, configs, or tests.",
            "",
            "Identify: codebase type, primary language, doc locations, info source types",
            "(README, API docs, comments, types, configs, schemas, ADRs, style guides, tests)",
        ],
    },
    2: {
        "title": "DIMENSION SELECTION",
        "actions": [
            "DIMENSION SELECTION",
            "",
            "Select from catalog (A-M) based on Step 1 info sources.",
            "Do NOT read files or create domain-specific dimensions.",
            "",
            DIMENSION_CATALOG,
            "",
            "Output: Selected dimensions with one-line rationale each.",
        ],
    },
    3: {
        "title": "EXPLORATION DISPATCH",
        "actions": [
            "EXPLORATION DISPATCH",
            "",
            "Launch one agent per dimension (subagent_type='Explore', model='haiku').",
            parallel_constraint("N"),
            "",
            "AGENT PROMPT:",
            "  DIMENSION: {letter} - {name}. DESCRIPTION: {from_catalog}",
            _invoke_line(f'uv run python -m {MODULE_PATH} --step-number 4 --thoughts \\"Dimension: {{letter}}\\"'),
        ],
        "next": "After all agents complete, run the <invoke_after> command.",
        "next_step": 7,
    },
    4: {
        "title": "BROAD SWEEP [SUB-AGENT]",
        "actions": [
            "BROAD SWEEP [SUB-AGENT]",
            "",
            "Cast WIDE NET. Prioritize recall over precision. Your dimension is in --thoughts.",
            "",
            "SEARCH: docs/, README, src/, configs, schemas, types, tests.",
            "",
            "FOR L/M DIMENSIONS: Build entity registry first:",
            "  - DEFINED: tables, endpoints, types (entity_name, file:line, components)",
            "  - REFERENCED: FKs, type usages, API calls (entity_name, file:line)",
            "  - Cross-ref: referenced-not-defined=L, defined-but-incomplete=M",
            "",
            "PER FINDING: Location A, Location B, conflict, confidence (low OK).",
            "Bias: Report more. Track searched locations.",
        ],
    },
    5: {
        "title": "COVERAGE CHECK [SUB-AGENT]",
        "actions": [
            "COVERAGE CHECK [SUB-AGENT]",
            "",
            "Identify GAPS: unexplored dirs, skipped file types, unchecked modules.",
            "Diversity check: all findings same dir/type? Check both docs AND code.",
            "",
            "Output: each gap with the specific files/patterns to search next.",
        ],
    },
    6: {
        "title": "GAP-FILL EXPLORATION [SUB-AGENT]",
        "actions": [
            "GAP-FILL EXPLORATION [SUB-AGENT]",
            "",
            "Search every location on the gap list.",
            "Try: tests, examples, scripts/, negations ('not', 'deprecated'), TODOs/FIXMEs.",
            "",
            "Record new findings: Location A, Location B, conflict, confidence.",
            "",
            "Output format:",
            "  DIMENSION {letter} | TOTAL: N | AREAS SEARCHED: [list]",
            "  FINDING 1: A=[file:line] B=[file:line] Conflict=[desc] Confidence=[h/m/l]",
            "  ...",
            "",
            "Include ALL findings, original and new. The parent deduplicates them.",
        ],
        "next": "Output formatted results. Sub-agent task complete.",
    },
    7: {
        "title": "SYNTHESIZE CANDIDATES",
        "actions": [
            "SYNTHESIZE CANDIDATES",
            "",
            "1. Merge candidates that cite the same pair of locations (same A and B).",
            "2. Output: C1, C2... with location, summary, dimension",
            "",
            "Pass every remaining candidate to step 8; do not drop any for low confidence.",
        ],
    },
    8: {
        "title": "DEEP-DIVE DISPATCH",
        "actions": [
            "DEEP-DIVE DISPATCH",
            "",
            "Launch one agent per candidate (subagent_type='general-purpose', model='sonnet').",
            "With more than 20 candidates, dispatch them in batches of at most 20, each batch after the previous one returns; N below is the size of the current batch.",
            parallel_constraint("N"),
            "",
            "AGENT PROMPT:",
            "  CANDIDATE: {id} at {location} | DIMENSION: {letter} - {name}",
            "  Claimed: {summary}",
            _invoke_line(f'uv run python -m {MODULE_PATH} --step-number 9 --thoughts \\"Verifying: {{id}}\\"'),
        ],
        "next": "After all agents complete, run the <invoke_after> command.",
        "next_step": 10,
    },
    9: {
        "title": "DEEP-DIVE EXPLORATION [SUB-AGENT]",
        "actions": [
            "DEEP-DIVE EXPLORATION [SUB-AGENT]",
            "",
            "1. Read both sources with 100+ lines context, extract exact quotes",
            "2. Analyze by dimension:",
            "   - A,B,C,E,F,J,K (contradiction): genuinely conflicting? -> TRUE_INCOHERENCE",
            "   - G (ambiguity): two readers interpret differently? -> SIGNIFICANT_AMBIGUITY",
            "   - H (policy): orphaned ref -> DOC_GAP, active violation -> TRUE_INCOHERENCE",
            "   - I (completeness): missing needed info? -> DOCUMENTATION_GAP",
            "   - L,M (omission): undefined/incomplete entity? -> SPECIFICATION_GAP",
            "",
            "3. Verdict: TRUE_INCOHERENCE | SIGNIFICANT_AMBIGUITY | DOCUMENTATION_GAP |",
            "   SPECIFICATION_GAP | FALSE_POSITIVE",
            "",
            "Output format:",
            "  CANDIDATE: {id} | VERDICT: {verdict} | SEVERITY: {c/h/m/l}",
            '  SOURCE A: {file}:{line} "{quote}" Claims: {claim}',
            '  SOURCE B: {file}:{line} "{quote}" Claims: {claim}',
            "  ANALYSIS: {why conflict} | RECOMMENDATION: {fix}",
        ],
        "next": "Output formatted result. Sub-agent task complete.",
    },
    10: {
        "title": "VERDICT ANALYSIS",
        "actions": [
            "VERDICT ANALYSIS",
            "",
            "1. Quality check: each non-FALSE_POSITIVE has exact quotes",
            "2. Deduplicate: merge identical source pairs, keep richer analysis",
            "3. Group related issues:",
            "   - SHARED ROOT CAUSE: same file, same outdated doc, same config",
            "   - SHARED THEME: same dimension, same concept, same fix type",
            "   Output: G1, G2... with member issues, relationship, unified resolution",
        ],
    },
    11: {
        "title": "PREPARE RESOLUTION BATCHES",
        "actions": [
            "PREPARE RESOLUTION BATCHES",
            "",
            "Batch rules (priority order, max 4 per batch):",
            "1. Group-based: issues sharing G1/G2/... together",
            "2. File-based: ungrouped issues affecting same file",
            "3. Singletons: remaining unrelated issues",
            "",
            "Per batch output: Issues, theme/file, group suggestion (if applicable)",
            "",
            "Per issue output:",
            "  ISSUE {id}: {title} | Severity | Dimension | Group",
            '  Source A: {file}:{line} "{quote max 10 lines}" Claims: ...',
            '  Source B: {file}:{line} "{quote max 10 lines}" Claims: ...',
            "  Analysis: {conflict} | Suggestions: 1. {action} 2. {alt action}",
            "",
            "Suggestions must use ACTUAL values (e.g., 'Update to 60s' not 'match code').",
        ],
    },
    12: {
        "title": "PRESENT RESOLUTION BATCH",
        "actions": [
            "PRESENT RESOLUTION BATCH",
            "",
            "Use AskUserQuestion. Check <context> for 'MODE: individual'.",
            "Edge cases: empty batch=skip, single-member group=individual, quotes>10 lines=truncate.",
            "",
            "GROUP BATCH (2+ members, no 'MODE: individual' in <context>): ask group question only",
            "  header: 'G{n}', options: unified_suggestion | 'Resolve individually' | 'Skip all'",
            "",
            "NON-GROUP, or 'MODE: individual' in <context>: ask per-issue questions",
            "  header: 'I{n}', include: file:line, quotes, claims, analysis",
            "  options: suggestion_1 | suggestion_2 | 'Skip'",
            "",
            "Suggestions must use ACTUAL values (e.g., 'Update to 60s' not 'match code').",
        ],
        "next": "After AskUserQuestion returns, run the <invoke_after> command.",
    },
    13: {
        "title": "RESOLUTION LOOP CONTROLLER",
        "actions": [
            "RESOLUTION LOOP CONTROLLER",
            "",
            "Process response:",
            "  G{n} response: unified -> record for all; 'individually' -> record none (asked per issue next);",
            "                 'skip all' -> NO_RESOLUTION for all; 'other' -> record custom for all",
            "  I{n} responses: record each resolution or NO_RESOLUTION",
            "",
            "After the last batch, if every resolution is NO_RESOLUTION, output 'No issues selected' and stop.",
        ],
        "branches": [
            ("the responses select 'Resolve individually' for a group", 12, "MODE: individual"),
            ("no response selects 'Resolve individually' and more batches remain", 12),
            ("no response selects 'Resolve individually' and all batches are complete", 14),
        ],
    },
    14: {
        "title": "PLAN DISPATCH",
        "actions": [
            "PLAN DISPATCH",
            "",
            "Read the collected resolutions; skip NO_RESOLUTION.",
            "",
            "1. Target files: use Source A/B as hints, resolution may specify",
            "2. Agent types: .md/.rst/.txt -> technical-writer, code/config -> developer",
            "3. Group by file: multiple issues same file -> one agent",
            "4. Waves: different files parallel, conflicts sequential",
            "",
            "Output: FILE GROUPS (file, issues, agent) + DISPATCH PLAN (waves)",
        ],
    },
    15: {
        "title": "RECONCILE DISPATCH",
        "actions": [
            "RECONCILE DISPATCH",
            "",
            "Launch agents for current wave (Wave 1 first time, next wave after step 17).",
            "Agent types: developer (code/config) or technical-writer (docs).",
            "",
            "AGENT PROMPT:",
            "  TARGET: {file} | ISSUES: {ids}",
            "  Per issue: type, severity, sources, analysis, resolution_text",
            _invoke_line(f'uv run python -m {MODULE_PATH} --step-number 16 --thoughts \\"FILE: {{file}}\\"'),
            "",
            parallel_constraint("N"),
        ],
        "next": "After all wave agents complete, run the <invoke_after> command.",
        "next_step": 17,
    },
    16: {
        "title": "RECONCILE APPLY [SUB-AGENT]",
        "actions": [
            "RECONCILE APPLY [SUB-AGENT]",
            "",
            "For each resolution: locate target, apply change, verify it addresses the issue.",
            "Batched: apply in order, watch for conflicts.",
            "Bias: apply the resolution, interpret charitably, skip rarely.",
            "",
            "Output, per issue: ISSUE: {id} | STATUS: RESOLVED|SKIPPED | FILE: {path}",
            "  If RESOLVED: CHANGE: {brief description}",
            "  If SKIPPED: REASON: {why}",
        ],
        "next": "Output formatted result(s). Sub-agent task complete.",
    },
    17: {
        "title": "RECONCILE COLLECT",
        "actions": [
            "RECONCILE COLLECT",
            "",
            "Collect wave results: per agent, issues handled, status, change/reason.",
            "Check the dispatch plan for remaining waves.",
        ],
        "branches": [
            ("the dispatch plan has more waves", 15),
            ("all waves are complete", 18),
        ],
    },
    18: {
        "title": "PRESENT REPORT",
        "actions": [
            "PRESENT REPORT",
            "",
            "Output inline (no file):",
            "  Summary: detected N, resolved M, skipped K",
            "  Table: ID | Severity | Status | Summary (~40 chars)",
            "",
            "List ALL issues. RESOLVED or SKIPPED with reason.",
        ],
        "next": "WORKFLOW COMPLETE.",
    },
}


def generic_step_handler(step_info, **kwargs):
    """Generic handler for standard steps."""
    return {
        "actions": step_info.get("actions", []),
        "next": step_info.get("next", ""),
        "next_step": step_info.get("next_step"),
        "branches": step_info.get("branches"),
    }


STEP_HANDLERS = dict.fromkeys(STEPS, generic_step_handler)


def get_step_guidance(step_number, total_steps):
    step_info = STEPS.get(step_number, {})
    handler = STEP_HANDLERS.get(step_number, generic_step_handler)
    return handler(step_info, total_steps=total_steps)


WORKFLOW = Workflow(
    "incoherence",
    StepDef(
        id="survey",
        title="Codebase Survey",
        actions=get_step_guidance(1, len(STEPS))["actions"],
    ),
    StepDef(
        id="dimension_selection",
        title="Dimension Selection",
        actions=get_step_guidance(2, len(STEPS))["actions"],
    ),
    StepDef(
        id="exploration_dispatch",
        title="Exploration Dispatch",
        actions=get_step_guidance(3, len(STEPS))["actions"],
    ),
    StepDef(
        id="broad_sweep",
        title="Broad Sweep [SUB-AGENT]",
        actions=get_step_guidance(4, len(STEPS))["actions"],
    ),
    StepDef(
        id="coverage_check",
        title="Coverage Check [SUB-AGENT]",
        actions=get_step_guidance(5, len(STEPS))["actions"],
    ),
    StepDef(
        id="gap_fill",
        title="Gap-Fill Exploration [SUB-AGENT]",
        actions=get_step_guidance(6, len(STEPS))["actions"],
    ),
    StepDef(
        id="synthesize_candidates",
        title="Synthesize Candidates",
        actions=get_step_guidance(7, len(STEPS))["actions"],
    ),
    StepDef(
        id="deep_dive_dispatch",
        title="Deep-Dive Dispatch",
        actions=get_step_guidance(8, len(STEPS))["actions"],
    ),
    StepDef(
        id="deep_dive_exploration",
        title="Deep-Dive Exploration [SUB-AGENT]",
        actions=get_step_guidance(9, len(STEPS))["actions"],
    ),
    StepDef(
        id="verdict_analysis",
        title="Verdict Analysis",
        actions=get_step_guidance(10, len(STEPS))["actions"],
    ),
    StepDef(
        id="prepare_resolution_batches",
        title="Prepare Resolution Batches",
        actions=get_step_guidance(11, len(STEPS))["actions"],
    ),
    StepDef(
        id="present_batch",
        title="Present Resolution Batch",
        actions=get_step_guidance(12, len(STEPS))["actions"],
    ),
    StepDef(
        id="resolution_loop",
        title="Resolution Loop Controller",
        actions=get_step_guidance(13, len(STEPS))["actions"],
    ),
    StepDef(
        id="plan_dispatch",
        title="Plan Dispatch",
        actions=get_step_guidance(14, len(STEPS))["actions"],
    ),
    StepDef(
        id="reconcile_dispatch",
        title="Reconcile Dispatch",
        actions=get_step_guidance(15, len(STEPS))["actions"],
    ),
    StepDef(
        id="reconcile_apply",
        title="Reconcile Apply [SUB-AGENT]",
        actions=get_step_guidance(16, len(STEPS))["actions"],
    ),
    StepDef(
        id="reconcile_collect",
        title="Reconcile Collect",
        actions=get_step_guidance(17, len(STEPS))["actions"],
    ),
    StepDef(
        id="present_report",
        title="Present Report",
        actions=get_step_guidance(18, len(STEPS))["actions"],
    ),
    description="Multi-phase incoherence detection and resolution workflow",
    validate=False,
)


def main(step_number: int | None = None):
    """Entry point with parameter annotations for testing framework.

    Note: Parameters have defaults because actual values come from argparse.
    The annotations are metadata for the testing framework.
    """
    parser = argparse.ArgumentParser(description="Incoherence Detector")
    parser.add_argument("--step-number", type=int, required=True, choices=range(1, len(STEPS) + 1))
    parser.add_argument(
        "--thoughts", type=str, default="", help="Routing value from a printed dispatch or loop command"
    )
    args = parser.parse_args()

    guidance = get_step_guidance(args.step_number, WORKFLOW.total_steps)

    # Determine agent type and phase
    # Detection sub-agents: exploration and deep-dive
    if args.step_number in [4, 5, 6, 9]:
        agent_type = "SUB-AGENT"
        phase = "DETECTION"
    # Application sub-agents: apply resolution
    elif args.step_number == 16:
        agent_type = "SUB-AGENT"
        phase = "APPLICATION"
    # Detection parent
    elif args.step_number <= 10:
        agent_type = "PARENT"
        phase = "DETECTION"
    # Resolution parent
    elif args.step_number <= 13:
        agent_type = "PARENT"
        phase = "RESOLUTION"
    # Application parent
    else:
        agent_type = "PARENT"
        phase = "APPLICATION"

    output = format_incoherence_output(
        args.step_number, phase, agent_type, guidance, thoughts=args.thoughts
    )
    print(output)


if __name__ == "__main__":
    main()
