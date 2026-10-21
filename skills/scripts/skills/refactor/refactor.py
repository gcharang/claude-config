#!/usr/bin/env python3
"""
Refactor Skill - Category-based code smell detection and synthesis.

WORKFLOW and format_output below define the steps and their routing.
"""

import argparse
import random
import re
import shlex
import sys
from enum import Enum
from xml.sax.saxutils import quoteattr

from skills.lib.workflow.ast import (
    CurrentActionNode,
    FileContentNode,
    InvokeAfterNode,
    StepHeaderNode,
    TemplateDispatchNode,
    XMLRenderer,
    render_current_action,
    render_invoke_after,
    render_step_header,
    render_template_dispatch,
)
from skills.lib.workflow.core import (
    StepDef,
    Workflow,
)
from skills.lib.workflow.prompts.step import pin_cwd
from skills.lib.workflow.prompts.subagent import parallel_constraint
from skills.refactor.explore import CATEGORY_HEADING_RE, CONVENTIONS_DIR


class DocumentAvailability(Enum):
    """Explicit document availability states.

    Enum makes valid states explicit and eliminates silent filtering bugs.

    Centralizes phase + design_mode logic across call sites.
    """

    DESIGN_AND_CODE = "design_and_code"
    CODE_ONLY = "code_only"
    NOT_AVAILABLE = "not_available"


# Module paths for -m invocation
MODULE_PATH = "skills.refactor.refactor"
EXPLORE_MODULE_PATH = "skills.refactor.explore"


def _invoke_tag(cmd: str) -> str:
    """Render a well-formed <invoke> directive for the refactor workflow.

    pin_cwd makes the command cwd-independent, so a sub-agent whose cwd has drifted
    still resolves the ``skills`` package (a relative working-dir attr fails with
    "No module named 'skills'"). quoteattr then escapes the whole command so a
    --scope path containing XML metacharacters (&, <, ") cannot break out of the
    attribute and malform the directive.
    """
    return f"<invoke cmd={quoteattr(pin_cwd(cmd))} />"

# Default number of code smell categories to explore per analysis run
DEFAULT_CATEGORY_COUNT = 10


# =============================================================================
# Category Parser
# =============================================================================


def parse_documents() -> list[dict]:
    """Parse document metadata (phases, mode availability).

    Returns:
        List of dicts with keys: file, applicable_phases, has_design_mode, categories
    """
    docs = []
    for md_file in [
        "01-naming-and-types.md",
        "02-structure-and-composition.md",
        "03-patterns-and-idioms.md",
        "04-repetition-and-consistency.md",
        "05-documentation-and-tests.md",
        "06-module-and-dependencies.md",
        "07-cross-file-consistency.md",
        "08-codebase-patterns.md",
    ]:
        path = CONVENTIONS_DIR / md_file
        if not path.exists():
            continue

        content = path.read_text()
        lines = content.splitlines()

        phases_match = re.search(r"<!--\s*applicable_phases:\s*([^-]+?)\s*-->", content)
        phases = []
        if phases_match:
            phases = [p.strip() for p in phases_match.group(1).split(",")]

        # NOTE: build_target_pool gates design targets on this tag as well as on the
        # phase; its docstring gives the reason.
        has_design = "<design-mode>" in content

        categories = []
        current_cat = None
        for i, line in enumerate(lines, 1):
            if match := CATEGORY_HEADING_RE.match(line):
                if current_cat:
                    current_cat["end_line"] = i - 1
                    categories.append(current_cat)
                current_cat = {
                    "file": md_file,
                    "name": match.group(1),
                    "start_line": i,
                }
        if current_cat:
            current_cat["end_line"] = len(lines)
            categories.append(current_cat)

        docs.append(
            {
                "file": md_file,
                "applicable_phases": phases,
                "has_design_mode": has_design,
                "categories": categories,
            }
        )

    return docs


def build_target_pool(mode_filter: str = "both") -> list[dict]:
    """Build pool of (category, mode) targets for refactor exploration.

    Filtering logic:
    - Phase filter (HTML comment): Document declares which workflow phases it supports
    - Mode availability (XML tag): Document has implemented mode-specific guidance
    - Both must pass: A doc declaring refactor_design phase support still needs
      <design-mode> tag to generate design targets. This prevents incomplete docs
      (phase declared but guidance missing) from entering the exploration pool.

    Args:
        mode_filter: "design", "code", or "both"

    Returns:
        List of dicts with keys: file, name, start_line, end_line, mode
    """
    targets = []
    for doc in parse_documents():
        phases = doc["applicable_phases"]

        for cat in doc["categories"]:
            if (
                mode_filter in ("both", "design")
                and "refactor_design" in phases
                and doc["has_design_mode"]
            ):
                targets.append({**cat, "mode": "design"})

            if mode_filter in ("both", "code") and "refactor_code" in phases:
                targets.append({**cat, "mode": "code"})

    return targets


def select_targets(n: int = DEFAULT_CATEGORY_COUNT, mode_filter: str = "both") -> list[dict]:
    """Randomly select N targets from filtered pool.

    Args:
        n: Number of targets to select
        mode_filter: "design", "code", or "both"

    Returns:
        List of N randomly selected target dicts
    """
    pool = build_target_pool(mode_filter)
    return random.sample(pool, min(n, len(pool)))


# =============================================================================
# XML Formatters (refactor-specific)
# =============================================================================


