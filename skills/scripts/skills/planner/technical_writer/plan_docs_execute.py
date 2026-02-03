#!/usr/bin/env python3
"""Plan docs execution - first-time documentation workflow.

8-step workflow for technical-writer sub-agent:
  1. Task Description (context display, JSON-IR architecture)
  2. Extract Planning Context (decision log, constraints, risks)
  3. Temporal Contamination Review (5 detection categories)
  4. Prioritization and Doc Tiers (HIGH/MEDIUM/LOW, Tiers 3-6)
  5. Comment Injection via CLI (WHY comments, decision_refs)
  6. README Synthesis (invisible knowledge -> READMEs)
  7. Diagram Rendering (ASCII diagrams from graph specs)
  8. Final Validation (validate plan.json completeness)

Scope: Documentation quality only -- capturing planning knowledge in
documentation fields. This phase does NOT modify code logic.

In scope (per conventions/documentation.md):
- Invisible knowledge coverage: decisions -> inline_comments/function_blocks
- Temporal contamination removal from documentation strings
- WHY-not-WHAT quality in comments
- Structural completeness of documentation{} fields
- README synthesis from invisible_knowledge

Out of scope (handled by Developer in plan-code phase):
- Code correctness, compilation, types
- Diff content and format
- Logic changes

This is the EXECUTE script for first-time documentation.
For QR fix mode, see plan_docs_qr_fix.py.
Router (plan_docs.py) dispatches to appropriate script.
"""

from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention
from skills.planner.shared.resources import (
    STATE_DIR_ARG_REQUIRED,
    get_context_path,
    render_context_file,
    validate_state_dir_requirement,
)
from skills.planner.shared.temporal_detection import format_as_prose, format_actions


STEPS = {
    1: "Task Description",
    2: "Extract Planning Context",
    3: "Temporal Contamination Review",
    4: "Prioritization and Documentation Tiers",
    5: "Comment Injection via CLI",
    6: "README Synthesis",
    7: "Diagram Rendering",
    8: "Final Validation",
}


