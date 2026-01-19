# Sampling and Aggregation Techniques

## Overview

Sampling and aggregation techniques improve LLM accuracy by generating multiple
reasoning paths or outputs and combining them through voting, ranking, or
synthesis. Use these techniques when: (1) a single model output is unreliable or
inconsistent, (2) the task admits multiple valid solution paths, (3) you need
higher confidence in answers, or (4) the problem requires exploration of
alternatives. These methods trade increased compute cost for improved accuracy
and are most valuable for complex reasoning tasks where correct solutions
converge despite diverse reasoning paths.

---

## Techniques

### Self-Consistency

**Mechanism:** Sample multiple diverse reasoning paths via temperature-based
decoding, then select the most consistent final answer by majority vote.

**Triggers:**

- Complex reasoning admits multiple valid solution paths
- Arithmetic or mathematical problem solving
- Tasks where correct reasoning converges to same answer
- Model reasoning is partially reliable but inconsistent
- Answer must be from fixed answer set or easily parseable

**Tradeoffs:**

- Token overhead: 40x tokens (recommended 5-40 paths)
- API calls: k independent sampling calls (typically 5-40)
- Requirements: Few-shot CoT examples, temperature-based sampling enabled
- Gains: GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2% over greedy CoT

---

### Tree of Thoughts (ToT)

**Mechanism:** Explores multiple reasoning paths via tree search with LM-based
thought generation and self-evaluation; supports BFS/DFS with backtracking.

**Triggers:**

- Task requires exploration of multiple solution paths
- Initial decisions are pivotal and hard to reverse
- Task requires strategic lookahead or backtracking
- Left-to-right decoding fails frequently at early steps
- Creative tasks requiring high-level planning before execution

**Tradeoffs:**

- Token overhead: 5-100x tokens vs CoT
- API calls: Adaptive (BFS keeps top-b states per step; DFS explores until
  pruning)
- Requirements: Few-shot examples for thought generation, search algorithm,
  state evaluation prompts
- Gains: Game of 24: 74% vs CoT 4%; Creative Writing: 7.56 vs CoT 6.93

---

### Diversity of Thought (Div-Se / IDiv-Se)

**Mechanism:** Solicit LLM to generate multiple high-level reasoning approaches,
augment few-shot examples per approach, ensemble across diverse prompts via
majority vote.

**Triggers:**

- Complex multi-step reasoning requiring diverse solution strategies
- Math problems solvable via multiple approaches (algebra, visualization,
  elimination)
- Problems where token-level diversity fails to ensure methodological diversity
- Tasks where baseline CoT and self-consistency plateau

**Tradeoffs:**

- Token overhead: Div-Se: 3-5x tokens (k separate calls); IDiv-Se: 1.5-2x tokens
  (single call)
- API calls: Div-Se: k calls (k=3 or 5); IDiv-Se: 1 call
- Requirements: LLM feedback for approach generation, few-shot example
  augmentation
- Gains: AQuA-RAT +16.52pp, Blocksworld 4/5 +29.6pp, Graph Coloring +82pp (GPT-4
  ZS)

---

### Multi-Chain Reasoning (MCR)

**Mechanism:** LLM meta-reasons over multiple CoT chains to combine facts and
generate unified explanation rather than simple majority voting.

**Triggers:**

- Multi-hop questions requiring multiple reasoning steps
- Questions where individual CoT chains contain partial but incomplete
  information
- Tasks requiring fact composition across multiple reasoning paths
- Problems where majority voting fails due to large output space

**Tradeoffs:**

- Token overhead: 5x tokens (1 greedy + 4 sampled chains + meta-reasoner)
- API calls: 6 total calls (5 decomposition chains + 1 meta-reasoner)
- Requirements: Few-shot examples for decomposition and meta-reasoner, retrieval
  system
- Gains: Beats self-consistency by +0.6% to +5.7% across 7 multi-hop QA datasets

---

### Complexity-Based Prompting

**Mechanism:** Select few-shot examples with more reasoning steps and vote among
complex generated chains over simple ones.

**Triggers:**

