# Acceptance: packaging (`menkyo` as a Python package)

Work item: the uncommitted diff on top of `d96c08d`. It turns the generator
into the package `menkyo` (`src/menkyo/`, hatchling, the `menkyo` console
script, the font and `example.toml` as package data) and adds `--version`,
`--example-config` and `--json`. `d96c08d` is the last commit before
packaging, and its behaviour is the baseline. The user asked for regression
tests that cover the existing functionality. The work is committed once
everything is in order and the tests pass.

## Scope

**In**

- The wheel and sdist: what they contain and what they leave out.
- Behaviour from a checkout versus an installed copy: configuration search
  order, default output directory, package resources (font, example), and
  traced crest glyphs looked up beside the configuration.
- `--version` and `--example-config`.
- The `--json` event contract (README, "As a package"): `progress`, `file`,
  `done`, `error`, `planned`, exit codes, and step totals.
- Plain output without `--json`: unchanged stdout, progress on stderr only
  when stderr is a terminal.
- `src/gui.py` and `web/app.py` importing from the package, and the web
  endpoints still working.
- **Regression:** everything the generator did at `d96c08d` still does the
  same thing (SVG output, `--list`, Inkscape and Ghostscript calls, config
  handling, `service`).
- Test infrastructure: the pytest config and dev group, the Docker test
  image, and the pytest step in `.github/workflows/package.yml`.

**Out** (not tested here; manual if at all)

- The macOS app (`packaging/build_app.sh`, `menkyo.spec`), the Homebrew
  formula and the deploy image (`deploy/`). They changed in this diff, but
  building them needs PyInstaller or a Mac signing setup or a VPS. See the
  manual checks M-1 to M-3.
- How the certificates look. Nothing in this item changes what is drawn,
  which AC-1 proves at the SVG level. Visual review is not repeated.
- The Tk window's behaviour beyond importing.

## Acceptance criteria

**AC-1: Existing output is unchanged.** For every case in
`tests/regression/golden_cases.py`, run with the stand-in inkscape and gs,
the current code produces the same results as `d96c08d`: byte-identical
SVGs, the same text layer handed to Inkscape, the same Inkscape and
Ghostscript calls (paths normalised), the same set of files, the same
stdout, and the same `--list` output. The cases cover all 3 example awards ×
6 variants, filled and blank name/rank/date, `--honorific ''`, a rank on a
licence, long-name shrinking, the `[sample]` fallback and its gating on
`grade_column`, two test configurations (`text_drop` 0 and 0.12, an empty
crest ring and motto, a 5-character ring, a different honorific),
`--press`, `--supersample`, `--dpi`, and the suffix rules.

**AC-2: Wheel contents.** `uv build` produces
`menkyo-<version>-py3-none-any.whl` and `menkyo-<version>.tar.gz`, where
`<version>` comes from `pyproject.toml`.
- The wheel holds `menkyo/{__init__,__main__,border,build_diploma,config,ink,paths,service}.py`,
  `menkyo/example.toml` (identical to the source),
  `menkyo/fonts/YujiBoku-Regular.ttf` and `menkyo/fonts/OFL.txt`.
- Its metadata declares the version, `Requires-Python >=3.11`, pillow, numpy
  and scipy, the console script `menkyo = menkyo.build_diploma:cli`, and the
  licence files LICENSE, NOTICE and OFL.txt.
- It holds nothing else: no `gui.py`, `web/`, `packaging/`, `deploy/`,
  `tests/`, `dojo.toml`, `crest/`, `ref/`, `build/`, `__pycache__` or
  `.pyc`.
- The sdist holds no `dojo.toml`, `crest/`, `ref/`, `build/`, `dist/` or
  `.venv`.

**AC-3: The installed wheel works outside the checkout.** Installed into a
fresh virtualenv and run from an unrelated directory:
- `menkyo --version` and `python -m menkyo --version` print
  `menkyo <version>`.
- `--example-config` prints the shipped example.
- `--list` uses the shipped example even when a `dojo.toml` sits in the
  current directory.
- A run without `--out` writes to `~/Documents/Menkyo` and emits a
  `done` event.
- Inkscape is given a fontconfig whose first font directory is the installed
  `menkyo/fonts`, which holds Yuji Boku.
- With real Inkscape (marked `render`), the flat PDF embeds Yuji Boku. This
  mirrors the release smoke test.

