# Codebase Analysis

Builds an evidence-based understanding of a codebase before planning work in it:
structure, patterns, flows, decisions and context. It describes; it does not grade.

| Step       | What happens                                                                  |
| ---------- | ----------------------------------------------------------------------------- |
| Scope      | Turn the request into 1-3 understanding goals                                 |
| Survey     | Dispatch 1-5 haiku sub-agents, one per focus area, each running `subagent.py` |
| Deepen     | Read and trace the least-understood areas directly; 1-4 iterations            |
| Synthesize | Summary with Structure, Patterns, Flows, Decisions and Context sections       |

## When to Use

Before planning a change in an unfamiliar codebase, or before a refactor or architecture
discussion that needs grounded understanding. Skip it when you already know the codebase
or the user has given the context.

## Example Usage

```
Use your codebase-analysis skill to understand this codebase before we plan the authentication refactor.
```
