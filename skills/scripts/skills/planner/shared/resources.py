"""Resource management for planner scripts.

Handles loading of resource files, path resolution, and state-directory placement.
"""

import contextlib
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from skills.lib.io import atomic_write_text, read_text_or_exit

# WHY an explicit __all__: sub-agent scripts and the two orchestrators import from this
# module by name, and the test suite pins the rest of the surface directly. The list is
# what a future split into skills/lib must keep importable under some name; everything
# else here (the _-prefixed helpers especially) is an implementation detail that split is
# free to move. Three kinds of entry qualify: something a production module imports,
# something the suite pins (a dependency the split has to honour just the same), and the
# types naming a public parameter. It sits beside the imports so a reader sees the
# surface first.
__all__ = [
    "AGENT_STATE_DIRNAME",
    "GITIGNORE_RULE",
    "PROJECT_ROOT_FILE",
    "RUNS_KEEP_NEWEST",
    "RUNS_MAX_AGE_DAYS",
    "RUNS_NAMESPACE",
    "STATE_DIR_ARG_REQUIRED",
    "PlannerResourceProvider",
    "StateDirKind",
    "ensure_agent_state_ignored",
    "ensure_project_root_recorded",
    "find_repo_root",
    "get_context_path",
    "get_exhaustiveness_prompt",
    "get_mode_script_path",
    "get_resource",
    "load_project_root",
    "render_context_file",
    "render_phase_context",
    "require_usable_state_dir",
    "resolve_project_root",
    "resolve_state_dir",
    "validate_state_dir_requirement",
]


# Contract: state_dir is REQUIRED for steps 2+. The CLI declares the flag optional
# because step 1 must be invocable without it; validate_state_dir_requirement enforces the
# real rule.
# Step 1: creates state_dir when --state-dir is absent; a supplied one is the resume path
# Steps 2+: Requires state_dir (passed from step 1)
# QR retry mode: Detected via qr-{phase}.json file inspection

# WHY STATE_DIR_ARG_REQUIRED instead of CONTEXT_FILE_ARG_REQUIRED:
# Convention over configuration. If state_dir is known, all other paths are deterministic.
# This matches the pattern: component that READS a file owns its location convention.
# Single source of truth for path derivation prevents drift across 3 sub-agent scripts.
STATE_DIR_ARG_REQUIRED = (
    ["--state-dir"],
    {"type": str, "required": True, "help": "Path to state directory (REQUIRED)"},
)


def validate_state_dir_requirement(step: int, state_dir: str | None) -> None:
    """Validate state_dir based on step.

    Raises ValueError if state_dir is required but missing.

    WHY step 1 doesn't require state_dir:
    - Step 1 (init) CREATES the state directory
    - Requiring it as input would be circular: the first run has no path to pass
    - User invokes: /plan -> step 1 creates the state dir -> passes it to step 2

    WHY steps 2+ require state_dir:
    - All workflow state persists in this directory (qa_state.json, plan.md, etc.)
    - Without it, steps can't read previous work or write outputs
    - Orchestrator passes state_dir between steps via invoke_after

    WHERE step 1 puts it: resolve_state_dir() owns the location when --state-dir is
    absent; a supplied path is honoured as the resume path. Project-local and git-ignored
    by default so state survives a /tmp reap and is attributable to the project it
    belongs to; per-session temp only as a fallback.

    WHAT BREAKS if validation changes:
    - Remove step > 1 check -> Step 1 fails spuriously (no state_dir exists yet)
    - Change to warning -> Steps silently fail later with cryptic IOErrors
    """
    if step > 1 and not state_dir:
        raise ValueError(
            f"--state-dir required for step {step}. "
            "Step 1 creates the state directory; subsequent steps require it."
        )


def get_context_path(state_dir: str) -> Path:
    """Derive context.json path from state directory.

    WHY this function: Centralizes path derivation convention. If context.json location
    changes (e.g., moves to state_dir/inputs/context.json), only this function needs updating.
    Sub-agents call this instead of manually constructing Path(state_dir) / "context.json".
    """
    return Path(state_dir) / "context.json"


# =============================================================================
# State Directory Placement
# =============================================================================

# WHY "_runs" and not ".agent-state/{planner,executor}/" directly: .agent-state/<slug>/
# is where the session task-tracking convention puts its own files, so a task slugged
# "planner" would write tasks.md into the same tree the planner mints run dirs in. The
# reservation is a convention, not something code enforces -- but a leading underscore
# is not a shape kebab-case slugs take, and unlike a dot-prefix it stays visible in
# `ls`, which durable project-local state depends on.
AGENT_STATE_DIRNAME = ".agent-state"
RUNS_NAMESPACE = "_runs"

# Appended to an existing .gitignore when .agent-state is not already ignored. Anchored
# and directory-suffixed per the git-ignore policy: matches only the repo-root directory,
# never a nested path that happens to share the name.
GITIGNORE_RULE = f"/{AGENT_STATE_DIRNAME}/"

# File inside a state dir recording the project it belongs to. Step 1 is the only step
# whose cwd is the project (see resolve_project_root); every later step arrives with
# `cd <SKILLS_DIR> && ...` already applied, so the answer has to be carried, not
# re-derived.
PROJECT_ROOT_FILE = "project_root"

# Retention for minted run dirs. A repo working tree has no reaper of its own, so
# durability would otherwise mean unbounded growth inside the user's project.
# Both bounds must be exceeded before anything is removed -- see _reap_old_runs.
RUNS_KEEP_NEWEST = 20
RUNS_MAX_AGE_DAYS = 14

# Name shape resolve_state_dir mints: <UTC yyyymmdd-HHMMSS>-<mkdtemp suffix>. The reaper
# deletes only paths matching it, so anything a user parks in the same directory is left
# alone no matter how old.
_RUN_DIR_RE = re.compile(r"\d{8}-\d{6}-")

# The two orchestrators that mint a state dir. `kind` becomes both a path component
# under _runs/ and a temp-dir prefix, so a stray value would open a second namespace
# ("Planner") or escape .agent-state/ ("../../etc"). The annotation is enforced by
# pyright, not at runtime -- which is sufficient here because `kind` is developer-
# supplied at two call sites. Environment-supplied values are a different trust class
# and ARE sanitised at runtime; see _session_token.
StateDirKind = Literal["planner", "executor"]


def _is_git_dir(git_path: Path) -> bool:
    """Whether `.git` is a real repo marker, not just a path that exists.

    A bare `exists()` test false-positives on a stray empty `.git` directory -- there is
    one at /tmp/.git and another at ~/.git on this machine, both of which git rejects
    ("not a git repository") while an exists() walk accepts as a root. The second one
    archived a plan for an unrelated project into $HOME. Mirrors git's own test: a repo
    directory has HEAD; a worktree/submodule pointer file starts with "gitdir:".
    """
    try:
        if git_path.is_dir():
            return (git_path / "HEAD").is_file()
        if git_path.is_file():
            return git_path.read_text(encoding="utf-8", errors="replace").startswith("gitdir:")
    except (OSError, ValueError):
        # ValueError rides along with OSError for symmetry with find_repo_root, where a
        # NUL-carrying path genuinely raises it from start.resolve(). Nothing here can:
        # is_dir()/is_file() absorb an embedded NUL and answer False, so read_text() --
        # the one call that would raise -- is never reached with such a path.
        return False
    return False


