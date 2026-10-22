r"""Pure Python TeX preprocessing utilities.

Handles \input{} expansion and encoding normalization without external tools.
"""

import re
from pathlib import Path


def expand_inputs(
    tex_content: str,
    base_dir: Path,
    seen: set | None = None,
    root: Path | None = None,
) -> str:
    """Recursively expand \\input{} and \\include{} statements.

    Every path resolves against base_dir, including paths inside included files, as
    LaTeX resolves them against the compile directory.

    Args:
        tex_content: TeX source content
        base_dir: Directory to resolve relative paths from
        seen: Set of already-processed files (circular reference detection)
        root: Directory every expanded file must resolve inside; defaults to base_dir

    Returns:
        TeX content with all inputs expanded inline
    """
    if seen is None:
        seen = set()
    if root is None:
        root = base_dir.resolve()

    def replace_input(match):
        filename = match.group(1).strip()
        # \input{foo} -> foo.tex if no extension
        if not filename.endswith(".tex"):
            filename = filename + ".tex"

        filepath = base_dir / filename
        resolved = filepath.resolve()

        if not resolved.is_relative_to(root):
            return f"% [OUTSIDE SOURCE: {filename}]"

        if resolved in seen:
            return f"% [CIRCULAR REFERENCE: {filename}]"
        seen.add(resolved)

        if resolved.exists():
            try:
                content = resolved.read_text(encoding="utf-8", errors="replace")
                return expand_inputs(content, base_dir, seen, root)
            except Exception as e:
                return f"% [READ ERROR: {filename}: {e}]"
        return f"% [MISSING FILE: {filename}]"

    # Match \input{file} and \include{file}, handling whitespace
    pattern = r"\\(?:input|include)\s*\{([^}]{1,512})\}"
    return re.sub(pattern, replace_input, tex_content)


def normalize_encoding(content: str) -> str:
    """Normalize content to valid UTF-8.

    Args:
        content: String content (may have encoding issues)

    Returns:
        Clean UTF-8 string with replacement chars for invalid sequences
    """
    return content.encode("utf-8", errors="replace").decode("utf-8")


def strip_comments(tex_content: str) -> str:
    """Remove TeX comments (lines starting with %).

    Preserves escaped percent signs (\\%).

    Args:
        tex_content: TeX source content

    Returns:
        Content with comments removed
    """
    lines = []
    for line in tex_content.split("\n"):
        # Find first unescaped % and truncate
        result = []
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            result.append(line[i])
            i += 1
        lines.append("".join(result).rstrip())
    return "\n".join(lines)


def extract_abstract(tex_content: str) -> str:
    """Convert abstract environment to a section pandoc will render.

    Transforms \\begin{abstract}...\\end{abstract} into a proper section.

    Args:
        tex_content: TeX source content

    Returns:
        Content with abstract converted to section
    """
    begin, end = r"\begin{abstract}", r"\end{abstract}"
    parts = []
    pos = 0
    while (start := tex_content.find(begin, pos)) != -1:
        body_start = start + len(begin)
        stop = tex_content.find(end, body_start)
        if stop == -1:
            break
        parts.append(tex_content[pos:start])
        parts.append(f"\\section*{{Abstract}}\n{tex_content[body_start:stop].strip()}")
        pos = stop + len(end)
    parts.append(tex_content[pos:])
    return "".join(parts)