def build_explore_dispatch(
    n: int = DEFAULT_CATEGORY_COUNT, mode_filter: str = "both", scope: str | None = None
) -> str:
    """Build parallel dispatch block for explore agents.

    Each category uses the same explore workflow.
    Uses TemplateDispatchNode for SIMD-style dispatch: single instruction, multiple data.
    """
    selected = select_targets(n, mode_filter)

    # Build targets with substitution variables
    targets = tuple(
        {
            "ref": f"{t['file']}:{t['start_line']}-{t['end_line']}",
            "name": t["name"],
            "mode": t["mode"],
        }
        for t in selected
    )

    # Scope propagation to explore agents. Double every $ so the safe_substitute
    # that render_template_dispatch runs over `command` below treats a $-bearing
    # scope token (e.g. "src/$mode") as a literal instead of interpolating it as
    # a $ref/$mode template var. The real placeholders are the bare
    # $ref/$mode concatenated separately into `command`; safe_substitute turns
    # $$ back into a single $, and shlex's single-quotes still shield it at the
    # shell layer when the agent runs the invoke.
    scope_arg = f" --scope {shlex.quote(scope)}".replace("$", "$$") if scope else ""

    # Template prompt with $var placeholders. The command lives in `command`
    # below, not inline here -- a hand-built <invoke> in the prose would
    # double-wrap and interpolate $scope unescaped.
    template = (
        "Explore the codebase for this code smell.\n"
        "\n"
        "CATEGORY: $name\n"
        "MODE: $mode\n"
        "\n"
        "Run the invoke command below to begin."
    )

    # Bare command (with $var placeholders); render_template_dispatch wraps it in
    # the <invoke>.
    command = f"uv run python -m {EXPLORE_MODULE_PATH} --step 1 --category $ref --mode $mode{scope_arg}"

    node = TemplateDispatchNode(
        agent_type="general-purpose",
        template=template,
        targets=targets,
        command=command,
        model="haiku",
        instruction=f"Launch {len(selected)} general-purpose sub-agents for code smell exploration.",
    )

    return render_template_dispatch(node)


def format_expected_output(sections: dict[str, str]) -> str:
    """Render expected output block."""
    lines = ["<expected_output>"]
    for name, content in sections.items():
        lines.append(f'  <section name={quoteattr(name)}>')
        for line in content.split("\n"):
            lines.append(f"    {line}" if line else "")
        lines.append("  </section>")
    lines.append("</expected_output>")
    return "\n".join(lines)


# =============================================================================
# Step Definitions
# =============================================================================


STEPS = {
    1: {
        "title": "Mode Selection",
        "brief": "Analyze user request to determine design/code/both/custom",
    },
    2: {
        "title": "Dispatch / Category Selection",
        "brief": "Non-custom: dispatch explore agents. Custom: LLM selects categories.",
    },
    3: {
        "title": "Category Verification",
        "brief": "Custom mode only: verify category selections before dispatch",
    },
    4: {
        "title": "Dispatch / Triage",
        "brief": "Custom: dispatch verified categories. Non-custom: triage findings.",
    },
    5: {
        "title": "Triage",
        "brief": "Structure smell findings with IDs for synthesis",
        "actions": [
            "REVIEW all smell_report outputs from explore agents.",
            "",
            "STRUCTURE each finding as a smell object with unique ID:",
            "",
            "OUTPUT FORMAT (JSON array):",
            "```json",
            "{",
            '  "smells": [',
            "    {",
            '      "id": "smell-1",',
            '      "type": "category from smell_report",',
            '      "location": "file:line-range",',
            '      "description": "issue description from finding",',
            '      "severity": "high|medium|low",',
            # WHY evidence is split into code/line_count fields:
            #
            # Code snippets have variable token cost:
            #   - 2-line snippet: ~30 tokens
            #   - 5-line snippet: ~75 tokens
            #
            # Storing line_count separately enables:
            #   - Downstream budget estimation without parsing code
            #   - Filtering decisions based on evidence completeness
            #   - Verification that quoted code matches claimed length
            #
            # The alternative (opaque string field) makes it impossible to assess
            # evidence completeness without tokenizing the code.
            #
            # WHY occurrences is an object with count/verification/locations:
            #
            # Separate fields support different use cases:
            #   - count: Used for severity ranking (high occurrence = high impact)
            #   - verification: Used for falsifiability (reviewer can reproduce)
            #   - locations: Used for proportionality (affected files)
            #
            # Collapsing these into a string loses structure needed for:
            #   - Automated verification (cannot extract command)
            #   - Evidence selection (cannot compare counts numerically)
            #   - Scope analysis (cannot count affected files)
            '      "evidence": {',
            '        "code": "quoted code snippet (2-5 lines, preserve indentation)",',
            '        "line_count": N',
            "      },",
            '      "impact": "WHY fix this - copied from <impact> tag",',
            '      "occurrences": {',
            '        "count": N,',
            '        "verification": "grep command to reproduce count",',
            '        "locations": ["file:line examples from the report; may be fewer than count"]',
            "      }",
            "    }",
            "  ],",
            '  "smell_count": N,',
            '  "original_prompt": "user\'s original request (preserve exact wording)"',
            "}",
            "```",
            "",
            # WHY evidence validation happens at Triage rather than Cluster:
            #
            # Triage is the first JSON-producing step. It has:
            #   - Full smell_report XML (structured data to validate against)
            #   - Direct access to evidence fields (no smell ID lookup)
            #   - Ability to reject before IDs are assigned (no orphan references)
            #
            # If validation deferred to Cluster:
            #   - Agent sees smell-1, smell-2 IDs without original XML
            #   - Cannot verify evidence completeness (would need to re-parse reports)
            #   - Rejection produces smell IDs with no corresponding smells (confusing)
            #
            # Validating at Triage means rejected findings never get IDs, never propagate.
            "EVIDENCE VALIDATION:",
            "  Before including a smell, verify:",
            "  1. evidence.code is actual quoted code (not description)",
            "  2. impact explains consequence (not just restates issue)",
            "  3. occurrences.count is the Grep count the explore agent reported",
            "  4. occurrences.verification is executable command",
            "",
            "  REJECT findings that lack concrete evidence.",
            "",
            "PRESERVE the user's original prompt exactly - it will be used for intent extraction.",
            "",
            "Output the JSON, then proceed to clustering.",
        ],
    },
    6: {
        "title": "Cluster",
        "brief": "Group smells by shared root cause",
    },
    7: {
        "title": "Contextualize",
        "brief": "Extract user intent and prioritize issues",
    },
    8: {
        "title": "Synthesize",
        "brief": "Generate actionable work items",
    },
}


