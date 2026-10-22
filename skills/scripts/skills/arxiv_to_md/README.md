# arxiv_to_md Architecture

## Working Directory

Every command the orchestrator prints runs under `uv run --directory <skills/scripts>`
(`pin_cwd`), so `convert.py` and `sub_agent.py` start in the scripts project, not in the
user's directory. They take absolute paths: `convert.py` rejects a relative `--out-dir`
or `--dest-file`, and step 1 has the orchestrator write the user's directory as one.

## Untrusted Source

An e-print is whatever the authors uploaded. arXiv serves it as a gzipped tar, a single
gzipped file, or a PDF when there is no TeX source (Content-Disposition
`arXiv-<id>v<N>.tar.gz`, `.gz` or `.pdf`, checked 2026-10-22), so `convert.py` sniffs the
bytes instead of assuming a tar.

- Decompression and extraction run under the size and member caps defined at the top of
  `convert.py`, through tarfile's `data` filter (Python 3.11.4 or later); link members
  are skipped, so nothing in the extracted tree points outside it.
- `tex_utils.expand_inputs` inlines only files inside the extracted tree.
- pandoc runs with `--sandbox` and a heap cap: without `--sandbox`, pandoc itself reads
  the files that `\lstinputlisting`, `\input` and `\include` name, wherever they are.
- One deadline covers a paper's downloads and subprocesses; a SIGTERM exits through the
  cleanup below.
- Work files live in a `tempfile.TemporaryDirectory` that is removed when the command
  exits.
- The destination is written to a temporary file beside it and published with
  `os.link`, which refuses an existing name: an existing file is never replaced;
  `convert.py` reports it instead.
- `convert.py` prints no paper text to the main session: the written path, the date,
  a residual-span count and fixed-wording failures. The paper's title enters only the
  written file name, and file names of several-candidate main files are shell-quoted.

## Invariants

- Every rendered command starts with `uv run` (`tests/test_uv_run_invariant.py`).
