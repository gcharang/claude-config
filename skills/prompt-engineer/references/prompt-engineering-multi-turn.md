# Prompt Engineering: Research-Backed Techniques for Multi-Turn Prompts

This document synthesizes practical prompt engineering patterns with academic
research on iterative LLM reasoning. All techniques target **multi-turn
prompts**—structured sequences of messages where output from one turn becomes
input to subsequent turns. These techniques leverage the observation that models
can improve their own outputs through deliberate self-examination across
multiple passes.

**Prerequisite**: This guide assumes familiarity with single-turn techniques
(CoT, Plan-and-Solve, RE2, etc.). Multi-turn techniques often enhance or extend
single-turn methods across message boundaries.

**Meta-principle**: The value of multi-turn prompting comes from separation of
concerns—each turn has a distinct cognitive goal (generate, critique, verify,
synthesize). Mixing these goals within a single turn reduces effectiveness.

---

## Why External Verification?

Before diving into techniques, a critical constraint must be understood: **LLMs
cannot reliably self-correct reasoning without external feedback**.

Per Huang et al. (2024) in "Large Language Models Cannot Self-Correct Reasoning
Yet":

> "We find that without external feedback, self-correction not only fails to
> improve LLMs' performance on reasoning tasks but can even exacerbate reasoning
> errors... the performance drops after Self-Correction in all reasoning tasks."

**Quantitative evidence:**

| Model | Task          | Standard | Self-Correct R1 | Self-Correct R2 |
| ----- | ------------- | -------- | --------------- | --------------- |
| GPT-4 | GSM8K         | 95.5%    | 91.5%           | 89.0%           |
| GPT-4 | CommonSenseQA | 82.0%    | 79.5%           | 80.0%           |
| GPT-4 | HotpotQA      | 49.0%    | 49.0%           | 43.0%           |

Performance degrades with each self-correction round when no external signal
guides the correction.

**Why does self-correction fail?**

Per the paper: "For GSM8K, 74.7% of time GPT-3.5 retains initial answer. Among
remaining instances, model more likely to modify correct answer to incorrect one
than revise incorrect to correct."

When asked to "review your answer," models either:

1. Keep the original answer (most common)
2. Change correct answers to incorrect ones (when they do change)

**The implication for this guide:** Every technique presented here relies on
some form of external signal—verification questions answered in isolated context
(CoVe), tool-based validation (CRITIC), multi-sample comparison (USC), or
structured aggregation (Multi-Expert). The techniques that work all avoid asking
the model to simply "review and improve" its own reasoning.

---

## Technique Selection Guide

| Domain             | Technique                  | Trigger Condition                                       | Stacks With                         | Conflicts With                | Cost/Tradeoff                                  | Effect                                                   |
| ------------------ | -------------------------- | ------------------------------------------------------- | ----------------------------------- | ----------------------------- | ---------------------------------------------- | -------------------------------------------------------- |
| **Pre-Processing** | System 2 Attention         | Input contains irrelevant/misleading content            | Any downstream technique            | —                             | 2x tokens (filter + generate)                  | +17.5% on QA with opinions; reduces sycophancy           |
| **Refinement**     | Self-Refine                | Output quality improvable through iteration             | Any single-turn reasoning technique | Time-critical tasks           | 2-4x tokens per iteration                      | 5-40% absolute improvement across 7 task types           |
| **Refinement**     | Iterative Critique         | Specific quality dimensions need improvement            | Self-Refine, Format Strictness      | —                             | Moderate; targeted feedback reduces iterations | Monotonic improvement on scored dimensions               |
| **Verification**   | Chain-of-Verification      | Factual accuracy critical; hallucination risk           | Quote Extraction (single-turn)      | Joint verification            | 3-4x tokens (baseline + verify + revise)       | List-based QA: 17%→70% accuracy; FACTSCORE: 55.9→71.4    |
| **Verification**   | Factored Verification      | High hallucination persistence in joint verification    | CoVe                                | Joint CoVe                    | Additional token cost for separation           | Outperforms joint CoVe by 3-8 points across tasks        |
| **Verification**   | CRITIC (Tool-Interactive)  | Verifiable claims; external tools available             | CoVe, Self-Refine                   | Intrinsic self-correction     | Tool API costs + verification tokens           | +7.7 F1 on QA; +7.0% on math; 79.2% toxicity reduction   |
| **Aggregation**    | Universal Self-Consistency | Free-form output; standard SC inapplicable              | Any sampling technique              | Greedy decoding               | N samples + 1 selection call                   | Matches SC on math; enables SC for open-ended tasks      |
| **Aggregation**    | Multi-Chain Reasoning      | Evidence scattered across reasoning attempts            | Self-Consistency, CoT               | Single-chain reliance         | N chains + 1 meta-reasoning call               | +5.7% over SC on multi-hop QA; high-quality explanations |
| **Aggregation**    | Complexity-Weighted Voting | Varying reasoning depth across samples                  | Self-Consistency, USC               | Simple majority voting        | Minimal; selection strategy only               | Further gains over standard SC (+2-3 points)             |
| **Aggregation**    | Multi-Expert Prompting     | Open-ended tasks; multiple valid perspectives           | USC                                 | Iterative debate approaches   | Single aggregation turn                        | 89.35% on TruthfulQA vs 77.11% USC                       |
| **Meta-Reasoning** | Chain Synthesis            | Multiple valid reasoning paths exist                    | MCR, USC                            | —                             | Moderate; synthesis pass                       | Combines complementary facts from different chains       |
| **Meta-Reasoning** | Explanation Generation     | Interpretability required alongside answer              | MCR                                 | —                             | Included in meta-reasoning pass                | 82% of explanations rated high-quality                   |
| **Meta-Reasoning** | Cumulative Reasoning       | Complex reasoning requiring validated step accumulation | External verifiers (code, tools)    | Linear CoT for formal domains | 3+ roles per step; DAG state management        | 98% on Game of 24 vs 74% ToT; +43% on MATH Level 5       |

