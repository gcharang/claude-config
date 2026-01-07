# Workflow Abstraction Refactoring Plan

## Overview

The skills codebase has evolved a sophisticated workflow orchestration pattern. The planner skill developed excellent primitives (QRState, GateConfig, XML formatters) but they're trapped in `planner/scripts/shared/`, preventing reuse by other skills. Standalone skills (problem-analysis, decision-critic, refactor) duplicate this pattern; planner mode scripts (9 files in qr/, tw/, dev/) already use the shared module via sys.path manipulation.

This plan extracts workflow orchestration into a shared framework at `skills/lib/workflow/` with proper types (AgentRole, Routing, Dispatch, Step, WorkflowDefinition), a unified engine, and reusable formatters. The migration preserves all existing behavior while eliminating ~500+ lines of duplication.

## Planning Context

### Decision Log

| Decision                                                                   | Reasoning Chain                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Full framework extraction over minimal types-only                          | Types alone don't solve formatter duplication -> skills would still copy-paste XML functions -> full extraction provides single source of truth for all patterns                                                                                                                                                                  |
| Package at skills/lib/workflow/ over skills/shared/                        | lib/ signals "library code" vs application code -> follows Python convention for internal packages -> clear separation between framework and skills                                                                                                                                                                               |
| AgentRole as Enum over string literals                                     | String literals allow typos and invalid values -> Enum provides compile-time validation -> IDE autocomplete improves developer experience                                                                                                                                                                                         |
| Routing as union type (Linear/Branch/Terminal) over single class with mode | Union type makes invalid states unrepresentable -> pattern matching on routing type is explicit -> matches how routing is actually used (mutually exclusive modes)                                                                                                                                                                |
| Killed ConditionalRouting variant                                          | Only one instance found (executor.py reconciliation_check) -> adding variant for single case violates NO_SPECULATION -> can model as BranchRouting with named condition if needed later                                                                                                                                           |
| Stateless engine over stateful WorkflowEngine class                        | Pure function execute_step(context, config) -> output is easier to test -> no hidden state to manage -> matches current format_output pattern                                                                                                                                                                                     |
| Compatibility layer during migration                                       | Zero breaking changes initially -> skills can migrate incrementally -> rollback is simple if issues arise -> planner/scripts/shared/ re-exports from lib/workflow during transition                                                                                                                                               |
| Formatters as pure functions over template classes                         | Current formatters are pure (input -> XML string) -> keeping this pattern maintains testability -> no need for object-oriented abstraction                                                                                                                                                                                        |
| Testing strategy: integration with before/after diff                       | User-specified: output equivalence is the contract for this refactoring -> pure formatters produce deterministic output -> before/after diffing proves no behavior change -> property-based tests add value for complex formatters but integration tests are sufficient baseline                                                  |
| M0/M3 test skip                                                            | User-specified: M0 creates only type definitions with no logic -> types validated by usage in M1-M4 integration tests -> M3 CLI utilities are thin wrappers -> deferred validation in M5 integration tests is adequate risk                                                                                                       |
| free_form field in Dispatch                                                | Port from existing format_subagent_dispatch() parameter -> controls script mode vs free-form agent delegation -> False = agent follows script strictly, True = agent uses free-form instructions -> existing pattern in planner/scripts/shared/formatting.py:244                                                                  |
| QRState structure (iteration, failed, status)                              | Port unchanged from planner/scripts/shared/domain.py:17-31 -> iteration tracks QR loop count (1=initial, 2+=re-verify) -> failed indicates re-work from prior QR failure -> status is gate input ("pass"/"fail") -> both failed+status needed: failed is state entering step, status is result from previous step                 |
| Formatter research grounding (RE2, CoVe)                                   | Formatters implement patterns from RE2 (retrieval-augmented generation) and CoVe (chain-of-verification) research -> format_qr_banner uses fresh_review mode to prevent confirmation bias -> format_factored_verification implements CoVe's factored verification pattern -> docstrings preserve citations for future maintainers |
| Import mechanism: sys.path.insert in entry points                          | Each script entry point adds skills/ to sys.path -> no external environment dependency (PYTHONPATH not required) -> works in any invocation context -> matches existing pattern in planner mode scripts (sys.path.insert for shared/)                                                                                             |
| Explicit **all** in compatibility layer                                    | Implicit exports would include internal helpers -> breaks if shared/ adds private functions -> explicit list provides stable API contract -> maintenance cost acceptable for compatibility layer (temporary, removed in M10)                                                                                                      |

### Rejected Alternatives

| Alternative                              | Why Rejected                                                                                         |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Types-only extraction (Option A)         | Leaves XML formatters duplicated in 3+ skills; doesn't solve the core problem                        |
| New custom DSL for workflow definition   | Over-engineering; Python dataclasses provide sufficient structure with IDE support                   |
| YAML-based workflow configuration        | Adds parsing layer; Python dicts are already data-driven; YAML provides no benefit for this use case |
| Merge all skills into single package     | Violates skill isolation; skills should remain independently deployable                              |
| Keep planner/scripts/shared as canonical | Path implies planner-internal; other skills can't import without coupling to planner                 |

### Constraints & Assumptions

- **Python version**: 3.10+ (union types with `|` syntax used in domain.py)
- **No behavior change**: All scripts must produce identical output for same inputs
- **Incremental migration**: Skills migrate one at a time; old and new patterns coexist
- **Resource loading**: resources.py stays in planner/scripts/shared (skill-specific resource paths)
- **Import setup**: Each script entry point adds `sys.path.insert(0, str(Path(__file__).parent.parent.parent))` (or appropriate depth to reach skills/). No PYTHONPATH required. Pattern matches existing planner mode scripts.
- **Duplication accounting**: planner/scripts/shared/formatting.py (726 lines, 26 format\_\* functions), refactor/scripts/refactor.py (87 lines formatter duplication), refactor/scripts/explore.py (83 lines formatter duplication). Total extraction: ~550 lines. Functions to extract: format_step_header, format_current_action, format_invoke_after, format_step_output, format_subagent_dispatch, format_qr_banner, format_gate_step, format_resource, format_forbidden, format_routing, format_expected_output, format_verification_checklist, format_detection_questions, format_orchestrator_constraint, format_post_qr_routing, format_factored_verification_rationale, format_next_block, format_state_banner, format_gate_actions, format_xml_mandate (20 core functions)

### Known Risks