# =============================================================================
# Workflow Definition
# =============================================================================


WORKFLOW = Workflow(
    "refactor",
    StepDef(
        id="mode_selection",
        title="Mode Selection",
        actions=[],
    ),
    StepDef(
        id="dispatch",
        title="Dispatch / Category Selection",
        actions=[
            "IDENTIFY the scope from user's request:",
            "  - Could be: file(s), directory, subsystem, entire codebase",
        ],
    ),
    StepDef(
        id="verification",
        title="Category Verification",
        actions=[],
    ),
    StepDef(
        id="dispatch_or_triage",
        title="Dispatch / Triage",
        actions=[],
    ),
    StepDef(
        id="triage",
        title="Triage",
        actions=STEPS[5]["actions"],
    ),
    StepDef(
        id="cluster",
        title="Cluster",
        actions=[],
    ),
    StepDef(
        id="contextualize",
        title="Contextualize",
        actions=[],
    ),
    StepDef(
        id="synthesize",
        title="Synthesize",
        actions=[],
    ),
    description="Category-based code smell detection and synthesis",
    validate=False,
)


# =============================================================================
# Synthesis Prompts
# =============================================================================


def format_cluster_prompt() -> str:
    """Format the clustering prompt (Step 3)."""
    return """<task>
Given the smells from the previous step, identify which ones share root causes and should be addressed together.
</task>

<input>
Use the smells JSON from Step 2 output above.
</input>

<analysis>
Group smells that share a root cause. Classify each group's abstraction level
(structural, implementation, surface -- illustrative; name the project-specific form),
mark cross-cutting patterns (same theme in 3+ locations), and give a smell that fits
several groups one primary group, listing the others as related.
</analysis>

<output_format>
Output JSON:
```json
{
  "issues": [
    {
      "id": "issue-1",
      "type": "pattern|cross_cutting|standalone",
      "root_cause": "Description of underlying issue",
      "smell_ids": ["smell-1", "smell-2"],
      "representative_evidence": {
        "from_smell": "smell-id of highest severity constituent",
        "location": "file:line-range",
        "code": "quoted 2-5 lines",
        "impact": "Blocks/Degrades/Risks statement",
        "total_occurrences": N,
        "verification": "grep command"
      },
      "abstraction_level": "structural|implementation|surface",
      "scope": "file|module|system",
      "confidence": "STRONG|MODERATE",
      "related_issues": []
    }
  ],
  "analysis_notes": "Brief clustering rationale"
}
```

EVIDENCE SELECTION FOR CLUSTERED ISSUES:
  When N smells cluster into 1 issue:
  - representative_evidence: From highest-severity smell
  - Tie-breaker: Highest occurrence count
  - total_occurrences: Sum across constituent smells (they share one root cause, so the fix clears all of them)
</output_format>

<edge_cases>
- No smells: Return empty issues array.
- No patterns found: Return all as standalone issues - this is valid.
- Single smell: Return as standalone, skip clustering.
</edge_cases>

Output the issues JSON, then proceed to contextualization."""


