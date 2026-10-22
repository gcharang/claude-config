# Skills Architecture

Script-based agent workflows with shared orchestration framework.

## File Organization: The "Book" Pattern

Skill files read top-to-bottom like a book. Dependencies are defined before use. The ordering principle: **a reader should never need to scroll up to understand what they're reading.**

### Section Order

Files use a fixed section sequence. Group by type, not by step. Within each type-group, order by workflow step. Omit sections with no content.

```python
# ============================================================================
# SHARED PROMPTS
# ============================================================================
# Prompts used by 2+ workflow steps. If large, extract to prompts/shared.py

# ============================================================================
# CONFIGURATION
# ============================================================================
# Constants, temperatures, thresholds

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================
# Step-delimited subsections (see below)

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

# ============================================================================
# MESSAGE BUILDERS
# ============================================================================
# Functions that compose templates into complete messages

# ============================================================================
# [DOMAIN] LOGIC
# ============================================================================
# Domain-specific (utility) functions

# ============================================================================
# STEP DEFINITIONS
# ============================================================================
# STATIC_STEPS and DYNAMIC_STEPS dicts (table-driven dispatch)

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================
# format_output() entry point

# ============================================================================
# ENTRY POINT
# ============================================================================
# main() function
```

Rationale: functions often reference prompts from multiple steps. Grouping by type avoids forward references within function sections.

### Step-Delimited MESSAGE TEMPLATES

Within MESSAGE TEMPLATES, use step dividers to organize chronologically:

```python
# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: SCOPE -----------------------------------------------------------

SCOPE_INSTRUCTIONS = """..."""

# --- STEP 2: SURVEY ----------------------------------------------------------

SURVEY_DISPATCH_CONTEXT = """\
Analysis goals from SCOPE step:
- User intent and what they want to understand
- Identified focus areas"""

SURVEY_DISPATCH_GUIDANCE = """\
DISPATCH GUIDANCE:
...
ADVANCE: After results received, re-invoke with --confidence low."""

SURVEY_LOW_INSTRUCTIONS = """..."""
SURVEY_MEDIUM_INSTRUCTIONS = """..."""

# --- STEP 3: DEEPEN ----------------------------------------------------------

DEEPEN_DISPATCH_CONTEXT = SURVEY_DISPATCH_CONTEXT  # reuse if identical
DEEPEN_LOW_INSTRUCTIONS = """..."""

# --- STEP 4: SYNTHESIZE ------------------------------------------------------

SYNTHESIZE_EXPLORING_INSTRUCTIONS = """..."""
```

Step divider format: `# --- STEP N: PHASE_NAME ` followed by dashes to column 76.

Within a step section, order constants by execution flow. Dispatch-related constants (context, guidance) come before instruction constants.

### Dispatch Prompts: Templates vs Builders

Dispatch prompts combine static text with the dispatch building blocks in `skills.lib.workflow.prompts` (`agent_tool_instruction`, `parallel_constraint`, `sub_agent_invoke`). Split them:

**Static parts -> MESSAGE TEMPLATES** (constants). A dispatch with no runtime inputs is a constant even though it calls the building blocks: see `DISPATCH_INSTRUCTIONS` in `deepthink/think.py` and `SURVEY_INSTRUCTIONS` in `codebase_analysis/analyze.py`.

When the orchestrator decides the number of agents at runtime, as in both, write the count as `N`, pass `parallel_constraint("N")`, and say what N is. A placeholder list passed to `template_dispatch()` prints its own length as the agent count, which contradicts the real one.

**Composition -> MESSAGE BUILDERS** (functions), for a dispatch built from values the script computes when it runs. `build_explore_dispatch` in `refactor/refactor.py` renders one entry per category it selected, so its agent count is exact.

This separation ensures:

1. Prompt text is visible at the constant definition (no tracing into functions)
2. Builders reference only constants defined above (chronological ordering)
3. Changes to dispatch parameters don't require modifying prompt text

### Naming Convention

```
[PHASE]_[TYPE]
```

PHASE is the workflow phase: `SCOPE`, `SURVEY`, `DEEPEN`, `SYNTHESIZE`, `DISCOVERY`, `IDEATION`.
TYPE is its role: `INSTRUCTIONS`, `DISPATCH_CONTEXT`, `DISPATCH_GUIDANCE`, `FORMAT`, `FEEDBACK`.