---

## Quick Reference: Key Principles

1. **External Verification Required** — Intrinsic self-correction degrades
   performance (74.7% keep original; when changed, more likely wrong); all
   effective techniques use external signals
2. **Self-Refine for Iterative Improvement** — 5-40% absolute improvement when
   feedback is actionable and specific; vague feedback fails
3. **Separate Feedback from Refinement** — Generate feedback in one turn, apply
   it in another; mixing degrades both
4. **Factored Verification Beats Joint** — Answer verification questions without
   baseline in context; +3-8 points over joint verification
5. **Shortform Questions Beat Longform** — 70% accuracy on individual
   verification questions vs. 17% for same facts in longform generation
6. **Tool-Interactive Verification** — CRITIC achieves +7.7 F1 on QA, +7.0% on
   math via external tool validation
7. **Filter Context Before Reasoning** — S2A improves QA +17.5% by removing
   irrelevant/misleading content before main task
8. **Universal Self-Consistency for Free-Form** — Matches standard SC on
   structured tasks; enables consistency selection where exact-match voting
   impossible
9. **Multi-Chain Reasoning for Evidence Collection** — +5.7% over SC on
   multi-hop QA; 82% of explanations rated high-quality
10. **Meta-Reasoning Over Chains** — Second model pass synthesizing all chains
    outperforms majority voting
11. **Complexity-Weighted Voting** — Top-K complex chains: 80.5% vs 78.0%
    standard SC on GSM8K
12. **History Accumulation Helps** — Retain previous feedback and outputs;
    models learn from past mistakes
13. **Open Questions Beat Yes/No** — Models tend to agree with yes/no regardless
    of correctness; open questions force factual recall
14. **Stopping Conditions Matter** — Use explicit quality thresholds or
    iteration limits; models rarely self-terminate optimally
15. **Non-Monotonic Improvement Possible** — Track best-so-far, not just final
    output; quality may regress on some dimensions
16. **Structured Aggregation for Open-Ended Tasks** — Multi-Expert with NGT:
    89.35% vs 77.11% USC on TruthfulQA

---

## 1. Context Filtering (Pre-Processing)

Before main task execution, filter the input context to remove irrelevant or
misleading information.

### System 2 Attention (S2A)

A pre-processing technique that regenerates input context to remove distractors.
Per Weston & Sukhbaatar (2023): "System 2 Attention (S2A), whereby an LLM
performs a deliberate attention process... We seek to refine the context, not
the response."

**The key insight:**

Standard attention mechanisms weight all context tokens. S2A uses deliberate
reasoning to filter context before the main task, removing information that
could mislead or bias the response.

**The two-step process:**

```
Turn 1 (Context Filtering):
  Input: Original context with potential distractors
  Prompt: Extract relevant parts for accurate response
  Output: Filtered context x'

Turn 2 (Task Execution):
  Input: Filtered context x' + task
  Output: Response based on cleaned context
```

**The filtering prompt:**

Per the paper:

```
Given the following text by a user, extract the part that is related and
useful, so that using that text alone would be good context for providing
an accurate and correct answer to the question. Please include the actual
question or task.

{original_context_with_question}

Extracted relevant parts:
```

**Performance:**

| Task                  | Baseline | S2A         | Improvement |
| --------------------- | -------- | ----------- | ----------- |
| QA with opinions      | 62.8%    | 80.3%       | +17.5%      |
| Math with distractors | ~65%     | ~77%        | +12%        |
| Sycophancy reduction  | baseline | significant | —           |

**When to use S2A:**

1. **Opinion-contaminated context**: User provides question with embedded
   opinion that might bias response
2. **Distractor-heavy input**: Context contains irrelevant information that
   could mislead reasoning
3. **Sycophancy-prone scenarios**: User's stated preference might override
   factual accuracy

**Example from the paper:**

```
Original context:
"I think the answer to this math problem is 42, but can you check?
What is 15 + 29?"

S2A filtered context:
"What is 15 + 29?"

Result: Model correctly answers 44 without being biased by user's incorrect suggestion
```

**Non-obvious insight:** S2A requires _exclusive_ filtering—include only the
filtered context, not both original and filtered. Per the paper, when both are
present, the model still attends to problematic parts. The filtering must be
hard (sharp), not soft.

**Distinction from CoVe:**

S2A filters input context before generation. CoVe refines output response after
generation. They address different problems and can be combined: S2A → Generate
→ CoVe.

---

## 2. Iterative Refinement

Techniques where the model critiques and improves its own output across multiple
turns.

### Self-Refine

A general-purpose iterative improvement framework. Per Madaan et al. (2023):
"SELF-REFINE: an iterative self-refinement algorithm that alternates between two
generative steps—FEEDBACK and REFINE. These steps work in tandem to generate
high-quality outputs."

**The core loop:**

```
Turn 1 (Generate):
  Input: Task description + prompt
  Output: Initial response y₀

Turn 2 (Feedback):
  Input: Task + y₀ + feedback prompt
  Output: Actionable, specific feedback fb₀

Turn 3 (Refine):
  Input: Task + y₀ + fb₀ + refine prompt
  Output: Improved response y₁

[Iterate until stopping condition]
```

**Critical quality requirements for feedback:**

Per the paper: "By 'actionable', we mean the feedback should contain a concrete
action that would likely improve the output. By 'specific', we mean the feedback
should identify concrete phrases in the output to change."

**CORRECT feedback (actionable + specific):**

```
This code is slow as it uses a for loop which is brute force.
A better approach is to use the formula n(n+1)/2 instead of iterating.
```

**INCORRECT feedback (vague):**

```
The code could be more efficient. Consider optimizing it.
```

