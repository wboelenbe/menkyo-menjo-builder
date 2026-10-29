# plain-white: acceptance

Planned at `823af58` (clean tree). Tester: PLAN mode, revised once after the
user's decisions and the developer's review (see "Agreement" at the end).

## The decision being built

The user, in their words: "drop the coloured variants with fancy
backgrounds, stick to the plain white diploma." The orchestrator's reading,
recorded in DECISIONS.md `## Open` ("Plain white only"):

- drop the variants `full`, `full-cream` and `full-flat`, the drawn border
  (`border.py`), the per-award `colour`, the paper tint, and `--press` (the
  `-K` / `-CMYK` files and every use of Ghostscript);
- keep `overlay` (inked), `overlay-flat` and `proof`, printed on plain white
  paper;
- the Open item "The `-K` press files of the inked variants are not K-only"
  retires with `--press`.

This item comes before `no-inkscape` (docs/work/no-inkscape/spike.md, risk 2
and Q-7) and exists to make that build smaller. It does none of that build:
Inkscape stays, and so do the fakes for it.

## Scope

**In**

- `src/menkyo/border.py` deleted, and everything in `build_diploma.py` that
  only served it or the tint: `SEPIA`, `CREAM`, `CREST_C_BORDERED`, the
  `drawn_border`, `paper` and `border_colour` parameters, the three coloured
  entries of `VARIANTS`.
- `--press` deleted: the flag, the `press` progress stage, the `-K.pdf` and
  `-CMYK.pdf` files, the Ghostscript call in `render()` (and its `press` and
  `convert` parameters), `"gs"` in `paths._INSTALL_HINT`, the `--list` lines
  for press files.
- The default variants become `overlay` alone (open question 1, decided).
- Plain white paper only: the bought-stock (賞状用紙) route ends in code
  comments, `--help`, README, `example.toml` and the DECISIONS Open list
  (open question 4, decided).
- The version goes to `0.2.0` (open question 6, decided).
- `Award.colour` removed. A `colour` key in `[[awards]]` is accepted and
  ignored (open question 2); `config.save()` no longer writes one;
  `example.toml` no longer has one.
- `--help` text: the `-v` list and default, the epilog (no `--press`
  examples, no "full-cream reference", no bought stock), the module
  docstring.
- Documentation: README (quick start requirements, "As a package" install
  line and stage list, the config example, `colour` paragraph, Options,
  Variants, the two "Printing" sections become one for plain white A3, "How
  it looks", Layout), `docs/three_up.png` (it shows the `full-cream` sheets
  today), CLAUDE.md ("Ghostscript converts for `--press`"), `pyproject.toml`
  (version, the system-programs comment and the `render` marker
  description), a new DECISIONS entry, and the DECISIONS `## Open` list.
- CI and the test image: `.github/workflows/package.yml` and
  `tests/docker/Dockerfile` stop installing Ghostscript; the workflow's smoke
  test drops `--press`; `scripts/test-docker.sh`'s comment follows.