Confidence variants use suffixes: `_LOW`, `_MEDIUM`, `_HIGH`, `_EXPLORING`, `_CERTAIN`.

Examples:

```python
EVALUATION_CRITERIA              # shared (used by 2+ steps)
SCOPE_INSTRUCTIONS               # step 1
SURVEY_DISPATCH_CONTEXT          # step 2, dispatch context
SURVEY_LOW_INSTRUCTIONS          # step 2, low confidence variant
DEEPEN_HIGH_INSTRUCTIONS         # step 3, high confidence variant
SYNTHESIZE_FORMAT                # step 4, output format
```

### Placement Rule

> A prompt belongs in the earliest section where it is used.

- Used in Steps 2, 4, 6? -> SHARED PROMPTS section
- Used only in Step 3? -> Step 3 position in MESSAGE TEMPLATES
- Used in Steps 3 and 4 only? -> Step 3 position (consecutive use doesn't require SHARED)

### Visual Formatting

Section headers (76 equals signs):

```python
# ============================================================================
# SECTION NAME
# ============================================================================
```

Step dividers within MESSAGE TEMPLATES (76 chars total):

```python
# --- STEP N: PHASE_NAME ------------------------------------------------------
```

Blank line before and after section headers. No blank line required around step dividers.

### String Format Convention

Multi-line strings use parenthesized concatenation, not triple-quoted strings:

```python
# GOOD - each line visible at its indentation level
SCOPE_INSTRUCTIONS = (
    "PARSE user intent:\n"
    "  - What codebase(s) are we analyzing?\n"
    "  - What is the user trying to understand?\n"
    "\n"
    "DEFINE goals (1-3 specific objectives):\n"
    "  - 'Understand how [system X] processes [Y]'\n"
    "  - 'Map dependencies between [A] and [B]'"
)

# GOOD - composing with variables
EXECUTE_INSTRUCTIONS = (
    "Apply each approved change.\n"
    "\n"
    "INTEGRATION CHECKS:\n"
    "  - Cross-section references correct?\n"
    "  - Terminology consistent?\n"
    "\n"
    + ANTI_PATTERN_AUDIT + "\n"
    "\n"
    + CHANGE_PRESENTATION
)

# BAD - triple-quoted strings force column 0 for content
SCOPE_INSTRUCTIONS = """\
PARSE user intent:
  - What codebase(s) are we analyzing?
  - What is the user trying to understand?"""
```

**Exception — prompt-content modules** (e.g. `planner/.../prompts/content.py`): multi-line
prompt blocks relocated verbatim from prior per-phase files MAY use triple-quoted strings
when the exact text (including column-0 layout) is asserted by tests on substrings/offsets.
Triple-quoting preserves that text faithfully; parenthesized concatenation is preferred for
all other multi-line strings.

Rules:

- Every line gets its own string literal with explicit `\n`
- Blank lines become `"\n"` on their own line
- Last line has no trailing `\n`
- Variable composition uses `+ VARIABLE + "\n"` (or no `"\n"` if last)

## How Skills Build Step Bodies

No "action factories". No inversion of control. Just strings.

### Pattern 1: Static Steps (deepthink subagent)

All-static workflows use one `STATIC_STEPS` dict of (title, instructions) tuples:

```python
STATIC_STEPS = {
    1: ("Context Grounding", CONTEXT_GROUNDING_INSTRUCTIONS),
    2: ("Analogical Generation", ANALOGICAL_GENERATION_INSTRUCTIONS),
    3: ("Analysis", ANALYSIS_INSTRUCTIONS),
    # ...
}

def format_output(step: int) -> str:
    if step not in STATIC_STEPS:
        return f"ERROR: Invalid step {step}"
    title, instructions = STATIC_STEPS[step]
    next_cmd = build_next_command(step)
    return format_step(instructions, next_cmd or "", title=f"WORKFLOW - {title}")
```

### Pattern 2: Parameterized Steps (codebase-analysis)

A step whose title or body depends on CLI parameters such as `--confidence` and `--iteration` gets a dynamic formatter. The step's instructions stay in MESSAGE TEMPLATES constants; the formatter chooses and formats them, and may return a short completion body of its own. In `codebase_analysis/analyze.py`, `_format_step_3` renders the DEEPEN body for the current iteration, or a completion body once the previous iteration reached the exit confidence. The module layout is Pattern 5's.

### Pattern 3: Dispatch Steps (planner orchestrator)

```python
from skills.lib.workflow.prompts import format_step, subagent_dispatch
from skills.planner.shared.constraints import ORCHESTRATOR_CONSTRAINT

def format_dispatch_step(agent_type: str, invoke_cmd: str, state_dir: str) -> str:
    dispatch = subagent_dispatch(agent_type=agent_type, command=invoke_cmd)

    body = (
        ORCHESTRATOR_CONSTRAINT + "\n"
        "\n"
        + dispatch
    )

    next_step_cmd = "uv run python -m skills.planner.orchestrator.planner --step N --state-dir " + state_dir
    return format_step(body, next_step_cmd)
```

### Pattern 4: File Injection (prompt-engineer)

```python
from skills.lib.workflow.prompts import format_step, format_file_content

def format_technique_step(categories: list[str]) -> str:
    file_blocks = []
    for cat in categories:
        path = CATEGORY_TO_FILE[cat]
        content = (REFS_DIR / path).read_text()
        file_blocks.append(format_file_content(f"references/{path}", content))

    body = (
        "TECHNIQUE REFERENCES\n"
        "The following files have been loaded based on your category selection:\n"
        "\n"
        + "\n".join(file_blocks) + "\n"
        "\n"
        "TASK: Apply techniques from these references to the target prompt.\n"
        "..."
    )

    return format_step(body, "uv run python -m skills.prompt_engineer.optimize --step 5")
```

### Pattern 5: Hybrid Static/Dynamic Steps

Workflows with mostly static steps and few parameterized steps benefit from a hybrid approach. The skeleton below is illustrative; `deepthink/think.py` is the live example:

```python
# ============================================================================
# MESSAGE BUILDERS
# ============================================================================

def _refinement_done(confidence: str, iteration: int) -> bool:
    return iteration > 1 and confidence in ("high", "certain")


def build_next_command(step: int, mode: str, confidence: str, iteration: int) -> str | None:
    # ...
    elif step == 11:
        if _refinement_done(confidence, iteration):
            return f"{base} --step 12 --confidence {confidence} --mode {mode}"
        # ...


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

# Static steps: (title, instructions) tuples
STATIC_STEPS = {
    1: ("Context Clarification", CONTEXT_CLARIFICATION_INSTRUCTIONS),
    2: ("Abstraction", ABSTRACTION_INSTRUCTIONS),
    # ... more static steps
}


# Dynamic formatter functions - defined BEFORE DYNAMIC_STEPS dict
def _format_step_10(mode: str, confidence: str, iteration: int) -> tuple[str, str]:
    """Dynamic step whose body depends on a parameter."""
    body = SYNTHESIS_FULL_INSTRUCTIONS if mode == "full" else SYNTHESIS_QUICK_INSTRUCTIONS
    return ("Initial Synthesis", body)


def _format_step_11(mode: str, confidence: str, iteration: int) -> tuple[str, str]:
    """Dynamic step with parameterized title and body, and a completion body at loop exit."""
    if _refinement_done(confidence, iteration):
        return (
            "Iterative Refinement Complete",
            f"The previous iteration reached {confidence.upper()} confidence. Proceed to formatting.",
        )
    title = f"Iterative Refinement (Iteration {iteration} of {MAX_ITERATIONS})"
    body = REFINEMENT_INSTRUCTIONS.format(iteration=iteration, max_iter=MAX_ITERATIONS)
    return (title, body)


# Dynamic steps dict - references functions defined above
DYNAMIC_STEPS = {
    10: _format_step_10,
    11: _format_step_11,
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_output(step: int, mode: str, confidence: str, iteration: int) -> str:
    """Callable dispatch: static lookup or dynamic function call."""
    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
    elif step in DYNAMIC_STEPS:
        title, instructions = DYNAMIC_STEPS[step](mode, confidence, iteration)
    else:
        return f"ERROR: Invalid step {step}"

    next_cmd = build_next_command(step, mode, confidence, iteration)
    return format_step(instructions, next_cmd or "", title=f"WORKFLOW - {title}")
```

**Ordering constraint (book pattern)**: Dynamic formatter functions that call MESSAGE BUILDERS must appear AFTER MESSAGE BUILDERS. The DYNAMIC*STEPS dictionary must appear AFTER all `\_format_step*\*` functions it references.

**Loop exit**: write a loop's exit test once, as a function that both `build_next_command` and the step's formatter call, so the printed body and the next command cannot disagree.

Use this pattern when:

- Many steps share the same structure (title + constant body)
- Few steps need parameters for title or body construction
- Parameters are uniform across all dynamic steps

Benefits:

- Compact representation for static steps (one line per step)
- Clear, readable functions for dynamic steps
- Single dispatch point in `format_output()`
- Follows "book pattern" (all references resolve to definitions above)

### Anti-Pattern: Action Factories

```python
# BAD - unnecessary indirection
def technique_review_actions(for_ecosystem=False):
    base = ["For each technique...", "1. QUOTE the trigger", ...]
    if for_ecosystem:
        base.append("Note techniques across prompts")
    return base
```

Replace with:

```python
# GOOD - text at call site
TECHNIQUE_REVIEW = (
    "For each technique in the Technique Selection Guide:\n"
    "1. QUOTE the trigger condition from the table\n"
    "2. QUOTE text from the target prompt that matches\n"
    "3. Verdict: APPLICABLE or NOT APPLICABLE"
)

TECHNIQUE_REVIEW_ECOSYSTEM = (
    TECHNIQUE_REVIEW + "\n"
    "Note techniques that apply to multiple prompts."
)

# Usage: compose with +
body = (
    "...\n"
    + TECHNIQUE_REVIEW_ECOSYSTEM + "\n"
    "..."
)
```

Functions that return prompt fragments are only justified when there's complex conditional logic (multiple if/else branches). Even then, they live in the skill, not the shared lib.

## Shared Library

Location: `skills/lib/workflow/prompts/`

Only abstractions used by 3+ skills with identical semantics:

```
prompts/
    __init__.py         # re-exports
    subagent.py         # dispatch templates
    step.py             # format_step()
    file.py             # format_file_content()
```

### subagent.py

Dispatch patterns for spawning sub-agents via the Agent tool:

- `subagent_dispatch(agent_type, command, prompt="", model=None)` -- single sequential dispatch
- `template_dispatch(agent_type, template, targets, command, ...)` -- parallel SIMD (same template, N targets with $var substitution)

Building blocks (also exported):

- `agent_tool_instruction(agent_type, model)` -- how to use the Agent tool
- `sub_agent_invoke(cmd)` -- command the spawned agent runs
- `parallel_constraint(count)` -- parallel dispatch instruction

### step.py

```python
def format_step(body: str, next_cmd: str = "", title: str = "") -> str:
    """Assemble a complete workflow step.

    Args:
        body: The prompt content (free-form text)
        next_cmd: Command to run next (empty string for final step)
        title: Optional title rendered as "TITLE\\n======\\n\\n" header

    Returns:
        Complete step output as plain text
    """
```

### file.py

```python
def format_file_content(path: str, content: str) -> str:
    """Embed file content in a prompt.

    Uses 4-backtick fence to handle content containing triple-backticks.
    """
```

## Two Invoke Concepts

The codebase has two distinct "invoke" situations:

**Sub-agent invoke** (`sub_agent_invoke()` in subagent.py): Appears INSIDE a dispatch prompt. Tells the SPAWNED agent what command to run after it's created.

**Parent invoke_after** (in `format_step()`): Appears AFTER the body as the step's terminal directive. Tells the CURRENT agent what to run next.

A dispatch step has BOTH:

- The body contains a dispatch prompt with the sub-agent's invoke command
- The step ends with the parent's invoke_after for what happens after the sub-agent returns

## Core Abstraction: The Step

Every workflow step has the same fundamental structure:

```
[body]

[invoke_after]
```

That's it. Two parts:

1. **body**: The actual prompt content. Free-form text.
2. **invoke_after**: The command the LLM should run next. Optional (empty for final steps).
