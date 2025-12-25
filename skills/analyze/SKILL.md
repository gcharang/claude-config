---
name: analyze
description: Systematic codebase analysis with exploration and deep investigation phases. Use for architecture review, performance analysis, security assessment, or quality evaluation. Leverages Explore sub-agent for fast initial discovery.
---

# Analyze Skill

## Purpose

Six-phase analysis workflow with forced reflection pauses:

1. **EXPLORATION**: Fast discovery via Explore sub-agent (Haiku)
2. **FOCUS SELECTION**: Classify investigation areas by priority
3. **INVESTIGATION PLANNING**: Commit to specific files and questions
4. **DEEP ANALYSIS**: Progressive investigation with evidence collection
5. **VERIFICATION**: Validate completeness before synthesis
6. **SYNTHESIS**: Consolidate verified findings into recommendations

## When to Use

Use the analyze skill when the task requires:

- Understanding unfamiliar codebase architecture
- Identifying performance bottlenecks or optimization opportunities
- Security review or vulnerability assessment
- Code quality evaluation and technical debt identification
- Comprehensive review before major refactoring

## When to Skip

Skip the analyze skill when:

- You already understand the codebase well
- The task is a simple bug fix with obvious scope
- User has already provided comprehensive context

---

## Workflow Overview

```
EXPLORATION (Step 1)
    |-- Delegate to Explore sub-agent first
    |-- Process: structure, tech stack, entry points
    v
FOCUS SELECTION (Step 2)
    |-- Classify: architecture, performance, security, quality
    |-- Assign priorities: P1, P2, P3
    |-- Estimate total_steps
    v
INVESTIGATION PLANNING (Step 3)
    |-- Commit to specific files per focus area
    |-- Form hypotheses with expected evidence
    |-- Create accountability contract
    v
DEEP ANALYSIS (Steps 4 to N-2)
    |-- Step 4: Initial investigation (execute plan)
    |-- Step 5: Deepen (trace root causes, find patterns)
    |-- Step 6+: Extended (fill gaps, strengthen evidence)
    v
VERIFICATION (Step N-1)
    |-- Audit: all committed files examined?
    |-- Gaps: any questions unanswered?
    |-- Evidence: all findings have file:line + quoted code?
    |-- If gaps: return to DEEP ANALYSIS
    v
SYNTHESIS (Step N)
    |-- Consolidate by severity (CRITICAL -> LOW)
    |-- Identify systemic patterns
    |-- Provide prioritized action plan
```

---

## Invocation

Script location: `scripts/analyze.py` (relative to this skill)

```bash
python3 scripts/analyze.py \
  --step-number <current_step> \
  --total-steps <estimated_total> \
  --thoughts "<accumulated state from all previous steps>"
```

## Arguments

| Argument        | Required | Description                                              |
| --------------- | -------- | -------------------------------------------------------- |
| `--step-number` | Yes      | Current step (starts at 1)                               |
| `--total-steps` | Yes      | Minimum 6; adjust as understanding grows                 |
| `--thoughts`    | Yes      | Accumulated findings, evidence, and state from all steps |

---

## Step-by-Step Workflow

### Step 1: Exploration

**BEFORE invoking step 1**, delegate to the Explore sub-agent:

```
Use Task tool with subagent_type="Explore":
  "Explore this repository. Report directory structure,
   tech stack, entry points, main components, observed patterns."
```

Then invoke step 1 with the Explore agent's findings in --thoughts.

### Step 2: Focus Selection

Classify codebase against four dimensions:

- **Architecture**: structural concerns, dependencies, layering
- **Performance**: efficiency, database queries, concurrency
- **Security**: input validation, auth flows, data handling
- **Quality**: duplication, complexity, error handling, tests

Assign priorities: P1 (most critical) > P2 > P3

Estimate total_steps based on scope (minimum 6).

### Step 3: Investigation Planning

Create accountability contract:

```
FOCUS AREA: [name] (Priority: P1)

Files to examine:
  - path/to/file.py
    Question: [specific question to answer]
    Hypothesis: [what you expect to find]

Evidence needed:
  - [what would confirm hypothesis]
  - [what would refute it]
```

This is a CONTRACT. You must read every file and answer every question.

### Steps 4-N-2: Deep Analysis

Progressive investigation:

- **Step 4 (Initial)**: Execute plan, document findings with file:line + quoted code
- **Step 5 (Deepen)**: Trace root causes, examine related files, look for patterns
- **Step 6+ (Extended)**: Fill remaining gaps, validate cross-file patterns

### Step N-1: Verification

Before synthesis, verify:

- All committed files were examined
- All questions were answered with evidence
- All [CRITICAL]/[HIGH] findings have quoted code
- No gaps in investigation

If gaps exist: return to DEEP ANALYSIS to fill them.

### Step N: Synthesis

Consolidate verified findings:

- **CRITICAL**: file:line, quoted code, impact, recommended fix
- **HIGH**: file:line, description, recommended fix
- **MEDIUM**: description, general guidance
- **LOW**: patterns, defer to future work

Provide prioritized action plan: IMMEDIATE > SHORT-TERM > LONG-TERM

---

## State Accumulation

Your --thoughts MUST include these sections (from step 2 onward):

```
1. FOCUS AREAS: Each area and its priority
2. INVESTIGATION PLAN: Files and questions committed to
3. FILES EXAMINED: Every file read with observations
4. ISSUES BY SEVERITY: [CRITICAL]/[HIGH]/[MEDIUM]/[LOW] items
5. PATTERNS: Cross-file patterns identified
6. HYPOTHESES: Current theories and evidence
7. REMAINING: What still needs investigation
```

If any section is missing, reconstruct before proceeding.

---

## Evidence Format

All findings must include evidence:

```
[SEVERITY] Brief description (file.py:45-48)
> quoted code from file (2-5 lines)
Explanation: why this is an issue
```

Findings without quoted code are UNVERIFIED.

---

## Dynamic Step Adjustment

Adjust --total-steps as understanding grows:

- **Increase** when investigation reveals more complexity
- **Decrease** when areas prove simpler than expected
- **Minimum**: 6 steps (exploration + focus + planning + 1 analysis + verification + synthesis)

---

## Quick Reference

```bash
# Step 1: After Explore agent returns
python3 scripts/analyze.py --step-number 1 --total-steps 6 \
  --thoughts "Explore found: [summary of structure, tech stack, patterns]"

# Step 2: Focus selection
python3 scripts/analyze.py --step-number 2 --total-steps 7 \
  --thoughts "Structure: ... | Focus: security (P1), quality (P2) | ..."

# Step 3: Investigation planning
python3 scripts/analyze.py --step-number 3 --total-steps 7 \
  --thoughts "[Previous] + PLAN: auth/login.py (Q: input validation?), ..."

# Step 4: Initial investigation
python3 scripts/analyze.py --step-number 4 --total-steps 7 \
  --thoughts "[Previous] + FILES: auth/login.py. [CRITICAL] SQL injection :45"

# Step 5: Deepen investigation
python3 scripts/analyze.py --step-number 5 --total-steps 7 \
  --thoughts "[Previous] + Traced to db/queries.py, pattern in 3 files"

# Step 6: Verification (N-1)
python3 scripts/analyze.py --step-number 6 --total-steps 7 \
  --thoughts "[All findings] Audit: all files read, all questions answered"

# Step 7: Synthesis (N)
python3 scripts/analyze.py --step-number 7 --total-steps 7 \
  --thoughts "[Verified findings] Ready for consolidation"
```
