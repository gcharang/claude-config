# Workflow Framework

## Overview

Framework for skill registration and testing. Skills are defined using the `Workflow` class with `StepDef` instances - a data-driven approach where transitions are explicit data structures.

## Architecture

```
Workflow() -> register_workflow() -> _WORKFLOW_REGISTRY
                                          |
                                          v
                                     testing.py -> L0/L1/L2 validation
```

Registration happens at import time.

## Core Types

### Outcome Enum

Separates "what outcome?" from "where next?" to make transition graphs introspectable as data:

```python
class Outcome(str, Enum):
    OK = "ok"           # Success, proceed to next
    FAIL = "fail"       # Failure, may trigger error handling
    SKIP = "skip"       # Skip branch (used for mode branching)
    ITERATE = "iterate" # Continue loop (used for confidence progression)
    DEFAULT = "_default" # Fallback if specific outcome not mapped
```

**Why not booleans?** Booleans force transitions into code logic. Outcomes make the transition graph data that can be validated, visualized, and reasoned about.

**Example**: Without Outcome, mode branching requires:

```python
if mode == "quick":
    return "step_11"  # Implicit meaning
else:
    return "step_5"   # What does this mean? Success? Skip?
```

With Outcome:

```python
def step_planning(ctx):
    if ctx.workflow_params["mode"] == "quick":
        return Outcome.SKIP, {}  # Explicit: skipping this branch
    return Outcome.OK, {}        # Explicit: proceeding normally

StepDef(id="planning", next={
    Outcome.OK: "subagent_design",      # Full mode path
    Outcome.SKIP: "initial_synthesis",  # Quick mode path
})
```

The transition graph is now visible in the StepDef, not buried in handler logic.

### StepContext

Runtime state container passed to handlers, enabling stateful iteration:

```python
@dataclass
class StepContext:
    step_id: str                         # Current step identifier
    workflow_params: dict[str, Any]      # Immutable workflow parameters (--mode, --decision)
    step_state: dict[str, Any]           # Mutable state (iteration count, confidence level)
```

**Why separate params and state?**

- `workflow_params`: Set at workflow start, never change (e.g., mode, input paths)
- `step_state`: Updated by handlers, carries iteration state between steps

**Example - Confidence-driven iteration**:

```python
def step_investigate(ctx: StepContext) -> tuple[Outcome, dict]:
    iteration = ctx.step_state.get("iteration", 1)
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "high":
        return Outcome.OK, {"confidence": confidence}
    elif iteration >= MAX_ITERATIONS:
        return Outcome.OK, {"confidence": "capped"}
    else:
        return Outcome.ITERATE, {"iteration": iteration + 1}

StepDef(id="investigate", handler=step_investigate,
        next={Outcome.OK: "formulate", Outcome.ITERATE: "investigate"})
```

### Handler Signature

Handlers process step logic and return next outcome:

```python
def handler(ctx: StepContext) -> tuple[Outcome, dict]:
    # Access workflow parameters (immutable)
    mode = ctx.workflow_params.get("mode", "full")

    # Access step state (from previous iterations)
    iteration = ctx.step_state.get("iteration", 1)

    # Perform step logic...

    # Return outcome and updated state
    return Outcome.OK, {"iteration": iteration + 1}
```

**Why return state dict?** Handlers are pure functions. Returning state rather than mutating context makes flow explicit and testable.

**Output-only steps**: Steps that just print instructions can use a no-op handler:

```python
def step_handler(ctx: StepContext) -> tuple[Outcome, dict]:
    return Outcome.OK, {}
```

### Arg (Parameter Metadata)

Annotates handler parameters for testing:

```python
@dataclass(frozen=True)
class Arg:
    description: str = ""
    default: Any = inspect.Parameter.empty
    min: int | float | None = None
    max: int | float | None = None
    choices: tuple[str, ...] | None = None
    required: bool = False
```

**Usage**:

```python
from typing import Annotated

def step_handler(
    ctx: StepContext,
    mode: Annotated[str, Arg(description="Workflow mode", choices=("quick", "full"))] = "full"
) -> tuple[Outcome, dict]:
    ...
```

The `Arg` metadata is extracted during workflow validation for testing.

### Dispatch vs Callable Handlers

**Callable handler**: Inline Python function (most common)

```python
def step_analyze(ctx: StepContext) -> tuple[Outcome, dict]:
    # Analysis logic here
    return Outcome.OK, {}

StepDef(id="analyze", handler=step_analyze, ...)
```

**Dispatch handler**: Delegates to sub-agent script (for QR gates, parallel agents)

```python
from skills.lib.workflow.types import Dispatch, AgentRole

StepDef(
    id="qr_completeness",
    handler=Dispatch(
        agent=AgentRole.QUALITY_REVIEWER,
        script="skills.planner.qr.plan_completeness",
        total_steps=1,
    ),
    next={Outcome.OK: "implementation", Outcome.FAIL: "revise_plan"}
)
```

The `Dispatch` handler tells the orchestrator to:

1. Launch the specified agent with the script
2. Wait for completion
3. Map the agent's result to an Outcome

**When to use Dispatch?**

- QR gates (quality reviewer checks)
- Parallel sub-agent execution
- Complex sub-workflows that need separate scripts

## Workflow Validation

`Workflow.__init__` performs 5 validation checks:

