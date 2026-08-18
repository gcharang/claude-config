"""State-directory placement: project-local by default, per-session temp as fallback.

The load-bearing property under test is that nothing lands at the flat
/tmp/{planner,executor}-* namespace a cleanup glob in any other session would sweep
(2026-08-18: `rm -rf /tmp/planner-*` destroyed a concurrent session's plan).

Sections run outward from the primitives: repo discovery, the project anchor, its
persistence, ignore gating, placement, retention, then the orchestrator call sites.
That is resources.py's order but for the last pair, which is deliberately swapped:
the source keeps private helpers above their caller throughout (_last_activity above
_reap_old_runs, _temp_state_dir and _fallback above resolve_state_dir), which is a
convention rather than a requirement -- module-level names resolve at call time -- and
reading the tests wants the caller first.
"""

from __future__ import annotations

import errno
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from skills.planner.shared import resources
from skills.planner.shared.resources import (
    AGENT_STATE_DIRNAME,
    GITIGNORE_RULE,
    PROJECT_ROOT_FILE,
    RUNS_KEEP_NEWEST,
    RUNS_MAX_AGE_DAYS,
    RUNS_NAMESPACE,
    ensure_agent_state_ignored,
    ensure_project_root_recorded,
    find_repo_root,
    load_project_root,
    require_usable_state_dir,
    resolve_project_root,
    resolve_state_dir,
)

# chmod is a no-op for uid 0, so every permission-dependent test below would pass
# without exercising the branch it names (Docker CI commonly runs as root).
requires_unprivileged = pytest.mark.skipif(
    os.geteuid() == 0, reason="chmod-based permission tests are meaningless as root"
)


# What resolve_state_dir passes in: the runs directory whose ignore status decides the
# branch. Tests that call the gate directly use the same shape rather than a synthetic
# path, so a rule matching only a made-up basename cannot satisfy them either.
_PROBE = f"{AGENT_STATE_DIRNAME}/{RUNS_NAMESPACE}/planner"


def _git_repo(path: Path) -> Path:
    """Real git repo (not a fake .git dir): check-ignore needs git to accept it."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    return path


def _commit_all(repo: Path, message: str = "init") -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _runs_parent(root: Path, kind: str) -> Path:
    return root / AGENT_STATE_DIRNAME / RUNS_NAMESPACE / kind


def _make_run(parent: Path, name: str, *, age_days: float) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    d = parent / name
    d.mkdir(exist_ok=True)
    when = (datetime.now(UTC) - timedelta(days=age_days)).timestamp()
    os.utime(d, (when, when))
    return d


def _within(seconds: float, call):
    """Run `call` on a worker thread and fail if it has not returned in `seconds`.

    The guard being protected is O_NONBLOCK on the marker open. Without it the call
    BLOCKS rather than misbehaving, so an ordinary assertion never runs: the test hangs,
    which in CI is an indefinite stall rather than a red build. A watchdog turns that into
    an ordinary failure without taking a pytest-timeout dependency.

    The worker is a daemon, so a genuinely stuck open cannot keep the interpreter alive
    after the suite finishes.
    """
    box = {}

    def run():
        try:
            box["value"] = call()
        except BaseException as exc:  # surfaced on the main thread below
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), f"call did not return within {seconds}s -- it is blocking"
    if "error" in box:
        raise box["error"]
    return box["value"]


def _fail_close_of(monkeypatch, target: Path) -> None:
    """Make os.close report a deferred write-back error for `target`'s descriptor only.

    NFS surfaces a failed write-back at close() rather than at write(), which is the one
    way close() reports something a caller has not already seen.

    Scoped to a single descriptor because os.close is process-wide: git subprocesses and
    pytest's own capture run through it during the same call, so a blanket raise fires
    somewhere other than the site under test. The descriptor is closed for real before
    the error, matching a kernel that has already released it -- nothing leaks, and
    there is nothing to retry.
    """
    real_open, real_close = os.open, os.close
    watched: set[int] = set()

    def watching_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if str(path) == str(target):
            watched.add(fd)
        return fd

    def failing_close(fd):
        real_close(fd)
        if fd in watched:
            watched.discard(fd)
            raise OSError(errno.EIO, "deferred write-back failed")

    monkeypatch.setattr(os, "open", watching_open)
    monkeypatch.setattr(os, "close", failing_close)


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """Isolate the temp branch and guarantee the project anchor resolves to nothing.

    Both anchors must be neutralised, not just the env var: resolve_project_root falls
    back to the cwd, and pytest's own cwd is inside this checkout. tempfile.tempdir is
    patched rather than TMPDIR because gettempdir() caches on first call.
    """
    fallback = tmp_path / "tmp"
    fallback.mkdir()
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(fallback))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(nowhere)
    return fallback


@pytest.fixture
def repo(tmp_path, temp_root, monkeypatch):
    """A git repo named by CLAUDE_PROJECT_DIR, with the temp branch isolated.

    Sets the real anchor rather than patching resolve_project_root, so the project-local
    assertions cover the path production actually takes. Depends on temp_root so an
    accidental fallback lands under tmp_path and the two branches stay distinguishable.
    """
    root = _git_repo(tmp_path / "repo")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    return root


@pytest.fixture
def filled_window(repo):
    """A project-local runs parent whose keep window is already full.

    Retention reaches a run only once it is BOTH surplus and stale, so a reaper test
    needs the newest RUNS_KEEP_NEWEST slots occupied before its own fixture is surplus at
    all. Copying that setup per test is how a foreign directory ends up sorted INTO the
    keep window by accident, leaving the _RUN_DIR_RE guard untested behind a test that
    passes.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    for i in range(RUNS_KEEP_NEWEST):
        _make_run(parent, f"29990101-0000{i:02d}-fresh", age_days=0)
    return parent


@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin datetime.now(UTC) so stamp-derived assertions cannot straddle a second."""

    fixed = datetime(2026, 8, 18, 4, 5, 6, tzinfo=UTC)

    class _Frozen:
        @staticmethod
        def now(tz=None):
            # A tz-less call answers a DIFFERENT instant on purpose: answering the same
            # one for both leaves datetime.now() and datetime.now(UTC) indistinguishable,
            # and nothing can then pin the "UTC stamp" INTENT.md promises -- which the
            # reaper's name-sort depends on across a DST fall-back.
            return fixed + timedelta(hours=7) if tz is None else fixed.astimezone(tz)

    monkeypatch.setattr(resources, "datetime", _Frozen)
    return fixed


# --- repo discovery: find_repo_root ------------------------------------------------


def test_find_repo_root_walks_up_to_git_dir(tmp_path):
    root = _git_repo(tmp_path / "repo")
    nested = root / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == root


def test_find_repo_root_accepts_git_file_worktree(tmp_path):
    """A worktree's .git is a FILE pointing at the parent repo, not a directory."""
    root = tmp_path / "worktree"
    (root / "sub").mkdir(parents=True)
    (root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n", encoding="utf-8")
    assert find_repo_root(root / "sub") == root


def test_find_repo_root_resolves_a_real_worktree(tmp_path):
    root = _git_repo(tmp_path / "main")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _commit_all(root)
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-q", str(wt)], cwd=root, check=True, capture_output=True
    )
    assert (wt / ".git").is_file()
    assert find_repo_root(wt) == wt


def test_find_repo_root_returns_none_outside_repo(tmp_path):
    """No repo marker anywhere up the chain -> None.

    pytest's tmp_path lives under the system temp dir, which is where a stray empty
    /tmp/.git turns up in practice -- _is_git_dir is what keeps this deterministic.
    """
    outside = tmp_path / "no-repo" / "deep"
    outside.mkdir(parents=True)
    assert find_repo_root(outside) is None


def test_find_repo_root_rejects_a_stray_empty_git_dir(tmp_path):
    """An empty `.git/` is not a repo -- git itself says so (see /tmp/.git and ~/.git).

    Without the HEAD check the walk returns such a directory as a root; the one at
    ~/.git is how a plan for an unrelated project came to sit in ~/docs/plans/.
    """
    stray = tmp_path / "stray"
    (stray / ".git").mkdir(parents=True)
    (stray / "deep").mkdir()
    assert find_repo_root(stray / "deep") != stray


def test_find_repo_root_rejects_a_non_gitdir_file(tmp_path):
    """A `.git` FILE that is not a `gitdir:` pointer is not a worktree marker."""
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / ".git").write_text("notes to self\n", encoding="utf-8")
    assert find_repo_root(stray) != stray


def test_find_repo_root_accepts_a_file_start(tmp_path):
    """The walk starts at whatever it is given; a file start is not special-cased.

    Contract pin for the leak guard's second anchor, which is
    find_repo_root(Path(resources.__file__)) -- a FILE. A defensive
    `if not start.is_dir(): return None` added here would turn that anchor into None
    and leave the guard watching nothing, silently.
    """
    root = _git_repo(tmp_path / "repo")
    f = root / "pkg" / "mod.py"
    f.parent.mkdir(parents=True)
    f.write_text("", encoding="utf-8")
    assert find_repo_root(f) == root


@requires_unprivileged
def test_find_repo_root_survives_an_unsearchable_ancestor(tmp_path):
    """An unreadable ancestor reads as "no marker here", not a PermissionError traceback.

    pathlib absorbs only ENOENT/ENOTDIR/EBADF/ELOOP, so probing `.git` under a directory
    with no search bit raises EACCES; _is_git_dir catches it and the walk climbs past.
    Unguarded, it surfaces as a raw traceback out of executor step 1.
    """
    blocked = tmp_path / "blocked"
    inner = blocked / "inner"
    inner.mkdir(parents=True)
    blocked.chmod(0o000)
    try:
        assert find_repo_root(inner) is None
    finally:
        blocked.chmod(0o755)


def test_find_repo_root_requires_an_explicit_start():
    """No default: defaulting to this module's path is the anchoring bug itself."""
    with pytest.raises(TypeError):
        find_repo_root()  # type: ignore[call-arg]


# --- the project anchor: resolve_project_root --------------------------------------


def test_project_root_prefers_the_env_var(tmp_path, monkeypatch):
    root = _git_repo(tmp_path / "repo")
    other = _git_repo(tmp_path / "other")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.chdir(other)
    assert resolve_project_root() == (root, "")


def test_project_root_falls_back_to_cwd(tmp_path, monkeypatch):
    """Step 1's invocation keeps the caller's cwd precisely so this works."""
    root = _git_repo(tmp_path / "repo")
    sub = root / "packages" / "app"
    sub.mkdir(parents=True)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    assert resolve_project_root() == (root, "")


def test_an_unreadable_working_directory_degrades_rather_than_raising(tmp_path, monkeypatch):
    """A cwd deleted out from under the process -- a vanished mount, an `rm -rf` of the
    shell's directory -- makes Path.cwd() raise, and both orchestrators call this through
    _begin_run with nothing wrapping it.
    """

    def gone():
        raise FileNotFoundError(errno.ENOENT, "No such file or directory")

    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(Path, "cwd", staticmethod(gone))

    root, reason = resolve_project_root()

    assert root is None
    assert "working directory is unreadable" in reason


def test_project_root_is_none_when_neither_anchor_is_a_repo(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(plain)
    root, reason = resolve_project_root()
    assert root is None
    assert "unset" in reason and str(plain) in reason


def test_project_root_names_the_env_var_when_it_points_nowhere(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(plain))
    root, reason = resolve_project_root()
    assert root is None
    assert "CLAUDE_PROJECT_DIR" in reason and str(plain) in reason


def test_a_whitespace_only_env_anchor_counts_as_unset(tmp_path, monkeypatch):
    """`.strip()` decides whether CLAUDE_PROJECT_DIR is SET; the value itself is passed
    through untouched, because trailing whitespace is legal in a directory name.

    Without the strip, "   " is truthy and gets resolved as a RELATIVE path against cwd,
    so the failure is reported against CLAUDE_PROJECT_DIR -- naming an input the user did
    not meaningfully provide, and hiding that the real anchor was the working directory.
    """
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "   ")
    monkeypatch.chdir(nowhere)

    root, reason = resolve_project_root()

    assert root is None
    assert "unset" in reason and str(nowhere) in reason


def test_project_root_walks_up_from_a_subdirectory_anchor(tmp_path, monkeypatch):
    root = _git_repo(tmp_path / "repo")
    sub = root / "packages" / "app"
    sub.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(sub))
    assert resolve_project_root() == (root, "")


def test_project_root_resolves_a_submodule_to_its_own_root(tmp_path, monkeypatch):
    """git's ignore semantics are per-repo, so a submodule is its own project."""
    outer = _git_repo(tmp_path / "outer")
    (outer / "f.txt").write_text("x", encoding="utf-8")
    _commit_all(outer)
    inner = _git_repo(tmp_path / "inner")
    (inner / "g.txt").write_text("y", encoding="utf-8")
    _commit_all(inner)
    subprocess.run(
        ["git", "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(inner), "sub"],
        cwd=outer,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(outer / "sub"))
    root, _ = resolve_project_root()
    assert root == outer / "sub"


def test_project_root_round_trips_through_the_state_dir(tmp_path, monkeypatch):
    """Steps after the first lose cwd, so the answer is carried, not re-derived."""
    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))

    ensure_project_root_recorded(str(state))

    assert (state / PROJECT_ROOT_FILE).exists()
    assert load_project_root(str(state)) == (root, "")


def test_state_dir_never_lands_in_the_skill_repo(temp_root):
    """Anchoring on this module's own location puts one project's state into another
    project's repo, and makes the project-local branch unreachable for a user-global
    install. With no project anchor the only correct answer is the temp fallback.
    """
    state_dir = Path(resolve_state_dir("planner"))

    assert temp_root in state_dir.parents
    # Asserted against the RESOLVED anchor rather than the result: with state_dir already
    # pinned under temp_root, "not under the skill repo" is true of any path this could
    # return, so it would pass under an implementation that anchors on __file__.
    root, reason = resolve_project_root()
    assert root is None, f"the skill repo answered as the project: {root}"
    assert "unset" in reason


