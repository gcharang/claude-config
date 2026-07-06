# Planner Resources

## Overview

Reference files for the planner. One is injected into a sub-agent prompt at
runtime; the rest are read by whoever edits the planner's structure.

## Loading mechanism

`plan-json-schema.md` is the authoritative plan.json (JSON-IR) schema. The
architect sub-agent loads it at runtime through
`PlannerResourceProvider.get_resource()` (`shared/resources.py`) during its
plan-writing step (`architect/plan_design_execute.py`, step 6) and injects it
into the prompt, so the agent emits schema-conformant JSON without an embedded
copy that could drift from the schema.

`plan-format.md` (human-readable plan-structure reference) and
`explore-output-format.md` (XML schema for exploration output) are NOT injected
— they are reference docs, read when editing the plan or exploration structure.

`get_resource(name)` is the single loader for runtime-injected resources; it
resolves `<deploy-root>/skills/planner/resources/<name>` (the repo tree under
`.claude/` once synced).
