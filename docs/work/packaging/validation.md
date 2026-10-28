# Validation: packaging

## Round 1

2026-10-28, tester. The contract is `acceptance.md` with its `## Agreement`
(added this round: decisions on open questions 1 to 7, F-3 fixed by moving
to `xlink:href`, and the inked `-K` check marked `xfail(strict=True)`).

**VERDICT: PASS**

### Runs

| where | command | result |
|---|---|---|
| Mac (no Inkscape) | `uv run pytest` | **249 passed, 10 skipped** (the 10 are the render tests: 9 in test_ac_render.py, 1 in test_ac_wheel.py) |
| Docker test image (bookworm, Inkscape 1.2.2) | `scripts/test-docker.sh -rA` (REQUIRE_RENDER=1) | **257 passed, 1 skipped, 1 xfailed**. The skip is `test_ac12` gui import ("Tk is not available"), which AC-12 allows. The xfail is `test_ac13_press_inked_k_only` (agreed). Every render test ran. |

Both runs include the developer's `tests/test_packaging_fixes.py` (all
passed) and the tests added this round.

Changes to tests this round (tester-owned):
- `tests/regression/golden/` was refreshed with `make_golden.py --current`,
  after the xlink-only claim was checked (see AC-1).
- `tests/acceptance/test_ac_render.py`:
  - `test_ac13_press_conversions` now holds the hard checks: flat `-K` is
    K-only, `-CMYK` has colour, proof gets no press file.
  - The new `test_ac13_press_inked_k_only` is `xfail(strict=True)`.
  - `test_ac13_inked_svg_carries_its_raster` asserts `xlink:href` and the
    `xmlns:xlink` declaration.
- `tests/acceptance/test_ac_json.py`: new tests
  - `test_ac9_abbreviated_json_is_json` (`--js`, `--jso`)
  - `test_ac9_odd_argv_is_an_error_event` (`--json=1`, `-c` and `--out`
    without a value)
  - `test_ac9_unreadable_config_is_an_error_event` (malformed, not UTF-8, a
    directory)
  - `test_ac9_informational_flags_stay_plain`
  - plus the AC-10 assertion that `--list --json` emits no `done`.
- `tests/acceptance/test_ac_paths.py`: new
  `test_ac4_another_projects_pyproject_is_not_a_checkout`.

### Per AC

- **AC-1 PASS.** `test_output_matches_baseline` (14 cases) and
  `test_list_matches_baseline` (16) pass against the refreshed goldens.
  - **Checking the developer's claim before the refresh:**
    - The two `test_output_matches_baseline` failures (`inked`,
      `supersample`) showed only the `xmlns:xlink` and `xlink:href` lines.
    - A scratch script then ran every golden case against an extracted
      `d96c08d` and against the working tree. Its inkscape wrapper kept a
      copy of every SVG handed to Inkscape, which goes beyond what the
      goldens capture.
    - 34 SVGs differ. In each, undoing exactly one `xmlns:xlink` on the root
      and one `xlink:href=`→`href=` gives the baseline bytes. All 34 are
      inked composites of overlay, full and full-cream: the 9 written by
      `inked`, the 18 handed to Inkscape by `inked`, the 6 handed to it by
      `inked-default`, and 1 written by `supersample`.
    - Everything else is identical to `d96c08d`: all other SVGs, every text
      layer, every Inkscape and Ghostscript call, file sets, stdout and all
      16 `--list` outputs.
  - **The refresh:** the manifest diff is exactly 10 SVG hashes plus
    `source: "working tree"`.
- **AC-2 PASS.** `test_ac2_*` passed in both runs. Manually,
  `uv build --out-dir`:
  - It gave `menkyo-0.1.0-py3-none-any.whl` and `menkyo-0.1.0.tar.gz`.
  - The wheel holds the 8 modules, `example.toml`, `fonts/{METADATA.pb,OFL.txt,YujiBoku-Regular.ttf}`
    and the licences (LICENSE, NOTICE, OFL.txt), and nothing else.
- **AC-3 PASS.** `test_ac3_*` passed, including the render test in Docker.
  Manual check with the wheel in a throwaway Python 3.11 venv, run from an
  unrelated directory that holds a trap `dojo.toml`, with an isolated HOME:
  - `menkyo --version` and `python -m menkyo --version` print
    `menkyo 0.1.0`.
  - `--list` uses the shipped example and ignores the trap.
  - `menkyo.__file__` is in site-packages, and `checkout_root()` is `None`.
  - A `--json` render (`-a dan -v overlay,overlay-flat --press`, stand-in
    tools) gives 6 progress steps, 4 `file` events and a `done`, and writes
    into `~/Documents/Menkyo`.
  - Error cases print one `error` event, exit 1 and leave stderr empty:
    - `-a nope`;
    - `--dpi abc`;
    - `--out` under a regular file (`NotADirectoryError: …`);
    - `FAKE_INKSCAPE_FAIL=pdf` (`inkscape failed.` with `detail`).