def test_home_is_not_a_project_when_merely_stumbled_into(tmp_path, monkeypatch):
    """A dotfiles repo at $HOME plus a cwd outside any project resolves "project" to ~.

    That puts state in ~/.agent-state/, a rule in ~/.gitignore, and plans in
    ~/docs/plans/ -- the exact misfiling this anchor exists to stop.
    """
    fake_home = _git_repo(tmp_path / "home")
    outside = fake_home / "not-a-project"
    outside.mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(outside)

    root, reason = resolve_project_root()

    assert root is None
    assert "$HOME" in reason


def test_home_is_honoured_when_named_explicitly(tmp_path, monkeypatch):
    """Pointing CLAUDE_PROJECT_DIR at $HOME is a choice, not a stumble."""
    fake_home = _git_repo(tmp_path / "home")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(fake_home))

    assert resolve_project_root() == (fake_home, "")


@pytest.mark.parametrize("shape", ["symlinked", "relative"])
def test_home_refusal_survives_an_unnormalised_home(tmp_path, monkeypatch, shape):
    """find_repo_root always resolves; Path.home() does not.

    Comparing them directly leaves the guard present, tested and inert wherever $HOME is
    relative or reached through a symlink -- /home/x -> /mnt/..., NixOS impermanence,
    relocated or NFS homes.
    """
    real_home = _git_repo(tmp_path / "real" / "home")
    outside = real_home / "not-a-project"
    outside.mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    if shape == "symlinked":
        link = tmp_path / "link"
        link.symlink_to(tmp_path / "real")
        monkeypatch.setenv("HOME", str(link / "home"))
        monkeypatch.chdir(outside)
    else:
        monkeypatch.chdir(outside)
        monkeypatch.setenv("HOME", "..")

    root, reason = resolve_project_root()

    assert root is None, f"$HOME reached as {shape} must still be refused"
    assert "$HOME" in reason


def test_unresolvable_home_does_not_propagate(tmp_path, monkeypatch):
    """Path.home() raises RuntimeError where the UID has no passwd entry."""
    root_repo = _git_repo(tmp_path / "repo")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(root_repo)
    monkeypatch.setattr(
        resources.Path, "home", staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no home")))
    )

    assert resolve_project_root() == (root_repo, "")


# --- project identity: the recorded marker -----------------------------------------


def test_load_project_root_is_none_when_unrecorded(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    root, reason = load_project_root(str(state))
    assert root is None
    assert "no project root recorded" in reason


def test_load_project_root_rejects_a_path_that_is_no_longer_a_repo(tmp_path):
    """A state dir can outlive its checkout; writing a plan into a non-repo is worse."""
    gone = tmp_path / "gone"
    gone.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text(f"{gone}\n", encoding="utf-8")
    root, reason = load_project_root(str(state))
    assert root is None
    assert "no longer a git repository" in reason


def test_recording_the_project_is_idempotent(repo):
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    state_dir = resolve_state_dir("planner")

    ensure_project_root_recorded(state_dir)
    first = (Path(state_dir) / PROJECT_ROOT_FILE).read_text(encoding="utf-8")
    ensure_project_root_recorded(state_dir)

    assert (Path(state_dir) / PROJECT_ROOT_FILE).read_text(encoding="utf-8") == first


def test_recording_the_project_is_announced(repo, capsys):
    """A temp-branch path names no repo, so the plan's destination is otherwise unstated."""
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    state_dir = resolve_state_dir("planner")
    capsys.readouterr()

    ensure_project_root_recorded(state_dir)

    assert f"belongs to project {repo}" in capsys.readouterr().err


def test_recording_says_why_when_no_project_resolves(temp_root, capsys):
    """No project -> nothing recorded, and the reason is stated.

    Silence here is the worst case: a supplied --state-dir never calls resolve_state_dir,
    so no fallback message covers it either, and the run reaches the terminal save with
    no identity and no hint of why.
    """
    state_dir = resolve_state_dir("planner")
    capsys.readouterr()

    ensure_project_root_recorded(state_dir)

    assert not (Path(state_dir) / PROJECT_ROOT_FILE).exists()
    err = capsys.readouterr().err
    assert "not recording a project" in err and "CLAUDE_PROJECT_DIR is unset" in err


def test_corrupt_project_root_marker_declines_without_raising(tmp_path):
    """Bytes that are not UTF-8 reach the shape test and classify as foreign.

    The decode itself cannot raise (errors="replace"). The ValueError arm in the read
    guard is for an embedded-NUL path, which the nul-byte case of
    test_recording_never_raises_on_an_unusable_state_dir owns.
    """
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_bytes(b"\xff\xfe\x00\x01garbage")

    root, reason = load_project_root(str(state))

    assert root is None
    assert "did not write" in reason


@pytest.mark.parametrize(
    "bad_dir",
    ["\x00embedded-nul", "unsearchable"],
    ids=["nul-byte", "unsearchable"],
)
@requires_unprivileged
def test_recording_never_raises_on_an_unusable_state_dir(
    tmp_path, temp_root, monkeypatch, bad_dir, capsys
):
    """Neither input may surface as a traceback.

    Both are absorbed by the same guard, and both classify as _MARKER_KEEP: the read
    raised, so the marker's content is unknown, and unknown is never overwritten. One
    warning each, and no write is attempted.

    A project must resolve, or the function returns before touching the state dir at
    all and neither hazard is exercised.
    """
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(_git_repo(tmp_path / "proj")))
    if bad_dir == "unsearchable":
        target = tmp_path / "blocked"
        target.mkdir()
        target.chmod(0o000)
    else:
        target = tmp_path / bad_dir
    try:
        ensure_project_root_recorded(str(target))  # must not raise
    finally:
        if bad_dir == "unsearchable":
            target.chmod(0o755)
    # The failure must be reported, not swallowed.
    err = capsys.readouterr().err
    # Pinned so the docstring's account cannot drift from what happens: the read guard
    # fires once and no write follows, because an unreadable marker is kept.
    assert err.count("Warning:") == 1, err
    assert "leaving it as it is" in err


def test_symlinked_marker_is_neither_read_nor_written_through(tmp_path, temp_root, capsys):
    """Both consumers must refuse it, not just the recorder.

    Classifying the symlink inside _read_marker is what makes that true: a check living
    only in ensure_project_root_recorded leaves step 1 declining while load_project_root
    follows the link and hands the terminal save a repo the run never belonged to.
    """
    victim = _git_repo(tmp_path / "victim")
    state = tmp_path / "state"
    state.mkdir()
    target = tmp_path / "elsewhere.txt"
    target.write_text(f"{victim}\n", encoding="utf-8")
    (state / PROJECT_ROOT_FILE).symlink_to(target)

    ensure_project_root_recorded(str(state))

    # Read side: the consumer that archives the plan must not resolve the link.
    # O_NOFOLLOW refuses it at open() with ELOOP, so the reason names the link rather
    # than the type -- what matters is that no project comes back.
    root, reason = load_project_root(str(state))
    assert root is None and str(state / PROJECT_ROOT_FILE) in reason
    # Write side: the target keeps its content, and the marker stays a symlink.
    assert target.read_text(encoding="utf-8") == f"{victim}\n"
    assert (state / PROJECT_ROOT_FILE).is_symlink()
    assert "leaving it as it is" in capsys.readouterr().err


def test_corrupt_marker_is_repaired_rather_than_stuck(tmp_path, monkeypatch, capsys):
    """Content that is provably not ours is replaced rather than left permanent.

    Gating on presence alone makes such a marker stick: every resume short-circuits on
    the file existing, and the terminal step reports the same failure forever with no
    recovery but deleting it by hand.
    """
    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_bytes(b"\xff\xfe\x00\x01garbage")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))

    ensure_project_root_recorded(str(state))

    assert load_project_root(str(state)) == (root, "")
    err = capsys.readouterr().err
    assert "did not write" in err
    assert f"belongs to project {root}" in err


def test_marker_that_is_a_directory_reports_rather_than_silently_no_ops(
    tmp_path, monkeypatch, capsys
):
    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))

    ensure_project_root_recorded(str(state))

    err = capsys.readouterr().err
    assert "not a regular file" in err, "the report must name why the marker is unusable"
    assert "leaving it as it is" in err, "an unknown marker is kept, never overwritten"
    assert (state / PROJECT_ROOT_FILE).is_dir(), "and the directory is left alone"


def test_empty_marker_is_reported_as_empty_and_replaced(tmp_path, monkeypatch):
    """An empty marker is a distinct outcome from a missing one, and must be replaced
    rather than reported: nothing was recorded, so there is no identity to protect.

    load_project_root returns the same (None, "... is empty") whether the kind is
    CORRUPT or KEEP, so the reason alone cannot pin the classification -- replacement
    is the only observable difference. Classified KEEP, a zero-length marker (an ext4
    post-crash tail, `> project_root`, an editor saving empty) would be PERMANENT:
    every resume reports it and the plan never archives.
    """
    project = _git_repo(tmp_path / "project")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    marker.write_text("\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    root, reason = load_project_root(str(state))
    assert root is None
    assert "is empty" in reason

    ensure_project_root_recorded(str(state))
    assert marker.read_text(encoding="utf-8").strip() == str(project)


def test_resuming_under_a_different_project_keeps_the_recorded_one(
    tmp_path, temp_root, monkeypatch, capsys
):
    """Re-deriving here would silently re-point a run minted in A at B.

    The recorded value is the run's identity; the resuming shell's cwd is not.
    """
    proj_a = _git_repo(tmp_path / "a")
    proj_b = _git_repo(tmp_path / "b")
    state = tmp_path / "state"
    state.mkdir()

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj_a))
    ensure_project_root_recorded(str(state))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj_b))
    capsys.readouterr()

    ensure_project_root_recorded(str(state))

    assert load_project_root(str(state)) == (proj_a, "")
    err = capsys.readouterr().err
    assert str(proj_a) in err and str(proj_b) in err


def test_marker_naming_a_vanished_repo_is_not_re_derived(tmp_path, monkeypatch, capsys):
    """Same reasoning: a recorded project that no longer resolves must not be replaced
    by whatever project the resuming shell happens to sit in.
    """
    gone = tmp_path / "gone"
    gone.mkdir()
    other = _git_repo(tmp_path / "other")
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text(f"{gone}\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other))

    ensure_project_root_recorded(str(state))

    assert (state / PROJECT_ROOT_FILE).read_text(encoding="utf-8").strip() == str(gone)
    assert "leaving it as it is" in capsys.readouterr().err


def test_marker_this_planner_did_not_write_is_replaced(tmp_path, monkeypatch, capsys):
    """_save_project_root only ever writes one absolute line, so relative or multi-line
    content is provably foreign -- safe to overwrite, unlike a well-formed path.
    """
    root = _git_repo(tmp_path / "repo")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    for i, content in enumerate(("some/relative/path", "/a\n/b", "garbage text")):
        state = tmp_path / f"state-{i}"
        state.mkdir()
        (state / PROJECT_ROOT_FILE).write_text(content, encoding="utf-8")

        ensure_project_root_recorded(str(state))

        assert load_project_root(str(state)) == (root, ""), content
        assert "did not write" in capsys.readouterr().err


def test_a_well_formed_path_to_a_vanished_project_is_kept(tmp_path, monkeypatch, capsys):
    """A truncated write is byte-for-byte a deleted project; neither may be overwritten,
    because guessing wrong re-points the run at whatever project the shell sits in.
    """
    gone = tmp_path / "gitrep"  # what "/…/gitrepos" looks like truncated
    gone.mkdir()
    other = _git_repo(tmp_path / "other")
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text(f"{gone}\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other))

    ensure_project_root_recorded(str(state))

    assert (state / PROJECT_ROOT_FILE).read_text(encoding="utf-8").strip() == str(gone)
    assert "leaving it as it is" in capsys.readouterr().err


@requires_unprivileged
def test_a_marker_that_cannot_be_written_is_reported_not_swallowed(tmp_path, monkeypatch, capsys):
    """Losing the marker degrades the run rather than failing it, but must not be silent.

    Only docs/plans/ depends on it, so this is a degrade -- and the terminal save is the
    step that will fail later, far from the cause. The warning is the only thing linking
    the two.
    """
    project = _git_repo(tmp_path / "project")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    state.chmod(0o500)  # readable and searchable, not writable
    try:
        ensure_project_root_recorded(str(state))
    finally:
        state.chmod(0o700)

    err = capsys.readouterr().err
    assert "could not record project root" in err
    assert str(state) in err
    # The False return is what suppresses the success note; asserting only the warning
    # leaves "reported the failure AND claimed success" green.
    assert "belongs to project" not in err, "nothing was recorded, so nothing may be announced"
    assert not (state / PROJECT_ROOT_FILE).exists()


def test_the_marker_is_opened_without_blocking_on_a_fifo(tmp_path, monkeypatch):
    """O_NONBLOCK is asserted on the FLAGS, not through behaviour.

    Its absence makes test_a_non_regular_marker_is_kept_not_opened[fifo] block forever
    rather than fail -- an indefinite CI hang, not a red test -- so the guard needs a
    check that fails fast. O_NOFOLLOW is asserted alongside it because the two travel
    together and a single-flag assertion invites dropping the other.
    """
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text(f"{tmp_path}\n", encoding="utf-8")
    seen = []
    real_open = os.open

    def watching_open(path, flags, *args, **kwargs):
        if str(path) == str(state / PROJECT_ROOT_FILE):
            seen.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", watching_open)

    load_project_root(str(state))

    assert seen, "the marker was never opened"
    assert all(f & os.O_NONBLOCK for f in seen), "a FIFO marker would block step 1 forever"
    assert all(f & os.O_NOFOLLOW for f in seen), "a symlinked marker would be followed"


def test_marker_write_goes_through_the_atomic_primitive(tmp_path, monkeypatch):
    """Two step-1 runs sharing one --state-dir must not splice a path.

    Asserting the end state cannot show this -- a plain write_text produces an identical
    file when there is only one writer. What distinguishes them is the primitive, so
    that is what this pins: a truncate-then-write leaves content that decodes fine, is
    not a repo, and reads as a vanished project -- the one state deliberately never
    replaced, so the run's identity would be lost for good.
    """
    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    calls = []
    real = resources.atomic_write_text
    monkeypatch.setattr(
        resources, "atomic_write_text", lambda p, text: (calls.append(Path(p)), real(p, text))[1]
    )

    ensure_project_root_recorded(str(state))

    assert calls == [state / PROJECT_ROOT_FILE], "the marker write must be atomic"
    assert (state / PROJECT_ROOT_FILE).read_text(encoding="utf-8") == f"{root}\n"
    assert [p.name for p in state.iterdir()] == [PROJECT_ROOT_FILE]


def test_matching_marker_still_announces_the_project(tmp_path, temp_root, monkeypatch, capsys):
    """The resume path is where a user most wants to be told where the plan will go."""
    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    ensure_project_root_recorded(str(state))
    capsys.readouterr()

    ensure_project_root_recorded(str(state))

    assert f"belongs to project {root}" in capsys.readouterr().err


@requires_unprivileged
def test_an_unreadable_marker_is_kept_not_overwritten(tmp_path, monkeypatch, capsys):
    """Content that could not be READ is unknown, not provably foreign.

    The criterion is "could _save_project_root have produced these bytes?" -- an EACCES,
    EIO, or stale-handle read cannot answer no, so overwriting is a guess. Guessing wrong
    replaces the run's own project with whichever one the resuming shell sits in, which
    is the silent re-point the whole mechanism exists to prevent.
    """
    proj_a = _git_repo(tmp_path / "a")
    proj_b = _git_repo(tmp_path / "b")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    marker.write_text(f"{proj_a}\n", encoding="utf-8")
    marker.chmod(0o000)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj_b))
    try:
        ensure_project_root_recorded(str(state))
        marker.chmod(0o644)
        assert marker.read_text(encoding="utf-8").strip() == str(proj_a)
    finally:
        marker.chmod(0o644)
    err = capsys.readouterr().err
    assert "leaving it as it is" in err and "did not write" not in err