- Multi-step reasoning problems with intermediate steps
- Math word problems requiring sequential calculations
- Problems where reasoning complexity varies significantly
- When avoiding spurious reasoning shortcuts is critical

**Tradeoffs:**

- Token overhead: 3-4x tokens (complex prompts ~9 steps vs simple ~3 steps)
- API calls: 50 samples for voting, select top K=30-40 complex chains
- Requirements: Annotated reasoning chains for 8 few-shot examples, large model
  (>100B parameters)
- Gains: +5.3 avg accuracy, up to +18 on MathQA with GPT-3/Codex

---

### Boosted Prompt Ensembles

**Mechanism:** Iteratively construct few-shot prompts by selecting hard examples
where current ensemble shows disagreement.

**Triggers:**

- Multi-step reasoning with current prompt showing high variance
- Small labeled dataset available (50-300 samples) for train-time boosting
- Initial prompt suboptimal or distribution shift between train and test
- Problems where single prompt fails systematically on specific subtypes

**Tradeoffs:**

- Token overhead: n x m tokens (e.g., 10 prompts x 10 samples = 100x baseline)
- API calls: n x m calls per test question
- Requirements: Small training set, chain-of-thought generation,
  self-consistency sampling
- Gains: GSM8K: 85.2% vs 83.5% (SC); AQUA: 63.5% vs 57% (SC)

---

### Multi-Perspective Self-Consistency (MPSC)

**Mechanism:** Generate solutions, specifications, and test cases, then rank by
consistency using 3-partite graph optimization.

**Triggers:**

- Code generation tasks where single-attempt accuracy is insufficient
- Programming problems requiring multiple verification perspectives
- Tasks with executable test cases and verifiable specifications
- Scenarios where inter-consistency between code artifacts can be measured

**Tradeoffs:**

- Token overhead: ~3.5x tokens (200 solutions + 50 specs + 100 test cases)
- API calls: 350 independent calls per problem
- Requirements: Code execution environment, few-shot examples for each
  perspective
- Gains: GPT-3.5: +15.91% HumanEval, +15.64% HumanEval+, +6.43% MBPP

---

### PREFER (Prompt Ensemble Learning via Feedback-Reflect-Refine)

**Mechanism:** Iteratively generates diverse prompts via feedback on errors,
reflection, and refinement, then ensembles with adaptive weights.

**Triggers:**

- Task requires high accuracy and stability across diverse inputs
- Single prompts show high variance or hallucination issues
- Hard examples exist that individual prompts fail to solve
- Manual prompt engineering is too costly or suboptimal

**Tradeoffs:**

- Token overhead: k iterations with k prompts: k \* (2-5 iterations) \* 2x
  tokens
- API calls: 2k calls for training, k calls for inference
- Requirements: Training dataset for error feedback, multiple boosting
  iterations
- Gains: Outperforms single prompts by 6.3-13.1%, APO by significant margins

---

### Refined Answer Distributions (RAD)

**Mechanism:** Iteratively refine answer distributions by marginalizing over
previous answers, weighting refinements by estimated probability of each answer.

**Triggers:**

- Reasoning tasks where self-consistency plateaus after few samples
- Problems where providing hints helps LLMs verify/refine answers
- Multi-step reasoning requiring answer distribution refinement
- Tasks where probability flow into correct answer exceeds flow out

**Tradeoffs:**

- Token overhead: 2-3x tokens compared to CoT+SC
- API calls: 40 total samples across 2-3 iterations (e.g., B1=5, B2=15, B3=20)
- Requirements: Few-shot examples, hint-based refinement strategy
- Gains: Outperforms Self-Consistency in 30/36 scenarios; +2-5% on arithmetic

---

### Dipper (Diverse Prompt Ensembles)

**Mechanism:** Feed a single LLM multiple diverse reasoning prompts in parallel,
aggregate responses via voting or best-of-N selection.

**Triggers:**

- Complex reasoning tasks where smaller LLMs struggle
- Resource-constrained settings where scaling model size is impractical
- Tasks where diverse reasoning approaches could yield different valid paths
- Need performance boost without model training or fine-tuning