- **AC-4 PASS.** `test_ac4_*` passed, including the new foreign-pyproject
  case (Agreement 5). The developer's `test_checkout_needs_this_projects_pyproject`
  passed too.
- **AC-5 PASS.** `test_ac5_*` passed.
- **AC-6 PASS.** `test_ac6_*` passed.
- **AC-7 PASS.** `test_ac7_*` passed. In Docker, the real render emitted 23
  progress steps 1..23, `total` 23 throughout.
- **AC-8 PASS.** All 11 rows of `test_ac8_step_totals` passed.
- **AC-9 PASS.** All `test_ac9_*` passed, including F-1 (bad flags) and F-2
  (unwritable `--out`), both failing in the PLAN run, and the new tests for
  Agreements 1 to 3. The manual attempts to break it also held: each gave
  one `error` event, exit 1 and empty stderr.
  - `--json=1` gives "argument --json: ignored explicit argument '1'".
  - `--js` and `--j` give the error event.
  - `--json -c` and `-c --json` give "argument -c/--config: expected one
    argument".
  - `--out` and `--rank` without a value give the same "expected one
    argument" message.
  - An unknown flag together with `--list` gives "unrecognized arguments".
  - A config that is a directory gives `IsADirectoryError: …`.
  - A non-UTF-8 TOML gives "`<path>: 'utf-8' codec can't decode …`".
  - A config without read permission gives `PermissionError: …`.
- **AC-10 PASS.** `test_ac10_*` passed. `--list --json` emits only `planned`
  events and no `done` (Agreement 4).
- **AC-11 PASS.** `test_ac11_*` passed. Without `--json`, a rejected flag is
  still plain argparse (exit 2, usage on stderr), as
  `test_rejected_flag_without_json_is_plain_argparse` shows.
- **AC-12 PASS.** `test_ac12_*` and tests/regression/test_web.py passed. The
  gui import test ran on the Mac and is skipped in Docker (no Tk).
- **AC-13 PASS** (with the agreed xfail). In Docker, with Inkscape 1.2.2:
  - Every `test_ac13_*` passed, including `test_ac13_text_is_drawn`, which
    failed in the PLAN run (F-3).
  - `test_ac13_press_inked_k_only` xfailed as agreed.
  - **Visual check:** `dan overlay` was rendered as PNG in the image (filled
    name, rank 2, date). The alpha bbox is (610, 363, 4261, 2677), not the
    crest alone. The preview, composited on white, shows:
    - the heading 段位免状;
    - ヤン・ヤンセン殿 and 二段;
    - the formula 右授与ス;
    - the date column 西暦二〇二六年九月五日;
    - the dōjō and teacher columns;
    - the crest.
    The text is clearly drawn.
- **AC-14 PASS.** `test_ac14_*` passed.
- **AC-15 PASS.** `test_ac15_*` passed, and the Docker image built through
  its guard. The new root `.dockerignore` (Agreement 6) excludes
  `dojo.toml`, `**/dojo.toml`, `crest`, `ref`, `build`, `dist`, `.venv`,
  `.git` and `deploy/.env`. Every manual run here pinned `-c` (the shipped
  example) or ran with an isolated HOME and a trap config.
- **AC-16 PASS.** `test_ac16_*` passed.
- **AC-17 PASS.** `test_ac17_*` passed.

Manual checks M-1 (.app) and M-3 (Homebrew): not run (Agreement 7). M-2
(deploy image): the developer reports it built and works; not repeated
here.

### New finding, not in contract

- **N-1 (minor, pre-existing at `d96c08d`): an unreadable configuration
  gives a traceback without `--json`.**
  - **How it shows:** `-c` pointing at a directory, or at a file without
    read permission, raises `IsADirectoryError` or `PermissionError` from
    `config.load` with a full traceback and exit 1.
  - **Compared with malformed or non-UTF-8 TOML:** those now get a clean
    `<path>: …` message.
  - **Under `--json` it is contract-compliant:** one `error` event, but with
    the generic `IsADirectoryError: [Errno 21] …` text.
  - **Suggested fix:** catch `OSError` next to `TOMLDecodeError` and
    `UnicodeDecodeError` in `config.load`.
  - **To reproduce:** `mkdir /private/tmp/claude-501/d && uv run menkyo -c /private/tmp/claude-501/d`.
