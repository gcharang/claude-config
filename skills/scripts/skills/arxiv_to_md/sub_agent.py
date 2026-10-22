"""arxiv-to-md review sub-agent: print the brief and the flagged lines of one converted file."""

import argparse
from pathlib import Path

from skills.arxiv_to_md.convert import find_residual_spans
from skills.lib.io import read_text_or_exit
from skills.lib.workflow.prompts import format_step

REVIEW_INSTRUCTIONS = (
    "The arxiv-to-md converter wrote this file from the paper's TeX source and flagged the\n"
    "lines below, where LaTeX commands remain outside math and code. Later work reads this\n"
    "file in place of the paper, so a repair that changes what the paper says is worse than\n"
    "leaving the LaTeX in place.\n"
    "\n"
    "For each flagged line, edit the file:\n"
    "  - A command with a Markdown form (emphasis, a link, a list, a table): rewrite it in\n"
    "    Markdown and keep its text.\n"
    "  - A command that only formats or labels (\\vspace, \\centering, \\label): delete it.\n"
    "  - A LaTeX block with no Markdown form: put the whole block in a fenced code block\n"
    "    whose opening fence is ```latex, on lines of its own.\n"
    "Leave $...$ and $$...$$ math unchanged. Change nothing outside the flagged lines except\n"
    "the fence lines around a block you fence."
)

REPLY_FORMAT = (
    "Reply with:\n"
    "REVIEWED: <file path>\n"
    "and one line per flagged line you left as LaTeX:\n"
    "LEFT: <line number>: <reason>\n"
    "Reply with the REVIEWED:/LEFT: lines only."
)


def format_output(path: Path) -> str:
    spans = find_residual_spans(read_text_or_exit(path, "reading the converted paper"))
    lines = [f"File: {path}", ""]
    if spans:
        lines += [REVIEW_INSTRUCTIONS, "", "FLAGGED LINES:"]
        lines += [f"  L{number}: {text}" for number, text in spans]
    else:
        lines.append("No flagged lines remain.")
    lines += ["", REPLY_FORMAT]
    return format_step("\n".join(lines), "", title="ARXIV-TO-MD REVIEW - Residual LaTeX")


def main():
    parser = argparse.ArgumentParser(
        description="arxiv-to-md review sub-agent: residual LaTeX in one file"
    )
    parser.add_argument(
        "--file", required=True, help="Absolute path of the converted markdown file"
    )
    args = parser.parse_args()
    print(format_output(Path(args.file)))


if __name__ == "__main__":
    main()
