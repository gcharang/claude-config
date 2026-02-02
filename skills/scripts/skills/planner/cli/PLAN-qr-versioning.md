# Plan: QR CLI Versioning and Output Consistency

## Context

### Problem

cli/qr.py does not follow the "plan state mutation" protocol established in INTENT.md. Specifically:

- QR items lack a version field
- Output uses unstructured `<qr_cli_success>` instead of `<entity_result>` format
- No shared abstractions between plan.py and qr.py for entity output

### Decisions

1. **Add version field to QR items** -- provides audit trail for status transitions (version 1 = created, version 2+ = updated)

2. **No CAS validation for QR** -- file locking handles concurrency; constrained state machine (TODO -> terminal) eliminates merge conflict scenarios that CAS solves

3. **Extract shared output module** -- EntityResult and print_entity_result live in cli/output.py; VersionMismatchError stays in plan.py (only consumer)

4. **No migration logic** -- per user directive, existing files without version field are not a concern

### Constraints

- QR items are created by decompose scripts (not qr.py) -- qr.py only updates
- qr.py operates on raw dicts, not QAItem dataclass
- schema.py is the source of truth for QR item fields

### Invisible Knowledge

- QAItem dataclass in types.py is documentation/type-checking only; qr.py never instantiates it
- The "version" field serves output consistency, not concurrency control
- plan.py needs CAS because entities undergo N updates; QR items undergo 1-2 transitions

## Implementation

### 1. Create cli/output.py (new file)

```python
"""Shared output formatting for CLI entity mutations.

Both plan.py and qr.py output structured entity results after mutations.
This module provides consistent formatting for success output.
"""

from dataclasses import dataclass


@dataclass
class EntityResult:
    """Mutation result for structured CLI output."""
    id: str
    version: int
    operation: str  # "created" | "updated"


def print_entity_result(r: EntityResult) -> None:
    """Print structured success output after entity mutation."""
    print(f"""<entity_result>
  <id>{r.id}</id>
  <version>{r.version}</version>
  <operation>{r.operation}</operation>
</entity_result>""")
```

### 2. Update shared/qr/schema.py

```python
# WHY: Version tracks status transition audit trail
QA_ITEM_REQUIRED_FIELDS = frozenset({"id", "scope", "check", "status", "version"})

# WHY: Version 1 represents creation; increments on each status change
QA_ITEM_DEFAULTS = {
    "id": "unknown",
    "scope": "*",
    "check": "",
    "status": QAItemStatus.TODO.value,
    "version": 1,
    "finding": None,
}

# WHY: Schema template documents expected structure for QR item creation
QA_ITEM_SCHEMA_TEMPLATE = '''{{
  "id": "{id_example}",
  "scope": "*" or "file:path:lines",
  "check": "Description of what was checked",
  "status": "TODO",
  "version": 1,
  "finding": null
}}'''
```

### 3. Update shared/qr/types.py

```python
@dataclass
class QAItem:
    """Single QA checklist item.

    Tracks verification tasks across decomposition iterations with scope
    (macro vs micro), check description, status, and findings.
    """

    id: str
    scope: str
    check: str
    status: QAItemStatus
    version: int = 1  # WHY: Audit trail for status transitions; increments on each change
    finding: str | None = None
```

### 4. Update cli/plan.py

```python
# WHY: Shared structured output format for entity mutations
from .output import EntityResult, print_entity_result
```

**Deletions** (consolidation to shared module):

- EntityResult dataclass (lines 148-153)
- print_success function (lines 189-195)

**Retain** in plan.py (CAS-specific, only plan.py uses these):

- VersionMismatchError class (lines 156-159)
- check_version() -- WHY: CAS validation specific to plan entities
- bump_version() -- WHY: CAS increment specific to plan entities
- print_version_error() -- WHY: CAS error output specific to plan entities

**Function rename**: `print_success(EntityResult(...))` becomes `print_entity_result(EntityResult(...))` for consistency with shared module.

### 5. Update cli/qr.py

```python
# WHY: Shared structured output format for entity mutations
from .output import EntityResult, print_entity_result
```

**cmd_update_item function**:

```python
        # WHY: Version increments on each status transition for audit trail
        item["version"] = item.get("version", 1) + 1
        item["status"] = status
        if finding:
            item["finding"] = finding
        elif "finding" in item and status == "PASS":
            # WHY: PASS status clears previous finding; no stale failure data persists
            del item["finding"]

        qr_state["items"][idx] = item
        save_qr_state_atomic(state_dir, phase, qr_state)

    print_entity_result(EntityResult(
        id=item_id,
        version=item["version"],
        operation="updated"
    ))
```

**Deletions**:

- success() function (lines 62-66) -- WHY: Shared print_entity_result provides consistent output format

## Quality Checklist

Code quality standards from ~/.claude/conventions/code-quality/ applicable to this change:

- [ ] 01-naming-and-types (design-mode): EntityResult, print_entity_result naming consistent
- [ ] 02-structure-and-composition (design-mode): Shared module extracts common patterns
- [ ] 06-module-and-dependencies (design-mode): cli/output.py has no dependencies on plan or qr internals
- [ ] 07-cross-file-consistency (design-mode): Both CLIs use identical output format

## Execution Protocol

```
1. delegate @agent-developer: implement per this plan file
2. delegate @agent-quality-reviewer: verify against plan + ~/.claude/conventions/code-quality/ (code-mode)

When delegating, pass this plan file path. Supplement only with:
- rationale for decisions not captured in plan
- business constraints
- technical prerequisites the agent cannot infer
```
