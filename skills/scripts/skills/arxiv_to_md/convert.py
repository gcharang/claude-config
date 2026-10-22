"""arxiv-to-md converter: write one arXiv paper's TeX source as Markdown, without a model.

  --arxiv-id ID (--out-dir DIR | --dest-file FILE) [--main-tex REL]

Paths are absolute: the command runs from the scripts directory. On success it prints

  FILE: <path written>
  DATE: <YYYY-MM-DD>          (with --out-dir, when the abstract page gives the first-submission date)
  RESIDUAL: <n> spans         (when n lines hold LaTeX left outside math and code)

and exits 0. Otherwise it prints one FAIL: <reason> line and exits 1.
"""

import argparse
import errno
import gzip
import html.parser
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from skills.arxiv_to_md.tex_utils import preprocess_tex, read_tex_text, strip_comments

MIB = 2**20
MAX_DOWNLOAD_BYTES = 100 * MIB
MAX_UNPACKED_BYTES = 500 * MIB
MAX_MEMBERS = 5000
MAX_PAGE_BYTES = 5 * MIB
NETWORK_TIMEOUT = 60  # seconds per socket operation
PANDOC_TIMEOUT = 300  # seconds
TOTAL_TIMEOUT = 540  # seconds per paper, below the Bash tool's 600 s maximum
PANDOC_HEAP_MIB = 1024
PANDOC_MIN_VERSION = (2, 15)
MAX_OLDER_VERSIONS = 2
MAX_LISTED_CANDIDATES = 20
ARXIV_ID_RE = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z]+(?:-[a-z]+)*(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?")

_SAFE_CANDIDATE_RE = re.compile(r"[A-Za-z0-9._/-]+")
_NO_HARD_LINKS = frozenset({errno.EPERM, errno.ENOTSUP, errno.ENOSYS, errno.EXDEV})
_PREFERRED_MAIN_NAMES = ("main.tex", "paper.tex", "ms.tex")
_DOCUMENT_CLASS_RE = re.compile(
    r"\\document(?:class|style)\s*(?:\[[^\]]{0,500}\]\s*)?\{([^}]{0,100})\}"
)
_TITLE_BREAKS = re.compile(r"[?;:]")
_WHITESPACE = re.compile(r"\s+")
_DROPPED_SECTIONS = frozenset(
    {
        "references",
        "bibliography",
        "acknowledgments",
        "acknowledgements",
        "acknowledgment",
        "acknowledgement",
    }
)
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING_RE = re.compile(r"(#{1,6})[ \t]+(.*)$")
_SECTION_NUMBER_RE = re.compile(r"\d+(?:\.\d+)*\.?\s+")
_DIV_FENCE_RE = re.compile(r"^(:{3,})(.*)$")
_BIBLIOGRAPHY_CLASS_RE = re.compile(r"(?<![\w-])thebibliography(?![\w-])")
_IMAGE_RE = re.compile(
    r"!\[((?:[^\[\]]|\[[^\[\]]{0,200}\]){0,1000})\]\(([^)\n]{0,1000})\)(?:\{[^}\n]{0,1000}\})?"
)
_CITATION_RE = re.compile(r"\[(-?@[^\[\]@;]+(?:;\s*-?@[^\[\]@;]+)*)\]")
_CITATION_MARK_RE = re.compile(r"(^|;\s*)-?@")
_MASK_TOKEN_RE = re.compile(r"\\[^A-Za-z]|\$\$|\$|`[^`\n]*`")
_COMMAND_RE = re.compile(r"\\[A-Za-z]")
_PANDOC_ERROR_RE = re.compile(r"Error at \(line \d+, column \d+\):?")
_PANDOC_VERSION_RE = re.compile(r"^pandoc\S*\s+(\d+(?:\.\d+)*)")


class ConvertError(Exception):
    """The message is the FAIL: reason."""


class NoTexSource(ConvertError):
    """The archive holds no TeX main file."""


def _timeout(own: float, deadline: float | None) -> float:
    if deadline is None:
        return own
    left = deadline - time.monotonic()
    if left <= 0:
        raise ConvertError(f"conversion ran past {TOTAL_TIMEOUT} s")
    return min(own, left)


def fetch(url: str, dest: Path, max_bytes: int, deadline: float | None = None) -> str:
    """Stream url into dest; return the Content-Disposition file name, or ''."""
    try:
        with urllib.request.urlopen(url, timeout=_timeout(NETWORK_TIMEOUT, deadline)) as resp:
            name = resp.headers.get_filename() or ""
            total = 0
            with dest.open("wb") as out:
                while chunk := resp.read(MIB):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ConvertError(f"download exceeds {max_bytes // MIB} MiB")
                    out.write(chunk)
                    _timeout(NETWORK_TIMEOUT, deadline)
    except urllib.error.HTTPError as e:
        raise ConvertError(f"HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ConvertError(f"{url}: {e}") from e
    return name


class _MetaParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        name = attributes.get("name")
        content = attributes.get("content")
        if name in ("citation_title", "citation_date") and content is not None:
            self.found.setdefault(name, content)


def fetch_metadata(
    arxiv_id: str, work: Path, deadline: float | None = None
) -> tuple[str | None, str | None]:
    """Title and first-submission date (YYYY-MM-DD) from the abstract page; None when unavailable."""
    page = work / "abs.html"
    try:
        fetch(f"https://arxiv.org/abs/{arxiv_id}", page, MAX_PAGE_BYTES, deadline)
        parser = _MetaParser()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        parser.close()
        title = " ".join(parser.found["citation_title"].split())
        date = datetime.strptime(parser.found["citation_date"], "%Y/%m/%d").date().isoformat()
    except (ConvertError, OSError, KeyError, ValueError):
        return None, None
    return title or None, date


def _head(path: Path, n: int) -> bytes:
    with path.open("rb") as f:
        return f.read(n)


def _gunzip_capped(src: Path, dest: Path) -> None:
    total = 0
    try:
        with gzip.open(src, "rb") as f, dest.open("wb") as out:
            while chunk := f.read(MIB):
                total += len(chunk)
                if total > MAX_UNPACKED_BYTES:
                    raise ConvertError(
                        f"source exceeds {MAX_UNPACKED_BYTES // MIB} MiB uncompressed"
                    )
                out.write(chunk)
    except (OSError, EOFError, zlib.error) as e:
        raise ConvertError(f"cannot decompress the source: {type(e).__name__}") from e


def _member_filter(member: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo | None:
    # Link members are skipped: a TeX build does not need them, and a tree without links
    # keeps every later containment check a plain resolved-prefix check.
    if member.issym() or member.islnk():
        return None
    if member.issparse():
        raise ConvertError("source archive has a sparse member")
    return tarfile.data_filter(member, dest_path)


def _extract_tar(tar_path: Path, src_dir: Path) -> None:
    if not hasattr(tarfile, "data_filter"):
        raise ConvertError("safe tar extraction needs Python 3.11.4 or later")
    try:
        with tarfile.open(tar_path, "r:") as tar:
            total = 0
            for count, member in enumerate(tar, 1):
                if count > MAX_MEMBERS:
                    raise ConvertError(f"source archive has more than {MAX_MEMBERS} members")
                if member.issparse():
                    raise ConvertError("source archive has a sparse member")
                if member.isreg():
                    total += member.size
                if total > MAX_UNPACKED_BYTES:
                    raise ConvertError(
                        f"source archive exceeds {MAX_UNPACKED_BYTES // MIB} MiB unpacked"
                    )
            tar.extractall(src_dir, filter=_member_filter)
    except tarfile.FilterError as e:
        raise ConvertError(f"unsafe archive member ({type(e).__name__})") from e
    except (tarfile.TarError, OSError) as e:
        raise ConvertError(f"cannot unpack the source archive: {type(e).__name__}") from e


def unpack_source(download: Path, src_dir: Path, tex_name: str) -> None:
    """Unpack an e-print (gzipped tar, tar, gzipped single file, plain file) into src_dir.

    A PDF or PostScript payload leaves src_dir empty.
    """
    src_dir.mkdir(parents=True, exist_ok=True)
    payload = download
    if _head(download, 2) == b"\x1f\x8b":
        payload = download.with_name(download.name + ".unpacked")
        _gunzip_capped(download, payload)
    if tarfile.is_tarfile(payload):
        _extract_tar(payload, src_dir)
    elif _head(payload, 4) not in (b"%PDF", b"%!PS"):
        shutil.copyfile(payload, src_dir / tex_name)  # single-file submission


def _reject_html(download: Path) -> None:
    if _head(download, 512).lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise ConvertError("arXiv returned an HTML page, not a source archive")


def _flat(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_")


def _document_class(text: str) -> str | None:
    found = _DOCUMENT_CLASS_RE.search(text)
    return found.group(1).strip() if found else None


def find_main_tex(src_dir: Path, arxiv_id: str, override: str | None) -> Path:
    """Return the main .tex file of an extracted source tree."""
    candidates: list[Path] = []
    for tex in sorted(src_dir.rglob("*.tex")):
        if not tex.is_file():
            continue
        text = strip_comments(read_tex_text(tex))
        doc_class = _document_class(text)
        if doc_class is not None and doc_class != "standalone":
            candidates.append(tex)
    if not candidates:
        raise NoTexSource("no TeX source (PDF-only submission)")

    root = src_dir.resolve()
    if override is not None:
        chosen = (src_dir / override).resolve()
        if (
            not _SAFE_CANDIDATE_RE.fullmatch(override)
            or not chosen.is_relative_to(root)
            or chosen not in {c.resolve() for c in candidates}
        ):
            raise ConvertError("--main-tex does not name a main-file candidate of the archive")
        return chosen
    if len(candidates) == 1:
        return candidates[0]

    preferred = (f"{_flat(arxiv_id)}.tex", *_PREFERRED_MAIN_NAMES)
    top_level = [c for c in candidates if c.parent == src_dir and c.name in preferred]
    if len(top_level) == 1:
        return top_level[0]

    names = [
        rel for c in candidates if _SAFE_CANDIDATE_RE.fullmatch(rel := str(c.relative_to(src_dir)))
    ]
    if not names:
        raise ConvertError(
            "several main .tex candidates, all with names outside the set [A-Za-z0-9._/-]"
        )
    shown = " ".join(names[:MAX_LISTED_CANDIDATES])
    if len(names) > MAX_LISTED_CANDIDATES:
        shown += f" (and {len(names) - MAX_LISTED_CANDIDATES} more)"
    raise ConvertError(f"several main .tex candidates: {shown}; run again with --main-tex <one>")


def _check_pandoc_version(pandoc: str, work: Path, deadline: float | None) -> None:
    too_old = ConvertError(
        "pandoc {}.{} or newer is required (--sandbox)".format(*PANDOC_MIN_VERSION)
    )
    try:
        result = subprocess.run(
            [pandoc, "--version"],
            capture_output=True,
            timeout=_timeout(30, deadline),
            cwd=work,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ConvertError("pandoc --version timed out") from e
    first = result.stdout.decode("utf-8", errors="replace").splitlines()[:1]
    found = _PANDOC_VERSION_RE.match(first[0]) if first else None
    if found is None:
        raise too_old
    version = tuple(int(part) for part in found.group(1).split("."))
    if version < PANDOC_MIN_VERSION:
        raise too_old


def run_pandoc(tex: Path, work: Path, deadline: float | None = None) -> str:
    """Convert tex to Markdown with pandoc, sandboxed and memory-capped."""
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise ConvertError("pandoc not found on PATH")
    _check_pandoc_version(pandoc, work, deadline)
    command = [
        pandoc,
        "+RTS",
        f"-M{PANDOC_HEAP_MIB}m",
        "-RTS",
        "--sandbox",
        str(tex),
        "-f",
        "latex",
        "-t",
        "markdown",
        "--wrap=none",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=_timeout(PANDOC_TIMEOUT, deadline),
            cwd=work,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ConvertError("pandoc ran past its time limit") from e
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        if result.returncode == 251 or "heap exhausted" in stderr.lower():
            raise ConvertError(f"pandoc exceeded the {PANDOC_HEAP_MIB} MiB memory cap")
        found = _PANDOC_ERROR_RE.search(stderr)
        detail = found.group(0) if found else f"exit status {result.returncode}"
        raise ConvertError(f"pandoc failed: {detail}")
    return result.stdout.decode("utf-8", errors="replace")


def _fenced_lines(lines: list[str]) -> list[bool]:
    """Per line: inside a fenced code block, fence lines included."""
    flags = []
    fence: tuple[str, int] | None = None
    for line in lines:
        if fence is None:
            m = _FENCE_OPEN_RE.match(line)
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = (m.group(1)[0], len(m.group(1)))
                flags.append(True)
            else:
                flags.append(False)
        else:
            flags.append(True)
            stripped = line.strip()
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= fence[1]:
                fence = None
    return flags


def _heading(line: str) -> tuple[int, str] | None:
    m = _HEADING_RE.match(line)
    if m is None:
        return None
    text = m.group(2).strip()
    if text.endswith("}"):
        brace = text.rfind("{")
        if brace != -1 and "}" not in text[brace:-1]:
            text = text[:brace].rstrip()
    return len(m.group(1)), text


def _is_dropped_section(heading_text: str) -> bool:
    if len(heading_text) > 200:
        return False
    number = _SECTION_NUMBER_RE.match(heading_text)
    if number:
        heading_text = heading_text[number.end() :]
    return heading_text.rstrip(".:").strip().casefold() in _DROPPED_SECTIONS


def clean_markdown(md: str) -> str:
    """Drop reference/acknowledgment sections and bibliography divs; simplify images and citations."""
    lines = md.split("\n")
    fenced = _fenced_lines(lines)
    out: list[str] = []
    drop_level: int | None = None
    div_depth = 0
    for line, in_code in zip(lines, fenced, strict=True):
        if in_code:
            if drop_level is None and div_depth == 0:
                out.append(line)
            continue

        if div_depth:
            div = _DIV_FENCE_RE.match(line)
            if div:
                div_depth += -1 if not div.group(2).strip() else 1
            continue

        heading = _heading(line)
        if drop_level is not None:
            if heading is None or heading[0] > drop_level:
                continue
            drop_level = None
        if heading and _is_dropped_section(heading[1]):
            drop_level = heading[0]
            continue

        div = _DIV_FENCE_RE.match(line)
        if div and div.group(2).strip() and _BIBLIOGRAPHY_CLASS_RE.search(div.group(2)):
            div_depth = 1
            continue

        line = _IMAGE_RE.sub(_image_placeholder, line)
        line = _CITATION_RE.sub(
            lambda m: "[" + _CITATION_MARK_RE.sub(r"\1", m.group(1)) + "]", line
        )
        out.append(line)
    return "\n".join(out)


def _image_placeholder(m: re.Match[str]) -> str:
    label = m.group(1).strip() or os.path.basename(m.group(2))
    return f"[IMAGE: {label}]"


def _unmasked_text(line: str, in_display: bool) -> tuple[str, bool]:
    """Line text outside math, code spans and Markdown escapes; the display-math state after it."""
    visible: list[str] = []
    pos = 0
    while True:
        token = _MASK_TOKEN_RE.search(line, pos)
        if token is None:
            if not in_display:
                visible.append(line[pos:])
            return " ".join(visible), in_display
        text = token.group(0)
        if in_display:
            if text == "$$":
                in_display = False
            pos = token.end()
            continue
        visible.append(line[pos : token.start()])
        pos = token.end()
        if text == "$$":
            in_display = True
        elif text == "$":
            close = line.find("$", pos)
            if close > pos:
                pos = close + 1
            else:
                visible.append(text)


def find_residual_spans(md: str) -> list[tuple[int, str]]:
    """Lines holding a LaTeX command outside math, code and Markdown escapes.

    Display math may span lines; indented lines count as code only outside display math.
    """
    lines = md.split("\n")
    fenced = _fenced_lines(lines)
    spans = []
    in_display = False
    for number, (line, in_code) in enumerate(zip(lines, fenced, strict=True), 1):
        if in_code or (not in_display and line.startswith(("    ", "\t"))):
            continue
        text, in_display = _unmasked_text(line, in_display)
        if _COMMAND_RE.search(text):
            spans.append((number, line.strip()[:200]))
    return spans


def build_filename(title: str | None, date: str | None, arxiv_id: str) -> str:
    spaced = _WHITESPACE.sub(" ", _TITLE_BREAKS.sub(" - ", title or ""))
    name = " ".join("".join(ch for ch in spaced if ch.isalnum() or ch in " .,-_").split())
    if not name or not date:
        return _flat(arxiv_id) + ".md"
    return f"{date} {name}.md"


def write_new(path: Path, text: str) -> None:
    """Publish text at path atomically; an existing name is never replaced."""
    try:
        fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".arxiv-to-md-", suffix=".tmp")
    except OSError as e:
        raise ConvertError(f"cannot create {shlex.quote(str(path))}: {e}") from e
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        temp.chmod(0o644)
        try:
            os.link(temp, path)
        except FileExistsError:
            raise
        except OSError as e:
            if e.errno not in _NO_HARD_LINKS:
                raise
            _write_exclusive(path, text)
    except FileExistsError as e:
        raise ConvertError(f"destination exists: {shlex.quote(str(path))}") from e
    except OSError as e:
        raise ConvertError(f"cannot write {shlex.quote(str(path))}: {e}") from e
    finally:
        temp.unlink(missing_ok=True)


def _write_exclusive(path: Path, text: str) -> None:
    """Exclusive-create write for filesystems that refuse hard links."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _ensure_absent(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise ConvertError(f"destination exists: {shlex.quote(str(path))}")


def _fetch_source(name: str, work: Path, deadline: float) -> tuple[Path, str]:
    download = work / f"download-{_flat(name)}"
    url_name = fetch(f"https://arxiv.org/e-print/{name}", download, MAX_DOWNLOAD_BYTES, deadline)
    _reject_html(download)
    return download, url_name


def convert(
    arxiv_id: str, out_dir: Path | None, dest_file: Path | None, main_tex: str | None
) -> tuple[Path, str | None, list[tuple[int, str]]]:
    """Convert one paper; return the written path, the first-submission date and the residual spans."""
    deadline = time.monotonic() + TOTAL_TIMEOUT
    date: str | None = None
    with tempfile.TemporaryDirectory(prefix="arxiv-to-md-") as work_name:
        work = Path(work_name)
        if dest_file is not None:
            destination = dest_file
            _ensure_absent(destination)
        else:
            assert out_dir is not None
            title, date = fetch_metadata(arxiv_id, work, deadline)
            destination = out_dir / build_filename(title, date, arxiv_id)
            _ensure_absent(destination)

        tex_name = _flat(arxiv_id) + ".tex"
        download, served_name = _fetch_source(arxiv_id, work, deadline)
        src = work / "src"
        unpack_source(download, src, tex_name)
        try:
            main = find_main_tex(src, arxiv_id, main_tex)
            root = src
        except NoTexSource:
            found = _older_version(arxiv_id, served_name, work, tex_name, deadline, main_tex)
            if found is None:
                raise
            main, root = found

        preprocessed = preprocess_tex(str(main), root=str(root))
        raw = run_pandoc(Path(preprocessed), work, deadline)
        cleaned = clean_markdown(raw)
        if not cleaned.strip():
            raise ConvertError("pandoc produced no text")
        spans = find_residual_spans(cleaned)
        write_new(destination, cleaned)
    return destination, date, spans


def _older_version(
    arxiv_id: str,
    served_name: str,
    work: Path,
    tex_name: str,
    deadline: float,
    main_tex: str | None,
) -> tuple[Path, Path] | None:
    latest = re.search(r"v(\d+)\.[a-z.]+$", served_name)
    if re.search(r"v\d+$", arxiv_id) or latest is None or int(latest.group(1)) <= 1:
        return None
    newest = int(latest.group(1))
    for version in range(newest - 1, max(newest - 1 - MAX_OLDER_VERSIONS, 0), -1):
        download, _ = _fetch_source(f"{arxiv_id}v{version}", work, deadline)
        src = work / f"src-v{version}"
        unpack_source(download, src, tex_name)
        try:
            return find_main_tex(src, arxiv_id, main_tex), src
        except NoTexSource:
            continue
    raise ConvertError("no TeX source in any version (PDF-only submission)")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _fail(message)


def _fail(reason: str) -> NoReturn:
    print("FAIL: " + " ".join(reason.split())[:500])
    sys.exit(1)


def _on_sigterm(signum, frame):
    sys.exit(128 + signum)


def main() -> None:
    parser = _Parser(description="arxiv-to-md converter: one arXiv paper to Markdown")
    parser.add_argument("--arxiv-id", required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--out-dir", help="Absolute existing directory; the filename is built")
    target.add_argument("--dest-file", help="Absolute path whose parent directory exists")
    parser.add_argument(
        "--main-tex", help="Path in the source archive, after a several-candidates FAIL"
    )
    args = parser.parse_args()

    if not ARXIV_ID_RE.fullmatch(args.arxiv_id):
        _fail("invalid arXiv id")
    out_dir = Path(args.out_dir) if args.out_dir else None
    dest_file = Path(args.dest_file) if args.dest_file else None
    if out_dir is not None and not (out_dir.is_absolute() and out_dir.is_dir()):
        _fail("--out-dir must be an absolute existing directory")
    if dest_file is not None and not (dest_file.is_absolute() and dest_file.parent.is_dir()):
        _fail("--dest-file must be an absolute path in an existing directory")
    if args.main_tex is not None and Path(args.main_tex).is_absolute():
        _fail("--main-tex must be relative to the source archive")

    signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        written, date, spans = convert(args.arxiv_id, out_dir, dest_file, args.main_tex)
    except ConvertError as e:
        _fail(str(e))
    except (OSError, subprocess.TimeoutExpired) as e:
        _fail(f"{type(e).__name__}: {e}")
    print(f"FILE: {written}")
    if date:
        print(f"DATE: {date}")
    if spans:
        print(f"RESIDUAL: {len(spans)} spans")


if __name__ == "__main__":
    main()