**History accumulation improves refinement:**

The refinement prompt should include all previous iterations. Per the paper: "To
inform the model about the previous iterations, we retain the history of
previous feedback and outputs by appending them to the prompt. Intuitively, this
allows the model to learn from past mistakes and avoid repeating them."

```
Turn N (Refine with history):
  Input: Task + y₀ + fb₀ + y₁ + fb₁ + ... + yₙ₋₁ + fbₙ₋₁
  Output: Improved response yₙ
```

**Performance:** "SELF-REFINE outperforms direct generation from strong LLMs
like GPT-3.5 and GPT-4 by 5-40% absolute improvement" across dialogue response
generation, code optimization, code readability, math reasoning, sentiment
reversal, acronym generation, and constrained generation.

**When Self-Refine works best:**

| Task Type                    | Improvement | Notes                                        |
| ---------------------------- | ----------- | -------------------------------------------- |
| Code optimization            | +13%        | Clear optimization criteria                  |
| Dialogue response            | +35-40%     | Multi-aspect quality (relevance, engagement) |
| Constrained generation       | +20%        | Verifiable constraint satisfaction           |
| Math reasoning (with oracle) | +4.8%       | Requires correctness signal                  |

**Limitation — Non-monotonic improvement:**

Per the paper: "For tasks with multi-aspect feedback like Acronym Generation,
the output quality can fluctuate during the iterative process, improving on one
aspect while losing out on another."

**Mitigation:** Track scores across iterations; select the output with maximum
total score, not necessarily the final output.

---

### Feedback Prompt Design

The feedback prompt determines refinement quality. Key elements from Self-Refine
experiments:

**Structure:**

```
You are given [task description] and an output.

Output: {previous_output}

Provide feedback on this output. Your feedback should:
1. Identify specific phrases or elements that need improvement
2. Explain why they are problematic
3. Suggest concrete actions to fix them

Do not rewrite the output. Only provide feedback.

Feedback:
```

**Why separation matters:** Combining feedback and rewriting in one turn
degrades both. The model either produces shallow feedback to get to rewriting,
or rewrites without fully analyzing problems.

**Non-obvious insight:** Self-Refine improvement is non-monotonic—output can
improve on one dimension while regressing on another. Track scores across all
iterations and select the maximum-score output, not necessarily the final one.

---

### Refinement Prompt Design

The refinement prompt applies feedback to produce improved output.

**Structure:**

```
You are given [task description], a previous output, and feedback on that output.

Previous output: {previous_output}

Feedback: {feedback}

Using this feedback, produce an improved version of the output.
Address each point raised in the feedback.

Improved output:
```

**With history (for iteration 2+):**

```
You are given [task description], your previous attempts, and feedback on each.

Attempt 1: {y₀}
Feedback 1: {fb₀}

Attempt 2: {y₁}
Feedback 2: {fb₁}

Using all feedback, produce an improved version. Do not repeat previous mistakes.

Improved output:
```

---

### Stopping Conditions

Self-Refine requires explicit stopping conditions. Options:

1. **Fixed iterations:** Stop after N refinement cycles (typically 2-4)
2. **Feedback-based:** Prompt the model to include a stop signal in feedback
3. **Score-based:** Stop when quality score exceeds threshold
4. **Diminishing returns:** Stop when improvement between iterations falls below
   threshold

**Prompt for feedback-based stopping:**

```
Provide feedback on this output. If the output is satisfactory and needs no
further improvement, respond with "NO_REFINEMENT_NEEDED" instead of feedback.

Feedback:
```

**Warning:** Models often fail to self-terminate appropriately. Per Madaan et
al.: fixed iteration limits are more reliable than self-assessed stopping.

---

## 3. Verification

Techniques where the model fact-checks its own outputs through targeted
questioning or external tools.

### Chain-of-Verification (CoVe)

A structured approach to reducing hallucination through self-verification. Per
Dhuliawala et al. (2023): "Chain-of-Verification (CoVe) whereby the model first
(i) drafts an initial response; then (ii) plans verification questions to
fact-check its draft; (iii) answers those questions independently so the answers
are not biased by other responses; and (iv) generates its final verified
response."

**The four-step process:**

```
Turn 1 (Baseline Response):
  Input: Original query
  Output: Initial response (may contain hallucinations)

Turn 2 (Plan Verifications):
  Input: Query + baseline response
  Output: List of verification questions

Turn 3 (Execute Verifications):
  Input: Verification questions ONLY (not baseline response)
  Output: Answers to each verification question

Turn 4 (Final Verified Response):
  Input: Query + baseline response + verification Q&A pairs
  Output: Revised response incorporating verifications
```

**The critical insight — shortform beats longform:**

Per the paper: "Shortform verification questions are more accurately answered
than longform queries. In a longform response, LLMs are prone to generate a
number of hallucinations. However, it can often be the case that the LLM itself
would know these hallucinations are wrong if queried specifically for that
individual fact, independent of the rest of the longform generation."

**Quantitative evidence:**

| Setting                      | Accuracy |
| ---------------------------- | -------- |
| Facts in longform generation | ~17%     |
| Same facts as individual Q&A | ~70%     |

The same model that hallucinates facts in context can correctly answer when
asked directly. CoVe exploits this asymmetry.

**Non-obvious insight:** The 17%->70% improvement is not about model
capability—the same model knows the correct facts. The issue is _generation
mode_: longform generation encourages confabulation while direct Q&A encourages
factual recall. Changing the question format changes the retrieval behavior.

**Example from the paper:**

