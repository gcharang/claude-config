# Prompt Engineering: Research-Backed Techniques for Multi-Turn Prompts

This document synthesizes practical prompt engineering patterns with academic
research on iterative LLM reasoning. All techniques target **multi-turn
prompts**--structured sequences where output from one turn becomes input to
subsequent turns.

**Meta-principle**: Multi-turn value comes from separation of concerns--each
turn has a distinct cognitive goal (generate, critique, verify, synthesize).
Mixing goals within a single turn reduces effectiveness.

**Prerequisite**: Assumes familiarity with single-turn techniques (CoT,
Plan-and-Solve, RE2). Multi-turn techniques extend single-turn methods across
message boundaries.

**Notation**: Throughout this document, `T1`, `T2`, `T3` denote Turn 1, Turn 2,
Turn 3--sequential LLM calls in a multi-turn conversation.

---

## Technique Selection Guide

| Domain             | Technique              | Trigger Condition                           | Stacks With               | Conflicts With       | Cost/Tradeoff                     | Effect                                          |
| ------------------ | ---------------------- | ------------------------------------------- | ------------------------- | -------------------- | --------------------------------- | ----------------------------------------------- |
| **Pre-Processing** | S2A Context Filtering  | Input contains irrelevant/misleading noise  | Any downstream technique  | --                   | 2x tokens (filter + generate)     | QA +17.5pp; math +12pp                          |
| **Pre-Processing** | Step-Back Abstraction  | Task has low-level details; need principles | S2A, CoT                  | Direct answering     | 1 abstraction turn                | MMLU Physics +7%; Chemistry +11%; TimeQA +27%   |
| **Pre-Processing** | Generated Knowledge    | Commonsense reasoning; implicit knowledge   | Any downstream technique  | --                   | 1 generation turn + M samples     | NumerSense, CSQA, QASC SOTA                     |
| **Refinement**     | Self-Refine            | Output quality improvable via iteration     | Any single-turn reasoning | Time-critical tasks  | 2-4x tokens per iteration         | 5-40% absolute improvement across 7 task types  |
| **Refinement**     | Progressive-Hint (PHP) | Math reasoning; previous answer as hint     | CoT, Self-Consistency     | --                   | 2+ iterations until convergence   | GSM8K 95.5%; SVAMP 91.9%; MATH 53.9%            |
| **Refinement**     | Think Twice            | Complex math/code; cognitive inertia        | Any reasoning technique   | Single-pass          | 2-4 rounds; answer-only context   | AIME +2.8pp (80.3%→83.1%); GPQA +2.2pp          |
| **Refinement**     | Iteration of Thought   | Response improvable via inner dialogue      | Any single-turn reasoning | Static prompts       | 2-5 iterations; IDA overhead      | HotpotQA +35% F1; Game of 24 +15% over CoT      |
| **Verification**   | CoVe (Question-Based)  | Factual accuracy critical                   | Quote Extraction, CRITIC  | Joint verification   | 3-4x tokens                       | List QA: 17%->70%; FACTSCORE +15pp              |
| **Verification**   | Factored Verification  | Summary verification against source         | CoVe                      | Joint CoVe           | Claims x calls                    | HaluEval: 76.2% (+10pp); 45% hallucination cut  |
| **Verification**   | CRITIC (Tool-Based)    | Verifiable via search/code/calculator       | CoVe, Self-Refine         | Intrinsic correction | Tool API + 2-3x tokens            | AmbigNQ +7.7 EM; GSM8K +7.0%; 79% toxicity cut  |
| **Verification**   | Self-Explanation       | Dialogue tasks; context understanding       | Any dialogue technique    | --                   | 1 explanation turn                | +6pp JGA on dialogue state tracking             |
| **Meta-Reasoning** | Cumulative Reasoning   | Complex reasoning; validated steps needed   | External verifiers        | Linear CoT           | 3+ roles/step; DAG management     | Game of 24: 98% vs 74% ToT; MATH L5 +43%        |
| **Meta-Reasoning** | Selection-Inference    | Multi-step logical reasoning needed         | External verifiers        | Single-pass CoT      | 2 modules per step (select+infer) | 3x performance vs vanilla; interpretable traces |
| **Decomposition**  | Least-to-Most          | Problem harder than examples; easy-to-hard  | CoT, Self-Consistency     | --                   | 2-stage: decompose + solve        | DROP +8pp over CoT; GSM8K 5+ steps +6pp         |
| **Decomposition**  | Decomposed Prompting   | Task needs specialized sub-handlers         | Any verification          | Monolithic prompts   | Handler setup overhead            | Enables tasks CoT cannot learn from few-shot    |
| **Decomposition**  | ADAPT                  | Task complexity unknown; may fail           | Self-Refine, CRITIC       | Fixed decomposition  | Recursive calls on failure        | ALFWorld +28%; WebShop +27%; TextCraft +33%     |
| **Decomposition**  | Look Before You Leap   | Math problem requires clarification first   | CoT, Decomposed Prompting | Direct solving       | 1 elaboration turn                | +5.38% math; +4.99% geometry                    |
| **Decomposition**  | Successive Prompting   | Multi-hop QA; sequential dependencies       | Decomposed Prompting      | Monolithic prompts   | N decomposition steps             | Multi-hop QA; 30.6% F1 DROP; +4.3% over CoT     |

---

## Quick Reference: Key Principles

1. **External Signals for Self-Correction** -- Intrinsic correction fails (74.7%
   keep wrong); use verification Qs, tools, or multi-sample