def convert_bold_headers(tex_content: str) -> str:
    """Convert bold-text pseudo-headers to proper subsections.

    Many papers use {\\bf Title} or \\textbf{Title} instead of \\subsubsection{}.
    This detects standalone bold patterns and converts them.

    Heuristic: inline labels typically end with punctuation (period, colon),
    while section headers don't. We only convert non-punctuated bold text.

    Args:
        tex_content: TeX source content

    Returns:
        Content with bold headers converted to subsubsections
    """
    # Pattern: \noindent {\bf Title} or \noindent \textbf{Title}
    # Only convert if the title does NOT end with punctuation (., :, ?)
    # to avoid converting inline definition labels.

    def make_subsubsection(m, title_group=1):
        title = m.group(title_group).strip()
        # Skip if ends with punctuation (inline label, not header)
        if title and title[-1] in ".,:;?!":
            return m.group(0)  # Return unchanged
        return f"\\subsubsection*{{{title}}}"

    # {\bf ...} style with \noindent
    tex_content = re.sub(
        r"\\noindent\s*\{\\bf\s+([^}\s][^}]{0,199})\}",
        lambda m: make_subsubsection(m, 1),
        tex_content,
    )

    # \textbf{...} style with \noindent
    tex_content = re.sub(
        r"\\noindent\s*\\textbf\{([^}]{1,200})\}",
        lambda m: make_subsubsection(m, 1),
        tex_content,
    )

    # Standalone {\bf ...} at line start (no \noindent)
    tex_content = re.sub(
        r"^([ \t]*)\{\\bf\s+([^}\s][^}]{0,199})\}[ \t]*$",
        lambda m: (
            m.group(0)
            if m.group(2).strip()[-1:] in ".,:;?!"
            else f"{m.group(1)}\\subsubsection*{{{m.group(2)}}}"
        ),
        tex_content,
        flags=re.MULTILINE,
    )

    return tex_content


def inline_bibliography(tex_content: str, base_dir: Path, main_stem: str | None = None) -> str:
    """Inline .bbl bibliography file if available.

    Replaces \\bibliography{...} command with contents of compiled .bbl file.
    This allows pandoc to see the expanded bibliography entries.

    Args:
        tex_content: TeX source content
        base_dir: Directory containing the .bbl file
        main_stem: Basename of the main .tex file; selects <main_stem>.bbl

    Returns:
        Content with bibliography inlined (or unchanged if no .bbl found)
    """
    bbl_files = sorted(base_dir.glob("*.bbl"))
    named = [f for f in bbl_files if f.stem == main_stem]
    if named:
        bbl_path = named[0]
    elif len(bbl_files) == 1:
        bbl_path = bbl_files[0]
    else:
        return tex_content
    try:
        bbl_content = bbl_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return tex_content

    # Replace \bibliography{...} with the .bbl contents
    # The .bbl file contains \begin{thebibliography}...\end{thebibliography}
    pattern = r"\\bibliography\s*\{[^}]*\}"

    if re.search(pattern, tex_content):
        # Use lambda to avoid backslash interpretation in replacement string
        return re.sub(pattern, lambda _: bbl_content, tex_content)

    # If no \bibliography command but \end{document} exists, insert before it
    if r"\end{document}" in tex_content and bbl_content.strip():
        return tex_content.replace(r"\end{document}", f"\n{bbl_content}\n\\end{{document}}")

    return tex_content


def preprocess_tex(main_tex_path: str, root: str | None = None) -> str:
    """Main preprocessing entry point.

    Reads main .tex file, expands inputs, normalizes encoding,
    and transforms problematic LaTeX patterns for pandoc.

    Args:
        main_tex_path: Path to main .tex file
        root: Directory inputs must stay inside; defaults to the main file's directory

    Returns:
        Path to preprocessed.tex output file
    """
    path = Path(main_tex_path)
    if not path.exists():
        raise FileNotFoundError(f"Main TeX file not found: {main_tex_path}")

    content = path.read_text(encoding="utf-8", errors="replace")

    # Expand \input{} and \include{} recursively
    expanded = expand_inputs(content, path.parent, root=Path(root).resolve() if root else None)

    # Inline .bbl bibliography if available
    with_bib = inline_bibliography(expanded, path.parent, path.stem)

    # Convert abstract environment to section (pandoc strips it otherwise)
    with_abstract = extract_abstract(with_bib)

    # Convert bold pseudo-headers to proper subsubsections
    with_headers = convert_bold_headers(with_abstract)

    # Normalize to clean UTF-8
    normalized = normalize_encoding(with_headers)

    # Write preprocessed output
    output_path = path.parent / "preprocessed.tex"
    output_path.write_text(normalized, encoding="utf-8")

    return str(output_path)
