---
name: incoherence
description: Detect and resolve incoherence in documentation, code, specs vs implementation. Includes reconciliation phase for applying user-provided resolutions.
---

# Incoherence Detector Skill

## Purpose

Detect and resolve incoherence: contradictions between docs and code, ambiguous specifications, missing documentation, or policy violations.

## Prerequisites

**Before starting**: User must specify the report filename (e.g., "output to incoherence-report.md").

## Invocation

```bash
# Detection phase (steps 1-9)
python3 scripts/incoherence.py --step-number 1 --total-steps 18 --thoughts "<context>"

# Reconciliation phase (steps 10-18, after user edits report)
python3 scripts/incoherence.py --step-number 10 --total-steps 18 --thoughts "Reconciling..."
```

## Workflow (18 Steps)

```
DETECTION PHASE (Steps 1-9):

Step 1:  CODEBASE SURVEY          ─────┐
Step 2:  DIMENSION SELECTION           │
Step 3:  EXPLORATION DISPATCH          │ Parent
Step 4:  SYNTHESIS                     │
Step 5:  DEEP-DIVE DISPATCH       ─────┘
         │
         ▼
    ┌────────────────────────┐
    │ Step 6:  EXPLORATION   │ Sub-agents
    │ Step 7:  FORMAT        │ (invoke script)
    └────────────────────────┘
         │
         ▼
Step 8:  VERDICT ANALYSIS         ─────┐
Step 9:  REPORT GENERATION             │ Parent
         │                        ─────┘
         ▼
    ═══════════════════════════
    USER EDITS REPORT
    (fills in Resolution sections)
    ═══════════════════════════
         │
         ▼
RECONCILIATION PHASE (Steps 10-18):

Step 10: RECONCILE PARSE          ─────┐
Step 11: RECONCILE ANALYZE             │
Step 12: RECONCILE PLAN                │ Parent
Step 13: RECONCILE DISPATCH       ─────┘
         │
         ▼
    ┌────────────────────────┐
    │ Step 14: APPLY         │ Sub-agents
    │ Step 15: FORMAT        │ (invoke script)
    └────────────────────────┘
         │
         ▼
Step 16: RECONCILE COLLECT        ───┐
         │ (loop if more waves)      │
         ▼                           │ Parent
Step 17: RECONCILE UPDATE            │
         │                           │
         ▼                           │
Step 18: RECONCILE COMPLETE      ────┘
```

## Reconciliation Behavior

**Idempotent**: Can be run multiple times on the same report.

**Skip conditions** (issue left unchanged):
- No resolution provided by user
- Already marked as resolved (from previous run)
- Could not apply (sub-agent failed)

**Only action**: Mark successfully applied resolutions as ✅ RESOLVED in report.

## Report Format

Step 9 generates issues with Resolution sections:

```markdown
### Issue I1: [Title]

**Type**: Contradiction | Ambiguity | Gap | Policy Violation
**Severity**: critical | high | medium | low

#### Source A / Source B
[quotes and locations]

#### Suggestions
1. [Option A]
2. [Option B]

#### Resolution
<!-- USER: Write your decision below. Be specific. -->

<!-- /Resolution -->
```

After reconciliation, resolved issues get a Status section:

```markdown
#### Resolution
<!-- USER: Write your decision below. Be specific. -->
Use the spec value (100MB).
<!-- /Resolution -->

#### Status
✅ RESOLVED — src/uploader.py:156: Changed MAX_FILE_SIZE to 100MB
```

## Dimension Catalog (A-K)

| Cat | Name | Detects |
|-----|------|---------|
| A | Specification vs Behavior | Docs vs code |
| B | Interface Contract Integrity | Types/schemas vs runtime |
| C | Cross-Reference Consistency | Doc vs doc |
| D | Temporal Consistency | Stale references |
| E | Error Handling Consistency | Error docs vs implementation |
| F | Configuration & Environment | Config docs vs code |
| G | Ambiguity & Underspecification | Vague specs |
| H | Policy & Convention Compliance | ADRs/style guides violated |
| I | Completeness & Documentation Gaps | Missing docs |
| J | Compositional Consistency | Claims valid alone, impossible together |
| K | Implicit Contract Integrity | Names/messages that lie about behavior |