def format_contextualize_prompt() -> str:
    """Format the contextualization prompt (Step 4)."""
    return """<task>
Given the issues from the previous step and the user's original prompt, extract their intent and prioritize accordingly.
</task>

<input>
Use the issues JSON from Step 3 and original_prompt from Step 2.
</input>

<intent_extraction>
Read the original prompt again.

Extract quoted phrases that signal intent:
- Scope: "this file", "auth module", "entire codebase"
- Action: "quick cleanup", "refactor", "redesign", "fix"
- Thoroughness: "minimal changes", "comprehensive", "before shipping"
- Domain: "focus on security", "ignore tests", "API layer"

Rephrase: "The user wants to [action] at [scope] level, with [thoroughness] approach, focusing on [domain]."

Structure as:
```json
{
  "scope": "file|module|system|codebase",
  "action_type": "quick|refactor|redesign|investigate",
  "thoroughness": "minimal|balanced|comprehensive",
  "domain_focus": ["..."] or null
}
```
</intent_extraction>

<prioritization>
User phrasing directly influences promotion:
- quick -> promote surface issues, defer structural
- refactor -> promote implementation issues
- redesign -> promote structural issues
- Scope match -> boost priority
- Domain match -> boost priority

Mark each issue as:
- primary: Matches intent, should address
- deferred: Out of scope, noted for later
- appendix: Filtered but safety-notable (security/correctness >= MEDIUM, max 5)

If > 10 high-severity issues suppressed, flag as systemic warning.
</prioritization>

<relationships>
For primary issues, identify relationships using VERB FORMS with explicit direction.

STRUCTURAL (affect execution order):
- requires: A cannot start until B completes. Format: A requires B
- enables: A unlocks value from B but B can proceed alone. Format: A enables B

SUPERSESSION (affect what work is needed):
- obsoletes: Completing A makes B unnecessary. Format: A obsoletes B
  Example: Refactoring entire module obsoletes fixing small smells in old code.
- conflicts_with: A and B are mutually exclusive. Format: A conflicts_with B

SYNERGY (affect combined value):
- amplifies: Doing both together yields more value than sum. Format: A amplifies B

CONTRASTIVE EXAMPLE:
WRONG: {"type": "obsolescence", "items": ["work-5", "work-6"]}
  Problem: Direction unclear. Does this item obsolete them, or vice versa?

RIGHT: {"type": "obsoletes", "subject": "issue-2", "object": "issue-5", "reason": "..."}
  Clear: issue-2 (subject) obsoletes issue-5 (object). Direction is always subject -> object.

Output relationships as:
[
  {"type": "obsoletes", "subject": "issue-2", "object": "issue-5", "reason": "StepInfo dataclass replaces dict pattern"}
]
</relationships>

<constraint_conflicts>
If intent conflicts with findings, use concrete examples:

NOT: "There's a conflict between your preferences and the issues."
USE: "Based on 'quick fixes': 7 items match (low complexity - single-file mechanical changes). 3 structural issues don't fit - defer or include?"
</constraint_conflicts>

<output_format>
Output JSON:
```json
{
  "intent": {
    "scope": "...",
    "action_type": "...",
    "thoroughness": "...",
    "domain_focus": ["..."],
    "rephrased": "The user wants to..."
  },
  "prioritized_issues": [
    {
      "id": "issue-1",
      "status": "primary|deferred|appendix",
      "relevance_rationale": "Why this status",
      "representative_evidence": {
        "location": "file:line-range",
        "code": "quoted code",
        "impact": "consequence statement",
        "total_occurrences": N,
        "verification": "grep command"
      },
      "relationships": [
        {"type": "obsoletes|requires|enables|conflicts_with|amplifies", "subject": "issue-1", "object": "issue-N", "reason": "..."}
      ]
    }
  ],
  "checkpoint_message": "Summary for user",
  "constraint_conflict": null or "Description with options"
}
```
</output_format>

<checkpoint>
PRESENT the checkpoint_message to the user. If there's a constraint_conflict, ask which direction they prefer before proceeding.

For conversational mode: pause here and let the user steer. They might say "focus on X" or "skip the structural issues" or "proceed with all".

For batch mode: proceed with primary issues.
</checkpoint>

<edge_cases>
- No intent signals: Exploratory mode - present top 5 by severity.
- All filtered: Empty primary, message about broadening.
- Contradictory signals: Surface conflict, ask for clarification.
</edge_cases>

Output the prioritized JSON and checkpoint_message, then proceed to synthesis."""