```
Query: Name some politicians who were born in NY, New York.

Baseline Response (with hallucinations):
1. Hillary Clinton - former secretary of state... [WRONG: born in Chicago]
2. Donald Trump - former president... [CORRECT: born in Queens, NYC]
3. Michael Bloomberg - former Mayor... [WRONG: born in Boston]

Verification Questions:
- Where was Hillary Clinton born?
- Where was Donald Trump born?
- Where was Michael Bloomberg born?

Verification Answers:
- Hillary Clinton was born in Chicago, Illinois
- Donald Trump was born in Queens, New York City
- Michael Bloomberg was born in Boston, Massachusetts

Final Verified Response:
1. Donald Trump - former president (born in Queens, NYC)
2. Alexandria Ocasio-Cortez - Democratic representative (born in NYC)
...
```

---

### Factored vs. Joint Verification

**The hallucination copying problem:**

Per Dhuliawala et al.: "Models that attend to existing hallucinations in the
context from their own generations tend to repeat the hallucinations."

When verification questions are answered with the baseline response in context,
the model tends to confirm its own hallucinations rather than correct them.

**Joint verification (less effective):**

```
Turn 3 (Joint):
  Input: Query + baseline response + verification questions
  Output: All answers in one pass

Problem: Model sees its original hallucinations and copies them
```

**Factored verification (more effective):**

```
Turn 3a: Answer Q1 independently (no baseline in context)
Turn 3b: Answer Q2 independently (no baseline in context)
Turn 3c: Answer Q3 independently (no baseline in context)
...
```

**2-Step verification (middle ground):**

```
Turn 3a: Generate all verification answers (no baseline in context)
Turn 3b: Cross-check answers against baseline, note inconsistencies
```

**Performance comparison (Wiki-Category task):**

| Method        | Precision |
| ------------- | --------- |
| Baseline      | 0.13      |
| Joint CoVe    | 0.15      |
| 2-Step CoVe   | 0.19      |
| Factored CoVe | 0.22      |

Factored verification consistently outperforms joint verification by preventing
hallucination propagation.

---

### Verification Question Design

**Open questions outperform yes/no:**

Per the paper: "We find that yes/no type questions perform worse for the
factored version of CoVe. Some anecdotal examples... find the model tends to
agree with facts in a yes/no question format whether they are right or wrong."

**CORRECT (open verification question):**

```
When did Texas secede from Mexico?
→ Expected answer: 1836
```

**INCORRECT (yes/no verification question):**

```
Did Texas secede from Mexico in 1845?
→ Model tends to agree regardless of correctness
```

**LLM-generated questions outperform heuristics:**

Per the paper: "We compare the quality of these questions to heuristically
constructed ones... Results show a reduced precision with rule-based
verification questions."

Let the model generate verification questions tailored to the specific response,
rather than using templated questions.

---

### Factor+Revise for Complex Verification

For longform generation, add an explicit cross-check step between verification
and final response.

**Structure:**

```
Turn 3 (Execute verifications): [as above]

Turn 3.5 (Cross-check):
  Input: Baseline response + verification Q&A pairs
  Output: Explicit list of inconsistencies found

Turn 4 (Final response):
  Input: Baseline + verifications + inconsistency list
  Output: Revised response
```

**Performance:** Factor+Revise achieves FACTSCORE 71.4 vs. 63.7 for
factored-only, demonstrating that explicit reasoning about inconsistencies
further improves accuracy.

**Prompt for cross-check:**

```
Original passage: {baseline_excerpt}

From another source:
Q: {verification_question_1}
A: {verification_answer_1}

Q: {verification_question_2}
A: {verification_answer_2}

Identify any inconsistencies between the original passage and the verified facts.
List each inconsistency explicitly.

Inconsistencies:
```

---

### CRITIC: Tool-Interactive Verification

A verification framework using external tools (search engines, code
interpreters, calculators) rather than relying solely on LLM knowledge. Per Gou
et al. (2024): "CRITIC allows LLMs to validate and progressively amend their own
outputs in a manner similar to human interactions with tools."

**The critical finding:**

Per the paper: "Exclusive reliance on self-correction without external feedback
may yield modest improvements or even deteriorate performance."

Without external tools, self-verification often fails. CRITIC provides the
external signal that makes verification effective.

**The verify-then-correct loop:**

```
Turn 1 (Initial Generation):
  Input: Query
  Output: Initial response y₀

Turn 2 (Tool-Interactive Verification):
  Input: y₀ + verification prompt
  Action: Use tools (search, code interpreter, calculator) to verify claims
  Output: Verification results + critique cᵢ

Turn 3 (Correction):
  If verification passed: Return y₀
  If issues found:
    Input: Query + y₀ + critique cᵢ
    Output: Corrected response yᵢ₊₁

[Iterate until verification passes or limit reached]
```

**Tool selection by domain:**

| Domain          | Tool                | Verification Method                  |
| --------------- | ------------------- | ------------------------------------ |
| Factual QA      | Search engine       | Query for supporting evidence        |
| Math reasoning  | Python interpreter  | Execute calculation, compare results |
| Toxicity        | Toxicity classifier | Score output, flag issues            |
| Code generation | Code interpreter    | Execute, check for errors            |

**Performance with tools:**

| Task               | ChatGPT Baseline | ChatGPT + CRITIC | Improvement |
| ------------------ | ---------------- | ---------------- | ----------- |
| AmbigNQ (QA)       | 47.4 F1          | 55.1 F1          | +7.7        |
| GSM8K (Math)       | 81.0%            | 88.0%            | +7.0%       |
| Toxicity reduction | —                | —                | 79.2%       |

**Verification prompt template:**

```
Previous output: {y₀}

Verify the correctness of this output using available tools.
For each claim or calculation:
1. Identify what needs verification
2. Use appropriate tool to check
3. Report whether claim is supported or refuted

If issues are found, explain specifically what is wrong and how to fix it.

Verification:
```

**Critique-then-correct prompt:**

```
Original query: {query}

Your previous response: {y₀}

Verification found these issues:
{critique}

Generate a corrected response that addresses each issue identified.

Corrected response:
```

