#!/usr/bin/env python3
"""
Refactor Explore - Dimension-specific exploration for refactoring analysis.

Two-step workflow per dimension:
  1. Exploration - Search for issues using dimension-specific heuristics
  2. Synthesis   - Format findings with severity assessment

Usage:
    python3 explore.py --step 1 --total-steps 2 --dimension naming
"""

import argparse
import os
import sys


# =============================================================================
# Dimension Definitions
# =============================================================================

DIMENSIONS = {
    "naming": {
        "title": "Naming & Semantics",
        "focus": "Names that mislead, obscure intent, or operate at wrong abstraction level",
        "heuristics": [
            "Names describing HOW not WHAT (e.g., loopOverItems vs processOrders)",
            "Verbs that lie (get that mutates, validate that parses)",
            "Synonym drift (userId, uid, id for same concept)",
            "Wrong abstraction level (impl details in public API names)",
            "Vague names (Manager, Handler, Utils, Helper, Data, Info)",
            "Negated booleans (isNotValid, disableFeature)",
        ],
        "detection_questions": [
            "What does this name tell me about WHAT it does vs HOW?",
            "If I only saw the name, would I guess its behavior correctly?",
            "Are there multiple names for the same concept in this file?",
            "Does the name match the abstraction level of its scope?",
        ],
        "examples": [
            ("processData()", "parseUserInput() -- names the domain concept"),
            ("handleStuff()", "validateAndRouteRequest() -- specific action"),
            ("mgr.doIt()", "orderProcessor.submitOrder() -- domain language"),
        ],
    },
    "extraction": {
        "title": "Extraction & Composition",
        "focus": "Code that resists change due to duplication, mixed responsibilities, or complexity",
        "heuristics": [
            "Duplicated logic (look for 3+ similar blocks)",
            "God functions (multiple unrelated responsibilities)",
            "Long parameter lists (4+ params often signal missing concept)",
            "Deep nesting (3+ levels of conditionals)",
            "Mixed abstraction levels in same function",
            "Boolean parameters that fork behavior",
        ],
        "detection_questions": [
            "If I fixed a bug here, where else would I need to fix it?",
            "Can I describe this function's purpose in one sentence?",
            "What would I name each distinct responsibility in this function?",
            "Could this parameter list be replaced with a single concept?",
        ],
        "examples": [
            ("100-line function", "Extract: validateInput(), processCore(), formatOutput()"),
            ("if debug: ... (50 lines)", "Extract: debugLog() called conditionally"),
            ("fn(a,b,c,d,e,f)", "fn(Config) where Config groups related params"),
        ],
    },
    "testability": {
        "title": "Testability",
        "focus": "Code that is difficult to test in isolation",
        "heuristics": [
            "Hard-coded dependencies (new Date(), database calls inline)",
            "Global state access",
            "Side effects mixed with computation",
            "Concrete class dependencies (no interfaces)",
            "Environment coupling (reads env vars, files directly)",
            "Time-dependent logic without injection",
        ],
        "detection_questions": [
            "Can I test this function without network/disk/database?",
            "What would I need to mock to test this in isolation?",
            "Does this function do computation AND side effects?",
            "Can I inject test doubles for all dependencies?",
        ],
        "examples": [
            ("datetime.now() inline", "Inject clock: fn(clock) -> clock.now()"),
            ("db.query() inside logic", "Separate: fetchData() then processData(data)"),
            ("reads os.environ directly", "Inject config: fn(config) not fn()"),
        ],
    },
    "types": {
        "title": "Type & Interface Design",
        "focus": "Missing domain concepts, primitive obsession, leaky abstractions",
        "heuristics": [
            "Primitive obsession (domain concepts as string/int)",
            "Missing value objects (money, dates, IDs passed as primitives)",
            "Stringly-typed data (JSON strings instead of typed objects)",
            "Leaky abstractions (callers must know implementation details)",
            "Inconsistent interfaces (similar operations, different signatures)",
            "Optional explosion (many nullable fields)",
        ],
        "detection_questions": [
            "What domain concepts are represented as primitives here?",
            "Would a type prevent an invalid state that's currently possible?",
            "Do callers need to know implementation details to use this?",
            "Are there validation rules repeated wherever this value is used?",
        ],
        "examples": [
            ("user_id: str", "UserId type with validation"),
            ("price: float", "Money(amount, currency) value object"),
            ("config: dict", "TypedConfig with defined fields"),
        ],
    },
    "errors": {
        "title": "Error Handling",
        "focus": "Inconsistent, swallowed, or poorly-located error handling",
        "heuristics": [
            "Swallowed exceptions (empty catch blocks)",
            "Generic catches (catch Exception, catch all)",
            "Errors at wrong level (low-level errors leak to callers)",
            "Inconsistent patterns (exceptions here, return codes there)",
            "Missing context (errors without operation/identifiers)",
            "Validation scattered (same checks in multiple places)",
        ],
        "detection_questions": [
            "What happens if this operation fails?",
            "Does the error message help diagnose the problem?",
            "Is error handling consistent across similar operations?",
            "Are errors caught at the right abstraction level?",
        ],
        "examples": [
            ("except: pass", "except SpecificError: log_and_handle()"),
            ("raise Error('failed')", "raise Error(f'order {id} failed: {reason}')"),
            ("return None on error", "return Result[T, Error] or raise"),
        ],
    },
    "modules": {
        "title": "Module Boundaries & Dependencies",
        "focus": "Circular dependencies, wrong cohesion, layer violations",
        "heuristics": [
            "Circular dependencies (A imports B imports A)",
            "Layer violations (domain imports infrastructure)",
            "Wrong cohesion (unrelated things grouped together)",
            "Missing facades (internals exposed directly)",
            "Dependency on implementation (not interface)",
            "God modules (too many responsibilities)",
        ],
        "detection_questions": [
            "Do changes in this module ripple to unrelated modules?",
            "Is there a clear direction to the dependency graph?",
            "Could I swap the implementation without changing callers?",
            "What would break if I moved this to a different module?",
        ],
        "examples": [
            ("models.py imports views.py", "Extract shared types to separate module"),
            ("service imports ORM directly", "service imports repository interface"),
            ("utils.py with 50 functions", "Split by domain: string_utils, date_utils"),
        ],
    },
    "modernization": {
        "title": "Modernization",
        "focus": "Outdated patterns, deprecated APIs, missed language features",
        "heuristics": [
            "Old iteration patterns (manual index loops vs for-each)",
            "Deprecated API usage (check language/framework docs)",
            "Missing language features (no destructuring, no pattern matching)",
            "Legacy patterns (callbacks vs async/await)",
            "Outdated idioms (string concatenation vs f-strings/templates)",
            "Manual null checks (vs optional chaining, null coalescing)",
        ],
        "detection_questions": [
            "Is there a newer language feature that simplifies this?",
            "Does this use deprecated APIs or patterns?",
            "Would a modern developer write it this way?",
            "Are there framework utilities that replace this manual code?",
        ],
        "examples": [
            ("for i in range(len(items))", "for item in items / enumerate()"),
            ("'%s %s' % (a, b)", "f'{a} {b}'"),
            (".then().catch()", "async/await"),
        ],
    },
    "architecture": {
        "title": "Architecture",
        "focus": "Wrong boundaries, scaling bottlenecks, structural constraints",
        "heuristics": [
            "Wrong component boundaries (features split awkwardly)",
            "Single points of failure (no fallback, no retry)",
            "Scaling bottlenecks (synchronous where async needed)",
            "Monolith patterns in distributed code (or vice versa)",
            "Missing abstraction layers (direct coupling everywhere)",
            "Configuration scattered (no central policy)",
        ],
        "detection_questions": [
            "Would adding a feature require touching many components?",
            "Can this component scale independently?",
            "Is there a clear separation between policy and mechanism?",
            "What would a 10x traffic increase break?",
        ],
        "examples": [
            ("Every service talks to DB directly", "Introduce repository layer"),
            ("Sync calls to external APIs", "Async with circuit breaker"),
            ("Config in 20 files", "Central config with environment overlay"),
        ],
    },
}