def test_marker_read_survives_a_close_time_error(repo, tmp_path, monkeypatch, capsys):
    """close() on the marker descriptor must not escape into step 1.

    Both orchestrators call ensure_project_root_recorded bare, so an OSError from the
    close in _read_marker's finally aborts step 1 with a traceback -- and does it on the
    path where nothing is wrong: the bytes were read before the close, the verdict is
    already decided, and the descriptor is released whether or not close reports.

    Both consumers are covered here because the read side runs under the same patch.
    """
    state = tmp_path / "state"
    state.mkdir()
    ensure_project_root_recorded(str(state))
    capsys.readouterr()
    _fail_close_of(monkeypatch, state / PROJECT_ROOT_FILE)

    ensure_project_root_recorded(str(state))
    root, reason = load_project_root(str(state))

    assert root == repo and not reason
    assert "leaving it as it is" not in capsys.readouterr().err


def test_corrupt_marker_with_no_project_does_not_claim_a_replacement(temp_root, tmp_path, capsys):
    """ "Replacing it" must not print when there is nothing to replace it with.

    The announcement has to follow the `live is None` bail, not precede it: a corrupt
    marker in a run with no resolvable project is left exactly as it was, so saying it
    was replaced is simply false.
    """
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text("relative/path", encoding="utf-8")

    ensure_project_root_recorded(str(state))

    err = capsys.readouterr().err
    assert "did not write" not in err, "no problem may be announced before the bail"
    assert "not recording a project" in err
    assert (state / PROJECT_ROOT_FILE).read_text(encoding="utf-8") == "relative/path"


@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_a_non_regular_marker_is_kept_not_opened(tmp_path, temp_root, kind, capsys):
    """Opening a marker that is not a regular file is never safe.

    A FIFO passes an is_symlink() check and then blocks the read forever, hanging step 1
    in both orchestrators and the terminal docs/plans save with nothing on stderr. The
    type test has to come first, and covers every non-regular type at once.
    """
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    if kind == "fifo":
        os.mkfifo(marker)
    else:
        marker.mkdir()

    root, reason = _within(10, lambda: load_project_root(str(state)))

    assert root is None
    assert "not a regular file" in reason
    _within(10, lambda: ensure_project_root_recorded(str(state)))
    assert "leaving it as it is" in capsys.readouterr().err


def test_a_marker_whose_bytes_cannot_be_READ_is_kept_and_not_re_pointed(
    tmp_path, monkeypatch, capsys
):
    """A failed READ answers "unknown", never "not ours".

    The bytes may name a perfectly good project. Classifying CORRUPT replaces the marker
    with whichever project the resuming shell sits in; classifying MISSING replaces it AND
    reports success. Both are the silent re-point this module exists to prevent, and the
    end state alone cannot tell the three kinds apart.
    """

    def raise_io(_fd):
        raise OSError(errno.EIO, "io error")

    ours = _git_repo(tmp_path / "ours")
    live = _git_repo(tmp_path / "live")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    marker.write_text(f"{ours}\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(live))
    monkeypatch.setattr(resources, "_read_all", raise_io)

    ensure_project_root_recorded(str(state))

    assert marker.read_text(encoding="utf-8") == f"{ours}\n"
    err = capsys.readouterr().err
    assert "leaving it as it is" in err
    assert "belongs to project" not in err, "an unread marker must not be reported recorded"


def test_a_project_path_with_trailing_space_round_trips(tmp_path, monkeypatch):
    """strip() is not the inverse of appending one newline.

    A trailing space is legal in a directory name, and stripping it reads back a path
    that never existed -- reported as a vanished project forever, with a recovery hint
    that loops: delete the marker, re-record, read back mangled again.
    """
    root = _git_repo(tmp_path / "trail ")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))

    ensure_project_root_recorded(str(state))

    assert load_project_root(str(state)) == (root, "")


def test_a_project_path_with_a_newline_is_refused_not_misrecorded(tmp_path, monkeypatch, capsys):
    """One line is the whole marker format, so such a path cannot round-trip.

    Recording it anyway makes the next read classify it as content this planner did not
    write, and the run is re-pointed at whichever project the shell happens to be in --
    the exact defect the keep-set exists to prevent.
    """
    root = _git_repo(tmp_path / "we\nird")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))

    ensure_project_root_recorded(str(state))

    assert not (state / PROJECT_ROOT_FILE).exists()
    assert "cannot be stored" in capsys.readouterr().err


def test_a_multibyte_path_truncated_mid_character_is_kept(tmp_path, monkeypatch, capsys):
    """A decode failure only proves "not ours" for an all-ASCII path.

    Corruption that cuts a multi-byte character leaves our own truncated write
    undecodable -- exactly the case the keep-set exists for. Judging by the decode
    failing instead of by shape would replace it with whichever project the shell is in.
    """
    cjk = _git_repo(tmp_path / "项目")
    other = _git_repo(tmp_path / "other")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cjk))
    ensure_project_root_recorded(str(state))
    marker = state / PROJECT_ROOT_FILE
    marker.write_bytes(marker.read_bytes()[:-2])  # drop "\n" and one byte of the last char
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other))
    capsys.readouterr()

    ensure_project_root_recorded(str(state))

    assert str(other) not in marker.read_bytes().decode("utf-8", errors="replace")
    assert "leaving it as it is" in capsys.readouterr().err


@pytest.mark.parametrize(
    "tail", ["\n", "\x00\x00\x00", "\n\x00\x00"], ids=["blank-line", "nul-tail", "both"]
)
def test_padding_after_our_own_path_is_kept_not_replaced(tmp_path, monkeypatch, capsys, tail):
    """A trailing blank line or NUL tail leaves our single-line write intact ahead of it.

    An editor "fixing" the file on save produces the first; a post-crash ext4 tail
    produces the second. Judging the whole body as multi-line calls both foreign and
    REPLACES a marker whose payload is perfectly good -- re-pointing the run at whichever
    repo the resuming shell sits in, which is the one outcome this module exists to
    prevent. "/a\n/b" is two real paths and must still classify CORRUPT; see below.
    """
    ours = _git_repo(tmp_path / "ours")
    live = _git_repo(tmp_path / "live")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    original = f"{ours}\n{tail}"
    marker.write_text(original, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(live))

    ensure_project_root_recorded(str(state))

    assert marker.read_text(encoding="utf-8") == original
    assert load_project_root(str(state))[0] == ours
    assert "did not write" not in capsys.readouterr().err


