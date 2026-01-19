# Decomposition Techniques

## Overview

Decomposition techniques break complex problems into simpler sub-problems that
models can solve more reliably. Use decomposition when:

- Multi-step reasoning exceeds model capability in a single pass
- Test problems are harder or longer than training exemplars (easy-to-hard
  generalization)
- Problems have natural hierarchical or sequential structure
- Intermediate results need to be verified before proceeding
- Different sub-tasks require specialized handling or external tools

The core tradeoff: decomposition increases API calls and token usage but enables
solving problems that would otherwise fail, provides interpretable reasoning
traces, and allows modular debugging of sub-components.

---

## Techniques

### Least-to-Most Prompting

**Mechanism:** Decompose complex problems into simpler subproblems, then
sequentially solve them using previous answers accumulated in context.

**Triggers:**

- Test problems harder than exemplars (easy-to-hard generalization)
- Compositional generalization with systematic combination
- Multi-step problems where subproblems build on prior solutions
- Length generalization beyond training examples

**Tradeoffs:** 2-3x tokens (decomposition + sequential solving). k+1 API calls
(1 decomposition + k subproblems). Requires few-shot examples for both
decomposition and subproblem solving. Domain-specific decomposition prompts do
not generalize well across domains.

---

### Decomposed Prompting (DecomP)

**Mechanism:** Decompose complex tasks into simpler sub-tasks delegated to
specialized prompts in a shared library, with hierarchical or recursive
decomposition possible.

**Triggers:**

- Individual reasoning steps hard to learn in monolithic prompt
- Sub-components need specialized knowledge or capabilities
- Multi-hop reasoning requiring retrieval or external tools
- Need to swap sub-task implementations without changing overall system
- Isolated debugging of sub-components would improve accuracy

**Tradeoffs:** Variable token overhead depending on decomposition depth.
Multiple adaptive calls -- 1 decomposer + k sub-task handlers per step. Requires
upfront task decomposition design. Enables modular optimization and tool
integration at cost of increased latency.

---

### ADAPT (As-Needed Decomposition)

**Mechanism:** Recursively decompose tasks only when executor fails, adapting
decomposition depth to task complexity dynamically.

**Triggers:**

- Multi-step tasks with unpredictable sub-task complexity
- Navigation or exploration in unknown environments
- Compositional tasks where some sub-tasks harder than others
- Tasks requiring both high-level planning and low-level execution
- Interactive decision-making with long action trajectories

**Tradeoffs:** Adaptive 2-4x tokens depending on task complexity. 1 to d_max
recursive levels of planner + executor calls. Requires environment interaction
capabilities and self-evaluation in executor. Only decomposes when needed,
avoiding redundant re-execution.

---

### Tree of Thoughts (ToT)

**Mechanism:** Maintain tree of intermediate thoughts, explore multiple
reasoning paths via search (BFS/DFS) with LM-based evaluation and backtracking.

**Triggers:**

- Task requires exploration or strategic lookahead
- Initial decisions play pivotal role in solution quality
- Problem involves search through combinatorial space
- Multiple valid reasoning paths exist requiring evaluation
- Need backtracking when reasoning hits dead ends

**Tradeoffs:** 5-100x tokens vs CoT depending on search depth/breadth. Adaptive
API calls based on search algorithm -- typically 10-100+ calls. Requires few-shot
examples for thought generation plus state evaluation prompts. Not needed for
tasks where LM already excels via simpler methods.

---

### Selection-Inference

**Mechanism:** Alternate between selecting relevant facts from context and
making single-step inferences to build causal reasoning chains.

**Triggers:**

- Multi-step logical reasoning with 2+ inference steps
- Context contains both relevant and irrelevant facts
- Deductive/inductive reasoning requiring step-by-step justification
- Tasks requiring causal, interpretable reasoning traces
- Vanilla LLMs struggle with multi-hop reasoning

**Tradeoffs:** N x 2 steps tokens where N is reasoning depth. 2N API calls
(selection + inference per step). Requires few-shot examples for both selection
and inference modules. Fixed halting depth must be predetermined.

---

### Plan-and-Solve Prompting

**Mechanism:** Replace "Let's think step by step" with explicit plan-devising
and plan-execution instructions to reduce missing steps.

**Triggers:**

- Multi-step reasoning with calculation errors
- Complex tasks prone to missing intermediate steps
- Problems requiring explicit variable extraction
- Arithmetic word problems requiring step-by-step planning
- Zero-shot scenarios where manual examples unavailable

**Tradeoffs:** 2x tokens. 2 API calls (reasoning generation + answer
extraction). Zero-shot approach eliminates need for manual few-shot examples.
Does not address semantic misunderstanding errors.

---

### Self-Ask

**Mechanism:** Model explicitly generates and answers follow-up sub-questions
before answering the main compositional question.

**Triggers:**

- Multi-hop questions requiring composition of separately-known facts
- Model knows sub-facts but fails to compose them
- Compositional reasoning where intermediate steps need external verification
- Tasks requiring explicit sub-question formulation for tool integration

**Tradeoffs:** 2-3x tokens vs direct prompting, 30% fewer than least-to-most. 1
call for self-ask alone, 1+k calls with search (k=number of follow-ups).
Requires few-shot examples demonstrating self-questioning pattern. May generate
unnecessary decomposition for simple queries.

