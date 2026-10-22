# DeepThink

Structured multi-step reasoning for open-ended analytical questions. Handles
questions where the answer structure is itself unknown: taxonomy design,
conceptual analysis, trade-off exploration, definitional questions.

## When to Use

Use this when the question resists predefined frameworks:

- "What's the correct way to classify X?"
- "What makes a good Y?"
- "How should I balance A versus B?"
- "What does Z actually mean in our context?"

Do NOT use for:

- Problems with verifiable answers (math, coding with test cases)
- Problems requiring external data retrieval
- Known problem types (use problem-analysis)

## Workflow Phases

Two modes: Full dispatches parallel sub-agents; Quick synthesizes directly. Step 3
chooses the mode. `STATIC_STEPS` and `DYNAMIC_STEPS` in
`../scripts/skills/deepthink/think.py` define the steps, and `build_next_command`
routes between them.

## Invisible Knowledge

### Why Context Clarification First

LLM soft attention assigns probability to irrelevant context, causing factual
errors and sycophancy. Regenerating the input to extract only relevant,
unbiased portions prevents framing effects from contaminating downstream
reasoning.

### Why Abstraction Before Reasoning

Prompting for high-level concepts and first principles before addressing
specifics improves performance 7-27%. Abstraction moves UP to principles rather
than DOWN to subtasks -- distinct from decomposition.

### Why Self-Generated Analogies

Prompting to recall similar problems from training accesses parametric knowledge
that isn't retrieved without explicit prompting. Works better than providing
fixed examples because analogies are problem-specific.

### Why Factored Verification

LLMs that view their own synthesis when verifying tend to justify existing
conclusions rather than check them. Generating verification questions, then
answering each from a cited evidence source rather than from the synthesis's
wording, counters that. The draft stays in the same context, so this is an
approximation of factored verification, which answers in a separate context.
Short-form questions are more accurately answered than long-form queries.

### Why Actionable Feedback

Generic feedback ("could be stronger") fails to improve output. Feedback must
specify: ELEMENT (what), PROBLEM (why wrong), ACTION (how to fix). Changing from
actionable to generic drops performance 43.2 -> 31.2.

### Why Intermediate Insight Extraction

Multiple reasoning chains contain valuable intermediate steps even when final
conclusions are wrong. Extracting evidence from ALL chains, not just majority,
produces better synthesis than pure voting.

### Why Confidence Gates the Loop

The refinement step asks for a confidence level with a written justification; the script
reads that level to decide between another iteration and formatting, and the
iteration cap ends the loop when the level never reaches the exit.

### Why Iteration Cap

Analytical questions could theoretically continue forever. The cap (5
iterations) forces eventual termination while allowing sufficient depth. Balance
between shallow analysis and indefinite loops.

## Academic Grounding (Condensed)

| Pattern                  | Source                           | Key Insight                              |
| ------------------------ | -------------------------------- | ---------------------------------------- |
| Context Clarification    | S2A (Weston & Sukhbaatar, 2023)  | Regenerate input sans bias               |
| Step-Back Abstraction    | Zheng et al., ICLR 2024          | Principles before specifics: +7-27%      |
| Self-Generated Exemplars | Analogical (Yasunaga, ICLR 2024) | Own analogies beat provided examples     |
| Metacognitive Stages     | Wang & Zhao, NAACL 2024          | Five-stage evaluation: +26.9%            |
| Anti-Pattern Generation  | Contrastive CoT (Chia, 2023)     | Knowing what NOT to do: +10-16pts        |
| Parallel Perspectives    | Multi-Agent Debate (Du, ICML 24) | Diverse viewpoints beat single-agent     |
| Generate-Critique-Revise | Self-Refine (Madaan, NeurIPS 23) | Actionable feedback: +5-40%              |
| Factored Verification    | Chain-of-Verification (Meta, 23) | Independent verification: 17% -> 70%     |
| Complex Reasoning        | Complexity-Based (Fu, ICLR 2023) | More steps = better: +5.3-18%            |
| Intermediate Extraction  | MCR (Yoran, 2024)                | All chains have value, not just majority |

## Output Formats

Final output adapts to question type (determined in Step 3):

- **Taxonomy**: Structure + rationale + edge cases + alternatives rejected
- **Trade-off**: Dimensions + balance point + shift conditions + framework
- **Definitional**: Definition + boundaries + adjacent concepts + misunderstandings
- **Evaluative**: Criteria + assessment + confidence + change conditions
- **Exploratory**: Landscape + framework + promising directions + gaps

## Implementation Notes

Each step is rendered by `skills.lib.workflow.prompts.format_step`. Step 5's next
command follows the MODE chosen in Step 3. The refinement step carries `--iteration`, which
the script increments up to `MAX_ITERATIONS`.