def test_a_marker_beginning_with_a_blank_line_is_replaced(tmp_path, monkeypatch):
    """Classified KEEP, such a marker is permanent: every resume reports it and the plan
    never archives. The reason distinguishes it from a genuinely zero-length file, which
    is what the user will go and look at.
    """
    live = _git_repo(tmp_path / "live")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    marker.write_text(f"\n{live}\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(live))

    root, reason = load_project_root(str(state))
    assert root is None
    assert "begins with a blank line" in reason

    ensure_project_root_recorded(str(state))
    # Exact bytes, not .strip(): the original content strips to the SAME string as a
    # correct replacement, so a stripped comparison passes whether or not the marker was
    # replaced -- and the reason text is identical for CORRUPT and KEEP.
    assert marker.read_text(encoding="utf-8") == f"{live}\n"


def test_two_real_paths_are_still_foreign(tmp_path, monkeypatch, capsys):
    """The padding tolerance above must not swallow the case it is carved out of: a
    non-blank remainder is content _save_project_root provably did not write.
    """
    live = _git_repo(tmp_path / "live")
    state = tmp_path / "state"
    state.mkdir()
    marker = state / PROJECT_ROOT_FILE
    marker.write_text(f"{tmp_path / 'a'}\n{tmp_path / 'b'}\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(live))

    ensure_project_root_recorded(str(state))

    assert marker.read_text(encoding="utf-8").strip() == str(live)
    assert "did not write" in capsys.readouterr().err


def test_a_problem_is_stated_without_promising_a_replacement(tmp_path, monkeypatch, capsys):
    """The write can still refuse after the problem is announced.

    Saying "replacing it" up front is false whenever _save_project_root then declines --
    an unstorable path here, a failed write elsewhere. The announcement states the
    problem; the outcome is announced by whichever branch actually happens.
    """
    weird = _git_repo(tmp_path / "we\nird")  # a path _save_project_root refuses
    state = tmp_path / "state"
    state.mkdir()
    (state / PROJECT_ROOT_FILE).write_text("relative/path", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(weird))

    ensure_project_root_recorded(str(state))

    err = capsys.readouterr().err
    assert "did not write" in err, "the problem must still be stated"
    # The success announcement is "state dir belongs to project <x>"; there is no
    # "replacing it" phrasing anywhere in the source, so asserting on that would pin
    # nothing. What must not appear is a claim that the marker now names a project.
    assert "belongs to project" not in err, "nothing was recorded"
    assert "cannot be stored" in err
    assert (state / PROJECT_ROOT_FILE).read_text(encoding="utf-8") == "relative/path"


# --- ensure_agent_state_ignored ----------------------------------------------------


def test_already_ignored_by_negative_whitelist_appends_nothing(tmp_path):
    """The model this repo itself uses: '*' + anchored allowlist already ignores it.

    A literal-string grep for '.agent-state' reads this as unignored and appends a
    redundant rule. check-ignore must see it as covered and leave the file untouched.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("*\n!/src/\n!/.gitignore\n", encoding="utf-8")
    before = gitignore.read_text(encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert gitignore.read_text(encoding="utf-8") == before


def test_unignored_repo_gets_anchored_rule_appended(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    # Leading newline is unconditional: probing for one would race a concurrent append.
    assert gitignore.read_text(encoding="utf-8") == f"node_modules/\n\n{GITIGNORE_RULE}\n"


def test_append_is_idempotent_across_two_calls(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    first = gitignore.read_text(encoding="utf-8")
    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert gitignore.read_text(encoding="utf-8") == first
    assert first.count(GITIGNORE_RULE) == 1


def test_append_preserves_existing_rules_and_order(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    original = "# secrets\n.env\n*.log\n!keep.log\n"
    gitignore.write_text(original, encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    content = gitignore.read_text(encoding="utf-8")
    assert content.startswith(original)
    assert content.rstrip("\n").endswith(GITIGNORE_RULE)


def test_append_does_not_glue_onto_a_file_without_a_trailing_newline(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert gitignore.read_text(encoding="utf-8") == f"node_modules/\n{GITIGNORE_RULE}\n"


def test_crlf_gitignore_keeps_its_line_endings(tmp_path):
    """A read_text/write_text cycle silently rewrites every CRLF line to LF."""
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_bytes(b"node_modules/\r\n*.log\n.env\r\nbuild/")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    raw = gitignore.read_bytes()
    assert raw.startswith(b"node_modules/\r\n*.log\n.env\r\nbuild/")
    assert raw.endswith(f"\n{GITIGNORE_RULE}\n".encode())


def test_comments_only_gitignore_is_appendable(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("# nothing yet\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert gitignore.read_text(encoding="utf-8").startswith("# nothing yet\n")


def test_commented_out_rule_is_not_mistaken_for_the_real_one(tmp_path):
    """`# /.agent-state/` is inert; declining on it would leave the repo unignored."""
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text(f"# {GITIGNORE_RULE}\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert gitignore.read_text(encoding="utf-8").count(GITIGNORE_RULE) == 2


@pytest.mark.parametrize("indent", ["  ", "\t"], ids=["spaces", "tab"])
def test_indented_rule_is_not_mistaken_for_the_real_one(tmp_path, indent):
    """gitignore keeps LEADING whitespace as part of the pattern, so an indented rule
    matches nothing. Comparing with `.strip()` reads it as already-present and
    declines to add the real one -- a mis-indented line silently defeating the fix.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text(f"{indent}{GITIGNORE_RULE}\n", encoding="utf-8")

    ignored, _ = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is True
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", f"{AGENT_STATE_DIRNAME}/anything"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0


def test_no_gitignore_is_not_created(tmp_path):
    """Creating one demands the full negative-whitelist treatment -- never silently."""
    root = _git_repo(tmp_path / "repo")

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "no .gitignore" in reason
    assert not (root / ".gitignore").exists()


def test_symlinked_gitignore_is_never_written_through(tmp_path):
    """git cannot read a symlinked .gitignore; Path.is_file() follows it anyway.

    Appending would mutate whatever the link points at -- possibly a dotfiles-managed
    file outside the repo -- for a branch that then fails its re-probe regardless.
    """
    root = _git_repo(tmp_path / "repo")
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "ignore-src"
    original = "shared rules\n"
    target.write_text(original, encoding="utf-8")
    (root / ".gitignore").symlink_to(target)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    # O_NOFOLLOW refuses the link at open() with ELOOP, so the reason names the path
    # rather than the type ("symbolic links", not "symlink"). Asserting the path is what
    # a neutral tmp dir survives; asserting a type word passes only because pytest names
    # the tmp dir after this test.
    assert str(root / ".gitignore") in reason
    assert target.read_text(encoding="utf-8") == original


def test_hardlinked_gitignore_is_appended_normally(tmp_path):
    """git reads a hardlink like any regular file; only symlinks are special-cased."""
    root = _git_repo(tmp_path / "repo")
    source = tmp_path / "source"
    source.write_text("node_modules/\n", encoding="utf-8")
    os.link(source, root / ".gitignore")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert GITIGNORE_RULE in source.read_text(encoding="utf-8")


def test_deliberate_negation_is_not_overridden(tmp_path):
    """A user's `!.agent-state` after the rule means they want it tracked.

    Appending a second copy would both duplicate the rule and reverse their intent.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    original = f"node_modules/\n{GITIGNORE_RULE}\n!.agent-state\n"
    gitignore.write_text(original, encoding="utf-8")

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "un-ignores" in reason
    assert gitignore.read_text(encoding="utf-8") == original


def test_rule_below_the_read_boundary_is_still_found(tmp_path):
    """_read_all must reassemble the whole file, not just its first 64 KiB pread.

    The decline above is decided by _has_rule over the bytes _read_all returns, so an
    implementation that stops at one chunk reads a rule below that boundary as absent
    and appends a duplicate -- reversing the user's `!.agent-state` in exactly the way
    the single-chunk case is written to prevent. Every other fixture in this file is a
    few hundred bytes, so nothing else makes the loop run twice.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    padding = "".join(f"build/artifact-{n:05d}/\n" for n in range(4000))
    assert len(padding.encode()) > 65536, "the rule must start past the first pread"
    original = f"{padding}{GITIGNORE_RULE}\n!.agent-state\n"
    gitignore.write_text(original, encoding="utf-8")

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "un-ignores" in reason
    assert gitignore.read_text(encoding="utf-8") == original


def test_append_survives_a_close_time_error(repo, monkeypatch, capsys):
    """close() on the .gitignore descriptor must not escape into step 1 either.

    It fires from the finally, so it beats the announcement: the rule is on disk and the
    error aborts resolve_state_dir -- which both orchestrators call bare -- before
    anything says the user's tracked file was touched. That silent-mutation outcome is
    the one the announcement exists to prevent, so the note is asserted, not just the
    absence of a traceback.
    """
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    _fail_close_of(monkeypatch, repo / ".gitignore")

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent == _runs_parent(repo, "planner")
    assert GITIGNORE_RULE in (repo / ".gitignore").read_text(encoding="utf-8")
    assert f"appended {GITIGNORE_RULE}" in capsys.readouterr().err


def test_an_unanswerable_tracked_probe_declines_rather_than_appending(tmp_path, monkeypatch):
    """Rule A governs BOTH questions the decision depends on, not just the ignore status.

    `None` is falsy, so without the guard an unreadable index falls through to the append
    -- writing to a tracked file on evidence git could not produce.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    original = "node_modules/\n"
    gitignore.write_text(original, encoding="utf-8")
    monkeypatch.setattr(resources, "_tracks_anything", lambda repo_root, relative: None)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "cannot determine what is tracked" in reason
    assert gitignore.read_text(encoding="utf-8") == original


def test_the_tracked_probe_answers_none_when_git_cannot_read_the_index(tmp_path):
    """A corrupt `.git/index` -- the post-crash shape -- is the input that splits the two
    probes: check-ignore still answers from the rules, ls-files cannot answer at all.

    Returning False there would read as "nothing tracked" and append to the user's
    .gitignore on evidence git could not produce.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".git" / "index").write_bytes(b"not an index")

    assert resources._tracks_anything(root, AGENT_STATE_DIRNAME) is None
    assert resources._tracks_anything(tmp_path / "not-a-repo", AGENT_STATE_DIRNAME) is None


def test_the_tracked_probe_ignores_inherited_git_env(tmp_path, monkeypatch):
    """GIT_DIR and friends override cwd discovery, so an inherited one answers about
    another repository's index -- and the answer here decides whether a tracked
    `.agent-state` is left alone.

    The ignore probe has the same scrub and its own test; this one needs an `other` repo
    whose index DIFFERS, or the two answers coincide and the scrub is unobservable.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    other = _git_repo(tmp_path / "other")
    (other / AGENT_STATE_DIRNAME).mkdir()
    (other / AGENT_STATE_DIRNAME / "committed.md").write_text("x\n", encoding="utf-8")
    _commit_all(other)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))

    assert resources._tracks_anything(root, AGENT_STATE_DIRNAME) is False, (
        "the inherited index answered for the wrong repository"
    )


def test_the_ignore_probe_answers_from_rules_not_from_the_index(tmp_path):
    """`--no-index` is why the probe answers "would a new file here be ignored".

    Without it a path that happens to be tracked reports NOT ignored -- true about
    tracking, and the wrong answer to "may I create state here", which sends every run in
    such a repo to temp.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".gitignore").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")
    tracked = root / AGENT_STATE_DIRNAME / RUNS_NAMESPACE / "planner"
    tracked.mkdir(parents=True)
    (tracked / "keep.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "-A"], cwd=root, check=True, capture_output=True)

    assert resources._check_ignored(root, _PROBE) is True


def test_a_gitignore_swapped_after_the_probe_is_refused(tmp_path, monkeypatch):
    """fstat classifies what was actually OPENED, not what the probe saw.

    O_NOFOLLOW stops a symlink at open(); nothing else does. A FIFO opens fine under
    O_RDWR|O_APPEND|O_NOFOLLOW -- O_RDWR does not block on one -- and the append then
    goes into a pipe instead of a file.

    Reaching that guard needs the probe to have already answered, because a .gitignore
    that is a FIFO from the start makes git itself hang and Rule A declines first (a real
    outcome, just a different one). The swap between the probe and the open is the case
    this check exists for, so that is what is staged here.
    """
    root = _git_repo(tmp_path / "repo")
    os.mkfifo(root / ".gitignore")
    monkeypatch.setattr(resources, "_check_ignored", lambda repo_root, relative: False)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "not a regular file" in reason


def test_a_short_write_still_appends_the_whole_rule(tmp_path, monkeypatch):
    """os.write may write fewer bytes than asked (ENOSPC nearing a full disk, or an
    interrupted write), and a truncated pattern like `/.agent-stat` in the user's tracked
    .gitignore matches the wrong paths rather than none.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")
    real_write = os.write
    first = [True]

    def short_write(fd, data):
        if first[0] and len(data) > 1:
            first[0] = False
            return real_write(fd, data[: len(data) // 2])
        return real_write(fd, data)

    monkeypatch.setattr(os, "write", short_write)

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert not first[0], "the short write never fired; the test proves nothing"
    body = gitignore.read_text(encoding="utf-8")
    assert f"\n{GITIGNORE_RULE}\n" in body
    assert "agent-stat\n" not in body, "a torn pattern was left in the user's file"


def test_a_write_that_fails_part_way_says_so(tmp_path, monkeypatch, capsys):
    """A raise after a partial write leaves a TORN pattern in a tracked file.

    The decline reads "could not append", which a user takes as "nothing happened", while
    `/.agent` is on disk matching paths the real rule does not. The announcement contract
    for this function is that a mutation is never silent; a partial mutation is a mutation.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")
    real_write = os.write
    torn = []

    def fail_part_way(fd, data):
        # A short RETURN, then a raise on the continuation -- os.write either reports a
        # count or raises, never both, so this is the only shape that reaches the guard.
        # Matched on the payload rather than on call order: subprocess machinery writes
        # through os.write too, so a first-call guard fires on a git pipe instead.
        if GITIGNORE_RULE.encode() in data and not torn:
            torn.append(real_write(fd, data[:8]))
            return torn[0]
        if torn and len(torn) == 1:
            torn.append("raised")
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_write(fd, data)

    monkeypatch.setattr(os, "write", fail_part_way)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert len(torn) == 2, "the short-write-then-raise sequence never fired"
    assert "could not append" in reason
    assert "only part of" in capsys.readouterr().err, "a partial mutation was left silent"
    assert GITIGNORE_RULE not in gitignore.read_text(encoding="utf-8")


def test_a_write_that_fails_immediately_claims_nothing(tmp_path, monkeypatch, capsys):
    """The partial-write warning must not fire when nothing was written.

    Announcing there tells the user to hand-remove a truncated line from a file this run
    never touched -- a false report in the one place the module is careful never to make one.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    original = "node_modules/\n"
    gitignore.write_text(original, encoding="utf-8")
    real_write = os.write

    def refuse(fd, data):
        if GITIGNORE_RULE.encode() in data:
            raise OSError(errno.EDQUOT, "Disk quota exceeded")
        return real_write(fd, data)

    monkeypatch.setattr(os, "write", refuse)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "could not append" in reason
    err = capsys.readouterr().err
    assert "only part of" not in err
    # The announcement must not have run either: it says the rule LANDED, and the file is
    # byte-identical. Asserting only the absence of the partial-write warning lets the
    # announcement move ahead of the write and stay green.
    assert "appended" not in err
    assert gitignore.read_text(encoding="utf-8") == original


@requires_unprivileged
def test_unreadable_gitignore_declines_without_raising(tmp_path):
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")
    gitignore.chmod(0o000)
    try:
        ignored, reason = ensure_agent_state_ignored(root, _PROBE)
        assert ignored is False
        assert reason
    finally:
        gitignore.chmod(0o644)


def test_a_missing_git_binary_is_an_unanswerable_probe_not_an_ignored_one(tmp_path, monkeypatch):
    """`git` absent (or the probe timing out) must answer None, never True.

    Answering True writes state into a repo where `.agent-state` is not ignored, which
    `git status` then shows and `git clean -fd` destroys. The exit-128 path (a non-repo)
    is covered below; this is the OSError arm beside it.
    """
    root = _git_repo(tmp_path / "repo")
    monkeypatch.setenv("PATH", str(tmp_path / "no-binaries-here"))

    assert resources._check_ignored(root, _PROBE) is None


def test_no_gitignore_edit_when_git_cannot_answer(tmp_path):
    """check-ignore exit 128 (or a missing binary) must not trigger a blind append.

    A probe that cannot answer cannot verify the edit either, so appending would
    mutate the user's file for nothing.
    """
    root = tmp_path / "not-a-repo"
    root.mkdir()
    original = "node_modules/\n"
    (root / ".gitignore").write_text(original, encoding="utf-8")

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "cannot determine ignore status" in reason, "the ignore probe is the guard under test"
    assert (root / ".gitignore").read_text(encoding="utf-8") == original


def test_append_is_announced_even_when_the_reprobe_fails(tmp_path, monkeypatch, capsys):
    """The announcement exists so a mutation is never unattributed in `git diff`.

    Announcing only on success leaves the confirm-failed path -- git going away
    between the two probes -- writing to a tracked file with nothing on stderr.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")

    calls = {"n": 0}

    def flaky_check(repo_root, relative_path):
        calls["n"] += 1
        return False if calls["n"] == 1 else None

    monkeypatch.setattr(resources, "_check_ignored", flaky_check)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert GITIGNORE_RULE in gitignore.read_text(encoding="utf-8")
    assert f"Note: appended {GITIGNORE_RULE}" in capsys.readouterr().err
    assert "still" in reason and "removed by hand" in reason


def test_info_exclude_coverage_needs_no_gitignore(tmp_path):
    """.git/info/exclude already ignoring it must short-circuit, not create a file."""
    root = _git_repo(tmp_path / "repo")
    (root / ".git" / "info").mkdir(exist_ok=True)
    (root / ".git" / "info" / "exclude").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")
    assert not (root / ".gitignore").exists()


def test_tracked_gitignore_shows_as_modified_after_append(tmp_path):
    """Documented consequence: the append dirties a tracked .gitignore.

    Unavoidable -- a rule cannot reach a tracked file without a working-tree diff --
    but INTENT.md says so out loud rather than surprising a first-time user.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    _commit_all(root)

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    assert " M .gitignore" in status


def test_ignore_probe_ignores_inherited_git_env(tmp_path, monkeypatch):
    """GIT_DIR and friends override cwd discovery outright.

    Inheriting them lets git answer about a different repository entirely -- the same
    confident wrong answer the cwd= pin exists to prevent, through the other door. Here
    the other repo's exclude file ignores .agent-state and this one's does not, so an
    inherited GIT_DIR would report "already ignored" and state would be written into a
    tracked path.
    """
    root = _git_repo(tmp_path / "repo")
    other = _git_repo(tmp_path / "other")
    (other / ".git" / "info").mkdir(exist_ok=True)
    (other / ".git" / "info" / "exclude").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False, "the other repo's rules must not answer for this one"
    assert "no .gitignore" in reason


def test_the_appended_rule_is_anchored_to_the_repo_root(tmp_path):
    """Asserted through git, not against the constant.

    Every other gitignore test compares to GITIGNORE_RULE, so dropping its leading `/`
    stays self-consistent across the whole suite while silently changing what it matches:
    unanchored, it also ignores `packages/app/.agent-state/`, which the constant's own
    comment and INTENT.md both forbid.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")

    nested = f"packages/app/{AGENT_STATE_DIRNAME}/run"
    assert resources._check_ignored(root, f"{AGENT_STATE_DIRNAME}/run") is True
    assert resources._check_ignored(root, nested) is False, "the rule matched a nested directory"


def test_a_tracked_agent_state_is_not_ignored_behind_the_users_back(tmp_path):
    """Committed content is expressed intent, and the ignore rules cannot see it.

    _check_ignored passes --no-index deliberately, so it answers about the RULES and is
    blind to the index. Appending over a directory the user committed does not untrack
    what is already there, but it does make every NEW file under it invisible -- Rule B
    declines rather than reinterpreting a decision they made explicitly.
    """
    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    original = "node_modules/\n"
    gitignore.write_text(original, encoding="utf-8")
    (root / AGENT_STATE_DIRNAME).mkdir()
    (root / AGENT_STATE_DIRNAME / "progress.md").write_text("x\n", encoding="utf-8")
    _commit_all(root)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "tracks files under" in reason
    assert gitignore.read_text(encoding="utf-8") == original


def test_an_untracked_agent_state_directory_is_still_appendable(tmp_path):
    """The tracked check must key on the index, not on the directory merely existing --
    a present-but-untracked .agent-state is the ordinary case on a second run.
    """
    root = _git_repo(tmp_path / "repo")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    _commit_all(root)
    (root / AGENT_STATE_DIRNAME).mkdir()
    (root / AGENT_STATE_DIRNAME / "leftover.txt").write_text("x\n", encoding="utf-8")

    assert ensure_agent_state_ignored(root, _PROBE) == (True, "")


def test_gitignore_failure_names_the_file_once(tmp_path, monkeypatch):
    """This reason is the user's only explanation for state going to temp.

    Each branch names the file exactly once. A reason carrying the path twice reads as
    two different files, and this arm is not otherwise reached: the unreadable-.gitignore
    test fails earlier, at open().
    """

    def raise_io(_fd):
        raise OSError(errno.EIO, "io error")

    root = _git_repo(tmp_path / "repo")
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")
    monkeypatch.setattr(resources, "_read_all", raise_io)

    ignored, reason = ensure_agent_state_ignored(root, _PROBE)

    assert ignored is False
    assert "could not read" in reason
    assert reason.count(str(gitignore)) == 1


# --- resolve_state_dir: placement --------------------------------------------------


@pytest.mark.parametrize("kind", ["planner", "executor"])
def test_project_local_after_appending_the_rule(repo, kind):
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    state_dir = Path(resolve_state_dir(kind))

    assert state_dir.parent == _runs_parent(repo, kind)
    assert GITIGNORE_RULE in (repo / ".gitignore").read_text(encoding="utf-8")


def test_project_local_dir_is_actually_ignored_by_git(repo):
    """End-to-end: git itself must not see the created dir as a working-tree change."""
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    state_dir = Path(resolve_state_dir("planner"))
    (state_dir / "plan.json").write_text("{}", encoding="utf-8")

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    assert AGENT_STATE_DIRNAME not in status
    # The run dir is 0o700 on THIS branch too, not just in a shared /tmp. Only the leaf:
    # the ancestors take mkdir's masked default, which is what INTENT.md now says.
    assert stat.S_IMODE(state_dir.stat().st_mode) == 0o700


def test_resolve_state_dir_does_not_record_the_project(repo):
    """Placement and identity are separate jobs; step 1 owns the recording.

    resolve_state_dir is not called at all on the resume path, so making it the recorder
    leaves that route -- and both fallback routes -- with no project.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")

    state_dir = resolve_state_dir("planner")

    assert not (Path(state_dir) / PROJECT_ROOT_FILE).exists()


def test_dir_name_is_utc_stamp_plus_random_suffix(repo, frozen_clock):
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")

    name = Path(resolve_state_dir("planner")).name

    # yyyymmdd-HHMMSS- then mkdtemp's suffix; no slug (overview.problem is empty here)
    assert name.startswith(frozen_clock.strftime("%Y%m%d-%H%M%S-"))
    assert re.fullmatch(r"\d{8}-\d{6}-\w{6,}", name), name


def test_same_stamp_resolves_never_collide(repo, frozen_clock):
    """Eight runs sharing one timestamp must yield eight distinct directories.

    The clock is frozen, so this pins the mkdtemp-over-computed-name choice rather than
    depending on eight real calls landing inside one wall-clock second.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")

    dirs = [resolve_state_dir("planner") for _ in range(8)]

    stamps = {Path(d).name[: len("YYYYMMDD-HHMMSS")] for d in dirs}
    assert stamps == {frozen_clock.strftime("%Y%m%d-%H%M%S")}
    assert len(set(dirs)) == 8


def test_planner_and_executor_are_separate_subtrees(repo):
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")

    p = Path(resolve_state_dir("planner"))
    e = Path(resolve_state_dir("executor"))

    assert p.parent != e.parent
    assert p.parent.name == "planner" and e.parent.name == "executor"


def test_runs_namespace_cannot_collide_with_a_task_slug(repo):
    """.agent-state/<task-slug>/ is the task-tracking convention's namespace.

    A task slugged "planner" must not land in the same directory as planner runs;
    the "_runs" level is what keeps them apart.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")

    state_dir = Path(resolve_state_dir("planner"))

    assert repo / AGENT_STATE_DIRNAME / "planner" not in state_dir.parents
    assert state_dir.parent.parent.name == RUNS_NAMESPACE


@pytest.mark.parametrize("kind", ["planner", "executor"])
def test_fallback_when_no_project_root(temp_root, monkeypatch, kind):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-abc123")

    state_dir = Path(resolve_state_dir(kind))

    assert state_dir.is_dir()
    assert state_dir.parent == temp_root / "cc-sess-abc123"
    assert state_dir.name.startswith(f"{kind}-")
    # The whole point: not at the shared top-level prefix another session sweeps.


def test_fallback_when_repo_has_no_gitignore(repo, temp_root, monkeypatch):
    """Per-kind naming is pinned by test_fallback_when_no_project_root; this covers the
    decline itself, which is kind-independent.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-xyz")

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent == temp_root / "cc-sess-xyz"
    assert not (repo / ".gitignore").exists()
    assert not (repo / AGENT_STATE_DIRNAME).exists()


def test_fallback_when_project_local_parent_is_unwritable(repo, temp_root, monkeypatch):
    """A read-only or otherwise unwritable checkout must degrade, not abort."""
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-ro")
    # .agent-state exists as a FILE -> mkdir(parents=True) raises OSError under it.
    (repo / AGENT_STATE_DIRNAME).write_text("", encoding="utf-8")

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent == temp_root / "cc-sess-ro"


def test_a_rule_matching_a_synthetic_probe_basename_does_not_satisfy_the_gate(repo):
    """The gate is asked about the runs directory, never about a made-up filename.

    Probing `<AGENT_STATE_DIRNAME>/probe` asks about a file nothing ever creates, so a
    repo carrying a bare `probe` rule answers "ignored" while the run directory beside it
    stays plainly visible to git -- state then lands untracked in the user's repo, where
    a `git clean -fd` destroys in-flight plans: the 2026-08-18 incident relocated from
    /tmp into the project. Asked about the real path, that same repo is correctly found
    unignored, gets the rule appended, and ends up genuinely ignored.
    """
    (repo / ".gitignore").write_text("probe\n", encoding="utf-8")

    state_dir = Path(resolve_state_dir("planner"))
    (state_dir / "plan.json").write_text("{}", encoding="utf-8")

    assert state_dir.parent == _runs_parent(repo, "planner"), "a probe rule must not divert the run"
    assert GITIGNORE_RULE in (repo / ".gitignore").read_text(encoding="utf-8")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    assert AGENT_STATE_DIRNAME not in status


def test_a_run_dir_that_cannot_be_minted_still_takes_the_parent_back(repo, temp_root, monkeypatch):
    """The only decline that runs after the gate may have appended to a tracked file.

    The tree is already dirty at this point, so leaving the directories behind as well
    would compound it -- and the reason must name minting, not the parent write that
    succeeded.
    """
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    real_mkdtemp = tempfile.mkdtemp

    def refuse_run_dir(*args, **kwargs):
        if RUNS_NAMESPACE in str(kwargs.get("dir", "")):
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_mkdtemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkdtemp", refuse_run_dir)

    state_dir = Path(resolve_state_dir("planner"))

    assert temp_root in state_dir.parents
    assert not (repo / AGENT_STATE_DIRNAME).exists()


@pytest.mark.parametrize("rules", ["/.agent-state/*", "/.agent-state/_runs/", ".agent-state/**"])
def test_the_gate_asks_about_the_runs_dir_not_about_agent_state_itself(repo, rules):
    """Which PATH the gate is handed, not just whether it is synthetic.

    `/.agent-state/*` is an ordinary shape (it keeps a `.gitkeep` tracked): the runs
    directory below it is ignored while `.agent-state` itself is not. Asked about the
    parent, the gate reports "not ignored", appends `/.agent-state/` to a version-
    controlled file for no reason, fails its re-probe, and diverts state to temp -- the
    feature defeated and the user's tree dirtied. Asked about the path it is going to
    create, it correctly does nothing.
    """
    gitignore = repo / ".gitignore"
    original = f"{rules}\n"
    gitignore.write_text(original, encoding="utf-8")

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent == _runs_parent(repo, "planner")
    assert gitignore.read_text(encoding="utf-8") == original, "the gate appended for nothing"


def test_a_minted_run_dir_git_will_not_vouch_for_is_taken_back(repo, temp_root, monkeypatch):
    """The last check before state is written, and the take-back behind it.

    A .gitignore cannot reach this branch: git refuses to re-include anything below an
    excluded directory, so the leaf cannot be unignored while its parent is ignored. What
    reaches it is git ceasing to be able to answer between the two probes, which
    `is not True` catches alongside an outright False.

    The take-back is the half with no other guard. `git status` cannot see it -- git does
    not report empty directories -- so only the filesystem shows whether a declined run
    left its tree behind.
    """
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    real_check = resources._check_ignored

    def unanswerable_for_the_leaf(repo_root, relative):
        # The runs parent still answers; the freshly minted leaf below it does not.
        return None if relative.count("/") > 2 else real_check(repo_root, relative)

    monkeypatch.setattr(resources, "_check_ignored", unanswerable_for_the_leaf)

    state_dir = Path(resolve_state_dir("planner"))

    assert temp_root in state_dir.parents
    assert not (repo / AGENT_STATE_DIRNAME).exists(), "the declined run left its tree behind"
    # The appended rule STAYS: removing a line from the user's .gitignore is not this
    # module's to do, and the announcement already said it landed.
    assert GITIGNORE_RULE in (repo / ".gitignore").read_text(encoding="utf-8")


def test_a_declined_gate_leaves_nothing_behind_in_the_tree(repo, temp_root):
    """The runs parent is created BEFORE the gate runs, so a decline must take it back.

    Otherwise every declined run leaves an empty `.agent-state/` in a repo that was
    never going to hold state -- visible in `ls`, and confusing precisely where the
    fallback message says state went somewhere else.
    """
    state_dir = Path(resolve_state_dir("planner"))  # `repo` has no .gitignore: declines

    assert temp_root in state_dir.parents
    assert not (repo / AGENT_STATE_DIRNAME).exists()


def test_a_partly_created_parent_is_taken_back(repo, temp_root, monkeypatch):
    """The mkdir decline's take-back, with something actually to take back.

    The other tests on this arm make `.agent-state` a regular file, so nothing was ever
    created and the take-back is a no-op -- decline() and a bare _fallback look identical.
    A partial mkdir(parents=True) is the shape where they differ.
    """
    real_mkdir = Path.mkdir

    def fail_on_the_leaf(self, *args, **kwargs):
        if self.name == "planner":
            real_mkdir(self.parent, parents=True, exist_ok=True)
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_on_the_leaf)

    state_dir = Path(resolve_state_dir("planner"))

    assert temp_root in state_dir.parents
    assert not (repo / AGENT_STATE_DIRNAME).exists(), "the partly-created tree was left behind"


