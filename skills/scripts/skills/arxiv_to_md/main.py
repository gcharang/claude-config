#!/usr/bin/env python3
"""arxiv-to-md orchestrator: discover papers, print their convert commands, dispatch reviews.

Two invocation modes:
  MODE 1: Direct conversion (default)
    - User provides arXiv IDs directly or via discovery
    - The converter builds the filename from the paper's title and first-submission date

  MODE 2: PDF folder sync
    - User specifies source PDF folder + destination markdown folder
    - Orchestrator matches PDFs to existing .md files, identifies gaps
    - Destination filename derived from PDF filename

The steps are build_next_command and format_output below.
"""

import argparse
import shlex
import sys
from pathlib import Path

from skills.arxiv_to_md.convert import ARXIV_ID_RE, find_residual_spans
from skills.lib.io import read_text_or_exit
from skills.lib.workflow.prompts import format_step, parallel_constraint, pin_cwd

# ============================================================================
# SHARED PROMPTS
# ============================================================================

# ============================================================================

DEST_PATH_QUOTING = (
    "In a shell command, the destination path goes in single quotes because it contains\n"
    "spaces. Write each ' in it as '\\'' (Let's -> Let'\\''s) so an apostrophe in a title\n"
    "does not end the quoted string early."
)

# ============================================================================
# CONFIGURATION
# ============================================================================

MODULE_PATH = "skills.arxiv_to_md.main"
CONVERT_MODULE_PATH = "skills.arxiv_to_md.convert"
REVIEW_AGENT = "arxiv-latex-reviewer"


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: DISCOVER --------------------------------------------------------

DISCOVER_INSTRUCTIONS = (
    "MODE DETECTION:\n"
    "Determine which mode based on user input:\n"
    "\n"
    "MODE 1 (default): Direct conversion\n"
    "  Trigger: User provides arXiv IDs directly, or asks to convert papers\n"
    "  Filename: the converter builds it from the paper's title and first-submission date\n"
    "\n"
    "MODE 2: PDF folder sync\n"
    "  Trigger: User specifies source PDF folder AND destination markdown folder\n"
    "  Filename: derived from the PDF filename; the orchestrator passes it to the converter\n"
    "\n"
    "============================================================\n"
    "\n"
    "MODE 1 DISCOVERY:\n"
    "Before asking the user for arXiv IDs, check for:\n"
    "  - CLAUDE.md in current directory (may list arXiv IDs)\n"
    "  - README.md or similar docs with arXiv links/IDs\n"
    "  - .bib files with arXiv entries\n"
    "If IDs found, confirm with user: 'Found arXiv ID(s) X, Y. Convert these?'\n"
    "\n"
    "PARSE USER INPUT:\n"
    "If user provides input directly, parse for arXiv IDs:\n"
    "  - Format: YYMM.NNNNN (e.g., 2503.05179)\n"
    "  - Or full URL: https://arxiv.org/abs/YYMM.NNNNN\n"
    "  - May be multiple IDs (comma-separated, space-separated, or multiple URLs)\n"
)

MODE2_DISCOVERY_INSTRUCTIONS = (
    "\n"
    "============================================================\n"
    "\n"
    "MODE 2 DISCOVERY (PDF folder sync):\n"
    "\n"
    "Resolve each arXiv ID with WebSearch on the paper title from the PDF's filename;\n"
    "the filename carries the title, so the PDFs themselves are not opened.\n"
    "\n"
    "Most PDFs already have a converted .md, so check the destination before\n"
    "dispatching: a PDF with a matching .md is skipped.\n"
    "\n"
    "FILE NAMING CONVENTION:\n"
    "  PDFs:     YYYY-MM-DD <title>.pdf\n"
    "  Markdown: YYYY-MM-DD <title>.md\n"
    "  Example:  2025-01-08 Pruning the Unsurprising.pdf\n"
    "\n"
    "1. SCAN DESTINATION FOLDER for existing markdown FIRST:\n"
    "   - List all *.md files in destination folder\n"
    "\n"
    "2. SCAN SOURCE FOLDER for PDFs:\n"
    "   - List all *.pdf files in source folder\n"
    "   - Extract base filename (without .pdf extension)\n"
    "\n"
    "3. For EACH PDF, check if matching .md exists:\n"
    "   Matching logic: same YYYY-MM-DD prefix + similar title\n"
    "   - '2025-01-08 Pruning the Unsurprising.pdf' matches '2025-01-08 Pruning the Unsurprising.md'\n"
    "   If match exists -> SKIP this PDF (do not dispatch)\n"
    "\n"
    "4. RESOLVE ARXIV IDs from unmatched PDFs:\n"
    "   - Extract paper title from PDF filename (after YYYY-MM-DD prefix)\n"
    "   - Use WebSearch to find arXiv ID for that paper title\n"
    "\n"
    "5. DETERMINE DESTINATION FILENAMES:\n"
    "   For each unmatched PDF with resolved arXiv ID:\n"
    "   - dest_file = '<absolute dest_folder>/<pdf_basename>.md'\n"
    "   - Example: source/2025-01-08 Pruning the Unsurprising.pdf\n"
    "             -> dest/2025-01-08 Pruning the Unsurprising.md\n"
)

