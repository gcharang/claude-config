# Efficiency and Compression Techniques

Efficiency techniques address scenarios where LLM inference costs become prohibitive --
verbose chain-of-thought traces consuming excessive tokens, long prompts increasing
latency, or batching requirements for high-volume applications. These techniques trade
some reasoning depth for reduced computational overhead. Use them when token costs or
latency are primary concerns, when problems are simple enough to not require full
reasoning elaboration, or when operating at scale where per-request costs compound.

## Output Compression Techniques

### Concise Chain-of-Thought (CCoT)

**Mechanism**: Append "Be concise" to standard CoT prompt; optionally provide concise
few-shot examples.

**When to use**: Default CoT responses are unnecessarily verbose; per-token costs are a
concern; problems do not require elaborate mathematical reasoning.

**Implementation**: Add instruction "Be concise" after "think step-by-step". Provide
one-shot example with abbreviated reasoning. Works best with larger models (GPT-4 class);
smaller models may suffer accuracy loss on math problems (~28% degradation on GPT-3.5 for
math).

**Tradeoffs**: 48% token reduction with negligible accuracy impact on most tasks. Math
problems on smaller models show significant accuracy loss. No additional API calls.

---

### Chain of Draft (CoD)

**Mechanism**: Instruct model to limit each reasoning step to 5 words maximum, mimicking
human shorthand notes.

**When to use**: Reasoning tasks where abbreviated notation suffices (arithmetic,
symbolic reasoning, commonsense); latency is critical; standard CoT produces
92%+ excess tokens.

**Implementation**: Prompt: "Think step by step, but only keep a minimum draft for each
thinking step, with 5 words at most." Requires few-shot examples demonstrating the
condensed format. Example output: "20 - x = 12; x = 8" instead of paragraph explanation.

**Tradeoffs**: 76-92% token reduction. Requires few-shot examples (degrades significantly
in zero-shot). Performance gap widens on small models (<3B). Maintains accuracy on
arithmetic, commonsense, and symbolic tasks.

---

### Constrained-CoT (CCoT) with Word Limits

**Mechanism**: Explicitly request maximum word/token count in prompt: "limit the length
of the answer to N words."

**When to use**: Need predictable generation times; real-time systems with latency
constraints; large models (70B+) that can follow length constraints reliably.

**Implementation**: Append length constraint after CoT instruction. Test with varying
limits (15, 30, 45, 60, 100 words). Larger models (Llama2-70b) can improve accuracy
while reducing length; smaller models often fail to respect constraints or lose accuracy.

**Tradeoffs**: 21-28% token reduction. Large models may gain accuracy through forced
conciseness. Small/medium models (<13B) often cannot follow constraints reliably. Requires
tuning optimal word limit per task.

---

### Token-Budget-Aware Reasoning (TALE)

**Mechanism**: Dynamically estimate required tokens per problem, then include budget in
prompt: "use less than N tokens."

**When to use**: Problem difficulty varies significantly; want adaptive compression rather
than fixed limits; willing to trade one extra API call for better budget estimation.

**Implementation**: TALE-EP: First call estimates budget from problem complexity
(zero-shot), second call reasons within budget. TALE-PT: Fine-tune model to internalize
budget awareness. Token elasticity phenomenon: too-small budgets cause models to exceed
limits dramatically.

**Tradeoffs**: 67% token reduction with <3% accuracy loss. Requires extra API call for
budget estimation. Models struggle with unreasonably small budgets. Post-training version
(TALE-PT) eliminates extra call but requires fine-tuning access.

---

### Sketch-of-Thought (SoT)

**Mechanism**: Route problems to one of three cognitively-inspired paradigms: Conceptual
Chaining (arrows between concepts), Chunked Symbolism (mathematical notation), or Expert
Lexicons (domain abbreviations).

**When to use**: Multi-domain reasoning with distinct problem types; want structured
compression with interpretable intermediate steps; can afford lightweight routing model.