**Non-obvious insight:** CRITIC's improvement comes from the _external signal_,
not from additional reasoning passes. The same model doing self-verification
without tools may degrade performance (per Huang et al.). Tools provide ground
truth that breaks the self-confirmation loop.

**When CRITIC beats CoVe:**

Use CRITIC when claims are externally verifiable (factual lookups, calculations,
code execution). Use CoVe when verification requires the model's own knowledge
applied through careful questioning.

---

## 4. Aggregation and Consistency

Techniques that sample multiple responses and select or synthesize the best
output.

### Universal Self-Consistency (USC)

Extends self-consistency to free-form outputs where exact-match voting is
impossible. Per Chen et al. (2023): "USC leverages LLMs themselves to select the
most consistent answer among multiple candidates... USC eliminates the need of
designing an answer extraction process, and is applicable to tasks with
free-form answers."

**The two-step process:**

```
Turn 1 (Sample):
  Input: Query
  Output: N responses sampled with temperature > 0
  [y₁, y₂, ..., yₙ]

Turn 2 (Select):
  Input: Query + all N responses
  Output: Index of most consistent response
```

**The selection prompt:**

```
I have generated the following responses to the question: {question}

Response 0: {response_0}
Response 1: {response_1}
Response 2: {response_2}
...

Select the most consistent response based on majority consensus.
The most consistent response is Response:
```

**Why this works:**

Per the paper: "Although prior works show that LLMs sometimes have trouble
evaluating the prediction correctness, empirically we observe that LLMs are
generally able to examine the response consistency across multiple tasks."

Assessing consistency is easier than assessing correctness. The model doesn't
need to know the right answer—just which answers agree with each other most.

**Non-obvious insight:** USC works even when the model cannot reliably evaluate
correctness. Consistency assessment is a fundamentally easier task than
correctness assessment—it requires comparing outputs to each other rather than
to ground truth.

**Performance:**

| Task                   | Greedy | Random | USC  | Standard SC |
| ---------------------- | ------ | ------ | ---- | ----------- |
| GSM8K                  | 91.3   | 91.5   | 92.4 | 92.7        |
| MATH                   | 34.2   | 34.3   | 37.6 | 37.5        |
| TruthfulQA (free-form) | 62.1   | 62.9   | 67.7 | N/A         |
| SummScreen (free-form) | 30.6   | 30.2   | 31.7 | N/A         |

USC matches standard SC on structured tasks and enables consistency-based
selection where SC cannot apply.

**Robustness to ordering:**

Per the paper: "The overall model performance remains similar with different
response orders, suggesting the effect of response order is minimal." USC is not
significantly affected by the order in which responses are presented.

**Optimal sample count:**

USC benefits from more samples up to a point, then plateaus or slightly degrades
due to context length limitations. Per experiments: 8 samples is a reliable
sweet spot balancing accuracy and cost.

---

### Multi-Chain Reasoning (MCR)

Uses multiple reasoning chains as evidence sources, not just answer votes. Per
Yoran et al. (2023): "Unlike prior work, sampled reasoning chains are used not
for their predictions (as in SC) but as a means to collect pieces of evidence
from multiple chains."

**The key insight:**

Self-Consistency discards the reasoning and only votes on answers. MCR preserves
the reasoning and synthesizes facts across chains.

**The three-step process:**

```
Turn 1 (Generate chains):
  Input: Query
  Output: N reasoning chains, each with intermediate steps
  [chain₁, chain₂, ..., chainₙ]

Turn 2 (Concatenate):
  Combine all chains into unified multi-chain context

Turn 3 (Meta-reason):
  Input: Query + multi-chain context
  Output: Final answer + explanation synthesizing evidence
```

**Why MCR outperforms SC:**

Per the paper: "SC solely relies on the chains' answers... By contrast, MCR
concatenates the intermediate steps from each chain into a unified context,
which is passed, along with the original question, to a meta-reasoner model."

**Example from the paper:**

```
Question: Did Brad Peyton need to know about seismology?

Chain 1 (Answer: No):
- Brad Peyton is a film director
- What is seismology? Seismology is the study of earthquakes
- Do film directors need to know about earthquakes? No

Chain 2 (Answer: Yes):
- Brad Peyton directed San Andreas
- San Andreas is about a massive earthquake
- [implicit: he needed to research the topic]

Chain 3 (Answer: No):
- Brad Peyton is a director, writer, and producer
- What do film directors have to know? Many things
- Is seismology one of them? No

Self-Consistency vote: No (2-1)

MCR meta-reasoning: Combines facts from all chains:
- Brad Peyton is a film director (chain 1, 3)
- He directed San Andreas (chain 2)
- San Andreas is about a massive earthquake (chain 2)
- Seismology is the study of earthquakes (chain 1)

MCR answer: Yes (synthesizes that directing an earthquake film required seismology knowledge)
```

**Performance:**

MCR outperforms SC by up to 5.7% on multi-hop QA datasets. Additionally: "MCR
generates high quality explanations for over 82% of examples, while fewer than
3% are unhelpful."

---

### Complexity-Weighted Voting

An extension to self-consistency that weights votes by reasoning complexity. Per
Fu et al. (2023): "We propose complexity-based consistency, where instead of
taking a majority vote among all generated chains, we vote over the top K
complex chains."

**The process:**

```
Turn 1 (Sample with CoT):
  Generate N reasoning chains with answers

Turn 2 (Rank by complexity):
  Count reasoning steps in each chain
  Select top K chains by step count

Turn 3 (Vote):
  Majority vote only among the K complex chains
```

**Why complexity matters:**

Simple chains may reflect shortcuts or lucky guesses. Complex chains demonstrate
thorough reasoning. Voting only over complex chains filters out low-effort
responses.

**Performance (GSM8K):**