def test_an_uncreatable_parent_does_not_strand_a_gitignore_rule(repo, temp_root):
    """Ordering guard: the gate may APPEND to a tracked .gitignore, so it must not run
    until the directory is known to be creatable.

    Appending for a run that then lands in temp dirties the user's version-controlled
    file with nothing to show for it, and is silent on every later run, because the rule
    is by then already present and the gate short-circuits before the announcement.
    """
    original = "node_modules/\n"
    (repo / ".gitignore").write_text(original, encoding="utf-8")
    (repo / AGENT_STATE_DIRNAME).write_text("", encoding="utf-8")  # a file: mkdir fails

    state_dir = Path(resolve_state_dir("planner"))

    assert temp_root in state_dir.parents
    assert (repo / ".gitignore").read_text(encoding="utf-8") == original


def test_taking_the_parent_back_never_touches_a_non_empty_agent_state(repo, temp_root):
    """`.agent-state/<task-slug>/` belongs to the global task-tracking convention.

    The take-back walks an explicit list of the directories this run created, so it never
    reaches one it did not make; rmdir refusing a non-empty directory is a second line of
    defence behind that, not the property being relied on.
    """
    keep = repo / AGENT_STATE_DIRNAME / "some-task"
    keep.mkdir(parents=True)
    (keep / "tasks.md").write_text("x\n", encoding="utf-8")

    state_dir = Path(resolve_state_dir("planner"))  # no .gitignore: declines

    assert temp_root in state_dir.parents
    assert (keep / "tasks.md").exists()
    assert not (repo / AGENT_STATE_DIRNAME / RUNS_NAMESPACE).exists()