- Tests (tester's part, done in the PLAN rounds, see "Test changes"): the
  goldens, the press tests and the xfail, the full-variant render tests, the
  `gs` fake.

**Out**

- Anything of `no-inkscape`: Inkscape, `_font_env()`, `paths.require_tool`,
  `tool_env`, `system_font_dirs`, `_EXTRA_BIN`, `--supersample`'s wording,
  the `inkscape` fake. They stay exactly as they are.
- What is drawn on the three remaining variants: layout, crest, ink, proof
  guides. Their output is byte-identical (AC-8).
- The overlay PNG's transparent background (open question 8): unchanged.
- `[paper] border` and `safe_inset` in code: they stay, with the same
  defaults, and keep drawing the proof's guides (AC-11). The internal
  attribute `Config.stock_border` keeps its name. Only their documentation
  changes (open question 3).
- `src/menkyo/ink.py`: untouched. Its stale "composited back under the
  vector border" docstring line belongs to the `ink-memory` item.
- The annotated Dutch companion sheet in the default output: the separate
  future item `annotated-nl` (DECISIONS `## Open`).
- Deprecation shims: no alias, warning or "this was removed" message for
  `full*` or `--press` (open question 5).
- Earlier DECISIONS entries: untouched (open question 7).
- `.claude/` (agent configuration; `developer.md` and `tester.md` mention
  Ghostscript). The orchestrator updates it; excluded from the AC-14 scan
  (open question 9).
- dojo-portal. Not built yet; see "Portal impact".
- A4, kyū grades, and the other Open items.

## Acceptance criteria

All CLI runs pin `-c src/menkyo/example.toml` or a config the test writes,
with `HOME` / `XDG_CONFIG_HOME` isolated (conftest.py, support.isolated_env).

- **AC-1 Three variants.** `VARIANTS` is exactly `overlay`, `overlay-flat`,
  `proof`, in that order; only `overlay` is inked. `-v all` (any case,
  spaces allowed, also `--variants=all`) selects exactly those three, in
  that order; `--all` selects them for every award (it overrides `-a`, as
  it always has). `--all` writes byte-for-byte what
  `-a dan,shihan,renshi -v overlay,overlay-flat,proof` writes.
- **AC-2 Removed variants are rejected.** `-v full`, `-v full-cream`,
  `-v full-flat`, and lists that contain one (`overlay,full`,
  `proof,full-cream,full-flat`): exit 1, stdout empty, stderr
  `unknown variant: <the bad ones, comma-separated>` followed by
  `choose from: overlay, overlay-flat, proof (or 'all')`, no traceback, no
  output directory created, Inkscape never called. With `--json`: exactly
  one event, `error`, with that message, exit 1, nothing on stderr.
- **AC-3 `--press` is rejected.** `--press` and its former abbreviations
  `--pre`, `--pr` are unknown flags: exit 2 with argparse's usage and
  `unrecognized arguments: --press` on stderr, stdout empty, nothing written,
  Inkscape never called; with `--list` too. With `--json`: exactly one
  `error` event containing `unrecognized arguments: --press`, exit 1,
  nothing on stderr.
- **AC-4 Default variants: `overlay`** (open question 1, decided by the
  user). `DEFAULT_VARIANTS == ["overlay"]`, formats still `["pdf"]`.
  `menkyo --list` with the example lists `dan-overlay-sample.pdf`,
  `shihan-overlay-sample.pdf`, `renshi-overlay-sample.pdf` and nothing else.
  A default `--json` run reports 9 progress steps (text, ink, pdf per award)
  and those 3 files.
- **AC-5 No Ghostscript.** `--all -f pdf,png,svg` with only a (stand-in)
  Inkscape on PATH succeeds, calls nothing but `inkscape`, and writes exactly
  the 3 × 3 × 3 files plus the three overlay `-textlayer.png`; no file ends
  in `-K.pdf` or `-CMYK.pdf`. `paths._INSTALL_HINT` names only `inkscape`.
- **AC-6 `--json` stages and totals.** `STAGES` is exactly `text`, `ink`,
  `pdf`, `png` (labels unchanged). Totals: `--all -f pdf,png` 24 steps / 18
  files; `--all --no-ink` 9 / 9; `--all -f pdf,png,svg` 24 / 30;
  `-a dan -v all -f svg` 2 / 4; `-a renshi -v all --no-ink -f png` 3 / 3.
  `step` runs 1..total, `total` constant, `done.files` equals the `file`
  events. Event shapes are unchanged (packaging AC-7..AC-10 still pass).
- **AC-7 `--list`.** `--list --all -f pdf,png,svg` prints exactly 27 names,
  award → variant → format, no press names. `--list --json` gives the same
  names as `planned` events.
- **AC-8 What remains is unchanged.** For overlay, overlay-flat and proof:
  every SVG (inked composite, flat, proof, text layer handed to Inkscape),
  every Inkscape call, the files written and stdout are identical to
  `823af58`, across the 14 render cases and 16 `--list` cases in
  `tests/regression/golden_cases.py` (example, `minimal.toml`, and
  `dropped.toml`, which still carries a `colour` per award).
- **AC-9 `colour` is accepted and ignored** (open question 2, agreed). A
  config with `colour = "#8a6a33"`, `"#ff0000"`, `"not a colour"`, `""` or
  `5` in every `[[awards]]` loads to the same `Config` as without it and
  writes byte-identical output for `--all`; no warning on stderr or in the
  events. `Award` has exactly the fields `slug`, `heading`, `formula`,
  `grade_column`. `config.save()` writes no `colour`, and its file loads
  back to the same awards.
- **AC-10 The example configuration.** `example.toml` (and so
  `--example-config`) has no `colour` key and no mention of colour, `full`,
  cream, tint or the drawn border; `--example-config` still prints the file
  byte for byte and it still loads (three awards; `border` 22.0,
  `safe_inset` 38.0, `text_drop` 0.05).
- **AC-11 `[paper] border` and `safe_inset` stay.** Both keys load as before
  and still place the proof's two guide rectangles (a config with 10 / 20
  draws them at 10 mm and 20 mm). The attribute `Config.stock_border` keeps
  its name. README and `example.toml` describe them as margins on plain
  white paper: `border` the margin kept clear all round, `safe_inset` where
  text may begin (open question 3; manual check M-5).