1. **Entry point exists**: The `entry_point` step ID must be in the workflow
2. **All transition targets exist**: Every target in `next` dicts must be a valid step ID or `None` (terminal)
3. **At least one terminal step**: At least one step must have `None` in its `next` dict
4. **All steps reachable**: Every step must be reachable from the entry point (detects orphaned steps)
5. **Parameter extraction**: Extract `Arg` metadata from handler signatures for testing

These checks run at registration time, catching errors early.

## Workflow Example

```python
from skills.lib.workflow.core import (
    Workflow, StepDef, StepContext, Outcome, Arg, register_workflow
)

def step_handler(ctx: StepContext) -> tuple[Outcome, dict]:
    return Outcome.OK, {}

WORKFLOW = Workflow(
    "decision-critic",
    StepDef(
        id="extract_structure",
        title="Extract Structure",
        phase="DECOMPOSITION",
        actions=[...],
        handler=step_handler,
        next={Outcome.OK: "classify_verifiability"},
    ),
    StepDef(
        id="classify_verifiability",
        title="Classify Verifiability",
        phase="DECOMPOSITION",
        actions=[...],
        handler=step_handler,
        next={Outcome.OK: "generate_questions"},
    ),
    # ... remaining steps
    description="Structured decision criticism workflow",
)

register_workflow(WORKFLOW)
```

Benefits of this architecture:

- Steps and transitions together in data structure
- Transitions explicit and validatable
- Workflow structure introspectable and validatable
- Transition graph introspectable

## Design Decisions

**Why separate Workflow and StepDef?** Workflows are collections; steps are atomic units. Separation allows validation at workflow level (reachability, terminals) while keeping step definitions focused.

**Why frozen dataclasses?** Workflows and StepDefs are immutable specifications. Frozen dataclasses prevent accidental mutation and make them safe to share across threads.

**Why handler callables instead of strings?** Type safety, IDE support, and easier refactoring. Handlers are first-class functions, not magic strings.

**Separate CLI entry points**: Running modules as `__main__` causes module identity issues (imported by `__init__.py` vs executed as `__main__`). Separate CLI entry points (`testing.py`) avoid this.

**Three test levels**: L0 (import), L1 (registration valid), L2 (invocability).
L2 runs the skill via subprocess with synthetic boundary inputs. L3 (output
validation) is not implemented -- invocability is sufficient for regression
detection.

**Single-factor variation**: Test inputs vary one parameter at a time from
defaults rather than Cartesian product. Avoids test explosion (5^5 = 3125 vs 5\*5 = 25).

## Common Patterns

### Pattern 1: Linear Workflow

```python
WORKFLOW = Workflow(
    "skill-name",
    StepDef(id="step1", title="...", actions=[...],
            handler=step_handler, next={Outcome.OK: "step2"}),
    StepDef(id="step2", title="...", actions=[...],
            handler=step_handler, next={Outcome.OK: "step3"}),
    StepDef(id="step3", title="...", actions=[...],
            next={Outcome.OK: None}),  # terminal
)
```

### Pattern 2: Confidence-Driven Iteration

```python
def step_investigate(ctx: StepContext) -> tuple[Outcome, dict]:
    iteration = ctx.step_state.get("iteration", 1)
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "high":
        return Outcome.OK, {"confidence": confidence}
    elif iteration >= MAX_ITERATIONS:
        return Outcome.OK, {"confidence": "capped"}
    else:
        return Outcome.ITERATE, {"iteration": iteration + 1}

StepDef(id="investigate", handler=step_investigate,
        next={
            Outcome.OK: "formulate",       # exit loop
            Outcome.ITERATE: "investigate"  # continue loop
        })
```

### Pattern 3: Mode Branching

```python
def step_planning(ctx: StepContext) -> tuple[Outcome, dict]:
    mode = ctx.workflow_params.get("mode", "full")
    if mode == "quick":
        return Outcome.SKIP, {}
    return Outcome.OK, {}

StepDef(id="planning", handler=step_planning,
        next={
            Outcome.OK: "subagent_design",      # full mode
            Outcome.SKIP: "initial_synthesis",  # quick mode
        })
```

### Pattern 4: QR Gate

```python
from skills.lib.workflow.types import Dispatch, AgentRole

StepDef(
    id="qr_completeness",
    title="QR: Plan Completeness",
    actions=[...],
    handler=Dispatch(
        agent=AgentRole.QUALITY_REVIEWER,
        script="skills.planner.qr.plan_completeness",
        total_steps=1,
    ),
    next={
        Outcome.OK: "implementation",   # QRStatus.PASS -> Outcome.OK
        Outcome.FAIL: "revise_plan",    # QRStatus.FAIL -> Outcome.FAIL
    },
)
```

## Invariants

- Every skill module appears in `_import_all_skills()` in `testing.py`
- Workflow validation must pass (entry point exists, all transitions valid, at least one terminal, all steps reachable)
- Handler signatures must match `(ctx: StepContext) -> tuple[Outcome, dict]` or be a `Dispatch` instance
- `next` dict keys must be `Outcome` enum values
- `next` dict values must be valid step IDs or `None` (terminal)

## Testing

### Run All Tests

```bash
python -m skills.lib.workflow.testing --level 2
```

### Test Specific Skill

```bash
python -m skills.lib.workflow.testing --skill decision-critic --level 2
```

### Test Levels

- **L0**: Import skill module successfully
- **L1**: Registration valid (total_steps set, entry point exists)
- **L2**: Invocability (skill executes without error for boundary inputs)