def format_synthesize_prompt() -> str:
    """Format the synthesis prompt (Step 5)."""
    return """<task>
Generate actionable work items from the prioritized issues. Each work item should be immediately executable with clear steps and verification.
</task>

<input>
Use the prioritized_issues (status=primary) from Step 4.
Use the action_type from the intent extraction.
Use the relationships from each issue.
</input>

<dependency_resolution>
Resolve relationships before writing work items:
- An issue that a recommended item obsoletes, directly or through a chain, is not a
  work item; list it under Superseded Items with the item that covers it.
- For A conflicts_with B, recommend one (more items obsoleted, fewer dependencies,
  lower complexity) and list the other under Superseded Items, superseded by the
  recommended one, with the conflict as the reason.
- A requires B puts B first; mutual requires makes an atomic group.
Prefer one comprehensive refactor over several small fixes when it obsoletes them.
</dependency_resolution>

<step_generation>
Generate steps appropriate to action_type:

quick:
- Specific edits with line references
- Single-file changes preferred
- Example: "Change line 45 from X to Y"

refactor:
- Approach outline with intermediate verification
- May span multiple files
- Example: "Extract method, update callers, verify tests"

redesign:
- Architectural changes with migration path
- Multi-phase approach
- Example: "Create interface, implement adapter, migrate consumers"
</step_generation>

<work_item_requirements>
Each work item needs:
- title: Specific (not "Fix X" but "Extract Y from Z to enable W")
- description: What this accomplishes
- affected_files: Specific files that change
- implementation_steps: Numbered, concrete steps
- verification_criteria: How to confirm it worked (tests, grep, behavior)
- obsoletes: List of issues/items this makes unnecessary (from dependency resolution)
- estimated_complexity: Based on LLM execution characteristics (NOT time):
    - low: Single file, mechanical transformation, clear pattern
      Examples: rename symbol, extract constant, add type hints
    - medium: Multiple files OR cross-file relationship understanding needed
      Examples: extract method with caller updates, move function between modules
    - high: Architectural scope, design decisions required, module boundary changes
      Examples: introduce abstraction layer, restructure data flow, change API contract
- evidence_summary: Inline evidence supporting this work item (REQUIRED)
  Format:
    representative_example:
      location: file:line-range
      code: 2-5 lines quoted exactly
    scope:
      occurrence_count: Total across codebase
      verification: Command to reproduce
    before_after: (REQUIRED for abstractions, signature changes, code movement)
      before: Current code pattern
      after: Proposed code pattern
      delta: What changes and why
</work_item_requirements>

<quality_criteria>
CORRECT work items have:
  - Specific title: "Extract X from Y to enable Z" (not "Fix X")
  - Concrete steps with file paths and line references where known
  - Verification that can be executed (test commands, grep patterns)
  - Realistic complexity estimate

INCORRECT work items have:
  - Vague titles: "Fix auth", "Clean up code"
  - Abstract steps: "Refactor the authentication"
  - No verification criteria
  - Missing file references
</quality_criteria>

<output_format>
Generate a HUMAN-READABLE REPORT optimized for decision-making. Do NOT output raw JSON.

FORMAT:

```
# Refactoring Recommendation

## Summary
[2-3 sentences: Core recommendation and expected outcome]

**Recommended:** N work items | **Superseded:** M items | **Total complexity:** [low/medium/high]

---

## Recommended Work Items

[For each recommended item:]

### [work-N]: [Specific Descriptive Title]
**Complexity:** [low/medium/high] | **Addresses:** [issue IDs]

[1-2 sentences: What this accomplishes and why it matters]

**Evidence:**
```
// Representative example from [file:line-range]
[2-5 lines of actual code]
```
*Why this matters:* [impact statement from evidence]
*Scope:* [N occurrences across M files] | Verify: `[grep command]`

[If before_after required:]
**Proposed Change:**
```
// Before
[current pattern]

// After
[proposed pattern]
```
*Delta:* [what changes and why it improves things]

**Approach:**
1. [Concrete step with file reference]
...

**Verification:**
- [Test command, grep pattern, or behavioral check]

---

## Superseded Items (No Action Needed)

[If any items were superseded by recommended work:]

| Originally Identified | Superseded By | Reason |
|-----------------------|---------------|--------|
| [issue description]   | work-N        | [why this work makes the original unnecessary] |

[If none: "All identified issues require direct action."]

---

## Execution Notes

[If dependencies exist between recommended items:]
**Suggested order:** work-N -> work-M -> work-K
**Reason:** [explain sequencing based on requires/enables relationships]

[If atomic groups exist:]
**Must do together:** work-A and work-B (mutual dependency)

---
```
</output_format>

<edge_cases>
- Single issue: Single work item, simplified format without tables.
- Mutual dependencies: Present as atomic group that must be done together.
- No code context: Approach-level steps, note that line-specific details require code access.
- All items independent: Note that items can be done in any order.
</edge_cases>

Present the report directly to the user. The report should be immediately actionable for deciding what refactoring to pursue."""


# =============================================================================
# Output Formatting
# =============================================================================


def format_step_1_output(n: int, info: dict, mode_filter: str, scope: str | None = None) -> str:
    """Format Step 1: Mode selection output."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=1)))
    parts.append("")

    if scope:
        substitution = "with $MODE replaced by your mode (design, code or both)"
    else:
        substitution = (
            "with $MODE replaced by your mode (design, code or both) and $SCOPE by your\n"
            "<scope> path, shell-quoted; when your scope is null or not a path, delete\n"
            '" --scope $SCOPE" instead'
        )
    xml_mandate_text = f"""<xml_format_mandate>
