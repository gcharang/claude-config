# Prompt Engineering: Research-Backed Techniques for Reasoning Compression

This document synthesizes practical prompt engineering patterns with academic
research on efficient LLM reasoning. All techniques target **reasoning
compression**--reducing token usage in chain-of-thought outputs while
maintaining accuracy. Techniques may be combined with single-turn or multi-turn
methods.

**Meta-principle**: Effective reasoning compression preserves essential logical
steps while eliminating verbosity. The goal is not minimal output, but
_sufficient_ output--enough tokens to maintain reasoning fidelity, no more.

**Prerequisites**: Assumes familiarity with Chain-of-Thought (CoT) prompting.
Compression techniques modify CoT behavior, not replace it.

---

## Technique Selection Guide

| Domain                | Technique            | Trigger Condition                           | Stacks With                                      | Conflicts With         | Cost/Tradeoff                       | Effect                                     |
| --------------------- | -------------------- | ------------------------------------------- | ------------------------------------------------ | ---------------------- | ----------------------------------- | ------------------------------------------ |
| **Explicit Limits**   | Concise CoT          | General verbosity reduction needed          | Any CoT variant                                  | --                     | Few-shot examples required          | ~49% token reduction; negligible acc. loss |
| **Explicit Limits**   | Constrained-CoT      | Predictable output length needed            | CoT, larger models                               | Small models (<13B)    | May miss constraint on hard limits  | 28-68% token reduction; +5% acc. on large  |
| **Per-Step Limits**   | Chain of Draft (CoD) | Maximum compression with accuracy           | Few-shot only                                    | Zero-shot              | 5-word-per-step limit               | 75-92% token reduction; ~same accuracy     |
| **Dynamic Budget**    | TALE-EP              | Variable complexity; cost-sensitive         | Any reasoning task                               | --                     | Extra estimation call               | 67% token reduction; <3% acc. loss         |
| **Cognitive**         | Sketch-of-Thought    | Multi-domain reasoning; maximum compression | Self-Refine, Multi-Agent Debate, Self-Consistency | --                     | Router overhead; paradigm selection | Up to 84% token reduction; +/- 1% accuracy |
| **Path Optimization** | MARP                 | Math reasoning; known reasoning boundaries  | PoT, Tool Usage, Self-Consistency (for PFRB)    | Verbose demonstrations | Requires boundary knowledge         | +7% acc.; -20% tokens vs CoT               |

---

## Quick Reference: Key Principles

