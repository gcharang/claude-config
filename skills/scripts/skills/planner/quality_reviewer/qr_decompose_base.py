"""Base class for QR decomposition scripts.

Definition locality + INTENT.md compliance:
- INTENT.md requires separate files per phase
- Base class provides shared logic
- Subclasses override phase-specific parts

Understanding decompose workflow: read THIS file.
Understanding plan-design checks: read plan_design_qr_decompose.py.

Decompose scripts separate from verify scripts:
- Single Responsibility: decomposition is analysis (identify checks), verification is judgment (pass/fail)
- Testability: decompose output is deterministic list; verify outcome depends on artifact quality
- Parallelization: one agent decomposes (sequential), N agents verify (parallel)
- Ownership: decompose runs first-time only; verify runs on each iteration

13-step cognitive workflow:
Steps 1-8: Core decomposition (analysis -> item generation)
  1. Absorb context - understand plan and phase objectives
  2. Holistic concerns - top-down brainstorming
  3. Structural enumeration - bottom-up element listing
  4. Gap analysis - compare top-down vs bottom-up
  5. Generate items - umbrella + specific pattern
  6. Atomicity check - split critical non-atomic items
  7. Coverage validation - verify completeness
  8. Finalize - write qr-{phase}.json

Steps 9-13: Grouping phases (batching for parallel verification)
  9. Structural grouping - parent-child and umbrella batching
  10. Component grouping - same structural element
  11. Concern grouping - same quality dimension
  12. Affinity grouping - semantic similarity
  13. Final validation - verify grouping quality

Invariants:
- Each item has unique id within phase
- All items status:TODO (verify agents mutate to PASS/FAIL)
- Item count is adaptive (content determines quantity, no fixed caps)
"""

from __future__ import annotations

import json
from pathlib import Path
from abc import ABC, abstractmethod

from skills.planner.shared.qr.phases import get_phase_config
from skills.planner.shared.resources import get_context_path, render_context_file
from skills.lib.workflow.ast import W, render, XMLRenderer, TextNode

# Total steps in decompose workflow: 8 core + 5 grouping
TOTAL_STEPS = 13


