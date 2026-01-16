# Planner

## Overview

Planning and execution workflows with QR (Quality Review) gates, TW (Technical Writer) passes, and Dev (Developer) execution phases.

## Architecture

```
Skills Layer (12 modules)
       |
       v
   Workflow API (Workflow/StepDef/Outcome)
       |
       v
Discovery Layer (importlib scanning)
       |
       v
Core Framework (types, registry, ResourceProvider)
       |
       v
CLI / Test Harness
```

## Components

**planner.py**: Main planning workflow with 5 QR gates for plan validation.

**executor.py**: Extended planning workflow with 8 steps including implementation and post-implementation review (QR gates, TW passes, Dev execution).

**qr/**: Quality Review modules (plan_completeness, plan_code, plan_docs, post_impl_code, post_impl_doc, reconciliation). Each module performs validation with severity-based blocking thresholds.

**tw/**: Technical Writer modules (plan_scrub, fill_diffs). Remove temporal directives and prepare plans for implementation.

**dev/**: Developer modules (post_impl). Handle implementation execution and validation.

**shared/**: Shared resources (conventions, resource provider implementation).

## Data Flow

```
CLI invocation
      |
      v
discover_workflows() -> scan skills/ -> build registry
      |
      v
Workflow.run(step_id) -> STEPS[step_id].handler(context)
      |
      v
StepOutput (title, actions, next_command)
```

### Execution Flow

```
Plan Creation (planner.py)
      |
      v
QR Gates (plan_completeness, plan_docs, plan_code)
      |
      v
TW Pass (plan_scrub -> remove directives, prepare comments)
      |
      v
User Edit
      |
      v
Implementation (executor.py + Dev execution)
      |
      v
Post-Implementation QR Gates (post_impl_code, post_impl_doc)
      |
      v
Reconciliation (verify plan matches implementation)
```

## Invariants

- **INVARIANT 1**: Every skill entry point defines exactly ONE Workflow
- **INVARIANT 2**: discover_workflows() finds all Workflows without import errors
- **INVARIANT 3**: Dispatcher routing produces same output as old if-step chains
- **INVARIANT 4**: ResourceProvider protocol supports all 5 access patterns (conventions, file I/O, resources, Workflow objects, step data)
- **INVARIANT 5**: QR iteration blocking severities: iter 1-2 block all; iter 3-4 block MUST/SHOULD; iter 5+ block MUST only

## Design Decisions

**Data-driven step dispatch**: STEPS dict provides O(1) routing across all workflow files. Dict lookup replaces 63 if-step chains with unified dispatcher pattern.

**ResourceProvider protocol**: Protocol interface in types.py breaks 3-layer coupling (QR/TW/Dev modules importing from both lib/workflow and planner/shared). Enables mock implementations for isolated unit testing.

**QR iteration blocking**: Severity thresholds vary by iteration depth. Early iterations (1-2) block all severities to force immediate fixes. Later iterations (3-4) block MUST/SHOULD only. Final iterations (5+) block MUST only to prevent infinite retry loops.

**Step handler signature**: All handlers accept (context: StepContext) -> StepOutput. Unified signature enables single dispatcher implementation across all skills. StepContext provides step_id, args, state; StepOutput provides title, actions, next_command.

**Golden file baseline testing**: Output format stability critical for downstream script consumers (executor.py, planner.py parse step output). Byte-exact comparison detects unintended format changes.

## QR Gate Workflow

QR gates use LoopState enum to track iteration progression:

- **INITIAL**: First review attempt
- **RETRY**: Fixing issues from previous iteration
- **COMPLETE**: Passed review

State transitions:

```
INITIAL -> (QRStatus.PASS) -> COMPLETE [terminal]
INITIAL -> (QRStatus.NEEDS_CHANGES) -> RETRY -> (iteration++) -> RETRY -> ...
```

Blocking severity thresholds by iteration:

| Iteration | Block Severities      | Rationale                                |
| --------- | --------------------- | ---------------------------------------- |
| 1-2       | All (MUST/SHOULD/MAY) | High failure rate, force immediate fixes |
| 3-4       | MUST/SHOULD           | Address nuanced issues                   |
| 5+        | MUST only             | Prevent infinite retry loops             |

## ResourceProvider Protocol

QR/TW/Dev modules receive ResourceProvider instead of importing skills.planner.shared.resources directly. Protocol breaks circular dependencies and enables mock implementations.

```python
class ResourceProvider(Protocol):
    def get_resource(self, name: str) -> str:
        """Retrieve resource content by name."""
        ...

    def get_step_guidance(self, **kwargs) -> dict:
        """Get step-specific guidance (placeholder for forward compatibility)."""
        ...
```

Implementation in shared/resources.py:

```python
class PlannerResourceProvider:
    def get_resource(self, name: str) -> str:
        resource_path = CONVENTIONS_DIR / name
        if not resource_path.exists():
            raise FileNotFoundError(f"Resource not found: {name}")
        return resource_path.read_text()

    def get_step_guidance(self, **kwargs) -> dict:
        return {}  # Placeholder until per-step guidance requirements emerge
```

## Tradeoffs

**Idiomatic API vs Minimal**: Higher refactoring scope for consistent architecture across all skills. Extending think.py's Workflow/StepDef pattern creates consistency without inventing new abstractions.

**Centralized enums vs Local**: One more place to update for discoverability and shared understanding. LoopState enum makes QR state transitions explicit and enables property-based testing.

**Clean break vs Dual-path**: Simpler implementation at cost of no migration period. Refactoring scope is internal (no external callers) so clean break reduces total work and eliminates transition bugs.