- **AC-12 `--help`.** Shows `comma-separated: overlay,overlay-flat,proof
  (default: overlay)` (unwrapped), and none of `--press`, `full-cream`,
  `full-flat`, `-v full`, `CMYK`, `-K`, `printer`, `cream`, `border`,
  `stock`, `bought`. Every other flag is still listed.
- **AC-13 The code is gone.** No `src/menkyo/border.py`; `menkyo.border`
  cannot be imported and `build_diploma` has no `border` attribute; no
  `SEPIA`, `CREAM`, `CREST_C_BORDERED`; `document`, `build_one` and `render`
  take none of `drawn_border`, `paper`, `border_colour`, `press`, `convert`;
  every `VARIANTS` entry uses only `inked` / `guides`. The built wheel has no
  `menkyo/border.py`.
- **AC-14 No references left.** Outside DECISIONS.md, `docs/work/`,
  `.claude/` and the test file that lists them, no tracked or untracked
  (non-ignored) text file mentions the removed things: `full-cream`,
  `full-flat`, `-v full`, `--press`, the `press` stage, `CMYK`, `-K.pdf`,
  Ghostscript / `gs`, `border.py`, the drawn or engraved border, the border
  colour, `SEPIA`, cream, the paper tint, the three hex colours, `K-only`,
  `inkcov`, `賞状用紙`, `bought` (so also "bought stock"), and a bare word
  `gs` anywhere. `賞状` on its own stays allowed. In `src/menkyo/*.py`
  additionally no `colour` attribute, key or assignment.
- **AC-15 README.** The Variants table lists exactly `overlay`,
  `overlay-flat`, `proof`; the Options row for `-v` says
  `(default: \`overlay\`)`; there is no `--press` row; the config example has
  no `colour` and still shows `[paper] border` / `safe_inset`; the `stage`
  sentence lists `text`, `ink`, `pdf`, `png`; Quick start names Inkscape
  (and no Ghostscript); no "Printing" heading names a border or stock, and
  a Printing section speaks of white paper.
- **AC-16 DECISIONS.** Everything before `## Open` at `823af58` is an
  unchanged prefix of the file. Among the entries after it there is exactly
  one dated entry (`## YYYY-MM-DD — …`) whose heading mentions "white",
  found by its heading; it need not be the only or the last new entry
  (`ink-memory` may add its own). It mentions `--press`, Ghostscript,
  overlay, proof, `colour` and the portal. In `## Open` the items "Source
  the 賞状用紙", "Plain white only", "The `-K` press files …" and "Test the
  drawn border on the actual printer" are gone; "Render without Inkscape"
  and "An annotated version in Dutch" stay.
- **AC-17 CLAUDE.md, pyproject.toml, tests/README.md.** CLAUDE.md still says
  Inkscape renders and no longer mentions Ghostscript or `--press`; the
  pyproject comment on system programs names Inkscape only; the `render`
  marker's description names Inkscape and not Ghostscript;
  `tests/README.md` describes the `823af58` baseline (done by the tester).
- **AC-18 CI and the test image.** `tests/docker/Dockerfile` and the
  workflow install `inkscape poppler-utils fontconfig fonts-noto-cjk` and
  not `ghostscript`; the image keeps `REQUIRE_RENDER=1`; the workflow's
  smoke test renders `-v overlay,overlay-flat` without `--press` and still
  checks `pdffonts … | grep -qi yuji`. `scripts/test-docker.sh` passes with
  the render tests running, not skipping (M-1).