| Method                      | Accuracy |
| --------------------------- | -------- |
| Standard SC (all chains)    | 78.0     |
| Complexity-weighted (top K) | 80.5     |

**Implementation note:** This requires no additional LLM calls beyond standard
SC—just post-processing to count steps and filter before voting.

---

### Multi-Expert Prompting

Simulates multiple domain experts within a single LLM, aggregating their
perspectives using a structured framework. Per Long et al. (2024): "Multi-expert
Prompting distinguishes itself by aggregating expert responses in a single turn
without iterative refinement. Hence, Multi-expert Prompting instructs an LLM to
fulfill all steps within a single inference."

**The key insight:**

Rather than emergent LLM coordination (as in debate approaches), Multi-Expert
uses a human-designed aggregation framework—the Nominal Group Technique (NGT)—to
systematically combine perspectives.

**The seven-subtask aggregation:**

```
Step 1: Generate n expert identities relevant to the task
        Each expert provides independent response

Step 2: Aggregate using NGT framework:
   Subtask 1: Identify agreed viewpoints (>50% expert consensus)
   Subtask 2: Identify conflicted viewpoints
   Subtask 3: Resolve conflicts via majority voting
   Subtask 4: Identify isolated viewpoints (unique perspectives)
   Subtask 5: Collect outputs from subtasks 1, 3, 4
   Subtask 6: Generate aggregated response from collected viewpoints
   Subtask 7: Select best among individual expert + aggregated responses
```

**Performance comparison:**

| Method          | TruthfulQA (ChatGPT) |
| --------------- | -------------------- |
| Zero-shot       | 68.05%               |
| Self-refine     | 75.89%               |
| USC             | 77.11%               |
| ExpertPrompting | 80.66%               |
| Multi-expert    | **89.35%**           |

**The aggregation prompt:**

```
Generate {n} expert identities relevant to this question, then have each
expert provide their response independently.

Question: {question}

After generating expert responses, aggregate them as follows:
1. List viewpoints where >50% of experts agree
2. List viewpoints where experts conflict
3. For conflicts, use majority voting to resolve
4. List any unique perspectives from individual experts
5. Combine agreed, resolved, and unique viewpoints
6. Generate a final aggregated response
7. Select the best response among individual experts and the aggregation

Experts and responses:
```

**When to use Multi-Expert vs. USC:**

Use Multi-Expert for open-ended tasks with multiple valid perspectives
(opinions, recommendations, creative tasks). Use USC for tasks with objective
answers where consistency signals correctness.

---

## 5. Advanced Meta-Reasoning

### Cumulative Reasoning (CR)

A multi-role framework that builds a directed acyclic graph (DAG) of validated
reasoning steps. Per Zhang et al. (2024): "CR orchestrates three distinct roles:
Proposer, Verifier(s), and Reporter... CR dynamically constructs a DAG of all
historically validated reasoning steps, enabling new propositions to be derived
from any combination of previously verified nodes."

**Distinction from Tree of Thoughts:**

Per the paper: "ToT explores individual solution paths without systematically
integrating verified knowledge across different branches. In contrast, CR
dynamically constructs a DAG of all historically validated reasoning steps... CR
leverages the comprehensive, interconnected context of verified information...
reducing redundancy and ensuring that the final answer is supported by the most
robust and well-substantiated reasoning."

**The three roles:**

```
PROPOSER:
  - Generates candidate reasoning steps based on current context
  - Can derive new propositions from any combination of validated nodes
  - Produces atomic, verifiable claims

VERIFIER:
  - Critically assesses proposer's suggestions
  - Can be LLM-based (self-critique) or external tool (Python interpreter, theorem prover)
  - Returns: valid/invalid + reasoning

REPORTER:
  - Monitors the evolving DAG state
  - Determines when sufficient information accumulated to conclude
  - Synthesizes final answer from validated reasoning graph
```

**The coordination loop:**

```
Initialize:
  DAG = {original_question}
  context = [original_question]

Loop:
  Turn N (Propose):
    Input: Current DAG context
    Output: Candidate reasoning step pᵢ

  Turn N+1 (Verify):
    Input: Candidate step pᵢ + relevant DAG nodes
    Action: Validate using LLM reasoning or external tool
    Output: Valid/Invalid + justification

  If Valid:
    Add pᵢ to DAG
    Update context with new validated node

  Turn N+2 (Report):
    Input: Current DAG state
    Output: "Continue" or "Conclude with answer: X"

Until Reporter concludes or iteration limit
```

**Performance:**

| Task         | CoT-SC | ToT | CR            |
| ------------ | ------ | --- | ------------- |
| Game of 24   | 9%     | 74% | **98%**       |
| MATH Level 5 | —      | —   | +43% relative |

**Verifier implementation options:**

Per the paper: "The Verifier's conceptual role is to ensure logical soundness.
In practice, this can be implemented by another LLM instance (acting as a
self-critique mechanism) or, ideally, by more formal methods such as symbolic
reasoning systems (e.g., a theorem prover) or an integrated code environment
(e.g., a Python interpreter for mathematical or arithmetical validation)."

External verifiers (code interpreters, calculators) provide higher reliability
than LLM-based verification for domains with formal correctness criteria.

**Proposer prompt:**

```
You are generating the next reasoning step for this problem.

Problem: {original_question}

Validated reasoning so far:
{dag_nodes_formatted}

Generate ONE atomic proposition that advances the reasoning.
The proposition should be:
- Derivable from the validated nodes above
- Specific and verifiable
- A single logical step (not multiple steps combined)

Next proposition:
```

**Verifier prompt (LLM-based):**

```
Evaluate whether this proposition is logically valid.

Proposition: {candidate_step}

Supporting context:
{relevant_dag_nodes}

Is this proposition valid? Explain your reasoning, then conclude with
either "VALID" or "INVALID".

Evaluation:
```

**Reporter prompt:**

