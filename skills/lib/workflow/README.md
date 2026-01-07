# Workflow Orchestration Framework

## Overview

Shared workflow orchestration primitives extracted from planner skill. Provides typed domain model (AgentRole, Routing, Dispatch, Step, QRState), reusable XML/text formatters, and CLI utilities for building multi-step agent scripts with Quality Review (QR) loops.

Eliminates 550+ lines of duplication across skills (planner, refactor, problem-analysis, decision-critic).

## Architecture

```
skills/
  lib/
    workflow/
      __init__.py          # Public API exports
      types.py             # Domain types (AgentRole, Routing, Dispatch, Step, QRState, GateConfig)
      formatters/
        __init__.py        # Re-exports from xml.py and text.py
        xml.py             # 26 XML formatters (format_step_output, format_gate_step, etc.)
        text.py            # Plain text formatters (format_text_output)
      cli.py               # Argument parsing (add_qr_args, mode_main)

  planner/
    scripts/
      shared/              # Compatibility layer re-exports lib.workflow (temporary)
      planner.py           # Uses lib.workflow
      qr/                  # QR mode scripts use lib.workflow
      tw/                  # TW mode scripts use lib.workflow
      dev/                 # Dev mode scripts use lib.workflow

  refactor/
    scripts/
      refactor.py          # Uses lib.workflow formatters
      explore.py           # Uses lib.workflow formatters

  problem-analysis/
    scripts/
      analyze.py           # Uses lib.workflow.formatters.text

  decision-critic/
    scripts/
      decision-critic.py   # Uses lib.workflow.formatters.text
```

## Data Flow

```
CLI args --> parse_args() --> WorkflowContext
                                   |
                                   v
STEPS dict --> StepConfig lookup --> format_step_output()
                                          |
                                          v
                               XML/text output --> print()
```

Detailed flow for QR (Quality Review) loops:

```
Work Step (--qr-fail=false)
  |
  v
format_step_output() --> XML with actions, routing
  |
  v
QR Step (review work)
  |
  v
Gate Step (--qr-status=pass|fail)
  |
  +-- PASS --> Next step or COMPLETE
  |
  +-- FAIL --> Work Step (--qr-fail=true, --qr-iteration=N+1)
```

## Why This Structure

**lib/workflow/ location**: Framework code that all skills import. `lib/` signals "library code" vs application code (follows Python convention for internal packages).

**types.py separate from formatters**: Types have zero dependencies; formatters import types. Separation keeps types lightweight and prevents circular imports.

**formatters/ subdirectory**: 26+ formatters (format_step_header, format_step_output, format_gate_step, etc.). Grouping in subdirectory with xml.py (structured output) and text.py (simple output) prevents single 700+ line file.

**Compatibility layer (planner/scripts/shared/)**: Re-exports from lib.workflow so existing imports (`from shared import format_step_output`) work during migration. Temporary - removed after all skills migrate to direct lib.workflow imports.

## Design Decisions

**AgentRole as Enum over string literals**: String literals allow typos ("develper") and invalid values. Enum provides compile-time validation, IDE autocomplete, exhaustive pattern matching.

