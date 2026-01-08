# Solution Design

Ask an LLM for five solutions and you get one idea in five costumes. Add caching with Redis. Add caching with Memcached. Add caching with an in-memory store. The model anchored on its first thought and dressed it up.

This skill forces diversity by running separate agents in parallel, each reasoning from a different mode.

## When to Use

Use this when you have a defined problem and need to explore solution space. Defined is the key word. If you are still figuring out what the problem is, use problem-analysis first.

The skill adds value when:

- Multiple approaches could work, and choosing wrong has real cost
- You need to justify a decision to stakeholders
- The obvious solution feels too obvious

If the solution is clear -- add a button, fix a typo, implement a known pattern -- skip this and execute directly.

## How It Works

The skill defines seven reasoning perspectives:

- **Minimal**: What is the smallest change that addresses the root cause?
- **Structural**: What design change makes this class of problem impossible?
- **Stateless**: What if we eliminated or simplified state?
- **Domain**: What domain concept are we failing to represent?
- **Removal**: What if we removed something instead of adding?
- **First Principles**: What solution emerges if we ignore convention?
- **Upstream**: What if we solved this earlier in the causal chain?

For each problem, the skill selects 4-6 perspectives likely to produce distinct solutions. Each perspective dispatches as a separate sub-agent. The agents run in parallel -- this matters. A single agent cycling through perspectives compresses each one and anchors on earlier ideas. Parallel execution gives each mode full context to reason without contamination.

After collection, a synthesis step identifies where perspectives converge, where they conflict, and whether combining insights produces solutions none proposed individually. A challenge step stress-tests each solution. The output is a ranked list with trade-offs explicit.

## Usage

After problem-analysis:

```
Use your solution-design skill on the root cause from problem-analysis
```

Standalone:

```
Use your solution-design skill. Problem: [statement]
```

With constraints:

```
Use your solution-design skill. Problem: [statement]. Must complete in 2 days.
```

## Output

A ranked list of solutions with:

- Concrete specification (not "improve error handling" -- actual steps)
- Trade-offs made explicit
- Conditions under which each solution would fail
- A recommendation with rationale

The skill does not implement anything. It produces analysis for you to act on.

## Related Skills

**problem-analysis** identifies what the problem actually is. Use it first when the problem statement is vague.

**planner** turns a chosen solution into an executable plan. After solution-design recommends an approach, use the planner to implement it.