**Implementation**: Train DistilBERT router on 14K samples to classify incoming queries.
Conceptual Chaining: "#Seoul -> #South Korea -> Won". Chunked Symbolism: "a = 2.5, vi = 15,
vf = vi + a\*t = 40". Expert Lexicons: "STEMI -> MONA -> Aspirin in MONA".

**Tradeoffs**: Up to 84% token reduction. Requires training router model. Performance
varies by paradigm-task alignment. Generalizes to multilingual/multimodal with adapted
exemplars.

---

### Focused Chain-of-Thought (F-CoT)

**Mechanism**: Separate information extraction from reasoning -- first extract structured
context (XML format), then reason only over that context.

**When to use**: Input contains irrelevant narrative details; verbose word problems;
model tends to overthink; want interpretable intermediate representation.

**Implementation**: Stage 1: Extract facts into `<info_1>`, `<info_2>`, `<question>` blocks.
Stage 2: Reason exclusively over structured context with explicit citations. Can use
larger model for extraction, smaller for reasoning.

**Tradeoffs**: 2-3x token reduction. Extraction stage may lose subtle information.
Reasoning quality depends on extraction accuracy. Smaller models struggle with
self-extraction; hybrid pipeline recommended.

---

### Compressed Chain of Thought (CCoT - Continuous)

**Mechanism**: Generate continuous contemplation tokens that compress reasoning chains
into dense vector representations.

**When to use**: Have fine-tuning access; want maximum compression; can tolerate
interpretability loss; need adaptive compression at inference.

**Implementation**: Train module to approximate subset of full CoT hidden states. Use
intermediate layer (l ~ L/2) for autoregressive token generation. Variable compression
ratio (5-10% of original) controlled at training time.

**Tradeoffs**: 10x speedup possible. Requires LoRA fine-tuning. Loses explicit reasoning
trace interpretability. Accuracy plateaus around 20% compression ratio due to
approximation error propagation.

---

### ASAP (Anchor-guided, Surprisal-based Pruning)

**Mechanism**: Two-stage CoT compression: (1) prune structural redundancy via alignment
with "direct thought" anchor, (2) prune logical redundancy by retaining high
first-token-surprisal steps.

**When to use**: Working with long reasoning traces from Large Reasoning Models (R1-class);
need both structural and logical compression; have compute for offline preprocessing.

**Implementation**: Generate concise "direct thought" from (question, answer) pair. Pattern-match
original CoT steps against anchor. Compute surprisal of first token per step; iteratively
remove lowest-surprisal steps until budget met. Fine-tune on pruned CoTs.

**Tradeoffs**: 75% training token reduction, 60% training time reduction. 23% inference
token reduction with accuracy improvements. Requires offline preprocessing pipeline.
First-token surprisal outperforms perplexity for logical importance.

## Input Compression Techniques

### Batch Prompting

**Mechanism**: Group multiple samples in single prompt; model generates all responses in
one API call.

**When to use**: High-volume inference with similar problem types; few-shot prompting
where exemplars dominate token cost; batch size 2-6 samples optimal.

**Implementation**: Group K few-shot exemplars into K/b batches. Append b test samples.
Add position identifiers "[1]", "[2]" for response parsing. Token efficiency scales as
b/(K+b) versus 1/(K+1) for standard prompting.

**Tradeoffs**: Up to 5x cost reduction (6 samples/batch). Performance degrades with
batch size >6. Long input contexts degrade batch performance more. Task complexity
affects optimal batch size.

---

### System 2 Attention (S2A)

**Mechanism**: Regenerate input context to remove irrelevant/opinion content before
reasoning.

**When to use**: Context contains distractor information; sycophancy concerns; irrelevant
sentences in math word problems; opinion-laden queries.

**Implementation**: Two-step process: (1) Prompt model to regenerate only relevant
context portions, (2) Reason over regenerated context. Variants: with/without
question-context separation, keep-original for safety.