NEXT_STEP_ARGS_INSTRUCTIONS = (
    "\n"
    "============================================================\n"
    "\n"
    "NEXT STEP ARGUMENTS:\n"
    "Run the NEXT STEP command with $PAPERS replaced by one --paper argument per paper to\n"
    "convert, and $OUT_DIR by the absolute path of the directory MODE 1 writes to (the\n"
    "current working directory unless the user named another). Change nothing else.\n"
    "  MODE 1: --paper <arxiv_id>\n"
    "  MODE 2: --paper '<arxiv_id>::<dest_file>', and delete ' --out-dir $OUT_DIR'\n"
    "The converter runs from the scripts directory, so $OUT_DIR and every <dest_file> are\n"
    "absolute paths.\n" + DEST_PATH_QUOTING + "\n"
    "\n"
    "When no paper is left to convert (every PDF already has its .md), skip the NEXT STEP\n"
    "and tell the user which PDFs were skipped.\n"
)

# --- STEP 2: CONVERT ---------------------------------------------------------

CONVERT_INSTRUCTIONS = (
    "Run each command below in its own Bash call, all in one message so they run in\n"
    "parallel. Give each call a 600000 ms timeout: a large source archive or a long paper\n"
    "takes minutes.\n"
)

CONVERT_RESULT_INSTRUCTIONS = (
    "Each command prints FILE: with the path it wrote, or one FAIL: line.\n"
    "  - A RESIDUAL: line after FILE: says LaTeX remains outside math and code in that\n"
    "    file; the file goes to review in the next step.\n"
    "  - A FAIL: that lists several main .tex candidates: run that paper's command again\n"
    "    with --main-tex '<candidate>' added, choosing the candidate that is the paper's\n"
    "    main file.\n"
    "  - Any other FAIL: report it in the summary.\n"
    "\n"
    "Run the NEXT STEP command with $REVIEW replaced by one --review '<FILE path>' per file\n"
    "that printed a RESIDUAL: line; with none, delete $REVIEW. Change nothing else.\n"
    + DEST_PATH_QUOTING
)

# --- STEP 3: REVIEW ----------------------------------------------------------

REVIEW_BRIEF = (
    "The arxiv-to-md converter wrote this file from the paper's TeX source and flagged the\n"
    "lines below, where LaTeX commands remain outside math and code. Later work reads this\n"
    "file in place of the paper, so a repair that changes what the paper says is worse than\n"
    "leaving the LaTeX in place.\n"
    "\n"
    "Read the file, then for each flagged line, edit the file:\n"
    "  - A command with a Markdown form (emphasis, a link, a list, a table): rewrite it in\n"
    "    Markdown and keep its text.\n"
    "  - A command that only formats or labels (\\vspace, \\centering, \\label): delete it.\n"
    "  - A LaTeX block with no Markdown form: put the whole block in a fenced code block\n"
    "    whose opening fence is ```latex, on lines of its own.\n"
    "Leave $...$ and $$...$$ math unchanged. Change nothing outside the flagged lines except\n"
    "the fence lines around a block you fence.\n"
    "\n"
    "Reply with:\n"
    "REVIEWED: <file path>\n"
    "and one line per flagged line you left as LaTeX:\n"
    "LEFT: <line number>: <reason>\n"
    "Reply with the REVIEWED:/LEFT: lines only."
)

REVIEW_DISPATCH_TEMPLATE = (
    "DISPATCH {count} PARALLEL REVIEW AGENTS\n"
    "=======================================\n"
    "\n"
    "{parallel_block}\n"
    "\n"
    "For EACH prompt below, use the Agent tool with:\n"
    "  - subagent_type: {agent}\n"
    "  - prompt: the text between the markers, unchanged\n"
    "\n"
    "{prompts}\n"
    "\n"
    "After ALL {count} agents return, continue with the next workflow step."
)

REVIEW_PROMPT_TEMPLATE = (
    "--- Prompt {index} ---\n"
    "File: {path}\n"
    "Flagged line numbers: {numbers}\n"
    "\n" + REVIEW_BRIEF + "\n"
    "--- End of prompt {index} ---"
)

NO_REVIEW_BODY = "No conversion printed a RESIDUAL: line, so no file needs review."

# --- STEP 4: SUMMARIZE -------------------------------------------------------