- **AC-19 Real renders.** In the Docker image: `-a dan -v
  overlay,overlay-flat,proof -f pdf,png` writes those 6 files in 8 steps
  (stages `text`, `ink`, `pdf`, `png` only); every PDF is one A3 landscape
  page; every PNG is 4961 × 3508 at 300 dpi; the heading column carries ink
  in every PNG and PDF; overlay and overlay-flat PNGs are transparent; the
  flat and proof PDFs embed Yuji Boku; overlay and overlay-flat have no
  coloured pixel (chroma ≤ 12 in the PNG and in the PDF at 50 dpi); the
  inked SVG still places its raster with `xlink:href`.
- **AC-20 Installed wheel.** From a throwaway venv outside the checkout:
  no `border.py` in site-packages; `--list --all` gives 9 names, `--list`
  gives the 3 overlays; `-a dan -v full --json` is one `error` event
  (`unknown variant: full …`), exit 1; `--press` exits 2 with
  `unrecognized arguments: --press`; `--help` shows the new `-v` line.
  Packaging AC-3 (installed run, defaults to `~/Documents/Menkyo`, render
  embeds Yuji Boku) still passes without `--press`.
- **AC-21 The README image.** `docs/three_up.png` is the default `overlay`
  PNGs of the three awards, rendered with `-c src/menkyo/example.toml` and
  nothing else (personal-data rule), flattened onto white and set side by
  side at 1890 × 455, as now. Each sheet has a 1 px light-grey outline and
  at least 4 px of white around it. Tested: exactly 1890 × 455; the outer
  4 px of the image are white (every channel ≥ 245, so the corners are);
  fewer than 0.1 % of pixels have chroma > 24 (no sepia or purple border,
  no cream); black text; at least 6 horizontal light-grey runs ≥ 300 px and
  6 vertical ones ≥ 200 px (three outlined sheets). The composition script
  is not committed.
- **AC-22 Nothing else changes.** The rest of the suite passes unchanged in
  meaning: rank / date / name / suffix handling, `--version`,
  `--example-config`, the per-user and checkout config search, `--clean`,
  `--out`, every other `--json` error path (Inkscape missing or failing,
  bad TOML, unwritable `--out`, odd argv), the plain-output contract, and
  the cli-only and packaging criteria not listed under "Contract changes to
  earlier items".
- **AC-23 Version 0.2.0.** `pyproject.toml` has `version = "0.2.0"`;
  `menkyo --version` prints `menkyo 0.2.0`, from the checkout and from the
  installed wheel; `uv build --wheel` writes
  `menkyo-0.2.0-py3-none-any.whl`.

## Test approach per AC

`tests/acceptance/test_ac_plain_white.py` is this item's file (`test_ac<N>_…`).

| AC | automated | manual |
|---|---|---|
| AC-1 | `test_ac1_the_variants_are_the_plain_three`, `test_ac1_all_means_the_plain_three[…]`, `test_ac1_all_flag_lists_every_award_and_variant`, `test_ac1_all_writes_what_the_explicit_list_writes` | |
| AC-2 | `test_ac2_removed_variants_are_rejected[…]`, `test_ac2_removed_variants_are_json_errors[…]` | |
| AC-3 | `test_ac3_press_is_rejected[--press/--pre/--pr]`, `test_ac3_press_is_a_json_error[…]`, `test_ac3_press_is_rejected_by_list_too` | |
| AC-4 | `test_ac4_default_variants`, `test_ac4_default_list`, `test_ac4_default_run` | |
| AC-5 | `test_ac5_a_full_run_needs_only_inkscape`, `test_ac5_ghostscript_is_not_a_known_tool` | |
| AC-6 | `test_ac6_stages`, `test_ac6_step_totals[…]`; packaging `test_ac_json.py` AC-7..AC-10 | |
| AC-7 | `test_ac7_list_every_format`, `test_ac7_list_json_is_the_same`; `test_ac_json.py::test_ac10_*` | |
| AC-8 | `tests/regression/test_golden.py` (goldens regenerated from `823af58`) | |
| AC-9 | `test_ac9_colour_is_accepted_and_ignored[…]`, `test_ac9_colour_draws_no_warning`, `test_ac9_an_award_has_no_colour`, `test_ac9_save_writes_no_colour`; golden cases `dropped-config*` | |
| AC-10 | `test_ac10_example_config_has_no_colours`, `test_ac10_example_config_still_round_trips`; `test_ac_cli.py::test_ac6_*`; `test_config.py::test_example_loads` | |
| AC-11 | `test_ac11_paper_keys_still_drive_the_proof`; golden `dropped-config` (border 18.5 / 30) | M-5 |
| AC-12 | `test_ac12_help`; `test_ac_cli.py::test_ac17_help`; `test_ac_cli_only.py::test_ac7_cli_help_unchanged` | |
| AC-13 | `test_ac13_the_border_module_is_gone`, `test_ac13_no_colour_machinery_left`, `test_ac13_wheel_has_no_border_module` (slow) | |
| AC-14 | `test_ac14_no_references_left`, `test_ac14_no_colour_or_gs_in_the_package` | |
| AC-15 | `test_ac15_readme_variants_table`, `…_options_table`, `…_config_example_has_no_colour`, `…_stages_and_requirements` | M-5 |
| AC-16 | `test_ac16_decisions_entry_appended_history_untouched`, `test_ac16_open_items_retired` | read the entry |
| AC-17 | `test_ac17_claude_md_pyproject_and_tests_readme`; AC-14's scan | |
| AC-18 | `test_ac18_test_image_has_no_ghostscript`, `test_ac18_workflow_has_no_ghostscript`; `test_ac_release.py` | M-1 |
| AC-19 | `tests/acceptance/test_ac_render.py` (render marker; rewritten) | M-2 |
| AC-20 | `test_ac20_installed_wheel` (slow); `test_ac_wheel.py::test_ac3_*` | M-4 |
| AC-21 | `test_ac21_readme_image_is_plain_white` | M-3 |
| AC-22 | the whole suite: `uv run pytest` and `scripts/test-docker.sh` | |
| AC-23 | `test_ac23_version_is_0_2_0`, `test_ac23_wheel_is_0_2_0` (slow); packaging `test_ac5_version`, `test_ac2_wheel_name_and_version` | M-4 |