2. **Self-Refine for Iteration** -- 5-40% improvement when feedback is
   actionable and specific
3. **Progressive-Hint for Math** -- Previous answer as hint until convergence;
   GSM8K 95.5%, SVAMP 91.9%
4. **Think Twice for Cognitive Inertia** -- Re-prompt with prior answer to break
   entrenched errors; AIME +2.8pp
5. **Iteration of Thought (IoT)** -- Inner dialogue agent generates thought-
   provoking prompts; HotpotQA +35% F1
6. **Separate Feedback from Refinement** -- Generate feedback in one turn, apply
   in another; mixing degrades both
7. **Factored over Joint Verification** -- Answer verification Qs without
   baseline in context; +3-8pp
8. **Shortform over Longform** -- 70% accuracy on individual Qs vs 17% for same
   facts in longform
9. **Open Questions over Yes/No** -- Models agree with yes/no regardless of
   correctness; open forces recall
10. **Claim Decomposition for Summaries** -- Decompose, verify each against
    source; 76.2% vs 61.2% single-prompt
11. **Tool-Interactive Verification** -- CRITIC: +7.7 EM on QA, +7.0% math via
    external validation
12. **Filter Context Before Reasoning** -- S2A: +17.5pp by removing noise before
    main task
13. **History Accumulation** -- Retain previous feedback; models learn from past
    mistakes
14. **Explicit Stopping Conditions** -- Use limits or thresholds; models rarely
    self-terminate well
15. **Track Best-So-Far** -- Quality may regress; select max-score output, not
    final
16. **Decompose Only on Failure** -- ADAPT's recursive approach: +28% over fixed
    plans
17. **Look Before You Leap** -- Elaborate problem before solving; +5.38% math
18. **Exclusive Context Filtering** -- S2A T2 uses ONLY filtered context;
    including original defeats purpose
19. **LLM-Generated Verification Qs** -- Outperform heuristic/template; tailored
    to response
20. **Factor+Revise for Complex** -- Explicit cross-check between verification
    and final: +7.7pp
21. **Actionable Feedback** -- "Use n(n+1)/2 instead of loop" beats "could be
    more efficient"
22. **DAG over Linear** -- Cumulative Reasoning: propositions combine any prior
    validated nodes
23. **Self-Generated Success Heuristic** -- ADAPT uses executor LLM to determine
    completion
24. **Step-Back for Abstraction** -- Extract principles/concepts first; MMLU
    Physics +7%, TimeQA +27%
25. **Generated Knowledge First** -- T1 generate relevant knowledge, T2 reason
    with it; commonsense SOTA
26. **Least-to-Most for Easy-to-Hard** -- Decompose then solve sequentially;
    generalizes beyond example complexity
27. **Selection-Inference for Logic** -- Alternate select facts + infer new;
    3x performance, causal traces
28. **Self-Explanation for Dialogue** -- Explain each turn before task; +6pp
    joint goal accuracy

---

## 1. Context Filtering

### S2A: Pre-Processing Filter

Regenerates input to remove distractors before main task. Per Weston &
Sukhbaatar (2023): "S2A leverages LLMs to reason about what to attend to."

**Process:**

```
T1 (Filter):  original_context -> filtered_context x'
T2 (Execute): x' + task -> response  [original EXCLUDED]
```

**Filter prompt:**

```
Extract the part that is related and useful for an accurate answer.
Include the actual question. Exclude opinions and irrelevant details.

{original_context}

Extracted relevant parts:
```

**Performance:**

| Task                  | Baseline | S2A   | Delta   |
| --------------------- | -------- | ----- | ------- |
| QA with opinions      | 62.8%    | 80.3% | +17.5pp |
| Math with distractors | ~65%     | ~77%  | +12pp   |

**Critical:** Attention must be "hard not soft" (Weston & Sukhbaatar). Including
both original AND filtered context defeats the purpose--model still attends to
problematic parts.

WRONG: `T2: Use original + x' for task` RIGHT: `T2: Use ONLY x' for task`

**Stacking:** Orthogonal to all downstream techniques. Chain: S2A -> Generate ->
Verify.

### Step-Back Prompting: Abstraction Before Detail

Extracts high-level principles or concepts before reasoning on specific details.
Per Zheng et al. (2024): "Step-Back Prompting grounds reasoning on abstractions
to reduce errors in intermediate reasoning steps."

**Process:**

```
T1 (Abstract):  question -> high-level concept/principle
T2 (Reason):    question + principles -> answer
```

**Abstraction prompt (STEM):**

```
You are an expert at Physics. Your task is to extract the physics concepts
and principles involved in solving this problem.

{question}

Principles Involved:
```

**Why it works:** Questions often contain many low-level details that cause
reasoning errors. Abstracting first retrieves relevant principles (Ideal Gas
Law, Doppler Effect) that guide correct reasoning paths.

**Performance:**

| Task           | Baseline | +Step-Back | Delta |
| -------------- | -------- | ---------- | ----- |
| MMLU Physics   | 66.4%    | 73.4%      | +7pp  |
| MMLU Chemistry | 70.9%    | 81.9%      | +11pp |
| TimeQA         | 41.5%    | 68.7%      | +27pp |

**Key insight:** Zheng et al.: "Abstraction skills are easy to demonstrate;
reasoning remains the bottleneck." One exemplar suffices for the abstraction
step.

WRONG: `Solve this physics problem directly` RIGHT: `First: What principles
apply? Then: Solve using those principles`

