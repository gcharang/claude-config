# workflow/

Workflow orchestration framework: types, formatters, registration, and testing.

## Files

| File              | What                                                 | When to read                                                      |
| ----------------- | ---------------------------------------------------- | ----------------------------------------------------------------- |
| `README.md`       | Architecture, design decisions, patterns, invariants | Understanding workflow design, migration guide, common patterns   |
| `core.py`         | Workflow, StepDef, StepContext, Outcome, Arg         | Defining new skills, understanding workflow data model            |
| `__init__.py`     | Public API exports                                   | Importing workflow types, checking available exports              |
| `cli.py`          | CLI helpers for workflow entry points                | Adding CLI arguments, modifying step output                       |
| `constants.py`    | Shared constants                                     | Adding new constants, modifying defaults                          |
| `manifest_cli.py` | CLI for manifest generation                          | Generating manifest, checking migration status                    |
| `registry.py`     | @skill decorator, Param constraints (legacy)         | Understanding legacy registration, combining old + new registries |
| `testing.py`      | L0-L2 test harness, boundary input gen               | Running skill tests, adding test coverage, debugging tests        |
| `types.py`        | Domain types: Step, WorkflowDefinition, etc (legacy) | Understanding legacy types, Dispatch for QR gates                 |

## Subdirectories

| Directory     | What                         | When to read                                    |
| ------------- | ---------------------------- | ----------------------------------------------- |
| `formatters/` | Output formatting (XML/text) | Modifying step output format, adding formatters |

## Test

```bash
# Run all skill tests (L0-L2)
python -m skills.lib.workflow.testing --level 2

# Test specific skill
python -m skills.lib.workflow.testing --skill decision-critic --level 2
```

## Manifest

```bash
# Generate manifest (auto-derived from registered workflows)
python -m skills.lib.workflow.manifest_cli -o skills-manifest.json

# Output shows migration status:
# - Total skills: N
# - Migrated to Workflow: M (skill1, skill2, ...)
# - Legacy only: K (skillX, ...) [if any]
```

The manifest is derived from workflows, not manually maintained.