**Manual checks (VALIDATE)**

- **M-1** `scripts/test-docker.sh`: the full suite in an image built without
  Ghostscript; the `render` tests run (no skips under `REQUIRE_RENDER=1`) and
  pass. Also `docker run --rm menkyo-test sh -c 'command -v gs'` prints
  nothing.
- **M-2** In the image: `menkyo -c src/menkyo/example.toml -a dan -v all
  -f pdf -n ヤン・ヤンセン -r 2 -d 2026-09-05 --out /tmp/o`, then
  `pdftoppm -r 50 -png` each PDF and look at the PNGs: black text and crest
  on white, no border, no tint; the proof keeps its pale guides. Compare with
  the same command at `823af58` (`git archive 823af58`): the three must look
  identical.
- **M-3** Open `docs/three_up.png`: three plain white sheets side by side,
  each with a thin light-grey outline, readable columns, no border, no tint;
  the README caption still fits.
- **M-4** `uv build --wheel` (expect `dist/menkyo-0.2.0-py3-none-any.whl`),
  install into a fresh venv in `/tmp`, run from `/tmp`: `menkyo --version`
  (expect `menkyo 0.2.0`), `menkyo --example-config > ex.toml`,
  `menkyo -c ex.toml --list`, `menkyo -c ex.toml -v full --json`,
  `menkyo -c ex.toml --press`, `menkyo -c ex.toml --help`.
- **M-5** Read README "Configuring it for your dōjō", the Printing section,
  Options and Variants, `example.toml`'s `[paper]` comment and
  `build_diploma.py`'s module docstring: nothing describes something the
  tool no longer does; printing is on plain white A3 only, with no mention
  of bought stock; `border` / `safe_inset` are explained as margins on plain
  paper.

## Portal impact (CLI contract change)

dojo-portal is not built yet, so nothing depends on any of this. What a
caller of `menkyo … --json` would notice:

1. `--press` is gone: passing it is a usage error (exit 2 plain; one `error`
   event and exit 1 with `--json`).
2. `-v full`, `full-cream`, `full-flat` are gone: one `error` event
   (`unknown variant: …`), exit 1.
3. The default variants change from `overlay,full-cream` to `overlay`. The
   portal should pass `--variants` explicitly anyway.
4. `-v all` / `--all` now mean three variants, not six.
5. The `press` stage key disappears from `progress` events; a stage-to-Dutch
   map needs only `text`, `ink`, `pdf`, `png`. Totals for the same flags are
   unchanged except where `--press` or a removed variant was involved.
6. No more `file` events for `-K.pdf` / `-CMYK.pdf`.
7. `--example-config` prints a template without `colour`; an old
   configuration with `colour` keeps working.
