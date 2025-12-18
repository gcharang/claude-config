# skills/planner/

## Overview

Planning skill with resources that must stay synced with agent prompts.

## Index

| File/Directory                        | Contents                                      | Read When                                   |
| ------------------------------------- | --------------------------------------------- | ------------------------------------------- |
| `SKILL.md`                            | Planning workflow, phases, plan format        | Using the planner skill                     |
| `scripts/planner.py`                  | Step-by-step planning orchestration           | Debugging planner behavior                  |
| `resources/temporal-contamination.md` | Detection heuristic for contaminated comments | Updating TW/QR temporal contamination logic |
| `resources/diff-format.md`            | Unified diff spec for code changes            | Updating Developer diff consumption logic   |

## Resource Sync Requirements

Resources are **authoritative sources**.

- **SKILL.md** references resources directly (main Claude can read files)
- **Agent prompts** embed resources 1:1 (sub-agents cannot access files reliably)

### temporal-contamination.md

Authoritative source for temporal contamination detection. Full content embedded 1:1.

| Synced To                    | Embedded Section           |
| ---------------------------- | -------------------------- |
| `agents/technical-writer.md` | `<temporal_contamination>` |
| `agents/quality-reviewer.md` | `<temporal_contamination>` |

**When updating**: Modify `resources/temporal-contamination.md` first, then copy content into both `<temporal_contamination>` sections.

### diff-format.md

Authoritative source for unified diff format. Full content embedded 1:1.

| Synced To             | Embedded Section |
| --------------------- | ---------------- |
| `agents/developer.md` | `<diff_format>`  |

**When updating**: Modify `resources/diff-format.md` first, then copy content into `<diff_format>` section.

## Sync Verification

After modifying a resource, verify sync:

```bash
# Check temporal-contamination.md references
grep -l "temporal.contamination\|four detection questions\|change-relative\|baseline reference" agents/*.md

# Check diff-format.md references
grep -l "context lines\|AUTHORITATIVE\|APPROXIMATE\|context anchor" agents/*.md
```

If grep finds files not listed in sync tables above, update this document.