**Tradeoffs:**

- Token overhead: n times base cost where n is ensemble size (3-9 typical)
- API calls: n parallel calls per query
- Requirements: Parallel batch inference, prompt generation, sentence embedding
  for diversity optimization
- Gains: 3x Qwen2-MATH-1.5B outperforms single Qwen2-MATH-7B; ~10pp over single
  model

---

### Self-ICL

**Mechanism:** LLM generates pseudo-inputs and pseudo-labels from test query,
then uses them as ICL demonstrations for zero-shot scenarios.

**Triggers:**

- No access to training dataset or demonstration pool
- End-user query without example corpus
- Zero-shot setting where few-shot would help
- Challenging unexpected tasks without existing demonstrations

**Tradeoffs:**

- Token overhead: 3-5x tokens
- API calls: k+2 calls (1 for pseudo-inputs, k for pseudo-labels, 1 for final)
- Requirements: Instruction-following model, zero-shot capability essential
- Gains: 18-0-5 win-tie-lose vs zero-shot direct; comparable to real 3-shot ICL

---

### Jekyll & Hyde (Persona-Neutral Ensemble)

**Mechanism:** Ensemble role-playing and neutral perspectives, selecting better
solution via LLM evaluator with position bias mitigation.

**Triggers:**

- Role-playing prompts may introduce bias for the given question
- Uncertain whether persona assignment will help or hurt performance
- Task requires balancing domain expertise with general reasoning
- Need robustness against persona-induced confusion

**Tradeoffs:**

- Token overhead: 3-5x tokens (persona generator + dual solvers + evaluator)
- API calls: 3.81 avg calls (1 persona gen + 2 solvers + 1.81 evaluator)
- Requirements: LLM for persona generation, LLM for evaluation, consistency
  verification
- Gains: 9.98% avg improvement over best single-perspective baseline (GPT-4)

---

### Ordered Prompts (Entropy-Based Selection)

**Mechanism:** Rank few-shot example orderings using entropy metrics on
model-generated probing set to select performant permutations.

**Triggers:**

- Few-shot in-context learning with 3-8 examples where order matters
- High variance observed across different example orderings
- No labeled development set available for permutation selection
- True few-shot setting where additional annotated data is unavailable

**Tradeoffs:**

- Token overhead: n! permutations for probing (24x for 4-shot)
- API calls: n! calls for probing generation + n! calls for evaluation
- Requirements: Few-shot examples, generative model for probing set
- Gains: 13% average relative improvement using GlobalE across 11 tasks

---

### PEDAL (Diverse Exemplars with Greedy Decoding)

**Mechanism:** Generate multiple greedy outputs using diverse exemplar sets,
then aggregate with LLM-based selection.

**Triggers:**

- Need better accuracy than greedy decoding with lower cost than
  self-consistency
- Math word problems or multiple-choice reasoning tasks
- Tasks where diverse exemplars can induce output variation
- Cost-sensitive deployments where output token count matters

**Tradeoffs:**

- Token overhead: 1.5x input tokens, 0.4x output tokens vs Self-Consistency
- API calls: k+1 calls (k diverse prompts + 1 aggregation)
- Requirements: Few-shot examples, k diverse exemplar sets (typically 3-4)
- Gains: 1.89-3.89% accuracy improvement over greedy; 60-80% fewer output tokens

---

### Synthetic Prompting

**Mechanism:** LLM generates additional demonstrations via backward question
synthesis and forward reasoning refinement from seed examples.

**Triggers:**

- Only 2-4 seed examples available for complex reasoning tasks
- Need diverse demonstrations but manual annotation is costly
- Existing demonstrations are too simple for target task complexity
- Task requires complex multi-step reasoning chains

**Tradeoffs:**

- Token overhead: 1000x synthesis calls + 3x forward sampling per synthetic
  example
- API calls: 1000 backward + 1000 forward calls for synthesis; 1 inference call
- Requirements: 2-8 seed examples with reasoning chains, clustering for
  selection
