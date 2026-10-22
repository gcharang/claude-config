# Reference Selection Guide

These reference documents contain research-backed prompt engineering techniques
organized by problem type. Each file synthesizes findings from multiple papers
into actionable guidance.

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

## Navigation Anti-patterns

Do not read `papers/**/*.md` directly: the source paper summaries are too granular for the optimization workflow, and the reference files here synthesize them into actionable techniques.

## Usage in Prompt Optimization Workflow

`skills/scripts/skills/prompt_engineer/optimize.py` has the model choose the categories (`CATEGORY_SELECTION_INSTRUCTIONS`) and embeds the chosen files in the next step (`CATEGORY_TO_FILE`, `format_output`).