def test_taking_the_parent_back_never_removes_one_the_user_made(repo, temp_root):
    """rmdir refusing a non-empty directory is not the whole guard.

    An EMPTY `.agent-state/` someone created by hand is exactly as removable as one this
    run made, so the take-back is scoped to the components that did not exist before the
    mkdir -- Rule B, narrowest unambiguous scope, in the module that states Rule B.
    """
    (repo / AGENT_STATE_DIRNAME).mkdir()  # user's, empty, pre-existing

    state_dir = Path(resolve_state_dir("planner"))  # no .gitignore: the gate declines

    assert temp_root in state_dir.parents
    assert (repo / AGENT_STATE_DIRNAME).is_dir(), "the run removed a directory it did not create"
    assert not (repo / AGENT_STATE_DIRNAME / RUNS_NAMESPACE).exists(), "but its own is gone"


def test_taking_the_parent_back_cannot_delete_a_concurrent_runs_plan(tmp_path):
    """The take-back removes empty DIRECTORIES; it must never remove a tree.

    _created_ancestors scopes it to what this run made, but between that capture and the
    decline a second orchestrator in the same repo can mint a run inside one of those
    directories. rmdir refusing a non-empty directory is then the only thing between a
    declining run and another session's in-flight plan -- which is the 2026-08-18 incident
    this whole feature exists to prevent, relocated into the repo.
    """
    parent = tmp_path / AGENT_STATE_DIRNAME / RUNS_NAMESPACE / "planner"
    parent.mkdir(parents=True)
    live = parent / "20260818-000000-liveb"
    live.mkdir()
    (live / "plan.json").write_text('{"overview": {}}', encoding="utf-8")

    resources._prune_empty([parent, parent.parent, parent.parent.parent])

    assert (live / "plan.json").read_text(encoding="utf-8") == '{"overview": {}}'
    assert parent.is_dir(), "a populated ancestor must survive the take-back"


def test_the_take_back_refuses_a_leaf_outside_its_stop(tmp_path):
    """Containment is a precondition, not something to work around: without it the walk
    climbs past `stop` and could rmdir outside the repo. The single call site guarantees
    it today; the helper is bound for a shared module.
    """
    assert resources._created_ancestors(tmp_path / "a" / "b", tmp_path / "elsewhere") == []


def test_taking_the_parent_back_skips_a_component_that_never_appeared(tmp_path):
    """A partial mkdir(parents=True) leaves the shallow components and no leaf.

    Stopping at the first missing entry would strand `.agent-state/_runs/` in a repo that
    was never going to hold state.
    """
    root = tmp_path / AGENT_STATE_DIRNAME
    (root / RUNS_NAMESPACE).mkdir(parents=True)
    never_created = root / RUNS_NAMESPACE / "planner"

    resources._prune_empty([never_created, root / RUNS_NAMESPACE, root])

    assert not root.exists(), "the walk stopped at the component that never appeared"


@pytest.mark.parametrize("mode", [0o777, 0o770, 0o707], ids=["all", "group", "other"])
def test_a_pre_existing_temp_parent_we_do_not_own_is_not_used(temp_root, monkeypatch, capsys, mode):
    """`cc-<session>` is predictable, and CLAUDE_CODE_SESSION_ID is not a secret -- it is
    also the basename of ~/.claude/projects/<slug>/<session>.jsonl.

    mkdir(exist_ok=True) accepts whatever already sits there, including a world-writable
    directory another local user can unlink run dirs from. An unguessable 0700 directory
    is the floor this must not fall below, so an unvouchable parent is not repaired and
    not adopted -- mkdtemp mints one elsewhere.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-victim")
    hostile = temp_root / "cc-sess-victim"
    hostile.mkdir()
    os.chmod(hostile, mode)

    state_dir = Path(resolve_state_dir("planner"))

    assert hostile not in state_dir.parents
    assert state_dir.parent.parent == temp_root
    assert stat.S_IMODE(state_dir.parent.stat().st_mode) == 0o700
    assert "not a private directory of ours" in capsys.readouterr().err


@requires_unprivileged
def test_a_temp_parent_we_cannot_even_stat_is_not_used(temp_root):
    """Unclassifiable is not the same as ours. Answering True adopts a directory whose
    ownership and mode we were unable to read -- the inverse of the whole check.
    """
    blocked = temp_root / "blocked"
    blocked.mkdir()
    (blocked / "cc-sess-opaque").mkdir()
    blocked.chmod(0o000)
    try:
        assert resources._is_our_private_dir(blocked / "cc-sess-opaque") is False
    finally:
        blocked.chmod(0o700)


@requires_unprivileged
def test_a_git_dir_we_cannot_read_is_not_treated_as_a_repo(tmp_path):
    """An EACCES on `.git` must not answer "this is the project".

    It would make the first unreadable ancestor the project root, sending state AND
    approved plans there.
    """
    root = tmp_path / "opaque"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    root.chmod(0o000)
    try:
        assert resources._is_git_dir(root / ".git") is False
    finally:
        root.chmod(0o700)


def test_a_regular_file_at_the_temp_parent_path_is_not_used(temp_root, monkeypatch):
    """Ownership and mode both pass on a regular file we made; only the type test refuses.

    Vouched, it becomes `mkdtemp(dir=<a file>)`, which raises -- and _temp_state_dir turns
    that into sys.exit, so step 1 aborts where the contract says it degrades.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-victim")
    impostor = temp_root / "cc-sess-victim"
    impostor.write_text("", encoding="utf-8")
    impostor.chmod(0o700)

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent.parent == temp_root
    assert impostor.is_file(), "the impostor was replaced rather than declined"


def test_a_temp_parent_that_is_a_symlink_is_not_followed(temp_root, tmp_path, monkeypatch):
    """Same predictable name, planted as a link: mkdir(exist_ok=True) succeeds against
    it and the whole run lands inside whatever it points at.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-victim")
    attacker = tmp_path / "attacker"
    # 0o700 and owned by us, so every test except "is it a link" passes: this is the
    # ~/.ssh shape, where following the link lands the run in a directory that looks
    # exactly like one of ours.
    attacker.mkdir(mode=0o700)
    (temp_root / "cc-sess-victim").symlink_to(attacker, target_is_directory=True)

    state_dir = Path(resolve_state_dir("planner"))

    assert attacker.resolve() not in state_dir.resolve().parents
    assert not list(attacker.iterdir())


def test_a_temp_parent_owned_by_someone_else_is_not_used(temp_root, monkeypatch):
    """Mode and ownership are separate tests, and the fixture can only vary the mode.

    A directory at 0o700 that belongs to another uid is not ours to put a run inside --
    they can unlink it -- but every mode-based assertion passes on it, so without an
    explicit ownership check nothing here would fail.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-victim")
    theirs = temp_root / "cc-sess-victim"
    theirs.mkdir(mode=0o700)
    monkeypatch.setattr(os, "getuid", lambda: os.stat(theirs).st_uid + 1)

    state_dir = Path(resolve_state_dir("planner"))

    assert theirs not in state_dir.parents
    assert state_dir.parent.parent == temp_root


def test_a_hostile_umask_does_not_abort_the_run(temp_root, monkeypatch):
    """mkdir's mode is masked, so a umask clearing OWNER bits leaves a directory we
    cannot create inside -- and _temp_state_dir turns that into sys.exit rather than the
    documented degrade. The chmod after mkdir is what keeps it usable.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-umask")
    previous = os.umask(0o700)
    try:
        state_dir = Path(resolve_state_dir("planner"))
        # Sampled here, ahead of the repair below -- reading the modes after it would hand
        # the assertions the owner bits the repair itself just put back.
        modes = {p: stat.S_IMODE(p.stat().st_mode) for p in (state_dir.parent, state_dir)}
        (state_dir / "plan.json").write_text("{}", encoding="utf-8")
    finally:
        os.umask(previous)
        # Only a FAILING path gets here with anything to repair, which is exactly when it
        # matters: drop either chmod and this run leaves 0o000 directories that pytest's
        # own tmp_path cleanup can never remove, and every later session in this checkout
        # warns about them. Top-down, so each directory is made searchable before os.walk
        # descends into it.
        for containing, subdirs, _ in os.walk(temp_root):
            for name in subdirs:
                d = Path(containing) / name
                d.chmod(stat.S_IMODE(d.stat().st_mode) | stat.S_IRWXU)

    assert state_dir.parent == temp_root / "cc-sess-umask"
    assert modes[state_dir.parent] == 0o700
    # The RUN dir too: mkdtemp's 0o700 is masked the same way, and returning a directory
    # the caller cannot write into defers the failure instead of degrading.
    assert modes[state_dir] == 0o700


@requires_unprivileged
def test_a_temp_parent_we_cannot_write_into_is_not_used(temp_root, monkeypatch):
    """Ownership and the group/other mask both pass on a 0o500 directory of ours.

    Vouched, mkdtemp raises inside it and _temp_state_dir exits -- and because the name
    derives from a session id that does not change, ONE such directory aborts every step 1
    for the rest of the session, with an errno that never names it.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-ro")
    unwritable = temp_root / "cc-sess-ro"
    unwritable.mkdir(mode=0o500)
    try:
        state_dir = Path(resolve_state_dir("planner"))
    finally:
        unwritable.chmod(0o700)

    assert unwritable not in state_dir.parents
    assert state_dir.parent.parent == temp_root


def test_a_parent_this_session_created_is_reused_by_the_next_run(temp_root, monkeypatch):
    """Grouping a session's runs under one parent is the whole point of the derived
    name; the hardening must not cost it for the ordinary case where we made it.
    """
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-mine")

    first = Path(resolve_state_dir("planner"))
    second = Path(resolve_state_dir("executor"))

    assert first.parent == second.parent == temp_root / "cc-sess-mine"


def test_fallback_reason_is_reported_on_stderr(temp_root, capsys):
    """Every condition that declines project-local returns one indistinguishable str."""
    resolve_state_dir("planner")

    err = capsys.readouterr().err
    assert "falls back to temp" in err and "CLAUDE_PROJECT_DIR is unset" in err


@pytest.mark.parametrize(
    "session_id, expected_parent",
    [
        ("sess-plain", "cc-sess-plain"),
        ("../../etc/evil", "cc-etcevil"),
        ("sess-你好-01", "cc-sess--01"),
        ("s" * 300, "cc-" + "s" * 64),
    ],
    ids=["plain", "traversal-stripped", "non-ascii-stripped", "truncated-at-64"],
)
def test_session_token_shapes_the_temp_parent(temp_root, monkeypatch, session_id, expected_parent):
    """The token becomes a directory name: no traversal, no UTF-8, nothing past NAME_MAX."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent == temp_root / expected_parent
    assert state_dir.is_dir()


@pytest.mark.parametrize("session_id", ["", "!!!==="], ids=["unset", "stripped-to-empty"])
def test_random_token_when_session_id_is_unusable(temp_root, monkeypatch, session_id):
    """Punctuation-only is a different input from unset; both need a usable token."""
    if session_id:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
    else:
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)

    state_dir = Path(resolve_state_dir("planner"))

    assert re.fullmatch(r"cc-[0-9a-f]{8}", state_dir.parent.name), state_dir.parent.name


def test_two_sessions_without_an_id_do_not_share_a_parent(temp_root, monkeypatch):
    """Absent CLAUDE_CODE_SESSION_ID the token must be RANDOM, not merely well-shaped.

    The shape assertion elsewhere (`cc-[0-9a-f]{8}`) is satisfied by a constant, which
    would put every id-less session in one predictable parent -- the floor _session_parent
    exists to hold.
    """
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)

    first = Path(resolve_state_dir("planner")).parent
    second = Path(resolve_state_dir("planner")).parent

    assert first != second


def test_temp_parent_is_not_world_readable(temp_root, monkeypatch):
    """cc-<session> is a predictable name in a shared /tmp; state must not be readable."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-perm")

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.parent.stat().st_mode & 0o077 == 0


def test_resolve_state_dir_never_raises_oserror(tmp_path, temp_root, monkeypatch):
    """Neither orchestrator wraps the call, so the helper owns the terminal failure.

    _temp_state_dir exits rather than raising (lib.io.read_text_or_exit's idiom); this
    pins that contract so a future edit cannot turn step 1 into a raw traceback.
    """
    unwritable = tmp_path / "nope"
    unwritable.write_text("", encoding="utf-8")  # a FILE -> mkdir under it raises
    monkeypatch.setattr(tempfile, "tempdir", str(unwritable))

    with pytest.raises(SystemExit) as excinfo:
        resolve_state_dir("planner")
    assert "failed to create planner state directory" in str(excinfo.value)


@requires_unprivileged
def test_resolve_state_dir_survives_an_unsearchable_anchor(tmp_path, temp_root, monkeypatch):
    """A CLAUDE_PROJECT_DIR under a no-search-bit ancestor raises PermissionError."""
    blocked = tmp_path / "blocked"
    inner = blocked / "inner"
    inner.mkdir(parents=True)
    blocked.chmod(0o000)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(inner))
    try:
        state_dir = Path(resolve_state_dir("planner"))
        assert temp_root in state_dir.parents
    finally:
        blocked.chmod(0o755)


# --- retention: _reap_old_runs -----------------------------------------------------


def test_reaper_keeps_the_newest_regardless_of_age(repo):
    """The count bound alone never deletes: a resumed run stays safe however old."""
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    # One fewer than the window: resolve_state_dir's own new dir takes the last slot.
    kept = [
        _make_run(parent, f"20200101-0000{i:02d}-old", age_days=RUNS_MAX_AGE_DAYS + 99)
        for i in range(RUNS_KEEP_NEWEST - 1)
    ]

    resolve_state_dir("planner")

    assert all(d.exists() for d in kept)