1. **Per-Step > Global Budgets** -- Per-step word limits (CoD: "5 words per
   step") outperform global token budgets; models follow local constraints
   better
2. **Few-Shot Required for Compression** -- Zero-shot compression fails; models
   need examples of concise reasoning style
3. **Larger Models Compress Better** -- Compression techniques degrade small
   models (<7B); larger models (>40B) may improve accuracy. Per Chen et al.
   (2024): reasoning boundary increases with model parameter count (scaling
   law), explaining why compression constraints work better at scale
4. **Math Most Sensitive** -- Mathematical reasoning suffers most from
   aggressive compression; use Chunked Symbolism or preserve calculation steps
5. **Token Elasticity** -- Very small budgets cause token _increase_; models
   resist unrealistic constraints by producing more output
6. **Symbolic > Natural Language** -- Symbolic notation (equations, shorthand)
   compresses better than abbreviated natural language
7. **Concise Examples Mandatory** -- "Be concise" instruction alone insufficient;
   provide explicitly concise few-shot examples
8. **Paradigm Matching** -- Different reasoning types (math vs commonsense)
   benefit from different compression strategies
9. **Maintain Reasoning Steps** -- Compress _verbosity_, not _reasoning_;
   preserve logical step boundaries
10. **Route by Task Type** -- Use routers or heuristics to select compression
    paradigm based on query structure

---

## 1. Explicit Length Constraints

### Concise Chain-of-Thought: Verbosity Reduction

Combines "be concise" instruction with concise few-shot examples. Per Renze
(2024): "CCoT reduced average response length by 48.70% for both GPT-3.5 and
GPT-4 while having a negligible impact on problem-solving performance."

**Process:**

```
System: Think step-by-step through the problem to ensure the correct answer.
        Be concise.

Few-shot example (concise style):
Q: What is the capital of the state where Johns Hopkins University is located?
A: Johns Hopkins University is in Baltimore, Maryland.
   The capital of Maryland is Annapolis.
   Answer: Annapolis
```

**Critical:** Both instruction AND concise examples required. Instruction alone
fails.

WRONG: `"Think step by step. Be concise." + verbose examples`
RIGHT: `"Think step by step. Be concise." + examples showing concise reasoning`

**Performance (GPT-4):**

| Metric        | Verbose CoT | Concise CoT | Delta   |
| ------------- | ----------- | ----------- | ------- |
| Token count   | ~200        | ~100        | -49.77% |
| Accuracy      | 82.9%       | 83.2%       | +0.3pp  |
| Cost per 1000 | $26.90      | $20.58      | -23.49% |

**Math caveat:** GPT-3.5 with Concise CoT shows 27.69% accuracy reduction on math
problems. GPT-4 unaffected. Use larger models or preserve math steps.

### Constrained-CoT: Explicit Word Limits

Adds explicit length constraint to CoT prompt. Per Nayab et al. (2024): "CCoT
encourages the LLM to limit output length and control the reasoning process."

**Prompt format:**

```
Let's think step by step and limit the length of the answer to [N] words.
```

**Performance (Llama2-70B on GSM8K):**

| Setting  | Accuracy | Avg Words | Inference Time |
| -------- | -------- | --------- | -------------- |
| Base     | 34.8%    | --        | --             |
| CoT      | 36.0%    | 99        | 30.09s         |
| CCoT-100 | 41.1%    | 71        | 23.86s         |
| CCoT-45  | 40.2%    | 64        | --             |

**Model size matters:**

| Model Size | CCoT Effectiveness |
| ---------- | ------------------ |
| <7B        | Degrades accuracy  |
| 13B        | Mixed results      |
| >40B       | Improves accuracy  |

**Key insight:** Large models (Llama2-70b) improve accuracy WITH compression.
Small models (Falcon-7b) cannot follow length constraints effectively.

**Step count trade-off:** Per Chen et al. (2024), increasing reasoning steps
improves accuracy only up to a threshold; beyond this optimal count, performance
degrades. See "The Overcomplexity Trap" in Anti-Patterns.

WRONG: `"Limit to 10 words"` (too restrictive; causes token elasticity)
RIGHT: `"Limit to 45-100 words"` (reasonable constraint respects model limits)

---

## 2. Per-Step Constraints

### Chain of Draft (CoD): Minimal Intermediate Steps

Constrains each reasoning step to ~5 words, mimicking human shorthand. Per Xu et
al. (2025): "CoD matches or surpasses CoT in accuracy while using as little as
only 7.6% of the tokens."

**Process:**

```
System: Think step by step, but only keep a minimum draft for each thinking
        step, with 5 words at most. Return the answer after a separator ####.

Few-shot example:
Q: Jason had 20 lollipops. He gave Denny some. Now Jason has 12. How many
   did Jason give to Denny?
A: 20 - x = 12; x = 8. #### 8
```

**Critical:** Per-step limit, NOT global budget. Models follow local constraints
better than global ones.

**Performance (Claude 3.5 Sonnet):**

| Task               | CoT Acc | CoD Acc | CoT Tokens | CoD Tokens | Reduction |
| ------------------ | ------- | ------- | ---------- | ---------- | --------- |
| GSM8K (math)       | 95.8%   | 91.4%   | 190.0      | 39.8       | -79.1%    |
| Date Understanding | 87.0%   | 89.7%   | 172.5      | 31.3       | -81.9%    |
| Sports             | 93.2%   | 97.3%   | 189.4      | 14.3       | -92.4%    |
| Coin Flip          | 100%    | 100%    | 135.3      | 18.9       | -86.0%    |

**Limitations:**

1. **Zero-shot fails:** Without few-shot examples showing draft style, models
   revert to verbose output
2. **Small models struggle:** <3B models show significant accuracy drops with
   CoD

**Few-shot is mandatory:**

| Setting       | GSM8K Acc | Tokens |
| ------------- | --------- | ------ |
| Zero-shot CoT | 90.4%     | 248.8  |
| Zero-shot CoD | 65.5%     | 73.7   |
| Few-shot CoT  | 95.8%     | 190.0  |
| Few-shot CoD  | 91.4%     | 39.8   |

WRONG: Zero-shot: `"Keep each step to 5 words"`
RIGHT: Few-shot with examples showing 5-word steps

---

## 3. Dynamic Budget Estimation

### TALE-EP: Token-Budget-Aware Reasoning

Estimates optimal token budget per problem before prompting. Per Han et al.
(2025): "TALE-EP achieves a 67% reduction in token usage while maintaining
accuracy with less than a 3% decrease."

**Process:**

```
Step 1 (Estimate): Prompt LLM to estimate reasoning complexity
Step 2 (Prompt):   Include estimated budget in CoT prompt

Estimation prompt:
"Estimate how many tokens of reasoning this problem requires: [question]"

Reasoning prompt:
"Let's think step by step and use less than [estimated_budget] tokens:"
```

**Token elasticity phenomenon:** Very small budgets cause models to produce MORE
tokens, not fewer. The optimal budget sits in a "sweet spot" range.

**Performance (GPT-4o-mini):**

| Method      | Accuracy | Output Tokens | Expense |
| ----------- | -------- | ------------- | ------- |
| Direct      | 53.3%    | 1.1           | 0.6     |
| Vanilla CoT | 95.4%    | 205.1         | 4.2     |
| TALE-EP     | 71.8%    | 112.2         | --      |

**Training alternative (TALE-PT):** For users who can modify models, TALE-PT
internalizes budget awareness via post-training (SFT or DPO). Per Han et al.
(2025): "TALE-PT-SFT achieves the best accuracy (78.57%) with reduced tokens"
without explicit budget prompts at inference time. Requires model fine-tuning;
not a prompting technique.

---

## 4. Cognitive-Inspired Compression

### Sketch-of-Thought (SoT): Paradigm-Based Sketching

Uses cognitively-inspired reasoning paradigms selected by lightweight router.
Per Thawakar et al. (2025): "SoT achieves token reductions of up to 84% with
minimal accuracy loss."

**Three paradigms:**

| Paradigm            | Use Case                | Style                     |
| ------------------- | ----------------------- | ------------------------- |
| Conceptual Chaining | Commonsense, multi-hop  | Concept -> Concept -> ... |
| Chunked Symbolism   | Math, arithmetic        | Variables and equations   |
| Expert Lexicons     | Technical, domain-specific | Abbreviations, notation  |

**Conceptual Chaining example:**

```
Q: What is the currency used in Seoul?
A: <think> #Seoul -> #South Korea -> Won </think>
Answer: Korean Won
```

**Chunked Symbolism example:**

```
Q: A car accelerates at 2.5 m/s^2 for 10 seconds. Initial velocity 15 m/s.
   Final velocity?
A: <think> a=2.5, t=10, vi=15; vf=15+(2.5*10)=40 </think>
Answer: 40 m/s
```

**Expert Lexicons example:**

```
Q: Patient with STEMI given MONA therapy. Allergic to aspirin. At risk?
A: <think> STEMI -> ST-Elevation MI; MONA -> Morphine, O2, Nitrates, Aspirin;
   Aspirin in MONA </think>
Answer: Yes
```

**Router selection:** Lightweight DistilBERT model classifies query -> paradigm.
96.4% routing accuracy.

**Performance (Qwen-2.5-32B, averaged across 18 datasets):**

| Method | Accuracy | Tokens | Reduction |
| ------ | -------- | ------ | --------- |
| CoT    | 82.24%   | 177    | --        |
| CCoT   | 81.70%   | 45     | -74.6%    |
| CoD    | 76.91%   | 34     | -80.8%    |
| SoT    | 82.30%   | 45     | -74.6%    |

**Paradigm-task alignment matters:**

| Dataset (Type)   | Dominant Paradigm   | Acc with Dominant | Acc with Others |
| ---------------- | ------------------- | ----------------- | --------------- |
| GSM8K (math)     | Chunked Symbolism   | 86.94%            | 78-82%          |
| HotpotQA (multi) | Conceptual Chaining | 88.30%            | 81-85%          |
| MedQA (medical)  | Expert Lexicons     | 85.70%            | 73-79%          |

**Ensemble stacking:** SoT combines effectively with ensemble methods. Per
Thawakar et al. (2025): "In the Self-Refine setting, SoT improves accuracy by
0.27% while generating 60% fewer tokens per response. In the Multi-Agent Debate
framework, SoT yields a 0.57% accuracy increase alongside a 69% token reduction."

**Multilingual and multimodal:** SoT maintains 80%+ token reduction across
Korean, Italian, German. Works with vision-language models.

**Multimodal caveat:** Per Thawakar et al. (2025): "On GQA, however, we observed
a 2.50% reduction in accuracy when using SoT while reducing output length by
75%." Visual grounding tasks requiring fine-grained image analysis show
degradation with abstract sketching methods.

---

## 5. Reasoning Path Optimization

### Minimum Acceptable Reasoning Paths (MARP)

Maximizes computation per step while minimizing total steps. Derived from
Reasoning Boundary Framework. Per Chen et al. (2024): "MARP demonstrably
improves model performance and effectively reduces token consumption."

**Core principle:** The reasoning boundary depends on both calculation
complexity AND planning steps. Optimize the product, not individual factors.

```
Reasoning Boundary = f(calculation_per_step, total_steps)
Goal: Maximize calculation_per_step while minimizing total_steps
      within model's capability
```

**MARP construction:**

```
1. Identify model's single-step calculation limit (via probing)
2. Construct demonstrations that approach (not exceed) this limit per step
3. Minimize total steps by combining operations
4. Add instruction constraining single-step complexity upper bound
```

**Performance (GPT-3.5-Turbo on BigGSM):**

| Method        | Accuracy | Input Tokens | Output Tokens |
| ------------- | -------- | ------------ | ------------- |
| CoT           | 57.00%   | 780          | 96.76         |
| Complex-CoT   | 59.78%   | 1111         | 131.82        |
| Least-to-Most | 58.25%   | 679          | 176.09        |
| CoT+MARP      | 64.37%   | 614          | 95.12         |
| PoT+MARP      | 80.55%   | 576          | 76.34         |

**Three reasoning boundaries (from RBF theory):**

| Boundary | Accuracy Range | Model Behavior                      | Optimization Strategy                    |
| -------- | -------------- | ----------------------------------- | ---------------------------------------- |
| CFRB     | >90%           | Complete mastery; zero-shot capable | No compression needed                    |
| PFRB     | 10-90%         | Partial confidence; needs consensus | Apply MARP + Self-Consistency            |
| CIRB     | <10%           | Model cannot solve                  | Use tools or decompose                   |

**Self-Consistency for PFRB:** Per Chen et al. (2024): "as the integration of
reasoning paths increases, the accuracy improves significantly within PFRB
compared with other RBs." When accuracy falls in the 10-90% zone, combine MARP
with Self-Consistency (sampling multiple reasoning paths) for best results.

**Stacking with tools:** When using code execution (PoT), calculation boundary
-> infinity, leaving only planning boundary to optimize.

---

## 6. Metrics for Compression Evaluation

### Concise Correctness Metrics

Standard accuracy ignores output length. These metrics penalize verbosity.

**Hard-k Concise Accuracy (HCA):**

```
HCA(k) = (correct answers with length <= k) / total questions
```

Strict cutoff. Use for systems with hard length requirements.

**Soft-k Concise Accuracy (SCA):**

```
SCA(k, alpha) = sum(correct_i * min(1, exp((k - length_i) / alpha))) / N
```

Exponential penalty for exceeding k. Alpha controls tolerance.

**Consistent Concise Accuracy (CCA):**

```
CCA(k, alpha, beta) = SCA(k, alpha) * min(1, exp((beta - std_dev) / beta))
```

Additional penalty for high variance in output lengths. Beta controls tolerance.

**When to use:**

- HCA: Real-time systems, strict latency requirements
- SCA: Cost optimization with soft constraints
- CCA: Predictable response times needed (user-facing applications)

---

## 7. Anti-Patterns

### Zero-Shot Compression

Compression instructions without examples fail. Models default to verbose
patterns from training.

WRONG: `"Be concise. Think step by step in under 50 words."`
RIGHT: `"Be concise." + few-shot examples showing concise reasoning`

### Unrealistic Budgets

Very small budgets trigger "token elasticity"--model produces MORE output when
constraint is unrealistic.

WRONG: `"Limit to 10 tokens"` for multi-step math
RIGHT: `"Limit to 50-100 tokens"` or use per-step limits

### Small Model Compression

Models <7B parameters cannot reliably follow compression constraints. Accuracy
degrades significantly.

WRONG: Applying Constrained-CoT to Falcon-7b
RIGHT: Use compression only on models >13B, preferably >40B

### Global vs Per-Step Confusion

Global token budgets harder to follow than per-step limits.

WRONG: `"Keep your entire response under 50 words"`
RIGHT: `"Keep each reasoning step to 5 words or less"`

### Math Verbosity Stripping

Mathematical reasoning is most sensitive to compression. Stripping calculation
steps causes errors.

WRONG: `"Skip the calculations, just give the answer"`
RIGHT: Use Chunked Symbolism: `a=5, b=3; a*b=15`

### Paradigm Mismatch

Using wrong compression paradigm for task type reduces both efficiency and
accuracy.

WRONG: Expert Lexicons for simple arithmetic
RIGHT: Chunked Symbolism for math; Conceptual Chaining for multi-hop

### Ignoring Model Self-Awareness

Models can estimate their own complexity bounds. Ignoring this leads to
suboptimal budgets.

WRONG: Fixed 50-token budget for all problems
RIGHT: Let model estimate appropriate budget per problem (TALE-EP)

### The Overcomplexity Trap

Increasing reasoning steps beyond the optimal count degrades performance. Per
Chen et al. (2024): "the model performance first increases and then decreases
with the increasing number of CCoT steps."

```
# PROBLEMATIC
"Let's break this into 20 detailed steps..."
[Model produces excessive steps, accuracy drops]
```

Per Chen et al. (2024), there exists an optimal step count for each problem
complexity. Beyond this threshold, additional steps introduce noise and planning
overhead that hurts accuracy.

```
# BETTER
Use MARP: maximize computation per step, minimize total steps
"Solve in the fewest steps that stay within calculation limits"
```

### The Decomposition Trap

Decomposing problems into sub-questions (Least-to-Most style) doesn't always
reduce token cost or improve accuracy. Per Chen et al. (2024): "Although the
pressure of local planning has been reduced, Least-to-Most has not effectively
reduced the pressure of global planning, nor the pressure of optimization
calculations."

```
# PROBLEMATIC
"Break this into sub-questions: Q1, Q2, Q3..."
[Total planning overhead increases; no token savings]
```

Decomposition releases local planning pressure but increases global planning
pressure. For compression, prefer MARP (maximizing per-step computation) over
Least-to-Most (maximizing sub-question count).

```
# BETTER
Use MARP: combine operations into fewer, denser steps
"Solve each step with maximum calculation, minimum steps"
```

---

## Research Citations

- Chen, Y., et al. (2024). "Unlocking the Capabilities of Thought: A Reasoning
  Boundary Framework to Quantify and Optimize Chain-of-Thought." arXiv.
- Han, T., et al. (2025). "Token-Budget-Aware LLM Reasoning." arXiv.
- Nayab, S., et al. (2024). "Concise Thoughts: Impact of Output Length on LLM
  Reasoning and Cost." arXiv.
- Renze, M. (2024). "The Benefits of a Concise Chain of Thought on
  Problem-Solving in Large Language Models." arXiv.
- Thawakar, O., et al. (2025). "Sketch-of-Thought: Efficient LLM Reasoning with
  Adaptive Cognitive-Inspired Sketching." arXiv.
- Xu, S., et al. (2025). "Chain of Draft: Thinking Faster by Writing Less."
  arXiv.