Do the action in <current_action>, then run the command in <invoke_after>: the
<if_custom> command when your mode is custom, the <if_not_custom> command otherwise,
{substitution}. Change nothing else in it.
</xml_format_mandate>"""
    parts.append(xml_mandate_text)
    parts.append("")

    # Custom mode takes precedence over design/code when problem indicators present
    actions = [
        "ANALYZE the user's request to determine refactor mode and extract context:",
        "",
        "STEP A - MODE DETECTION:",
        "",
        "Indicators for CUSTOM mode (problem-focused):",
        '  - Problem keywords: "simplify", "too much boilerplate", "consolidate"',
        '  - Problem keywords: "abstractions don\'t work", "hard to understand"',
        '  - Problem keywords: "reduce duplication", "clean up the mess"',
        "  - Pattern: User describes WHAT is wrong, not just WHERE to look",
        "",
        "Indicators for DESIGN mode (architecture/intent focus):",
        '  - Keywords: "architecture", "design", "structure", "boundaries", "responsibilities"',
        "  - Focus: System organization, module relationships, high-level intent",
        "",
        "Indicators for CODE mode (implementation focus):",
        '  - Keywords: "implementation", "code quality", "patterns", "idioms", "readability"',
        "  - Focus: Function structure, naming, duplication, control flow",
        "",
        "CONTRASTIVE EXAMPLES:",
        '  CUSTOM:     "there is too much boilerplate in the auth module"',
        "              -> Problem: boilerplate. Location: auth module.",
        '  NOT CUSTOM: "apply refactor skill on the auth module"',
        "              -> No problem specified. Just a location.",
        "",
        "PRECEDENCE RULE:",
        "  If BOTH custom and design/code indicators present, prefer CUSTOM.",
        "  Rationale: User stating a problem is more specific than mentioning a category.",
        '  Example: "simplify the architecture" -> CUSTOM (problem: simplify)',
        "",
        "STEP B - SCOPE EXTRACTION:",
        "",
        "If user mentions a specific path/directory/module, extract it:",
        '  - "in src/planner" -> scope: src/planner',
        '  - "the auth module" -> scope: (resolve to actual path if known, else leave as hint)',
        "  - No path mentioned -> scope: null (entire codebase)",
        "",
        "SCOPE PRECEDENCE:",
        "  If --scope CLI arg is provided, it OVERRIDES any scope detected from user text.",
        "  CLI arg = explicit intent. User text = descriptive context.",
        "",
        "STEP C - PROBLEM STATEMENT (custom mode only):",
        "",
        "If mode is CUSTOM, extract the problem statement:",
        "  - What specific issue is the user describing?",
        "  - Preserve their exact wording where possible",
        "",
        f"CLI override: --mode {mode_filter}"
        + (" (use this)" if mode_filter not in ("both", "custom") else " (detect if 'both')"),
        f"CLI scope: {scope or '(none provided)'}"
        + (" (use this)" if scope else " (detect from request)"),
        "",
        "OUTPUT FORMAT:",
        "<mode_selection>",
        "  <mode>design|code|both|custom</mode>",
        "  <scope>path/to/scope or null</scope>",
        "  <problem_statement>user's problem description (custom only)</problem_statement>",
        "</mode_selection>",
        "",
        "Then invoke the appropriate next step based on mode.",
    ]

    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Conditional branching: custom vs non-custom modes have different step 2 invocations
    # Shell escape scope to prevent injection. Without a CLI scope the command carries a
    # $SCOPE slot, so the scope STEP B extracts from the request reaches step 2.
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else " --scope $SCOPE"

    invoke_after = f"""<invoke_after>
  <if_custom>
    {_invoke_tag(f"uv run python -m {MODULE_PATH} --step 2 --mode custom{scope_arg}")}
  </if_custom>
  <if_not_custom>
    {_invoke_tag(f"uv run python -m {MODULE_PATH} --step 2 --n {n} --mode $MODE{scope_arg}")}
  </if_not_custom>
</invoke_after>"""
    parts.append(invoke_after)

    return "\n".join(parts)


def format_step_2_dispatch(n: int, info: dict, mode_filter: str, scope: str | None = None) -> str:
    """Format Step 2 for non-custom modes: Random sampling + dispatch.

    Skips step 3 (verification) via direct jump to step 4 (which is triage for non-custom).
    """
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=2)))
    parts.append("")

    xml_mandate_text = """<xml_format_mandate>