### Generated Knowledge Prompting: Elicit Then Reason

Generates relevant knowledge statements before answering. Per Liu et al. (2022):
"We can generate useful knowledge from a language model, then provide it as
input prompt concatenated with the question."

**Process:**

```
T1 (Generate):  question -> [k_1, k_2, ..., k_M] knowledge statements
T2 (Reason):    question + selected_knowledge -> answer
```

**Generation prompt:**

```
Generate some knowledge about the concepts in the question. The knowledge
should be helpful for answering the question.

Question: {question}

Knowledge:
```

**Selection:** Generate M knowledge statements, then select best by scoring each
(question + k_m) with the inference model.

**Performance:** State-of-the-art on NumerSense (numerical commonsense), CSQA
(general commonsense), and QASC (scientific commonsense).

**Why it works:** Liu et al.: "Generated knowledge transforms commonsense
reasoning into explicit reasoning procedures--deduction, induction, analogy."
The LLM surfaces its implicit knowledge explicitly.

WRONG: `Answer directly from implicit knowledge` RIGHT: `First generate
relevant facts, then reason with those facts explicitly`

**Stacking:** Combines with any downstream technique. Generated knowledge feeds
into S2A, CoT, or verification workflows.

---

## 2. Iterative Refinement

### Self-Refine: Feedback-Then-Improve Loop

General-purpose iterative improvement alternating FEEDBACK and REFINE turns. Per
Madaan et al. (2023): "These steps work in tandem to generate high-quality
outputs."

**Process:**

```
T1 (Generate): task -> y_0
T2 (Feedback): task + y_0 -> fb_0  [feedback ONLY, no rewrite]
T3 (Refine):   task + y_0 + fb_0 -> y_1
[Loop until stopping condition]
```

**Feedback quality requirements** (Madaan et al.):

- **Actionable**: Contains concrete action to improve output
- **Specific**: Identifies concrete phrases to change

WRONG: `"The code could be more efficient. Consider optimizing it."` RIGHT:
`"This uses a for loop (brute force). Use n(n+1)/2 instead."`

**History accumulation improves refinement:**

```
T_n (Refine): task + y_0 + fb_0 + y_1 + fb_1 + ... + fb_{n-1} -> y_n
```

Per Madaan et al.: "Retaining history allows the model to learn from past
mistakes."

**Performance:**

| Task Type              | Improvement |
| ---------------------- | ----------- |
| Code optimization      | +13%        |
| Dialogue response      | +35-40%     |
| Constrained generation | +20%        |

**Non-monotonic warning:** Quality can improve on one dimension while regressing
on another. Track scores across iterations; select max-score output, not final.

**Stopping conditions** (models rarely self-terminate well):

1. Fixed iterations (typically 2-4)
2. Score threshold
3. Feedback includes "NO_REFINEMENT_NEEDED"

WRONG: `"Iterate until perfect."` RIGHT:
`"Iterate 3 rounds, select best by score."`

**Feedback prompt:**

```
Output: {previous_output}

Provide feedback. Identify specific phrases needing improvement,
explain why they're problematic, suggest concrete fixes.
Do NOT rewrite. Only provide feedback.
```

**Refinement prompt:**

```
Previous attempts and feedback:
- Attempt 1: {y_0} -> Feedback: {fb_0}
- Attempt 2: {y_1} -> Feedback: {fb_1}

Produce improved version. Do not repeat previous mistakes.
```

### Progressive-Hint Prompting (PHP): Answer Convergence

Uses previous answers as hints until consecutive responses converge. Per Zheng
et al. (2023): "PHP follows a human-like thought process where previous answers
are leveraged as hints to arrive at the correct answer after re-evaluating the
question."

**Process:**

```
T1 (Base):    question + CoT -> answer_0
T2 (Hint 1):  question + "(Hint: The answer is near to {answer_0})"
              -> answer_1 [with hint acknowledgment]
T3 (Hint 2):  question + "(Hint: The answer is near to {answer_0}, {answer_1})"
              -> answer_2
...
Tn:           Stop when answer_n == answer_{n-1}
```

**The hint acknowledgment pattern:**

```
We know the Answer Hints: {previous_answers}.
With the Answer Hints: {previous_answers}, we will answer the question.
[Then proceed with reasoning]
```

**Performance (GPT-4 + Complex CoT):**

| Dataset | Baseline | +PHP  | Delta   |
| ------- | -------- | ----- | ------- |
| GSM8K   | 92.0%    | 95.5% | +3.5pp  |
| SVAMP   | 87.1%    | 91.9% | +4.8pp  |
| MATH    | 42.5%    | 53.9% | +11.4pp |

**Key insight:** Both correct and incorrect hints improve performance. Correct
hints confirm good reasoning paths; incorrect hints force the model to
reconsider and "jump out of" wrong answers.

**Stopping criterion:** Two consecutive identical answers signals convergence.
Stronger models/prompts converge faster (fewer iterations).

WRONG: `"Here's your previous answer: [58]. Try again."`
RIGHT: `"(Hint: The answer is near to 58). We know the Answer Hints: 58..."`

**Stacking:** Combines with Self-Consistency (PHP applied to best SC chain) for
additional gains. Works with any CoT variant as base prompt.

### Think Twice: Multi-Round Answer Re-Evaluation

Re-prompts with prior answer to break cognitive inertia. Per Tian et al.
(2025): "This approach parallels human cognitive processes, breaking cognitive
inertia and enabling the model to correct entrenched reasoning errors."

**Process:**

