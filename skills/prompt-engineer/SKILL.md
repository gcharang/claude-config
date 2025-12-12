---
name: prompt-optimizer
description: Optimize system prompts for Claude Code agents using proven prompt engineering patterns. Use when users request prompt improvement, optimization, or refinement for agent workflows, tool instructions, or system behaviors.
---

# Prompt Optimizer

Optimizes system prompts by applying research-backed prompt engineering patterns. This skill operates through human-in-the-loop phases: understand, plan, propose changes, receive approval, then integrate.

## Purpose and Success Criteria

A well-optimized prompt achieves three things:

1. **Behavioral clarity**: The agent knows exactly what to do in common cases and how to handle edge cases.
2. **Appropriate scope**: Complex tasks get systematic decomposition; simple tasks don't trigger overthinking.
3. **Grounded changes**: Every modification traces to a specific pattern with documented behavioral impact.

Optimization is complete when:

- Every change has explicit pattern attribution from the reference document
- No section contradicts another section
- The prompt matches its operating context (tool-use vs. conversational, token constraints, failure modes)
- Human has approved both section-level changes and full integration

## When to Use This Skill

Use when the user provides a prompt and wants it improved, refined, or reviewed for best practices.

Do NOT use for:

- Writing prompts from scratch (different skill)
- Prompts that are already working well and user just wants validation (say so, don't force changes)
- Non-prompt content (documentation, code, etc.)

## Required Resources

Before ANY analysis, read the pattern reference:

```
references/prompt-engineering.md
```

This contains the complete catalog of applicable patterns, including:

- The **Technique Selection Guide** table (maps domains, trigger conditions, stacking compatibility, conflicts, and expected effects)
- The **Quick Reference: Key Principles** (numbered list of foundational techniques)
- Domain-organized technique sections with research citations and examples
- The **Anti-Patterns to Avoid** section documenting common failure modes

All technique selection decisions must be grounded in this reference. Do not apply patterns from memory or general knowledge—consult the reference to ensure accuracy and to surface stacking/conflict information.

---

## Phase 0: Triage

Not every prompt needs the full optimization process. Before proceeding, assess complexity.

**Simple prompts** (use lightweight process):

- Under 20 lines
- Single clear purpose (one tool, one behavior)
- No conditional logic or branching
- No inter-section dependencies

**Complex prompts** (use full process):

- Multiple sections serving different functions
- Conditional behaviors or rule hierarchies
- Tool orchestration or multi-step workflows
- Known failure modes that need addressing

### Lightweight Process (Simple Prompts)

For simple prompts, skip section decomposition. Instead:

1. Read the prompt once, identify its purpose
2. Consult the reference's Anti-Patterns section to check for obvious problems
3. Consult the Technique Selection Guide to identify 1-3 applicable patterns
4. Propose targeted changes with pattern attribution
5. Present the optimized prompt directly

Do not over-engineer simple prompts.

### Full Process (Complex Prompts)

Proceed to Phase 1.

---

## Phase 1: Understand the Prompt

Before decomposing or modifying anything, understand what the prompt is trying to accomplish and the context in which it operates. This understanding phase is essential—without it, technique selection becomes guesswork.

Answer these questions (internally, not presented to user unless clarification needed):

### 1.1 Operating Context

- **Interaction model**: Is this single-shot (tool description, one-time instruction) or conversational (back-and-forth with user)?
- **Agent type**: Tool-use agent, coding agent, analysis agent, or general assistant?
- **Token constraints**: Is brevity critical, or is thoroughness more important?
- **Failure modes**: What goes wrong when this prompt fails? What behaviors is it trying to prevent?

### 1.2 Current State Assessment

- **What's working**: Which parts of the prompt are clear and effective? (Preserve these.)
- **What's unclear**: Which instructions are ambiguous or could be misinterpreted?
- **What's missing**: Are there obvious gaps—edge cases unhandled, examples absent, priorities unclear?

### 1.3 Document Observations

Before consulting the reference, write down specific observations about problems in the prompt. Examples of observable problems:

- "Lines 12-15 use hedging language ('might want to', 'could try')"
- "No examples provided for the expected output format"
- "Multiple rules marked CRITICAL with no clear precedence"
- "Instructions say what NOT to do but don't specify what TO do"

These observations become the input to technique selection in Phase 2.

---

## Phase 2: Plan — Select Techniques from Reference

With the prompt understood and problems documented, consult the reference to devise a plan.

### 2.1 Consult the Technique Selection Guide

Open the reference document and locate the **Technique Selection Guide** table. This table maps:

- **Domain** (Reasoning, Input, Example Design, Output, NLU, Behavioral, Verification)
- **Technique** name
- **Trigger Condition** (when to apply)
- **Stacks With** (compatible techniques)
- **Conflicts With** (incompatible techniques)
- **Cost/Tradeoff**
- **Effect** (expected behavioral impact with research citations)

For each documented problem from Phase 1.3, scan the Trigger Condition column to identify candidate techniques. Record:

1. Which technique addresses the problem
2. What it stacks with (so you can combine complementary patterns)
3. What it conflicts with (so you avoid contradictory applications)
4. The expected effect and any cost/tradeoff

### 2.2 Check the Anti-Patterns Section

Before finalizing the plan, consult the reference's **Anti-Patterns to Avoid** section. Verify that your planned changes don't introduce known failure modes such as:

- The Hedging Spiral
- The Everything-Is-Critical Problem
- The Implicit Category Trap
- The Soft Attention Trap
- The Negative Instruction Trap

### 2.3 Formulate the Optimization Plan

Describe the plan before executing it:

```markdown
## Optimization Plan

**Problems identified**:

1. [Problem from Phase 1.3]
2. [Problem from Phase 1.3]
   ...

**Techniques to apply**:
| Problem | Technique | Reference Section | Stacks With | Conflicts With |
|---------|-----------|-------------------|-------------|----------------|
| 1 | [name] | [section] | [if any] | [if any] |
| 2 | [name] | [section] | [if any] | [if any] |

**Application order**: [List techniques in order, grouping compatible ones]

**Conflict check**: [Note any conflicts between planned techniques and how to resolve]
```

Do not proceed to Phase 3 until you have a concrete plan grounded in the reference.

---

## Phase 3: Execute — Section-by-Section Optimization

With the plan established, apply techniques to the prompt systematically.

### 3.1 Decompose the Prompt

Decompose the prompt into functional sections. Sections are defined by **what function they serve**, not by formatting or headers in the original. Common section functions include:

- Identity establishment
- Capability descriptions
- Tool instructions
- Constraints and prohibitions
- Priority rules
- Output format requirements
- Examples

### 3.2 Apply Techniques per Section

For each section, apply the relevant techniques from your plan. Present each change to the user with:

```markdown
#### Change N

- **Section**: [Which functional section]
- **Problem**: [What's wrong, from Phase 1.3]
- **Technique**: [Name from reference]
- **Reference**: [Section/subsection in the reference document]
- **Before**: [Original text]
- **After**: [Modified text]
- **Expected impact**: [From the reference's Effect column or technique description]
```

### 3.3 Quality Standards for Changes

**Every change must**:

- Cite a specific technique from the reference
- Identify the problem it solves
- Show before/after text
- State the expected behavioral impact

**Avoid**:

- Applying techniques without identifying what problem they solve
- Introducing hedging language ("might", "could", "perhaps")
- Escalating emphasis without justification (adding CRITICAL to routine instructions)
- Removing functionality that was working

### 3.4 Handle Conflicts

When multiple techniques could apply to the same text but suggest different approaches, present the conflict to the user:

```markdown
### Pattern Conflict: [Section Name]

**Context**: [The text in question]

**Option A: [Technique Name]**

- Application: [How it would change the text]
- Benefits: [What it achieves]
- Trade-offs: [What you might lose]

**Option B: [Technique Name]**

- Application: [How it would change the text]
- Benefits: [What it achieves]
- Trade-offs: [What you might lose]

**Recommendation**: [Which option and why, based on the prompt's operating context from Phase 1]
```

Wait for user decision before proceeding.

---

## Phase 4: Integrate and Verify

After section-by-section changes are approved, assemble the complete prompt and review holistically.

### 4.1 Integration Checks

1. **Cross-section coherence**: Do sections reference each other correctly? Are there dangling references to removed content?

2. **Terminology consistency**: Does the prompt use the same terms throughout? (e.g., don't switch between "user", "human", and "person")

3. **Priority consistency**: If multiple sections establish priorities, do they align?

4. **Emphasis audit**: Count emphasis markers (CRITICAL, IMPORTANT, NEVER, ALWAYS). Per the reference's anti-patterns section, if more than 2-3 items use highest-level emphasis, reconsider.

5. **Flow and ordering**: Does the prompt follow logical progression?

### 4.2 Token Efficiency Review

If the prompt has grown significantly:

- Remove redundant explanations (say it once, clearly)
- Consolidate related instructions
- Replace verbose descriptions with concise examples
- Check if any added examples can be shortened without losing contrastive value

Do NOT sacrifice clarity for brevity. Per the reference, longer instructions for safety-critical operations are appropriate.

### 4.3 Final Anti-Pattern Check

Re-consult the reference's Anti-Patterns section. Verify the optimized prompt doesn't exhibit:

- Overuse of emphasis markers
- Hedging language
- Negative instructions where affirmative would work
- Implicit categories without explicit principles
- Any other documented anti-patterns

### 4.4 Present Final Optimization

```markdown
## Optimized Prompt

[Complete optimized prompt text]

## Summary of Changes

**Patterns applied**: [List of unique patterns used, with reference sections]

**Major improvements**:

1. [Most significant change and its impact]
2. [Second most significant]
3. [Third most significant]

**Preserved from original**: [What was already working well and kept]

**Token change**: [Original length] → [New length] ([+/-X%])
```

---

## Completion Checkpoint

Before presenting the final prompt, verify:

- [ ] Phase 1 context assessment was completed (operating context understood)
- [ ] Phase 2 plan was formulated by consulting the reference's Technique Selection Guide
- [ ] Every change cites a specific technique from the reference document
- [ ] No pattern was applied without identifying the problem it solves
- [ ] Stacking compatibility was checked; no conflicting patterns applied together
- [ ] Pattern conflicts were presented to user and resolved
- [ ] No section contradicts another section
- [ ] Anti-patterns section was consulted; no anti-patterns introduced
- [ ] Emphasis markers are used sparingly (≤3 highest-level markers)
- [ ] Cross-section terminology is consistent
- [ ] Simple prompts were not over-engineered (Phase 0 triage respected)
- [ ] Human approved section-level changes before integration

If any checkbox fails, address it before presenting the final prompt.

---

## Quick Reference: The Process

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. READ THE REFERENCE                                           │
│    Load references/prompt-engineering.md before any analysis    │
├─────────────────────────────────────────────────────────────────┤
│ 2. UNDERSTAND THE PROMPT (Phase 1)                              │
│    - Operating context (single-shot? tool-use? constraints?)    │
│    - Current state (working? unclear? missing?)                 │
│    - Document specific, observable problems                     │
├─────────────────────────────────────────────────────────────────┤
│ 3. PLAN USING THE REFERENCE (Phase 2)                           │
│    - Match problems → Technique Selection Guide trigger         │
│      conditions                                                 │
│    - Check stacking compatibility and conflicts                 │
│    - Verify against Anti-Patterns section                       │
│    - Write out the plan before executing                        │
├─────────────────────────────────────────────────────────────────┤
│ 4. EXECUTE SECTION BY SECTION (Phase 3)                         │
│    - Decompose prompt into functional sections                  │
│    - Apply techniques from plan with full attribution           │
│    - Present changes for approval                               │
├─────────────────────────────────────────────────────────────────┤
│ 5. INTEGRATE AND VERIFY (Phase 4)                               │
│    - Check cross-section coherence                              │
│    - Audit emphasis usage                                       │
│    - Final anti-pattern check                                   │
│    - Present complete optimized prompt                          │
└─────────────────────────────────────────────────────────────────┘
```
