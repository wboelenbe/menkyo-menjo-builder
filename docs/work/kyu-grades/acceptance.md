# kyu-grades: acceptance

Item: DECISIONS `## Open` "Kyū grades". Planned against `04f45ec` (HEAD,
clean). Suite before the change, `uv run pytest -m "not slow"`: 713 passed,
17 deselected (Mac, 197 s).

## User decisions (2026-10-29, not reopened here)

1. **A simpler sheet, a new award `kyu`** (`-a kyu`), not the dan sheet. It
   keeps the heading, the recipient's name, the grade, the formula, the
   date, the art, the dōjō, the signatory's title and name, and the inked
   look (the same three variants). It drops the crest (mon), the crest ring
   and the motto column. A3 and A4 like every award (`--paper`). How the
   layout re-spaces is OQ-3.
2. **The example's kyū award**: heading 級位認定証, formula 右認定ス; a
   `dojo.toml` sets its own, as for any award.
3. **Grades 1–10 kyū**, 10 lowest, 1 just below shodan. Belts: white 6,
   yellow 5, orange 4, green 3, blue 2, brown 1. Kids' steps in between:
   white-yellow → 準五級, yellow-orange → 準四級, orange-green → 準三級.
4. **Input, on a kyū award**: `-r 5`, `-r gokyu`, `-r yellow` → 五級;
   `-r white-yellow`, `-r jun5` → 準五級; a literal (`-r 三級`) passes
   through. The award decides the unit: on a dan award `-r 3` stays 三段.
   Unknown input is an error naming the accepted forms, plain and under
   `--json`.

## Scope

In:

- `src/menkyo/build_diploma.py`: reading `--rank` and `[sample] rank` in
  each award's unit; the kyū sheet without crest, ring and motto; the
  grade fitted to its zone (OQ-12); the up-front glyph check following
  what each award draws; `--rank` help; the module docstring.
- `src/menkyo/config.py`: the award's unit and its two sheet keys (OQ-1,
  OQ-2), validated with errors naming the file and key; `save()` writes
  them and they load back.
- `src/menkyo/example.toml`: the `kyu` award after `renshi` (OQ-5), its
  keys commented; the `[sample] rank` comment says what 5 is on a kyū
  sheet.
- README, DECISIONS, `docs/kyu-explained.md` (docs agent; AC-16, OQ-8).
- `pyproject.toml`: version (OQ-9) and description.
- Tests: `tests/acceptance/test_ac_kyu_grades.py` (new) and the older
  tests that count the example's awards (see "Test changes").

Out:

- Printing the belt colour anywhere on the sheet. The colour is an input
  form only.
- Grades outside 1–10 kyū; 準 for any step but the three kids' ones
  (OQ-7); 準初段 or other dan-side intermediate steps (a literal still
  passes through on a dan award, as today).
- Any change to what a dan, shihan or renshi sheet draws, at A3 or A4
  (AC-14), and to `--rank` on a dan-unit award beyond OQ-4.
- A re-balanced kyū layout, unless OQ-3 goes that way.
- The Dutch companion sheet (its own Open item); the portal.
- New flags, new `--json` events or fields, new progress stages.

## Acceptance criteria