- Gains: Up to 15.6% absolute improvement over PaL prompting baseline

---

### Reprompting (Gibbs Sampling)

**Mechanism:** Iteratively samples and evolves CoT recipes through Gibbs
sampling with rejection to optimize few-shot prompts.

**Triggers:**

- Human-written CoT prompts unavailable or require costly engineering
- Need to optimize CoT prompts for specific model without human intervention
- Tasks requiring multi-step reasoning where initial zero-shot solutions vary
- Fair comparison needed across different LLMs with model-specific prompts

**Tradeoffs:**

- Token overhead: 10000x+ tokens during training phase
- API calls: Up to 20000 iterative sampling calls
- Requirements: Training question-answer pairs, iterative sampling budget
- Gains: +9.4 points over human-written CoT, +11-33 points over Auto-CoT/APO/SC

---

### Fairness-guided Few-shot Prompting

**Mechanism:** Select few-shot examples that minimize predictive bias by
maximizing entropy on content-free inputs.

**Triggers:**

- Few-shot prompting shows high variance across example selections
- Performance is sensitive to demonstration order
- Need to select optimal demonstrations without labeled dev set
- Classification tasks where bias can be measured

**Tradeoffs:**

- Token overhead: Standard few-shot tokens (no overhead at inference)
- API calls: O(N) for T-fair, O(N^2) for G-fair during search phase; 1 at
  inference
- Requirements: Pool of candidate demonstrations, content-free input
  construction
- Gains: 10%+ improvement over random selection on TREC

---

## Decision Guidance

| Scenario                              | Recommended Technique          | Reason                                 |
| ------------------------------------- | ------------------------------ | -------------------------------------- |
| Math/arithmetic with fixed answers    | Self-Consistency               | Simple, effective, well-understood     |
| Multi-hop QA with partial info        | Multi-Chain Reasoning          | Synthesizes across incomplete chains   |
| Creative/planning requiring lookahead | Tree of Thoughts               | Enables backtracking and exploration   |
| Method diversity more than token div  | Diversity of Thought           | Explicitly varies reasoning approaches |
| Code generation with verification     | Multi-Perspective SC           | Leverages executable test cases        |
| Zero-shot without examples            | Self-ICL                       | Self-generates demonstrations          |
| Prompt optimization without training  | Reprompting                    | Automated CoT discovery                |
| Cost-sensitive deployment             | PEDAL or IDiv-Se               | Lower token overhead than SC           |
| Persona uncertainty                   | Jekyll & Hyde                  | Mitigates persona-induced bias         |
| Few-shot order sensitivity            | Ordered Prompts or Fairness-FP | Reduces permutation variance           |
| Self-consistency plateau              | Refined Answer Distributions   | Iterative distribution refinement      |
| Small model, need big model perf      | Dipper                         | Ensemble of diverse prompts            |

---

## Composability Notes

**Foundation techniques:**

- Self-Consistency builds on Chain-of-Thought and is composed into most other
  techniques
- Tree of Thoughts extends both CoT and Self-Consistency with search

**Technique combinations:**

- Diversity of Thought + Self-Consistency: Use diverse approaches with sampling
  within each
- Tree of Thoughts + PREFER: Iteratively refine thought generation prompts
- Multi-Chain Reasoning + Complexity-Based: Prioritize complex chains in
  meta-reasoning
- Self-ICL + Self-Consistency: Sample multiple pseudo-demonstrations, then vote

**Aggregation methods:**

- Voting: Self-Consistency, Diversity of Thought, Dipper, Complexity-Based
- Ranking: Ordered Prompts, Multi-Perspective SC
- Synthesis: Multi-Chain Reasoning, PREFER, RAD
- Selection: Tree of Thoughts, PEDAL, Jekyll & Hyde

**Anti-patterns:**

- Avoid combining techniques with conflicting context strategies (isolated vs
  accumulated)
- Memory-requiring techniques (ToT, Boosted Ensembles, Reprompting) have higher
  state management overhead
- Most techniques require few-shot examples; Self-ICL and Dipper work zero-shot