```
T1: question -> {thinking_1, answer_1}
T2: question + "The assistant's previous answer is: <answer>{answer_1}</answer>,
    and please re-answer." -> {thinking_2, answer_2}
T3: [repeat with answer_2]
...
Tn: Return answer_n after N rounds (typically 2-4)
```

**Critical design:** Intermediate reasoning traces are DISCARDED between rounds.
Only the final answer is passed. This forces independent reconsideration rather
than path-dependent refinement.

**Performance (QwQ-32B across rounds):**

| Benchmark     | R1    | R2    | R3    | R4    |
| ------------- | ----- | ----- | ----- | ----- |
| AIME 2024     | 80.3% | 82.1% | 82.8% | 83.1% |
| MATH-500      | 97.2% | 97.8% | 97.8% | 97.7% |
| GPQA-Diamond  | 65.9% | 67.2% | 67.5% | 68.1% |
| LiveCodeBench | 63.0% | 64.7% | 65.2% | 65.9% |

**Why it works:** Word frequency analysis shows R2 responses use fewer
hesitation markers ("but", "wait", "maybe") and become more decisive. In
Incorrect→Correct cases, "wait" usage increases—indicating deliberate
reconsideration before correction.

**Diminishing returns:** Improvement rate decreases after R2. R4 gains are
marginal. Optimal for most tasks: 2-3 rounds.

WRONG: `"Your answer of 13 was wrong. Try harder."`
RIGHT: `"The assistant's previous answer is: <answer>13</answer>, please re-answer."`

### Iteration of Thought (IoT): Inner Dialogue Agent

Uses a dedicated "Inner Dialogue Agent" (IDA) to generate context-sensitive
prompts that iteratively refine the LLM's response. Per Radha et al. (2024):
"IoT adapts its reasoning path dynamically, based on evolving context, without
generating alternate explorative thoughts which are ultimately discarded."

**Two variants:**

| Variant | Termination           | Best For          | Risk                  |
| ------- | --------------------- | ----------------- | --------------------- |
| AIoT    | LLM decides when done | Simple tasks      | Premature convergence |
| GIoT    | Fixed N iterations    | Complex reasoning | Redundant iterations  |

**Process (GIoT):**

```
T1: query + "Initial Prompt" -> response_0
For i = 1 to N-1:
    T_ida: IDA(query, response_{i-1}) -> thought_provoking_prompt_i
    T_i:   query + prompt_i -> response_i
T_final: IDA generates final prompt, LLM produces final_response
```

**IDA function:** Maps (query, previous_response) → new_prompt. The IDA
generates prompts that challenge, extend, or verify the current response—
functioning like an internal critic.

**Performance:**

| Task          | CoT    | IoT   | Delta  |
| ------------- | ------ | ----- | ------ |
| HotpotQA (F1) | ~50%   | ~85%  | +35pp  |
| HotpotQA (EM) | ~30%   | ~74%  | +44pp  |
| Game of 24    | 60%    | 75%   | +15pp  |
| GPQA          | varies | +5-8% | varies |

**Key insight:** GIoT outperforms AIoT on complex tasks because forced
iterations prevent premature conclusion. AIoT performs better on simpler tasks
where early termination is appropriate.

**Failure mode:** AIoT often "misjudges the completeness of its responses,
leading to premature convergence." Use GIoT for multi-step reasoning.

WRONG: `"Think more about your answer."`
RIGHT: IDA-generated: `"Your response addresses X but does not consider Y.
       What happens when Z is applied to your reasoning?"`

**Stacking:** IoT thought sequences can be used for fine-tuning. Combines with
any base reasoning technique (CoT, Complex CoT).

---

## 3. Verification Methods

Multi-turn verification addresses the constraint that LLMs cannot self-correct
without external signals. Per Huang et al. (2024): "Without external feedback,
self-correction fails to improve and can exacerbate errors."

Three approaches exist, each suited to different scenarios:

| Method   | External Signal     | When to Use              | Cost            |
| -------- | ------------------- | ------------------------ | --------------- |
| CoVe     | Isolated Q&A        | General factual claims   | 3-4x tokens     |
| Factored | Source documents    | Summaries with source    | Claims x calls  |
| CRITIC   | Any available tools | Verifiable via execution | Tool API + 2-3x |

### CoVe: Question-Based Fact-Checking

Per Dhuliawala et al. (2023): "CoVe drafts response, plans verification
questions, answers them independently, then generates verified response."

**Process:**

```
T1 (Baseline): query -> response_0 [may hallucinate]
T2 (Plan):     query + response_0 -> verification_questions
T3 (Execute):  verification_questions ONLY -> answers  [baseline EXCLUDED]
T4 (Revise):   query + response_0 + QA_pairs -> final_response
```

**Why this works:** Same model that hallucinates in longform correctly answers
direct questions. Shortform forces factual recall; longform encourages
confabulation.

| Setting                    | Accuracy |
| -------------------------- | -------- |
| Facts in longform          | ~17%     |
| Same facts as individual Q | ~70%     |

**Critical: Factored (isolated) verification**

WRONG (joint): `T3: Answer all Qs with response_0 in context` -- copies
hallucinations RIGHT (factored): `T3a: Answer Q1 alone; T3b: Answer Q2 alone` --
independent recall

| Method        | Precision |
| ------------- | --------- |
| Baseline      | 0.13      |
| Joint CoVe    | 0.15      |
| Factored CoVe | 0.22      |

**Open questions outperform yes/no:**