# =============================================================================
# XML Formatters (self-contained)
# =============================================================================


def format_step_header(step: int, total: int, title: str, dimension: str) -> str:
    """Render step header with dimension context."""
    return f'<step_header script="explore" step="{step}" total="{total}" dimension="{dimension}">{title}</step_header>'


def format_xml_mandate() -> str:
    """Return first-step guidance about XML format."""
    return """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>"""


def format_current_action(actions: list[str]) -> str:
    """Render current action block."""
    lines = ["<current_action>"]
    lines.extend(actions)
    lines.append("</current_action>")
    return "\n".join(lines)


def format_invoke_after(command: str) -> str:
    """Render invoke after block."""
    return f"<invoke_after>\n{command}\n</invoke_after>"


def format_heuristics(heuristics: list[str]) -> str:
    """Format heuristics as XML."""
    lines = ["<heuristics>"]
    for h in heuristics:
        lines.append(f"  <heuristic>{h}</heuristic>")
    lines.append("</heuristics>")
    return "\n".join(lines)


def format_detection_questions(questions: list[str]) -> str:
    """Format detection questions as XML."""
    lines = ["<detection_questions>"]
    for q in questions:
        lines.append(f"  <question>{q}</question>")
    lines.append("</detection_questions>")
    return "\n".join(lines)


