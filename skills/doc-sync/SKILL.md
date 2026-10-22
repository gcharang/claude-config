---
name: doc-sync
description: Synchronizes docs across a repository. Use when user asks to sync docs.
---

# Doc Sync

Maintains the CLAUDE.md navigation hierarchy and README.md invisible knowledge
docs across a repository. The skill has no script: you do the documentation
work directly, against the format specification below.

## Documentation Conventions

For authoritative CLAUDE.md and README.md format specification:

<file working-dir=".claude" uri="conventions/documentation.md" />

The conventions/ directory contains all universal documentation standards.

## Scope Resolution

Determine scope FIRST:

| User Request                                            | Scope                                     |
| ------------------------------------------------------- | ----------------------------------------- |
| "sync docs" / "update documentation" / no specific path | REPOSITORY-WIDE                           |
| "sync docs in src/validator/"                           | DIRECTORY: src/validator/ and descendants |
| "update CLAUDE.md for parser.py"                        | FILE: single file's parent directory      |

For REPOSITORY-WIDE scope, perform a full audit. For narrower scopes, operate only within the specified boundary.

## Workflow

### Phase 1: Discovery

Map directories requiring CLAUDE.md verification:

```bash
# Directories holding tracked or new non-ignored files, with every ancestor
git -c core.quotePath=false ls-files --cached --others --exclude-standard | awk -F/ '{p="."; for (i=1;i<NF;i++) {p=p"/"$i; print p}} END {print "."}' | sort -u
```

Outside a git repository:

```bash
find . -type d \( -name .git -o -name node_modules -o -name vendor -o -name third_party -o -name __pycache__ -o -name .venv -o -name target -o -name dist -o -name build -o -name .idea -o -name .vscode \) -prune -o -type d -print
```

For each directory in scope, record:

1. Does CLAUDE.md exist?
2. If yes, does it have the required table-based index structure?
3. Which subdirectories and entry-point files need a row (conventions/documentation.md)?

### Phase 2: Audit

For each directory, check for drift and misplaced content:

- Missing from index: subdirectories and entry-point files with no row
- Stale in index: rows that name a deleted path
- Triggers: task-oriented, or vague or descriptive (see Anti-Patterns)
- Misplaced content: architecture or design prose that belongs in README.md
- README.md: whether one exists, and whether the directory meets the README.md
  Creation Criteria in conventions/documentation.md

### Phase 3: Content Migration

CLAUDE.md holds navigation and operational commands; README.md holds explanation. For each block in a CLAUDE.md, ask whether it explains WHY or tells HOW:

- Explanatory content - architecture, component interactions, design decisions, invariants and constraints, rationale, and any overview or purpose prose longer than one sentence - moves to README.md.
- Operational content - copy-pasteable build, test, regenerate or deploy commands for this directory - stays in CLAUDE.md.

Migration process:

1. Identify misplaced content in CLAUDE.md
2. Create or update README.md with the architectural content
3. Strip CLAUDE.md down to pure index format
4. Add README.md to the CLAUDE.md index table

### Phase 4: Index Updates

For each directory needing work:

**Creating/Updating CLAUDE.md:**

1. Use the appropriate template (ROOT or SUBDIRECTORY)
2. Populate tables with the subdirectories and entry-point files
3. Write "What" column: factual content description
4. Write "When to read" column: action-oriented triggers
5. If README.md exists, include it in the Files table

**Creating README.md:**

1. Confirm the directory meets the README.md Creation Criteria in conventions/documentation.md (a semantic trigger, not a structural one)
2. Document architecture, design decisions, invariants, tradeoffs
3. Apply the content test: remove anything visible from code
4. Keep as concise as possible while capturing all of that knowledge
5. Must be self-contained (conventions/documentation.md)

### Phase 5: Verification

After all updates complete, verify:

1. Every directory in scope has CLAUDE.md
2. All CLAUDE.md files use table-based index format (pure navigation)
3. No drift remains: every subdirectory and entry-point file has a row, and no row names a deleted path
4. No misplaced content in CLAUDE.md (explanatory prose moved to README.md)
5. README.md files are indexed in their parent CLAUDE.md
6. CLAUDE.md contains only: one-sentence overview + tabular index + operational sections
7. README.md exists in every directory that meets the README.md Creation Criteria
8. README.md files are self-contained (outside sources summarized, repository files pointed at)

## Output Format

```
## Doc Sync Report

### Scope: [REPOSITORY-WIDE | directory path]

### Changes Made
- CREATED: [list of new CLAUDE.md files]
- UPDATED: [list of modified CLAUDE.md files]
- MIGRATED: [list of content moved from CLAUDE.md to README.md]
- CREATED: [list of new README.md files]
- FLAGGED: [any issues requiring human decision]

### Verification
- Directories audited: [count]
- CLAUDE.md coverage: [count]/[total]
- CLAUDE.md format: [count] pure index / [count] needed migration
- Drift detected: [count] entries fixed
- Content migrations: [count] (prose moved to README.md)
- README.md files: [count]
- Self-contained: [YES/NO] (outside sources summarized, repository files pointed at)
```

## Exclusions

DO NOT create CLAUDE.md for:

- Generated files directories (dist/, build/, compiled outputs)
- Vendored dependencies (node_modules/, vendor/, third_party/)
- Git internals (.git/)
- IDE/editor configs (.idea/, .vscode/ unless project-specific settings)
- **Stub directories** (contain only `.gitkeep` or no code files) - these do not
  require CLAUDE.md until code is added

DO NOT index (skip these files in CLAUDE.md):

- Generated or vendored files inside a directory whose own row already flags it as generated or vendored

DO index:

Every subdirectory, and the entry-point files conventions/documentation.md (`### Index Format`) defines.

## Anti-Patterns

### Index Anti-Patterns

**Too vague (matches everything):**

```markdown
| `config/` | Configuration | Working with configuration |
```

**Content description instead of trigger:**

```markdown
| `cache.rs` | Contains the LRU cache implementation | - |
```

**Missing action verb:**

```markdown
| `parser.py` | Input parsing | Input parsing and format handling |
```

### Correct Examples

```markdown
| `cache.rs` | LRU cache with O(1) get/set | Implementing caching, debugging misses, tuning eviction |
| `config/` | YAML config parsing, env overrides | Adding config options, changing defaults, debugging config loading |
```

## When NOT to Use This Skill

- Single file documentation (inline comments, docstrings) - handle directly
- Code comments - handle directly
- Function/module docstrings - handle directly
- This skill is for CLAUDE.md/README.md synchronization specifically

## Reference

For additional trigger pattern examples, see `references/trigger-patterns.md`.