WRONG: `"Was Bloomberg born in New York?"` -- model agrees regardless RIGHT:
`"Where was Bloomberg born?"` -- forces factual recall

**Factor+Revise** adds explicit cross-check for +7.7pp:

```
T3.5 (Cross-check): response_0 + QA_pairs -> inconsistency_list
T4 (Revise):        response_0 + QA_pairs + inconsistencies -> final
```

### Factored Verification: Source-Based Checking

Specialized for summaries with source material. Per George & Stuhlmuller (2023):
"Decompose summary into claims, verify each against source."

**Process:**

```
T1 (Decompose): summary -> [claim_1, claim_2, ..., claim_n]
T2 (Verify):    For each claim: source + claim -> Supported/Not + reasoning
T3 (Revise):    summary + unsupported_claims + critiques -> revised_summary
```

**Why single-prompt fails:** George & Stuhlmuller: "Single-prompt (decompose +
verify together) achieved 63.3% vs multi-prompt factored 71.2%." Separating
prevents rationalization.

**Decomposition prompt:**

```
Extract ALL claims from this summary as a "-" separated list.
Start with "The claims are:"

[summary]
```

**Verification prompt:**

```
Check if claim is supported by document. Include quotes in reasoning.

Document: [document]
Claim: [claim]

Reasoning: [with quotes]
Supported: [Yes/No]
```

**Performance (HaluEval):**

| Model   | Few-shot | CoT   | Factored |
| ------- | -------- | ----- | -------- |
| GPT-4   | 30.9%    | 75.5% | 76.2%    |
| GPT-3.5 | 58.5%    | 61.2% | 71.2%    |

**Hallucination reduction:** GPT-4: 0.84->0.46/s (-45%); Claude2: 1.55->0.95/s
(-39%)

**Warning:** Simple self-correction makes hallucinations WORSE. George &
Stuhlmuller: "Self-correct increased hallucinations from 1.55 to 2.13." Factored
succeeds because claims verified against source, not model's own reasoning.

### CRITIC: Tool-Interactive Verification

Uses external tools instead of LLM knowledge. Per Gou et al. (2024): "CRITIC
allows LLMs to validate outputs similar to human tool interaction."

**Tool flexibility:** The original paper uses search APIs and calculators, but
CRITIC generalizes to any verification tool the agent can access. Most claims
can be verified with basic tools—grep to find patterns, search to locate
information, read to check source content. For complex claims that can't be
verified through simple lookup, write temporary verification code.

**Process:**

```
T1 (Generate): query -> response_0
T2 (Verify):   response_0 + tools -> verification_results + critique
T3 (Correct):  If issues: query + response_0 + critique -> corrected
               If passed: return response_0
```

**Performance:**

| Task               | Baseline | +CRITIC | Delta  |
| ------------------ | -------- | ------- | ------ |
| AmbigNQ (QA)       | 47.4 F1  | 55.1 F1 | +7.7   |
| GSM8K (Math)       | 81.0%    | 88.0%   | +7.0pp |
| Toxicity reduction | --       | --      | 79.2%  |

**Key insight:** CRITIC's improvement comes from external signal, not additional
reasoning. Per Gou et al.: "Exclusive reliance on self-correction without
external feedback may deteriorate performance."

**Stacking:** All three verification methods share the contaminated-context
anti-pattern. Can combine when different verification types needed (e.g., CoVe
for knowledge claims + CRITIC for calculations).

### Self-Explanation: Comprehension Before Task

For dialogue understanding tasks, explain each conversation turn before
performing the downstream task. Per Zhang et al. (2023): "Self-explanation
prompting generates an explanation of each dialogue turn, then reasons about
state tracking."

**Process:**

```
T1 (Explain):  dialogue -> turn-by-turn explanations
T2 (Execute):  dialogue + explanations -> task output (e.g., slot values)
```

**Explanation prompt:**

```
For each turn in this dialogue, explain what the speaker meant and what
information they conveyed.

Dialogue:
{dialogue_turns}

Turn-by-turn explanation:
```

**Performance:** +6 percentage points on Joint Goal Accuracy for dialogue state
tracking tasks. The technique helps models correctly identify slot values,
entities, and intents that are implicit in conversational language.

**Why it works:** Dialogues contain implicit information, ellipsis, and
coreference that single-pass processing misses. Explicit explanation forces
comprehension before extraction.

WRONG: `Extract slot values directly from dialogue` RIGHT: `First explain each
turn, then extract values with explanations in context`

**Scope:** Designed for dialogue tasks (state tracking, response generation) but
the explain-then-execute pattern generalizes to any task requiring implicit
understanding.

---

## 4. Meta-Reasoning

### Cumulative Reasoning (CR): DAG-Based Validation

For complex reasoning requiring validated step accumulation. Per Zhang et al.
(2024): "CR dynamically constructs DAG of validated steps; new propositions
derive from any combination of prior nodes."

**Three roles:**

```
PROPOSER: Generates candidate steps from current DAG
VERIFIER: Validates proposals (LLM or external tool)
REPORTER: Monitors DAG, determines when to conclude
```

**Coordination loop:**

```
Initialize: DAG = {original_question}

Loop:
  Propose: DAG -> candidate_step
  Verify:  candidate + relevant_nodes -> Valid/Invalid
  If Valid: Add to DAG
  Report:  DAG -> "Continue" or "Conclude: answer"

Until Reporter concludes or iteration limit
```

**Why CR beats Tree of Thoughts:** ToT explores paths independently. CR
integrates validated knowledge across paths into shared DAG. New propositions
combine facts from ANY prior validated nodes.

