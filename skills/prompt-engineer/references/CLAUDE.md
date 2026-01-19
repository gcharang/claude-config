# references/

Research-backed prompt engineering technique references, organized by problem type.

## Decision Tree

```
What is your PRIMARY problem?
|
+-> INPUT issues (context too long/noisy/missing)?
|   YES -> context/reframing.md or context/augmentation.md
|
+-> OUTPUT issues:
    |
    +-> Model can't reason through problem -> reasoning/*.md
    +-> Model reasons but wrong answers   -> correctness/*.md
    +-> Output too verbose/expensive      -> efficiency.md
    +-> Need specific format              -> structure.md
```

## Files

| File                          | Problem It Solves                        | When to Read                                     |
| ----------------------------- | ---------------------------------------- | ------------------------------------------------ |
| `reasoning/decomposition.md`  | Model can't handle multi-step complexity | Task requires breaking into sub-problems         |
| `reasoning/elicitation.md`    | Model skips steps, doesn't show work     | Need step-by-step reasoning traces               |
| `correctness/sampling.md`     | Model gives inconsistent answers         | Same input produces different (wrong) outputs    |
| `correctness/verification.md` | Model produces unverified claims         | Output contains factual errors or hallucinations |
| `correctness/refinement.md`   | Output needs iterative improvement       | First-pass output is acceptable but not optimal  |
| `context/reframing.md`        | Context is noisy or poorly framed        | Model ignores relevant info or focuses on noise  |
| `context/augmentation.md`     | Model lacks knowledge to reason with     | Task requires facts not in context or training   |
| `efficiency.md`               | Output too verbose, inference too slow   | Need to reduce tokens while maintaining quality  |
| `structure.md`                | Need specific output format              | Must produce code, JSON, tables, or constrained  |

## NEVER Read

- `papers/**/*.md` - Source paper summaries, too granular for optimization workflow
- `papers/**/*.yaml` - Paper metadata, not actionable guidance
- `papers/**/*.pdf` - Original papers, not consumable

## Usage in Workflow

The optimize.py script selects references based on diagnosed problem:

1. **Triage** determines scope (single-prompt, ecosystem, greenfield, problem)
2. **Assess/Diagnose** identifies the specific failure mode
3. **Plan/Design** reads relevant references based on failure mode:
   - Reasoning failures -> reasoning/\*.md
   - Consistency failures -> correctness/\*.md
   - Context issues -> context/\*.md
   - Verbosity issues -> efficiency.md
   - Format issues -> structure.md