8. The wheel no longer needs Ghostscript on the host; the portal image can
   drop it. Inkscape is still required until `no-inkscape`.
9. The version is `0.2.0`: the portal builds
   `menkyo-0.2.0-py3-none-any.whl` and must point its path source at the new
   file name; `menkyo --version` says `menkyo 0.2.0`.

## Test changes

New:

- `tests/acceptance/test_ac_plain_white.py` (AC-1..AC-7, AC-9..AC-18,
  AC-20, AC-21, AC-23), 66 tests. Against `823af58` it collects and the new
  criteria fail, as expected.

Goldens (AC-8):

- `tests/regression/golden_cases.py`: every case names its variants
  explicitly and only the three that remain; no `--press`. Renamed:
  `inked-default` → `inked-sample` (`-v overlay`), `flat-press` → `flat-pdf`;
  list cases `default`/`all`/`all-press-formats`/`shihan-press`/
  `minimal-press` → `overlay`/`plain`/`plain-formats`/`shihan`/`minimal`;
  the others got `-v overlay` or the explicit three.
- Goldens regenerated with `make_golden.py --ref 823af58`
  (`manifest.json` `"source": "823af58"`). The diff is 43 deleted blobs
  (the coloured variants and their text layers) and the manifest: **no
  blob was added or changed**, so every retained SVG and text layer is the
  one already pinned since the packaging item.
