# Prompt Engineer

Prompts are code. They have bugs, edge cases, and failure modes. This skill
treats prompt optimization as a systematic discipline -- analyzing issues,
applying documented patterns, and proposing changes with explicit rationale.

I use this on my own workflow. The skill was optimized using itself -- of
course.

## When to Use

- A sub-agent definition that misbehaves (agents/developer.md)
- A Python script with embedded prompts that underperform
  (skills/scripts/skills/planner/orchestrator/planner.py)
- A multi-prompt workflow that produces inconsistent results
- Any prompt that does not do what you intended

## How It Works

The skill:

1. Reads prompt engineering pattern references
2. Analyzes the target prompt for issues
3. Proposes changes with explicit pattern attribution
4. Waits for approval before applying changes
5. Presents optimized result with self-verification

I use recitation and careful output ordering to ground the skill in the
referenced patterns. This prevents the model from inventing techniques.

## Example Usage

Optimize a sub-agent:

```
Use your prompt engineer skill to optimize the system prompt for
the following claude code sub-agent: agents/developer.md
```

Optimize a multi-prompt workflow:

```
Consider @skills/scripts/skills/planner/orchestrator/planner.py. Identify all prompts,
understand how they interact, then use your prompt engineer skill
to optimize each.
```

## Example Output

Each proposed change includes scope, problem, technique, before/after, and
rationale. A single invocation may propose many changes. The change format the
skill prints is in the plan step's output:

```
uv run --directory <scripts> python -m skills.prompt_engineer.optimize --step 4 --scope single-prompt
```

`<scripts>` is the absolute path of the `skills/scripts` install.

## Caveat

When you tell an LLM "find problems and opportunities for optimization", it will
find problems. That is what you asked it to do. Some may not be real issues.

I recommend invoking the skill multiple times on challenging prompts, but
recognize when it is good enough and stop. Diminishing returns are real.