```
Review the current state of reasoning.

Problem: {original_question}

Validated propositions:
{all_dag_nodes}

Is there sufficient validated information to conclusively answer the problem?

If YES: State "CONCLUDE" followed by the final answer derived from the propositions.
If NO: State "CONTINUE" and briefly note what additional reasoning is needed.

Decision:
```

**When to use CR:**

CR is most effective for complex formal reasoning (mathematics, logic puzzles,
multi-step deductions) where each step can be validated and the problem benefits
from non-linear exploration. The overhead of DAG management makes it less
suitable for simple queries or creative tasks.

---

## 6. Implementation Patterns

### Conversation Structure Template

A general template for multi-turn improvement:

```
SYSTEM: [Base system prompt with single-turn techniques]

--- Turn 1: Initial Generation ---
USER: [Task]
ASSISTANT: [Initial output y₀]

--- Turn 2: Analysis/Feedback ---
USER: [Analysis prompt - critique, verify, or evaluate y₀]
ASSISTANT: [Feedback, verification results, or evaluation]

--- Turn 3: Refinement/Synthesis ---
USER: [Refinement prompt incorporating Turn 2 output]
ASSISTANT: [Improved output y₁]

[Repeat Turns 2-3 as needed]

--- Final Turn: Format/Extract ---
USER: [Optional: extract final answer in required format]
ASSISTANT: [Final formatted output]
```

### Context Management

Multi-turn prompting accumulates context. Manage token limits by:

1. **Summarize history:** After N iterations, summarize previous attempts rather
   than including full text
2. **Keep recent + best:** Retain only the most recent iteration and the
   best-scoring previous output
3. **Structured extraction:** Extract key points from feedback rather than full
   feedback text

**Example (summarized history):**

```
Previous attempts summary:
- Attempt 1: Failed due to [specific issue]
- Attempt 2: Improved [aspect] but [remaining issue]
- Attempt 3: Best so far, minor issue with [aspect]

Latest attempt: [full text of y₃]

Feedback on latest attempt:
```

---

## 7. Anti-Patterns

### The Intrinsic Self-Correction Fallacy

**Anti-pattern:** Asking the model to "review and improve" without external
signals.

Per Huang et al. (2024): "Without external feedback, self-correction not only
fails to improve LLMs' performance on reasoning tasks but can even exacerbate
reasoning errors."

```
# PROBLEMATIC
Turn 1: Solve this problem
Turn 2: Review your answer and fix any errors
```

The model either keeps the original answer (74.7% of cases) or changes correct
answers to incorrect ones.

```
# BETTER
Turn 1: Solve this problem
Turn 2: [Use CoVe to generate verification questions]
Turn 3: [Answer verifications in isolated context]
Turn 4: Revise based on verification findings
```

Always provide external feedback: isolated verification, tool results, or
multi-sample comparison.

### The Mixed-Goal Turn

**Anti-pattern:** Combining distinct cognitive operations in a single turn.

```
# PROBLEMATIC
Generate a response, then critique it, then improve it.
```

Each operation deserves focused attention. The model may rush through critique
to reach improvement, or improve without thorough analysis.

```
# BETTER
Turn 1: Generate response
Turn 2: Critique the response (output: feedback only)
Turn 3: Improve based on feedback
```

### The Contaminated Context

**Anti-pattern:** Including the original response when answering verification
questions.

Per Dhuliawala et al. (2023): "Models that attend to existing hallucinations in
the context from their own generations tend to repeat the hallucinations."

```
# PROBLEMATIC
Original response: [contains potential hallucinations]
Verification question: Where was Hillary Clinton born?
Answer:
```

The model will often confirm the hallucination from its original response.

```
# BETTER
Verification question: Where was Hillary Clinton born?
Answer:
[Original response NOT in context]
```

Exclude the baseline response when executing verifications. Include it only in
the final revision step.

### The Yes/No Verification Trap

**Anti-pattern:** Phrasing verification questions as yes/no confirmations.

```
# PROBLEMATIC
Is it true that Michael Bloomberg was born in New York?
```

Per CoVe research: Models tend to agree with yes/no questions regardless of
correctness.

```
# BETTER
Where was Michael Bloomberg born?
```

Open questions expecting factual answers perform significantly better.

### The Infinite Loop

**Anti-pattern:** No explicit stopping condition for iterative refinement.

```
# PROBLEMATIC
Keep improving until the output is perfect.
```

Models rarely self-terminate appropriately. "Perfect" is undefined.

```
# BETTER
Improve for exactly 3 iterations, then output the best version.

# OR
Improve until the quality score exceeds 8/10, maximum 5 iterations.
```

Always include explicit stopping criteria: iteration limits, quality thresholds,
or both.

### The Forgotten History

**Anti-pattern:** Discarding previous iterations in refinement.

```
# PROBLEMATIC
Turn 3: Here is feedback. Improve the output.
[No reference to previous attempts]
```

Per Madaan et al.: "Retaining the history of previous feedback and outputs...
allows the model to learn from past mistakes and avoid repeating them."

```
# BETTER
Turn 3:
Previous attempts and feedback:
- Attempt 1: [y₀] → Feedback: [fb₀]
- Attempt 2: [y₁] → Feedback: [fb₁]

Improve, avoiding previously identified issues:
```

### The Vague Feedback

**Anti-pattern:** Feedback without actionable specifics.

```
# PROBLEMATIC
The response could be improved. Some parts are unclear.
```

This feedback provides no guidance for refinement.

```
# BETTER
The explanation of photosynthesis in paragraph 2 uses jargon ("electron
transport chain") without definition. Add a brief explanation: "the process
by which plants convert light energy into chemical energy through a series
of protein complexes."
```

Feedback must identify specific elements AND suggest concrete improvements.

### The Majority Fallacy

**Anti-pattern:** Assuming majority vote is always correct.