def get_step_guidance(
    step: int, module_path: str = None, **kwargs) -> dict:
    """Return guidance for the given step."""
    MODULE_PATH = module_path or "skills.planner.technical_writer.plan_docs_execute"
    state_dir = kwargs.get("state_dir", "")

    if step == 1:
        validate_state_dir_requirement(step, state_dir)
        context_file = get_context_path(state_dir) if state_dir else None
        context_display = render_context_file(context_file) if context_file else ""
        banner = render(
            W.el("state_banner", checkpoint="TW-PLAN-SCRUB", iteration="1", mode="work").build(),
            XMLRenderer()
        )

        actions = []
        if context_display:
            actions.extend([
                "PLANNING CONTEXT (from orchestrator):",
                "",
                context_display,
                "",
            ])
        actions.extend([
            banner,
            "",
            "TYPE: PLAN_DOCS (JSON-IR)",
            "",
            "TASK: Enrich plan.json with documentation.",
            "",
            "JSON-IR ARCHITECTURE:",
            "  plan.json contains code_changes[] populated by Developer.",
            "  Your job: fill documentation{} and why_comments.",
            "  Use CLI commands - DO NOT edit plan.json directly.",
            "",
            "WORKFLOW:",
            "  Steps 1-6: Enrich plan.json with documentation",
            "  Steps 7-8: Diagram rendering and final validation",
            "",
            "CLI COMMANDS (single invocation):",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
            "    --milestone M-001 --type module --content-file /tmp/mod.txt",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
            "    --milestone M-001 --type docstring --function func --content-file /tmp/doc.txt",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
            "    --milestone M-001 --type function_block --function func --content-file /tmp/fb.txt --decision-ref DL-001 --source invisible_knowledge",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
            "    --milestone M-001 --type inline --location 'func:line' --content-file /tmp/why.txt --decision-ref DL-001 --source decision_log",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-readme \\",
            "    --path src/module --content-file /tmp/readme.txt",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR validate --phase plan-docs",
            "",
            "BATCH MODE (preferred for multiple docs):",
            "",
            "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR batch '[",
            "    {\"method\": \"set-doc\", \"params\": {\"milestone\": \"M-001\", \"type\": \"module\", \"content_file\": \"/tmp/mod.txt\"}, \"id\": 1},",
            "    {\"method\": \"set-doc\", \"params\": {\"milestone\": \"M-001\", \"type\": \"docstring\", \"function\": \"check\", \"content_file\": \"/tmp/doc.txt\"}, \"id\": 2},",
            "    {\"method\": \"set-doc\", \"params\": {\"milestone\": \"M-001\", \"type\": \"function_block\", \"function\": \"process\", \"content_file\": \"/tmp/fb.txt\", \"decision_ref\": \"DL-001\"}, \"id\": 3},",
            "    {\"method\": \"set-doc\", \"params\": {\"milestone\": \"M-001\", \"type\": \"inline\", \"location\": \"func:42\", \"content_file\": \"/tmp/why.txt\", \"decision_ref\": \"DL-001\"}, \"id\": 4}",
            "  ]'",
            "",
            "Read plan.json now. Identify:",
            "  - planning_context.decisions entries",
            "  - milestones with code_changes",
            "  - invisible_knowledge section",
        ])

        return {
            "title": STEPS[1],
            "actions": actions,
            "next": f"python3 -m {MODULE_PATH} --step 2 --state-dir {state_dir}",
        }

    elif step == 2:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": STEPS[2],
            "actions": [
                "EXTRACT from plan.json planning_context:",
                "",
                "Read plan.json and extract:",
                "  cat $STATE_DIR/plan.json | jq '.planning_context'",
                "",
                "1. DECISION LOG entries:",
                "   - WHY each architectural choice was made",
                "   - What alternatives were rejected and why",
                "   - Specific values and their sensitivity analysis",
                "",
                "2. CONSTRAINTS that shaped the design:",
                "   - Technical limitations",
                "   - Compatibility requirements",
                "   - Performance targets",
                "",
                "3. KNOWN RISKS and mitigations:",
                "   - What could go wrong",
                "   - How the design addresses each risk",
                "",
                "List decision IDs for reference:",
                "  python3 -m skills.planner.cli.plan list-decisions",
                "",
                "Write out your CONTEXT SUMMARY before proceeding:",
                "  CONTEXT SUMMARY:",
                "  - Key decisions: [list from decision_log with IDs]",
                "  - Rejected alternatives: [list with reasons]",
                "  - Constraints: [list]",
                "  - Risks addressed: [list]",
                "",
                "These decision IDs are your SOURCE for WHY comments.",
                "Comments you add MUST reference these decision_refs.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 3{state_dir_arg}",
        }

    elif step == 3:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        temporal_resource = get_convention("temporal.md")
        resource_block = render(
            W.el("resource", TextNode(temporal_resource), name="temporal-contamination", purpose="plan-scrub").build(),
            XMLRenderer()
        )

        return {
            "title": STEPS[3],
            "actions": [
                "AUTHORITATIVE REFERENCE FOR TEMPORAL CONTAMINATION:",
                "",
                resource_block,
                "",
                "SCAN all existing comments in Code Changes sections.",
                "",
                format_as_prose(),
                "",
                "ACTIONS:",
                format_actions(),
                "",
                "CODE PRESENCE CHECK:",
                "  For each implementation milestone (modifies source files):",
                "  - Does it have Code Changes with unified diffs?",
                "  - If NO: Stop and report escalation (see step 6)",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 4{state_dir_arg}",
        }

    elif step == 4:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": STEPS[4],
            "actions": [
                "PRIORITIZE by uncertainty (scrub HIGH before MEDIUM, skip LOW):",
                "",
                "| Priority | Code Pattern                 | WHY Question           |",
                "| -------- | ---------------------------- | ---------------------- |",
                "| HIGH     | Multiple valid approaches    | Why this approach?     |",
                "| HIGH     | Thresholds, timeouts, limits | Why these values?      |",
                "| HIGH     | Error handling paths         | Recovery strategy?     |",
                "| HIGH     | External system interactions | What assumptions?      |",
                "| MEDIUM   | Non-standard pattern usage   | Why deviate from norm? |",
                "| MEDIUM   | Performance-critical paths   | Why this optimization? |",
                "| LOW      | Boilerplate/established      | Skip unless unusual    |",
                "| LOW      | Simple CRUD operations       | Skip unless unusual    |",
                "",
                "CHECK MILESTONE FLAGS (if present):",
                "  - `needs-rationale`: Every non-obvious element needs WHY comment",
                "  - `complex-algorithm`: Add Tier 5 algorithm block even if simple",
                "",
                "DOCUMENTATION TIERS (verify in Code Changes):",
                "",
                "| Tier | Location           | Purpose                         |",
                "| ---- | ------------------ | ------------------------------- |",
                "| 3    | Top of new files   | Module-level: what + why exists |",
                "| 4    | Above functions    | Docstrings: ALL functions       |",
                "| 5    | Complex algorithms | Strategy, invariants, edge cases|",
                "| 6    | Within code lines  | Specific WHY (never WHAT)       |",
                "",
                "CRITICAL: Document ALL functions (public AND private).",
                "Helper docstrings: [what it does] + [when to call it]",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 5{state_dir_arg}",
        }

    elif step == 5:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": STEPS[5],
            "actions": [
                "INJECT WHY comments for HIGH priority code using CLI:",
                "",
                "For each code_change needing WHY comments:",
                "  1. Find Decision Log entry (DL-XXX) that explains the choice",
                "  2. Write comment to temp file",
                "  3. Add via set-doc with function_block or inline type:",
                "     python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
                "       --milestone M-001 --type function_block --function func \\",
                "       --content-file /tmp/fb.txt --decision-ref DL-001 --source invisible_knowledge",
                "     python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
                "       --milestone M-001 --type inline --location 'func:line' \\",
                "       --content-file /tmp/why.txt --decision-ref DL-001 --source decision_log",
                "",
                "TRANSFORM Decision Log -> Code Comment:",
                "  Decision Log: 'Polling | 30% webhook failure -> need fallback'",
                "  Code Comment: // Polling: 30% webhook delivery failures observed",
                "",
                "Add documentation to milestones:",
                "  # Module comment (write to temp file first)",
                "  echo 'Rate limiting module using sliding window...' > /tmp/module.txt",
                "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
                "    --milestone M-001 --type module --content-file /tmp/module.txt",
                "",
                "  # Function docstring",
                "  echo 'Check if request is within rate limit.' > /tmp/docstring.txt",
                "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-doc \\",
                "    --milestone M-001 --type docstring --function check_rate_limit --content-file /tmp/docstring.txt",
                "",
                "PLANNING CONTEXT GAP PROTOCOL:",
                "  If code needs WHY but Decision Log lacks rationale:",
                "  1. Do NOT block -- proceed without comment",
                "  2. Record gap for final output (see step 6)",
                "  3. Continue with remaining work",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 6{state_dir_arg}",
        }

    elif step == 6:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": STEPS[6],
            "actions": [
                "README SYNTHESIS FROM INVISIBLE KNOWLEDGE",
                "",
                "Read invisible_knowledge from plan.json:",
                "  cat $STATE_DIR/plan.json | jq '.invisible_knowledge'",
                "",
                "IDENTIFY directories needing READMEs:",
                "  - Directories containing multiple related files",
                "  - Directories with cross-cutting architecture concepts",
                "  - Module roots with non-obvious organization",
                "",
                "SYNTHESIZE README content from invisible_knowledge:",
                "  - System architecture details",
                "  - Invariants spanning multiple files",
                "  - Tradeoffs affecting directory scope",
                "",
                "CONTENT TEST (apply before writing):",
                "  Ask: 'Could a developer learn this by reading source files?'",
                "  - If YES: delete content (redundant with code)",
                "  - If NO: keep content (invisible knowledge)",
                "",
                "ADD entries via set-readme:",
                "  echo 'Cross-cutting architecture content...' > /tmp/readme.txt",
                "  python3 -m skills.planner.cli.plan --state-dir $STATE_DIR set-readme \\",
                "    --path src/module --content-file /tmp/readme.txt",
                "",
                "SKIP if invisible_knowledge section is empty or contains no directory-level concepts.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 7{state_dir_arg}",
        }

    elif step == 7:
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": STEPS[7],
            "actions": [
                "RENDER DIAGRAMS TO ASCII",
                "",
                "Read plan.json diagram_graphs[]. For each diagram with ascii_render=null:",
                "",
                "1. ANALYZE graph structure:",
                "   - Count nodes (target: 3-7, prevents visual overload)",
                "   - Identify edge direction majority (vertical vs horizontal layout)",
                "   - Note any cycles or hub nodes (affects spacing requirements)",
                "",
                "2. SELECT layout:",
                "   - architecture: vertical stack or horizontal flow",
                "   - dataflow: left-to-right pipeline",
                "   - state: grid or radial based on transition count",
                "   - sequence: vertical timeline",
                "",
                "3. RENDER ASCII:",
                "   - Max width 80 chars (terminal compatibility)",
                "   - Box syntax: +--+, |, - (universal ASCII)",
                "   - Arrow syntax: v, ^, <, >, -->, <-- (directional clarity)",
                "   - Label edges inline or below arrow (readability over density)",
                "",
                "4. WRITE render:",
                "   echo '<ascii content>' > /tmp/diagram.txt",
                f"   python3 -m skills.planner.cli.plan --state-dir {state_dir} \\",
                "     set-diagram-render --diagram DIAG-001 --content-file /tmp/diagram.txt",
                "",
                "EXAMPLE (architecture type):",
                "```",
                "+------------------+",
                "| Client           |",
                "+------------------+",
                "        |",
                "        | gRPC",
                "        v",
                "+------------------+",
                "| Server           |",
                "+------------------+",
                "```",
                "",
                "SKIP if diagram_graphs is empty.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 8{state_dir_arg}",
        }

    elif step == 8:
        return {
            "title": STEPS[8],
            "actions": [
                "FINAL VALIDATION",
                "",
                "VALIDATE plan.json documentation completeness:",
                f"  python3 -m skills.planner.cli.plan validate --phase plan-docs --state-dir {state_dir}",
                "",
                "VERIFY COVERAGE:",
                "",
                "Tiers 3-4 (structure):",
                "  [ ] Every new file has module_comment in documentation{}",
                "  [ ] ALL functions have docstrings[] entries",
                "  [ ] Helper docstrings: [what it does] + [when to call it]",
                "",
                "Tiers 2 + 5-6 (understanding):",
                "  [ ] Every non-trivial function has function_blocks[] entry",
                "  [ ] Every non-obvious line has inline_comment",
                "  [ ] No comment states WHAT the code does",
                "",
                "Temporal contamination (in ALL string fields):",
                "  [ ] No change-relative (Added, Replaced, Changed, Now uses)",
                "  [ ] No baseline references (Previously, Instead of, Replaces)",
                "  [ ] No location directives (After X, Before Y, Insert)",
                "  [ ] No planning artifacts (TODO, Will, Planned, Temporary)",
                "",
                "When complete, output: PASS",
            ],
            "next": "",
        }

    return {"error": f"Invalid step {step}"}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "Plan-Docs-Execute: Technical writer documentation workflow",
        extra_args=[STATE_DIR_ARG_REQUIRED],
    )
