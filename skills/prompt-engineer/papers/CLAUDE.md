# papers/

Source papers organized by problem type (what they solve, not how they execute).

## Files

| File               | What                    | When to read                    |
| ------------------ | ----------------------- | ------------------------------- |
| `README.md`        | Taxonomy and navigation | Classifying papers, finding fit |
| `REORGANIZATION.md` | Migration rationale     | Understanding taxonomy design   |
| `.gitattributes`   | LFS config              | Never                           |

## Subdirectories

| Directory                   | What                                          | When to read                             |
| --------------------------- | --------------------------------------------- | ---------------------------------------- |
| `reasoning/decomposition/`  | Break problems into sub-problems              | Model can't handle multi-step complexity |
| `reasoning/elicitation/`    | Draw out step-by-step reasoning               | Model skips steps, doesn't show work     |
| `correctness/sampling/`     | Generate multiple candidates, aggregate       | Model gives inconsistent answers         |
| `correctness/verification/` | Explicit checking steps that catch errors     | Model produces unverified claims         |
| `correctness/refinement/`   | Feedback loops that improve output            | Output needs iterative improvement       |
| `context/reframing/`        | Restructure context for better attention      | Context is noisy, poorly framed          |
| `context/augmentation/`     | Retrieve and inject missing information       | Model lacks knowledge to reason with     |
| `efficiency/`               | Reduce token usage, latency, cost             | Output too verbose, inference too slow   |
| `structure/`                | Constrain output format (code, JSON, tables)  | Need specific output format              |
| `references/`               | Surveys, taxonomies, meta-analyses            | Understanding technique landscape        |