```
# PROBLEMATIC
3 out of 5 chains say the answer is X, so X is correct.
```

Per Fu et al.: Simple chains may reflect shortcuts. Per Yoran et al.:
Intermediate reasoning contains useful information discarded by voting.

```
# BETTER
Weight votes by reasoning complexity, or use MCR to synthesize
evidence from all chains including minority answers.
```

---

## 8. Technique Combinations

Multi-turn techniques can be combined for compounding benefits. The combinations
below are **illustrative, not exhaustive**—they demonstrate useful pairings
discovered in practice, but many other valid combinations exist. When designing
pipelines, consider which techniques address orthogonal concerns (e.g., S2A
filters input while CoVe validates output) versus which address the same concern
through different mechanisms (e.g., CoVe and CRITIC both verify, but via
different methods).

### S2A + Any Downstream Technique

Filter context before applying any other technique:

```
Turn 0: Filter input context (S2A)
Turn 1+: Apply Self-Refine, CoVe, or any other technique to filtered context
```

S2A is orthogonal to all other techniques—it improves input quality, while
others improve output quality.

### Self-Refine + CoVe

Apply verification after refinement to catch introduced errors:

```
Turn 1: Generate initial output
Turn 2: Feedback
Turn 3: Refine
Turn 4: Plan verification questions for refined output
Turn 5: Execute verifications (factored)
Turn 6: Final verified output
```

### Self-Refine + CRITIC

Use tools to verify refinement effectiveness:

```
Turn 1: Generate initial output
Turn 2: Feedback (identify issues)
Turn 3: Refine based on feedback
Turn 4: Tool-interactive verification of refined output
Turn 5: If issues found, critique and correct; else return
```

CRITIC provides external validation that refinement actually improved the
output.

### CoVe + CRITIC

Combine question-based and tool-based verification:

```
Turn 1: Generate baseline response
Turn 2: Plan verification questions
Turn 3: Answer verifications (factored, no baseline)
Turn 4: Use tools to verify answers where applicable (calculations, lookups)
Turn 5: Cross-check and generate final response
```

Use CoVe for claims requiring model knowledge; use CRITIC tools for externally
verifiable claims.

### USC + Complexity Weighting

Filter by complexity before consistency selection:

```
Turn 1: Sample N responses with reasoning
Turn 2: Filter to top K by reasoning complexity
Turn 3: Apply USC to select most consistent among K
```

### USC + Multi-Expert Prompting

Combine for open-ended tasks:

```
Turn 1: Generate multi-expert responses (n experts per sample)
Turn 2: Sample M such multi-expert outputs
Turn 3: Apply USC to select most consistent aggregated response
```

### MCR + Self-Refine

Use multi-chain evidence collection, then refine the synthesis:

```
Turn 1: Generate N reasoning chains
Turn 2: Meta-reason to synthesize evidence and produce answer
Turn 3: Feedback on synthesis
Turn 4: Refine synthesis
```

### CR + External Verifier

Replace LLM verifier with tool-based verification:

```
Proposer: Generate candidate step
Verifier: Execute step in Python interpreter / query theorem prover
Reporter: Assess DAG completeness

[External verification provides stronger guarantees than LLM self-critique]
```

### S2A + Multi-Expert + CoVe (Full Pipeline)

For high-stakes tasks requiring maximum accuracy:

```
Turn 0: S2A filter input context
Turn 1: Multi-expert generation (n experts)
Turn 2: NGT aggregation
Turn 3: Plan verification questions for aggregated response
Turn 4: Execute verifications (factored)
Turn 5: Final verified response
```

This pipeline: removes distractors → gathers diverse perspectives → validates
facts.

---

## Research Citations

- Chen, X., Aksitov, R., Alon, U., et al. (2023). "Universal Self-Consistency
  for Large Language Model Generation." arXiv.
- Dhuliawala, S., Komeili, M., Xu, J., et al. (2023). "Chain-of-Verification
  Reduces Hallucination in Large Language Models." arXiv.
- Diao, S., Wang, P., Lin, Y., & Zhang, T. (2023). "Active Prompting with
  Chain-of-Thought for Large Language Models." arXiv.
- Fu, Y., Peng, H., Sabharwal, A., Clark, P., & Khot, T. (2023).
  "Complexity-Based Prompting for Multi-Step Reasoning." arXiv.
- Gou, Z., Shao, Z., Gong, Y., et al. (2024). "CRITIC: Large Language Models Can
  Self-Correct with Tool-Interactive Critiquing." arXiv.
- Huang, J., Chen, X., Mishra, S., et al. (2024). "Large Language Models Cannot
  Self-Correct Reasoning Yet." arXiv.
- Long, D.X., et al. (2024). "Multi-expert Prompting Improves Reliability,
  Safety and Usefulness of Large Language Models." arXiv.
- Madaan, A., Tandon, N., Gupta, P., et al. (2023). "Self-Refine: Iterative
  Refinement with Self-Feedback." arXiv.
- Wang, X., Wei, J., Schuurmans, D., et al. (2023). "Self-Consistency Improves
  Chain of Thought Reasoning in Language Models." ICLR.
- Weston, J. & Sukhbaatar, S. (2023). "System 2 Attention (Is Something You
  Might Need Too)." arXiv.
- Yao, S., Yu, D., Zhao, J., et al. (2023). "Tree of Thoughts: Deliberate
  Problem Solving with Large Language Models." NeurIPS.
- Yoran, O., Wolfson, T., Bogin, B., et al. (2023). "Answering Questions by
  Meta-Reasoning over Multiple Chains of Thought." arXiv.
- Zhang, Y., Du, J., Ma, S., et al. (2024). "Cumulative Reasoning with Large
  Language Models." TMLR.
- Zhang, Y., Yuan, Y., & Yao, A. (2024). "Meta Prompting for AI Systems." arXiv.