**Tradeoffs**: Doubles API calls. 18% accuracy improvement on distractor-heavy tasks.
Requires context to be regenerable (fails on very long contexts). Increases factuality,
decreases sycophancy.

---

### State-Update Multi-turn Dialogue

**Mechanism**: Replace linear history concatenation with state reconstruction -- inject
only previously-identified key information into each turn.

**When to use**: Long multi-turn dialogues; information filtering tasks; model suffers
"lost in the middle" phenomenon; token costs compound across turns.

**Implementation**: Each turn: provide new passage + "Previously selected: [prior key info]".
Use XML tags (`<info>`) for structured output. Parse model output, carry forward as
explicit history reminder.

**Tradeoffs**: 59% token reduction, 73% latency reduction. Requires structured output
parsing. Mitigates recency bias/forgetting. Both State Reconstruction and History Reminder
components essential.

---

### Behavior-Equivalent Token (BE Token)

**Mechanism**: Train single token to replace entire system prompt while preserving
downstream behavior.

**When to use**: Long system prompts (500-3000 tokens); prompt is fixed across many
queries; have fine-tuning access; single-turn interactions.

**Implementation**: Three-stage training: (1) Train universal [AE] trigger for text
reconstruction, (2) Train prompt-specific [BE] to reconstruct prompt via [AE],
(3) Distill behavioral alignment via KD from full-prompt teacher. Lambda=0.9 balances
reconstruction vs behavior.

**Tradeoffs**: 3000x prompt compression. 98% downstream performance retained. Requires
per-prompt training. Single-turn only. 28-59% TTFT reduction depending on prompt length.

## Theoretical Framework

### Token Complexity

**Mechanism**: Each problem has intrinsic minimum tokens required for solution --
performance exhibits sharp threshold at this complexity.

**When to use**: Evaluating compression strategies; understanding accuracy-length
tradeoffs; designing adaptive systems; benchmarking new methods.

**Implementation**: Estimate complexity by finding threshold where accuracy transitions
from 0 to 1 across compression levels. Universal tradeoff curve exists: all reasonable
compression prompts lie on same Pareto frontier.

**Tradeoffs**: Optimal compression requires knowing per-problem complexity. Current
prompt methods far from theoretical limit (3-11x gap). Verifier-based routing approaches
theoretical bound but requires accurate verifier.

## Decision Guidance

**Problem: Output too verbose, simple tasks**

- Start with CCoT ("be concise") -- zero implementation cost
- If still verbose, try Chain of Draft with few-shot examples
- For math/arithmetic: Chunked Symbolism from SoT

**Problem: Variable difficulty, want adaptive compression**

- TALE-EP for prompt-based estimation
- F-CoT if problems have extractable structure
- Token complexity framework for understanding limits

**Problem: High-volume batch processing**

- Batch Prompting for 2-6 samples per call
- BE Token if system prompt is long and fixed

**Problem: Long multi-turn conversations**

- State-Update Dialogue strategy
- Compress context between turns, not within

**Problem: Noisy/distractor-heavy context**

- S2A for context regeneration
- F-CoT for structured extraction

**Problem: Maximum compression needed, have fine-tuning**

- ASAP for training data compression
- Compressed CoT for continuous representations
- TALE-PT for internalized budget awareness

## Composability Notes

**Combine well:**

- Batch Prompting + any output compression (CCoT, CoD)
- F-CoT extraction + CoD reasoning
- S2A context cleaning + subsequent reasoning technique
- TALE budget estimation + any constrained generation

**Avoid combining:**

- Multiple output compression instructions (conflicting constraints)
- Continuous compression (CCoT) + interpretability requirements
- Heavy compression + small models (<7B parameters)
- Token limits + complex mathematical reasoning

**Synergies:**

- Structured input (F-CoT) naturally produces shorter outputs without explicit constraint
- S2A + standard CoT often outperforms compressed CoT on distractor tasks
- Batch Prompting efficiency gains compound with any per-sample compression
