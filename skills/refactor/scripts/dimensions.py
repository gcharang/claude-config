#!/usr/bin/env python3
"""
Shared dimension definitions for refactor skill.

Single source of truth for all dimension metadata. Used by:
  - explore.py: Full definitions for exploration prompts
  - refactor.py: Focus summaries for selection, full definitions for deep dive

Usage:
    python3 dimensions.py --list              # List dimension IDs
    python3 dimensions.py --dimension naming  # Full definition for one dimension
    python3 dimensions.py --focuses           # ID -> focus mapping (for sync check)
"""

import argparse
import sys


DIMENSIONS = {
    "naming": {
        "title": "Naming & Semantics",
        "focus": "Names that mislead, obscure intent, or operate at wrong abstraction level",
        "impact_weight": 1,
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
        "impact_weight": 1,
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
        "impact_weight": 1,
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
        "impact_weight": 2,
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
        "impact_weight": 2,
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
        "impact_weight": 3,
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
        "impact_weight": 1,
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
        "impact_weight": 3,
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
    "readability": {
        "title": "Readability & LLM Comprehension",
        "focus": "Code that requires external context to understand, especially for LLMs",
        "impact_weight": 1,
        "heuristics": [
            "Boolean trap (fn(True, False) - meaning unclear without signature)",
            "Magic numbers/strings without explaining context",
            "Positional args where named params would clarify intent",
            "Dense expressions that are hard to parse (nested ternaries)",
            "Missing WHY comments on non-obvious code decisions",
            "Implicit ordering dependencies between calls",
            "Code requiring reading multiple files to understand",
        ],
        "detection_questions": [
            "Can I understand this function from its name + parameters alone?",
            "Would an LLM understand this without seeing the class definition?",
            "Are preconditions and triggers for this code obvious?",
            "Do comments explain WHY, not just WHAT?",
        ],
        "examples": [
            ("Config('foo', True, 'bar', 6, None)", "Config(name='foo', enabled=True, mode='bar', timeout_sec=6)"),
            ("x = a if b else c if d else e", "Split into named intermediate variables"),
            ("# Set x to 5\\nx = 5", "# Rate limit prevents API throttling\\nmax_requests = 5"),
        ],
    },
}

# Ordered list for iteration (matching original order)
DIMENSION_ORDER = [
    "naming",
    "extraction",
    "testability",
    "types",
    "errors",
    "modules",
    "modernization",
    "architecture",
    "readability",
]


def format_dimension_full(dim_id: str) -> str:
    """Format full dimension definition as XML for agent consumption."""
    dim = DIMENSIONS[dim_id]
    lines = [f'<dimension id="{dim_id}">']
    lines.append(f"  <title>{dim['title']}</title>")
    lines.append(f"  <focus>{dim['focus']}</focus>")
    lines.append(f"  <impact_weight>{dim['impact_weight']}</impact_weight>")
    lines.append("")
    lines.append("  <heuristics>")
    for h in dim["heuristics"]:
        lines.append(f"    <heuristic>{h}</heuristic>")
    lines.append("  </heuristics>")
    lines.append("")
    lines.append("  <detection_questions>")
    for q in dim["detection_questions"]:
        lines.append(f"    <question>{q}</question>")
    lines.append("  </detection_questions>")
    lines.append("")
    lines.append("  <examples>")
    for before, after in dim["examples"]:
        lines.append(f'    <example before="{before}">{after}</example>')
    lines.append("  </examples>")
    lines.append("</dimension>")
    return "\n".join(lines)


def format_focuses() -> str:
    """Format ID -> focus mapping for sync checking."""
    lines = ["<dimension_focuses>"]
    for dim_id in DIMENSION_ORDER:
        dim = DIMENSIONS[dim_id]
        lines.append(f'  <dim id="{dim_id}" weight="{dim["impact_weight"]}">{dim["focus"]}</dim>')
    lines.append("</dimension_focuses>")
    return "\n".join(lines)


def format_list() -> str:
    """Format dimension ID list."""
    lines = ["<dimensions>"]
    for dim_id in DIMENSION_ORDER:
        lines.append(f"  <id>{dim_id}</id>")
    lines.append("</dimensions>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Shared dimension definitions for refactor skill",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List dimension IDs")
    group.add_argument("--dimension", type=str, help="Get full definition for dimension")
    group.add_argument("--focuses", action="store_true", help="Get ID -> focus mapping")

    args = parser.parse_args()

    if args.list:
        print(format_list())
    elif args.dimension:
        if args.dimension not in DIMENSIONS:
            sys.exit(f"ERROR: Unknown dimension '{args.dimension}'. Valid: {', '.join(DIMENSION_ORDER)}")
        print(format_dimension_full(args.dimension))
    elif args.focuses:
        print(format_focuses())


if __name__ == "__main__":
    main()