def find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` to find the repo root, or None if there is none.

    Supports both regular repos (.git directory) and git worktrees (.git file pointing
    at the parent repo). `start` is required: defaulting it to this module's path is
    exactly the anchoring mistake resolve_project_root exists to avoid, and a default
    that callers must be warned off is a trap rather than a convenience.

    OSError and ValueError are swallowed: the probes inside the walk absorb their own
    errors, but `start.resolve()` raises for a relative path whose cwd has been removed
    (FileNotFoundError) and for one carrying an embedded NUL (ValueError, before any errno
    exists). Either means "no repo found here", not a crash three frames up in an
    orchestrator.
    """
    try:
        current = start.resolve()
        while current != current.parent:
            if _is_git_dir(current / ".git"):
                return current
            current = current.parent
    except (OSError, ValueError):
        return None
    return None


def _resolved_home() -> Path | None:
    """$HOME fully resolved, or None when it cannot be determined.

    Resolved because find_repo_root always returns a resolved path, so comparing it
    against a bare Path.home() silently never matches when $HOME is relative or reached
    through a symlink (/home/x -> /mnt/..., NixOS impermanence, relocated or NFS homes)
    -- the guard would be present, tested, and inert.

    Path.home() raises RuntimeError where the running UID has no passwd entry, which
    some container images produce; that must not propagate out of a placement helper.
    """
    try:
        return Path.home().resolve()
    except (RuntimeError, OSError, ValueError):
        return None


def resolve_project_root() -> tuple[Path | None, str]:
    """The repo the user is working in, or None plus why it could not be determined.

    Two inputs, in order: `$CLAUDE_PROJECT_DIR` when set (Claude Code populates it for
    hook subprocesses), else the process cwd. Never this module's location -- that is
    whichever repo holds the skill source, or an un-repo'd ~/.claude for a user-global
    install, and anchoring there sends one project's state and approved plans into
    another project's repo.

    The cwd is only trustworthy where the caller has not been `cd`'d away from the
    project first. That is step 1 alone: its SKILL.md invocation uses
    `uv run --project <SKILLS_DIR>` precisely so cwd survives, while every later step
    arrives through `cd <SKILLS_DIR> && ...`. Steps after the first therefore read the
    answer step 1 recorded (see save_project_root / load_project_root) instead of
    calling this.

    WHY the reason string: both callers report the degradation to the user, and the two
    None cases need different wording. Returning it keeps the input names in one place
    instead of re-derived at each call site. On success the reason is "" -- the pair is
    (Path, "") or (None, non-empty), never anything else.
    """
    anchor = os.environ.get("CLAUDE_PROJECT_DIR", "")
    # .strip() decides whether it is SET, but the value is passed through untouched:
    # trailing whitespace is legal in a directory name, and trimming it looks for a repo
    # at a path that does not exist.
    if anchor.strip():
        root = find_repo_root(Path(anchor))
        if root is None:
            return None, f"no git repository at or above CLAUDE_PROJECT_DIR ({anchor})"
        return root, ""

    try:
        cwd = Path.cwd()
    except OSError as e:
        return None, f"CLAUDE_PROJECT_DIR is unset and the working directory is unreadable ({e})"
    root = find_repo_root(cwd)
    if root is None:
        return None, f"CLAUDE_PROJECT_DIR is unset and no git repository at or above cwd ({cwd})"
    if root == _resolved_home():
        # Only when STUMBLED INTO: the walk climbs to /, so a cwd outside any project
        # plus a dotfiles repo at $HOME resolves the "project" to the home directory --
        # state into ~/.agent-state/, a rule into ~/.gitignore, plans into ~/docs/plans/.
        # That is exactly the misfiling this anchor exists to stop. An explicit
        # CLAUDE_PROJECT_DIR naming $HOME is honoured above, because that is a choice.
        return None, f"CLAUDE_PROJECT_DIR is unset and cwd ({cwd}) resolves only to $HOME"
    return root, ""


# Why a recorded marker cannot be used, one kind per OUTCOME -- what differs within a
# kind belongs in the `reason` string, which is what the user reads. Constants rather
# than substrings of a prose message: rewording a warning must not silently flip the
# decision to replace a marker. Module-internal, so they stay out of __all__.
#
#   _MARKER_OK       usable
#   _MARKER_MISSING  nothing recorded yet -- write one, no warning
#   _MARKER_CORRUPT  content this planner provably did not write -- announce, replace
#   _MARKER_KEEP     not usable and not safe to overwrite -- announce, leave alone
_MARKER_OK = ""
_MARKER_MISSING = "missing"
_MARKER_CORRUPT = "corrupt"
_MARKER_KEEP = "keep"


def _save_project_root(state_dir: str, root: Path) -> bool:
    """Write the project marker. True on success, False after reporting the failure.

    Private on purpose: recording identity on one path and forgetting it on the others
    is the defect ensure_project_root_recorded exists to prevent, and a public write
    primitive next to the wrapper that preserves the invariant re-opens that door.

    Atomic, unlike the .gitignore append: this REPLACES the whole file, so two step-1
    runs sharing one --state-dir could otherwise interleave a truncate and a write and
    leave a spliced path. Such a path decodes fine, is not a repo, and classifies as
    _MARKER_KEEP -- a state this module deliberately never overwrites, so the run's
    identity would be lost permanently. (The .gitignore case is the opposite: an
    append must not replace a file another writer is extending.)

    Non-fatal: the marker is what the terminal docs/plans save reads, so losing it
    degrades that one step rather than the run. ValueError joins OSError for a path
    carrying an embedded NUL, which raises before any errno exists.
    """
    if "\n" in str(root):
        # One line is the whole format, so such a path cannot round-trip: it reads back
        # as content this planner did not write and the run gets re-pointed at whichever
        # project the shell is in. Refusing to record is the honest failure.
        print(
            f"Warning: not recording project {root!r} -- a project path containing a "
            "newline cannot be stored",
            file=sys.stderr,
        )
        return False
    try:
        atomic_write_text(Path(state_dir) / PROJECT_ROOT_FILE, f"{root}\n")
    except (OSError, ValueError) as e:
        print(f"Warning: could not record project root in {state_dir}: {e}", file=sys.stderr)
        return False
    return True


def _close_quietly(fd: int) -> None:
    """Close `fd`, absorbing a close-time error.

    close() releases the descriptor even when it reports failure, so there is nothing to
    retry and nothing leaks. What it can report is a deferred write-back error -- NFS
    surfaces one here rather than at write() -- and that must not become a traceback out
    of step 1, which calls resolve_state_dir bare in both orchestrators.

    Swallowing is safe because neither caller trusts the descriptor for its verdict: the
    marker read already holds its bytes by this point, and the .gitignore append is
    confirmed by a fresh `git check-ignore`, which reads the file back from disk.
    """
    with contextlib.suppress(OSError):
        os.close(fd)


def _read_all(fd: int) -> bytes:
    """Every byte of `fd` from offset 0, without disturbing its file position.

    pread rather than read: it takes its offset as an argument, so this neither needs a
    seek to start nor moves a position the caller shares -- the .gitignore descriptor is
    also the one _append_gitignore_rule writes through. (O_APPEND governs writes only,
    so that descriptor's read position is 0 either way; independence is the property
    worth having, not a fix for a broken starting offset.)
    """
    chunks = []
    offset = 0
    while chunk := os.pread(fd, 65536, offset):
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _read_marker(state_dir: str) -> tuple[Path | None, str, str]:
    """The recorded project, a human-readable reason, and a _MARKER_* kind.

    The kind is what ensure_project_root_recorded dispatches on; the reason is what the
    user reads. Separating them keeps a reworded message from changing behaviour.

    Every consumer classifies here, so the file-type check lives here too: a marker
    that is not a regular file must not be trusted by the terminal docs/plans save any
    more than by the recorder. Splitting that judgement across the two gives them
    different answers, with step 1 refusing the marker while _save_plan_to_docs follows
    it into another repo.

    Two questions decide _MARKER_CORRUPT vs _MARKER_KEEP, in order:

    1. Is this a regular file whose bytes we can read? A wrong file type or a failed
       read answers "unknown" -- nothing is overwritten on an unknown.
    2. Could _save_project_root have produced these bytes? It writes a single-line
       ABSOLUTE path, always, because find_repo_root resolves. Empty, relative, or
       carrying a non-blank remainder after its first line answers no -- provably not
       ours, safe to overwrite. A trailing blank line or NUL tail is NOT such a
       remainder: our own write survives intact ahead of it, and an editor "fixing" the
       file on save or a post-crash ext4 tail produces exactly that. Undecodable bytes
       are NOT a separate test: they are decoded lossily and judged on that same shape,
       because a decode failure only proves "not ours" for an all-ASCII path. The
       shape test is deliberately one-sided: garbage that happens to decode to
       something absolute and single-line is KEPT, not replaced. Keeping something
       replaceable costs a stale marker the user can delete; replacing something
       keepable costs the run its identity.

    A TRUNCATED absolute path is not separable this way either: "/home/u/proj" cut short
    is byte-for-byte what a moved or deleted project looks like, so both are kept.
    Nothing here can originate a truncated marker -- _save_project_root is atomic -- so
    that case covers markers already on disk from another writer, and hardware faults.
    Making it decidable needs a format change (a trailing sentinel), not a heuristic.
    """
    marker = Path(state_dir) / PROJECT_ROOT_FILE
    # ONE descriptor decides the type and supplies the bytes. Checking the path and then
    # re-opening it is check-then-use: whatever satisfied the check can be swapped before
    # the read, and the read is where the damage lands. A descriptor is pinned to an
    # inode, so nothing can be substituted once it is open.
    #   O_NOFOLLOW -- a symlink raises ELOOP rather than letting whoever planted it
    #                 choose which repository the approved plan lands in.
    #   O_NONBLOCK -- a FIFO opens instead of blocking forever, so fstat can reject it;
    #                 without it step 1 hangs in both orchestrators with nothing on
    #                 stderr.
    try:
        fd = os.open(marker, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None, f"no project root recorded in {state_dir}", _MARKER_MISSING
    except (OSError, ValueError) as e:
        return None, f"cannot read {marker}: {e}", _MARKER_KEEP
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None, f"{marker} is not a regular file", _MARKER_KEEP
        # errors="replace", not a UnicodeDecodeError branch: a decode failure is only
        # evidence of "not ours" for an all-ASCII path. A project at 项目 whose marker is
        # truncated mid-character fails to decode while still being our own truncated
        # write -- the case that must be KEPT. Decoding lossily leaves it absolute and
        # single-line, so it falls through to the repo check and is kept. Foreign bytes
        # are replaced only when the lossy decode leaves something empty, relative, or
        # multi-line; anything else is kept, deliberately -- see the docstring above.
        raw = _read_all(fd).decode("utf-8", errors="replace")
    except OSError as e:
        # Content NOT read: a file-level EACCES, an EIO, a stale NFS handle. The bytes
        # may be a perfectly good project this run belongs to -- replacing them on a
        # guess is the silent re-point this module exists to prevent, so an unknown
        # marker is kept.
        return None, f"cannot read {marker}: {e}", _MARKER_KEEP
    finally:
        _close_quietly(fd)

    # removesuffix, not strip: _save_project_root appends exactly one newline, and
    # strip() also eats trailing whitespace that is part of a legal directory name --
    # reading back a path that never existed, and reporting it KEEP forever. Leading
    # whitespace needs no trimming; the is_absolute() test below rejects it.
    body = raw.removesuffix("\n")
    # Judge the FIRST line and require everything after it to be padding. A trailing
    # blank line (an editor "fixing" the file on save) or a NUL tail (the post-crash
    # ext4 shape) leaves our own single-line write intact ahead of it; classifying those
    # as foreign replaces a marker whose payload is perfectly good, which re-points the
    # run at whichever repo the resuming shell happens to sit in. Two real paths
    # ("/a\n/b") are something _save_project_root provably did not write, so a non-blank
    # remainder still classifies CORRUPT.
    recorded, _, trailing = body.partition("\n")
    if not recorded:
        # A blank FIRST line is not an empty file. Both are ours to replace, but "is
        # empty" is a claim about the marker the user will go and look at, and a
        # zero-length file reads very differently from one whose second line is a path.
        if body:
            return (
                None,
                f"{marker} begins with a blank line, which this planner did not write",
                _MARKER_CORRUPT,
            )
        return None, f"{marker} is empty", _MARKER_CORRUPT
    if trailing.strip("\n\x00 \t\r") or not Path(recorded).is_absolute():
        # repr'd: the content is arbitrary bytes here, and a raw newline would split the
        # warning across two lines.
        return (
            None,
            f"{marker} holds {body!r}, which this planner did not write",
            _MARKER_CORRUPT,
        )

    root = Path(recorded)
    if not _is_git_dir(root / ".git"):
        # repr'd: a CRLF-terminated marker leaves a trailing CR inside the path, and an
        # unquoted message would show a directory that looks exactly right.
        return None, f"recorded project {str(root)!r} is no longer a git repository", _MARKER_KEEP
    return root, "", _MARKER_OK


def load_project_root(state_dir: str) -> tuple[Path | None, str]:
    """The project `state_dir` belongs to, or None plus why it is unusable.

    Re-checks that the recorded path is still a repo root, and refuses a marker that is
    not a regular file: a state dir can outlive the checkout it was minted against, and
    writing a plan into a directory that is no longer a repo -- or into whichever repo a
    planted link names -- is worse than declining.
    """
    root, reason, _ = _read_marker(state_dir)
    return root, reason


def ensure_project_root_recorded(state_dir: str) -> None:
    """Record which project `state_dir` belongs to, replacing an unusable marker.

    WHY this is step 1's job and not resolve_state_dir's: identity is independent of
    placement. A run whose state lands in temp -- or that resumes into a caller-supplied
    --state-dir, which never reaches resolve_state_dir at all -- still belongs to a
    project, and the terminal docs/plans save needs to know which. Recording on the
    project-local branch alone would leave the likeliest first-run shape (a fresh
    `git init` with no .gitignore, which declines project-local and falls back to temp)
    unable to archive its approved plan.

    WHY it replaces rather than checking mere presence: a marker this planner could not
    have written would otherwise be permanent -- every resume short-circuits on the file
    existing, and the terminal step reports the same failure forever with no recovery
    but deleting it by hand.

    TWO outcomes are reported and NOT replaced -- _MARKER_KEEP, and a usable marker
    naming a different project than this shell sits in -- for one reason: overwriting
    would re-point a run minted in project A at project B, which is the "wrote into a
    repo nobody asked about" defect this whole mechanism exists to prevent. The recorded
    value is the run's identity; the shell that happens to resume it is not.

    Every path out of here says something on stderr. A supplied --state-dir never calls
    resolve_state_dir, so no _fallback message covers it either -- staying silent would
    leave a run with no identity and no hint of it until the plan is already built.
    """
    recorded, reason, kind = _read_marker(state_dir)
    live, live_reason = resolve_project_root()

    if kind == _MARKER_OK:
        if live is not None and live != recorded:
            print(
                f"Warning: {state_dir} records project {recorded}, but this shell is in "
                f"{live}. Keeping {recorded} -- the run's plan belongs to it. Delete "
                f"{Path(state_dir) / PROJECT_ROOT_FILE} if this state dir is being "
                f"reused for new work.",
                file=sys.stderr,
            )
        else:
            print(f"Note: state dir belongs to project {recorded}", file=sys.stderr)
        return

    if kind == _MARKER_KEEP:
        print(
            f"Warning: {reason}; leaving it as it is. Delete "
            f"{Path(state_dir) / PROJECT_ROOT_FILE} if this run should adopt the "
            f"project this shell is in.",
            file=sys.stderr,
        )
        return

    if live is None:
        # Checked before announcing a replacement: there is nothing to replace it WITH,
        # and "replacing it" followed by an unchanged marker is worse than one message
        # naming the real problem.
        print(f"Warning: not recording a project for {state_dir} -- {live_reason}", file=sys.stderr)
        return

    if kind == _MARKER_CORRUPT:
        # States the problem only. The outcome is announced by whichever branch below
        # actually happens -- _save_project_root can still refuse (an unstorable path, a
        # failed write), and claiming a replacement before attempting one is the same
        # false message the live-is-None guard above removes.
        print(f"Warning: {reason}", file=sys.stderr)
    elif kind != _MARKER_MISSING:
        # Only MISSING and CORRUPT may reach a replacement. Naming them both keeps a
        # kind added later from inheriting "overwrite the marker" by falling through --
        # which is the decision this function is most careful about everywhere else.
        print(
            f"Warning: {state_dir} has an unhandled marker state; leaving it as it is",
            file=sys.stderr,
        )
        return
    if _save_project_root(state_dir, live):
        print(f"Note: state dir belongs to project {live}", file=sys.stderr)


def require_usable_state_dir(state_dir: str) -> None:
    """Exit with one clear line when `state_dir` cannot hold this run's state.

    In practice only a caller-supplied --state-dir fails this; resolve_state_dir returns
    a directory it just created. Missing, or a file rather than a directory, are caller
    mistakes rather than degradations, because every later step writes into this path.

    Existence only -- NOT writability. A directory that exists but cannot be written is
    left to the individual writes, which degrade with their own messages; probing
    permissions here would be advisory anyway on ACL filesystems, and a false reject is
    worse than a late one.

    Called by BOTH orchestrators at step 1 before anything touches the directory, and
    again for steps 2+ before the plan.json read -- so a state dir that has been reaped or
    deleted reads as this message rather than as "plan.json not found", which names a file
    and invites a fix that recreates the directory without its project marker.
    """
    try:
        if not Path(state_dir).is_dir():
            sys.exit(f"Error: state directory {state_dir} is missing or not a directory")
    except OSError as e:
        # is_dir() absorbs an embedded NUL (returns False, so the branch above reports
        # it) but re-raises EACCES from an unsearchable ancestor.
        sys.exit(f"Error: state directory {state_dir} is unusable: {e}")


def _check_ignored(repo_root: Path, relative_path: str) -> bool | None:
    """Tri-state git check-ignore for `relative_path`, resolved against `repo_root`.

    True ignored, False not ignored, None git could not answer (binary missing, not a
    repo, dubious ownership, timeout, or a path reached "beyond a symbolic link" -- git
    refuses those, which is what keeps a symlinked `.agent-state` from being written
    through; the refusal is git's, not a check here).

    None is a distinct case because it is the one where the caller must not try to fix the
    situation by editing .gitignore: a probe that cannot answer cannot verify the edit.

    WHY cwd=repo_root: check-ignore resolves a relative path against the process cwd,
    not against the repo it is asked about. A drifted cwd silently probes the wrong
    repository and reports a confident wrong answer.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", relative_path],
            cwd=repo_root,
            # GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE override cwd discovery outright, so
            # inheriting them reintroduces the wrong-repository answer cwd= is set to
            # prevent -- through the other door. Scrubbing the whole GIT_ prefix also
            # drops config overrides (GIT_CONFIG_GLOBAL, GIT_CONFIG_COUNT/KEY/VALUE):
            # accepted, because this probe wants the repository's real ignore rules, not
            # a caller's substituted config. HOME and XDG_CONFIG_HOME are left alone --
            # they are not GIT_-prefixed, and a global excludesFile is part of those real
            # rules rather than a redirection to another repository.
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        # ValueError for a repo_root carrying an embedded NUL. No caller can currently
        # produce one -- resolve_state_dir's root is resolved and existence-checked, and
        # it is the only production path in. Kept because the cost is one except clause
        # and the alternative is a subprocess-layer traceback out of a helper whose whole
        # contract is a tri-state answer; not kept on the strength of a hypothetical
        # caller.
        return None
    if result.returncode in (0, 1):
        return result.returncode == 0
    return None


def _tracks_anything(repo_root: Path, relative_dir: str) -> bool | None:
    """Whether git tracks any path under `relative_dir`. None when git cannot answer.

    _check_ignored deliberately passes --no-index, so it answers about the ignore RULES
    and is blind to the index. That is the right question for "would a new file here be
    ignored" and the wrong one for "may I add this rule at all": an anchored rule over a
    directory the user committed does not untrack what is already in the index, but it
    does make every NEW file under it invisible. Committed content is the plainest form
    of expressed intent there is, so Rule B declines rather than reinterpreting it.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", relative_dir],
            cwd=repo_root,
            # Same GIT_* scrub and reasoning as _check_ignored: an inherited GIT_DIR or
            # GIT_INDEX_FILE would answer for a different repository's index.
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip(b"\x00"))


def _has_rule(raw: bytes) -> bool:
    """Whether GITIGNORE_RULE already occupies an ACTIVE line of `raw`.

    Compared as bytes, split on b"\\n", so a CRLF-authored file is judged on its real
    lines without a decode (and a later write's re-encode) touching them. The caller
    supplies bytes it already read from its own descriptor -- re-reading by path here
    would reintroduce the check-then-use gap that descriptor exists to close.

    rstrip, never strip: gitignore syntax drops trailing whitespace but treats LEADING
    whitespace as part of the pattern, so "  /.agent-state/" is a pattern with two
    leading spaces that matches nothing. Stripping both ends reads that inactive line as
    the rule already being present, and the caller then declines to add the real one --
    a mis-indented line silently defeating the fix.
    """
    target = GITIGNORE_RULE.encode()
    return any(line.rstrip() == target for line in raw.split(b"\n"))


def _append_gitignore_rule(fd: int, name: Path) -> None:
    """Append GITIGNORE_RULE on its own line, without a read-modify-write cycle.

    Takes a descriptor, not a path: the caller opened the file once with O_NOFOLLOW and
    checked its type through that descriptor. Re-opening by path here would undo both --
    a swap between the check and this write lands the append in whatever the path names
    by then, which is how a rule ends up inside a file outside the repo.

    WHY O_APPEND and not read_text + write_text (nor lib.io.atomic_write_text): both of
    those REPLACE the file, so a concurrent edit -- by the user's editor, or by a second
    orchestrator's step 1 -- is clobbered wholesale. An O_APPEND write only ever adds at
    the true end of file, whoever else is writing.

    The WRITE is atomic; the decision to write is not. `_has_rule` then append is
    check-then-act, so two concurrent step-1 runs can each append a copy. Git treats
    repeated identical anchored rules as a no-op, so the outcome stays correct and the
    cost is a duplicated line -- cheap enough that a lock file guarding a user's
    .gitignore is not worth it. (POSIX O_APPEND atomicity also does not hold on NFS.)

    WHY an unconditional leading newline: knowing whether one is needed means reading
    the last byte first, and between that read and the write another appender can move
    the end. Git treats the resulting blank line as a no-op, so one blank line is
    cheaper than a rule glued onto someone else's last line.

    Appended after everything, including any allowlist: later matches win, so the rule
    re-ignores .agent-state even under a "*" + "!/src/" whitelist model.
    """
    # Looped because os.write may write fewer bytes than asked (ENOSPC nearing a full
    # disk, or an interrupted write), and a partial write leaves a truncated pattern like
    # "/.agent-stat" in the user's tracked file. The interleaving another appender could
    # cause between the two halves is already possible for whole rules -- see the
    # duplicate-line note above -- but a torn rule matches the wrong paths rather than
    # repeating harmlessly.
    #
    # `name` is for the message only; the write still goes through the descriptor the
    # caller opened and type-checked, never through a re-opened path.
    payload = f"\n{GITIGNORE_RULE}\n".encode()
    written = 0
    try:
        while written < len(payload):
            written += os.write(fd, payload[written:])
    except OSError:
        if written:
            # The caller turns this exception into "could not append", which reads as
            # "nothing happened". Part of the rule IS on disk, in a version-controlled
            # file, so it is said here rather than left to a message that denies it.
            print(
                f"Warning: only part of {GITIGNORE_RULE} reached {name}; the truncated "
                "line matches paths the real rule does not, and should be removed by hand",
                file=sys.stderr,
            )
        raise


def ensure_agent_state_ignored(repo_root: Path, probe: str) -> tuple[bool, str]:
    """Make `probe` git-ignored in `repo_root` if it is not already, by ignoring `.agent-state`.

    `probe` is the path whose ignore status actually matters -- the caller's own runs
    directory. Hardcoding a synthetic `<AGENT_STATE_DIRNAME>/probe` here would ask about a
    file nothing ever creates, and a rule matching that BASENAME (a bare `probe`, or
    `*probe*`) answers "ignored" for it while the run directory beside it stays plainly
    visible to git.

    PRECONDITION: `probe` must be under AGENT_STATE_DIRNAME. Only that directory's rule is
    appended and only its index is consulted, so a probe outside it gets an append that
    cannot affect the answer, followed by a re-probe that fails -- a mutation of the user's
    file for nothing. The dirname becomes a parameter when this moves to skills/lib
    (see DEFERRED.md); until then the pairing is the caller's to keep.

    Returns (True, "") when it is ignored, or (False, reason) naming which decline
    happened -- the caller prints that reason, so every path out of here is
    distinguishable to whoever is asking why their state went to /tmp.

    TWO RULES govern every decline below; new cases should fall out of them rather than
    being added ad hoc:
      A. Only mutate when the effect can be verified before and after. An unanswerable
         probe means an unverifiable edit.
      B. Only mutate within the narrowest unambiguous scope: append to a file this repo
         owns, never author policy, never overwrite intent.

    WHY git check-ignore and not a text scan of .gitignore: ignore rules compose (nested
    files, excludesfile, negative whitelists). A repo whose .gitignore is "*" plus an
    anchored allowlist already ignores .agent-state without naming it; a literal-string
    check reads that as "not ignored" and appends a redundant rule. --no-index so the
    answer comes from the ignore rules alone: without it git reports a path that happens to
    be in the index as NOT ignored, which is a true statement about tracking and the wrong
    answer to "may I create state here". The probe path need not exist on disk either way;
    check-ignore answers for a pathname, not for a file.

    WHY it announces the append the moment it lands, not once it is confirmed: the write
    is to a version-controlled file the user authored, reached indirectly from
    resolve_state_dir. Announcing only on success leaves the confirm-failed path
    mutating their tree with nothing on stderr -- which is the exact outcome the
    announcement exists to prevent.
    """
    ignored = _check_ignored(repo_root, probe)
    if ignored is True:
        return True, ""
    if ignored is None:
        # Rule A: git cannot say, so an edit cannot be checked. Leave the file alone.
        return False, f"git cannot determine ignore status in {repo_root}"

    tracked = _tracks_anything(repo_root, AGENT_STATE_DIRNAME)
    if tracked is None:
        # Rule A again, for the other question this decision depends on.
        return (
            False,
            f"git cannot determine what is tracked under {AGENT_STATE_DIRNAME} in {repo_root}",
        )
    if tracked:
        # Rule B: the user committed files here. The rule would not untrack those, but it
        # would hide every new one -- reinterpreting a decision they made explicitly.
        return False, (
            f"{repo_root} tracks files under {AGENT_STATE_DIRNAME}; {GITIGNORE_RULE} would "
            "hide every new file there while leaving the committed ones tracked"
        )

    gitignore = repo_root / ".gitignore"
    try:
        # Rule B: authoring a .gitignore means choosing a whole ignore policy for
        # someone else's repo -- the negative-whitelist treatment is a judgement call a
        # state-dir helper must not make silently.
        # ONE descriptor for the type check, the read, and the append. Checking the
        # path and re-opening it to write is check-then-use: a swap in between sends
        # the append through whatever the path names by then -- observed landing a rule
        # inside a file outside the repo entirely. O_NOFOLLOW makes a symlink raise
        # ELOOP here, which is Rule A's refusal (git will not read one either); fstat
        # rejects every other non-regular type.
        fd = os.open(gitignore, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW)
    except FileNotFoundError:
        return False, f"{repo_root} has no .gitignore to add {GITIGNORE_RULE} to"
    except (OSError, ValueError) as e:
        return False, f"cannot open {gitignore}: {e}"

    try:
        action = "inspect"
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return False, f"{gitignore} is not a regular file"
        action = "read"
        existing = _read_all(fd)
        # Rule B: the rule is already an active line, yet the path is still not ignored,
        # so something later un-ignores it -- most plainly a deliberate "!.agent-state"
        # the user wrote. A second copy would duplicate the rule and reverse their intent.
        if _has_rule(existing):
            return (
                False,
                f"{GITIGNORE_RULE} is present in {gitignore} but something later un-ignores it",
            )
        action = f"append {GITIGNORE_RULE} to"
        _append_gitignore_rule(fd, gitignore)
    except OSError as e:
        return False, f"could not {action} {gitignore}: {e}"
    finally:
        _close_quietly(fd)
    print(f"Note: appended {GITIGNORE_RULE} to {gitignore}", file=sys.stderr)

    # Re-probe rather than trusting the append: writing state into a tracked path is
    # worse than falling back to temp. The mutation is already announced above, so a
    # failure here reports what was written AND that it did not take.
    if _check_ignored(repo_root, probe) is True:
        return True, ""
    return False, (
        f"appended {GITIGNORE_RULE} to {gitignore} but {AGENT_STATE_DIRNAME} is still "
        "not ignored -- the line is written and can be removed by hand"
    )


def _session_token() -> str:
    """Stable per-session token for the temp fallback, or a random one.

    CLAUDE_CODE_SESSION_ID groups a session's run dirs under one parent so they can be
    attributed and reaped together. Absent it, a random token still satisfies the
    load-bearing property: nothing lands at the flat /tmp/{planner,executor}-* prefix
    that another session's cleanup glob would sweep.
    """
    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    # Path-safe ASCII subset only: the value becomes a directory name, and a stray "/"
    # or ".." from a malformed env var would escape the tmpdir. str.isalnum() alone is
    # Unicode-aware and would pass arbitrary UTF-8 through into a path. Truncated
    # because a long id pushes the cc-<session> PARENT component past NAME_MAX (255) --
    # the mkdtemp child is "<kind>-XXXXXXXX" and does not vary with the id at all; 64
    # chars keeps sessions distinct.
    safe = "".join(c for c in session if c.isascii() and (c.isalnum() or c in "-_"))[:64]
    return safe or secrets.token_hex(4)


def _last_activity(path: Path) -> float:
    """Newest mtime anywhere under `path`, including `path` itself.

    A directory's own mtime moves only when an entry is created, renamed, or unlinked --
    an in-place rewrite of plan.json leaves it untouched. Keying retention on the
    directory alone therefore calls a run stale while it is being actively edited.

    Walks the whole subtree, not just direct children: the state dir is flat today, but
    a run whose only recent write is one level deeper would otherwise be invisible to
    this and get reaped while live.

    Raises rather than judging on a partial view. A directory this cannot list is one
    rmtree cannot remove either -- it unlinks the entries it reaches and then fails at
    that child -- so a run judged on the readable part of its tree would be partially
    destroyed rather than reaped, which is the one outcome retention must never produce.
    _reap_old_runs leaves such a run whole for the pass.

    lstat for every entry in the WALK: a symlink reports as S_ISLNK rather than S_ISDIR,
    so it cannot be followed out of the state dir and cannot cycle. The root is stat'ed,
    not lstat'ed -- it is the run dir itself, which _reap_old_runs has already refused to
    treat as a candidate if it is a link.
    """
    newest = path.stat().st_mtime
    stack = [path]
    while stack:
        for child in stack.pop().iterdir():
            info = child.lstat()
            newest = max(newest, info.st_mtime)
            if stat.S_ISDIR(info.st_mode):
                stack.append(child)
    return newest


def _reap_old_runs(parent: Path) -> None:
    """Delete run dirs under `parent` that are both surplus and stale.

    /tmp reaps itself; a project working tree does not, so durable state would
    otherwise grow one directory per invocation forever inside the user's repo.

    FOUR guards, all required together, because the thing being deleted is someone's
    planning state:
      - name matches _RUN_DIR_RE, so an unrelated directory parked here is left alone
        unless its name happens to take the minted shape (the regex is a prefix test,
        and _runs/<kind>/ is machine-managed rather than a place to keep things);
      - rank beyond RUNS_KEEP_NEWEST by name (the stamp sorts chronologically);
      - no activity for RUNS_MAX_AGE_DAYS, measured across the run dir and everything
        beneath it, so a session still being worked on is safe however many runs follow it;
      - not a symlink, so a planted link is never handed to rmtree and never stat'ed
        through -- _last_activity would otherwise report the TARGET's mtime.

    Deliberately NOT keyed on whether a plan was approved. A planner run dir does record
    it -- plan.md has one writer, and its only caller sits behind the terminal gate -- but
    approval is the wrong signal to key on: the run that must survive is the UNapproved one
    still being worked, while an approved plan has already been published to docs/plans/.
    An executor run dir has no plan.md at all. Age plus count protects in-progress work
    without inferring intent.

    Non-fatal throughout: failing to reap is untidy, failing a run is not acceptable. A
    candidate whose subtree cannot be fully examined -- or that another orchestrator
    removed between the listing and the judgement -- is left whole for the pass rather
    than judged on the part that could be read.
    """
    try:
        candidates = sorted(
            (p for p in parent.iterdir() if p.is_dir() and _RUN_DIR_RE.match(p.name)),
            key=lambda p: p.name,
            reverse=True,
        )
    except OSError:
        return

    cutoff = datetime.now(UTC).timestamp() - RUNS_MAX_AGE_DAYS * 86400
    for path in candidates[RUNS_KEEP_NEWEST:]:
        try:
            if path.is_symlink() or _last_activity(path) >= cutoff:
                continue
            shutil.rmtree(path)
        except OSError:
            continue


def _created_ancestors(leaf: Path, stop: Path) -> list[Path]:
    """The components of `leaf` below `stop` that do not exist yet, deepest first.

    Captured BEFORE the mkdir so the take-back knows what it is entitled to remove.
    rmdir alone is not that guarantee: it refuses a non-empty directory, but an EMPTY
    `.agent-state/` a user made by hand is just as removable as one we made, and Rule B
    says the narrowest unambiguous scope, never someone else's intent.
    """
    if stop not in leaf.parents:
        # Containment is a precondition, not something to work around: without it the
        # walk climbs past `stop` and _prune_empty could rmdir outside the repo. Today
        # the single call site guarantees it; this keeps that true after the move
        # recorded in DEFERRED.md puts the helper in a shared module.
        return []
    missing = []
    current = leaf
    while current != stop and current != current.parent:
        if current.exists():
            break
        missing.append(current)
        current = current.parent
    return missing


def _prune_empty(created: list[Path]) -> None:
    """Remove the directories in `created`, deepest first, while they stay empty.

    Takes an explicit list rather than walking a path, so it can only reach directories
    this run brought into existence -- never a pre-existing empty `.agent-state/`, never
    a sibling run dir, never `.agent-state/<task-slug>/` from the task-tracking
    convention. rmdir refusing a non-empty directory is then a second line of defence
    rather than the only one.

    A missing entry is skipped rather than stopping the walk: a partial
    `mkdir(parents=True)` leaves the shallow components behind while the leaf never
    appeared, and those are still ours to take back.

    Concurrency: two orchestrators starting in one repo can interleave, and a declining
    one can remove `_runs/` in the window after the other created it and before it
    created `<kind>/` beneath. The victim's mkdtemp then raises FileNotFoundError, which
    resolve_state_dir turns into a temp fallback -- a degrade, not a corruption. Closing
    that window means evaluating the ignore gate before creating anything, which requires
    holding the .gitignore descriptor open across the mkdir to keep the O_NOFOLLOW
    check-then-use guarantee. One speculative mkdir is the cheaper trade.
    """
    for path in created:
        try:
            path.rmdir()
        except FileNotFoundError:
            continue
        except OSError:
            return


def _is_our_private_dir(path: Path) -> bool:
    """Whether `path` is a directory we own that no one else can write.

    lstat, never stat: a symlink must fail S_ISDIR here. Following one lands on whatever
    it points at, and a link to a 0700 directory of ours -- `~/.ssh`, say -- satisfies
    every other test on this list while still putting the run inside it.

    Exactly 0o700, in both directions. Group or other bits open means someone who is not
    us can unlink an in-flight run dir out of it -- the property being checked. Missing
    OWNER bits mean we cannot create inside it: mkdtemp then raises and _temp_state_dir
    turns that into sys.exit, so a single unwritable directory at this predictable name
    aborts every step 1 for the rest of the session, with an errno that never names the
    directory to delete. Declining costs an unguessable parent; adopting costs the run.
    """
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o700
    )


def _mkdtemp_usable(prefix: str, parent: Path) -> str:
    """mkdtemp, then guarantee the result is one we can actually write into.

    mkdtemp asks for 0o700 and the umask masks it, so a umask with OWNER bits set yields a
    directory nobody can write -- including us. Returning that defers the failure to the
    first write, which is worse than declining: the caller has a path, announces it, and
    the run dies later somewhere that does not name the cause.

    Only owner bits can be missing; a umask cannot ADD group or other bits, so this can
    never loosen anything. Suppressed because a directory we just created and cannot
    chmod is not worth a second error path -- the write that follows will say so.
    """
    created = tempfile.mkdtemp(prefix=prefix, dir=parent)
    with contextlib.suppress(OSError):
        Path(created).chmod(0o700)
    return created


def _session_parent(tmpdir: Path) -> Path:
    """`tmpdir/cc-<session>` when it is a private directory of ours, else an unguessable one.

    The grouping name derives from CLAUDE_CODE_SESSION_ID, which is not a secret: it is
    also the basename of ~/.claude/projects/<slug>/<session>.jsonl, so any local user
    with a readable home can compute this path. Accepting whatever already sits there
    means accepting a 0777 directory someone else can unlink run dirs from, or a symlink
    pointing the whole run into their tree.

    An unguessable 0700 directory is the floor this must not fall below, so a parent we
    cannot vouch for is not repaired and not adopted -- mkdtemp mints an unguessable one
    instead. Grouping by session is a convenience for attribution; it is not worth a
    hijacked run dir. The decline is announced, because every other decline in this
    module is, and this is the one with an adversarial reading.

    The load-bearing property holds on both paths: nothing lands at the flat
    /tmp/{planner,executor}-* prefix another session's cleanup glob would sweep.
    """
    parent = tmpdir / f"cc-{_session_token()}"
    try:
        parent.mkdir(mode=0o700)
    except FileExistsError:
        if _is_our_private_dir(parent):
            return parent
        print(
            f"Note: {parent} is not a private directory of ours; grouping this session's "
            "runs under an unguessable temp parent instead",
            file=sys.stderr,
        )
    except OSError as e:
        print(
            f"Note: cannot create {parent} ({e}); using an unguessable temp parent", file=sys.stderr
        )
    else:
        # A umask only CLEARS bits, so the group/other half of the vouching test is
        # already guaranteed here. What it can clear is the OWNER bits: under a umask
        # like 0700 the new directory is unusable and mkdtemp inside it would fail,
        # turning a degrade into a hard exit. Re-asserting costs one syscall.
        with contextlib.suppress(OSError):
            parent.chmod(0o700)
        return parent
    return Path(_mkdtemp_usable("cc-", tmpdir))


def _temp_state_dir(kind: StateDirKind) -> str:
    """Per-session temp fallback: <tmpdir>/cc-<session>/<kind>-<rand>/.

    Exits rather than raising: this is the last resort, so failing here means no state
    dir at all, and every caller would only turn the exception into the same message.
    Mirrors lib.io.read_text_or_exit, the codebase's idiom for an unrecoverable I/O
    failure inside a helper, and lets both orchestrators call resolve_state_dir bare.
    """
    tmpdir = Path(tempfile.gettempdir())
    try:
        return _mkdtemp_usable(f"{kind}-", _session_parent(tmpdir))
    except OSError as e:
        sys.exit(f"Error: failed to create {kind} state directory: {e}")


def _fallback(kind: StateDirKind, reason: str) -> str:
    """Take the temp branch, saying why project-local was declined.

    Every condition that declines project-local routes here and the returned str cannot
    distinguish them, so "why is my state in /tmp again?" would otherwise be answerable
    only by re-deriving the predicates by hand.
    """
    print(f"Note: {kind} state dir falls back to temp ({reason})", file=sys.stderr)
    return _temp_state_dir(kind)


def resolve_state_dir(kind: StateDirKind) -> str:
    """Create and return a state directory for `kind`.

    THREE SIDE EFFECTS beyond creating the directory, all on the project-local path:
    it may append `/.agent-state/` to the project's existing .gitignore (announced on
    stderr; see ensure_agent_state_ignored); it creates `.agent-state/_runs/<kind>/`
    before that gate runs and takes it back with _prune_empty if the gate then declines;
    and it prunes its own `_runs/<kind>/` of run dirs that are both surplus and inactive
    (see _reap_old_runs).

    Project-local when the project is known and can hold ignored state:
      <project>/.agent-state/_runs/<kind>/<UTC yyyymmdd-HHMMSS>-<rand>/
    Per-session temp otherwise:
      <tmpdir>/cc-<session>/<kind>-<rand>/

    WHY project-local first: a flat /tmp/{planner,executor}-* namespace is shared by
    every session on the machine, so one session's cleanup glob deletes another's
    in-flight plan (observed 2026-08-18), the path carries no clue which repo or session
    owns it, and a /tmp reap or reboot discards work that only reaches docs/plans/ at
    approval.

    WHY a timestamp prefix and no slug: the run's slug would derive from
    overview.problem, which step 1 has not captured yet (plan.json is written with an
    empty problem). A sortable UTC stamp is what is actually knowable at creation, and
    the reaper depends on that sort order.

    WHY mkdtemp and not mkdir on a computed name: two sessions starting in the same
    second must not race for one directory. mkdtemp's atomic create-or-retry is the
    primitive for that; the timestamp is only its prefix.
    """
    repo_root, reason = resolve_project_root()
    if repo_root is None:
        return _fallback(kind, reason)

    parent = repo_root / AGENT_STATE_DIRNAME / RUNS_NAMESPACE / kind
    relative_parent = f"{AGENT_STATE_DIRNAME}/{RUNS_NAMESPACE}/{kind}"

    # EVERY decline past this point routes through here, so "a tree that was never going
    # to hold state keeps nothing" holds by construction rather than by remembering to
    # undo at each exit. A fifth decline path added later inherits it.
    created = _created_ancestors(parent, repo_root)

    def decline(why: str) -> str:
        # One signature, one list. The minted run dir is pushed onto `created` the moment
        # it exists, so a decline added after the mint inherits its cleanup too -- with an
        # optional leaf parameter that was the one thing each new exit had to remember.
        _prune_empty(created)
        return _fallback(kind, why)

    # The directory comes first, ahead of the ignore gate that may append to a tracked
    # .gitignore. Appending for a directory that then turns out to be uncreatable strands
    # that line with the run's state in temp -- a mutation of the user's file with nothing
    # to show for it, and silent on every later run, because the rule is by then already
    # present and the gate short-circuits ahead of the announcement. An empty directory is
    # invisible to git (it tracks files, not directories), so creating one costs nothing.
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # A read-only or otherwise unwritable checkout degrades; it does not abort.
        return decline(f"cannot write {parent}: {e}")

    ignored, reason = ensure_agent_state_ignored(repo_root, relative_parent)
    if not ignored:
        return decline(reason)

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    try:
        state_dir = _mkdtemp_usable(f"{stamp}-", parent)
    except OSError as e:
        return decline(f"cannot mint a run dir in {parent}: {e}")
    created.insert(0, Path(state_dir))  # deepest first, so the leaf is taken back first

    # Asked again about the LEAF, not the parent the gate was given. NOT because a nested
    # negation could un-ignore it -- git refuses to re-include anything below an excluded
    # directory, so a .gitignore alone cannot produce that -- but because this is the last
    # moment before state is written and the gate's answer was about a different path,
    # obtained earlier. `is not True` is the operative part: it also catches git having
    # become unable to answer at all (binary gone, timeout, an ownership check newly
    # failing), where trusting the earlier answer writes state into a tree nothing can
    # currently vouch for.
    relative = f"{relative_parent}/{Path(state_dir).name}"
    if _check_ignored(repo_root, relative) is not True:
        return decline(f"{repo_root}/{relative} is not ignored by git")

    _reap_old_runs(parent)
    return state_dir


# =============================================================================
# Resource Provider Implementation
# =============================================================================


class PlannerResourceProvider:
    """ResourceProvider implementation for planner workflows.

    Provides access to conventions and step guidance.
    """

    def get_resource(self, name: str) -> str:
        """Retrieve resource content from conventions directory.

        Implements ResourceProvider protocol for planner workflows.
        Maps resource name to file in CONVENTIONS_DIR.
        """
        resource_path = Path(__file__).resolve().parents[4] / "planner" / "resources" / name
        try:
            return read_text_or_exit(resource_path, "loading planner resource")
        except SystemExit as e:
            raise FileNotFoundError(f"Resource not found: {name}") from e

    def get_step_guidance(self, **kwargs) -> dict:
        """Get step-specific guidance (placeholder for forward compatibility).

        Returns empty dict until per-step guidance requirements emerge.
        Decision Log (get_step_guidance placeholder) explains deferral rationale.
        """
        return {}


# =============================================================================
# Resource Loading
# =============================================================================


def get_resource(name: str) -> str:
    """Read resource file from planner resources directory.

    Resources are authoritative sources for specifications that agents need.
    Scripts inject these at runtime so agents don't need embedded copies.

    Args:
        name: Resource filename (e.g., "plan-format.md")

    Returns:
        Full content of the resource file

    Exits:
        With contextual error message if resource doesn't exist
    """
    # shared -> planner -> skills -> scripts -> skills -> planner/resources
    resource_path = Path(__file__).resolve().parents[4] / "planner" / "resources" / name
    return read_text_or_exit(resource_path, "loading planner resource")


def get_mode_script_path(script_name: str) -> str:
    """Get module path for -m invocation.

    Mode scripts provide step-based workflows for sub-agents.
    Scripts are organized by agent: qr/, dev/, tw/

    Args:
        script_name: Script path relative to planner/ (e.g., "developer/exec_implement.py")

    Returns:
        Module path for python3 -m (e.g., "skills.planner.developer.exec_implement")
    """
    # Convert path to module: "quality_reviewer/qr_decompose.py" -> "quality_reviewer.qr_decompose"
    module = script_name.replace("/", ".").replace("-", "_").removesuffix(".py")
    return f"skills.planner.{module}"


def get_exhaustiveness_prompt() -> list[str]:
    """Return exhaustiveness verification prompt for QR steps.

    Research shows models satisfice (stop after finding "enough" issues)
    unless explicitly prompted to find more. This prompt counters that
    tendency by forcing adversarial self-examination.

    Returns:
        List of prompt lines for exhaustiveness verification
    """
    return [
        "<exhaustiveness_check>",
        "STOP. Before reporting your findings, perform adversarial self-examination:",
        "",
        "1. What categories of issues have you NOT yet checked?",
        "2. What assumptions are you making that could hide problems?",
        "3. Re-read each milestone -- what could go wrong that you missed?",
        "4. What would a hostile reviewer find that you overlooked?",
        "",
        "List any additional issues discovered. Only report PASS if this",
        "second examination finds nothing new.",
        "</exhaustiveness_check>",
    ]


def render_context_file(context_file: str | Path, *, missing_ok: bool = False) -> str:
    """Load and format context.json for sub-agent consumption.

    WHY logical name: LLM sees "context.json" (semantic) not the resolved
    "<state_dir>/context.json" (implementation detail).

    missing_ok: when True, a missing context.json degrades to a placeholder
    note instead of raising. Execution-phase QR (impl-code/impl-docs) runs in a
    state dir the executor populated with plan.json but no context.json, so its
    absence there is expected, not an error. Plan-phase callers keep the default
    (strict): the planner writes context.json in step 2, so a missing file there
    is a real dispatch-ordering bug worth surfacing loudly. See
    qr.phases.is_execution_phase, which callers pass through to this flag.
    """
    from skills.lib.workflow.prompts import format_file_content

    try:
        content = Path(context_file).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        if missing_ok:
            return format_file_content(
                "context.json",
                "(No planning context.json in this execution state directory. "
                "Plan-phase context is not carried into execution; verify against "
                "plan.json -- the source of truth for acceptance criteria.)",
            )
        raise FileNotFoundError(
            f"Context file not found: {context_file}. "
            "Orchestrator must create context.json before sub-agent dispatch."
        ) from e
    return format_file_content("context.json", content)


def render_phase_context(state_dir: str, phase: str) -> str:
    """Render context.json for a phase, degrading gracefully for execution phases.

    impl-* state dirs carry no context.json (the executor writes plan.json only), so
    missing_ok follows is_execution_phase; plan phases stay strict. Single owner of the
    'which phases tolerate a missing context.json' rule.
    """
    from skills.planner.shared.qr.phases import is_execution_phase

    return render_context_file(get_context_path(state_dir), missing_ok=is_execution_phase(phase))