class DecomposeBase(ABC):
    """Base class for QR decomposition scripts.

    Subclasses must:
    1. Set PHASE class attribute
    2. Override get_enumeration_guidance() with phase-specific element listing
    """

    PHASE: str = None  # Override in subclass

    def __init__(self):
        if not self.PHASE:
            raise ValueError("Subclass must set PHASE class attribute")
        self.config = get_phase_config(self.PHASE)

    @abstractmethod
    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3.

        Tells the LLM what structural elements to enumerate for this phase.
        """
        raise NotImplementedError

    def get_artifact_prompt(self) -> str:
        """Return instructions for reading the artifact.

        Override in subclass if artifact reading needs special handling.
        """
        return f"Read {self.config['artifact']} from STATE_DIR."

    def _render_item_list(self, items: list[dict], label: str = "UNGROUPED ITEMS") -> str:
        """Render item list using AST ElementNode for structured LLM parsing.

        Uses W.el() to create XML structure that LLMs parse more reliably
        than free-form text. Each item becomes an <item> element with
        attributes for id/scope and text content for the check description.
        """
        if not items:
            return f"<{label.lower().replace(' ', '_')} count=\"0\" />"

        item_nodes = [
            W.el("item",
                 TextNode(i.get('check', '')[:80]),
                 id=i['id'],
                 scope=i.get('scope', '*')).node()
            for i in items
        ]
        list_node = W.el(label.lower().replace(' ', '_'), *item_nodes,
                         count=str(len(items))).build()
        return render(list_node, XMLRenderer())

    def _format_assign_cmd(self, state_dir: str, prefix: str) -> list[str]:
        """Format CLI command template as plain text lines.

        Matches existing step output pattern (plain indented text).
        Prefix determines namespace: component-, concern-, affinity-.
        """
        return [
            "OUTPUT:",
            f"  python3 -m skills.planner.cli.qr --state-dir {state_dir} --qr-phase {self.PHASE} \\",
            f"    assign-group <item_id> --group-id {prefix}<name>",
        ]

    def _load_ungrouped_todo_items(self, state_dir: str) -> list[dict]:
        """Load items with status='TODO' and no group_id assigned."""
        from skills.planner.shared.qr.utils import load_qr_state
        qr_state = load_qr_state(state_dir, self.PHASE)
        if not qr_state:
            return []
        return [i for i in qr_state.get("items", [])
                if i.get("group_id") is None and i.get("status") == "TODO"]

    def get_step_guidance(self, step: int, total_steps: int, module_path: str = None, **kwargs) -> dict:
        """Shared step handling for 13-step decomposition + grouping workflow.

        Steps 1-8: Core decomposition (analysis -> item generation)
        Steps 9-13: Grouping phases (structural -> component -> concern -> affinity -> validation)
        """
        state_dir = kwargs.get("state_dir", "")
        module_path = module_path or ""

        if step == 1:
            return self._step_1_absorb_context(state_dir, module_path, total_steps)
        elif step == 2:
            return self._step_2_holistic_concerns(state_dir, module_path, total_steps)
        elif step == 3:
            return self._step_3_structural_enumeration(state_dir, module_path, total_steps)
        elif step == 4:
            return self._step_4_gap_analysis(state_dir, module_path, total_steps)
        elif step == 5:
            return self._step_5_generate_items(state_dir, module_path, total_steps)
        elif step == 6:
            return self._step_6_atomicity_check(state_dir, module_path, total_steps)
        elif step == 7:
            return self._step_7_coverage_validation(state_dir, module_path, total_steps)
        elif step == 8:
            return self._step_8_finalize(state_dir, module_path, total_steps)
        elif step == 9:
            return self._step_9_structural_grouping(state_dir, module_path, total_steps)
        elif step == 10:
            return self._step_10_component_grouping(state_dir, module_path, total_steps)
        elif step == 11:
            return self._step_11_concern_grouping(state_dir, module_path, total_steps)
        elif step == 12:
            return self._step_12_affinity_grouping(state_dir, module_path, total_steps)
        elif step == 13:
            return self._step_13_final_validation(state_dir, module_path, total_steps)
        else:
            return {"error": f"Unknown step {step}"}

    def _step_1_absorb_context(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 1: Absorb context and understand objectives."""
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        context_display = render_context_file(get_context_path(state_dir)) if state_dir else ""

        return {
            "title": f"QR Decomposition Step 1/{total_steps}: Absorb Context ({self.PHASE})",
            "actions": [
                f"PHASE: {self.PHASE}",
                "",
                self.get_artifact_prompt(),
                "",
                "PLANNING CONTEXT:",
                context_display,
                "",
                "TASK: Read and understand. Summarize in 2-3 sentences:",
                "  - What is this plan trying to accomplish?",
                "  - What does success look like for this phase?",
                "",
                "DO NOT generate items yet. Understanding first.",
            ],
            "next": f"python3 -m {module_path} --step 2{state_dir_arg}",
        }

    def _step_2_holistic_concerns(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 2: Holistic concerns - top-down brainstorming."""
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""

        return {
            "title": f"QR Decomposition Step 2/{total_steps}: Holistic Concerns ({self.PHASE})",
            "actions": [
                "THINKING TOP-DOWN: If reviewing this phase output, what would you check?",
                "",
                "Brainstorm concerns freely. Include:",
                "  - High-level: Does the overall approach make sense?",
                "  - Cross-cutting: Consistency across elements, patterns, conventions",
                "  - Quality: Completeness, clarity, correctness",
                "  - Risks: What could go wrong that isn't obvious?",
                "",
                "OUTPUT: Bulleted list of concerns.",
                "  - Quantity over quality at this step",
                "  - No filtering yet - capture everything",
                "",
                "These concerns will drive umbrella items in Step 5.",
            ],
            "next": f"python3 -m {module_path} --step 3{state_dir_arg}",
        }

    def _step_3_structural_enumeration(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 3: Structural enumeration - bottom-up element listing."""
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        enum_guidance = self.get_enumeration_guidance()

        return {
            "title": f"QR Decomposition Step 3/{total_steps}: Structural Enumeration ({self.PHASE})",
            "actions": [
                "THINKING BOTTOM-UP: What EXISTS in the plan for this phase?",
                "",
                enum_guidance,
                "",
                "OUTPUT: Structured list of plan elements.",
                "  - Use IDs where available (DL-001, M-001, CC-001)",
                "  - Note counts (e.g., '3 decisions, 5 milestones')",
                "",
                "This enumeration becomes a completeness checklist in Step 7.",
            ],
            "next": f"python3 -m {module_path} --step 4{state_dir_arg}",
        }

    def _step_4_gap_analysis(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 4: Gap analysis - compare top-down vs bottom-up."""
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""

        return {
            "title": f"QR Decomposition Step 4/{total_steps}: Gap Analysis ({self.PHASE})",
            "actions": [
                "COMPARE Step 2 (holistic concerns) vs Step 3 (structural elements):",
                "",
                "For each CONCERN from Step 2:",
                "  - Is it addressed by verifying specific elements from Step 3?",
                "  - Or is it cross-cutting (spans multiple elements)?",
                "  - Or is it about something MISSING from the plan?",
                "",
                "For each ELEMENT from Step 3:",
                "  - Is there a concern from Step 2 that covers it?",
                "  - If not, what verification does this element need?",
                "",
                "OUTPUT:",
                "  - Concerns needing UMBRELLA items (cross-cutting)",
                "  - Concerns mapping to SPECIFIC elements",
                "  - Elements needing their own verification items",
                "  - GAPS: things neither approach caught",
            ],
            "next": f"python3 -m {module_path} --step 5{state_dir_arg}",
        }

    def _step_5_generate_items(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 5: Generate initial items using umbrella + specific pattern.

        D2: Umbrella + specific pattern is intentional. Overlapping coverage
        preferred over gaps. Critical concerns get BOTH umbrella (catch outliers)
        AND specific items (explicit verification). Do not "optimize" by removing
        perceived redundancy.

        D4: Severity assigned at decompose-time based on check category per
        conventions/severity.md. Verify agent focuses on pass/fail judgment only.
        """
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""

        return {
            "title": f"QR Decomposition Step 5/{total_steps}: Generate Initial Items ({self.PHASE})",
            "actions": [
                "CREATE verification items using the UMBRELLA + SPECIFIC pattern:",
                "",
                "WHY THIS PATTERN: Overlapping coverage catches outliers that specific",
                "items miss. This intentional redundancy is a feature, not waste.",
                "",
                "UMBRELLA ITEMS (scope: '*'):",
                "  - One per cross-cutting concern from Step 4",
                "  - Broad enough to catch outliers",
                "  - Example: 'Verify consistent error handling across all code_changes'",
                "",
                "SPECIFIC ITEMS (scope: element reference):",
                "  - One per element needing verification",
                "  - Targeted at specific element",
                "  - Example: 'Verify decision DL-001 has multi-step reasoning'",
                "",
                "CRITICAL CONCERNS get BOTH:",
                "  - Umbrella for broad coverage",
                "  - Specific items for high-priority instances",
                "  - Keep both even if they seem redundant",
                "",
                "FORMAT each item:",
                '  {"id": "qa-NNN", "scope": "...", "check": "...", "status": "TODO", "severity": "..."}',
                "",
                "SEVERITY ASSIGNMENT (per conventions/severity.md):",
                "  MUST: Knowledge loss risks",
                "    - Decision log missing/incomplete",
                "    - Policy defaults without Tier 1 backing",
                "    - IK transfer failures",
                "    - Temporal contamination in comments",
                "    - Baseline references to removed code",
                "  SHOULD: Structural debt",
                "    - God objects (>15 methods, >10 deps)",
                "    - God functions (>50 lines, >3 nesting)",
                "    - Convention violations",
                "    - Testing strategy violations",
                "  COULD: Cosmetic/auto-fixable",
                "    - Dead code",
                "    - Formatter-fixable issues",
                "    - Minor inconsistencies without documented rule",
                "    - Toolchain-catchable code errors: errors in planned code",
                "      (+lines of diffs) that the compiler/linter/interpreter",
                "      would flag, where the intended correct code is obvious",
                "      from surrounding context (typos, missing imports for",
                "      clearly-used symbols, non-exhaustive match/switch).",
                "      NOT this category: plan structure errors (stale context",
                "      lines, broken refs) or code errors where correct intent",
                "      is unclear (wrong module, non-existent API).",
                "",
                "NO FIXED COUNT - generate what the content requires.",
            ],
            "next": f"python3 -m {module_path} --step 6{state_dir_arg}",
        }

    def _step_6_atomicity_check(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 6: Atomicity check - split based on severity.

        D5: Replace undefined "CRITICAL" concept with severity. Severity
        (MUST/SHOULD/COULD) is already defined in conventions/severity.md with
        clear categories and blocking semantics. MUST-severity items get atomic
        splits plus umbrella check; SHOULD/COULD items remain as umbrellas for
        broader coverage.
        """
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""

        return {
            "title": f"QR Decomposition Step 6/{total_steps}: Atomicity Check ({self.PHASE})",
            "actions": [
                "REVIEW each item for atomicity.",
                "",
                "An item is ATOMIC if:",
                "  - It tests exactly ONE thing",
                "  - Pass/fail is unambiguous",
                "  - It cannot be 'half passed'",
                "",
                "NON-ATOMIC signals:",
                "  - Contains 'and' joining distinct concerns",
                "  - Contains 'all/each/every' over unbounded collection",
                "  - Failure could mean multiple different problems",
                "",
                "DECISION RULE (based on severity):",
                "  - If non-atomic AND severity=MUST: SPLIT into specifics, KEEP umbrella",
                "  - If non-atomic AND severity=SHOULD/COULD: KEEP as umbrella (broader coverage)",
                "",
                "WHY SEVERITY DETERMINES SPLITTING:",
                "  MUST items block all iterations - specific diagnostics justify the cost",
                "  SHOULD/COULD items have lower stakes - umbrella catches suffice",
                "",
                "WHEN SPLITTING:",
                "  - Original item becomes PARENT (keep id, e.g., qa-002)",
                "  - New items become CHILDREN (suffixed, e.g., qa-002a, qa-002b)",
                "  - Each child MUST have parent_id field set to parent's id",
                "  - Children inherit parent's severity",
                "",
                "SPLIT EXAMPLE:",
                '  Original: {"id": "qa-002", "severity": "MUST", "check": "Verify decision log completeness"}',
                "  After split:",
                '    {"id": "qa-002", "severity": "MUST", "check": "..."}  <- parent umbrella',
                '    {"id": "qa-002a", "parent_id": "qa-002", "severity": "MUST", "check": "...DL-001"}',
                '    {"id": "qa-002b", "parent_id": "qa-002", "severity": "MUST", "check": "...DL-002"}',
                "",
                "OUTPUT: Revised item list with atomicity notes.",
            ],
            "next": f"python3 -m {module_path} --step 7{state_dir_arg}",
        }

    def _step_7_coverage_validation(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 7: Coverage validation - verify completeness."""
        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""

        return {
            "title": f"QR Decomposition Step 7/{total_steps}: Coverage Validation ({self.PHASE})",
            "actions": [
                "FINAL CHECK using Step 3 enumeration as checklist:",
                "",
                "For EACH element enumerated in Step 3:",
                "  [ ] At least one item would catch issues with this element",
                "",
                "For EACH concern from Step 2:",
                "  [ ] At least one item addresses this concern",
                "",
                "If any unchecked: ADD items.",
                "",
                "PREFERENCE: If uncertain whether coverage is adequate, ADD an item.",
                "Overlapping coverage is acceptable. Gaps are not.",
                "",
                "OUTPUT: Final item list ready for Step 8.",
            ],
            "next": f"python3 -m {module_path} --step 8{state_dir_arg}",
        }

    def _step_8_finalize(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Step 8: Write qr-{phase}.json.

        Orchestrator handles dispatch.
        Decompose agent's responsibility: item data. Dispatch generation
        requires TemplateDispatchNode, which belongs in orchestrator layer.

        Output includes structured summary so parent agent has visibility
        into what was decomposed without reading the file.
        """
        if not state_dir:
            return {
                "title": "Error",
                "actions": ["ERROR: --state-dir required for step 8"],
                "next": "",
            }

        state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
        return {
            "title": f"QR Decomposition Step 8/{total_steps}: Finalize ({self.PHASE})",
            "actions": [
                f"WRITE qr-{self.PHASE}.json to {state_dir}:",
                "",
                "{",
                f'  "phase": "{self.PHASE}",',
                '  "iteration": 1,',
                '  "items": [/* your items from Step 7 */]',
                "}",
                "",
                "Item count: whatever the content requires. No fixed caps.",
                "",
                "After writing, proceed to grouping phase.",
            ],
            "next": f"python3 -m {module_path} --step 9{state_dir_arg}",
        }

    def _step_9_structural_grouping(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Phase 0: Automatic structural grouping. No LLM judgment required.

        Applies deterministic rules:
        1. Parent-child: Items with parent_id inherit parent's group
        2. Umbrella batching: scope='*' items get group_id='umbrella'

        Only operates on items with status='TODO'. Completed items retain existing group_id.
        """
        from skills.planner.shared.qr.utils import load_qr_state
        qr_state = load_qr_state(state_dir, self.PHASE)
        items = qr_state.get("items", []) if qr_state else []

        todo_items = [i for i in items if i.get("status") == "TODO"]

        item_ids = {i["id"] for i in items}
        children = [i for i in todo_items if i.get("parent_id")]
        orphans = [i for i in children if i.get("parent_id") not in item_ids]
        valid_children = [i for i in children if i.get("parent_id") in item_ids]
        parents = {i["id"]: i for i in todo_items if any(c.get("parent_id") == i["id"] for c in valid_children)}
        umbrellas = [i for i in todo_items if i.get("scope") == "*" and not i.get("parent_id") and not i.get("group_id")]

        # Orphans block workflow progression - data corruption must not propagate
        if orphans:
            return {
                "title": f"QR Decomposition Step 9/{total_steps}: Structural Grouping ({self.PHASE})",
                "actions": [
                    "BLOCKING ERROR: Orphan items detected",
                    "",
                    f"Found {len(orphans)} orphan items (parent_id references missing parent):",
                    f"  {[i['id'] for i in orphans]}",
                    "",
                    "These items have parent_id but parent does not exist.",
                    "Return to Step 6 and fix atomicity splits to ensure parent items exist.",
                    "",
                    "WORKFLOW HALTED - fix parent_id references before continuing.",
                ],
                "next": "",  # Terminal error - no continuation
            }

        return {
            "title": f"QR Decomposition Step 9/{total_steps}: Structural Grouping ({self.PHASE})",
            "actions": [
                "AUTOMATIC GROUPING (deterministic rules, TODO items only):",
                "",
                f"Found {len(parents)} parent items with children",
                f"Found {len(valid_children)} child items with valid parent_id",
                f"Found {len(umbrellas)} umbrella items (scope='*')",
                "",
                "1. PARENT-CHILD RESOLUTION:",
                "   For each item with valid parent_id:",
                "   - Set parent.group_id = parent-{parent.id} (anchor the group)",
                "   - Set child.group_id = parent-{parent.id} (join parent's group)",
                "",
                "2. UMBRELLA BATCHING:",
                "   For items with scope='*' and no parent_id:",
                "   - Set group_id = 'umbrella'",
                "",
                f"Execute via CLI:",
                f"  python3 -m skills.planner.cli.qr --state-dir {state_dir} --qr-phase {self.PHASE} \\",
                "    assign-group <item_id> --group-id <group_id>",
            ],
            "next": f"python3 -m {module_path} --step 10 --state-dir {state_dir}",
        }

    def _step_10_component_grouping(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Phase 1: Component-based grouping.

        Groups items verifying different aspects of the same structural element.
        Uses helpers for DRY output formatting.
        """
        ungrouped = self._load_ungrouped_todo_items(state_dir)
        item_list_xml = self._render_item_list(ungrouped, "ungrouped_items")

        return {
            "title": f"QR Decomposition Step 10/{total_steps}: Component Grouping ({self.PHASE})",
            "actions": [
                "GROUP BY STRUCTURAL COMPONENTS",
                "",
                "A 'component' is a discrete structural element:",
                "  - In plan-design: a milestone, a major decision, a constraint category",
                "  - In plan-code: a file, a module, a code_intent cluster",
                "  - In plan-docs: a documentation section, a topic area",
                "",
                item_list_xml,
                "",
                "TASK:",
                "1. Identify components that multiple items verify aspects of",
                "2. Create group_id with 'component-' prefix (e.g., 'component-milestone-m001')",
                "3. Only group if items GENUINELY share structural element",
                "4. Items not clearly belonging: SKIP for later phases",
                "",
                "PRIORITY: If item could be component OR concern, prefer component.",
                "",
                "SELF-VERIFICATION:",
                "  - Would verifying together provide shared context benefit?",
                "  - Are these truly about the SAME structural element?",
                "  - If uncertain, do NOT group.",
                "",
                *self._format_assign_cmd(state_dir, "component-"),
                "",
                f"If no component groups: # No component groups. {len(ungrouped)} items to Phase 2.",
            ],
            "next": f"python3 -m {module_path} --step 11 --state-dir {state_dir}",
        }

    def _step_11_concern_grouping(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Phase 2: Concern-based grouping.

        Groups items verifying the same quality dimension across different elements.
        Uses helpers for DRY output formatting.
        """
        ungrouped = self._load_ungrouped_todo_items(state_dir)
        item_list_xml = self._render_item_list(ungrouped, "ungrouped_items")

        return {
            "title": f"QR Decomposition Step 11/{total_steps}: Concern Grouping ({self.PHASE})",
            "actions": [
                "GROUP BY QUALITY CONCERNS",
                "",
                "A 'concern' is a cross-cutting quality dimension:",
                "  - Error handling consistency",
                "  - Concurrent access safety",
                "  - Testing boundary clarity",
                "  - Documentation completeness",
                "",
                item_list_xml,
                "",
                "TASK:",
                "1. Identify concerns that span multiple elements",
                "2. Create group_id with 'concern-' prefix (e.g., 'concern-error-handling')",
                "3. Only group if items verify SAME quality dimension",
                "4. Items not clearly sharing concern: SKIP for affinity phase",
                "",
                "SELF-VERIFICATION:",
                "  - Do these check the same KIND of quality?",
                "  - Would a single agent have useful context overlap?",
                "",
                *self._format_assign_cmd(state_dir, "concern-"),
            ],
            "next": f"python3 -m {module_path} --step 12 --state-dir {state_dir}",
        }

    def _step_12_affinity_grouping(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Phase 3: Affinity grouping for remaining items.

        Uses helpers for DRY output formatting.
        """
        ungrouped = self._load_ungrouped_todo_items(state_dir)
        item_list_xml = self._render_item_list(ungrouped, "ungrouped_items")

        return {
            "title": f"QR Decomposition Step 12/{total_steps}: Affinity Grouping ({self.PHASE})",
            "actions": [
                "GROUP BY SEMANTIC AFFINITY",
                "",
                "For items that don't fit component/concern patterns:",
                "  - Similar verification complexity",
                "  - Related subject matter",
                "  - Shared verification context",
                "",
                item_list_xml,
                "",
                "TASK:",
                "1. Identify natural clusters by semantic similarity",
                "2. Create group_id with 'affinity-' prefix (e.g., 'affinity-validation-checks')",
                "3. Avoid large catch-all groups",
                "4. Singletons are acceptable for truly independent items",
                "",
                *self._format_assign_cmd(state_dir, "affinity-"),
                "",
                "Remaining ungrouped items become singletons.",
            ],
            "next": f"python3 -m {module_path} --step 13 --state-dir {state_dir}",
        }

    def _step_13_final_validation(self, state_dir: str, module_path: str, total_steps: int) -> dict:
        """Final validation of groupings.

        Output includes structured summary so parent agent has visibility
        into the final decomposition and grouping results.
        """
        from skills.planner.shared.qr.utils import load_qr_state
        qr_state = load_qr_state(state_dir, self.PHASE)
        items = qr_state.get("items", []) if qr_state else []

        groups = {}
        singletons = []
        for item in items:
            gid = item.get("group_id")
            if gid:
                groups.setdefault(gid, []).append(item["id"])
            else:
                singletons.append(item["id"])

        group_summary = "\n".join([
            f"  {gid}: {len(ids)} items"
            for gid, ids in sorted(groups.items())
        ]) if groups else "  (no groups)"

        return {
            "title": f"QR Decomposition Step 13/{total_steps}: Final Validation ({self.PHASE})",
            "actions": [
                "FINAL GROUPING VALIDATION",
                "",
                f"SUMMARY: {len(groups)} groups, {len(singletons)} singletons",
                "",
                "Groups:",
                group_summary,
                "",
                f"Singletons: {len(singletons)} items",
                "",
                "VALIDATION:",
                "[ ] All group_ids follow namespace convention:",
                "    - 'umbrella' for scope='*' items",
                "    - 'parent-{id}' for parent-child groups",
                "    - 'component-*' for Step 10 groups",
                "    - 'concern-*' for Step 11 groups",
                "    - 'affinity-*' for Step 12 groups",
                "[ ] Large groups (>10 items) reviewed for forced grouping",
                "[ ] Singletons are genuinely independent",
                "[ ] Parent-child items share same parent-{id} group",
                "[ ] No orphan items (parent_id referencing missing parent)",
                "",
                "AFTER VALIDATION, output: PASS",
            ],
            "next": "",
        }


def write_qr_state(state_dir: str, phase: str, items: list[dict]) -> None:
    """Write QR state file with iteration=1.

    WHY iteration=1 always:
    Decompose runs once per phase (enforced by skip logic in planner.py).
    Iteration counter tracks verification cycles, not decompose invocations.
    Verify step increments iteration on RETRY (after fixes applied).

    WHY separation of concerns:
    Decompose defines WHAT to verify (items); verify tracks HOW MANY times
    verification ran (iteration). Coupling these counts would conflate
    definition with execution.
    """
    qr_state = {
        "phase": phase,
        "iteration": 1,
        "items": items,
    }
    qr_path = Path(state_dir) / f"qr-{phase}.json"
    qr_path.write_text(json.dumps(qr_state, indent=2))