**AC-4: Checkout versus installed paths.**
- *Checkout* (a `pyproject.toml` two levels above the package):
  - `checkout_root()` is the repository root.
  - The default output is `<root>/build`.
  - `LOCAL_CONFIG` is `<root>/dojo.toml`.
  - The configuration search order is the per-user `dojo.toml`, then
    `<root>/dojo.toml`, then the shipped example.
- *Installed* (no `pyproject.toml` there):
  - `checkout_root()` and `LOCAL_CONFIG` are `None`.
  - The default output is `~/Documents/Menkyo`.
  - The search order is the per-user `dojo.toml`, then the shipped example.
  - A `dojo.toml` beside the package, above it, in the cwd or in HOME is
    never read.
- In both, the fonts and the example resolve inside the package.

**AC-5: `--version`.** Prints `menkyo <version>` with the version from
`pyproject.toml` in a checkout (and from the metadata when installed, see
AC-3), exits 0, writes nothing to stderr, and works with a missing or broken
`-c`.

**AC-6: `--example-config`.** Prints `src/menkyo/example.toml` byte for
byte and exits 0, including with a missing or broken `-c`. Its output,
saved as a file, loads as a configuration equal to the shipped example.

**AC-7: `--json` on success.**
- Every stdout line is a JSON object with an `event` key.
- `progress` events have exactly `step`, `total`, `award`, `variant`,
  `stage` and `label`. `step` runs 1..N with no gaps, `total` is N on every
  event, `stage` is one of `text`/`ink`/`pdf`/`press`/`png`, and
  `label == "<award> <variant>: <English stage>"`.
- Stages for a variant come in the order text, ink, pdf, press, png.
- A `file` event (exactly `path`) follows for each file written, in write
  order, before the next variant's progress.
- The last line is exactly one `done` with `out` (absolute) and `files`
  (equal to the `file` paths).
- The exit code is 0, and stderr is empty when it is not a terminal.
- `main(argv, progress=callback)` receives the same dicts.

**AC-8: Step totals are right from the first event.** `total` equals the
number of slow steps actually run, for:

| flags | total | files |
|---|---|---|
| `-a dan -v overlay -f pdf` (inked) | 3 | 1 |
| `-a dan -v overlay-flat -f pdf` (flat) | 1 | 1 |
| `-a dan -v overlay --no-ink -f pdf,png` | 2 | 2 |
| `-a dan -v overlay,full --press` | 8 | 4 |
| `-a dan -v proof --press -f pdf,png` (proof gets no press step) | 2 | 2 |
| `-a dan,shihan -v overlay,proof -f pdf,png,svg` (svg is not a step) | 12 | 14 |
| `-a dan -v overlay-flat -f svg` (no progress events at all) | 0 | 1 |
| `-a dan -v full-cream -f svg` | 2 | 2 |
| `--all --press -f pdf,png` | 69 | 51 |
| `--all --no-ink --press` | 33 | 33 |
| defaults (overlay, full-cream; pdf; 3 awards) | 18 | 6 |

**AC-9: `--json` on failure.** Every failure produces exactly one `error`
event with a `message`, as the last stdout line, with no `done`. The
process exits 1, with no traceback. This covers:
- an unknown award, variant or format;
- `--rank 11`, a bad `--date`, `--supersample 5`;
- a missing configuration, or one with the wrong schema;
- Inkscape missing, and Ghostscript missing with `--press`;
- Inkscape failing (query, png or pdf), where the message is
  `inkscape failed.` and `detail` holds the tail of its stderr;
- Ghostscript failing (`gs failed.` plus `detail`);
- **a flag argparse rejects** (`--dpi abc`, an unknown flag);
- **an OS error such as an unusable `--out`.**

**AC-10: `--list --json`.**
- One `planned` event (exactly `file`) per file, with the same names in
  the same order as plain `--list` (`-K`/`-CMYK` tags with `--press`, none
  for proof).
- Nothing is written, stderr is empty, and the exit code is 0.

**AC-11: Plain output is unchanged.**
- Without `--json`, stdout is the baseline's: `wrote <path>` per file, then
  a blank line and `N file(s) in <out>/`.
- When stderr is not a terminal it stays empty. When it is a terminal it
  gets `[i/N] <award> <variant>: <stage>` lines.
- `.work/` and `.fontconfig/` are removed after a run, and `--clean`
  empties the output first.
- A user error prints its message on stderr, leaves stdout empty and exits
  1. A missing Inkscape does the same with the install hint.

**AC-12: The front ends build on the package.**
- `web/app.py` imports the way uvicorn runs it, uses
  `menkyo.service.make_argv`/`run_build`, and serves `/`, `/api/state`,
  `/api/settings` and `/api/generate`. Settings save to the per-user file;
  generate returns a PDF, or a zip of several, a 400 for form errors and a
  500 for a failing tool.