**Performance:**

| Task         | CoT-SC | ToT | CR      |
| ------------ | ------ | --- | ------- |
| Game of 24   | 9%     | 74% | **98%** |
| MATH Level 5 | --     | --  | +43%    |

**Proposer prompt:**

```
Problem: {question}

Validated reasoning:
{dag_nodes}

Generate ONE atomic proposition advancing reasoning.
Must be: derivable from above, specific, verifiable, single logical step.
```

**Verifier prompt:**

```
Proposition: {candidate}
Supporting context: {relevant_nodes}

Is this valid? Explain reasoning, conclude "VALID" or "INVALID".
```

**Reporter prompt:**

```
Problem: {question}
Validated propositions: {all_nodes}

Sufficient to answer conclusively?
If YES: "CONCLUDE" + final answer
If NO: "CONTINUE" + what additional reasoning needed
```

**Stacking:** Replace LLM verifier with tool-based (Python, theorem prover) for
stronger guarantees.

### Selection-Inference: Interleaved Fact Selection and Deduction

For multi-step logical reasoning, alternates between selecting relevant facts
and inferring new facts. Per Creswell et al. (2022): "SI framework exploits LLMs
as general processing modules, alternating between selection and inference."

**Process:**

```
Initialize: context_0 = original_facts + rules + question

Loop until answer found:
  T_select: context_t + question -> subset of facts for this step
  T_infer:  selected_facts -> new_fact
  context_{t+1} = context_t + new_fact
```

**Selection prompt:**

```
Context:
{facts_and_rules}

Question: {question}

Select the facts and rules needed for the NEXT step of reasoning.
Do not solve the entire problem. Select for ONE inference only.
```

**Inference prompt:**

```
Selected facts:
{selection}

What can you infer from ONLY these facts? State ONE new fact.
```

**Why it works:** Creswell et al.: "LLMs are good at single-step inference but
struggle to chain multiple steps." SI factors multi-hop reasoning into separate,
manageable selection and deduction steps.

**Performance:** 7B parameter model in SI framework achieves 3x improvement over
vanilla baseline, and outperforms 280B parameter models on ProofWriter logical
reasoning tasks.

**Key benefit:** Produces _causal_ reasoning traces. Each inference depends only
on the selected facts, not the full context--creating interpretable,
debuggable reasoning chains.

WRONG: `Solve the entire multi-hop problem in one pass` RIGHT: `Step 1: Select
relevant facts. Step 2: Make one inference. Repeat until solved.`

**Stacking:** Add external verifiers after each inference step to catch invalid
deductions before they propagate.

---

## 5. Decomposition

### Least-to-Most Prompting: Easy-to-Hard Generalization

Two-stage decomposition that solves simpler subproblems first. Per Zhou et al.
(2023): "First decompose a complex problem into a list of easier subproblems,
then sequentially solve them, whereby solving a given subproblem is facilitated
by answers to previously solved subproblems."

**Process:**

```
Stage 1 (Decompose): complex_question -> [sub_q1, sub_q2, ..., sub_qn]
                     (easiest to hardest, original problem last)

Stage 2 (Solve):     For each sub_question in order:
                       context = [prior answers] + sub_question -> answer
```

**Decomposition prompt:**

```
To solve "{question}", we need to first solve these simpler problems:
```

**Solving prompt:**

```
{sub_q_1}: {answer_1}
{sub_q_2}: {answer_2}
...
{current_sub_q}:
```

**Why it works:** Zhou et al.: "Least-to-most prompting can generalize to
problems harder than those demonstrated." Prior answers become building blocks
for subsequent reasoning.

**Performance:**

| Task                     | CoT   | Least-to-Most | Delta |
| ------------------------ | ----- | ------------- | ----- |
| DROP (compositional)     | 74.8% | 82.5%         | +8pp  |
| GSM8K (5+ step problems) | 39.1% | 45.2%         | +6pp  |
| SCAN (length split)      | 16.2% | 99.7%         | +84pp |

**Key insight:** Chain-of-Thought struggles when test problems require more
reasoning steps than demonstration examples. Least-to-Most addresses this
"easy-to-hard" gap by teaching decomposition rather than direct solution.

**Single-pass variant:** For some tasks, decomposition and solving can merge:
"Let's break this down: 1. [sub-problem] -> [answer]. 2. [sub-problem] ->
[answer]. Final: [answer]."

WRONG: `Show complex multi-step reasoning in one demonstration` RIGHT: `Show
how to decompose, then how to solve simple sub-problems sequentially`

**Stacking:** Combines with CoT and Self-Consistency. Can precede Decomposed
Prompting when task structure is unknown.

### Decomposed Prompting (DECOMP): Specialized Handlers

Modular approach delegating sub-tasks to specialized handlers. Per Khot et al.
(2023): "Both decomposer and sub-task handlers have own few-shot prompts."

**Two-layer architecture:**

```
Layer 1 (Decomposer): complex_task -> sequence of sub-task calls
Layer 2 (Handlers):   Each sub-task type has specialized few-shot prompt
```

**Example:**

```
Complex: "Birthplace of Titanic's director?"

Decomposer:
  1. RETRIEVE("Who directed Titanic?")
  2. RETRIEVE("Where was {result1} born?")

Handlers:
  RETRIEVE("Who directed Titanic?") -> "James Cameron"
  RETRIEVE("Where was James Cameron born?") -> "Kapuskasing, Ontario"
```