def format_examples(examples: list[tuple[str, str]]) -> str:
    """Format before/after examples as XML."""
    lines = ["<examples>"]
    for before, after in examples:
        lines.append(f'  <example before="{before}">{after}</example>')
    lines.append("</examples>")
    return "\n".join(lines)


def format_findings_template() -> str:
    """Format the expected findings output structure."""
    return """<findings_format>
For each issue found, output:

  <finding severity="high|medium|low">
    <location>file.py:line-line</location>
    <evidence>quoted code (2-5 lines)</evidence>
    <issue>What's wrong and why it matters</issue>
  </finding>

After all findings, summarize:

  <dimension_summary>
    <dimension>$DIMENSION</dimension>
    <severity>none|low|medium|high</severity>
    <count>N</count>
    <recommendation>One sentence: worth deep dive or skip</recommendation>
  </dimension_summary>
</findings_format>"""


# =============================================================================
# Step Output
# =============================================================================


def format_step_1(dimension_id: str, script_path: str) -> str:
    """Format step 1: exploration prompt."""
    dim = DIMENSIONS[dimension_id]

    actions = [
        f"DIMENSION: {dim['title']}",
        f"FOCUS: {dim['focus']}",
        "",
        "EXPLORE the codebase using these heuristics:",
        "",
        format_heuristics(dim["heuristics"]),
        "",
        "ASK these questions as you read code:",
        "",
        format_detection_questions(dim["detection_questions"]),
        "",
        "EXAMPLES of improvements:",
        "",
        format_examples(dim["examples"]),
        "",
        "SEARCH STRATEGY:",
        "  1. Use Glob to find relevant files",
        "  2. Use Grep to find patterns matching heuristics",
        "  3. Use Read to examine suspicious code",
        "  4. Document each finding with location and evidence",
        "",
        "Do NOT propose solutions yet - just document findings.",
    ]

    parts = [
        format_step_header(1, 2, "Exploration", dimension_id),
        "",
        format_xml_mandate(),
        "",
        format_current_action(actions),
        "",
        format_invoke_after(f"python3 {script_path} --step 2 --total-steps 2 --dimension {dimension_id}"),
    ]
    return "\n".join(parts)


def format_step_2(dimension_id: str) -> str:
    """Format step 2: synthesis."""
    dim = DIMENSIONS[dimension_id]

    actions = [
        f"DIMENSION: {dim['title']}",
        "",
        "SYNTHESIZE your findings from Step 1.",
        "",
        format_findings_template(),
        "",
        "SEVERITY GUIDELINES:",
        "  HIGH: Blocks maintainability, affects multiple areas, clear fix exists",
        "  MEDIUM: Causes friction, localized impact, fix is straightforward",
        "  LOW: Minor annoyance, cosmetic, fix is trivial",
        "  NONE: No issues found in this dimension",
        "",
        "OUTPUT your findings now using the format above.",
    ]

    parts = [
        format_step_header(2, 2, "Synthesis", dimension_id),
        "",
        format_current_action(actions),
        "",
        "COMPLETE - Return findings to orchestrator.",
    ]
    return "\n".join(parts)


def format_output(step: int, total_steps: int, dimension: str, script_path: str) -> str:
    """Format output for the given step."""
    if step == 1:
        return format_step_1(dimension, script_path)
    else:
        return format_step_2(dimension)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Explore - Dimension-specific exploration",
        epilog=f"Dimensions: {', '.join(DIMENSIONS.keys())}",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--dimension", type=str, required=True, choices=list(DIMENSIONS.keys()))

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 2:
        sys.exit("ERROR: --total-steps must be >= 2")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    script_path = os.path.abspath(__file__)
    print(format_output(args.step, args.total_steps, args.dimension, script_path))


if __name__ == "__main__":
    main()