def test_reaper_deletes_only_what_is_both_surplus_and_stale(repo):
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    # Sort newest-first by name, so these occupy the whole keep window.
    fresh_surplus = [
        _make_run(parent, f"29990101-0000{i:02d}-fresh", age_days=0)
        for i in range(RUNS_KEEP_NEWEST)
    ]
    stale_surplus = _make_run(parent, "20200101-000000-stale", age_days=RUNS_MAX_AGE_DAYS + 1)

    resolve_state_dir("planner")

    assert not stale_surplus.exists(), "surplus AND stale -> reaped"
    assert all(d.exists() for d in fresh_surplus), "surplus but fresh -> kept"


def test_retention_bounds_are_the_documented_ones():
    """These two numbers decide when shutil.rmtree runs on someone's planning state.

    Every other retention test imports them, so a typo in either propagates into the
    assertions that would otherwise catch it.
    """
    assert RUNS_KEEP_NEWEST == 20
    assert RUNS_MAX_AGE_DAYS == 14


def test_the_reaper_ranks_by_name_not_by_mtime(repo, monkeypatch):
    """The stamp sorts chronologically, which is WHY the name is the key -- but every
    other fixture makes name-order and mtime-order agree, so keying on mtime instead
    passes them all.

    Here they disagree: the lexically newest run is the one touched longest ago. Ranking
    by mtime would put it in the surplus tail and delete it.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    newest_name = _make_run(parent, "29990101-000099-newest", age_days=RUNS_MAX_AGE_DAYS + 99)
    for i in range(RUNS_KEEP_NEWEST):
        _make_run(parent, f"20200101-0000{i:02d}-older-name", age_days=0)

    resolve_state_dir("planner")

    assert newest_name.exists(), "the highest-sorting name must occupy a keep slot"


def test_a_run_one_day_inside_the_age_bound_survives(repo, filled_window):
    """The bound is `>= cutoff` keeps. A run inactive for RUNS_MAX_AGE_DAYS - 1 is inside
    it, and INTENT.md promises that run is kept.

    Every other fixture is age 0 or age +1/+99, so an off-by-one in either direction
    passes them all -- on the arithmetic that decides an rmtree.
    """
    parent = filled_window
    inside = _make_run(parent, "20200101-000000-inside", age_days=RUNS_MAX_AGE_DAYS - 1)

    resolve_state_dir("planner")

    assert inside.exists()


def test_the_keep_rank_boundary_is_exact(repo):
    """`candidates[RUNS_KEEP_NEWEST:]` -- index 19 is the last kept, index 20 the first reaped.

    Every run here is stale, so RANK alone decides, and the two neighbours across the
    boundary are asserted in opposite directions: an off-by-one either way fails. Names
    sort above the dir resolve_state_dir mints for itself, so that one lands below them
    and does not shift the ranks under test.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    stale = [
        _make_run(parent, f"29990101-0000{i:02d}-stale", age_days=RUNS_MAX_AGE_DAYS + 99)
        for i in range(RUNS_KEEP_NEWEST + 1)
    ]

    resolve_state_dir("planner")

    last_kept, first_reaped = stale[1], stale[0]  # sorted descending by name
    assert last_kept.exists(), "the run at the last keep rank was reaped"
    assert not first_reaped.exists(), "the run past the keep rank survived"


def test_reaper_ignores_paths_it_did_not_mint(filled_window):
    """Anything a user parks in the runs directory is never touched, however old.

    The foreign name must sort BELOW the minted stamps. Candidates are ranked by name
    descending, so a leading letter ("my-notes") puts it at rank 0 -- inside the keep
    window, where _RUN_DIR_RE is never consulted and the test passes with the guard
    deleted. A leading "0000-" makes it genuinely surplus, so the regex is the only
    thing standing between it and rmtree.
    """
    parent = filled_window
    foreign = _make_run(parent, "0000-my-notes", age_days=RUNS_MAX_AGE_DAYS + 99)

    resolve_state_dir("planner")

    assert foreign.exists()


def test_reaper_never_stats_through_a_symlinked_run(filled_window, tmp_path, monkeypatch):
    """The symlink skip is observable only as a call, never as an end state.

    shutil.rmtree refuses a symlink outright (avoids_symlink_attacks) and
    _reap_old_runs swallows that OSError, so a planted link survives whether or not the
    guard exists -- asserting the target still exists cannot fail, and does not test
    anything. What the guard actually prevents is _last_activity following the link and
    measuring the TARGET's mtime, which would let an unrelated directory's activity
    decide whether this entry is reaped.
    """
    parent = filled_window
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "keep.txt").write_text("x", encoding="utf-8")
    # Name matches _RUN_DIR_RE and sorts below every stamp above, so it is a candidate
    # AND surplus -- otherwise the keep window, not the guard, is what spares it.
    link = parent / "00000101-000000-link"
    link.symlink_to(outside, target_is_directory=True)

    measured = []
    real_last_activity = resources._last_activity
    monkeypatch.setattr(
        resources, "_last_activity", lambda p: (measured.append(p), real_last_activity(p))[1]
    )

    resolve_state_dir("planner")

    assert link not in measured, "activity was measured through the symlink"
    assert outside.exists() and (outside / "keep.txt").exists()


def test_reaper_spares_a_run_whose_files_are_rewritten_in_place(filled_window):
    """A directory's mtime does not move when an existing file is rewritten.

    Keying retention on the run dir alone calls an actively-edited run stale.
    """
    parent = filled_window
    active = _make_run(parent, "20200101-000000-active", age_days=RUNS_MAX_AGE_DAYS + 1)
    plan = active / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    os.utime(plan, None)  # child is current; the directory's own mtime is not
    os.utime(active, (0, 0))

    resolve_state_dir("planner")

    assert active.exists(), "an in-place edit must count as activity"


def test_reaper_sees_activity_nested_below_the_run_dir(filled_window):
    """A direct-children-only scan calls a run stale when its recent write is deeper."""
    parent = filled_window
    active = _make_run(parent, "20200101-000000-active", age_days=RUNS_MAX_AGE_DAYS + 1)
    nested = active / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "plan.json").write_text("{}", encoding="utf-8")
    old = (datetime.now(UTC) - timedelta(days=RUNS_MAX_AGE_DAYS + 1)).timestamp()
    os.utime(active, (old, old))
    os.utime(active / "sub", (old, old))

    resolve_state_dir("planner")

    assert active.exists(), "activity two levels deep is still activity"


def test_reaper_scan_tolerates_a_broken_symlink_child(filled_window):
    """lstat stats the link, not its target, so a broken symlink is not an error.

    Under stat() it would be, and the raise would abort the scan -- making the answer
    depend on where iterdir() happens to place the broken entry.
    """
    parent = filled_window
    active = _make_run(parent, "20200101-000000-active", age_days=RUNS_MAX_AGE_DAYS + 1)
    (active / "aaa-broken").symlink_to(active / "nowhere")
    (active / "zzz-fresh.json").write_text("{}", encoding="utf-8")
    old = (datetime.now(UTC) - timedelta(days=RUNS_MAX_AGE_DAYS + 1)).timestamp()
    os.utime(active, (old, old))

    resolve_state_dir("planner")

    assert active.exists(), "a broken symlink must not hide a fresh sibling"


@requires_unprivileged
def test_reaper_spares_a_run_dir_it_cannot_enumerate(repo, filled_window):
    """A surplus, stale run holding an unreadable subdirectory is left whole.

    rmtree cannot clear that subdirectory either: it unlinks the siblings it reaches
    first and then fails, leaving the run hollowed out. Judging the run on the readable
    part of its tree is what would let that happen, so _last_activity raises and
    _reap_old_runs skips the candidate.
    """
    parent = filled_window
    stale = _make_run(parent, "00000101-000000-stale", age_days=RUNS_MAX_AGE_DAYS + 99)
    # Contents first, backdating second: every write stamps `stale` fresh, and a run
    # skipped for FRESHNESS never reaches the arm under test.
    blocked = stale / "blocked"
    blocked.mkdir()
    plan = stale / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    old = (datetime.now(UTC) - timedelta(days=RUNS_MAX_AGE_DAYS + 99)).timestamp()
    for target in (plan, blocked, stale):
        os.utime(target, (old, old))
    blocked.chmod(0o000)  # last: utime on it needs no permission, but ordering does
    try:
        # Direct, because the end state cannot separate the two behaviours: judging on the
        # readable part calls the run stale, rmtree then fails at `blocked`, and `stale`
        # exists either way -- only the entries scandir reached first differ.
        with pytest.raises(PermissionError):
            resources._last_activity(stale)

        resolve_state_dir("planner")

        assert stale.exists(), "a run that cannot be judged whole is not reaped"
        assert plan.is_file(), "and is not emptied part-way"
    finally:
        blocked.chmod(0o700)


@requires_unprivileged
def test_reaper_survives_an_unreadable_runs_parent(repo, temp_root):
    """The outer arm: the runs directory itself cannot be listed.

    resolve_state_dir has already minted into it by then, so failing here would abort a
    run whose state dir is perfectly good -- retention is untidy to skip, never fatal.
    """
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    parent = _runs_parent(repo, "planner")
    parent.mkdir(parents=True)
    parent.chmod(0o300)  # writable (mkdtemp works) but not listable (iterdir raises)
    try:
        state_dir = Path(resolve_state_dir("planner"))
        assert state_dir.parent == parent
    finally:
        parent.chmod(0o700)


def test_reaper_spares_a_run_with_a_child_it_cannot_stat(repo, filled_window, monkeypatch):
    """A child can vanish between iterdir() and lstat() -- another session reaping, or the
    user deleting mid-scan. That run is skipped for the pass, not judged on the rest.

    Skipping costs nothing either way. A vanish resolves itself: next pass the child is
    not in the listing at all. A child that persistently refuses lstat sits in a directory
    whose search bit is off, and rmtree needs that same bit to unlink anything inside it.
    """
    parent = filled_window
    stale = _make_run(parent, "20200101-000000-stale", age_days=RUNS_MAX_AGE_DAYS + 1)
    (stale / "vanishes.json").write_text("{}", encoding="utf-8")
    old_ts = (datetime.now(UTC) - timedelta(days=RUNS_MAX_AGE_DAYS + 1)).timestamp()
    os.utime(stale / "vanishes.json", (old_ts, old_ts))
    os.utime(stale, (old_ts, old_ts))

    real_lstat = Path.lstat

    def vanishing_lstat(self, *args, **kwargs):
        if self.name == "vanishes.json":
            raise FileNotFoundError(2, "No such file or directory", str(self))
        return real_lstat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", vanishing_lstat)

    # Direct, for the same reason as the unreadable-subdirectory case: rmtree uses os.lstat
    # rather than Path.lstat, so it would clear this run and the end state alone cannot say
    # whether the child was skipped or the whole run was.
    with pytest.raises(FileNotFoundError):
        resources._last_activity(stale)

    resolve_state_dir("planner")

    assert stale.exists(), "a run that cannot be judged whole is not reaped"


def test_a_candidate_that_vanishes_before_it_is_judged_is_skipped(repo, filled_window, monkeypatch):
    """Two orchestrators reaping one repo: the other one wins the race.

    A candidate deleted between the listing and the judgement makes _last_activity's root
    stat -- deliberately unguarded, so a symlinked or missing run is never judged from a
    partial view -- raise FileNotFoundError. Retention is untidy to skip and never fatal,
    so step 1 still returns the run dir it just minted.
    """
    parent = filled_window
    stale = _make_run(parent, "20200101-000000-stale", age_days=RUNS_MAX_AGE_DAYS + 1)

    real_last_activity = resources._last_activity

    def reaped_by_the_other_session(path: Path) -> float:
        if path == stale:
            shutil.rmtree(path)
        return real_last_activity(path)

    monkeypatch.setattr(resources, "_last_activity", reaped_by_the_other_session)

    state_dir = Path(resolve_state_dir("planner"))

    assert state_dir.is_dir(), "a concurrent reap must not cost this run its state dir"
    assert state_dir.parent == parent
    assert not stale.exists()


def test_reaper_does_not_follow_a_symlinked_child_out_of_the_run_dir(filled_window, tmp_path):
    """lstat, not stat: the walk must not descend through a symlink to elsewhere."""
    parent = filled_window
    stale = _make_run(parent, "20200101-000000-stale", age_days=RUNS_MAX_AGE_DAYS + 1)
    outside = tmp_path / "fresh-elsewhere"
    outside.mkdir()
    (outside / "recent.json").write_text("{}", encoding="utf-8")
    link = stale / "link"
    link.symlink_to(outside, target_is_directory=True)
    old = (datetime.now(UTC) - timedelta(days=RUNS_MAX_AGE_DAYS + 1)).timestamp()
    # Backdate the LINK itself: creating it stamps it fresh, and that is genuine activity
    # in this directory. What must not count is the fresh content on the far side.
    os.utime(link, (old, old), follow_symlinks=False)
    os.utime(stale, (old, old))

    resolve_state_dir("planner")

    assert not stale.exists(), "freshness outside the run dir is not this run's activity"
    assert outside.exists() and (outside / "recent.json").exists()


# --- the orchestrator call sites ---------------------------------------------------


def test_planner_step_1_uses_resolve_state_dir(repo, monkeypatch, capsys):
    """Step 1 must mint the durable path, not tempfile.mkdtemp(prefix='planner-')."""
    from skills.planner.orchestrator import planner as planner_orch

    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["planner.py", "--step", "1"])
    planner_orch.main()

    out = capsys.readouterr().out
    printed = next(line for line in out.splitlines() if line.startswith("STATE_DIR="))
    state_dir = Path(printed.removeprefix("STATE_DIR="))
    assert state_dir.parent == _runs_parent(repo, "planner")
    assert (state_dir / "plan.json").exists()
    # The project-local route must record identity too -- placement does not.
    assert load_project_root(str(state_dir)) == (repo, "")


def test_executor_step_1_uses_resolve_state_dir(repo, monkeypatch, capsys):
    from skills.planner.orchestrator import executor as executor_orch

    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["executor.py", "--step", "1"])
    executor_orch.main()

    out = capsys.readouterr().out
    match = re.search(r"State directory: (\S+)", out)
    assert match, out
    assert Path(match.group(1)).parent == _runs_parent(repo, "executor")