**Recursive Decomposition:** Handlers can themselves be decomposition prompts.
Per Khot et al.: "If a sub-task is too complex, it can be further decomposed
into simpler sub-tasks." This enables hierarchical problem-solving where a
handler delegates to its own sub-handlers.

**Handler reusability:** Handlers act as a library shared across tasks. A
`split` handler for tokenizing strings can serve both letter concatenation and
text processing tasks without modification.

**Key distinction from Least-to-Most:** Least-to-Most uses a single prompt to
answer all sub-questions sequentially. Decomposed Prompting assigns specialized
handlers per sub-task type, enabling: (1) richer examples per sub-task, (2)
symbolic functions (calculators, retrieval), (3) recursive decomposition.

WRONG: Single generic handler for all sub-tasks RIGHT: Specialized handlers with
own few-shot examples per sub-task type

### ADAPT: Decompose on Failure

Recursive approach decomposing only when executor fails. Per Prasad et al.
(2024): "ADAPT recursively decomposes to adapt to task complexity and LLM
capability."

**Recursive structure:**

```
ADAPT(task, depth):
  If depth > max_depth: Return failure

  result = Executor(task)

  If success: Return result
  Else:
    plan = Planner(task)  # Decompose
    For each sub_task in plan:
      sub_result = ADAPT(sub_task, depth + 1)
    Return aggregated results
```

**Why ADAPT beats fixed plans:** Plan-and-Execute creates fixed plans upfront,
fails when sub-tasks unexpectedly difficult. ADAPT decomposes only on failure,
matching depth to actual difficulty.

**Performance:**

| Dataset   | ReAct | Plan-Execute | ADAPT     |
| --------- | ----- | ------------ | --------- |
| ALFWorld  | 43.3% | 43.3%        | **71.6%** |
| WebShop   | 32.0% | 17.0%        | **44.0%** |
| TextCraft | 19.0% | 27.0%        | **52.0%** |

**Self-generated success heuristic:** Prasad et al.: "Executor LLM determines
completion without gold rewards."

WRONG: Always decompose to max depth RIGHT: Try execution first, decompose only
on failure

**Stacking:** Combine with Self-Refine for failed sub-tasks, CRITIC for
tool-validated execution.

### Look Before You Leap (LEP): Problem Elaboration

Elaborates the problem before solving to improve comprehension. Per Xu et al.
(2023): "Problem elaboration prompting improves mathematical reasoning by
making implicit information explicit before solving."

**Process:**

```
T1 (Elaborate): question -> elaboration including:
                - Key entities and relationships
                - Implicit constraints made explicit
                - Problem restatement in clearer terms
T2 (Solve):     question + elaboration -> answer
```

**Elaboration prompt:**

```
Before solving, elaborate on this problem:
1. Identify all given quantities and unknowns
2. State any implicit assumptions
3. Rephrase the problem in your own words
4. Identify the mathematical relationships involved

Problem: {question}
```

**Performance:**

| Dataset  | CoT   | +LEP  | Delta  |
| -------- | ----- | ----- | ------ |
| Math23K  | 78.2% | 83.6% | +5.4pp |
| Geometry | 64.3% | 69.3% | +5.0pp |
| SVAMP    | 79.0% | 83.1% | +4.1pp |

**Why it works:** Mathematical word problems often contain implicit information
that causes errors. Elaboration makes this explicit before reasoning begins,
reducing misinterpretation.

WRONG: `"Think carefully, then solve."`
RIGHT: `"First elaborate: what quantities are given? What's asked? What
relationships connect them?"`

**Stacking:** Pairs well with Decomposed Prompting—elaborate first, then
decompose. Can precede any reasoning technique.

### Successive Prompting: Sequential Decomposition

Iteratively decomposes complex questions into sub-questions answered
sequentially. Per Wang et al. (2022): "Complex questions are decomposed into
simpler sub-questions that can be answered in succession."

**Process:**

```
T1: question -> sub_question_1 + answer_1
T2: question + [sub_q1: answer_1] -> sub_question_2 + answer_2
T3: question + [sub_q1: answer_1, sub_q2: answer_2] -> sub_question_3 + answer_3
...
Tn: question + all_sub_qa_pairs -> final_answer
```

**Key principle:** Each turn generates BOTH the next sub-question AND its
answer. The growing context of answered sub-questions guides subsequent
decomposition.

**Example (multi-hop QA):**

```
Question: "What year was the university founded where the author of
          'The Great Gatsby' studied?"

T1: Sub-Q: "Who wrote 'The Great Gatsby'?"
    Answer: "F. Scott Fitzgerald"

T2: Sub-Q: "Where did F. Scott Fitzgerald study?"
    Answer: "Princeton University"

T3: Sub-Q: "When was Princeton University founded?"
    Answer: "1746"

Final: "1746"
```

**Difference from Decomposed Prompting:** Successive Prompting generates sub-
questions dynamically based on accumulated context; Decomposed Prompting uses
pre-defined handlers with fixed decomposition strategies.

**Performance:** Per Wang et al. (2022): Achieves 30.6% F1 on DROP (complex
compositional questions), outperforming CoT by +4.3%. The sequential
decomposition handles multi-hop dependencies that confuse single-pass reasoning.

WRONG: Plan all sub-questions upfront
RIGHT: Generate each sub-question after seeing previous answers

**Stacking:** Complements ADAPT—use Successive for known-structure multi-hop,
ADAPT for unknown complexity. Can apply verification after each sub-answer.

---

