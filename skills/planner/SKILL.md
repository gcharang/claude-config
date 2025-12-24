---
name: planner
description: Interactive sequential planning for complex tasks. Use when breaking down multi-step projects, system designs, migration strategies, or architectural decisions. Invoked via python script that outputs required actions between steps.
---

# Planner Skill

## Purpose

Two-phase planning workflow with forced reflection pauses:

1. **PLANNING PHASE**: Break down complex tasks into milestones with concrete specifications
2. **REVIEW PHASE**: Orchestrate TW annotation and QR validation before execution

## When to Use

Use the planner skill when the task has:

- Multiple milestones with dependencies
- Architectural decisions requiring documentation
- Migration steps that need coordination
- Complexity that benefits from forced reflection pauses

## When to Skip

Skip the planner skill when the task is:

- Single-step with obvious implementation
- A quick fix or minor change
- Already well-specified by the user

## Workflow Overview

```
PLANNING PHASE (steps 1-N)
    |
    v
Write plan to file
    |
    v
REVIEW PHASE (steps 1-2)
    |-- Step 1: @agent-technical-writer (plan-annotation)
    |-- Step 2: @agent-quality-reviewer (plan-review)
    v
APPROVED --> /plan-execution
```

---

## PLANNING PHASE

### Preconditions

Before invoking step 1, you MUST have:

1. **Plan file path** - If user did not specify, ASK before proceeding
2. **Clear problem statement** - What needs to be accomplished

### Invocation

Script location: `scripts/planner.py` (relative to this skill)

```bash
python3 scripts/planner.py \
  --step-number 1 \
  --total-steps <estimated_steps> \
  --thoughts "<your thinking about the problem>"
```

### Arguments

| Argument        | Description                                      |
| --------------- | ------------------------------------------------ |
| `--phase`       | Workflow phase: `planning` (default) or `review` |
| `--step-number` | Current step (starts at 1)                       |
| `--total-steps` | Estimated total steps for this phase             |
| `--thoughts`    | Your thinking, findings, and progress            |

### Planning Workflow

1. Confirm preconditions (plan file path, problem statement)
2. Invoke step 1 immediately
3. Complete REQUIRED ACTIONS from output
4. Invoke next step with your thoughts
5. Repeat until `STATUS: phase_complete`
6. Write plan to file using format below

---

## Phase Transition: Planning to Review

When planning phase completes, the script outputs an explicit `ACTION REQUIRED` marker:

```
============================================
>>> ACTION REQUIRED: INVOKE REVIEW PHASE <<<
============================================
```

**You MUST invoke the review phase before proceeding to /plan-execution.**

The review phase ensures:

- Temporally contaminated comments are fixed (via @agent-technical-writer)
- Code snippets have WHY comments (via @agent-technical-writer)
- Plan is validated for production risks (via @agent-quality-reviewer)
- Documentation needs are identified

**Why TW is mandatory**: The planning phase naturally produces temporally contaminated comments -- change-relative language ("Added...", "Replaced..."), baseline references ("Instead of...", "Previously..."), and location directives ("After line 425"). These make sense during planning but are inappropriate for production code. TW transforms them to timeless present form before @agent-developer transcribes them verbatim.

Without review, @agent-developer will transcribe contaminated comments directly into production code.

---

## REVIEW PHASE

After writing the plan file, transition to review phase:

```bash
python3 scripts/planner.py \
  --phase review \
  --step-number 1 \
  --total-steps 2 \
  --thoughts "Plan written to [path/to/plan.md]"
```

### Review Step 1: Technical Writer Review and Fix

Delegate to @agent-technical-writer with mode: `plan-annotation`

TW will:

- **Review and fix** temporally contaminated comments (see `resources/temporal-contamination.md`)
- Read ## Planning Context section
- Add WHY comments to code snippets
- Enrich plan prose with rationale
- Add documentation milestone if missing

**This step is never skipped.** Even if plan prose seems complete, code comments from the planning phase require temporal contamination review.

### Review Step 2: Quality Reviewer Validation

Delegate to @agent-quality-reviewer with mode: `plan-review`

QR will:

- Check production reliability (RULE 0)
- Check project conformance (RULE 1)
- Verify TW annotations are sufficient
- Exclude risks already documented in Planning Context
- Return verdict: PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES

### After Review

- **PASS / PASS_WITH_CONCERNS**: Ready for `/plan-execution`
- **NEEDS_CHANGES**: Return to planning phase to address issues

---

## Plan Format

The plan format template is in `resources/plan-format.md`. The script injects this
format when the planning phase completes, so you don't need to reference it manually.

---

## Resources

| Resource                              | Purpose                                                           |
| ------------------------------------- | ----------------------------------------------------------------- |
| `resources/plan-format.md`            | Plan template (injected by script at planning completion)         |
| `resources/diff-format.md`            | Authoritative specification for code change format                |
| `resources/temporal-contamination.md` | Terminology for detecting/fixing temporally contaminated comments |
| `resources/default-conventions.md`    | Default structural conventions when project docs are silent       |

---

## Quick Reference

```bash
# Start planning
python3 scripts/planner.py --step-number 1 --total-steps 4 --thoughts "..."

# Continue planning
python3 scripts/planner.py --step-number 2 --total-steps 4 --thoughts "..."

# Backtrack if needed
python3 scripts/planner.py --step-number 2 --total-steps 4 --thoughts "New info invalidated prior decision..."

# Start review (after plan written)
python3 scripts/planner.py --phase review --step-number 1 --total-steps 2 --thoughts "Plan at ..."

# Continue review
python3 scripts/planner.py --phase review --step-number 2 --total-steps 2 --thoughts "TW done ..."
```