**Routing as union type (Linear | Branch | Terminal) over single class with mode field**: Union type makes invalid states unrepresentable (can't have both if_pass and terminal). Pattern matching on routing type is explicit. Matches actual usage (mutually exclusive modes).

**Stateless formatters over template classes**: All formatters are pure functions (input -> XML string). No object state to manage. Easy to test (deterministic output). Composable - mix XML blocks and plain strings in actions list:

```python
actions = [
    format_state_banner(...),  # Returns XML string
    "",                        # Blank line
    "TASK: Do something",      # Plain string
    format_forbidden([...]),   # Returns XML string
]
```

**Two-layer composition model**: Guidance layer (get_step_guidance() returns dict with title/actions/next) + rendering layer (format_step_output() assembles XML). Actions list contains both plain strings and XML blocks. All formatters return strings, so mixing works seamlessly.

**Planner-specific types NOT in framework**: FlatCommand, BranchCommand, NextCommand, GuidanceResult live in planner/scripts/shared/domain.py. These are guidance layer types used by planner mode scripts, not framework primitives. xml.py imports them via importlib to avoid circular dependency.

**Import mechanism (sys.path.insert)**: Each script entry point adds skills/ to sys.path. No external environment dependency (PYTHONPATH not required). Works in any invocation context. Each script self-configures import path; no PYTHONPATH environment setup required.

## Invariants

1. **Output equivalence**: For any (step, total_steps, qr_state) input, formatters produce byte-identical output to original planner/scripts/shared/formatting.py implementation.

2. **Import compatibility**: During migration, `from shared import format_step_output` works identically to `from skills.lib.workflow.formatters import format_step_output`.

3. **Type safety**: AgentRole, Routing, Dispatch are exhaustive enums/unions. No stringly-typed dispatch metadata. Invalid states are unrepresentable.

4. **QRState three-pillar pattern**: iteration (loop count), failed (entry state flag), status (prior result). Both failed and status needed: failed indicates entering step to fix issues, status is QR result from previous step.

## Tradeoffs

1. **Duplication during migration**: planner/scripts/shared temporarily re-exports from lib/workflow; removed after all skills migrate.

2. **More files**: lib/workflow has 7+ files vs 4 in planner/scripts/shared; cleaner separation worth the overhead.

3. **Learning curve**: New skills must learn lib.workflow API; offset by reduced boilerplate.

## Usage Examples

### Basic workflow with linear routing

```python
import sys
from pathlib import Path

# Add skills/ to path
skills_dir = Path(__file__).parent.parent.parent
if str(skills_dir) not in sys.path:
    sys.path.insert(0, str(skills_dir))

from skills.lib.workflow.formatters import format_step_output
from skills.lib.workflow.types import Step, LinearRouting

STEPS = {
    1: Step(
        title="Analyze Problem",
        actions=["Read codebase", "Identify issues"],
        routing=LinearRouting(),
    ),
    2: Step(
        title="Propose Solution",
        actions=["Design fix", "Document approach"],
        routing=LinearRouting(),
    ),
}

# In main():
step_config = STEPS[args.step]
next_cmd = f"python3 script.py --step {args.step + 1} --total-steps {args.total_steps}"
print(format_step_output(
    script="script",
    step=args.step,
    total=args.total_steps,
    title=step_config.title,
    actions=step_config.actions,
    next_command=FlatCommand(next_cmd),
))
```

### QR loop with gate step

```python
from skills.lib.workflow.formatters import format_gate_step
from skills.lib.workflow.types import QRState, GateConfig, BranchRouting

# Step 5: QR verification
qr_step = Step(
    title="QR: Review Implementation",
    actions=["Check for errors", "Verify completeness"],
    routing=BranchRouting(if_pass=7, if_fail=6),
)

# Step 6: Gate (routes based on QR result)
gate_config = GateConfig(
    qr_name="Implementation QR",
    work_step=4,           # Step to re-run if FAIL
    pass_step=7,           # Step to jump to if PASS
    pass_message="Implementation verified. Proceeding.",
    self_fix=True,         # Agent fixes issues automatically
    fix_target=AgentRole.DEVELOPER,
)

# In main():
if args.step == 6:  # Gate step
    qr = QRState(
        iteration=args.qr_iteration,
        failed=args.qr_fail,
        status=args.qr_status,  # "pass" or "fail" from CLI
    )
    print(format_gate_step(
        script="script",
        step=6,
        total=12,
        title="Gate: Route based on QR result",
        qr=qr,
        gate=gate_config,
    ))
```

### Plain text output for simple skills

```python
from skills.lib.workflow.formatters.text import format_text_output

# Simple skill without XML structure
print(format_text_output(
    step=args.step,
    total=args.total_steps,
    title="Analyze Problem",
    actions=["Examine codebase", "List issues"],
    brief="Initial analysis phase",
    next_title="Propose Solutions",
))
```

### Sub-agent dispatch

```python
from skills.lib.workflow.formatters import format_subagent_dispatch
from skills.lib.workflow.types import AgentRole

actions = [
    "Parallel exploration across dimensions:",
    "",
    format_subagent_dispatch(
        agent=AgentRole.EXPLORE.value,
        script_path="/path/to/explore.py",
        step=1,
        total_steps=2,
        context_vars={"dimension": "naming"},
        free_form=False,  # Script mode (agent follows exact steps)
    ),
]
```

## Migration Guide

### From planner/scripts/shared to lib.workflow

**Before** (planner mode script):

```python
from shared import (
    QRState,
    GateConfig,
    format_step_output,
    format_gate_step,
)
```

**After** (direct lib.workflow import):

```python
import sys
from pathlib import Path

# Add skills/ to path (adjust parent depth for your script location)
skills_dir = Path(__file__).parent.parent.parent
if str(skills_dir) not in sys.path:
    sys.path.insert(0, str(skills_dir))

from skills.lib.workflow.types import QRState, GateConfig
from skills.lib.workflow.formatters import format_step_output, format_gate_step
```

**Path depth guide**:

- `planner/scripts/planner.py`: 3 parents (scripts -> planner -> skills)
- `planner/scripts/qr/plan-completeness.py`: 4 parents (qr -> scripts -> planner -> skills)
- `refactor/scripts/refactor.py`: 3 parents

### Adding sys.path setup to new skills

All workflow scripts need sys.path setup at the top:

```python
import sys
from pathlib import Path

# Add skills/ to sys.path for lib.workflow imports
skills_dir = Path(__file__).parent.parent.parent  # Adjust parent count
if str(skills_dir) not in sys.path:
    sys.path.insert(0, str(skills_dir))
```

### Using mode_main for CLI boilerplate reduction

**Before** (custom argparse + format_output):

```python
def main():
    parser = argparse.ArgumentParser(description="My Workflow")
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true")
    args = parser.parse_args()

    guidance = get_step_guidance(args.step, args.total_steps, ...)
    print(format_step_output(...))
```

**After** (mode_main handles argparse + formatting):

```python
from skills.lib.workflow.cli import mode_main

def get_step_guidance(step, total_steps, script_path, qr_iteration=1, qr_fail=False):
    # Return dict with title, actions, next
    return {
        "title": STEPS[step]["title"],
        "actions": STEPS[step]["actions"],
        "next": FlatCommand(f"python3 {script_path} --step {step+1} --total-steps {total_steps}"),
    }

if __name__ == "__main__":
    mode_main(__file__, get_step_guidance, "My Workflow")
```

## Common Patterns

### Composing XML blocks in actions

```python
actions = [
    format_state_banner("checkpoint_name", iteration=2, mode="re-verify"),
    "",
    "TASK: Fix identified issues",
    "",
    format_forbidden([
        "Do not modify unrelated files",
        "Do not change API contracts",
    ]),
    "",
    format_expected_output([
        "All QR issues resolved",
        "Tests passing",
    ]),
]
```

### Conditional routing based on QR status

```python
from skills.lib.workflow.types import BranchRouting

# In STEPS dict:
qr_step = Step(
    title="QR: Verify Implementation",
    actions=["Review code for issues"],
    routing=BranchRouting(if_pass=7, if_fail=6),  # Different next steps
)

# format_step_output will generate:
# <invoke_after>
#   <if_pass>python3 script.py --step 7 ...</if_pass>
#   <if_fail>python3 script.py --step 6 ...</if_fail>
# </invoke_after>
```

### Terminal step (workflow complete)

```python
from skills.lib.workflow.types import TerminalRouting

final_step = Step(
    title="Synthesize Results",
    actions=["Present findings to user"],
    routing=TerminalRouting(),  # No next command
)

# format_step_output will generate:
# <invoke_after>
# </invoke_after>  (empty - no continuation)
```

### Fresh review mode (CoVe pattern)

```python
from skills.lib.workflow.formatters import format_qr_banner

# Iteration 1: initial review
banner = format_qr_banner(qr=QRState(iteration=1), qr_name="Plan Completeness")
# Output: "PLAN COMPLETENESS: Review the work for issues."

# Iteration 2+: re-verify with fresh eyes (prevents confirmation bias)
banner = format_qr_banner(
    qr=QRState(iteration=2, failed=True, status="fail"),
    qr_name="Plan Completeness",
    fresh_review=True,
)
# Output: "PLAN COMPLETENESS (Iteration 2, fresh review): Previous review found issues."
```

## Research Grounding

Formatters implement patterns from research literature:

**RE2 (Retrieval-Augmented Generation)**: `format_resource()` embeds reference materials inline so agent can retrieve relevant context without external queries.

**CoVe (Chain-of-Verification)**: `format_qr_banner()` with `fresh_review=True` prevents confirmation bias by prompting QR agent to ignore prior findings. `format_factored_verification_rationale()` separates verification into independent sub-questions.

Citations in docstrings document research grounding for future maintainers.
