"""Guard: every authored <invoke>/<file> reference in skills & agents resolves.

This config is deployed to ~/.claude from this repo (private
``scripts/sync-to-claude.sh`` mirrors ``DIRS_TO_SYNC=(agents conventions
output-styles skills …)`` 1:1 into ``$HOME/.claude``), so **``.claude/`` ≡ repo
root** and **``.claude/skills/scripts`` ≡ ``<repo>/skills/scripts``**. Skills are
invoked from ``~/.claude/skills/scripts`` via ``uv run python -m skills.X.Y`` and
embed files via ``<file working-dir=".claude" uri="…"/>``. The reference-form
semantics are documented in ``skills/lib/workflow/prompts/README.md`` ("Three
Invocation Forms").

Nothing else validates the *authored markdown* reference layer:
``test_uv_run_invariant.py`` guards the Python renderer's *emitted* strings, not
SKILL.md / agents / INTENT.md. A renamed skill dir, moved module, deleted
convention file, or ``working-dir`` typo would dangle silently and only break at
runtime after deploy. This test fails at CI time instead (the CI ``paths:``
filter in ``.github/workflows/skills-test.yml`` covers every tree scanned here).

Five invariants (R1-R5), each collecting file:line violations like
``test_uv_run_invariant.py``:
  R1  every ``python -m skills.A.B.C`` maps to a ``-m``-runnable module
  R2  every ``<file … uri="U">`` target is a real file under the deploy root
  R3  every ``working-dir`` is a real deploy root
  R4  every ``python -m skills.…`` command is prefixed with ``uv run``
  R5  each skill's dir ↔ SKILL.md ``name:`` ↔ its invoke package stay consistent

Scope (``_reference_docs``): the docs whose ``<invoke>``/``<file>`` are *executed*
references — ``agents/*.md``, ``skills/*/SKILL.md``, ``skills/*/INTENT.md``.
Deliberately excluded: README / ``CLAUDE.md`` indexes (they carry *illustrative*
module examples — e.g. ``skills.<skill_name>.<module>`` — not deployed
references) and ``skills/*/resources/*.md`` (prompt *content*, not entry docs;
the only resource injected at runtime, ``plan-json-schema.md``, carries no
reference tags). Scanning either would risk false-failing on an illustrative
example.

Assumptions (revisit if they change): the ``skills`` tree uses **regular**
packages (every dir has ``__init__.py``), so R1 requires ``__init__.py`` at each
intermediate — a PEP-420 namespace migration would need R1 relaxed. A
``python -m`` command sits on one physical line (R1/R4 scan per line); tag
*structure* (R2/R3) is parsed over full text, so wrapped ``<invoke>``/``<file>``
tags still resolve, and a ``>`` inside a quoted attribute value does not
prematurely close the tag.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

# tests/ → scripts/ → skills/ → repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_SCRIPTS = REPO_ROOT / "skills" / "scripts"
PKG_ROOT = SKILLS_SCRIPTS / "skills"  # the `skills` Python package (packages=["skills"])

# The only directories `working-dir` may name — the deploy roots the sync creates.
# `.claude` ≡ REPO_ROOT; `.claude/skills/scripts` ≡ SKILLS_SCRIPTS. A downstream
# fork may deploy an additional first-party script package (e.g. a private
# `skills/custom-scripts/`); its candidate is listed here unconditionally and the
# `.exists()` filter below drops it wherever that tree is absent — so R3 stays
# correct both upstream (candidate filtered out, roots unchanged) and in a fork
# (present → that fork's `working-dir` refs resolve), with no per-fork divergence.
_WORKING_DIR_ROOT_CANDIDATES: dict[str, Path] = {
    ".claude": REPO_ROOT,
    ".claude/skills/scripts": SKILLS_SCRIPTS,
    ".claude/skills/custom-scripts": REPO_ROOT / "skills" / "custom-scripts",
}
WORKING_DIR_ROOTS: dict[str, Path] = {
    k: v for k, v in _WORKING_DIR_ROOT_CANDIDATES.items() if v.exists()
}

# `uri` targets deployed from outside this repo's tree: the global CLAUDE.md is
# written to ~/.claude by sync from the private root; the repo-root copy here is
# an intentional placeholder. Exempt from the file-exists check, but only under
# working-dir=".claude" (the root that reasoning applies to).
ALWAYS_DEPLOYED: frozenset[str] = frozenset({"CLAUDE.md"})

# A real `-m` module invocation: `python -m skills.a.b[.c…]`. The `python -m`
# prefix + `skills.` root excludes prose; `[A-Za-z0-9_]` segments admit a
# mis-cased typo (`skills.Refactor.x`) so R1 can catch it, while `<…>`/`{…}`
# placeholders (non-word chars) still don't match. ≥2 segments after `skills`.
PY_M_RE = re.compile(r"python3?\s+-m\s+(skills\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)")

# Structured reference tags, scanned over full file text so a tag whose
# attributes wrap across lines still matches. The body consumes whole quoted
# strings (`"[^"]*"`) or non-`>` chars, so a literal `>` inside a quoted value
# (e.g. `cmd="… --scope <scope>"`) does NOT close the tag early and drop later
# attributes. `\b` keeps `<invoke_after>` / `<filename>` from matching.
TAG_RE = re.compile(r'<(invoke|file)\b((?:"[^"]*"|[^>"])*?)/?>')
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')

# First `name:` line of a SKILL.md frontmatter block.
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Pure checks — shared by the tree-scan tests and the negative-control tests so
# the guard is proven to actually bite (a check that never fails is worthless).
# ---------------------------------------------------------------------------


def module_resolution_error(dotted: str) -> str | None:
    """R1: `skills.a.b.c` must be runnable via `python -m`.

    Requires the full import chain (each intermediate a regular package with
    ``__init__.py``) and a ``-m``-executable leaf: a ``.py`` module, or a package
    with ``__main__.py``. A package with only ``__init__.py`` is NOT runnable
    (``python -m pkg`` → "cannot be directly executed"). Checks file presence
    only — never imports — to avoid executing package init at collection time.
    """
    parts = dotted.split(".")
    if parts[0] != "skills":
        return f"{dotted}: not a `skills.` module path"
    if not (PKG_ROOT / "__init__.py").is_file():
        return f"{dotted}: package root missing {PKG_ROOT.relative_to(REPO_ROOT)}/__init__.py"
    cur = PKG_ROOT
    for seg in parts[1:-1]:  # intermediate packages
        cur = cur / seg
        if not (cur / "__init__.py").is_file():
            return f"{dotted}: missing package {cur.relative_to(REPO_ROOT)}/__init__.py"
    leaf = parts[-1]
    if (cur / f"{leaf}.py").is_file() or (cur / leaf / "__main__.py").is_file():
        return None
    return (
        f"{dotted}: not runnable via `python -m` "
        f"(no {(cur / leaf).relative_to(REPO_ROOT)}.py or {leaf}/__main__.py)"
    )


def working_dir_error(working_dir: str) -> str | None:
    """R3: working-dir must be a deploy root the sync actually creates."""
    if working_dir in WORKING_DIR_ROOTS:
        return None
    return f'working-dir="{working_dir}" not in {sorted(WORKING_DIR_ROOTS)}'


def uri_resolution_error(working_dir: str, uri: str) -> str | None:
    """R2: `<file>` uri resolves to a real file under its working-dir root."""
    base = WORKING_DIR_ROOTS.get(working_dir)
    if base is None:
        return f'working-dir="{working_dir}" not a deploy root (uri="{uri}")'
    if working_dir == ".claude" and uri in ALWAYS_DEPLOYED:
        return None
    return None if (base / uri).is_file() else f'missing file target uri="{uri}"'


def _command_start(line: str, pos: int) -> int:
    """Index just after the nearest *unquoted* ``;`` / ``&`` / ``|`` before pos (else 0).

    Quote-aware so a separator inside a quoted value (``--extra "a|b"``) does not
    split a command — otherwise a legitimately ``uv run``-prefixed line would
    false-fail. Tracks single/double quote state; a genuinely chained bare
    command (``… && python -m skills.x``) still starts a fresh window.
    """
    start = 0
    in_squote = in_dquote = False
    for i in range(pos):
        c = line[i]
        if c == "'" and not in_dquote:
            in_squote = not in_squote
        elif c == '"' and not in_squote:
            in_dquote = not in_dquote
        elif c in ";&|" and not in_squote and not in_dquote:
            start = i + 1
    return start


def uv_run_error(line: str) -> str | None:
    """R4: every `python -m skills.…` command on the line must have `uv run`.

    Each invocation must be preceded by ``uv run`` within its own shell command
    (bounded by unquoted separators), so a bare second command (``… && python -m
    skills.x``) is flagged even when an earlier command carried ``uv run``. The
    modern-python PreToolUse hook denies bare ``python``/``python3``.
    """
    for m in PY_M_RE.finditer(line):
        start = _command_start(line, m.start())
        if "uv run" not in line[start : m.start()]:
            return f"bare python invocation (needs `uv run`): {line[start:].strip()}"
    return None


# ---------------------------------------------------------------------------
# Doc discovery + structured-tag extraction
# ---------------------------------------------------------------------------


def _reference_docs() -> list[Path]:
    """Docs whose <invoke>/<file> are executed references (not prose examples)."""
    docs: list[Path] = []
    agents = REPO_ROOT / "agents"
    if agents.is_dir():
        docs += sorted(agents.glob("*.md"))
    skills = REPO_ROOT / "skills"
    if skills.is_dir():
        docs += sorted(skills.glob("*/SKILL.md"))
        docs += sorted(skills.glob("*/INTENT.md"))
    return docs


def _skill_manifests() -> list[Path]:
    skills = REPO_ROOT / "skills"
    return sorted(skills.glob("*/SKILL.md")) if skills.is_dir() else []


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _iter_doc_lines() -> Iterator[tuple[Path, int, str]]:
    """Yield (path, lineno, line) for every line of every in-scope doc."""
    for path in _reference_docs():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            yield path, lineno, line


def _iter_tags() -> Iterator[tuple[Path, int, str, dict[str, str]]]:
    """Yield (path, lineno, kind, attrs) for every <invoke>/<file> tag in scope.

    Scans full text (not per line) so tags with wrapped attributes still match.
    """
    for path in _reference_docs():
        text = path.read_text(encoding="utf-8")
        for m in TAG_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            yield path, lineno, m.group(1), dict(ATTR_RE.findall(m.group(2)))


def _iter_module_invocations() -> Iterator[tuple[Path, int, str]]:
    """Yield (path, lineno, module) for every `python -m skills.…` in scope."""
    for path, lineno, line in _iter_doc_lines():
        for m in PY_M_RE.finditer(line):
            yield path, lineno, m.group(1)


def _fail(violations: list[str], header: str) -> None:
    assert not violations, f"{header}\n  " + "\n  ".join(violations)


# ---------------------------------------------------------------------------
# Empty-scan safety — if discovery silently collapses (glob/exclusion
# regression), every scanning test passes vacuously; this one fails loud.
# ---------------------------------------------------------------------------


def test_discovery_is_non_empty() -> None:
    assert _reference_docs(), "no reference docs discovered — scan scope regressed"
    assert list(_iter_module_invocations()), "no `python -m skills.…` invocations found"
    assert any(a.get("working-dir") for *_, a in _iter_tags()), "no working-dir tags found"
    assert _skill_manifests(), "no SKILL.md manifests found"


# ---------------------------------------------------------------------------
# R1 — module paths resolve to a -m-runnable module
# ---------------------------------------------------------------------------


def test_invoke_module_paths_resolve() -> None:
    violations: list[str] = []
    for path, lineno, module in _iter_module_invocations():
        err = module_resolution_error(module)
        if err:
            violations.append(f"{_rel(path)}:{lineno}: {err}")
    _fail(violations, "Unresolvable `python -m skills.…` module reference(s):")


# ---------------------------------------------------------------------------
# R2 — <file> uri targets exist
# ---------------------------------------------------------------------------


def test_file_uris_resolve() -> None:
    violations: list[str] = []
    for path, lineno, kind, attrs in _iter_tags():
        if kind != "file":
            continue
        uri = attrs.get("uri")
        if uri is None:
            # Only <file working-dir uri> is a deploy embed. A <file> with
            # working-dir but no uri is a malformed embed (flag it); a <file>
            # with neither is an unrelated construct — a shell-arg placeholder
            # (`<file>`) or output-format schema (`<file path="…">`) — skip it.
            if "working-dir" in attrs:
                violations.append(f"{_rel(path)}:{lineno}: <file working-dir> missing uri=")
            continue
        err = uri_resolution_error(attrs.get("working-dir", ""), uri)
        if err:
            violations.append(f"{_rel(path)}:{lineno}: {err}")
    _fail(violations, "Unresolvable <file> reference(s):")


# ---------------------------------------------------------------------------
# R3 — working-dir values are real deploy roots
# ---------------------------------------------------------------------------


def test_working_dir_values_are_deploy_roots() -> None:
    violations: list[str] = []
    for path, lineno, _kind, attrs in _iter_tags():
        wd = attrs.get("working-dir")
        if wd is None:
            continue
        err = working_dir_error(wd)
        if err:
            violations.append(f"{_rel(path)}:{lineno}: {err}")
    _fail(violations, "Invalid working-dir value(s):")


# ---------------------------------------------------------------------------
# R4 — module invocations use `uv run`
# ---------------------------------------------------------------------------


def test_invocations_use_uv_run() -> None:
    violations: list[str] = []
    for path, lineno, line in _iter_doc_lines():
        err = uv_run_error(line)
        if err:
            violations.append(f"{_rel(path)}:{lineno}: {err}")
    _fail(violations, "Bare-python module invocation(s) (must use `uv run`):")


# ---------------------------------------------------------------------------
# R5 — skill dir ↔ SKILL.md name ↔ invoke package consistency
# ---------------------------------------------------------------------------


def test_skill_frontmatter_name_matches_dir() -> None:
    """R5a: SKILL.md `name:` must equal its parent directory name."""
    violations: list[str] = []
    for skill in _skill_manifests():
        dir_name = skill.parent.name
        m = NAME_RE.search(skill.read_text(encoding="utf-8"))
        if not m:
            violations.append(f"{_rel(skill)}: missing `name:` frontmatter")
        elif m.group(1) != dir_name:
            violations.append(f"{_rel(skill)}: name '{m.group(1)}' != dir '{dir_name}'")
    _fail(violations, "SKILL.md name/dir mismatch(es):")


def test_skill_invokes_reference_own_package() -> None:
    """R5b: a SKILL.md that invokes a script must invoke its OWN package (dir → _).

    Presence-based, not equality: a skill may also reference another skill's
    command, but its own ``skills.<dir>`` entry point must appear — catching a
    dir rename that left the invoke stale.
    """
    violations: list[str] = []
    for skill in _skill_manifests():
        expected = skill.parent.name.replace("-", "_")
        text = skill.read_text(encoding="utf-8")
        top_pkgs = {m.group(1).split(".")[1] for line in text.splitlines() for m in PY_M_RE.finditer(line)}
        if top_pkgs and expected not in top_pkgs:
            violations.append(f"{_rel(skill)}: invokes {sorted(top_pkgs)}, not own package '{expected}'")
    _fail(violations, "SKILL.md invoke-package/dir mismatch(es):")


# ---------------------------------------------------------------------------
# Negative controls — prove each check flags the failure it is meant to catch,
# and passes on the valid form (pattern from test_newa_cwd_pinning.py).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dotted, should_error",
    [
        ("skills.refactor.refactor", False),  # real .py leaf
        ("skills.planner.orchestrator.planner", False),  # real nested .py leaf
        ("skills.planner.cli", True),  # package, no __main__.py → not -m-runnable
        ("skills.nope.gone", True),  # missing package + module
        ("skills.refactor.does_not_exist", True),  # real package, missing leaf
        ("skills.Refactor.refactor", True),  # mis-cased segment → resolves to nothing
        ("notskills.foo.bar", True),  # non-`skills.` root guard
    ],
)
def test_module_resolution_control(dotted: str, should_error: bool) -> None:
    assert (module_resolution_error(dotted) is not None) == should_error


def test_py_m_re_captures_miscased_segment() -> None:
    """The regex must SEE a mis-cased ref so R1 can then reject it (else it's a blind spot)."""
    m = PY_M_RE.search("uv run python -m skills.Refactor.refactor --step 1")
    assert m is not None and m.group(1) == "skills.Refactor.refactor"


def test_tag_parse_survives_gt_in_quoted_attr() -> None:
    """A `>` inside a quoted attribute must not truncate the tag / drop later attrs."""
    line = '<file cmd="do <x> thing" working-dir=".claude" uri="conventions/severity.md" />'
    tags = [attrs for _p, _l, _k, attrs in _tags_in_text(line)]
    assert tags == [{"cmd": "do <x> thing", "working-dir": ".claude", "uri": "conventions/severity.md"}]


def _tags_in_text(text: str) -> list[tuple[Path, int, str, dict[str, str]]]:
    """Run TAG_RE/ATTR_RE over a literal string (for parser unit tests)."""
    out: list[tuple[Path, int, str, dict[str, str]]] = []
    for m in TAG_RE.finditer(text):
        lineno = text.count("\n", 0, m.start()) + 1
        out.append((Path("<synthetic>"), lineno, m.group(1), dict(ATTR_RE.findall(m.group(2)))))
    return out


@pytest.mark.parametrize(
    "working_dir, uri, should_error",
    [
        (".claude", "conventions/documentation.md", False),
        (".claude", "CLAUDE.md", False),  # ALWAYS_DEPLOYED under .claude
        (".claude", "conventions/ghost.md", True),
        (".claude", "conventions", True),  # a directory is not a <file> target
        # resolved relative to the working-dir root, not globally: a repo-root
        # file is absent under the skills/scripts root.
        (".claude/skills/scripts", "conventions/severity.md", True),
        (".claude/nope", "conventions/documentation.md", True),  # bad working-dir
    ],
)
def test_uri_resolution_control(working_dir: str, uri: str, should_error: bool) -> None:
    assert (uri_resolution_error(working_dir, uri) is not None) == should_error


@pytest.mark.parametrize(
    "wd, should_error",
    [(".claude", False), (".claude/skills/scripts", False), (".claude/scripts", True), ("", True)],
)
def test_working_dir_control(wd: str, should_error: bool) -> None:
    assert (working_dir_error(wd) is not None) == should_error


@pytest.mark.parametrize(
    "line, should_error",
    [
        ("uv run python -m skills.refactor.refactor --step 1", False),
        ('uv run --project "$X/.claude/skills/scripts" python -m skills.planner.cli.qr list', False),
        ('uv run --extra "a|b" python -m skills.refactor.refactor', False),  # quoted | must not split
        ("python3 -m skills.refactor.refactor --step 1", True),
        ("python -m skills.refactor.refactor", True),
        # second command is genuinely bare despite an earlier `uv run` on the line:
        ("uv run python -m skills.refactor.refactor && python -m skills.planner.cli.qr list", True),
        ("some prose with no invocation", False),
    ],
)
def test_uv_run_control(line: str, should_error: bool) -> None:
    assert (uv_run_error(line) is not None) == should_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