SUMMARY_INSTRUCTIONS = (
    "PRESENT FINAL SUMMARY to user:\n"
    "```\n"
    "Processed M papers: N converted, K skipped (already exist), F failed\n"
    "\n"
    "Skipped (already exist):\n"
    "  2025-01-08 Pruning the Unsurprising -> already exists\n"
    "\n"
    "Converted:\n"
    "  [OK] 2025-01-10 New Paper Title -> /path/to/2025-01-10 New Paper Title.md\n"
    "\n"
    "Failed:\n"
    "  [FAIL] 2024-12-15 Some Paper -> no TeX source (PDF-only submission)\n"
    "```\n"
    "Under a converted file, list each LEFT: line its reviewer returned."
)


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def build_convert_body(papers: list[tuple[str, str | None]], out_dir: str | None) -> str:
    """Build step 2 body: one exact convert command per paper."""
    commands = []
    for arxiv_id, dest in papers:
        if dest:
            target = f"--dest-file {shlex.quote(dest)}"
        else:
            assert out_dir is not None
            target = f"--out-dir {shlex.quote(out_dir)}"
        command = (
            f"uv run python -m {CONVERT_MODULE_PATH} --arxiv-id {shlex.quote(arxiv_id)} {target}"
        )
        commands.append("  " + pin_cwd(command))
    return CONVERT_INSTRUCTIONS + "\n" + "\n".join(commands) + "\n\n" + CONVERT_RESULT_INSTRUCTIONS


def build_review_body(files: list[str]) -> str:
    """Build step 3 body: one reviewer prompt per file that still has flagged lines."""
    flagged = []
    for path in files:
        text = read_text_or_exit(Path(path), "reading the converted paper")
        spans = find_residual_spans(text)
        if spans:
            flagged.append((path, spans))
    if not flagged:
        return NO_REVIEW_BODY
    prompts = [
        REVIEW_PROMPT_TEMPLATE.format(
            index=index,
            path=path,
            numbers=", ".join(str(number) for number, _ in spans),
        )
        for index, (path, spans) in enumerate(flagged, 1)
    ]
    return REVIEW_DISPATCH_TEMPLATE.format(
        count=len(prompts),
        parallel_block=parallel_constraint(len(prompts)),
        agent=REVIEW_AGENT,
        prompts="\n\n".join(prompts),
    )


def build_next_command(step: int) -> str | None:
    """Build invoke command for next step."""
    next_cmds = {
        1: f"uv run python -m {MODULE_PATH} --step 2 --out-dir $OUT_DIR $PAPERS",
        2: f"uv run python -m {MODULE_PATH} --step 3 $REVIEW",
        3: f"uv run python -m {MODULE_PATH} --step 4",
    }
    return next_cmds.get(step)


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

STATIC_STEPS = {
    1: (
        "Discover",
        DISCOVER_INSTRUCTIONS + MODE2_DISCOVERY_INSTRUCTIONS + NEXT_STEP_ARGS_INSTRUCTIONS,
    ),
    4: ("Summarize", SUMMARY_INSTRUCTIONS),
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(
    step: int,
    papers: list[tuple[str, str | None]],
    out_dir: str | None,
    review: list[str],
) -> str:
    """Format output for the given step."""
    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
    elif step == 2:
        title, instructions = "Convert", build_convert_body(papers, out_dir)
    elif step == 3:
        title, instructions = "Review", build_review_body(review)
    else:
        return f"ERROR: Invalid step {step}"

    next_cmd = build_next_command(step)
    return format_step(instructions, next_cmd or "", title=f"ARXIV-TO-MD - {title}")


def parse_paper(value: str) -> tuple[str, str | None]:
    """Split '<arxiv_id>' or '<arxiv_id>::<absolute dest_file>'."""
    arxiv_id, sep, dest = value.partition("::")
    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        sys.exit(f"ERROR: invalid arXiv id in --paper: {arxiv_id!r}")
    if sep and not Path(dest).is_absolute():
        sys.exit(f"ERROR: --paper dest_file must be an absolute path, got {dest!r}")
    return arxiv_id, (dest if sep else None)


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="arxiv-to-md orchestrator",
        epilog="Steps: discover (1) -> convert (2) -> review (3) -> summarize (4)",
    )
    parser.add_argument("--step", type=int, required=True, help="Current step (1-4)")
    parser.add_argument(
        "--paper",
        action="append",
        default=[],
        help="Step 2: <arxiv_id>, or '<arxiv_id>::<absolute dest_file>' in PDF folder sync",
    )
    parser.add_argument(
        "--out-dir", help="Step 2: absolute directory for papers given without a dest_file"
    )
    parser.add_argument(
        "--review",
        action="append",
        default=[],
        help="Step 3: absolute path of a converted file that printed a RESIDUAL line",
    )
    args = parser.parse_args()

    if args.step < 1 or args.step > 4:
        sys.exit(f"ERROR: --step must be 1-4, got {args.step}")

    papers = [parse_paper(value) for value in args.paper]
    if args.step == 2:
        if not papers:
            sys.exit("ERROR: step 2 needs at least one --paper")
        if any(dest is None for _, dest in papers) and not (
            args.out_dir and Path(args.out_dir).is_absolute()
        ):
            sys.exit("ERROR: --out-dir must be an absolute path when a --paper has no dest_file")
    if args.step == 3:
        for path in args.review:
            if not (Path(path).is_absolute() and Path(path).is_file()):
                sys.exit(f"ERROR: --review must be an absolute path to a file, got {path!r}")

    print(format_output(args.step, papers, args.out_dir, args.review))


if __name__ == "__main__":
    main()