- `support.BASELINE_REF` = `823af58` (make_golden's default ref).

Removed behaviour:

- `test_ac_json.py`: `--press` out of AC-7; AC-8 rows for `full`,
  `full-cream`, `--press` and the old defaults replaced with neutral ones
  (defaults and `--all` moved to this item's AC-4 / AC-6);
  `test_ac9_ghostscript_missing_with_press` and `test_ac9_ghostscript_fails`
  deleted.
- `test_ac_render.py`: three variants instead of six, no `--press`, no
  `ghostscript` fixture; `test_ac13_press_conversions` and the strict xfail
  `test_ac13_press_inked_k_only` deleted; the `full-cream` tint check
  replaced by "overlay and overlay-flat transparent"; new
  `test_ac13_nothing_coloured`.
- `test_ac_cli.py`: `--press` out of AC-11's plain-stdout run and AC-17;
  AC-17's console-script check uses the explicit three variants.
- `test_ac_wheel.py`: `border` out of `MODULES`; AC-3 runs without `--press`.
- `tests/regression/test_pure.py`: `test_variants_and_defaults` →
  `test_formats_and_page` (variants and defaults are AC-1 / AC-4 now);
  `test_document_layers` without `drawn_border`, plus "nothing drawn behind
  the sheet".
- `tests/regression/test_config.py`: awards compared without a colour.
- `tests/conftest.py`: `ghostscript` fixture deleted, `FakeTools` fakes
  `inkscape` only. `tests/fakes/fake_tool.py`: `gs` and `FAKE_GS_FAIL`
  deleted. `tests/support.py`: `normalise_svg` (which hashed the 800 kB
  border out of stored goldens) deleted, `make_fake_bin` defaults to
  `inkscape`; `golden_lib.py`, `test_golden.py` and `make_golden.py` follow.
- `tests/README.md`: the new baseline, no `gs`, no Ghostscript.

**Contract changes to earlier items** (recorded here because the tester
changed their tests):

- cli-only AC-7 (`test_ac_cli_only.py::test_ac7_cli_help_unchanged`) said
  `--help` is identical to `90e5799`. plain-white rewrites the `-v` help and
  the epilog, so it now checks the set of flags: identical to `90e5799`'s
  minus `--press`.
- cli-only AC-11 (`test_ac11_decisions_entry_appended_history_untouched`)
  required the cli-only entry to be the only one after `90e5799`. It now
  finds that entry by its heading, so later items can append theirs.
- packaging AC-13 (real renders) no longer covers `--press` or the coloured
  variants; packaging AC-8's totals and AC-9's Ghostscript cases are as
  above. Packaging's version tests read the version from `pyproject.toml`
  and need no change for 0.2.0.

State against `823af58` after the first round: `uv run pytest -m "not
slow"` had all failures in `test_ac_plain_white.py`, plus 2 intended
failures that pass once built (`test_ac_cli_only.py::test_ac7_cli_help_unchanged`,
`--press` still listed; `test_config.py::test_example_loads`, the example
still has colours); 226 passed. In Docker, `test_ac_render.py` and
`tests/regression` ran with real renders: 131 passed, 1 failed
(`test_example_loads`, as above).

## Open questions

None left. The answers are recorded under "Agreement". The original nine:

1. Default variants. **Decided by the user:** `overlay` only.
2. `colour` left in a configuration. **Agreed:** accepted and ignored
   silently.
3. `[paper] border` / `safe_inset`. **Agreed:** keep the keys, defaults,
   drawing and `stock_border`; reword the docs as plain-paper margins.
4. Bought 賞状用紙. **Decided by the user:** plain white paper only; the
   route ends.
5. How removed names fail. **Agreed:** the existing generic errors, no
   aliases.
6. Version. **Decided by the user:** `0.2.0` in this item (AC-23).
7. DECISIONS history against the file's own pruning rule. **Agreed:**
   history untouched; the new entry names what it overrides.
8. Overlay PNG background. **Agreed:** stays transparent.
9. `.claude/` mentions Ghostscript. **Orchestrator** updates the agent
   files; AC-14 keeps excluding `.claude/`.

## Agreement

Revision round 1 (2026-10-28). No disagreement remains between tester and
developer.

**User decisions.**

- Q1: the default is `overlay` only (AC-4). The user wants an annotated
  Dutch companion sheet in the default later; that is the separate item
  `annotated-nl` (DECISIONS `## Open`), not this one.
- Q4: plain white paper only; the bought-stock route ends (G-1 below).
- Q6: bump to `0.2.0` in this item (AC-23).

**Orchestrator.** Accepts the recommendations on Q2, Q3, Q5, Q7 and Q8, and
updates the `.claude/` agent files itself (Q9). It decided the composition
of `docs/three_up.png` (AC-21): the default `overlay` PNGs from the example
config, flattened onto white, three side by side at 1890 × 455, a 1 px
light-grey outline per sheet, at least 4 px of white around each sheet. The
composition script is not committed.

**Developer feedback, all taken.**

- G-1 (bought stock ends): AC-11 no longer mentions bought stock and states
  that `stock_border` stays; AC-14 forbids `賞状用紙` and `bought` (`賞状`
  alone allowed); AC-12 also bans `stock` and `bought` in `--help`; AC-15
  also bans "stock" in a Printing heading; AC-16 also requires "Source the
  賞状用紙" to be retired and "An annotated version in Dutch" and "Render
  without Inkscape" to survive; M-5 reworded.
- G-2: new AC-23 (version 0.2.0 in `pyproject.toml`, `--version`, wheel
  name); M-4 and Portal impact item 9 updated.
- C-1: AC-16 no longer requires this item's entry to be the only or the
  last new one; it keeps the `823af58` prefix check and finds the entry by
  its heading (the same fix as cli-only AC-11).
- `ink.py` stays untouched; its stale "vector border" line belongs to
  `ink-memory` (Scope, Out). AC-14's patterns do not match it.

**Tests changed in this round** (`test_ac_plain_white.py`): AC-12, AC-14,
AC-15 and AC-16 as above. AC-21 is rewritten for the agreed composition
(size, 4 px white frame, outline runs). It passes on a synthetic image built
to that recipe and fails on today's image. AC-23 is added
(`test_ac23_version_is_0_2_0`, slow `test_ac23_wheel_is_0_2_0`).

Revision round 2 (2026-10-29), after review (docs/work/plain-white/review.md).

- **Contract correction, R-1.** `test_ac1_all_means_the_plain_three[flags2]`
  ran `-a dan --all` and expected only dan files. That was wrong: `--all`
  overrides `-a`, unchanged since before `823af58`, documented in `--help`
  and kept by AC-22. The `["--all"]` case is dropped from that test; `--all`
  stays covered by `test_ac1_all_flag_lists_every_award_and_variant` (all
  nine) and `test_ac1_all_writes_what_the_explicit_list_writes`. AC-1's
  wording now says `--all` selects the three variants for every award.
  Developer, reviewer and tester agree.
- **R-3.** AC-14 now forbids a bare word `gs` in every scanned file (tests
  and docs included), not only a quoted `"gs"`; the separate `gs` check for
  `src/` was folded into it. Checked: it matches "stand-in inkscape / gs"
  and not "settings" or "gsub".