Every run pins `-c src/menkyo/example.toml` or a configuration the test
writes (for the installed wheel: the installed copy's own `example.toml`),
with HOME and XDG_CONFIG_HOME isolated. "The example" is
`src/menkyo/example.toml` as this item leaves it.

### The award

- **AC-1 The example has a kyū award.** `example.toml` defines four awards,
  in order `dan`, `shihan`, `renshi`, `kyu` (OQ-5). `kyu` has heading
  級位認定証, formula 右認定ス, declares the kyū unit and the simpler sheet
  with the agreed keys (OQ-1, OQ-2: `grade_column = "kyu"`,
  `crest = false`, `motto = false`). The other three awards say what they
  said. `--example-config` prints the file byte for byte. `--help` lists
  `dan,shihan,renshi,kyu` for `--awards`, and the `--rank` help says what a
  kyū award takes (mentions kyū and 級).
- **AC-2 What a run builds, and the names.** The default run and `-a all`
  build every award of the configuration, `kyu` included; `--all` is every
  award times every variant. With the example: `--list` is
  `{dan,shihan,renshi,kyu}-overlay-a3-sample.pdf`, `--all` twelve names,
  `--paper a4` the same with `-a4`. Kyū names follow
  `kyu-<variant>-<size>[-<suffix>].<ext>`; the derived suffix is the
  `--rank` value as typed, then the name, as for dan:

  | run | file |
  |---|---|
  | `-a kyu` | `kyu-overlay-a3-sample.pdf` |
  | `-a kyu --paper a4` | `kyu-overlay-a4-sample.pdf` |
  | `-a kyu -r yellow -n ヤン・ヤンセン` | `kyu-overlay-a3-yellow-ヤン-ヤンセン.pdf` |
  | `-a kyu -r white-yellow` | `kyu-overlay-a3-white-yellow.pdf` |
  | `-a kyu -r 準五級 --paper a4` | `kyu-overlay-a4-準五級.pdf` |
  | `-a kyu --suffix ''` | `kyu-overlay-a3.pdf` |
  | `-a dan,kyu -r 3` | `dan-overlay-a3-3.pdf`, `kyu-overlay-a3-3.pdf` |

  `--list --json` gives the same names as `planned` events.

### The sheet

- **AC-3 No crest, no ring, no motto; the rest is there.** A kyū sheet
  (`overlay-flat`, `proof`, and the inked `overlay`'s SVG) has no crest
  rings, no mon, no ring lettering (nothing in the crest's face) and no
  motto column, although the example sets `[motto] text`; the proof's only
  circle is the seal guide. With every slot printed, its columns are
  exactly: 級位認定証, the name with 殿, the grade, 右認定ス, the date, the
  art, the dōjō, the office, the signatory. With every slot blank: the
  heading, the formula, the blank date's fixed characters, the art, the
  dōjō, the office and the signatory.
- **AC-4 Layout (OQ-3: option B, the user's decision).** On an award
  with `motto = false` every column and the seal move 10 mm left, so the
  printed block is centred (68.75 mm left, 69 mm right). For the same
  flags, at A3 and at A4, a kyū sheet's name, date, art, dōjō, office and
  signatory are the dan sheet's glyphs 10 mm to the left (same y, size);
  heading and formula start 10 mm left of the dan sheet's, at its size;
  the grade sits in the dan sheet's grade column, 10 mm left. The
  crest's place stays empty; on an award with a crest and
  `motto = false` the crest stays at the page centre. The move is keyed
  on the award's `motto` key only: an empty `[motto] text` moves nothing
  (the dan sheet is the same minus the motto glyphs), so dan, shihan,
  renshi and every golden, `minimal.toml` included, stay byte for byte. A4 is the A3
  layout inside the `scale(0.7071067812)` wrapper, as for every award.
  **Grade fit (OQ-12, rule agreed):** on every award, a printed grade of
  n characters is set at `min(SZ_RANK, 2 × SZ_RANK / n)`, top-aligned:
  the first glyph's top at `y_rank − SZ_RANK / 2`, so the column never
  exceeds the two-character extent of 60 mm (準五級 at 20 mm, `-r Shihan`
  on dan at 10 mm, 師範代 on a licence at 20 mm); one and two characters
  keep `SZ_RANK`. No golden changes (every golden grade has two
  characters). Without this, 準五級 runs 30 mm into the calligrapher's
  name zone.
- **AC-5 It renders.** `-a dan,kyu -v all -f pdf,png` at A3 and at A4: exit
  0, every file named in `done`, every kyū PDF page 1190.55 × 841.89 pt
  (A3) or 841.89 × 595.28 pt (A4) ± 0.01. In every kyū PNG (all three
  variants) nothing is drawn in the crest's box (x 192–220, y 39–63 mm:
  the mon and the inner ring, clear of the moved formula) or the motto's
  strip (`X_MOTTO` ± 7 mm, y 95–165 mm), where the dan PNG of the same
  run has ink; the heading is drawn 10 mm left of the dan sheet's, and
  the dan sheet's signatory strip (x 88–92 mm) is empty on kyū. The inked
  overlay's `-f svg` has its text-layer `<image>` and no crest. The grades
  white-yellow, yellow-orange, orange-green and 10 render through the
  inked overlay (準, 級, 十 in the font).
- **AC-6 The proof's guides.** A kyū proof draws the same guides as the
  dan proof of the same run, at A3 and A4, the calligrapher's zones, the
  date slots and the seal 10 mm left (OQ-3 B; the border and safe inset
  are the page's and stay): the border and the safe
  inset, the seal circle, the grade zone when the grade is blank, the name
  zone when the name is blank, the nine date slots when the date is blank;
  a printed slot takes its guide away as on dan.

### Grades

- **AC-7 Kyū input forms.** On a kyū award, `--rank` gives:

  | input | prints |
  |---|---|
  | `1` … `10` (spaces around ignored), full-width digits too (`５`, `１０`) | 一級 … 十級 |
  | `ikkyu nikyu sankyu yonkyu gokyu rokkyu nanakyu shichikyu hachikyu hakkyu kyukyu jukkyu jikkyu` | the grade (OQ-7) |
  | any case, `ū` or `uu` for `u` (`GoKyu`, `gokyū`, `gokyuu`) | the same (OQ-7) |
  | `white yellow orange green blue brown`, any case | 六級 五級 四級 三級 二級 一級 |
  | `white-yellow yellow-orange orange-green`, any case | 準五級 準四級 準三級 |
  | `jun5 jun4 jun3`, any case, and `jun-5` (OQ-7) | 準五級 準四級 準三級 |
  | anything still non-ASCII after folding (`三級`, `準五級`, `弐級`, `初級`) | as given |

  Order (Agreement 1, review R-2): normalise to NFC; trim; fold `ū`/`Ū`
  to `u` and `uu` to `u`; then classify, so `gokyū`, `GOKYŪ`, ` rokkyū `
  and a decomposed `gokyū` (u + U+0304) are romaji, not literals. A
  number in full-width digits is a number, as on dan (user decision,
  2026-10-29).

- **AC-8 Anything else is refused.** On a kyū award, an ASCII value that
  is none of AC-7's forms (`purple`, `red`, `black`, `white-orange`,
  `green-blue`, `0`, `11`, `99`, `-1`, `jun6`, `jun2`, `jun1`, `jun10`,
  `jun`, `kyu`, `5kyu` (OQ-7), and the dan forms `nidan`, `shodan`,
  `godan` (OQ-4)) is an error: the message starts from `--rank <value>`
  and names the accepted forms (the range up to 10, the romaji `…kyu`,
  all six colours, the three kids' steps and `jun5`), no traceback.
  Checked before anything is written or emptied, `--list` and `--clean`
  included (nothing listed; `--clean` empties nothing). Plain: non-zero
  exit, the message on stderr. `--json`: exit 1, exactly one `error`
  event.
- **AC-9 The dan unit is unchanged.** On `dan` (and on a licence given an
  explicit `--rank`) every form reads as before: `1` → 初段, `3` → 三段,
  `10` → 十段, `nidan`, `SanDan`, `kyudan` and `kudan` → 九段 (the kyū
  detector matches whole words, Agreement 5), literals (`弐段`, `師範`,
  `Shihan`) pass through; **OQ-13:** the same folding applies, so
  `jūdan` → 十段 and `kyūdan` → 九段 (today they print as Latin); `-r 11` is still `--rank 11: dan grades run from 1 to 10`,
  `-a shihan -r 5` still prints 五段. In a mixed run each award reads the
  value in its own unit (`-a dan,kyu -r 3`: 三段 and 三級). **OQ-4:** a
  kyū-only form (a colour, a kids' step, `junN`, `…kyu` romaji) on a
  dan-unit award is an error naming `--rank <value>` and the award,
  rather than printing Latin text; a mixed run with such a value writes
  nothing.
- **AC-10 The sample grade.** With the example and no `--rank`, the kyū
  sheet prints 五級 (the sample `5` in the kyū unit), the dan sheet 五段,
  the licences nothing, as before. `-r ''` leaves the kyū grade blank and
  its proof shows the grade zone. **OQ-6:** the sample is read in each
  award's unit: `[sample] rank = "yellow"` gives 五級 on `kyu` and is an
  error naming `[sample] rank` on `dan`. On a licence (`grade_column =
  false`) the sample is not drawn, so it is not read at all (the same gate
  as the glyph check): `-a shihan` with that sample works, while an
  explicit `-a shihan -r yellow` is refused (Agreement 2).

### Configuration

- **AC-11 The award declares its unit and its sheet.** (Keys per OQ-1 and
  OQ-2.)
  - The unit follows the key, not the slug: an award `mudansha` with the
    kyū unit prints 五級 for `-r 5` (and is named `mudansha-…`); an award
    `kyu` declaring the dan unit prints 五段.
  - `grade_column = true` is the dan unit: a dan award with
    `grade_column = "dan"` draws byte for byte what `true` draws.
    `false` still means no grade column (no sample grade, the name closes
    up as before).
  - A bad unit (`"belt"`, `"Kyū grade"`, `2`, `1`, `"yes"`, `""`) is an
    error (any value but a boolean or `"dan"`/`"kyu"`, so `1` and `"yes"`,
    silently true in 0.4.0, are now refused) naming the
    file, the award's slug, `grade_column` and the values `"dan"` and
    `"kyu"`; also with `--list`; `--json` one `error` event.
  - `crest` and `motto` are per award and boolean: a dan award with both
    `false` has no crest and no motto; a kyū award with both `true` has
    them; `motto = false` alone keeps the crest. A non-boolean value
    (`"no"`, `0`, `"false"`) is an error naming the file, the key and the
    award.
  - A `dojo.toml`'s own heading and formula for its kyū award are printed.
  - `config.save()` writes `grade_column = "kyu"` for a kyū award and
    `true`/`false` otherwise, and `crest`/`motto` only when `false`, so a
    configuration without a kyū award saves byte for byte as in 0.4.0
    (Agreement 6); the saved file loads back to the
    same awards and draws the same SVGs (every award, and a kyū sheet with
    準五級).
  - A configuration from before this item (`grade_column` true or false,
    no new keys) loads, lists and draws as before (the goldens'
    `minimal.toml` and `dropped.toml` cases prove the bytes).
- **AC-12 Glyph checks follow what is drawn.** Before anything is written:
  a character the fonts lack in a kyū award's heading or formula, or in
  `--rank` on a kyū run, is the one `error` naming it (`U+…`) and its
  source (`the heading of [[awards]] 'kyu'`, `the formula of …`,
  `--rank`). A kyū sheet draws no crest ring and no motto, so on a
  kyū-only run neither `[dojo] crest_ring` nor `[motto] text` nor the art
  on the ring is checked: a configuration with `crest_ring = "한한한한"`
  and `text = "柔能𠮷剛"` renders `-a kyu` and fails `-a dan`, naming one
  of the two.

### Unchanged

- **AC-13 `--json` and progress.** `-a kyu` (overlay, PDF) emits three
  `progress` events (`text`, `ink`, `pdf`; steps 1–3 of 3; award `kyu`;
  labels `kyu overlay: …`; the same seven keys), one `file`, one `done`.
  The default run's progress covers the four awards, total 12. No new
  event kind, field or stage.
- **AC-14 A3 and A4 dan, shihan, renshi output unchanged.** The regression
  goldens pass. Their example cases run on a copy of the example without
  the `kyu` award (`golden_lib.baseline_awards_only`, everything else as
  the example has it), so stdout, file sets, every SVG, the text layers
  and the flat/proof PDF hashes are still compared byte for byte. And the
  `-a all` SVG cases (`sample`, `blank`, `filled`) on the example as it is
  write the goldens' dan, shihan and renshi files byte for byte, plus kyū
  files. paper-format's A4 tests keep passing.
- **AC-15 Installed wheel.** From a wheel installed outside the checkout:
  `--example-config` has the kyū award; `--list` the four awards; the
  portal's form `--config=<its example> --awards=kyu
  --variants=overlay-flat --formats=pdf,svg --name= --rank=white-yellow
  --date=… --json` writes `~/Documents/Menkyo/kyu-overlay-flat-a3-white-yellow.{pdf,svg}`
  with 準五級; `--rank=purple` is one `error`; `--paper a4` writes an A4
  kyū overlay.

### The record

- **AC-16 Docs.** README: the introduction mentions kyū certificates; the
  Options row for `--rank` shows a kyū form (級); "Filling the document
  in" (or its own section) gives the kyū forms (numbers, `gokyu`, the six
  colours, the three kids' steps, `jun5`, 準五級) and says the award
  decides the unit; the configuration example shows the `kyu` award with
  its keys (`grade_column = "kyu"`, `crest = false`, `motto = false`) and
  explains them; the glyph-check paragraph no longer says the art is
  always checked against the ring's face (only where a crest is drawn).
  `example.toml`: the kyū block and its keys commented; the `[sample]
  rank` comment mentions 五級. DECISIONS: a new dated entry, last before
  `## Open`, its heading naming kyū: the sheet and why (decision 1, OQ-3),
  級位認定証 / 右認定ス, the forms and 準 (white-yellow …), the keys
  (`grade_column` …), OQ-4/OQ-6/OQ-12 as decided, the version 0.5.0; it
  names what it overrides by title: ‘Purple menkyo, and a precept column’
  (the precept on every document) and ‘Printing the three hand slots’
  (anything unrecognised passes through). The Open item "Kyū grades" is
  gone, "An annotated version in Dutch" stays; the pinned history blocks
  are unchanged (house-style-sweep AC-11); the house-style lint passes on
  every in-scope file, `docs/kyu-explained.md` and `tests/README.md`
  included. **OQ-8:** `docs/kyu-explained.md`, a recipient's explainer
  like the other three: 級位認定証, 右認定ス, 準, the "If you are adapting
  this document" blocks, no precept (the kyū sheet has none).
- **AC-17 Version (OQ-9).** `pyproject.toml` says 0.5.0 and
  `menkyo --version` prints `menkyo 0.5.0`. The description mentions kyū
  (not tested).

## Test approach per AC

All in `tests/acceptance/test_ac_kyu_grades.py` unless named otherwise;
`render` marks real renders, `slow` the wheel.

| AC | test(s) |
|---|---|
| 1 | `test_ac1_example_has_the_kyu_award`, `test_ac1_example_config_prints_it`, `test_ac1_help_lists_kyu` |
| 2 | `test_ac2_default_and_all_include_kyu`, `test_ac2_names` (9 cases), `test_ac2_planned_events`; the updated counts in `test_ac_plain_white.py`, `test_ac_json.py`, `test_ac_cli.py`, `test_ac_paper_format.py` |
| 3 | `test_ac3_no_crest_no_ring_no_motto` (flat, proof), `test_ac3_keeps_the_core_text`, `test_ac3_blank_slots_stay_blank`, `test_ac5_inked_svg_has_no_crest` (render) |
| 4 | `test_ac4_same_columns_as_the_dan_sheet_moved_left` (4 fill-ins × A3/A4), `test_ac4_kyu_block_is_centred`, `test_ac4_an_empty_precept_moves_nothing`, `test_ac4_grade_stays_in_its_zone` (7 grades × with/without name), `test_ac11_sheet_keys_drive_the_sheet` (crest stays centred) |
| 5 | `test_ac5_renders_every_variant` (render, A3/A4), `test_ac5_inked_svg_has_no_crest` (render), `test_ac5_every_grade_form_renders` (render) |
| 6 | `test_ac6_proof_guides` (4 × A3/A4) |
| 7 | `test_ac7_kyu_rank_forms` (49 cases) |
| 8 | `test_ac8_unknown_kyu_rank_names_the_forms` (19), `test_ac8_plain_error`, `test_ac8_list_checks_too`, `test_ac8_json_error` |
| 9 | `test_ac9_dan_sheet_unchanged` (8), `test_ac9_dan_range_message_unchanged`, `test_ac9_licence_takes_an_explicit_rank_as_before`, `test_ac9_mixed_run_each_in_its_unit`, `test_ac9_kyu_forms_refused_on_a_dan_award` (8), `test_ac9_mixed_run_refused_before_anything_is_written`; `tests/regression/test_pure.py` |
| 10 | `test_ac10_sample_rank_on_a_kyu_sheet`, `test_ac10_sample_rank_cleared`, `test_ac10_sample_rank_in_the_kyu_unit` |
| 11 | `test_ac11_unit_follows_the_key_not_the_slug`, `test_ac11_true_is_dan`, `test_ac11_licences_unchanged_by_false`, `test_ac11_bad_unit_is_an_error` (4), `test_ac11_bad_sheet_key_is_an_error` (6), `test_ac11_sheet_keys_drive_the_sheet`, `test_ac11_dojo_overrides_heading_and_formula`, `test_ac11_save_round_trip`, `test_ac11_old_configuration_works`; `tests/regression/test_config.py` |
| 12 | `test_ac12_kyu_heading_checked_first`, `test_ac12_kyu_formula_and_rank_checked_first`, `test_ac12_what_a_kyu_sheet_does_not_draw_is_not_checked` (render) |
| 13 | `test_ac13_json_events` (render), `test_ac13_default_run_totals` (render) |
| 14 | `tests/regression/test_golden.py`, `test_ac14_example_as_it_is_still_draws_the_goldens` (3), `test_ac14_baseline_copy_is_the_example_without_kyu`; `test_ac_paper_format.py` |
| 15 | `test_ac15_installed_wheel` (slow, render) |
| 16 | `test_ac16_readme`, `test_ac16_example_comments`, `test_ac16_decisions_entry`, `test_ac16_recipient_explainer`; `test_ac_house_style_sweep.py` (lint over every in-scope file, AC-11 pin, AC-12 Open items) |
| 17 | `test_ac17_version`; `test_ac_render_without_inkscape.py::test_ac37_version` |

17 of the 194 new tests pass before the feature exists: the dan-unit
checks of AC-9 and AC-11's `true`/old-configuration checks, which pin
behaviour that must not change.

### Manual checks (VALIDATE)

- **M-1 Look at it.** `menkyo -c src/menkyo/example.toml -a dan,kyu -v
  overlay,proof -f png --dpi 100 -d 2026-09-05`, and the same with
  `--paper a4`: the kyū sheet beside the dan sheet. Judge the balance
  without the crest and the motto (OQ-3), and that the sheet reads as one
  of the set. Then `-a kyu -v proof -n '' -r white-yellow` and
  `-n ヤン・ヤンセン -r orange-green`: the smaller 準 grade sits in its
  zone, clear of the name zone (OQ-12).
- **M-2 Installed wheel.** Build the wheel, install it in a throwaway
  venv, from `/tmp`: `menkyo -c <site>/menkyo/example.toml -a kyu --list`,
  then the portal's form with `--rank=yellow` and with `--rank=jun3`, and
  `--rank=purple --json` (one `error`, listing the forms).
- **M-3 The error reads well.** The plain and `--json` messages for
  `-a kyu -r purple` and `-a dan -r yellow` say what was wrong and what is
  accepted, in one sentence or two a portal can show as it is.
- **M-4 The docs.** Read the new DECISIONS entry, the README sections and
  `docs/kyu-explained.md` for meaning and against the house style; the
  first mention of kyū and 準 glossed.
- **M-5 Linux.** `scripts/test-docker.sh`: the full suite with real
  renders, nothing skipped for want of a tool.

## Test changes (tests/acceptance, tests/regression)

Done in this PLAN, by the tester. They fail until the example has its
fourth award (or the version is 0.5.0), and are recorded here because they
change older items' contracts.

- **Why:** user decision 2 puts a `kyu` award in the example, and the
  default run and `--all` build every award of the configuration (AC-2),
  so every test that counted the example's three awards now counts four.
  - `test_ac_plain_white.py`: `AWARDS` gains `kyu`; AC-1's explicit list
    is `",".join(AWARDS)`; AC-4's total `3 * len(AWARDS)`; AC-6's totals
    in `len(AWARDS)`; AC-7's 18 → `len(AWARDS) * 3 * 2`.
  - `test_ac_plain_white.py` AC-9: the colour goes after every award's
    `grade_column` line, whatever its value (`\w+` did not match
    `"kyu"`), and the count is `len(AWARDS)`.
  - `test_ac_paper_format.py`: `AWARDS` gains `kyu`; AC-21's
    `_UNSIZED` also checks `kyu-…` names in the docs for a size.
  - `test_ac_cli.py` AC-17: 3 × 3 × 2 → 4 × 3 × 2.
  - `test_ac_json.py` AC-8 totals for `-a all`: 24/18 → 32/24, 9/9 → 12/12.
  - `test_ac_paths.py` AC-4 (×2), `test_ac_wheel.py` AC-3,
    `test_ac_remove_supersample.py` AC-6 (four text layers),
    `tests/regression/test_config.py` (slugs ×2).
- `tests/regression/golden_lib.py`: `baseline_awards_only()` and
  `run_case()` running every example case on a copy without the non-baseline
  awards (AC-14); `tests/README.md` says so. The manifest, `golden/svg/`
  and `pdf_sha256.json` are not regenerated.
- "Kyū grades" dropped from the Open items that
  `test_ac_house_style_sweep.py::test_ac12_open_item_closed` and
  `test_ac_render_without_inkscape.py::test_ac35_open_item_closed` require
  to remain (this item closes it, AC-16).
- `test_ac_render_without_inkscape.py`: `EXPECTED_VERSION = "0.5.0"`
  (OQ-9; reverted if the user decides another version).
- Found by running the older suite on a scratch copy whose example had a
  fourth award (`grade_column = true`): apart from the changes above,
  nothing else counts the example's awards. (In that copy
  `test_ac_paper_format.py::test_ac20_help_flags` also failed, an artefact
  of the copy's Python 3.12 venv formatting `-c PATH, --config PATH`; it
  passes on the checkout's 3.13.) Note for the developer: plain-white's
  AC-14 bans the string `k-only` anywhere outside the history, so a word
  such as `rank-only` in code or docs fails it.
- **IMPLEMENT round (2026-10-30): the developer found 11 failures, all
  in tests; each was checked by the tester, reproduced, and found to be the
  test's fault, so the contract stands and the tests change:**
  1. `test_ac_plain_white.py::test_ac9_colour_is_accepted_and_ignored`
     still counted 9 files for `--all -f svg`; now `len(AWARDS) * 3`
     (missed in PLAN).
  2. `test_ac_plain_white.py::test_ac9_an_award_has_no_colour` pinned
     `Award`'s fields to exactly four; OQ-1/OQ-2 add fields. It now pins
     the first four and that no field name holds `colo`.
  3. `test_ac1_help_lists_kyu` split on `-r GRADE, --rank GRADE`, the
     help format up to Python 3.12; 3.13 writes `-r, --rank GRADE`. Both
     are matched.
  4. `test_ac4_an_empty_precept_moves_nothing`: an empty motto column
     leaves an empty line in the SVG, as it always has (the `minimal.toml`
     goldens hold it), so blank lines are no longer compared.
  5. `test_ac5_renders_every_variant`: the narrowed crest box crossed the
     proof's safe-inset guide at y 38 mm. The box is now y 39–63 mm; the
     dan mon (y 38.7–61.3) still inks it. AC-5 updated.
  6. `test_ac11_licences_unchanged_by_false`: `printed_rank()` reads
     X_RANK ± 16 mm, where a licence's printed name sits (308 mm). The
     grade is now read with `-n ''`, and the named sheet is checked for
     the name column and no glyph at `SZ_RANK`.
- Developer deviations, accepted: a bad `[sample] rank` names its source
  (`[sample] rank 11: …`), while `--rank 11` on dan keeps its message
  word for word (AC-9). A fullwidth `５` is read as 5 on a dan award (as in
  0.4.0, `str.isdigit`) but is a literal on a kyū award (AC-7: non-ASCII
  after folding is a literal). Within the contract; reported to the user
  as a new finding, not in the contract.
- **After review round 1 (2026-10-30).** The user decided that full-width
  digits are numbers on a kyū award too (`５` → 五級, as on dan), which
  replaces the deviation accepted above; AC-7 says so. Review R-2 adds
  NFC normalisation before reading. New cases: `test_ac7_kyu_rank_forms`
  `５` → 五級, `１０` → 十級, decomposed `gokyū` and `GOKYŪ` → 五級;
  `test_ac9_dan_sheet_unchanged` decomposed `jūdan` → 十段 and `５` → 五段
  (the latter already 0.4.0's behaviour). Not added: `jun５`; the decision
  is about numbers, so `jun５` is outside the contract either way.
- `tests/regression/test_pure.py` calls `bd.rank_kanji(value)` with one
  argument and expects the dan behaviour; it stays as is (the developer
  keeps `rank_kanji(value, unit="dan", …)`, Agreement 8).

## Open questions

- **OQ-1 How an award declares its unit.** Recommendation: **`grade_column`
  takes `"dan"` or `"kyu"` as well as `true` (= `"dan"`) and `false`**
  (no grade column, as today; an explicit `--rank` on such an award reads
  in dan, as today). Case-insensitive like `[paper] size`; anything else
  is an error naming the file, the award, the key and the values (today
  any value is silently `bool()`-ed, so `grade_column = "kyu"` in a
  `dojo.toml` loaded by 0.4.0 would quietly be a dan award; that is
  acceptable, the portal builds its wheel from this checkout). The
  alternative, a separate `unit` key, would let `grade_column = false,
  unit = "kyu"` exist, which means nothing. Tests: `UNIT_KEY` in the test
  file.
- **OQ-2 How an award declares the simpler sheet.** Recommendation: **two
  per-award booleans, `crest = false` and `motto = false`, both `true` by
  default**, so every existing award and `dojo.toml` is unchanged and the
  example's `kyu` sets both. Alternatives: tie the sheet to the kyū unit
  (a dōjō could then never have a kyū sheet with its crest, or a licence
  without one), or one `sheet = "plain"` key (one switch for two things a
  dōjō may want apart). `crest = false` drops the mon, both rings and
  both arcs of lettering. Strict booleans: a string is an error. Tests:
  `CREST_KEY`, `MOTTO_KEY`.
- **OQ-3 The layout without crest and motto.** Recommendation: **the dan
  sheet's column positions, the crest's place and the motto's strip
  simply left empty.** The columns start at y ≈ 79 mm and the crest's
  outer ring ends at 69 mm, so the crest's absence is a band of white at
  the top centre, which is how a plain 賞状 looks; the motto strip was
  open margin before the motto existed (‘Purple menkyo, and a precept
  column’). One layout means one proof, one set of guides, no new
  constants, and a kyū sheet that reads as one of the set. The cost: the
  printed block spans x 78.75–361 mm, 59 mm from the right edge and
  79 mm from the left, about 10 mm right of centre (with the motto,
  51.5–361, balanced). If the user finds that lopsided at M-1, the
  alternative is **every column shifted left by 10 mm on a sheet without
  a motto** (heading 342, …, signatory 75), nothing else re-tuned; AC-4
  and AC-6 would then compare against the dan sheet shifted by 10 mm.
  Not raising the columns into the crest's band: `text_drop` already
  chose that air on purpose.
- **OQ-4 Forms of the other unit.** Recommendation: **refused.** A kyū-only
  form on a dan-unit award (`-a dan -r yellow`, `jun5`, `gokyu`) is an
  error naming the value and the award, instead of today's literal
  pass-through, which would print `yellow` in Latin letters on a dan
  sheet. Likewise a dan form on a kyū award (`-a kyu -r nidan`). Other
  ASCII on a dan-unit award still passes through as today (`Shihan`,
  pinned by `test_pure.py`). A mixed run (`-a dan,kyu -r yellow`) fails
  as a whole, before anything is written.
- **OQ-5 Where `kyu` goes in the example.** Recommendation: **after
  `renshi`**, so the three existing awards keep their order and `dan`
  stays first (the help's example uses the first slug). The default run
  of the example then writes four certificates. The user's own
  `dojo.toml` builds a kyū sheet only once it has a kyū award (the README
  says how); the portal passes `--awards` explicitly.
- **OQ-6 `[sample] rank` on a kyū sheet.** Recommendation: **the same
  value, read in each award's unit**, so the example's `5` is 五級 on the
  kyū sheet and 五段 on the dan sheet, and the default build shows a
  filled kyū sheet with no new key. A sample that is not a grade in an
  award's unit (OQ-4) is an error naming `[sample] rank`, as an explicit
  `--rank` would be. A separate `[sample] kyu_rank` was considered: one
  more key in a section meant to be deleted.
- **OQ-7 Exactly which spellings.** Recommendation:
  - numbers `1`–`10`; romaji `ikkyu nikyu sankyu yonkyu gokyu rokkyu
    nanakyu shichikyu hachikyu hakkyu kyukyu jukkyu jikkyu`, any case,
    with `ū` or `uu` for `u`;
  - colours in English only, any case, kids' steps joined by `-`
    (`white-yellow`); Dutch colour names (`geel`) are the portal's to
    map;
  - `jun5`, `jun4`, `jun3` and `jun-5` …, **only those three**: 準 exists
    for the kids' in-between belts and nowhere else, so `jun6` or `jun2`
    is a mistake, not a grade;
  - **not** `5kyu` / `5-kyu` (the error lists what is accepted);
  - a value with any non-ASCII character is a literal.
- **OQ-8 A recipient's explainer.** Recommendation: **yes,
  `docs/kyu-explained.md`**, written like the other three for the person
  who receives the sheet (often a child's parents here), by the docs
  agent: heading, formula, the grade and 準, the date, the authority; no
  crest or precept section, since the sheet has neither.
- **OQ-9 Version.** Recommendation: **0.5.0**: a new award in the example
  (the default build writes a fourth file) and new `--rank` behaviour
  (OQ-4 turns a former literal into an error). The portal's flags and
  events are unchanged.
- **OQ-10 The file-name tag.** Recommendation: **the `--rank` value as
  typed**, as for dan today (`-r 2` → `-2-`, not `-二段-`): `-r yellow` →
  `kyu-overlay-a3-yellow.pdf`, `-r white-yellow` → `…-white-yellow.pdf`.
  Two spellings of one grade give two names; that is how dan behaves now.
- **OQ-11 `--list` and a bad grade.** Recommendation: **checked first, as
  `-r 11` is today**: `--list -a kyu -r purple` is the error, nothing
  listed.
- **OQ-12 A three-character grade.** Not raised by the user, found while
  planning: the grade column is set at 30 mm per character, so 準五級
  (and any 3-character literal, dan sheet included) reaches 30 mm below
  the dan sheet's 二段, into the calligrapher's name zone (proof:
  `y 130–225`) when the name is left blank. Recommendation: **a grade
  longer than two characters shrinks to fit the two-character extent**,
  as a long name shrinks to `AWARDEE_MAX_H`; on every award, since it is
  the same column (no golden has a longer grade, so no golden changes).
  Tested on the kyū sheet only.

- **OQ-13 Folding on a dan award (from the developer, round 2).** The
  kyū forms fold `ū` and `uu` to `u` before reading (AC-7). Should a dan
  award do the same, so `jūdan` → 十段 and `kyūdan` → 九段, where 0.4.0
  prints `jūdan` in Latin letters? Recommendation: **yes**: nobody wants
  Latin on the sheet, and one reading rule for both units is simpler.
  `test_ac9_dan_sheet_unchanged` has the three cases; withdrawn if the
  user says no.

## Agreement

Round 2 (2026-10-29), developer and tester. The developer is ready to
build on the recommendations; OQ-3 is with the user (the contract assumes
option A until they answer), and OQ-13 is new and also the user's.

1. **AC-7 reading order.** Trim, fold `ū`/`Ū` → `u` and `uu` → `u`, then
   classify; "non-ASCII is a literal" applies after folding. Cases
   `GOKYŪ` and ` rokkyū ` added. Folding on dan: OQ-13 (recommended yes),
   three cases in `test_ac9_dan_sheet_unchanged`.
2. **AC-10, a sample on a licence.** Not drawn, so not read: `[sample]
   rank = "yellow"` with `-a shihan` works; `-a shihan -r yellow` is
   refused. `test_ac10_sample_not_drawn_not_validated`.
3. **OQ-3 option B, if chosen,** hangs off the award's `motto = false`,
   never off an empty `[motto] text` (else every dan sheet of a dōjō
   without a precept would move, and the `minimal.toml` golden breaks).
   Under B, AC-4's comparison, AC-6's guides and AC-5's motto/heading
   boxes compare against the dan sheet shifted 10 mm left (the crest box
   stays: it is empty either way). The tester prepares that variant when
   the user answers; A stays the default.
4. **OQ-12 rule pinned** (AC-4 above); `test_ac4_grade_stays_in_its_zone`
   now checks size and position exactly, on kyū, dan (`Shihan`, `2`) and
   a licence (`師範代`), with and without a name.
5. **OQ-4 detector on whole words.** `kyudan` and `kudan` stay dan forms
   (九段); added to `test_ac9_dan_sheet_unchanged`. The error names the
   award (already tested).
6. **AC-11 strictness and `save()`.** `1` and `"yes"` for `grade_column`
   are errors (added to `test_ac11_bad_unit_is_an_error`). `save()`
   writes `grade_column = "kyu"` only for kyū, `true`/`false` otherwise,
   and `crest`/`motto` only when `false`:
   `test_ac11_save_writes_new_keys_only_where_needed`.
7. **golden_lib.** `baseline_awards_only` drops from a non-baseline
   header to the next table header, so the ‘Stand-ins’ comment banner
   before `[sample]` goes too; harmless (comments), and `tests/README.md`
   now says exactly that.
8. **`test_pure.py`** unchanged: `rank_kanji(value, unit="dan", …)`
   keeps the one-argument calls.
9. **Lint traps, for the developer and docs:** plain-white's AC-14
   (`FORBIDDEN`, case-insensitive, outside DECISIONS, `docs/work/` and
   `.claude/`) bans `k-only` (so `rank-only`, `black-only`, `check-only`),
   `\bgs\b`, `\bcream\b`, `\bbought\b`; `FORBIDDEN_IN_SRC` bans
   `colour\s*=`, `.colour` and `'colour'` in `src/menkyo/*.py`: name the
   belt table `BELTS` / `belt`.

New totals: 192 tests in `test_ac_kyu_grades.py`, 17 of them passing
before the feature (dan behaviour that must not change).

## User approval (2026-10-29)

The user decided the open questions:

- **OQ-3: option B.** On an award with `motto = false` every column and
  the seal move 10 mm left, so the sheet is centred (about 69 mm each
  side). Keyed on the award's `motto` key only, never on an empty
  `[motto] text`; dan, shihan, renshi and the `minimal.toml` golden stay
  byte for byte. AC-4, AC-5 and AC-6 rewritten for it (above): the
  comparisons are against the dan sheet moved 10 mm left; the crest-box
  check stays, narrowed to x 192–220, y 31–63 mm because the moved
  formula (x from 223 mm, y from 64.85 mm) now reaches the old box's
  corner. New: `test_ac4_kyu_block_is_centred`,
  `test_ac4_an_empty_precept_moves_nothing`, the crest-stays-centred
  check in `test_ac11_sheet_keys_drive_the_sheet`.
- **OQ-13: yes.** `ū`/`uu` fold on a dan award too (`jūdan` → 十段); the
  cases stay in `test_ac9_dan_sheet_unchanged`.
- **All the others as recommended:** OQ-1 `grade_column` true/false/
  `"dan"`/`"kyu"`, strict; OQ-2 per-award `crest` and `motto` booleans;
  OQ-4 the other unit's forms refused; OQ-5 `kyu` after `renshi`, the
  example's default build writes four sheets; OQ-6 the sample read per
  award; OQ-7 the spellings listed; OQ-8 `docs/kyu-explained.md`; OQ-9
  version 0.5.0; OQ-10 the suffix as typed; OQ-11 checked before
  `--list`; OQ-12 shrink to fit on every award (rule in Agreement 4).

`test_ac_kyu_grades.py`: 194 tests, 17 passing before the feature.