---

### Successive Prompting

**Mechanism:** Iteratively decompose complex questions into simple QA pairs,
solve each, and repeat until final answer is reached.

**Triggers:**

- Complex multi-step questions requiring latent decisions
- Questions involving multiple arithmetic operations
- Compositional reading comprehension with sequential reasoning
- Problems where intermediate QA pairs can be explicitly articulated

**Tradeoffs:** k iterations where k is decomposition depth (typically 2-10x
tokens). 2k API calls per question (k QD + k QA calls). Requires decomposition
examples and separate QD/QA indices. Fine-tuning QA module provides ~10% F1
gain.

---

### Branch-Solve-Merge (BSM)

**Mechanism:** Decompose tasks into parallel sub-tasks via branching, solve each
independently, then merge solutions into final output.

**Triggers:**

- Multi-faceted tasks requiring evaluation against multiple criteria
- Constrained generation with multiple constraints to satisfy
- Evaluation of long-form responses to arbitrary questions
- Problems where parallel sub-task decomposition more natural than sequential
- LLM evaluation exhibiting position, length, or self-enhancement biases

**Tradeoffs:** 3-7x tokens depending on branching factor. k+2 API calls (1
branch + k solve + 1 merge), where k typically 2-5. Zero-shot prompts for
branch/solve/merge modules. Parallel decomposition enables better performance
than sequential approaches.

---

### Divide-and-Conquer Prompting

**Mechanism:** Divide input into parallel sub-inputs, solve independently, then
merge results without sequential dependency.

**Triggers:**

- Long sequences with repetitive sub-tasks (e.g., large integer arithmetic)
- Deceptive/misleading content requiring independent verification
- Task decomposable into parallel homogeneous sub-tasks without dependencies
- Task complexity exceeds TC^0 (e.g., NC^1-complete problems)
- Long document analysis where segments can be verified independently

**Tradeoffs:** k+2 API calls (decompose + k sub-tasks + merge). Recursive for
multi-level decomposition. Requires three distinct prompts: decomposition,
sub-task tackling, solution merge. Not suitable for sequential tasks with
dependent sub-steps.

---

### Skeleton-of-Thought

**Mechanism:** Generate answer skeleton first, then expand each point in
parallel via batched decoding or parallel API calls.

**Triggers:**

- Question answerable as list of independent points
- Answer covers multiple perspectives expandable separately
- Generic questions about types, tips, categories, or aspects
- Knowledge/commonsense questions with multiple facets
- Latency reduction critical for user experience

**Tradeoffs:** 30-90x prefilling tokens (batched decoding reuses common prefix).
1 + k parallel calls (skeleton + k point expansions). Achieves 2-2.39x speedup.
Fails on step-by-step reasoning where later steps depend on earlier step details
(math, coding).

---

### Cumulative Reasoning

**Mechanism:** Orchestrate Proposer, Verifier, and Reporter roles to build DAG
of verified reasoning steps iteratively.

**Triggers:**

- Multi-step reasoning requiring verified intermediate steps
- Logical inference problems with multiple premises
- Complex mathematical problems with cumulative derivations
- Tasks where error propagation must be prevented
- Problems requiring systematic exploration of validated knowledge

**Tradeoffs:** 2-3x tokens per iteration cycle. n iterations with Proposer +
Verifier + Reporter calls. Requires few-shot examples for role prompts and DAG
state management. More efficient than ToT (98% accuracy with 14.86 states vs 74%
with 61.72 states on Game of 24).

---

## Decision Guidance

**Start simple:** Use Plan-and-Solve or Self-Ask for zero-shot scenarios where
you lack few-shot examples.

**Sequential dependencies:** Use Least-to-Most or Successive Prompting when
later subproblems depend on earlier solutions.

**Parallel sub-tasks:** Use Branch-Solve-Merge or Divide-and-Conquer when
sub-problems are independent and can be solved simultaneously.

**Uncertain complexity:** Use ADAPT when task difficulty is unpredictable and
you want decomposition only when needed.

**Search required:** Use Tree of Thoughts when exploration, backtracking, or
strategic lookahead is essential.

**Tool integration:** Use Decomposed Prompting when sub-tasks require external
APIs, retrieval, or specialized handling.

**Verification critical:** Use Selection-Inference or Cumulative Reasoning when
intermediate steps need explicit validation.

---

## Composability Notes

**Layer techniques:** Decomposition composes well with:

- Self-consistency voting on sub-problem solutions
- Verification steps at each decomposition level
- Retrieval augmentation for knowledge-intensive sub-tasks

**Conflicts:**

- Skeleton-of-Thought conflicts with CoT/ToT/Least-to-Most (parallel vs
  sequential reasoning)
- Divide-and-Conquer conflicts with CoT/Least-to-Most (independent vs dependent
  sub-steps)

**Common patterns:**

- Decomposition + Self-Consistency: Apply voting to each sub-problem
- Decomposition + Verification: Check intermediate results before proceeding
- Decomposition + Tool Use: Route sub-tasks to appropriate handlers
- Recursive decomposition: Apply same technique to sub-problems that remain too
  complex