- `src/gui.py` imports the way `python src/gui.py` runs it (skipped without
  Tk).
- No module still imports the old top-level `config`/`paths`/`service`/...

**AC-13: Real renders** (marker `render`, which must run with
REQUIRE_RENDER=1). `-a dan -v all -f pdf,png --press` with a filled name,
rank and date gives:
- 17 files and 23 progress steps;
- PDFs that are 1 page of A3 landscape (1190.55 × 841.89 pt);
- PNGs of 4961 × 3508 px at 300 dpi;
- a transparent overlay PNG, a cream (#f7f1e3) full-cream PNG and an opaque
  proof PNG;
- ink in the heading column of every variant;
- Yuji Boku embedded in the flat and proof PDFs;
- `-K` files with zero CMY ink coverage and `-CMYK` files with some, and no
  press file for proof.

An inked `-f svg` carries its text-layer PNG alongside.

**AC-14: The release runs the suite.** In
`.github/workflows/package.yml`, the `build` job:
- runs `uv run --frozen pytest` with `REQUIRE_RENDER=1` after installing
  Inkscape, Ghostscript and poppler;
- keeps the existing wheel smoke test;
- runs both before uploading the artifact.

`release` still `needs: build`.

**AC-15: Personal data stays out.**
- Tests never read the repository-root or per-user `dojo.toml`. An autouse
  fixture repoints `USER_CONFIG`, `LOCAL_CONFIG` and `save()`'s default, and
  HOME/XDG_CONFIG_HOME are moved before menkyo is imported. Subprocesses
  get an isolated HOME and always pass `-c`.
- Goldens hold placeholder data only.
- The Docker test image's build context excludes `dojo.toml`, `crest/`,
  `ref/`, `build/`, `dist/` and `.venv`, and its build fails if any of them
  got in.

**AC-16: Traced crest glyphs come from `crest/` beside the configuration
file** (a deliberate change from the baseline's repository-root `crest/`).
With `traced_glyphs = true`, a glyph that has an SVG there is drawn from it,
and a glyph without one falls back to the font. With it off, the font is
always used.

**AC-17: `menkyo` and `python -m menkyo` agree,** and `--help` exits 0 as
`usage: menkyo …` and lists the new flags.

## Test approach

| AC | automated | file |
|---|---|---|
| 1 | `test_output_matches_baseline[*]` (14 cases), `test_list_matches_baseline[*]` (16), `test_manifest_covers_every_case`, `test_goldens_hold_placeholder_data_only` | tests/regression/test_golden.py |
| 1 (support) | rank, date, suffix, fallback, csv, layout constants, document layers | tests/regression/test_pure.py |
| 1 (support) | config load, validation, search order, save→load | tests/regression/test_config.py |
| 1 (support) | `make_argv` (every slot, `--flag=value`, FormErrors), `run_build` | tests/regression/test_service.py |
| 2 | `test_ac2_*` | tests/acceptance/test_ac_wheel.py (`slow`) |
| 3 | `test_ac3_*`, the last also `render` | tests/acceptance/test_ac_wheel.py (`slow`) |
| 4 | `test_ac4_*` | tests/acceptance/test_ac_paths.py |
| 5, 6, 11, 17 | `test_ac5_*`, `test_ac6_*`, `test_ac11_*`, `test_ac17_*` | tests/acceptance/test_ac_cli.py |
| 7–10 | `test_ac7_*` … `test_ac10_*` | tests/acceptance/test_ac_json.py |
| 12 | `test_ac12_*`; endpoints in tests/regression/test_web.py | tests/acceptance/test_ac_frontends.py |
| 13 | `test_ac13_*` (`render`) | tests/acceptance/test_ac_render.py |
| 14, 15 | `test_ac14_*`, `test_ac15_*`, plus the guard `RUN` in tests/docker/Dockerfile | tests/acceptance/test_ac_release.py |
| 16 | `test_ac16_*` | tests/acceptance/test_ac_paths.py |

Runs:

- `uv run pytest`: everything; `render` tests skip without Inkscape.
- `scripts/test-docker.sh`: the same in the Docker test image (Debian
  bookworm with Inkscape, Ghostscript, poppler and Noto CJK) with
  `REQUIRE_RENDER=1`, so a render test that would skip fails instead.

Manual checks (out of the automated scope):

- **M-1:** `packaging/build_app.sh` builds `dist/Menkyo.app`. Opening it
  and making one certificate with `-c`-equivalent example settings puts a
  PDF in `~/Documents/Menkyo`.
- **M-2:** `docker compose -f deploy/docker-compose.yml build` succeeds, and
  the container serves `/api/state`.
- **M-3:** The Homebrew formula installs, and `menkyo --version` works.

## Open questions

1. **Failures that never reach `cli()`'s handlers (AC-9).** argparse errors
   (`--dpi abc`, an unknown flag) exit **2** with usage on stderr and no
   `error` event. OS errors (an `--out` under a regular file, permission
   denied, disk full) end in a traceback and exit 1, again with no `error`
   event. The README promises an `error` event with exit code 1 when "the
   run failed". AC-9 holds the current code to that promise, and those three
   tests fail today. Is that the contract, or should the README narrow it?
   The tester recommends the event: the portal reads only stdout.
2. **`--js` and other abbreviations.** argparse accepts `--js` as `--json`,
   but `cli()` tests for the literal `"--json"`. With `--js`, the output is
   JSON but a failure is not wrapped into an `error` event. Should the
   parser set `allow_abbrev=False`, or should `cli()` check the parsed flag?
3. **`--version` and `--example-config` with `--json`** print plain text.
   They are informational, so this seems fine, but "every line on stdout is
   one JSON object" says otherwise. Not tested either way.
4. **`--list --json` ends without a `done` event.** The README does not say
   whether it should. Not tested either way.
5. **What counts as a checkout.** `checkout_root()` accepts any
   `pyproject.toml` two levels above the package, whatever project it
   belongs to. A consumer that vendors the package with
   `pip install --target <project>/vendor` would be treated as a checkout:
   it would read `<project>/dojo.toml` and write to `<project>/build`.
   `_version()` checks `name == "menkyo"`; should `checkout_root()` check it
   too?
6. **A root `.dockerignore`.** The test image uses
   `tests/docker/Dockerfile.dockerignore`, so the deploy build is untouched.
   `deploy/docker-compose.yml` builds from the repository root and still
   sends `dojo.toml`, `crest/` and `ref/` to the Docker daemon in its
   context, although its Dockerfile never copies them. Should a root
   `.dockerignore` exclude them for every build?

## Findings from the PLAN run (tests failing against the current code)

- **F-1: argparse errors under `--json` exit 2 and emit no `error` event
  (AC-9).** `test_ac9_bad_flags_are_error_events[bad-flag-value]` and
  `[unknown-flag]` fail. To reproduce:
  `uv run menkyo -c src/menkyo/example.toml --json --dpi abc` prints usage on
  stderr, nothing on stdout, and exits 2.
- **F-2: OS errors under `--json` end in a traceback with no `error` event
  (AC-9).** `test_ac9_unwritable_out_is_an_error_event` fails. To reproduce:
  `touch /tmp/f; uv run menkyo -c src/menkyo/example.toml -a dan -v overlay-flat -d '' --out /tmp/f/sub --json`
  raises `NotADirectoryError` from `os.makedirs`, prints a traceback and
  exits 1.
- **F-3: On Inkscape 1.2 the inked variants render without any text
  (AC-13).** `test_ac13_text_is_drawn` fails in the Docker test image
  (Debian bookworm, Inkscape 1.2.2).
  - **Cause:** the inked composite places its text raster with
    `<image href="…-textlayer.png">`, an SVG 2 plain `href`, and
    Inkscape 1.2 only honours `xlink:href`. Rewriting the same file to
    `xlink:href` (with `xmlns:xlink`) makes the text appear.
  - **Not a regression:** `d96c08d` produces byte-identical SVGs and
    PNGs.
  - **Why it matters now:**
    - `overlay` and `full-cream` (the defaults, and every web or portal
      certificate) print with no text wherever Inkscape is 1.2: the
      `deploy/` image (`python:3.13-slim-bookworm`), Ubuntu 24.04 (the
      release runner), and probably the portal's image.
    - The release workflow's smoke test checks fonts only on the flat
      variant, so it never noticed.
    - The new pytest step (REQUIRE_RENDER=1) will fail on ubuntu-24.04
      until this is fixed.
  - **To reproduce:** `scripts/test-docker.sh -k text_is_drawn`. Or
    render `-a dan -v overlay -f png` in the image: the PNG's alpha bbox
    covers only the crest.
  - **The fix changes the SVG output, which is a decision for the user.**
    Writing `xlink:href` would change every inked SVG, so the goldens would
    be refreshed with `make_golden.py --current`. The alternative is to
    require Inkscape 1.3 or later, which bookworm and Ubuntu 24.04 do not
    package.

## Agreement

Decided by the orchestrator after the PLAN run (VALIDATE round 1,
2026-10-28). Where the contract changed, the tests changed with it.

1. **Any failure under `--json`** (open question 1) ends in exactly one
   `error` event as the last stdout line, exit 1, no traceback: user
   errors, rejected flags (argparse), a config that cannot be read
   (malformed TOML, not UTF-8, a directory), OS errors and unexpected
   exceptions (`"<ExceptionType>: <message>"`). Tests:
   `test_ac9_bad_flags_are_error_events`,
   `test_ac9_unwritable_out_is_an_error_event`,
   `test_ac9_odd_argv_is_an_error_event` (`--json=1`, `-c` and `--out`
   without a value), `test_ac9_unreadable_config_is_an_error_event`.
2. **Abbreviations** (open question 2): JSON mode is decided the way
   argparse parses the flags, so `--js` counts; `allow_abbrev` stays on.
   Test: `test_ac9_abbreviated_json_is_json`.
3. **`--help`, `--version`, `--example-config`** (open question 3) print
   plain text and exit 0 even with `--json`; this is documented in the
   README. Test: `test_ac9_informational_flags_stay_plain`.
4. **`--list --json`** (open question 4) emits `planned` events only, no
   `done`; documented. `test_ac10_list_json_matches_plain_list` asserts it.
5. **What counts as a checkout** (open question 5): `checkout_root()`
   requires a `pyproject.toml` two levels up whose `[project].name` is
   `menkyo`. Test: `test_ac4_another_projects_pyproject_is_not_a_checkout`
   (a copy vendored under a `dojo-portal` pyproject behaves as installed and
   never reads that project's `dojo.toml`).
6. **A root `.dockerignore`** (open question 6) keeps `dojo.toml`, `crest/`,
   `ref/`, `build/`, `dist/`, `.venv` and `.git` out of the deploy build
   context.
7. **The .app, Homebrew and deploy image builds** (open question 7, M-1 to
   M-3) stay manual checks. The developer built the deploy image and checked
   it: menkyo is the installed copy in site-packages, not a checkout;
   `--version` and a `--json` render work.

**F-3 is fixed by changing the SVG; AC-1's baseline moves with it.** The
inked composite now places its text raster with `xlink:href`, and the root
`<svg>` declares `xmlns:xlink` only when `layer == "chrome"` (the base of an
inked composite). Inkscape 1.2 (Debian bookworm, Ubuntu 24.04) ignores a
plain `href`, so the inked variants printed without text there.
- The tester checked that these are the only changes: every golden case was
  run against an extracted `d96c08d` and the working tree, with an inkscape
  wrapper that also kept every SVG handed to Inkscape. In 34 SVGs, undoing
  exactly the two edits (drop the one `xmlns:xlink` declaration, turn the
  one `xlink:href=` back into `href=`) gives the baseline bytes. These are
  the inked composites of `overlay`, `full` and `full-cream`: the written
  `-f svg` files and the ones handed to Inkscape for pdf/png. Every other
  SVG, every text layer, every Inkscape and Ghostscript call, the file sets,
  stdout and all `--list` outputs are identical to `d96c08d`.
- The goldens were refreshed with `make_golden.py --current`, so
  `manifest.json` now says `"source": "working tree"`. Ten written-SVG
  hashes changed: the nine inked `out/*.svg` of the `inked` case and
  `dan-overlay-sample.svg` of `supersample`. Nothing else changed. AC-1 now
  reads: identical to `d96c08d` except for the xlink change.
- `test_ac13_inked_svg_carries_its_raster` now asserts `xlink:href` and the
  namespace declaration.

**Inked `-K` press files are not K-only: known, deferred.** Cairo's RGB
transparency group survives Ghostscript's `/Gray` conversion, so the inked
`-K` files carry some C/M/Y. This has been so since `--press` existed (also
with Inkscape 1.3+); it passed before only because Inkscape 1.2 drew no
text. It is now in DECISIONS.md, `## Open` ("The `-K` press files of the
inked variants are not K-only"). AC-13's press check is split:
- `test_ac13_press_conversions` keeps hard asserts: the flat `-K` is K-only,
  `-CMYK` has colour, and proof gets no press file.
- `test_ac13_press_inked_k_only` checks the inked `-K` and is
  `xfail(strict=True)` with a reason pointing at the Open item, so fixing it
  turns the run red until the mark is removed.
