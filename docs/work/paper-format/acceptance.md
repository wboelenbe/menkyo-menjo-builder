# paper-format: acceptance

Item: DECISIONS `## Open` "Paper format: A4 as well as A3". Planned against
`bc92fbe` (HEAD, clean). Full suite before the change: 631 passed (Mac,
203 s).

## User decisions (2026-10-29, not reopened here)

1. **A4 is the A3 layout scaled by 1/√2** (≈ 0.7071): the same layout,
   columns, crest, margins and text, all proportionally smaller, on a
   landscape sheet of 297 × 210 mm. No separate A4 layout, no minimum text
   size.
2. **Chosen by `--paper a3|a4`** on the command line and by a key in
   `dojo.toml` as the dōjō's default (see OQ-1 for the key's exact place).
   A3 stays the default when neither is set. The flag wins over the
   configuration.
3. **File names always carry the size** (`-a3` / `-a4`), so every existing
   output name changes. Exactly where: AC-6.

## Scope

In:

- `src/menkyo/build_diploma.py`: a `--paper` flag; the sheet size reaching
  `document()`, the text layer, the ink pass, the PDF and the PNG; the size
  in every output name (`build_one`'s stem, `--list`); help, epilog and
  module docstring wording (the epilog says "for plain white A3" today).
- `src/menkyo/config.py`: the paper-size key: loaded, validated, defaulting
  to A3, and written by `config.save()`.
- `src/menkyo/render.py` / `ink.py`: whatever the A4 sheet needs (the
  writer refuses a viewBox whose proportions differ from the page's by more
  than 1e-9, and A4 is not exactly A3 / √2: 297/420 = 0.707143, 210/297 =
  0.707071; how that is handled is the developer's call, AC-8/AC-9 fix
  the result).
- `src/menkyo/example.toml`: the key, documented, set to A3 (OQ-5); the
  comment that says "dan-overlay-sample.pdf rather than dan-overlay.pdf".
- README, DECISIONS (docs agent): see AC-21.
- Tests: `tests/acceptance/test_ac_paper_format.py` (new), the existing
  acceptance and regression tests that spell output names (see "Test
  changes"). The developer updates `tests/test_packaging_fixes.py`
  (three names: `dan-overlay.svg`, `dan-overlay-textlayer.png`,
  `dan-overlay-flat.svg`).

Out:

- Any other paper size (Letter, B4, A5): refused like any unknown value.
- Portrait sheets.
- A separate A4 layout, a minimum text size, re-tuned typography for A4.
- Any change to what an A3 run draws: A3 output is byte for byte what it
  was, apart from the file name (and the name of the side raster inside an
  inked SVG's `xlink:href`, which is a file name).
- Any change to other flags, to the `--json` event kinds or their fields,
  or to the progress stages.
- The Dutch companion sheet (its own Open item; it will be A4 regardless).
- `docs/work/*/` paperwork of earlier items.

## Acceptance criteria

Throughout, `s` is the layout's scale on A4, `1/√2`; a uniform scale
within 0.70707 … 0.70715 is accepted (both A4 sides are met to 0.03 mm).
Every run pins `-c src/menkyo/example.toml` or a configuration the test
writes, with HOME and XDG_CONFIG_HOME isolated.

### Choosing the size

- **AC-1 Help.** `menkyo --help` lists `--paper`, names both values `a3`
  and `a4`, says A3 is the default and that the configuration can set it.
  The epilog no longer says the default overlay is "for plain white A3"
  only. (plain-white's AC-12 still bans `border`, `stock`, `printer` and
  `cream` from the help text; the new help must not use them.)
- **AC-2 A3 is the default.** Without `--paper` and without the
  configuration key, a run is A3: names carry `-a3`, the PDF is
  420 × 297 mm. `--paper a3` writes exactly the bytes a run without the
  flag writes (PDF, PNG and SVG, all three variants, the inked overlay
  included).
- **AC-3 The configuration sets the dōjō's default; the flag wins.**
  With `[paper] size = "a4"` (OQ-1) a run without `--paper` is A4;
  `--paper a3` on top of it is A3. With `size = "a3"`, `--paper a4` is A4.
  A configuration without the key is A3. `config.save()` writes the key,
  and a saved configuration loads back with the same size. Upper case is
  accepted by both (`--paper A4`, `size = "A4"`) and the name says `a4`
  (OQ-2).
- **AC-4 A bad `--paper`.** `--paper a5`, `--paper letter`, `--paper ''`,
  `--paper a3,a4` and `--paper` with no value: a non-zero exit, stderr
  names `--paper` and the choices `a3` and `a4`, no traceback, nothing
  written to `--out` (and `--clean` empties nothing). The same with
  `--list` (nothing listed). With `--json`: exit 1, exactly one stdout line,
  an `error` event whose message names `--paper`, no `done`, no `planned`.
  For `--paper` with no value, argparse's own message ("argument --paper:
  expected one argument") is enough: it names `--paper` and need not name
  the choices. Upper case (`A4`) is accepted (OQ-2, AC-3).
- **AC-5 A bad configuration value.** `size = "a5"`, `size = 4`,
  `size = ""`, `size = true`: exit 1, the message names the configuration
  file, the key (`[paper]` and `size`) and the values `a3` and `a4`, no
  traceback, nothing written. The same with `--list`, and also when
  `--paper a3` is given (a broken configuration is reported, not
  overridden). With `--json`: exactly one `error` event, exit 1.

### Names

- **AC-6 Where the size goes.** Every output is named
  `<award>-<variant>-<size>[-<suffix>].<ext>`, `<size>` being `a3` or
  `a4`, lower case: after the variant, before the free-text suffix. An
  inked SVG's side raster is `<award>-<variant>-<size>[-<suffix>]-textlayer.png`
  and the SVG's `xlink:href` names it. The same names appear in `--list`,
  in `planned` events, in `wrote …` lines, in `file` events and in `done`'s
  `files`.

  | run (example config) | before | after |
  |---|---|---|
  | `menkyo` | `dan-overlay-sample.pdf` | `dan-overlay-a3-sample.pdf` |
  | `menkyo --paper a4` | – | `dan-overlay-a4-sample.pdf` |
  | `-v overlay-flat` | `dan-overlay-flat-sample.pdf` | `dan-overlay-flat-a3-sample.pdf` |
  | `-v proof --paper a4` | – | `dan-proof-a4-sample.pdf` |
  | `-n ヤン・ヤンセン -r 2` | `dan-overlay-2-ヤン-ヤンセン.pdf` | `dan-overlay-a3-2-ヤン-ヤンセン.pdf` |
  | `--suffix ''` | `dan-overlay.pdf` | `dan-overlay-a3.pdf` |
  | `--suffix archive -n ヤン・ヤンセン` | `dan-overlay-archive.pdf` | `dan-overlay-a3-archive.pdf` |
  | `-f svg` (inked) | `dan-overlay-sample-textlayer.png` | `dan-overlay-a3-sample-textlayer.png` |

  Why there: the award and variant are fixed vocabularies and the size is
  a third; the suffix is free text (a name, a grade, `--suffix`) and stays
  last, so a reader or a program splits the fixed part from the free one at
  the same place it does today, `--suffix` still means "a tag appended",
  and a listing sorts by award, then variant, then size.
- **AC-7 Only the size is new in a name.** Every name a run wrote before
  is the same name with `-<size>` inserted after the variant; nothing else
  in it changes (the regression goldens' names, mapped).

  Why the goldens change: user decision 3 renames every output. The
  goldens in `tests/regression/golden/` stay as made from `823af58` and are
  compared through that mapping, so they still prove that the bytes of
  every A3 file are unchanged; only the names (and the side raster's name
  in an inked SVG's `xlink:href`) move.

### The A4 sheet

- **AC-8 Page size.** An A4 PDF's page is 841.89 × 595.28 pt (297 × 210
  mm), ±0.01 pt, for `overlay`, `overlay-flat` and `proof`. An A3 PDF's is
  unchanged, 1190.55 × 841.89 pt. An A4 `-f svg` file's root says
  `width="297mm" height="210mm"`.
- **AC-9 The same layout, scaled.** For the same run, the A4 page drawn
  at 200 dpi matches the A3 page drawn at 200 dpi and scaled by `s`:
  the bounding box of everything drawn agrees within 0.3 mm on every
  side, and the mean absolute alpha difference over the drawn pixels is at
  most 15/255 (flat and proof; at most 20/255 for the inked overlay, whose
  grain is not resampled with the page). A 0.5 mm shift scores about 85, a
  faithful scale about 4 (prototype, see Notes). Cases: the filled sample,
  every slot blank, the proof, a licence with a long name, the inked
  overlay, a traced crest glyph, and a configuration with its own `border`,
  `safe_inset` and `text_drop` (OQ-3: the margins scale with the sheet).
- **AC-10 PNG resolution is the physical sheet's.** `--dpi N` is pixels
  per inch of the A4 sheet: an A4 PNG at 300 dpi is 3508 × 2480 px, at
  150 dpi 1754 × 1240; A3 at 300 stays 4961 × 3508. The PNG records the
  same dpi as an A3 one (`pHYs`). The 1–2400 range is unchanged with
  `--paper a4`.
- **AC-11 The text layer stays 600 dpi.** An A4 inked overlay's text layer
  is rendered at 600 dpi of the A4 sheet, so its pixel size is the A3
  one's scaled by `s` (± 2 px each way), RGBA, graded. `INK_DPI` stays 600.
- **AC-12 The ink reads as the A3's.** Over the inside of the strokes
  (the graded alpha ≥ 128, eroded by 3 px), the A4 text layer's share of
  lifted pixels (alpha < 0.9) is within 0.60–1.40 of the A3 one's, its 5th
  percentile within 8 levels and its mean within 1.5 levels. VALIDATE
  records the printed values from the Docker run too. Both ways of
  grading in OQ-4 pass this; the visual check is M-3.
- **AC-13 A4 costs no more than A3.** The `menkyo` process's peak RSS
  for `-a dan -v overlay -f pdf` (the portal's run) at A4 is at most
  0.9 × the same run's at A3 (peak_driver.py, fresh processes); had OQ-4
  gone to faithful grading, at most 1.05 × (RSS noise). With OQ-4's
  recommendation the ink pass alone drops from +201 MB to +119 MB on the
  Mac; the Docker figures (measure.sh, median of 3, A3 and A4, C-1p and
  C-4p) go into the DECISIONS entry (M-4).

### Unchanged apart from the size

- **AC-14 `--json` events.** The same run at A3 and at A4 emits the same
  events with the same fields and the same `progress` steps, totals,
  stages and labels; the paths differ only by `-a3` against `-a4`.
- **AC-15 Every variant and the sample.** `--all --paper a4` writes the
  three variants of the three awards, all `-a4-sample`, and `done` lists
  them; `-v proof --paper a4` draws the guides and the calligrapher's
  zones (AC-9's proof case).
- **AC-16 Deterministic.** The same A4 command writes the same bytes
  twice (PDF and PNG, inked and flat).
- **AC-17 Glyph checks before anything is written.** A character the
  fonts lack fails an A4 run exactly as an A3 one: exit 1, the message
  naming it, nothing written.
- **AC-18 A3 output is byte for byte unchanged.** The regression goldens
  pass with only the names mapped (AC-7): every SVG, the text layers
  drawn, stdout modulo names, the flat and proof PDF hashes. The
  render-without-inkscape comparisons of the inked overlay keep passing.
- **AC-19 Installed wheel.** From a wheel installed outside the checkout,
  `menkyo --paper a4 -a dan -v overlay-flat --json` (no `-c`, isolated
  HOME) writes `~/Documents/Menkyo/dan-overlay-flat-a4-sample.pdf`, an A4
  page; a configuration with the key, passed by `-c`, does the same without
  the flag.
- **AC-20 No other flag changes.** `--help` lists exactly the flags it
  listed before, plus `--paper`. `--dpi`, `--suffix`, `--list`, `--clean`,
  `--out` and the fill-in flags behave as before, at either size.

### The record

- **AC-21 Docs.** README: `--paper` in the Options table; the paper key
  in the configuration example; the naming scheme
  (`<award>-<variant>-<size>.<ext>` in Quick start) and every example file
  name with its size, the "As a package" output included; Printing says
  how to print A4 (297 × 210 mm, at 100 %). No file name in README,
  `example.toml` or `build_diploma.py`'s docstring lacks the size.
  DECISIONS: a new dated entry for A4 (what was decided above, the naming
  and why, the ink answer to OQ-4 with its numbers, the measurements of
  M-4), naming what it overrides: ‘Plain white paper only’ (‘plain white
  A3 and nothing else’) and the old naming; the pinned entries stay as
  written. `example.toml`'s `[paper]` comment no longer says "Millimetres,
  on plain white A3" alone: the values are A3 millimetres and scale on A4; the Open item "Paper format: A4 as well as A3" is gone; no pinned
  history block changes (`test_ac11_history_pinned`), the 2026-09-05 Brief
  keeps saying A3; the house-style lint passes. `pyproject.toml`'s
  description and version: OQ-6.

## Test approach per AC

All in `tests/acceptance/test_ac_paper_format.py` unless named otherwise;
`render` marks real renders, `slow` the wheel.

| AC | test(s) |
|---|---|
| 1 | `test_ac1_help_lists_paper` |
| 2 | `test_ac2_default_is_a3`, `test_ac2_explicit_a3_is_the_default_bytes` (render) |
| 3 | `test_ac3_config_sets_the_default`, `test_ac3_flag_beats_config`, `test_ac3_missing_key_is_a3`, `test_ac3_save_round_trip`, `test_ac3_upper_case_accepted` |
| 4 | `test_ac4_bad_paper_flag`, `test_ac4_bad_paper_flag_json`, `test_ac4_missing_value`, `test_ac4_bad_flag_cleans_nothing` |
| 5 | `test_ac5_bad_config_value`, `test_ac5_bad_config_value_json` |
| 6 | `test_ac6_list_names`, `test_ac6_planned_events`, `test_ac6_written_names_and_events` (render) |
| 7 | `tests/regression/test_golden.py` (names mapped), `test_ac7_sized_name_mapping` (incl. idempotence) |
| 8 | `test_ac8_pdf_page_size` (render), `test_ac8_svg_root_size` |
| 9 | `test_ac9_a4_is_a3_scaled` (render, 7 cases) |
| 10 | `test_ac10_png_size` (render), `test_ac10_dpi_range_unchanged` |
| 11 | `test_ac11_text_layer_600_dpi` (render; module fixture `text_layers`) |
| 12 | `test_ac12_ink_reads_as_a3` (render; the same renders) |
| 13 | `test_ac13_a4_peak_memory` (render) + M-4 |
| 14 | `test_ac14_json_events_same_but_names` (render) |
| 15 | `test_ac15_all_variants_a4` (render), AC-9's proof case |
| 16 | `test_ac16_deterministic` (render) |
| 17 | `test_ac17_glyph_check_first` |
| 18 | `tests/regression/`, `test_ac_render_without_inkscape.py` |
| 19 | `test_ac19_installed_wheel_a4` (slow, render) |
| 20 | `test_ac20_help_flags` |
| 21 | `test_ac21_readme`, `test_ac21_names_in_docs`, `test_ac21_example_config`, `test_ac21_decisions`, plus `test_ac_house_style_sweep.py` (lint, pin) |

### Manual checks (VALIDATE)

- **M-1 Look at it.** `menkyo -c src/menkyo/example.toml -a dan -v
  overlay,proof -f png --paper a4 --dpi 150 -d 2026-09-05` and the same at
  A3 at 106 dpi (about the same pixels): side by side, the same sheet.
- **M-2 Print scale.** Open the A4 PDF in Preview: Tools → Show Inspector
  shows 297 × 210 mm.
- **M-3 Ink at print size.** The A4 overlay's text layer at 600 dpi next
  to the A3 one downscaled to the same pixel size, crops of the formula and
  the date: the brush tips grade the same way, no darker or blotchier.
- **M-4 Memory and time.** `tests/acceptance/render_without_inkscape/measure.sh`
  in the Docker image for C-1p and C-4p, at A3 and at A4, median of 3:
  A4's peak and wall time at most A3's. The numbers go into DECISIONS.
- **M-5 Installed wheel.** Build the wheel, install it in a throwaway
  venv, from `/tmp`: `menkyo --paper a4 --list`, then a real run, and the
  portal's form (`--config=… --awards=dan --variants=overlay --formats=pdf
  --name=… --rank=… --date=… --out=… --json --paper=a4`).

## Test changes (tests/acceptance, tests/regression)

Done in this PLAN, by the tester; they fail until the names carry the size.

- `tests/regression/golden_lib.py`: `sized(text, size)`, which inserts
  `-<size>` after the variant in every output name in a string (file names,
  `wrote` lines, `--list` output, an `xlink:href`).
- `tests/regression/test_golden.py`: the goldens' names, stdout, PDF-hash
  keys and SVG text compared through `sized(…, "a3")`. The manifest,
  `golden/svg/` and `pdf_sha256.json` are not regenerated: they keep
  proving the A3 bytes against `823af58`.
- Names updated to carry `-a3`: `test_ac_cli.py` (AC-11 ×2),
  `test_ac_json.py` (AC-7), `test_ac_paths.py` (AC-15),
  `test_ac_plain_white.py` (AC-1, AC-4, AC-5, AC-7, AC-11, AC-19),
  `test_ac_remove_supersample.py` (AC-8; AC-7 reads the manifest and keeps
  the old names), `test_ac_render.py` (`f()`, AC-13),
  `test_ac_render_without_inkscape.py` (AC-9's listing), `test_ac_wheel.py`
  (AC-3 ×2).
- `--paper` added to the exact option set of
  `test_ac_render_without_inkscape.py::test_ac23_help_offers_todays_options`.
- "Paper format" dropped from the Open items that
  `test_ac_house_style_sweep.py::test_ac12_open_item_closed` and
  `test_ac_render_without_inkscape.py::test_ac35_open_item_closed` require to
  remain.
- After the user's approval (IMPLEMENT round):
  `test_ac_render_without_inkscape.py::test_ac37_version` expects 0.4.0
  (OQ-6), and `test_ac_cli_only.py::test_ac7_cli_help_unchanged` allows
  `--paper` as the one added flag (AC-20; it runs only where git has
  `90e5799`, so the Mac, not Docker). `test_ac3_upper_case_accepted` stays
  (OQ-2 approved).

## Open questions

- **OQ-1 The configuration key.** The decision says `paper = "a4"` in
  `dojo.toml`, but `[paper]` is already a table there (`border`,
  `safe_inset`, `text_drop`): a top-level `paper = "a4"` beside it is a
  TOML error (duplicate key), and every existing `dojo.toml` has the table.
  **Recommendation: `size = "a4"` under `[paper]`**, beside the other
  sheet settings. The tests use that; the key is one constant
  (`SIZE_KEY`) in the test file.
- **OQ-2 Upper case.** Should `--paper A4` and `size = "A4"` be accepted?
  **Recommendation: yes, case-insensitively, and named `a4` in files** –
  "A4" is how everybody writes it. Not in the tests until decided.
- **OQ-3 `border` and `safe_inset` on A4.** They are mm on the sheet. Under
  decision 1 they scale with everything else (22 → 15.6 mm, 38 → 26.9 mm),
  so the proof's guides sit where the A3's do, proportionally.
  **Recommendation: they scale** (the values in the configuration are A3
  millimetres); the alternative, keeping them physical, would put the 38 mm
  safe inset over the A4 text. AC-9's custom-margins case pins the
  recommendation. `text_drop` is a fraction of the page height and scales
  either way.
- **OQ-4 The ink at the smaller size.** `ink.py` measures in pixels of a
  200 dpi field (`WORK_DPI`), with grain blur `NOISE_MM = 0.30` mm and a
  final blur of 1.2 field pixels; `MIN_DENSITY` and `FULL_AT` are relative
  and stroke thickness is normalised per stroke. So the grading is
  physical: at A4 the grain and blur stay the same size in mm while the
  glyphs shrink. Measured on the example's dan text layer (prototype in
  the scratchpad, A4 drawn as the A3 SVG under `scale(1/√2)`):

  | | ink pass (Mac) | lifted share inside strokes | 5th pct | mean abs diff vs A3 scaled |
  |---|---|---|---|---|
  | A3 | +201 MB, 1.6 s | 0.0296 | 233 | – |
  | A4, ink.py as is (field at 200 dpi of the A4 sheet) | +119 MB, 0.8 s | 0.0227 | 237 | 1.57 |
  | A4, graded as the A3 (`ink_layer(…, dpi=600/√2)`: field and grain scale with the glyphs) | +194 MB, 1.6 s | 0.0266 | 235 | 1.01 |

  As is, the A4 brush lifts in about a quarter fewer pixels: a hair darker
  at the tips. Side by side at screen size the three are indistinguishable.
  **Recommendation: leave the ink parameters physical** (call `ink_layer`
  at 600 dpi as today): no change to `ink.py`, the ink pass's memory and
  time drop by 40–50 %, and the difference is below what a print shows.
  If the user prefers the faithful scale, AC-13's 0.9 becomes "at most
  A3's" and nothing else in the contract moves. M-3 is the eye check.
- **OQ-5 The example configuration.** **Recommendation: `size = "a3"`
  written out under `[paper]`, with a comment naming `a4` and `--paper`**,
  so a dōjō sees the knob. It changes `--example-config`'s output by those
  lines only.
- **OQ-6 Version and description.** Every output name changes, which a
  consumer that looks for a file by name would notice (the portal reads
  the `file` events' paths, so it should not). **Recommendation: 0.4.0**,
  and `pyproject.toml`'s description "A3, vertical, print-ready" becomes
  "A3 or A4, …". Not tested until decided.
- **OQ-7 A suffix that looks like a size.** `--suffix a4` at A3 gives
  `dan-overlay-a3-a4.pdf`. **Recommendation: allow it** (the size comes
  first, so it is unambiguous); no test.

## Notes

- The prototype (scratchpad, not in the repository): the example's dan
  certificate, A4 drawn as the A3 SVG inside `scale(0.7071067812)` on a
  297 × 210 mm, `viewBox="0 0 297 210"` root. Its page at 200 dpi scored a
  mean absolute alpha difference of 3.8 (flat) and 4.9 (proof) over the
  drawn pixels against the A3 page scaled down, and 85–90 when shifted by
  0.5 mm; bounding boxes agreed within 0.1 mm. AC-9's limits come from
  those numbers.

## Agreement

Round 2 (2026-10-29), developer and tester. The developer agrees with every
OQ recommendation (OQ-1 `[paper] size`, OQ-2 case-insensitive, OQ-3 the
margins scale, OQ-4 `ink.py` unchanged at 600 dpi, OQ-5 `size = "a3"` in
the example, OQ-6 0.4.0, OQ-7 allowed); the user's approval is pending and
the contract assumes it. Changes folded in:

- AC-4: `--paper` with no value only has to name `--paper` (argparse's
  "expected one argument"); the choices are not required in that case.
  The test already asked no more.
- AC-12: limits widened to a lifted-pixel ratio of 0.60–1.40 and a 5th
  percentile within 8 (were 0.70–1.30 and 5). Prototype: 0.767 and 4;
  developer: 0.83, p5 234 against 236. VALIDATE confirms in Docker.
- AC-13: under faithful grading (OQ-4 the other way) the limit would be
  1.05 × A3, not 1.0 ×. The developer measured the ink pass at A3 302 MB,
  A4 213 MB (0.71) under the recommendation.
- `golden_lib.sized()` is idempotent now (a name that already has
  `-a3`/`-a4` keeps it); `test_ac7_sized_name_mapping` asserts it.
- AC-21: the new DECISIONS entry names what it overrides (‘Plain white
  paper only’ and the old naming); `example.toml`'s margin comment says the
  values are A3 mm and scale on A4. Both in `test_ac21_*`.
- AC-11 and AC-12 share one A3 and one A4 render (module fixture
  `text_layers`).
- OQ-2: `test_ac3_upper_case_accepted` (`--paper A4`, `size = "A4"`, the
  name says `a4`). Withdrawn if the user decides against it.
- For the record, the implementation: the A4 root is
  `width="297mm" height="210mm" viewBox="0 0 297 210"` with everything
  inside `<g transform="scale(0.7071067812)">`; the writer's 1e-9 check is
  untouched; A3 emits no wrapper, so its SVG stays byte for byte.

## User approval (2026-10-29)

The user approved the plan with all the recommendations:
- OQ-1: the config key is `[paper] size`.
- OQ-2: the flag and the key are case-insensitive; file names use lower case.
- OQ-3: margins scale with the sheet.
- OQ-4: the ink grain keeps its physical size (no `ink.py` change), so
  AC-13 stays at 0.9 × A3.
- OQ-5: `example.toml` writes `size = "a3"`, with a comment.
- OQ-6: version 0.4.0.
- OQ-7: `--suffix a4` is allowed on A3.

Asked before planning: A4 is A3 scaled by 1/√2; `--paper` plus a config
default, the CLI wins, A3 is the default; file names always carry the size.
