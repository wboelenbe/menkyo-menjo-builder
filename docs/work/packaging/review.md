# Review: packaging

## Round 1

REVIEW: CHANGES REQUESTED

Checked: wheel and sdist built with `uv build` into a temp dir; wheel installed into a throwaway venv and run from outside the checkout with an isolated HOME; `deploy/Dockerfile` built and `dan` rendered (overlay, overlay-flat, proof; pdf+png; `--press --json`) with the example config only: 10 progress steps, all accounted for; the flat PDF embeds YujiBoku-Regular; `--no-ink` gives 1 step. Homebrew `libexec/src` layout simulated. Checkout resolves repo `dojo.toml` and `./build`; wheel, frozen and Homebrew resolve the per-user folder and `~/Documents/Menkyo`. The wheel holds the font and `example.toml`. Stdout without `--json` is unchanged; no stray subprocess output reaches stdout under `--json`. PyInstaller datas land where `paths.resource()` looks. No commits during the run.

[R-1] major contract — src/menkyo/build_diploma.py:981-1001 (cli), src/menkyo/config.py:105
What: Under `--json`, several failures exit without an `error` event: argparse errors (`--bogus`, `--dpi abc`) print usage to stderr and exit 2; a malformed TOML raises an uncaught `tomllib.TOMLDecodeError` (traceback, no event); an unwritable `--out` raises an uncaught `OSError` from `os.makedirs` (traceback). Reproduced all three: the last stdout line was never an `error` event.
Why it matters: The README promises an `error` event and exit 1 when a run fails. dojo-portal writes its own TOML and out dir; a bad setting or a full/read-only disk reaches it as a bare traceback with no event.
Suggested fix: In `cli()` under `--json`, also catch `Exception` → `error` with `f"{type(e).__name__}: {e}"`, exit 1 (as `service.run_build` does). Make argparse failures user messages (`exit_on_error=False` or an `error()` override raising `SystemExit(message)`). Ideally `config.load` turns `TOMLDecodeError` into `SystemExit(f"{path}: {e}")` so CLI and GUI both get a readable message.

[R-2] minor packaging/personal data — src/menkyo/paths.py:21-32 (checkout_root)
What: Any `pyproject.toml` two levels above the package counts as a checkout; `__init__._version` checks `[project].name == "menkyo"` but `checkout_root` does not.
Why it matters: A copy vendored inside another project with its own `pyproject.toml` (e.g. `pip install --target <proj>/vendor`, or `<proj>/src/menkyo`) is treated as a checkout: reads `<proj>/dojo.toml`, writes `<proj>/build` when `-c`/`--out` are omitted. Also makes the deploy image a "checkout" (R-3).
Suggested fix: `checkout_root()` also requires the project name `menkyo`; `_version` uses `paths.checkout_root()` instead of duplicating the logic.

[R-3] minor packaging — deploy/Dockerfile:14-17, web/app.py:23
What: The image does `pip install /app`, but `web/app.py` puts `/app/src` first on `sys.path`, so the web app imports `/app/src/menkyo`, never the installed copy (confirmed `menkyo.__file__` = `/app/web/../src/menkyo/__init__.py`). With `/app/pyproject.toml` present the image is a "checkout": `LOCAL_CONFIG=/app/dojo.toml`, default output `/app/build` (unwritable for `app`).
Why it matters: Harmless today (the web app always passes `--out`, `/data` wins), but two copies of the code and checkout behaviour inside a deployed container.
Suggested fix: Build/install from a temp dir and keep only `web/` in `/app` (`COPY pyproject.toml README.md LICENSE NOTICE src /tmp/menkyo/` → `pip install /tmp/menkyo -r web/requirements.txt && rm -rf /tmp/menkyo`); or insert `src` only when `menkyo` is not importable.

[R-4] minor packaging — packaging/homebrew/menkyo.rb:25,41
What: `libexec` has `src/` but no package metadata, so `menkyo --version` prints `menkyo unknown`. And `python -m menkyo` puts the cwd first on `sys.path` (the old `exec python <script>` did not), so a `menkyo/` folder or `numpy.py` in the user's cwd shadows the real one.
Suggested fix: Install the package into the formula's venv (`venv/bin/python -m pip install --no-deps <buildpath>`; deps via the `.pth`), point `bin/menkyo` at `venv/bin/menkyo` and run `gui.py` with that venv's python. At minimum `python -P -m menkyo`.

[R-5] nit contract — README.md ("every line on stdout is one JSON object"), build_diploma.py:773-781
What: `--help`, `--version`, `--example-config` print plain text on stdout even with `--json`.
Suggested fix: Document that these informational flags ignore `--json`.

[R-6] nit docs/structure
- README.md:311 still says `src/border.py`.
- README Layout block (README.md:336-342) omits `paths.py` and `service.py`, which ship in the wheel.
- build_diploma.py:580 `_font_env` docstring still says "adds ../fonts".
- build_diploma.py:16 and :70: edited lines run past the surrounding wrap width.
- src/menkyo/example.toml:34: the reflow left `# turning on: display` as a stub line.

## Round 2

REVIEW: APPROVE

Checked: whole diff vs `d96c08d` again, focused on the fix round. `uv run pytest`: 237 passed, 9 render skips, 2 failures, both only the known xlink golden diffs. Under `--json` with isolated HOME, each of `--json --dpi abc`, `--js --dpi abc`, `--bogus --json`, `--json=1`, `--json --config` (no value), `-n --json`, a malformed TOML, a non-UTF-8 TOML, `-c <directory>` and `--out` under a regular file gave exactly one `error` event, exit 1, empty stderr. `--json -h` and `--json --version` print plain text, exit 0. Built `deploy/Dockerfile`: `/app` holds only `web/`, LICENSE, NOTICE; the web app imports the site-packages copy; not a checkout; a malformed `/data/Menkyo/dojo.toml` gives a 500 on `/api/state` without killing uvicorn. On Inkscape 1.2.2 the inked overlay now has its text. No commits during the run.

R-1 verified fixed. R-2 verified fixed. R-3 verified fixed (in the built image). R-4 verified fixed by reading (Homebrew not run; manual check M-3). R-5 verified fixed. R-6 verified fixed.

[R-7] nit contract — src/menkyo/build_diploma.py:816-819 (pre-parser)
What: The pre-parser knows only `-c`, `--version`, `--example-config`, so it resolves abbreviations against those alone: `menkyo --v` prints the version (the full parser would reject `--v` as ambiguous with `--variants`); `--e` prints the example config. Pre-existing since round 1; the portal passes full names.
Suggested fix: Accept, or `allow_abbrev=False` on the pre-parser.

[R-8] nit docs
- DECISIONS.md, "A checkout behaves as before" bullet: one line runs to ~99 columns.
- src/menkyo/example.toml, [sample] comment: "# given, so that `menkyo` with no arguments produces a" left as a short stub line.

Orchestrator: R-7 accepted as is (pre-existing, harmless for the portal). R-8 fixed by the orchestrator after validation.