Do the action in <current_action>, then run the <invoke_after> command as printed.
</xml_format_mandate>"""
    parts.append(xml_mandate_text)
    parts.append("")

    scope_display = scope or "entire codebase"
    actions = [
        f"SCOPE: {scope_display}",
        "",
        build_explore_dispatch(n, mode_filter, scope),
        "",
        "WAIT for all agents to return before proceeding.",
        "",
        format_expected_output(
            {
                "Per target": "smell_report with severity (none/low/medium/high) and findings",
                "Format": "<smell_report> blocks from each explore agent",
            }
        ),
    ]

    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Non-custom: jump to step 4 (triage), skipping step 3 (verification)
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else ""
    parts.append(
        render_invoke_after(
            InvokeAfterNode(
                cmd=f"uv run python -m {MODULE_PATH} --step 4 --mode {mode_filter}{scope_arg}"
            )
        )
    )

    return "\n".join(parts)


def format_step_2_custom(info: dict, scope: str | None = None) -> str:
    """Format Step 2 for custom mode: LLM category selection.

    Embeds full category file content for LLM to select relevant ones
    based on problem statement from step 1.
    """
    parts = []

    parts.append(
        render_step_header(StepHeaderNode(title="Category Selection", script="refactor", step=2))
    )
    parts.append("")

    # Embed all category files for LLM review
    parts.append("<category_definitions>")
    parts.append(
        "Review the following code quality categories. Select those relevant to the problem statement from Step 1."
    )
    parts.append("")

    docs = parse_documents()
    parts.append("<category_index>")
    for c in (c for doc in docs for c in doc["categories"]):
        parts.append(f"  {c['file']}:{c['start_line']}-{c['end_line']}  {c['name']}")
    parts.append("</category_index>")
    parts.append("")

    for doc in docs:
        md_file = CONVENTIONS_DIR / doc["file"]
        content = md_file.read_text()
        # Path relative to conventions dir for cleaner display
        rel_path = f"conventions/code-quality/{md_file.name}"
        node = FileContentNode(rel_path, content)
        parts.append(XMLRenderer().render_file_content(node))
        parts.append("")

    parts.append("</category_definitions>")
    parts.append("")

    actions = [
        "CATEGORY SELECTION:",
        "",
        "Using the <problem_statement> from Step 1, select relevant categories.",
        "",
        "FALLBACK: If no <problem_statement> exists in the conversation context,",
        "select up to 10 categories covering common quality issues (naming, structure,",
        "duplication, patterns). This enables exploratory analysis without a",
        "specific problem focus.",
        "",
        "For each selected category, provide:",
        "  - Category reference: the ref from <category_index>",
        "  - Relevance: One sentence explaining why this category applies to the problem",
        "",
        "Selection guidelines:",
        "  - Select 3-10 categories (fewer for focused problems, more for broad ones)",
        "  - Prioritize categories that directly address the stated problem",
        "  - Include adjacent categories that might reveal related issues",
        "  - Skip categories clearly irrelevant to the problem domain",
        "",
        "OUTPUT FORMAT:",
        "<selected_categories>",
        '  <category ref="file:start-end" relevance="why this applies">Category Name</category>',
        "  <!-- repeat for each selected category -->",
        "</selected_categories>",
    ]

    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Next step: verification (step 3)
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else ""
    parts.append(
        render_invoke_after(
            InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 3 --mode custom{scope_arg}")
        )
    )

    return "\n".join(parts)


def format_step_3_verification(info: dict, scope: str | None = None, retry: int = 0) -> str:
    """Format Step 3: Category verification (custom mode only).

    Catches category selection errors before expensive dispatch.
    Recovery: If issues found and retry < 1, loop back with revised selection.
    """
    parts = []

    parts.append(
        render_step_header(StepHeaderNode(title="Category Verification", script="refactor", step=3))
    )
    parts.append("")

    actions = [
        "VERIFY your category selection from Step 2.",
        "",
        f"This is verification attempt {retry + 1} of 2.",
        "",
        "For EACH selected category, answer:",
        "  1. Does this category's detection patterns apply to this project's language/framework?",
        "  2. Would findings from this category address the stated problem?",
        "  3. Is there a more specific category that would be better?",
        "",
        "Also check for gaps:",
        "  - Are there obvious categories missing that would address the problem?",
        "  - Did superficial keyword matching cause irrelevant selections?",
        "",
        "OUTPUT FORMAT:",
        "<verification_result>",
        "  <status>PASS | REVISE</status>",
        "  <verified_categories>",
        "    <!-- categories that passed verification -->",
        '    <category ref="file:start-end">Category Name</category>',
        "  </verified_categories>",
        "  <removed_categories>",
        "    <!-- categories removed with reason -->",
        '    <removed ref="file:start-end" reason="why removed">Category Name</removed>',
        "  </removed_categories>",
        "  <added_categories>",
        "    <!-- categories added that were missing -->",
        '    <added ref="file:start-end" reason="why added">Category Name</added>',
        "  </added_categories>",
        "</verification_result>",
        "",
        "If status is REVISE and this is attempt 1, you'll get one more chance.",
        "If status is PASS or this is attempt 2, proceed to dispatch.",
        "",
        "Return REVISE only with a selection that differs from step 2's; an unchanged",
        "selection is a PASS, because a retry cannot resolve uncertainty that produced",
        "no change.",
    ]

    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Conditional branching: retry loopback vs proceed to dispatch
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else ""
    if retry < 1:
        # Still have retry budget
        invoke_after = f"""<invoke_after>
  <if_revise>
    {_invoke_tag(f"uv run python -m {MODULE_PATH} --step 3 --mode custom{scope_arg} --retry 1")}
  </if_revise>
  <if_pass>
    {_invoke_tag(f"uv run python -m {MODULE_PATH} --step 4 --mode custom{scope_arg}")}
  </if_pass>