def test_planner_step_1_resume_does_not_clobber_plan_json(repo, tmp_path, monkeypatch, capsys):
    """A supplied --state-dir is the resume path; the skeleton write must not fire."""
    from skills.planner.orchestrator import planner as planner_orch

    state = tmp_path / "resume"
    state.mkdir()
    original = '{"overview": {"problem": "real work", "approach": "a"}}'
    (state / "plan.json").write_text(original, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["planner.py", "--step", "1", "--state-dir", str(state)])
    planner_orch.main()
    capsys.readouterr()

    assert (state / "plan.json").read_text(encoding="utf-8") == original


@requires_unprivileged
def test_an_unsearchable_ancestor_is_reported_not_raised(tmp_path):
    """Path.is_dir() absorbs ENOENT, ENOTDIR, EBADF and ELOOP -- but NOT EACCES.

    An unsearchable ancestor therefore re-raises out of the existence check, and without
    the except arm both orchestrators' step 1 ends in a raw PermissionError traceback
    rather than the one clear line this function exists to produce.
    """
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "inner").mkdir()
    blocked.chmod(0o000)
    try:
        with pytest.raises(SystemExit) as excinfo:
            require_usable_state_dir(str(blocked / "inner"))
        assert "is unusable" in str(excinfo.value)
    finally:
        blocked.chmod(0o755)


@pytest.mark.parametrize("orchestrator", ["planner", "executor"])
def test_step_1_validates_before_it_records(tmp_path, temp_root, monkeypatch, capsys, orchestrator):
    """The order is load-bearing and NOTHING else pins it.

    Both orchestrators exit with the same message under either order, so
    test_step_1_rejects_an_unusable_state_dir cannot tell them apart -- it constrains
    which INPUTS are refused, not the sequence. Recording first puts a soft
    "not recording a project for <dir>" line on stderr immediately before the real error,
    which reads as a degradation when it is a caller mistake. An empty stderr is the
    observable, so the exact wording of that warning is not pinned here.
    """
    target = tmp_path / "nonexistent" / "nested"
    module = f"skills.planner.orchestrator.{orchestrator}"
    main = __import__(module, fromlist=["main"]).main
    monkeypatch.setattr(sys, "argv", [orchestrator, "--step", "1", "--state-dir", str(target)])

    with pytest.raises(SystemExit):
        main()

    assert capsys.readouterr().err == ""


def test_rendering_planner_step_1_does_not_touch_the_project(repo, tmp_path):
    """get_step_guidance/format_output must stay free of side effects on the user's tree.

    Other suites in this repo sweep a module's steps through get_step_guidance() to
    inspect the rendered action lines. With the mint inside init_step's handler, such a
    sweep would append to the developer's own .gitignore and create run dirs in their
    checkout. Rendering a step is not a mutation of the caller's repository, so the mint
    lives in main().
    """
    from skills.planner.orchestrator import planner as planner_orch

    original = "node_modules/\n"
    (repo / ".gitignore").write_text(original, encoding="utf-8")

    rendered = planner_orch.format_output(1, None, str(tmp_path))

    assert (repo / ".gitignore").read_text(encoding="utf-8") == original
    assert not (repo / AGENT_STATE_DIRNAME).exists()
    # The rendered next command must carry the path it was given, not an empty one.
    assert f"--state-dir {shlex.quote(str(tmp_path))}" in str(rendered)


@pytest.mark.parametrize(
    ("marker_bytes", "expected"),
    [
        (None, "no project root recorded"),
        ("{vanished}\n", "no longer a git repository"),
        ("garbage text\n", "did not write"),
    ],
    ids=["unrecorded", "vanished-project", "foreign-marker"],
)
def test_saving_to_docs_says_why_when_no_project_resolves(
    tmp_path, temp_root, capsys, marker_bytes, expected
):
    """The recorded project can be absent, unusable, or foreign.

    In each case the approved plan is silently not archived, and the warning is the only
    thing that says so. An end-state assertion cannot cover it: the outer
    `except Exception` returns None either way.
    """
    from skills.planner.orchestrator import planner as planner_orch

    state = tmp_path / "state"
    state.mkdir()
    (state / "plan.json").write_text(
        '{"overview": {"problem": "p", "approach": "a"}}', encoding="utf-8"
    )
    (state / "plan.md").write_text("# plan\n", encoding="utf-8")
    if marker_bytes is not None:
        vanished = tmp_path / "gone"
        (state / PROJECT_ROOT_FILE).write_text(
            marker_bytes.format(vanished=vanished), encoding="utf-8"
        )

    assert planner_orch._save_plan_to_docs(str(state)) is None

    err = capsys.readouterr().err
    assert "not saving to docs/plans/" in err
    assert expected in err


@pytest.mark.parametrize("orchestrator", ["planner", "executor"])
@pytest.mark.parametrize("bad", ["missing", "a-file"])
def test_steps_after_the_first_reject_an_unusable_state_dir(
    tmp_path, temp_root, monkeypatch, orchestrator, bad
):
    """A state dir that is gone must not be reported as "plan.json not found".

    Retention can remove a run dir between steps, so this is reachable rather than
    hypothetical -- and the misdiagnosis names a file, whose natural fix re-Writes
    plan.json, recreating the directory WITHOUT its project marker and silently costing
    the run its docs/plans archive.

    The flag-presence test below cannot cover this: `--state-dir ""` exits earlier, inside
    validate_state_dir_requirement.
    """
    if bad == "missing":
        target = tmp_path / "reaped"
    else:
        target = tmp_path / "afile"
        target.write_text("", encoding="utf-8")

    module = f"skills.planner.orchestrator.{orchestrator}"
    main = __import__(module, fromlist=["main"]).main
    monkeypatch.setattr(
        sys,
        "argv",
        [orchestrator, "--step", "2", "--state-dir", str(target), "--qr-status", "pass"],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert "is missing or not a directory" in str(excinfo.value)


@pytest.mark.parametrize("orchestrator", ["planner", "executor"])
@pytest.mark.parametrize("step", [2, 4, 6])
def test_steps_after_the_first_refuse_to_run_without_a_state_dir(
    temp_root, monkeypatch, orchestrator, step
):
    """INTENT.md states "Steps 2+ always require --state-dir"; both entry points enforce it.

    Enforcing it only inside step handlers is not equivalent: steps 2 and 3 surface it as
    a raw ValueError traceback, and steps 4 and 6 do not reach a handler that checks at
    all -- step 4 emits `--step 5 --state-dir ''` as its own next command, and step 6
    prints WORKFLOW COMPLETE while skipping both the plan render and the docs/plans
    archive. An empty string is falsy, so `--state-dir ''` reaches every one of those
    paths exactly as an omitted flag does.
    """
    module = f"skills.planner.orchestrator.{orchestrator}"
    main = __import__(module, fromlist=["main"]).main
    monkeypatch.setattr(
        sys, "argv", [orchestrator, "--step", str(step), "--state-dir", "", "--qr-status", "pass"]
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert "--state-dir required" in str(excinfo.value)


def test_no_orchestrator_mints_a_flat_temp_prefix():
    """Regression guard: a flat /tmp prefix is deletable by any session's cleanup glob.

    Matched as a pattern rather than as two exact literals, so a different quote style or
    a third kind cannot slip past. `dir=` is what makes an mkdtemp call safe here -- it
    puts the directory somewhere this module chose.
    """
    package = Path(__file__).parent.parent / "skills" / "planner"
    flat = re.compile(r"mkdtemp\((?![^)]*\bdir=)[^)]*\)")
    scanned = 0
    for src_path in package.rglob("*.py"):
        src = src_path.read_text(encoding="utf-8")
        if "mkdtemp" in src:
            scanned += 1
        assert not flat.search(src), f"{src_path.name} mints a temp dir without an explicit dir="
    # The mints live in shared/resources.py, not in the orchestrators; scanning only the
    # two entry points would point this guard at files where the risk no longer is.
    assert scanned, "no mkdtemp call was scanned -- the guard is pointed at nothing"


def test_skill_md_step_1_does_not_discard_the_caller_cwd():
    """The anchor only resolves because step 1 is invoked without a working-dir/cd.

    Every other anchor test stubs the anchor, so nothing else here can catch the entry
    point regressing to a form that `cd`s into the skill tree before Python starts.
    """
    skill_md = Path(__file__).parents[3] / "skills" / "planner" / "SKILL.md"
    body = skill_md.read_text(encoding="utf-8")
    rows = [
        line
        for line in body.splitlines()
        if "orchestrator.planner --step 1" in line or "orchestrator.executor --step 1" in line
    ]

    assert len(rows) == 2, rows
    for row in rows:
        assert "working-dir" not in row, row
        assert "cd " not in row, row
        assert "uv run --project" in row, row
    # The two must differ ONLY in the module. Asserting each contains the right pieces
    # lets one of them start probing a different directory and stay green.
    assert rows[0].replace("planner --step", "executor --step") == rows[1], rows

    # Self-contained: shell state does not persist between Bash-tool calls, so a command
    # that depends on an assignment made on an earlier line runs with --project empty.
    # Both install layouts reachable, and the selection keyed on something that survives a
    # Bash-tool subprocess: CLAUDE_PROJECT_DIR is not set in one.
    for row in rows:
        assert "$PWD" in row, row
        assert "$HOME/.claude/skills/scripts" in row, row


def test_planner_step_1_records_the_project_on_the_temp_branch(
    tmp_path, temp_root, monkeypatch, capsys
):
    """End-to-end for the shape that loses archiving if identity follows placement:
    a fresh git init with no .gitignore, which declines project-local.
    """
    from skills.planner.orchestrator import planner as planner_orch

    root = _git_repo(tmp_path / "repo")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setattr(sys, "argv", ["planner.py", "--step", "1"])
    planner_orch.main()

    out = capsys.readouterr().out
    state_dir = next(
        line for line in out.splitlines() if line.startswith("STATE_DIR=")
    ).removeprefix("STATE_DIR=")
    assert temp_root in Path(state_dir).parents
    assert load_project_root(state_dir) == (root, "")


def test_planner_step_1_records_the_project_on_the_resume_path(
    tmp_path, temp_root, monkeypatch, capsys
):
    """A supplied --state-dir skips resolve_state_dir entirely; nothing else records
    the project on this route.
    """
    from skills.planner.orchestrator import planner as planner_orch

    root = _git_repo(tmp_path / "repo")
    state = tmp_path / "resume"
    state.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setattr(sys, "argv", ["planner.py", "--step", "1", "--state-dir", str(state)])
    planner_orch.main()
    capsys.readouterr()

    assert load_project_root(str(state)) == (root, "")


def test_executor_step_1_records_the_project(tmp_path, temp_root, monkeypatch, capsys):
    from skills.planner.orchestrator import executor as executor_orch

    root = _git_repo(tmp_path / "repo")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setattr(sys, "argv", ["executor.py", "--step", "1"])
    executor_orch.main()

    out = capsys.readouterr().out
    match = re.search(r"State directory: (\S+)", out)
    assert match, out
    assert load_project_root(match.group(1)) == (root, "")


@pytest.mark.parametrize("orchestrator", ["planner", "executor"])
@pytest.mark.parametrize("bad", ["missing", "is-a-file"])
def test_step_1_rejects_an_unusable_state_dir(tmp_path, temp_root, monkeypatch, orchestrator, bad):
    """Without this, the executor announces "State directory: <path>" for a
    path that does not exist, and tells the agent to Write plan.json into it.

    Both entry points validate through one helper, so they cannot diverge on which
    inputs they accept.
    """
    if bad == "missing":
        target = tmp_path / "nonexistent" / "nested"
    else:
        target = tmp_path / "afile"
        target.write_text("", encoding="utf-8")

    module = f"skills.planner.orchestrator.{orchestrator}"
    main = __import__(module, fromlist=["main"]).main
    monkeypatch.setattr(sys, "argv", [orchestrator, "--step", "1", "--state-dir", str(target)])

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert "is missing or not a directory" in str(excinfo.value)


@pytest.mark.parametrize("orchestrator", ["planner", "executor"])
@requires_unprivileged
def test_step_1_degrades_on_an_unwritable_state_dir(tmp_path, temp_root, monkeypatch, orchestrator):
    """A supplied --state-dir that exists but cannot be written must not traceback.

    require_usable_state_dir checks existence only, so the individual writes are what
    meet this. The executor's stale-verify.json unlink is one of them: missing_ok covers
    ENOENT alone, so an unwritable directory makes the unlink raise PermissionError,
    which must be caught rather than escaping main().
    """
    state = tmp_path / "ro"
    state.mkdir()
    (state / "verify.json").write_text("{}", encoding="utf-8")
    (state / "plan.json").write_text("{}", encoding="utf-8")
    state.chmod(0o555)

    module = f"skills.planner.orchestrator.{orchestrator}"
    main = __import__(module, fromlist=["main"]).main
    monkeypatch.setattr(sys, "argv", [orchestrator, "--step", "1", "--state-dir", str(state)])
    try:
        # Either completing or exiting cleanly is acceptable; raising is not.
        try:
            main()
        except SystemExit:
            pass
    finally:
        state.chmod(0o755)


@requires_unprivileged
def test_planner_step_1_reports_a_failed_skeleton_write(tmp_path, temp_root, monkeypatch):
    """The unwritable-dir case above pre-seeds plan.json, so `if not exists()` short-
    circuits and the write handler is never reached. This drives it with a fresh dir.
    """
    from skills.planner.orchestrator import planner as planner_orch

    state = tmp_path / "ro-fresh"
    state.mkdir()
    state.chmod(0o555)
    monkeypatch.setattr(sys, "argv", ["planner.py", "--step", "1", "--state-dir", str(state)])
    try:
        with pytest.raises(SystemExit) as excinfo:
            planner_orch.main()
        assert "cannot write plan.json" in str(excinfo.value)
    finally:
        state.chmod(0o755)
