"""Workflow constants shared across all skills.

QR-related constants are defined here in the lib layer so that
formatters can use them without creating a dependency on planner.
"""


# =============================================================================
# State File Constants (JSON migration)
# =============================================================================

PLAN_FILE = "plan.json"


# =============================================================================
# Question Relay Protocol
# =============================================================================

SUB_AGENT_QUESTION_FORMAT = """\
<question_protocol>
When you need user clarification to proceed:

BEFORE YIELDING:
  Record everything you have already settled with your workflow's own state commands.
  The re-invocation sees only what those commands recorded, nothing else from this run.

THEN emit this XML as your ENTIRE response:

<needs_user_input>
  <question header="SHORT_LABEL" multi_select="false">
    <text>Your question here?</text>
    <option label="Choice A">Description of what A means</option>
    <option label="Choice B">Description of what B means</option>
  </question>
</needs_user_input>

EXAMPLE (multiple questions):
<needs_user_input>
  <question header="Auth">
    <text>Which authentication method?</text>
    <option label="OAuth">Industry standard, supports refresh tokens</option>
    <option label="JWT">Self-contained, no session storage</option>
  </question>
  <question header="Storage">
    <text>Which storage backend for cache?</text>
    <option label="Redis">Fast, requires external service</option>
    <option label="SQLite">Simple, file-based, no dependencies</option>
  </question>
</needs_user_input>

CONSTRAINTS:
  - Max 3 <question> elements
  - Each question: 2-3 <option> elements
  - header attribute: max 12 characters
  - multi_select: "true" or "false" (default false)
  - This XML is your COMPLETE response -- emit nothing else

WHEN TO USE:
  - Critical design decisions with competing valid approaches
  - Missing requirements that cannot be reasonably inferred
  - Trade-offs where user preference determines outcome

DO NOT USE FOR:
  - Implementation details with obvious best practices
  - Questions answerable from context already provided
  - Stylistic choices within established codebase patterns

WHAT HAPPENS NEXT:
  After emitting this XML, STOP. The orchestrator will:
  1. Relay the question to the user
  2. REINVOKE you fresh (NOT resume) with the user's answer
  3. Pass the same STATE_DIR, which holds what you recorded

  When reinvoked, you will receive:
  - <user_response> with answers to your questions
  - STATE_DIR pointing to your saved state
  - Instructions to invoke your script with --step 1

  Your script starts again at step 1. Read back what you recorded and build on it
  instead of re-deciding or re-creating it.
</question_protocol>
"""


QUESTION_RELAY_HANDLER = """\
<question_relay_handler>
If sub-agent output contains <needs_user_input>:
  1. Parse XML and call AskUserQuestion with extracted fields
  2. Reinvoke sub-agent FRESH (not resume) with <user_response> and same STATE_DIR
     Sub-agent restores its recorded state from STATE_DIR; invoke script --step 1
</question_relay_handler>
"""