## 6. Prompt Design

---

## 7. Context Management

Multi-turn accumulates context. Manage token limits by:

1. **Summarize history:** After N iterations, summarize previous attempts
2. **Keep recent + best:** Retain only most recent and best-scoring output
3. **Structured extraction:** Extract key points from feedback, not full text

WRONG:

```
[Full y_0] [Full fb_0] [Full y_1] [Full fb_1] ...
```

RIGHT:

```
Previous attempts summary:
- Attempt 1: Failed due to [issue]
- Attempt 2: Improved [aspect] but [remaining issue]
- Attempt 3: Best so far, minor [aspect] issue

Latest attempt: [full y_3]
```

**Conversation template:**

```
SYSTEM: [Base prompt with single-turn techniques]

T1 (Generate): USER: [Task] -> ASSISTANT: [y_0]
T2 (Analyze):  USER: [Critique/verify y_0] -> ASSISTANT: [Feedback]
T3 (Refine):   USER: [Refine with T2 output] -> ASSISTANT: [y_1]
[Repeat]
T_final:       USER: [Extract in format] -> ASSISTANT: [Final]
```

---

## 8. Anti-Patterns

### Intrinsic Self-Correction

"Review and improve without external signals" fails--74.7% keep original;
changes more likely wrong (Huang et al. 2024).

WRONG: `T1: Solve -> T2: Review and fix` RIGHT:
`T1: Solve -> T2: Generate verification Qs -> T3: Answer (isolated) -> T4: Revise`

### Mixed-Goal Turn

Combining distinct operations in single turn degrades both.

WRONG: `Generate, then critique it, then improve it` RIGHT:
`T1: Generate -> T2: Critique (feedback only) -> T3: Improve`

### Contaminated Context

Including original when answering verification questions.

WRONG: `Original: [hallucinations] + Verification Q: Where was X born?` RIGHT:
`Verification Q: Where was X born? [original NOT in context]`

### Yes/No Verification

Phrasing verification as yes/no confirmations.

WRONG: `"Is it true Bloomberg was born in New York?"` RIGHT:
`"Where was Bloomberg born?"`

### Infinite Loop

No explicit stopping condition.

WRONG: `Keep improving until perfect` RIGHT:
`Improve for 3 iterations, output best version`

### Forgotten History

Discarding previous iterations in refinement.

WRONG: `Here is feedback. Improve. [no previous attempts]` RIGHT:
`Attempts: 1: y_0 -> fb_0; 2: y_1 -> fb_1. Improve, avoid previous mistakes.`

### Vague Feedback

Feedback without actionable specifics.

WRONG: `Response could be improved. Some parts unclear.` RIGHT:
`Paragraph 2 uses "electron transport chain" without definition. Add: "process converting light to chemical energy."`

### Majority Fallacy

Assuming majority vote always correct.

WRONG: `3/5 say X, so X is correct` RIGHT:
`Consider confidence weighting, check for systematic errors common across samples`

---

## Research Citations

- Creswell, A., et al. (2022). "Selection-Inference: Exploiting Large Language
  Models for Interpretable Logical Reasoning." arXiv.
- Dhuliawala, S., et al. (2023). "Chain-of-Verification Reduces Hallucination in
  Large Language Models." arXiv.
- George, C. & Stuhlmuller, A. (2023). "Factored Verification: Detecting and
  Reducing Hallucination in Summaries." arXiv.
- Gou, Z., et al. (2024). "CRITIC: Large Language Models Can Self-Correct with
  Tool-Interactive Critiquing." arXiv.
- Huang, J., et al. (2024). "Large Language Models Cannot Self-Correct Reasoning
  Yet." arXiv.
- Khot, T., et al. (2023). "Decomposed Prompting: A Modular Approach for Solving
  Complex Tasks." arXiv.
- Liu, J., et al. (2022). "Generated Knowledge Prompting for Commonsense
  Reasoning." ACL.
- Madaan, A., et al. (2023). "Self-Refine: Iterative Refinement with
  Self-Feedback." arXiv.
- Prasad, A., et al. (2024). "ADAPT: As-Needed Decomposition and Planning with
  Language Models." arXiv.
- Radha, S., et al. (2024). "Iteration of Thought: Leveraging Inner Dialogue for
  Autonomous Large Language Model Reasoning." arXiv.
- Tian, X., et al. (2025). "Think Twice: Enhancing LLM Reasoning by Scaling
  Multi-round Test-time Thinking." arXiv.
- Wang, L., et al. (2022). "Successive Prompting for Decomposing Complex
  Questions." arXiv.
- Weston, J. & Sukhbaatar, S. (2023). "System 2 Attention (Is Something You
  Might Need Too)." arXiv.
- Xu, D., et al. (2023). "Look Before You Leap: Problem Elaboration Prompting
  Improves Mathematical Reasoning in Large Language Models." arXiv.
- Zhang, S., et al. (2023). "Self-Explanation Prompting Improves Dialogue
  Understanding in Large Language Models." arXiv.
- Zhang, Y., et al. (2024). "Cumulative Reasoning with Large Language Models."
  TMLR.
- Zheng, C., et al. (2023). "Progressive-Hint Prompting Improves Reasoning in
  Large Language Models." arXiv.
- Zheng, Z., et al. (2024). "Take a Step Back: Evoking Reasoning via Abstraction
  in Large Language Models." ICLR.
- Zhou, D., et al. (2023). "Least-to-Most Prompting Enables Complex Reasoning in
  Large Language Models." ICLR.