</invoke_after>"""
    else:
        # Retry budget exhausted - proceed regardless
        invoke_after = render_invoke_after(
            InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 4 --mode custom{scope_arg}")
        )

    parts.append(invoke_after)

    return "\n".join(parts)


def format_step_4_dispatch_custom(info: dict, scope: str | None = None) -> str:
    """Format Step 4 for custom mode: Dispatch with verified categories.

    Uses categories selected and verified in steps 2-3.
    """
    parts = []

    parts.append(render_step_header(StepHeaderNode(title="Dispatch", script="refactor", step=4)))
    parts.append("")

    scope_display = scope or "entire codebase"
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else ""
    invoke_cmd = _invoke_tag(
        f"uv run python -m {EXPLORE_MODULE_PATH} --step 1 --category $CATEGORY_REF --mode code{scope_arg}"
    )

    actions = [
        "DISPATCH explore agents for verified categories.",
        "",
        "Launch one sub-agent per category in <verified_categories> from Step 3",
        "(N = number of verified categories): subagent_type general-purpose, model haiku.",
        "",
        parallel_constraint("N"),
        "",
        "Prompt for each agent, with the category's name and ref substituted:",
        "    Explore the codebase for this code smell.",
        "",
        "    CATEGORY: $CATEGORY_NAME",
        "    MODE: code",
        f"    SCOPE: {scope_display}",
        "",
        f"    Start: {invoke_cmd}",
        "",
        "After all agents return, continue with the next step.",
    ]

    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Next step: Triage (step 5 in custom mode)
    parts.append(render_invoke_after(InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 5")))

    return "\n".join(parts)


def format_step_4_triage(info: dict) -> str:
    """Format Step 4 for non-custom modes: Triage (dispatch already happened in step 2)."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title="Triage", script="refactor", step=4)))
    parts.append("")

    # Use the triage actions from STEPS[5]
    actions = list(STEPS[5].get("actions", []))
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Non-custom: step 4 (triage) -> step 6 (cluster), skipping step 5
    parts.append(render_invoke_after(InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 6")))

    return "\n".join(parts)


def format_step_5_triage(info: dict) -> str:
    """Format Step 5: Triage output (custom mode path)."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=5)))
    parts.append("")

    actions = list(info.get("actions", []))
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    parts.append(render_invoke_after(InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 6")))

    return "\n".join(parts)


def format_step_6_cluster(info: dict) -> str:
    """Format Step 6: Cluster output."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=6)))
    parts.append("")

    actions = [format_cluster_prompt()]
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    parts.append(render_invoke_after(InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 7")))

    return "\n".join(parts)


def format_step_7_contextualize(info: dict) -> str:
    """Format Step 7: Contextualize output."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=7)))
    parts.append("")

    actions = [format_contextualize_prompt()]
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    parts.append(render_invoke_after(InvokeAfterNode(cmd=f"uv run python -m {MODULE_PATH} --step 8")))

    return "\n".join(parts)


def format_step_8_synthesize(info: dict) -> str:
    """Format Step 8: Synthesize output (terminal step)."""
    parts = []

    parts.append(render_step_header(StepHeaderNode(title=info["title"], script="refactor", step=8)))
    parts.append("")

    actions = [format_synthesize_prompt()]
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    parts.append("COMPLETE - Present work items to user with recommended sequence.")
    parts.append("")
    parts.append("The user can now:")
    parts.append("  - Execute work items in recommended order")
    parts.append("  - Ask to implement a specific work item")
    parts.append("  - Request adjustments to scope or approach")

    return "\n".join(parts)


def format_output(
    step: int,
    n: int = DEFAULT_CATEGORY_COUNT,
    mode_filter: str = "both",
    scope: str | None = None,
    retry: int = 0,
) -> str:
    """Format output for display. Dispatches based on step and mode.

    Step routing depends on mode:
    - Non-custom: 1 -> 2 -> [skip 3] -> 4 -> [skip 5] -> 6 -> 7 -> 8
    - Custom:     1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

    Step number semantics differ by mode:
    - Step 3: Custom only (verification)
    - Step 4: Custom = dispatch, Non-custom = triage
    - Step 5: Custom = triage (non-custom skips this, already did triage at step 4)
    """
    info = STEPS.get(step, STEPS[8])

    # Step 1: Mode selection (same for all modes, but needs scope)
    if step == 1:
        return format_step_1_output(n, info, mode_filter, scope)

    # Step 2: Mode-dependent
    # Custom: Category selection from embedded files
    # Non-custom: Random sampling and immediate dispatch
    if step == 2:
        if mode_filter == "custom":
            return format_step_2_custom(info, scope)
        else:
            return format_step_2_dispatch(n, info, mode_filter, scope)

    # Step 3: Verification (custom mode only)
    # Non-custom mode jumps from step 2 directly to step 4
    if step == 3:
        return format_step_3_verification(info, scope, retry)

    # Step 4: Semantically different per mode
    # Custom: Dispatch with verified categories
    # Non-custom: Triage (dispatch already happened in step 2)
    if step == 4:
        if mode_filter == "custom":
            return format_step_4_dispatch_custom(info, scope)
        else:
            return format_step_4_triage(info)

    # Step 5: Triage (custom mode path only)
    # Non-custom mode already did triage at step 4, jumps to step 6
    if step == 5:
        return format_step_5_triage(info)

    # Steps 6-8: Mode-agnostic
    if step == 6:
        return format_step_6_cluster(info)
    if step == 7:
        return format_step_7_contextualize(info)
    if step == 8:
        return format_step_8_synthesize(info)

    # Fallback
    return format_step_8_synthesize(info)


def main(
    step: int | None = None,
    n: int | None = None,
    mode: str | None = None,
    scope: str | None = None,
    retry: int | None = None,
):
    """Entry point with parameter annotations for testing framework.

    Note: Parameters have defaults because actual values come from argparse.
    The annotations are metadata for the testing framework.
    """
    parser = argparse.ArgumentParser(
        description="Refactor Skill - Category-based code smell detection and synthesis",
        epilog="Phases: mode selection -> dispatch/select -> [verify] -> triage -> cluster -> contextualize -> synthesize",
    )
    parser.add_argument("--step", type=int, required=True)

    # Number of random samples for non-custom modes
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_CATEGORY_COUNT,
        help=f"Number of targets for random modes (default: {DEFAULT_CATEGORY_COUNT}, ignored for custom)",
    )

    # Mode determines category selection strategy
    parser.add_argument(
        "--mode",
        type=str,
        choices=["design", "code", "both", "custom"],
        default="both",
        help="Category selection mode. custom: LLM selects based on problem statement",
    )

    # Filesystem constraint propagated to all explore agents
    parser.add_argument(
        "--scope",
        type=str,
        default=None,
        help="Filesystem scope constraint (e.g., 'src/planner/'). Propagates to explore agents.",
    )

    # Verification loopback counter (custom mode only, internal)
    parser.add_argument("--retry", type=int, default=0, help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.step > 8:
        sys.exit("ERROR: --step cannot exceed 8")
    if args.retry > 1:
        sys.exit("ERROR: --retry cannot exceed 1 (max one verification retry)")

    print(format_output(args.step, args.n, args.mode, args.scope, args.retry))


if __name__ == "__main__":
    main()