| Risk                                       | Mitigation                                                                      | Anchor                                                          |
| ------------------------------------------ | ------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| QR loop branching has subtle edge cases    | Port logic unchanged from formatting.py; before/after testing                   | planner/scripts/shared/formatting.py:659-725 (format_gate_step) |
| Import path changes break existing scripts | Compatibility layer re-exports from old location during transition              | Create planner/scripts/shared/**init**.py with re-exports       |
| WorkflowEngine complexity                  | Keep as pure functions, not class; port existing format_output logic verbatim   | planner/scripts/planner.py:502-560                              |
| Type changes break agent dispatch          | AgentRole.value returns original string; dispatch uses .value for compatibility | N/A - new code                                                  |

## Invisible Knowledge

### Architecture

```
skills/
  lib/
    __init__.py                    # Package marker
    workflow/
      __init__.py                  # Public API exports
      types.py                     # Domain types
      engine.py                    # Step execution
      formatters/
        __init__.py
        xml.py                     # XML formatters
        text.py                    # Plain text formatters
      cli.py                       # Argument parsing
  planner/
    scripts/
      shared/                      # Compatibility layer (re-exports)
      planner.py                   # Uses lib.workflow
      ...
  refactor/
    scripts/
      refactor.py                  # Uses lib.workflow
      ...
```

### Data Flow

```
CLI args --> parse_args() --> WorkflowContext
                                    |
                                    v
STEPS dict --> StepConfig lookup --> execute_step()
                                          |
                                          v
                               Format XML output --> print()
```

### Why This Structure

- **lib/workflow/**: Framework code that all skills can import
- **types.py separate from engine.py**: Types have no dependencies; engine imports types
- **formatters/ subdirectory**: Many formatters (20+); grouping prevents one huge file
- **Compatibility layer**: planner/scripts/shared re-exports from lib/workflow so existing imports work during migration

### Invariants

1. **Output equivalence**: For any (step, total_steps, qr_state) input, new engine must produce byte-identical output to old format_output
2. **Import compatibility**: `from shared import format_step_output` must work during transition
3. **Type safety**: AgentRole, Routing, Dispatch are exhaustive - no stringly-typed dispatch metadata

### Tradeoffs

- **Duplication during migration**: planner/scripts/shared temporarily re-exports from lib/workflow; removed after all skills migrate
- **More files**: lib/workflow has 7+ files vs 4 in planner/scripts/shared; cleaner separation is worth the overhead
- **Learning curve**: New skills must learn lib.workflow API; offset by reduced boilerplate

## Milestones

### Milestone 0: Foundation - Package Structure

**Files**:

- `skills/__init__.py` (new)
- `skills/lib/__init__.py` (new)
- `skills/lib/workflow/__init__.py` (new)
- `skills/lib/workflow/types.py` (new)

**Requirements**:

- Create skills/**init**.py package marker (enables `from skills.lib.workflow import ...`)
- Create skills/lib/ package with **init**.py
- Create skills/lib/workflow/ package with **init**.py
- Define core types: AgentRole, Routing variants, Dispatch, GateConfig, Step

**Acceptance Criteria**:

- `from skills.lib.workflow import AgentRole, Step` works
- AgentRole enum has all 5 agent types
- Routing is union of LinearRouting | BranchRouting | TerminalRouting
- All types are dataclasses with type hints

**Tests**:

- Skip: Foundation milestone creates structure only; types validated by usage in later milestones

**Code Intent**:

```
New file `skills/__init__.py`:
- Empty package marker (enables skills.lib.workflow imports)

New file `skills/lib/__init__.py`:
- Empty package marker

New file `skills/lib/workflow/__init__.py`:
- Re-export public API from types.py

New file `skills/lib/workflow/types.py`:
- AgentRole(Enum): QUALITY_REVIEWER, DEVELOPER, TECHNICAL_WRITER, EXPLORE, GENERAL_PURPOSE
- LinearRouting dataclass (empty - indicates step+1 routing)
- BranchRouting dataclass: if_pass: int, if_fail: int
- TerminalRouting dataclass (empty - indicates no continuation)
- Routing = LinearRouting | BranchRouting | TerminalRouting
- Dispatch dataclass: agent: AgentRole, script: str, total_steps: int, context_vars: dict[str, str], free_form: bool = False
- GateConfig dataclass: qr_name: str, work_step: int, pass_step: int | None, pass_message: str, self_fix: bool, fix_target: AgentRole | None = None
- QRState dataclass: iteration: int = 1, failed: bool = False, status: Literal["pass", "fail"] | None = None
- Step dataclass: title: str, actions: list[str], routing: Routing = field(default_factory=LinearRouting), dispatch: Dispatch | None = None, gate: GateConfig | None = None, phase: str | None = None
- WorkflowDefinition dataclass: name: str, script: str, steps: dict[int, Step], description: str = ""

NOTE: FlatCommand, BranchCommand, NextCommand remain in planner/scripts/shared/domain.py.
They are planner-specific guidance types, not framework primitives. M1 xml.py imports them from domain.py.
```

**Code Changes**:

```diff
--- /dev/null
+++ b/skills/__init__.py
@@ -0,0 +1 @@
+# Package marker - enables skills.lib.workflow imports
```

```diff
--- /dev/null
+++ b/skills/lib/__init__.py
@@ -0,0 +1 @@
+# Package marker for lib module
```

```diff
--- /dev/null
+++ b/skills/lib/workflow/__init__.py
@@ -0,0 +1,21 @@
+"""Workflow orchestration framework for skills.
+
+Public API for workflow types, formatters, and execution engine.
+"""
+
+from .types import (
+    AgentRole,
+    LinearRouting,
+    BranchRouting,
+    TerminalRouting,
+    Routing,
+    Dispatch,
+    GateConfig,
+    QRState,
+    Step,
+    WorkflowDefinition,
+)
+
+__all__ = [
+    "AgentRole", "LinearRouting", "BranchRouting", "TerminalRouting",
+    "Routing", "Dispatch", "GateConfig", "QRState", "Step", "WorkflowDefinition",
+]
```

```diff
--- /dev/null
+++ b/skills/lib/workflow/types.py
@@ -0,0 +1,96 @@
+"""Domain types for workflow orchestration.
+
+Explicit, composable abstractions over stringly-typed dicts and parameter groups.
+"""
+
+from dataclasses import dataclass, field
+from enum import Enum
+from typing import Literal
+
+
+# =============================================================================
+# Agent Role
+# =============================================================================
+
+
+class AgentRole(Enum):
+    """Agent types for sub-agent dispatch."""
+
+    QUALITY_REVIEWER = "quality-reviewer"
+    DEVELOPER = "developer"
+    TECHNICAL_WRITER = "technical-writer"
+    EXPLORE = "explore"
+    GENERAL_PURPOSE = "general-purpose"
+
+
+# =============================================================================
+# Routing
+# =============================================================================
+
+
+@dataclass
+class LinearRouting:
+    """Linear routing - proceed to step+1.
+
+    Empty dataclass: absence of routing config indicates linear progression.
+    """
+    pass
+
+
+@dataclass
+class BranchRouting:
+    """Conditional routing based on QR result."""
+
+    if_pass: int
+    if_fail: int
+
+
+@dataclass
+class TerminalRouting:
+    """Terminal routing - no continuation.
+
+    Empty dataclass: absence of next step indicates workflow completion.
+    """
+    pass
+
+
+Routing = LinearRouting | BranchRouting | TerminalRouting
+
+
+# =============================================================================
+# Dispatch
+# =============================================================================
+
+
+@dataclass
+class Dispatch:
+    """Sub-agent dispatch configuration."""
+
+    agent: AgentRole
+    script: str
+    total_steps: int
+    context_vars: dict[str, str] = field(default_factory=dict)
+    free_form: bool = False
+
+
+# =============================================================================
+# QR Loop State
+# =============================================================================
+
+
+@dataclass
+class QRState:
+    """Quality Review loop state.
+
+    iteration: Loop count (1=initial review, 2+=re-verification)
+    failed: True when entering step to fix prior QR issues
+    status: QR result from previous step ("pass"/"fail")
+
+    Both failed and status needed: failed is entry state, status is prior result.
+    """
+
+    iteration: int = 1
+    failed: bool = False
+    status: Literal["pass", "fail"] | None = None
+
+
+@dataclass
+class GateConfig:
+    """Configuration for a QR gate step.
+
+    self_fix controls routing: True -> agent fixes issues automatically,
+    False -> manual intervention required. fix_target specifies which agent
+    handles fixes when self_fix=True (defaults to developer if None).
+    """
+
+    qr_name: str
+    work_step: int
+    pass_step: int | None
+    pass_message: str
+    self_fix: bool
+    fix_target: AgentRole | None = None
+
+
+# =============================================================================
+# Step Configuration
+# =============================================================================
+
+
+@dataclass
+class Step:
+    """Step configuration for workflow."""
+
+    title: str
+    actions: list[str]
+    routing: Routing = field(default_factory=LinearRouting)
+    dispatch: Dispatch | None = None
+    gate: GateConfig | None = None
+    phase: str | None = None
+
+
+@dataclass
+class WorkflowDefinition:
+    """Complete workflow definition."""
+
+    name: str
+    script: str
+    steps: dict[int, Step]
+    description: str = ""
+```

---

### Milestone 1: Formatters - XML Functions

**Files**:

- `skills/lib/workflow/formatters/__init__.py` (new)
- `skills/lib/workflow/formatters/xml.py` (new)

**Flags**:

- `needs-rationale`: Formatters have research grounding (RE2, CoVe)

**Requirements**:

- Extract all XML formatters from planner/scripts/shared/formatting.py
- Preserve exact function signatures
- Preserve all docstrings including research citations
- Add module-level docstring explaining formatter composition pattern

**Acceptance Criteria**:

- All 20+ format\_\* functions available from lib.workflow.formatters
- Function signatures identical to original
- format_step_output produces same XML as original

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: user-specified
- **Scenarios**:
  - Core formatters: format_step_header, format_current_action, format_invoke_after, format_next_block (compare output with original formatting.py for identical inputs)
  - Complex formatters: format_step_output with flat command, branch command, gate result; format_gate_step with pass/fail QRState at iterations 1, 2, 3; format_qr_banner with fresh_review mode
  - Dispatch formatters: format_subagent_dispatch with script mode and free_form mode; format_orchestrator_constraint; format_post_qr_routing with self_fix True/False
  - Verification formatters: format_verification_checklist, format_detection_questions, format_expected_output, format_factored_verification_rationale
  - Utility formatters: format_resource, format_forbidden, format_routing, format_state_banner, format_gate_actions, format_xml_mandate

**Code Intent**:

```
New file `skills/lib/workflow/formatters/__init__.py`:
- Re-export all format_* functions from xml.py

New file `skills/lib/workflow/formatters/xml.py`:
- Copy all format_* functions from planner/scripts/shared/formatting.py
- Preserve docstrings, signatures, implementation
- Update imports to use types from skills.lib.workflow.types
- Key functions: format_step_header, format_current_action, format_invoke_after,
  format_step_output, format_subagent_dispatch, format_qr_banner, format_gate_step,
  format_resource, format_forbidden, format_routing, format_expected_output,
  format_verification_checklist, format_detection_questions, format_orchestrator_constraint,
  format_post_qr_routing, format_factored_verification_rationale
```

**Code Changes**:

```diff
--- /dev/null
+++ b/skills/lib/workflow/formatters/__init__.py
@@ -0,0 +1,30 @@
+"""Workflow formatters for XML and text output."""
+
+from .xml import (
+    format_step_header,
+    format_current_action,
+    format_invoke_after,
+    format_next_block,
+    format_gate_result,
+    format_xml_mandate,
+    format_step_output,
+    format_subagent_dispatch,
+    format_state_banner,
+    format_qr_banner,
+    format_expected_output,
+    format_forbidden,
+    format_routing,
+    format_post_qr_routing,
+    format_resource,
+    format_detection_questions,
+    format_verification_checklist,
+    format_incorrect_behavior,
+    format_orchestrator_constraint,
+    format_factored_verification_rationale,
+    format_open_question_guidance,
+    format_gate_actions,
+    format_gate_step,
+)
+
+__all__ = [
+    "format_step_header", "format_current_action", "format_invoke_after", "format_next_block",
+    "format_gate_result", "format_xml_mandate", "format_step_output", "format_subagent_dispatch",
+    "format_state_banner", "format_qr_banner", "format_expected_output", "format_forbidden",
+    "format_routing", "format_post_qr_routing", "format_resource", "format_detection_questions",
+    "format_verification_checklist", "format_incorrect_behavior", "format_orchestrator_constraint",
+    "format_factored_verification_rationale", "format_open_question_guidance",
+    "format_gate_actions", "format_gate_step",
+]
```

```diff
--- /dev/null
+++ b/skills/lib/workflow/formatters/xml.py
@@ -0,0 +1,734 @@
+"""XML formatting functions for workflow scripts.
+
+COMPOSITION PATTERN:
+
+The workflow framework uses a two-layer composition model for XML output:
+
+1. GUIDANCE LAYER: Functions return dicts with typed fields
+   - get_step_*_guidance() -> {"title": str, "actions": list[str], "next": str, ...}
+   - Actions list contains both plain strings AND XML blocks (from formatters)
+
+2. RENDERING LAYER: format_step_output() assembles final XML
+   - Takes dict fields as parameters
+   - Calls smaller XML formatters (format_step_header, format_current_action, etc.)
+   - Returns complete XML string via list + "\\n".join() pattern
+
+COMPOSABILITY:
+  actions = [
+      format_state_banner(...),    # Returns XML string
+      "",                          # Blank line (plain string)
+      "TASK: Do something",        # Plain string
+      format_forbidden([...]),     # Returns XML string
+  ]
+  This mixing works because all formatters return strings.
+
+ADDING NEW XML ELEMENTS:
+  1. Create format_*() function that returns XML string via list+join
+  2. Call it within actions list: actions.append(format_new_element(...))
+  3. If element belongs outside <current_action>, add parameter to format_step_output()
+"""
+
+from skills.lib.workflow.types import (
+    QRState,
+    GateConfig,
+)
+
+# Import planner-specific command types from domain.py
+# Planner-specific guidance types live in planner/scripts/shared/domain.py - not framework primitives
+from planner.scripts.shared.domain import (
+    FlatCommand,
+    BranchCommand,
+    NextCommand,
+)
+
+import sys
+from pathlib import Path
+
+# Add skills/ to path for cross-skill imports
+skills_dir = Path(__file__).parent.parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+# Import QR_ITERATION_LIMIT from planner resources
+# Runtime import decouples framework from planner-specific constants
+from planner.scripts.shared.resources import QR_ITERATION_LIMIT
+
+
+# =============================================================================
+# Core XML Formatters
+# =============================================================================
+
+
+def format_step_header(script: str, step: int, total: int, title: str, phase: str = None) -> str:
+    """Format the step header XML element.
+
+    Parameter order matters: callers depend on positional argument sequence.
+    """
+    script_attr = f' script="{script}"'
+    phase_attr = f' phase="{phase}"' if phase else ""
+    return f'<step_header{script_attr}{phase_attr} step="{step}" total="{total}">{title}</step_header>'
+
+
+def format_current_action(actions: list[str]) -> str:
+    """Format the current_action block."""
+    lines = ["<current_action>"]
+    lines.extend(actions)
+    lines.append("</current_action>")
+    return "\n".join(lines)
+
+
+def format_invoke_after(next_command: NextCommand, script: str = None) -> str:
+    """Format the invoke_after block with next command."""
+    if next_command is None:
+        return ""
+
+    if isinstance(next_command, FlatCommand):
+        return f"<invoke_after>\n{next_command.command}\n</invoke_after>"
+    elif isinstance(next_command, BranchCommand):
+        lines = [
+            "<invoke_after>",
+            "  <if_pass>",
+            f"    {next_command.if_pass}",
+            "  </if_pass>",
+            "  <if_fail>",
+            f"    {next_command.if_fail}",
+            "  </if_fail>",
+            "</invoke_after>",
+        ]
+        return "\n".join(lines)
+
+
+def format_next_block(next_command: NextCommand) -> str:
+    """Format the next step block (older pattern, prefer format_invoke_after)."""
+    if next_command is None:
+        return "<next>COMPLETE</next>"
+
+    if isinstance(next_command, FlatCommand):
+        return f"<next>{next_command.command}</next>"
+    elif isinstance(next_command, BranchCommand):
+        lines = [
+            "<next>",
+            f"  <if_pass>{next_command.if_pass}</if_pass>",
+            f"  <if_fail>{next_command.if_fail}</if_fail>",
+            "</next>",
+        ]
+        return "\n".join(lines)
+
+
+def format_gate_result(status: str) -> str:
+    """Format QR gate result."""
+    return f'<gate_result status="{status}" />'
+
+
+def format_xml_mandate() -> str:
+    """Format XML format mandate block."""
+    return """<xml_format_mandate>
+CRITICAL: All script outputs use XML format. You MUST:
+
+1. Execute the action in <current_action>
+2. When complete, invoke the exact command in <invoke_after>
+3. The <next> block re-states the command -- execute it
+4. For branching <invoke_after>, choose based on outcome:
+   - <if_pass>: Use when action succeeded / QR returned PASS
+   - <if_fail>: Use when action failed / QR returned ISSUES
+
+DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
+</xml_format_mandate>"""
+
+
+def format_step_output(
+    script: str,
+    step: int,
+    total: int,
+    title: str,
+    actions: list[str],
+    next_command: NextCommand,
+    is_step_one: bool = False,
+) -> str:
+    """Format complete step output with header, actions, and next command."""
+    lines = [format_step_header(step, total, title, script)]
+
+    if is_step_one:
+        lines.append("")
+        lines.append(format_xml_mandate())
+
+    lines.append("")
+    lines.append(format_current_action(actions))
+    lines.append("")
+    lines.append(format_invoke_after(next_command, script))
+
+    return "\n".join(lines)
+
+
+def format_subagent_dispatch(
+    agent: str,
+    script_path: str,
+    step: int,
+    total_steps: int,
+    context_vars: dict = None,
+    free_form: bool = False,
+) -> str:
+    """Format subagent dispatch block."""
+    lines = [f'<subagent_dispatch agent="{agent}">']
+
+    if free_form:
+        lines.append(f'  <mode>free_form</mode>')
+    else:
+        lines.append(f'  <mode>script</mode>')
+
+    lines.append(f'  <script>{script_path}</script>')
+    lines.append(f'  <step>{step}</step>')
+    lines.append(f'  <total_steps>{total_steps}</total_steps>')
+
+    if context_vars:
+        lines.append('  <context_vars>')
+        for k, v in context_vars.items():
+            lines.append(f'    <var name="{k}">{v}</var>')
+        lines.append('  </context_vars>')
+
+    lines.append('</subagent_dispatch>')
+    return "\n".join(lines)
+
+
+def format_state_banner(checkpoint: str, iteration: int, mode: str) -> str:
+    """Format state banner showing QR loop iteration."""
+    return f'<state_banner checkpoint="{checkpoint}" iteration="{iteration}" mode="{mode}">\n</state_banner>'
+
+
+def format_qr_banner(qr: QRState, qr_name: str, fresh_review: bool = False) -> str:
+    """Format QR verification banner.
+
+    Implements CoVe (Chain-of-Verification) pattern to prevent confirmation bias.
+    When fresh_review=True, prompts QR agent to ignore prior findings.
+    """
+    if qr.iteration == 1:
+        return f"{qr_name.upper()}: Review the work for issues."
+
+    mode = "fresh review" if fresh_review else "re-verify fixes"
+    return f"{qr_name.upper()} (Iteration {qr.iteration}, {mode}): Previous review found issues."
+
+
+def format_expected_output(items: list[str]) -> str:
+    """Format expected output block."""
+    lines = ["<expected_output>"]
+    for item in items:
+        lines.append(f"  - {item}")
+    lines.append("</expected_output>")
+    return "\n".join(lines)
+
+
+def format_forbidden(items: list[str]) -> str:
+    """Format forbidden actions block."""
+    lines = ["<forbidden>"]
+    for item in items:
+        lines.append(f"  - {item}")
+    lines.append("</forbidden>")
+    return "\n".join(lines)
+
+
+def format_routing(next_command: NextCommand) -> str:
+    """Format routing information."""
+    if next_command is None:
+        return "<routing>Terminal - no continuation</routing>"
+
+    if isinstance(next_command, FlatCommand):
+        return f"<routing>Linear -> {next_command.command}</routing>"
+    elif isinstance(next_command, BranchCommand):
+        return f"<routing>Branch -> pass={next_command.if_pass}, fail={next_command.if_fail}</routing>"
+
+
+def format_post_qr_routing(
+    qr: QRState, gate: GateConfig, work_script: str
+) -> str:
+    """Format post-QR routing explanation."""
+    lines = ["<post_qr_routing>"]
+
+    if gate.self_fix:
+        lines.append(f"  Self-fix enabled: {gate.fix_target or 'developer'} will fix issues")
+    else:
+        lines.append("  Manual fix: Issues block progression")
+
+    lines.append(f"  PASS -> {gate.pass_step if gate.pass_step else 'COMPLETE'}")
+    lines.append(f"  FAIL -> Step {gate.work_step} (--qr-fail --qr-iteration {qr.iteration + 1})")
+    lines.append("</post_qr_routing>")
+    return "\n".join(lines)
+
+
+def format_resource(name: str, content: str) -> str:
+    """Format embedded resource block."""
+    return f'<resource name="{name}">\n{content}\n</resource>'
+
+
+def format_detection_questions(questions: list[str]) -> str:
+    """Format detection questions block."""
+    lines = ["<detection_questions>"]
+    for q in questions:
+        lines.append(f"  - {q}")
+    lines.append("</detection_questions>")
+    return "\n".join(lines)
+
+
+def format_verification_checklist(items: list[str]) -> str:
+    """Format verification checklist."""
+    lines = ["<verification_checklist>"]
+    for item in items:
+        lines.append(f"  - {item}")
+    lines.append("</verification_checklist>")
+    return "\n".join(lines)
+
+
+def format_incorrect_behavior(examples: list[str]) -> str:
+    """Format incorrect behavior examples."""
+    lines = ["<incorrect_behavior>"]
+    for ex in examples:
+        lines.append(f"  - {ex}")
+    lines.append("</incorrect_behavior>")
+    return "\n".join(lines)
+
+
+def format_orchestrator_constraint(text: str) -> str:
+    """Format orchestrator constraint block."""
+    return f"<orchestrator_constraint>\n{text}\n</orchestrator_constraint>"
+
+
+def format_factored_verification_rationale(rationale: str) -> str:
+    """Format factored verification rationale.
+
+    Implements CoVe (Chain-of-Verification) factored verification pattern.
+    Separates verification into independent sub-questions to reduce bias.
+    """
+    return f"<factored_verification_rationale>\n{rationale}\n</factored_verification_rationale>"
+
+
+def format_open_question_guidance(text: str) -> str:
+    """Format open-ended question guidance."""
+    return f"<open_question_guidance>\n{text}\n</open_question_guidance>"
+
+
+def format_gate_actions(
+    qr: QRState,
+    pass_message: str,
+    self_fix: bool,
+    fix_target: str = None,
+    iteration_limit: int = None,
+) -> list[str]:
+    """Build actions list for a gate step.
+
+    Returns actions that route based on QR status.
+    Uses QR_ITERATION_LIMIT if iteration_limit parameter not provided.
+    """
+    limit = iteration_limit or QR_ITERATION_LIMIT
+
+    if qr.status == "pass":
+        return [pass_message]
+    elif qr.status == "fail":
+        if qr.iteration >= limit:
+            return [f"QR failed {limit} times. Manual intervention required."]
+        if self_fix:
+            agent = fix_target or "developer"
+            return [f"QR found issues. Routing to {agent} for fixes (--qr-fail --qr-iteration {qr.iteration + 1})."]
+        else:
+            return ["QR found issues. Fix manually and re-run workflow."]
+    else:
+        return ["ERROR: Gate step requires --qr-status=pass or --qr-status=fail"]
+
+
+def format_gate_step(
+    script: str,
+    step: int,
+    total: int,
+    title: str,
+    qr: QRState,
+    gate: GateConfig,
+    iteration_limit: int = None,
+) -> str:
+    """Format complete QR gate step with routing logic.
+
+    Implements the Three Pillars pattern: state banner, stop condition, re-verify mode.
+    """
+    actions = format_gate_actions(qr, gate.pass_message, gate.self_fix, gate.fix_target, iteration_limit)
+
+    # Determine next command based on QR status
+    if qr.status == "pass":
+        if gate.pass_step:
+            next_command = FlatCommand(command=f"python3 {script} --step {gate.pass_step} --total-steps {total}")
+        else:
+            next_command = None  # Terminal
+    elif qr.status == "fail":
+        next_command = FlatCommand(
+            command=f"python3 {script} --step {gate.work_step} --total-steps {total} --qr-fail --qr-iteration {qr.iteration + 1}"
+        )
+    else:
+        # No status - gate step must be invoked with --qr-status
+        next_command = None
+
+    return format_step_output(
+        script=script,
+        step=step,
+        total=total,
+        title=title,
+        actions=actions,
+        next_command=next_command,
+    )
+```

---

### Milestone 2: Formatters - Text Functions

**Files**:

- `skills/lib/workflow/formatters/text.py` (new)

**Requirements**:

- Create simple text formatters for skills that don't use XML (problem-analysis, decision-critic)
- format_text_output: simple step header + actions + next step
- Preserve exact output format of existing simple skills

**Acceptance Criteria**:

- problem-analysis output unchanged when using text formatter
- decision-critic output unchanged when using text formatter

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: user-specified
- **Scenarios**:
  - format_text_output with step 1/4, step 2/4, step 4/4 (terminal) - compare with problem-analysis/analyze.py output
  - format_text_output with step 1/7, step 7/7 - compare with decision-critic output
  - format_text_step_header with and without brief parameter

**Code Intent**:

```
New file `skills/lib/workflow/formatters/text.py`:
- format_text_step_header(step, total, title, brief=None) -> str
- format_text_output(step, total, title, actions, next_title=None) -> str
  - Returns plain text format matching problem-analysis/decision-critic output
  - "STEP N/TOTAL: Title\n  Brief\n\nDO:\n  actions...\n\nNEXT: Step N+1 - Title"
```

**Code Changes**:

```diff
--- /dev/null
+++ b/skills/lib/workflow/formatters/text.py
@@ -0,0 +1,48 @@
+"""Plain text formatters for simple workflow output.
+
+Used by skills that don't require XML structure (problem-analysis, decision-critic).
+"""
+
+
+def format_text_step_header(step: int, total: int, title: str, brief: str = None) -> str:
+    """Format a plain text step header.
+
+    Args:
+        step: Current step number
+        total: Total steps
+        title: Step title
+        brief: Optional brief description
+
+    Returns:
+        Plain text header string
+    """
+    lines = [f"STEP {step}/{total}: {title}"]
+    if brief:
+        lines.append(f"  {brief}")
+    return "\n".join(lines)
+
+
+def format_text_output(
+    step: int,
+    total: int,
+    title: str,
+    actions: list[str],
+    brief: str = None,
+    next_title: str = None,
+) -> str:
+    """Format complete plain text step output.
+
+    Matches output format of problem-analysis and decision-critic skills.
+    """
+    lines = [format_text_step_header(step, total, title, brief), "", "DO:"]
+
+    for action in actions:
+        if action:
+            lines.append(f"  {action}")
+        else:
+            lines.append("")
+
+    lines.append("")
+    if step >= total:
+        lines.append("COMPLETE - Present results to user.")
+    elif next_title:
+        lines.append(f"NEXT: Step {step + 1} - {next_title}")
+
+    return "\n".join(lines)
+```

---

### Milestone 3: CLI Utilities

**Files**:

- `skills/lib/workflow/cli.py` (new)

**Requirements**:

- Extract add_qr_args from planner/scripts/shared/cli.py
- Extract mode_main from planner/scripts/shared/cli.py
- Create workflow_main for simpler workflows (no QR args)

**Acceptance Criteria**:

- add_qr_args adds --qr-iteration, --qr-fail, --qr-status
- mode_main works with get_step_guidance callback pattern
- workflow_main works for simple STEPS dict workflows

**Tests**:

- Skip: CLI utilities validated by integration in milestone 5+

**Code Intent**:

```
New file `skills/lib/workflow/cli.py`:
- add_qr_args(parser): Add --qr-iteration, --qr-fail, --qr-status to ArgumentParser
- mode_main(script_file, get_step_guidance, description, extra_args=None):
  Copy from planner/scripts/shared/cli.py
  Update imports to use lib.workflow types and formatters
```

**Code Changes**:

```diff
--- /dev/null
+++ b/skills/lib/workflow/cli.py
@@ -0,0 +1,71 @@
+"""CLI utilities for workflow scripts.
+
+Handles argument parsing and mode script entry points.
+"""
+
+import argparse
+import os
+import sys
+from pathlib import Path
+from typing import Callable
+
+from .formatters import format_step_output
+
+
+def add_qr_args(parser: argparse.ArgumentParser) -> None:
+    """Add standard QR verification arguments to argument parser.
+
+    Used by orchestrator scripts (planner.py, executor.py, wave-executor.py)
+    to ensure consistent QR-related CLI flags.
+    """
+    parser.add_argument("--qr-iteration", type=int, default=1)
+    parser.add_argument("--qr-fail", action="store_true",
+                        help="Work step is fixing QR issues")
+    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"],
+                        help="QR result for gate steps")
+
+
+def mode_main(
+    script_file: str,
+    get_step_guidance: Callable[..., dict],
+    description: str,
+    extra_args: list[tuple[list, dict]] = None,
+):
+    """Standard entry point for mode scripts.
+
+    Args:
+        script_file: Pass __file__ from the calling script
+        get_step_guidance: Function that returns guidance dict for each step
+        description: Script description for --help
+        extra_args: Additional arguments beyond standard QR args
+    """
+    script_name = Path(script_file).stem
+
+    parser = argparse.ArgumentParser(description=description)
+    parser.add_argument("--step", type=int, required=True)
+    parser.add_argument("--total-steps", type=int, required=True)
+    parser.add_argument("--qr-iteration", type=int, default=1)
+    parser.add_argument("--qr-fail", action="store_true")
+    for args, kwargs in (extra_args or []):
+        parser.add_argument(*args, **kwargs)
+    parsed = parser.parse_args()
+
+    script_path = os.path.abspath(sys.argv[0])
+
+    guidance = get_step_guidance(
+        parsed.step, parsed.total_steps, script_path,
+        **{k: v for k, v in vars(parsed).items()
+           if k not in ('step', 'total_steps')}
+    )
+
+    # Handle both dict and dataclass (GuidanceResult) returns
+    # Scripts use different patterns - some return dicts, others return GuidanceResult
+    if hasattr(guidance, '__dataclass_fields__'):
+        # GuidanceResult dataclass - convert to dict
+        guidance_dict = {
+            "title": guidance.title,
+            "actions": guidance.actions,
+            "next": guidance.next,
+        }
+    else:
+        # Already a dict
+        guidance_dict = guidance
+
+    print(format_step_output(
+        script=script_name,
+        step=parsed.step,
+        total=parsed.total_steps,
+        title=guidance_dict["title"],
+        actions=guidance_dict["actions"],
+        next_command=guidance_dict["next"],
+        is_step_one=(parsed.step == 1),
+    ))
+
+
+```

---

### Milestone 4: Engine - Step Execution [DEFERRED]

**Status**: DEFERRED - QR feedback shows M5-M8 use formatters directly without engine layer

**Files**:

- `skills/lib/workflow/engine.py` (WILL NOT CREATE)

**Rationale for deferral**:

QR-Code review identified that M5-M8 diffs use format_text_output() and format_step_output() directly from formatters, bypassing any engine abstraction. The engine.py layer would add complexity without providing value for the current migration. Revisit if future workflows need centralized step execution logic.

**Original requirements** (preserved for reference):

- execute_step function that interprets StepConfig and produces output
- handle_qr_step for QR verification steps
- handle_gate_step for gate routing steps
- handle_dispatch_step for sub-agent dispatch steps

**Code Changes**: None (milestone deferred)

---

### Milestone 5: Compatibility Layer

**Files**:

- `skills/planner/scripts/shared/__init__.py` (modify)

**Requirements**:

- Re-export all public API from skills.lib.workflow
- Existing imports continue to work: `from shared import format_step_output`
- Add deprecation comment noting migration path

**Acceptance Criteria**:

- All existing planner scripts work without modification
- `from shared import QRState, format_step_output` works
- `from shared.formatting import format_step_output` works

**Tests**:

- **Test type**: integration
- **Backing**: default-derived
- **Scenarios**:
  - planner.py --step 1 --total-steps 12 produces unchanged output
  - qr/plan-completeness.py --step 1 --total-steps 6 produces unchanged output

**Code Intent**:

```
Modify `skills/planner/scripts/shared/__init__.py`:
- Add imports from skills.lib.workflow.types (all types)
- Add imports from skills.lib.workflow.formatters (all formatters)
- Add imports from skills.lib.workflow.cli (add_qr_args, mode_main)
- Explicit __all__ list for backwards compatibility:
  Types: AgentRole, LinearRouting, BranchRouting, TerminalRouting, Routing, Dispatch, GateConfig, QRState, Step, WorkflowDefinition, FlatCommand, BranchCommand, NextCommand, GuidanceResult
  Formatters: format_step_header, format_current_action, format_invoke_after, format_next_block, format_step_output, format_subagent_dispatch, format_qr_banner, format_gate_step, format_resource, format_forbidden, format_routing, format_expected_output, format_verification_checklist, format_detection_questions, format_orchestrator_constraint, format_post_qr_routing, format_factored_verification_rationale, format_state_banner, format_gate_actions, format_xml_mandate
  CLI: add_qr_args, mode_main
- Add comment: "# Compatibility layer - migrate to skills.lib.workflow"
```

**Code Changes**:

Add sys.path setup at top of `skills/planner/scripts/shared/__init__.py`:

```diff
--- a/skills/planner/scripts/shared/__init__.py
+++ b/skills/planner/scripts/shared/__init__.py
@@ -1,27 +1,53 @@
 """Shared utilities for planner scripts.

+Re-exports workflow types and formatters from skills.lib.workflow.
+Provides convenient imports: `from shared import QRState, format_step_output`

 QR Gate Pattern for Verification Loops:
   Every QR step is followed by a GATE step that:
   1. Takes --qr-status=pass|fail as input
   2. Outputs the EXACT next command to invoke
   3. Leaves no room for interpretation

   Work steps that follow a FAIL gate take --qr-fail flag to focus on fixing.

 This pattern is applied consistently across:
   - planner.py (steps 5-12: sequential QR with gates)
   - executor.py (step 4-5: holistic QR with gate)
   - wave-executor.py (steps 2-3: batch QR with gate)
 """

-# Re-export from domain
-from .domain import (
+import sys
+from pathlib import Path
+
+# Add skills/ to path for lib.workflow imports
+# Path depth: shared/__init__.py -> scripts -> planner -> skills (4 levels up)
+skills_dir = Path(__file__).parent.parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+# Re-export workflow types and formatters from skills.lib.workflow
+from skills.lib.workflow.types import (
+    AgentRole,
+    LinearRouting,
+    BranchRouting,
+    TerminalRouting,
+    Routing,
+    Dispatch,
+    GateConfig,
     QRState,
-    FlatCommand,
-    BranchCommand,
-    NextCommand,
-    GuidanceResult,
-    GateConfig,
+    Step,
+    WorkflowDefinition,
+)
+
+# Planner-specific guidance types from domain.py (GuidanceResult, FlatCommand, etc.)
+from .domain import (
+    FlatCommand,
+    BranchCommand,
+    NextCommand,
+    GuidanceResult,
 )

 # Re-export from resources
@@ -37,7 +63,7 @@
 )

-# Re-export from formatting
-from .formatting import (
+# Re-export from skills.lib.workflow.formatters
+from skills.lib.workflow.formatters import (
     format_step_header,
     format_current_action,
     format_invoke_after,
@@ -63,7 +89,7 @@
     format_gate_step,
 )

-# Re-export from cli
-from .cli import (
+# Re-export from skills.lib.workflow.cli
+from skills.lib.workflow.cli import (
     add_qr_args,
     mode_main,
 )
```

---

### Milestone 6: Migrate Problem-Analysis

**Files**:

- `skills/problem-analysis/scripts/analyze.py` (modify)

**Requirements**:

- Convert STEPS dict to use Step dataclass
- Replace custom format_output with workflow_main or engine
- Remove duplicate code

**Acceptance Criteria**:

- `python3 analyze.py --step 1 --total-steps 4` produces identical output
- All 4 steps produce identical output
- Code reduced by ~50 lines

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: default-derived
- **Scenarios**:
  - Step 1 output unchanged
  - Step 4 (terminal) output unchanged

**Code Intent**:

```
Modify `skills/problem-analysis/scripts/analyze.py`:
- Add import: from skills.lib.workflow import Step, TerminalRouting, workflow_main
- Convert STEPS dict entries to Step dataclass instances
- Replace format_output function with call to workflow engine
- Replace main() with workflow_main(STEPS, "analyze", "Problem Analysis")
- Remove ~80 lines of boilerplate (format_output, argparse, validation)
```

**Code Changes**:

```diff
--- a/skills/problem-analysis/scripts/analyze.py
+++ b/skills/problem-analysis/scripts/analyze.py
@@ -19,8 +19,18 @@
 """

 import argparse
 import sys
+from pathlib import Path
+
+# Add skills/ to path for lib.workflow imports
+skills_dir = Path(__file__).parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+from skills.lib.workflow.formatters.text import format_text_output
+from skills.lib.workflow.types import Step, TerminalRouting


 STEPS = {
     1: {
@@ -119,66 +129,23 @@
 }


-def format_output(step: int, total_steps: int) -> str:
-    """Format compact output for display."""
-    # Extra steps go to Verify (where accuracy improves most)
-    if step > 4 and step < total_steps:
-        info = STEPS[3]  # Extra verification rounds
-    elif step >= total_steps:
-        info = STEPS[4]  # Final synthesis
-    else:
-        info = STEPS.get(step, STEPS[4])
-
-    is_complete = step >= total_steps
-
-    lines = [
-        f"PROBLEM ANALYSIS - Step {step}/{total_steps}: {info['title']}",
-        f"  {info['brief']}",
-        "",
-        "DO:",
-    ]
-
-    for action in info["actions"]:
-        if action:
-            lines.append(f"  {action}")
-        else:
-            lines.append("")
-
-    lines.append("")
-
-    if is_complete:
-        lines.append("COMPLETE - Present recommendation to user.")
-    else:
-        next_step = step + 1
-        if next_step > 4 and next_step < total_steps:
-            next_info = STEPS[3]
-        elif next_step >= total_steps:
-            next_info = STEPS[4]
-        else:
-            next_info = STEPS.get(next_step, STEPS[4])
-        lines.append(f"NEXT: Step {next_step} - {next_info['title']}")
-
-    return "\n".join(lines)
-
-
 def main():
     parser = argparse.ArgumentParser(
         description="Problem Analysis - Compact reasoning workflow",
         epilog="Phases: define (1) -> explore (2) -> verify (3) -> synthesize (4)",
     )
     parser.add_argument("--step", type=int, required=True)
     parser.add_argument("--total-steps", type=int, required=True)
     args = parser.parse_args()

     if args.step < 1:
         sys.exit("ERROR: --step must be >= 1")
     if args.total_steps < 4:
         sys.exit("ERROR: --total-steps must be >= 4")
     if args.step > args.total_steps:
         sys.exit("ERROR: --step cannot exceed --total-steps")

-    print(format_output(args.step, args.total_steps))
+    # Use shared text formatter
+    info = STEPS.get(args.step if args.step <= 4 else (3 if args.step < args.total_steps else 4))
+    next_info = STEPS.get(args.step + 1 if args.step + 1 <= 4 else 4) if args.step < args.total_steps else None
+    print(format_text_output(
+        step=args.step,
+        total=args.total_steps,
+        title=f"PROBLEM ANALYSIS - {info['title']}",
+        actions=info["actions"],
+        brief=info["brief"],
+        next_title=next_info["title"] if next_info else None,
+    ))


 if __name__ == "__main__":
```

---

### Milestone 7: Migrate Decision-Critic

**Files**:

- `skills/decision-critic/scripts/decision-critic.py` (modify)

**Requirements**:

- Convert STEPS dict to use Step dataclass
- Use workflow_main for CLI handling
- Preserve --decision argument handling

**Acceptance Criteria**:

- `python3 decision-critic.py --step 1 --total-steps 7 --decision "test"` produces identical output
- All 7 steps produce identical output

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: default-derived
- **Scenarios**:
  - Step 1 with decision text
  - Step 7 (terminal) synthesis

**Code Intent**:

```
Modify `skills/decision-critic/scripts/decision-critic.py`:
- Add import: from skills.lib.workflow import Step, TerminalRouting
- Convert STEPS dict entries to Step dataclass instances
- Modify workflow_main to accept extra_args for --decision
- Remove format_output and main() boilerplate
```

**Code Changes**:

Similar pattern to M6 - add sys.path setup, import format_text_output, replace format_output function with format_text_output call.

```diff
--- a/skills/decision-critic/scripts/decision-critic.py
+++ b/skills/decision-critic/scripts/decision-critic.py
@@ -18,8 +18,18 @@

 import argparse
 import sys
+from pathlib import Path
+
+# Add skills/ to path for lib.workflow imports
+skills_dir = Path(__file__).parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+from skills.lib.workflow.formatters.text import format_text_output
+from skills.lib.workflow.types import Step, TerminalRouting


 STEPS = {
@@ -166,39 +176,6 @@
 }


-def format_output(step: int, total_steps: int, decision: str = None) -> str:
-    """Format output for display."""
-    info = STEPS.get(step, STEPS[7])
-    is_complete = step >= total_steps
-
-    lines = []
-
-    if step == 1 and decision:
-        lines.extend([
-            "DECISION UNDER REVIEW:",
-            decision,
-            "",
-        ])
-
-    lines.extend([
-        f"DECISION CRITIC - Step {step}/{total_steps}: {info['title']}",
-        f"Phase: {info['phase']}",
-        "",
-        "DO:",
-    ])
-
-    for action in info["actions"]:
-        if action:
-            lines.append(f"  {action}")
-        else:
-            lines.append("")
-
-    lines.append("")
-
-    if is_complete:
-        lines.append("COMPLETE - Present verdict to user.")
-    else:
-        next_info = STEPS.get(step + 1, STEPS[7])
-        lines.append(f"NEXT: Step {step + 1} - {next_info['title']}")
-
-    return "\n".join(lines)
-
-
 def main():
     parser = argparse.ArgumentParser(
         description="Decision Critic - Structured criticism workflow",
@@ -222,7 +199,19 @@
     if args.step == 1 and not args.decision:
         sys.exit("Error: --decision required for step 1")

-    print(format_output(args.step, args.total_steps, args.decision))
+    info = STEPS.get(args.step, STEPS[7])
+    next_info = STEPS.get(args.step + 1, STEPS[7]) if args.step < args.total_steps else None
+
+    # Add decision context to actions for step 1
+    actions = info["actions"]
+    if args.step == 1 and args.decision:
+        actions = [f"DECISION UNDER REVIEW: {args.decision}", ""] + actions
+
+    print(format_text_output(
+        step=args.step,
+        total=args.total_steps,
+        title=f"DECISION CRITIC - {info['title']}",
+        actions=actions,
+        brief=f"Phase: {info['phase']}",
+        next_title=next_info["title"] if next_info else None,
+    ))
```

---

### Milestone 8: Migrate Refactor Skill

**Files**:

- `skills/refactor/scripts/refactor.py` (modify)
- `skills/refactor/scripts/explore.py` (modify)

**Flags**:

- `conformance`: Must preserve parallel dispatch pattern

**Requirements**:

- Remove duplicate XML formatters from refactor.py and explore.py
- Import formatters from skills.lib.workflow.formatters
- Convert STEPS dict to use Step dataclass where applicable

**Acceptance Criteria**:

- `python3 refactor.py --step 1 --total-steps 7` produces identical output
- `python3 explore.py --step 1 --total-steps 2 --dimension naming` produces identical output
- ~100 lines removed (duplicate formatters)

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: default-derived
- **Scenarios**:
  - refactor.py step 1 (parallel dispatch)
  - refactor.py step 2 (triage)
  - explore.py step 1 (dimension exploration)

**Code Intent**:

```
Modify `skills/refactor/scripts/refactor.py`:
- Remove local format_step_header, format_xml_mandate, format_current_action, format_invoke_after
- Add import: from skills.lib.workflow.formatters import (format_step_header, ...)
- Keep STEPS dict structure (complex dimension logic)
- Keep format_parallel_dispatch (refactor-specific)

Modify `skills/refactor/scripts/explore.py`:
- Remove local format_* functions
- Add import: from skills.lib.workflow.formatters import (...)
- Keep dimension-specific logic
```

**Code Changes**:

```diff
--- a/skills/refactor/scripts/refactor.py
+++ b/skills/refactor/scripts/refactor.py
@@ -18,7 +18,17 @@
 import argparse
 import os
 import sys
+from pathlib import Path

+# Add skills/ to path for lib.workflow imports
+skills_dir = Path(__file__).parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+from skills.lib.workflow.formatters import (
+    format_step_header,
+    format_xml_mandate,
+    format_current_action,
+    format_invoke_after,
+)

 PHILOSOPHY = """
 REFACTORING PHILOSOPHY (apply throughout):
@@ -50,35 +60,6 @@
 # =============================================================================


-def format_step_header(step: int, total: int, title: str) -> str:
-    """Render step header."""
-    return f'<step_header script="refactor" step="{step}" total="{total}">{title}</step_header>'
-
-
-def format_xml_mandate() -> str:
-    """Return first-step guidance about XML format."""
-    return """<xml_format_mandate>
-CRITICAL: All script outputs use XML format. You MUST:
-
-1. Execute the action in <current_action>
-2. When complete, invoke the exact command in <invoke_after>
-
-DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
-</xml_format_mandate>"""
-
-
-def format_current_action(actions: list[str]) -> str:
-    """Render current action block."""
-    lines = ["<current_action>"]
-    lines.extend(actions)
-    lines.append("</current_action>")
-    return "\n".join(lines)
-
-
-def format_invoke_after(command: str) -> str:
-    """Render invoke after block."""
-    return f"<invoke_after>\n{command}\n</invoke_after>"
-
-
 def format_parallel_dispatch(explore_script_path: str) -> str:
     """Format the parallel dispatch block for step 1."""
     lines = [f'<parallel_dispatch agent="Explore" count="{len(DIMENSIONS)}">']
```

```diff
--- a/skills/refactor/scripts/explore.py
+++ b/skills/refactor/scripts/explore.py
@@ -13,7 +13,17 @@
 import argparse
 import os
 import sys
+from pathlib import Path

+# Add skills/ to path for lib.workflow imports
+skills_dir = Path(__file__).parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+from skills.lib.workflow.formatters import (
+    format_current_action,
+    format_invoke_after,
+)
+
 # Import shared dimension definitions
 from dimensions import DIMENSION_ORDER

@@ -24,35 +34,6 @@


-def format_step_header(step: int, total: int, title: str, dimension: str) -> str:
-    """Render step header with dimension context."""
-    return f'<step_header script="explore" step="{step}" total="{total}" dimension="{dimension}">{title}</step_header>'
-
-
-def format_xml_mandate() -> str:
-    """Return first-step guidance about XML format."""
-    return """<xml_format_mandate>
-CRITICAL: All script outputs use XML format. You MUST:
-
-1. Execute the action in <current_action>
-2. When complete, invoke the exact command in <invoke_after>
-
-DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
-</xml_format_mandate>"""
-
-
-def format_current_action(actions: list[str]) -> str:
-    """Render current action block."""
-    lines = ["<current_action>"]
-    lines.extend(actions)
-    lines.append("</current_action>")
-    return "\n".join(lines)
-
-
-def format_invoke_after(command: str) -> str:
-    """Render invoke after block."""
-    return f"<invoke_after>\n{command}\n</invoke_after>"
-
-
 def format_heuristics(heuristics: list[str]) -> str:
     """Format heuristics as XML."""
     lines = ['<heuristics exemplary="true" note="illustrative, not exhaustive">']
```

---

### Milestone 9: Documentation

**Delegated to**: @agent-technical-writer (mode: post-implementation)

**Source**: `## Invisible Knowledge` section of this plan

**Files**:

- `skills/lib/workflow/README.md` (new)
- `skills/lib/workflow/CLAUDE.md` (new)
- `skills/lib/CLAUDE.md` (new)

**Requirements**:

CLAUDE.md (lib/workflow/):

- Tabular index of all files in lib/workflow/
- One sentence overview
- No prose sections

README.md (lib/workflow/):

- Architecture diagram from Invisible Knowledge
- Data flow explanation
- "Why This Structure" section
- Usage examples for common patterns
- Migration guide from planner/scripts/shared

**Acceptance Criteria**:

- CLAUDE.md is tabular index only
- README.md is self-contained
- Architecture diagram matches implementation

**Code Intent**:

Documentation milestone - no code changes.

**Code Changes**: N/A

---

### Milestone 9.5: Migrate Planner Mode Scripts

**Files**:

- `skills/planner/scripts/planner.py` (modify)
- `skills/planner/scripts/executor.py` (modify)
- `skills/planner/scripts/qr/*.py` (modify - 6 files)
- `skills/planner/scripts/tw/*.py` (modify - 2 files)
- `skills/planner/scripts/dev/*.py` (modify - 1 file)

**Requirements**:

- Update all planner mode scripts to import from skills.lib.workflow instead of shared/
- Add sys.path setup at top of each script
- Replace `from shared import ...` with `from skills.lib.workflow import ...`
- Replace `from shared.formatting import ...` with `from skills.lib.workflow.formatters import ...`
- Replace `from shared.cli import ...` with `from skills.lib.workflow.cli import ...`
- Keep imports from shared.resources (QR_ITERATION_LIMIT, get_resource, get_mode_script_path)
- Keep imports from shared.domain (GuidanceResult, FlatCommand, BranchCommand, NextCommand)

**Acceptance Criteria**:

- All planner mode scripts import from skills.lib.workflow
- No `from shared.formatting import` in any planner mode script
- No `from shared.cli import` in any planner mode script
- All scripts run without import errors
- Output unchanged for all scripts

**Tests**:

- **Test type**: integration (before/after diff)
- **Backing**: user-specified
- **Scenarios**:
  - planner.py --step 1 --total-steps 12 produces unchanged output
  - executor.py --step 1 --total-steps 9 produces unchanged output
  - qr/plan-completeness.py --step 1 --total-steps 6 produces unchanged output
  - dev/fill-diffs.py --step 1 --total-steps 4 produces unchanged output

**Code Intent**:

```
Pattern for all scripts:
1. Add sys.path setup at top (before imports):
   import sys
   from pathlib import Path
   skills_dir = Path(__file__).parent.parent.parent.parent  # Adjust depth
   if str(skills_dir) not in sys.path:
       sys.path.insert(0, str(skills_dir))

2. Replace import statements:
   - from shared.formatting import X -> from skills.lib.workflow.formatters import X
   - from shared.cli import X -> from skills.lib.workflow.cli import X
   - from shared import QRState, GateConfig -> from skills.lib.workflow.types import QRState, GateConfig
   - Keep: from shared.resources import QR_ITERATION_LIMIT, get_resource, ...
   - Keep: from shared.domain import GuidanceResult, FlatCommand, ...

3. Update all planner mode scripts:
   - planner.py
   - executor.py
   - qr/plan-completeness.py
   - qr/plan-code.py
   - qr/plan-docs.py
   - qr/post-impl-code.py
   - qr/post-impl-doc.py
   - qr/reconciliation.py
   - tw/plan-scrub.py
   - tw/post-impl.py
   - dev/fill-diffs.py
```

**Code Changes**:

This milestone creates 11 diffs (one per script file). Each diff follows the same pattern:
1. Add sys.path setup
2. Replace shared.formatting imports with skills.lib.workflow.formatters
3. Replace shared.cli imports with skills.lib.workflow.cli
4. Replace shared type imports with skills.lib.workflow.types

Example diff for planner.py (other scripts follow same pattern):

```diff
--- a/skills/planner/scripts/planner.py
+++ b/skills/planner/scripts/planner.py
@@ -1,6 +1,16 @@
 """12-step planning workflow orchestrator."""

 import argparse
+import sys
+from pathlib import Path
+
+# Add skills/ to path for lib.workflow imports
+skills_dir = Path(__file__).parent.parent.parent
+if str(skills_dir) not in sys.path:
+    sys.path.insert(0, str(skills_dir))
+
+from skills.lib.workflow.types import QRState, GateConfig
+from skills.lib.workflow.formatters import format_step_header, format_step_output, format_gate_step, ...
+from skills.lib.workflow.cli import add_qr_args, mode_main
-from shared import (
-    QRState,
-    GateConfig,
-    format_step_header,
-    format_step_output,
-    format_gate_step,
-    add_qr_args,
-    mode_main,
-)
+from shared.resources import QR_ITERATION_LIMIT, get_resource, get_mode_script_path
+from shared.domain import GuidanceResult, FlatCommand, BranchCommand, NextCommand
```

---

### Milestone 10: Cleanup - Remove Compatibility Layer

**Files**:

- `skills/planner/scripts/shared/__init__.py` (modify)
- `skills/planner/scripts/shared/formatting.py` (delete)
- `skills/planner/scripts/shared/cli.py` (delete)
- `skills/planner/scripts/shared/domain.py` (keep - contains planner-specific types)

**Requirements**:

- Pre-deletion verification: `grep -r --include="*.py" "from shared\.formatting import\|from shared\.cli import" skills/planner/scripts/` - must return ZERO matches (all scripts migrated in M9.5)
- Pre-deletion verification: `grep -r --include="*.py" "from shared import.*format_\|from shared import.*mode_main\|from shared import.*add_qr_args" skills/planner/scripts/` - must return ZERO matches
- Remove planner/scripts/shared/**init**.py re-exports (keep only resources.py and domain.py imports)
- Delete formatting.py, cli.py (now in lib/workflow)
- Keep domain.py (contains planner-specific GuidanceResult, FlatCommand, BranchCommand, NextCommand)
- Verify all planner mode scripts import formatters from skills.lib.workflow.formatters
- Verify all planner mode scripts import CLI utilities from skills.lib.workflow.cli

**Acceptance Criteria**:

- Pre-deletion grep returns ZERO matches (all planner mode scripts migrated)
- planner/scripts/shared/ contains only resources.py, domain.py, and **init**.py
- formatting.py and cli.py deleted (migrated to lib/workflow)
- domain.py retained (contains planner-specific GuidanceResult type)
- All planner scripts use `from skills.lib.workflow.formatters import ...` for formatters
- All planner scripts use `from skills.lib.workflow.cli import ...` for CLI utilities
- No `from shared.formatting import` or `from shared.cli import` anywhere in planner scripts

**Tests**:

- **Test type**: integration
- **Backing**: user-specified
- **Scenarios**:
  - All planner scripts work after cleanup
  - No import errors from removed modules

**Code Intent**:

```
Modify `skills/planner/scripts/shared/__init__.py`:
- Remove all re-exports from skills.lib.workflow
- Keep: from .resources import get_resource, get_mode_script_path, QR_ITERATION_LIMIT
- Keep: from .domain import GuidanceResult, FlatCommand, BranchCommand, NextCommand
- Update __all__ to reflect reduced exports

Delete `skills/planner/scripts/shared/formatting.py`:
- All functions now in skills/lib/workflow/formatters/xml.py

Delete `skills/planner/scripts/shared/cli.py`:
- All functions now in skills/lib/workflow/cli.py

Keep `skills/planner/scripts/shared/domain.py`:
- Contains planner-specific GuidanceResult, FlatCommand, BranchCommand, NextCommand
- These are guidance layer types, not framework primitives
```

**Code Changes**:

```diff
--- a/skills/planner/scripts/shared/__init__.py
+++ b/skills/planner/scripts/shared/__init__.py
@@ -1,89 +1,18 @@
 """Shared utilities for planner scripts.

+Workflow types and formatters live in skills.lib.workflow.
+This module contains planner-specific resource utilities.

 QR Gate Pattern for Verification Loops:
   Every QR step is followed by a GATE step that:
   1. Takes --qr-status=pass|fail as input
   2. Outputs the EXACT next command to invoke
   3. Leaves no room for interpretation

   Work steps that follow a FAIL gate take --qr-fail flag to focus on fixing.

 This pattern is applied consistently across:
   - planner.py (steps 5-12: sequential QR with gates)
   - executor.py (step 4-5: holistic QR with gate)
   - wave-executor.py (steps 2-3: batch QR with gate)
 """

-import sys
-from pathlib import Path
-
-# Add skills/ to path for lib.workflow imports
-skills_dir = Path(__file__).parent.parent.parent.parent
-if str(skills_dir) not in sys.path:
-    sys.path.insert(0, str(skills_dir))
-
-# Compatibility layer - re-export from skills.lib.workflow
-from skills.lib.workflow.types import (
-    AgentRole,
-    LinearRouting,
-    BranchRouting,
-    TerminalRouting,
-    Routing,
-    Dispatch,
-    GateConfig,
-    QRState,
-    Step,
-    WorkflowDefinition,
-)
-
 # Re-export from resources
 from .resources import (
     QR_ITERATION_LIMIT,
     get_resource,
     get_mode_script_path,
     get_exhaustiveness_prompt,
 )
+
+# Re-export from domain (planner-specific guidance types)
+from .domain import (
+    GuidanceResult,
+    FlatCommand,
+    BranchCommand,
+    NextCommand,
+)

-# Re-export from skills.lib.workflow.formatters
-from skills.lib.workflow.formatters import (
-    format_step_header,
-    format_current_action,
-    format_invoke_after,
-    format_next_block,
-    format_gate_result,
-    format_xml_mandate,
-    format_step_output,
-    format_subagent_dispatch,
-    format_state_banner,
-    format_qr_banner,
-    format_expected_output,
-    format_forbidden,
-    format_routing,
-    format_post_qr_routing,
-    format_resource,
-    format_detection_questions,
-    format_verification_checklist,
-    format_incorrect_behavior,
-    format_orchestrator_constraint,
-    format_factored_verification_rationale,
-    format_open_question_guidance,
-    format_gate_actions,
-    format_gate_step,
-)
-
-# Re-export from skills.lib.workflow.cli
-from skills.lib.workflow.cli import (
-    add_qr_args,
-    mode_main,
-)
-
 __all__ = [
-    # Domain types
-    "QRState",
-    "FlatCommand",
-    "BranchCommand",
     # Constants
     "QR_ITERATION_LIMIT",
     # Resources
     "get_resource",
     "get_mode_script_path",
     "get_exhaustiveness_prompt",
+    # Domain types (planner-specific)
+    "GuidanceResult",
+    "FlatCommand",
+    "BranchCommand",
+    "NextCommand",
 ]
```

---

## Milestone Dependencies

```
M0 (Foundation)
 |
 +---> M1 (XML Formatters)
 |       |
 |       +---> M3 (CLI) [depends on M1 - imports format_step_output]
 |       |
 +---> M2 (Text Formatters)
         |
         v
       M4 (Engine) [DEFERRED - not needed]
         |
         v
       M5 (Compatibility Layer) [depends on M1, M2, M3]
         |
         +---> M6 (problem-analysis) --+
         |                              |
         +---> M7 (decision-critic) ---+---> M9 (Documentation)
         |                              |          |
         +---> M8 (refactor) ----------+          v
                                       M9.5 (Migrate planner mode scripts) [NEW]
                                              |
                                              v
                                         M10 (Cleanup)
```

**Parallel execution opportunities**:

- M1, M2 can run in parallel (both depend only on M0)
- M6, M7, M8 can run in parallel (all depend on M5)

**Sequential constraints**:

- M3 depends on M1 (imports format_step_output from formatters)
- M5 depends on M1, M2, M3 (compatibility layer imports from formatters and CLI)
- M9.5 (NEW) depends on M6, M7, M8 (all migrations complete) - migrates planner mode scripts to import from skills.lib.workflow
- M10 depends on M9.5 (all scripts migrated, documentation complete)

**Deferred**:

- M4 (Engine) - QR identified that M5-M8 use formatters directly; engine abstraction not needed
