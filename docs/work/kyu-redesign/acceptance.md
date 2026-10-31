# kyu-redesign: acceptance

Item: the kyū certificate rebuilt as a horizontal A4 portrait sheet
(user-approved from mock-ups, 2026-10-30). Planned against `ec62ba5` (HEAD,
clean, 0.5.0). The approved mock:
`scratchpad/mock/kyu-a4-crest-C.png` (with the watermark crest) and
`kyu-a4-horizontal.png` (without), drawn by `scratchpad/mockscripts/mock.py`;
its positions and sizes are the reference (`MOCK` in the test file).

## User decisions (2026-10-30, not reopened here)

1. **A4 portrait, 210 × 297 mm, text in horizontal rows (yokogaki).** Every
   printed character in Noto Serif JP SemiBold (bundled, the crest's face),
   in #111111, with no sumi ink texture.
2. **Top to bottom:** 級位認定証, letter-spaced and centred; the recipient
   and 殿, centred; the grade (e.g. 準五級), prominent and letter-spaced; the
   body 上記の者は本会所定の審査に合格したので / ここに認定します; the date
   西暦…; the issuer block 〇〇流柔術 / 〇〇道場 / 師範　山田太郎, right of
   centre. The wording as mocked (本会) is fine.
3. **The crest as a watermark:** about 120 mm across, about 8 % grey,
   centred behind the body, drawn first so the text prints over it. Its
   grey is configurable; the docs note the print risk (a test print).
4. **It replaces the 0.5.0 vertical 'simpler sheet'** for kyū and closes
   the Open item 'A second brush font for the simpler sheet'. Config stays
   backwards compatible.
5. **Unchanged:** grade input, belts, kids' steps and rank parsing from
   0.5.0; grades longer than two characters are not shrunk horizontally;
   dan, shihan and renshi output byte for byte (goldens).
6. Context: dan certificates get a real hand stamp, so the generator never
   prints a seal. Not in scope.

## Scope

In (as amended by the user's approval, 2026-10-30, below):

- `src/menkyo/build_diploma.py`: the horizontal portrait sheet (a document
  function of its own beside `document()`) for every award counting in
  kyū, the watermark through `crest()`, the sheet per award (OQ-1), no ink
  on it, progress totals that follow, the glyph checks against the face
  each award prints in, `--paper` help; `NO_MOTTO_SHIFT` and the
  `motto_column` path removed.
- `src/menkyo/config.py`: `body` and `watermark` per award, validated
  (file, award, key) on every award; `formula` optional on a kyū award;
  `motto` removed (setting it is an error); `save()` writes `body` and
  `watermark` for a kyū award only, and no empty formula.
- `src/menkyo/example.toml`: the `kyu` award's new block and comments, the
  key legend without `motto`.
- README, DECISIONS (a new entry; the Open item closed),
  `docs/kyu-explained.md` (docs agent).
- `pyproject.toml`: 0.6.0.
- Tests: `tests/acceptance/test_ac_kyu_redesign.py` (new),
  `tests/acceptance/kyu_redesign/` (the 0.5.0 example and pins), and the
  older tests listed under 'Test changes'.

Out:

- Any change to what dan, shihan and renshi draw (goldens), `minimal.toml`
  (a dōjō without a precept) included.
- The 0.5.0 vertical kyū sheet: removed, not kept (user approval).
- A printed seal on any sheet (decision 6); a horizontal sheet for dan or
  the licences.
- The annotated Dutch companion sheet (its own Open item, later).
- New flags, `--json` events, fields or stage names.
- The portal.

## Acceptance criteria

Every run pins `-c src/menkyo/example.toml`, the 0.5.0 example kept in
`tests/acceptance/kyu_redesign/example-0.5.0.toml` (refused as it is, and
used without its kyū block), or a configuration the test writes (the installed wheel: its own `example.toml`); HOME and
XDG_CONFIG_HOME are isolated. 'The example' is `src/menkyo/example.toml` as
this item leaves it. 'The kyū sheet' (or 'horizontal sheet') is what an
award with `grade_column = "kyu"` draws; every other award is vertical. Positions are in the layout's millimetres (A4
portrait); `SAFE` is `safe_inset / √2` (26.87 mm), `BORDER` is
`border / √2` (15.56 mm).

### The award

- **AC-1 The example's kyū award.** Four awards as before (`dan`, `shihan`,
  `renshi`, `kyu`). `kyu`: heading 級位認定証, `grade_column = "kyu"`,
  `body` = the two approved lines, `watermark = 0.08`, the crest on; its
  block sets no `crest`, `motto`, `layout` or `formula`. The other three
  blocks are byte for byte 0.5.0's; outside the kyū block only comments may
  differ from 0.5.0's example. The key legend names `body` and `watermark`
  and no longer `motto` (nor `layout`); the kyū block's comments say
  horizontal, A4 portrait and watermark. `--example-config` prints the file
  byte for byte.
- **AC-2 The sheet's size, and the names (OQ-1, OQ-10).** A horizontal
  sheet is A4 portrait (root `210.0mm` × `297.0mm`, no wrapper) whatever
  `[paper] size` says; `--paper` applies to every award of the run, so
  `--paper a3` gives A3 portrait (297 × 420 mm, the same layout inside
  `<g transform="scale(1.4142135624)">`, the same text and crest inside it)
  and `--paper a4` A4. Names follow `<award>-<variant>-<size>[-<suffix>]`
  with the kyū sheet's own size:

  | run | files |
  |---|---|
  | (default) | `{dan,shihan,renshi}-overlay-a3-sample.pdf`, `kyu-overlay-a4-sample.pdf` |
  | `-a kyu`, `-a kyu --paper a4` | `kyu-overlay-a4-sample.pdf` |
  | `-a kyu --paper a3` (or `A3`) | `kyu-overlay-a3-sample.pdf` |
  | `-a kyu -r yellow -n ヤン・ヤンセン` | `kyu-overlay-a4-yellow-ヤン-ヤンセン.pdf` |
  | `-a kyu --suffix ''` | `kyu-overlay-a4.pdf` |
  | `-a dan,kyu -r 3` | `dan-overlay-a3-3.pdf`, `kyu-overlay-a4-3.pdf` |
  | `-a dan,kyu --paper a4` / `a3` | both `a4` / both `a3` |
  | `[paper] size = "a4"` or `"a3"`, `-a dan,kyu` | dan at that size, kyū `a4` |

  `--all` lists three variants per award, kyū at `a4`; `--list --json` the
  same as `planned` events. `--help` for `--paper` says portrait and names
  the kyū (or horizontal) sheet.

### The sheet

- **AC-3 What it prints, in what face.** Printed text, read as lines top to
  bottom (texts within 3 mm of each other's centre, left to right,
  whitespace and U+3000 dropped), with `-n ヤン・ヤンセン -r white-yellow
  -d 2026-09-05`: 級位認定証, ヤン・ヤンセン殿, 準五級, the two body lines,
  西暦二〇二六年九月五日, 〇〇流柔術, 〇〇道場, 師範山田太郎. Without fill-in
  flags the `[sample]` stand-ins (ジョン・ドウ殿, 五級). Every printed
  `<text>` is in the mincho family (`FONT_CREST`) and #111111, none in Yuji
  Boku, none with a transform (ー not turned, small kana not shifted), and
  the SVG has no `<image>`. **Blank slots (OQ-7):** `-n '' -r '' -d ''`
  prints the heading, the body, 西暦年月日, the art, the dōjō and the
  signatory line, no 殿; the blank date keeps room for four, two and three
  characters after 西暦, 年 and 月.
- **AC-4 Layout as mocked.** Each line's centre within 4 mm of the mock's
  (heading 58, name 104, grade 140, body 180 and 193, date 213, art 236,
  dōjō 249, signatory 264) and its size within 15 % (16, 11, 22, 7.4, 7.4,
  6.6, 8.2 mm); the grade larger than the heading, the heading than the
  name, the name than the body; at A4 and A3 alike. Heading, name line and
  grade centred within 1 mm; the heading letter-spaced (at least 1.25 ×
  its solid width), the grade too (1.1 ×). The body lines share a left
  edge, the date starts no further left; the issuer's three lines share a
  left edge and the block's centre is at least 5 mm right of the page's;
  office and name on one line with at least half a character between them.
  Every line lies inside the safe inset, filled, blank and with the longest
  date. **No shrink for a grade (decision 5):** 準五級, 十級 and 三級 are
  set at 五級's size and place, centred. **What must shrink does (OQ-9):**
  a long name (24 characters) and a body line too long for the width are
  set smaller, inside the safe inset, the name still centred. **Long issuer
  lines and headings (Agreement 1):** the issuer block keeps the mock's
  left edge unless its longest line plus the seal's room (about 20 mm,
  reserved on every variant) would cross the safe inset; then it moves
  left, and shrinks only if moving left would pass the centre; a heading of
  seven or more characters tightens its spacing before it shrinks. `text_drop`
  does not move the horizontal sheet.
- **AC-5 The watermark (OQ-4, OQ-5).** The crest drawn through `crest()`,
  before the first printed text: centre x 105 mm, centre y within 10 mm of
  168, outer radius 60 ± 5 mm; the rings, the mon and the ring lettering
  (the art and `crest_ring`) all in one grey, `round(255 × (1 − w))` for
  `watermark = w`: 0.08 (and no key) gives #ebebeb, 0.2 #cccccc, 0.05
  #f2f2f2, 1 #000000. `crest = false` draws none of it and changes nothing
  else. The kyū sheet never prints `[motto] text`.
- **AC-6 Variants (OQ-2).** `overlay` is the certificate, not inked;
  `overlay-flat` is the same drawing (identical SVG and PDF bytes); `proof`
  is the same text and crest plus the guides. No text layer, no `<image>`;
  `--no-ink` changes no byte. `-v all` writes all three.
- **AC-7 The proof's guides (OQ-8).** The border and the safe inset as
  rectangles at `BORDER` and `SAFE` from every edge (in layout mm, so on
  A3 they are 22 and 38 mm), in the dan proof's colours. The seal circle
  (#e4b9b9) on the proof only: right of the signatory's name and clear of
  it, its centre within 3 mm of that line's, radius 6–12 mm, inside the
  safe inset. The overlays have no guide and only the watermark's two
  circles. The calligrapher's zones (#e4b9b9, at least 30 mm wide,
  centred) for a blank name (covering y 104) and a blank grade (covering
  y 140), and nine date slots (narrower than 12 mm) on the date line, in
  the gaps, clear of 西暦, 年, 月, 日; a printed slot takes its guide away.
- **AC-8 It renders.** `-a kyu -v all -f pdf,png --dpi 50` at A4 and at A3:
  exit 0; `done` lists the six files; PDF pages 595.28 × 841.89 pt (A4) or
  841.89 × 1190.55 pt (A3) ± 0.01; PNGs at that size in pixels; the
  overlays' PNGs grey (`LA`: DeviceGray, no colour), the proof's `RGBA`;
  the overlay and overlay-flat PDFs byte for byte the same; the text (alpha
  > 160) inside the safe inset. The watermark prints light: at 0.08 at
  least 1500 mm² of pixels at the alpha that grey gives (± 6), with
  `crest = false` at most 400 mm²; at 0.2 at least 1500 mm² at its own.
  Every kyū grade form renders (準, 十, 一).
- **AC-9 Glyph checks follow the face (decision 1).** Before anything is
  written, what a horizontal sheet prints is checked against Noto Serif JP:
  the name and honorific, the grade, the date, the art, the dōjō, the
  signatory, the heading, the body (`the body of [[awards]] 'kyu'`), and
  with the crest on, `crest_ring` and the art on the ring. So: 𠮷 (only in
  Noto Serif JP) prints on the kyū sheet and is refused on dan naming Yuji
  Boku; 한 (in neither) and ⁄ U+2044 (in Yuji Boku only) in `--name` are
  refused on kyū naming Noto Serif JP, the code point and `--name`; 한 in
  the heading or body is one `error` event naming the source and the face,
  nothing written. Not drawn, not checked: `[motto] text` and the
  `formula` on a horizontal-only run (dan still checks the motto); the
  crest ring is checked unless the kyū award sets `crest = false`.

### Grades

- **AC-10 As in 0.5.0.** On the kyū sheet `5`, `gokyu`, `yellow`,
  `５` → 五級, `white-yellow` → 準五級, `jun3` and `orange-green` → 準三級,
  `10` → 十級, `brown` → 一級, `三級` as given; `purple` refused with 0.5.0's
  message; `-a dan,kyu -r 3` gives 三段 and 三級. **The unit decides the
  sheet (user approval):** the kyū block with `grade_column = true`,
  `"dan"` or `false` (and a formula) draws a vertical A3 landscape sheet in
  Yuji Boku with a solid crest.

### Configuration

- **AC-11 Keys and errors.**
  - There is no `layout` key: a `layout = …` line is an unknown key and is
    ignored, as `colour` is (it was never released), so the sheet is the
    same with `"vertical"`, `"horizontal"` or `"diagonal"`.
  - `motto` is removed: on any award, `true` or `false`, it is an error
    naming the file, the award and `motto` (and saying it was removed), also
    with `--list`, one `error` under `--json`. So the 0.5.0 example is
    refused, naming `motto` and `'kyu'`; its kyū block without the `motto`
    line prints the approved body, its `formula` ignored, and no watermark
    (its `crest = false` stands).
  - `crest` keeps its meaning on every award: on a vertical sheet no crest
    (as in 0.5.0), on the kyū sheet no watermark.
  - `body`: one to three strings, none empty or whitespace only (`" "`,
    U+3000); a string, `[]`, `[""]`, `[1]` or four lines is an error naming
    the file, the award and `body`. The lines print as given. Without
    `body` a kyū award prints the approved two lines (OQ-6).
  - `watermark`: a number, 0 < w ≤ 1, a bool refused, an integer `1`
    accepted; `"0.08"`, `true`, `0`, `-0.1`, `1.5` are errors naming the
    file, the award and `watermark`.
  - `body` and `watermark` are validated on a vertical award too, then
    ignored there.
  - `formula` is optional on a kyū award and ignored there; still required
    on any other (`missing 'formula'`). Since the unit decides that,
    `grade_column` is validated before a missing formula is reported: a
    kyū block without a formula and with `grade_column = "belt"` gets the
    `grade_column` error (kyu-grades' `test_ac11_bad_unit_is_an_error`,
    which the prototype failed for this reason).
  - `save()`: the example saves and loads back to equal awards and draws
    every award the same; the kyū block has `body` and `watermark` and no
    `formula`, `motto` or `layout`; the other blocks have none of these
    four keys. A configuration without a kyū award (0.5.0's example without
    its kyū block) saves to the bytes 0.5.0 wrote (pinned at `ec62ba5`).

### Unchanged

- **AC-12 `--json` and progress (OQ-11).** No new event, field or stage.
  A horizontal sheet has no `text` or `ink` stage: `-a kyu` (overlay, PDF)
  is exactly one `progress` (step 1 of 1, stage `pdf`, label
  `kyu overlay: writing the PDF`), one `file`, one `done`; `-a kyu -v all
  -f pdf,png` six steps, `pdf` and `png` per variant; the example's default
  run nine steps for dan, shihan and renshi plus `kyu`'s `pdf`, total 10.
- **AC-13 The landscape awards unchanged.** The regression goldens pass;
  dan, shihan and renshi draw from the new example exactly what they draw
  from 0.5.0's (every variant, filled, blank, sample, A4); kyu-grades'
  AC-14 (the example as it is still writes the goldens' files) passes.
- **AC-14 Installed wheel.** From a wheel installed outside the checkout:
  `--example-config` has `watermark = 0.08`; `--list` ends with
  `kyu-overlay-a4-sample.pdf`; the portal's form `--config=<its example>
  --awards=kyu --variants=overlay --formats=pdf,svg --name=ヤン・ヤンセン
  --rank=white-yellow --date=… --json` writes
  `~/Documents/Menkyo/kyu-overlay-a4-white-yellow-ヤン-ヤンセン.{pdf,svg}`,
  A4 portrait, with AC-3's lines; `--name=ヤン한` is one `error` naming
  Noto Serif JP.

### The record

- **AC-15 Docs.**
  - README: the `--paper` row says portrait for kyū; 'Configuring it for
    your dōjō' shows the kyū block with `body = [` and `watermark = 0.08`,
    and no `layout` or `motto` key anywhere;
    'Variants' says what kyū's overlay is; 'Printing' covers the watermark
    with a test print and portrait; 'How it looks the way it does' names
    Noto Serif JP for kyū; the glyph-check paragraph says kyū is checked
    against Noto Serif JP.
  - DECISIONS: exactly one new entry, last before `## Open`, its heading
    naming kyū, stating horizontal (or yokogaki), A4, portrait, Noto Serif
    JP, watermark, 8 %, `body`, `watermark`, the removed `motto`, 0.6.0,
    and naming by title what it overrides: ‘Kyū grades, on a simpler sheet’
    and ‘A4 as well as A3’. Every earlier block (preamble and 22 entries)
    byte for byte as at `ec62ba5`. Open: 'A second brush font for the
    simpler sheet' gone; 'Confirm the katakana transcription', 'An
    annotated version in Dutch' and 'A smaller footprint' kept.
  - `docs/kyu-explained.md`: the heading, both body lines, 準, the 'If you
    are adapting this document' blocks, the crest or watermark; not 右認定ス
    and not the precept.
  - The house-style lint passes on every in-scope file (existing tests).
- **AC-16 Version (OQ-12).** `pyproject.toml` 0.6.0; `menkyo --version`
  prints `menkyo 0.6.0`.

## Test approach per AC

Mostly in `tests/acceptance/test_ac_kyu_redesign.py` (97 tests, one of
them slow; 123 before review round 3); `render` marks real renders, `slow`
the wheel. Since round 3 (see 'Review round 3' below) some checks live in
another file, named in the table with its file (`kg` is
`test_ac_kyu_grades.py`).

| AC | test(s) |
|---|---|
| 1 | `test_ac1_example_kyu_award`, `test_ac1_only_the_kyu_block_changed`, `test_ac1_example_config_prints_it`, `test_ac1_example_comments` |
| 2 | `test_ac2_default_listing`, `test_ac2_names` (10), `test_ac2_paper_size_key_does_not_move_kyu`, `test_ac2_planned_events`, `test_ac2_a3_is_the_a4_layout_scaled` (A4 default and A3, sizes, the wrapper), `test_ac2_help_says_portrait`; explicit `--paper a4` page size in `test_ac8_renders_every_variant[a4]`; kg `test_ac2_default_and_all_include_kyu` (`-a all --paper a4`) |
| 3 | `test_ac3_lines_top_to_bottom`, `test_ac3_sample_sheet`, `test_ac3_mincho_ink_no_vertical_tricks`, `test_ac3_blank_slots` |
| 4 | `test_ac4_positions_and_sizes_as_mocked` (A4, A3: positions, sizes, centring, alignment, letter spacing), `test_ac4_inside_the_safe_area`, `test_ac4_a_long_grade_is_not_shrunk` (3), `test_ac4_a_long_name_shrinks_to_fit`, `test_ac4_a_long_body_line_shrinks_to_fit`, `test_ac4_a_long_issuer_line_stays_inside`, `test_ac4_a_long_heading_stays_inside`, `test_ac4_text_drop_does_not_move_it` |
| 5 | `test_ac5_watermark_behind_the_body`, `test_ac5_watermark_grey_is_configurable` (3), `test_ac5_watermark_default_without_the_key`, `test_ac5_crest_false_means_no_watermark`; the precept not printed: `test_ac3_lines_top_to_bottom` |
| 6 | `test_ac6_variants`, `test_ac6_no_text_layer_and_no_ink_flag_changes_nothing` |
| 7 | `test_ac7_margins` (A4, A3), `test_ac7_seal_circle_on_the_proof_only`, `test_ac7_calligrapher_zones` (4) |
| 8 | `test_ac8_renders_every_variant` (render, A4/A3; 準 in the grade, 十 and 一 in the date `2026-12-31`), `test_ac8_watermark_prints_light` (render) |
| 9 | `test_ac9_a_mincho_character_prints_on_kyu`, `test_ac9_name_checked_against_mincho` (2), `test_ac9_award_text_checked_against_mincho` (2), `test_ac9_what_the_sheet_draws_decides` |
| 10 | `test_ac10_each_award_its_unit`, `test_ac10_the_unit_decides_the_sheet` (3); the grade forms on the kyū sheet: kg `test_ac7_kyu_rank_forms` (every form in AC-10 among them); `purple`: kg `test_ac8_unknown_kyu_rank_names_the_forms[purple]` |
| 11 | `test_ac11_a_layout_key_is_ignored` (3), `test_ac11_motto_is_an_error` (4), `test_ac11_the_050_example_is_refused`, `test_ac11_a_050_kyu_block_without_motto`, `test_ac11_bad_body` (7), `test_ac11_bad_watermark` (5), `test_ac11_checked_on_a_vertical_award_too` (2), `test_ac11_body_lines_as_given`, `test_ac11_formula_optional_on_kyu_only`, `test_ac11_save_round_trip`, `test_ac11_save_without_a_kyu_award_unchanged`; `test_ac5_crest_false_means_no_watermark`; kg `test_ac11_bad_sheet_key_is_an_error` (crest), kg `test_ac11_bad_unit_is_an_error` (the order) |
| 12 | `test_ac12_json_events`; six steps of `-v all -f pdf,png` and the progress fields: `test_ac8_renders_every_variant`; the default run (ten steps): `test_ac_plain_white.py::test_ac4_default_run` |
| 13 | `test_ac13_the_landscape_awards_unchanged` (flat, `-v all`); `tests/regression/test_golden.py` (the inked overlay among them); kg `test_ac14_*` |
| 14 | `test_ac14_installed_wheel` (slow, render; the `purple` refusal too) |
| 15 | `test_ac15_readme`, `test_ac15_decisions_entry`, `test_ac15_history_unchanged`, `test_ac15_open_items`, `test_ac15_recipient_explainer`; `test_ac_house_style_sweep.py` |
| 16 | `test_ac_render_without_inkscape.py::test_ac37_version` (`EXPECTED_VERSION = "0.6.0"`) |

How the tests read the sheet: printed text is every `<text>` with
`fill="#111111"`, at its own `x`/`y` in layout mm (inside the A3 wrapper);
extents come from the font's advance widths (`render.face`) and the
`text-anchor`, as the PDF writer lays them out. The watermark is found as
`crest()` writes it (`<g transform="translate(…)">` then the outer
`<circle r=…>`). A developer who draws text differently (inside a
translated group, say) should raise it under Agreement.

The tests were checked against a throwaway prototype of this contract in a
scratch copy (not the developer's code, deleted with the scratchpad): with
every test change below, the full suite, slow tests included, ran 1120
passed and 10 failed, the ten being docs, `--help` and version (which the
prototype left alone) and `test_ac_paper_format.py::test_ac20_help_flags`,
the Python 3.12 help-format artefact kyu-grades already recorded (the
scratch venv was 3.12; the checkout's is 3.13). At `ec62ba5`, 15 of the 117
non-slow tests pass (the 0.5.0 pins, the landscape awards, the listings that
coincide, the `purple` message, a filled proof's absent zones) and 102 fail.

### Manual checks (VALIDATE)

- **M-1 Look at it.** `menkyo -c src/menkyo/example.toml -a kyu -v
  overlay,proof -f png --dpi 100 -d 2026-09-05 -n ヤン・ヤンセン -r
  white-yellow`, then with `-n '' -r '' -d ''`, then `--paper a3`. Put the
  overlay beside the approved mock (`kyu-a4-crest-C.png`): the same sheet,
  the watermark as light, the text crisp over it.
- **M-2 A test print, if the user can.** Print the A4 overlay at 100 % on
  the dōjō's printer: the watermark visible but quiet, no banding, the text
  on top black.
- **M-3 Installed wheel.** Build, install in a throwaway venv, from `/tmp`:
  `--list`, the portal's form with `--rank=jun3`, `--name=ヤン한 --json`.
- **M-4 Docs.** The new DECISIONS entry, README sections and
  `docs/kyu-explained.md` read for meaning and house style (the print risk
  of the watermark stated plainly).
- **M-5 Linux.** `scripts/test-docker.sh`: the full suite, renders run.

## Test changes (tests/acceptance, tests/regression)

Done by the tester in PLAN. Round 3 (user approval) replaced round 1's
approach, which kept the vertical kyū sheet and pointed kyu-grades at a
0.5.0 configuration.

- `tests/acceptance/kyu_redesign/example-0.5.0.toml`: the example at
  `ec62ba5` (placeholders only). Used as it is to show it is refused
  (`motto`), and without its kyū block as the reference for dan, shihan and
  renshi (AC-13) and for `save()` (AC-11).
- `tests/acceptance/kyu_redesign/pins-0.5.0.json`, computed at `ec62ba5`:
  sha256 of every DECISIONS block (AC-15) and of what `save()` writes for
  the 0.5.0 example without its kyū block (AC-11). Round 1's pins of the
  vertical kyū SVGs and of `save()` of the whole 0.5.0 example are gone,
  with the compatibility they pinned. No DECISIONS headings are stored: two
  older lints ban words that occur in them.
- **`test_ac_kyu_grades.py`** (the 0.5.0 contract), back on the shipped
  example (`EX`, `SHIPPED`):
  - Removed, because they pinned the vertical kyū sheet or the `motto` key
    (kyu-redesign covers the new sheet): `test_ac3_no_crest_no_ring_no_motto`,
    `test_ac3_keeps_the_core_text`, `test_ac3_blank_slots_stay_blank`,
    `test_ac4_same_columns_as_the_dan_sheet_moved_left`,
    `test_ac4_kyu_block_is_centred`, `test_ac5_renders_every_variant`,
    `test_ac5_inked_svg_has_no_crest`, `test_ac5_every_grade_form_renders`,
    `test_ac6_proof_guides`, `test_ac11_sheet_keys_drive_the_sheet`,
    `test_ac11_dojo_overrides_heading_and_formula`,
    `test_ac12_what_a_kyu_sheet_does_not_draw_is_not_checked`,
    `test_ac13_json_events`, `test_ac13_default_run_totals`, and their
    helpers (`SHIFT`, `_alpha_in`, the crest and motto boxes, `_guides`).
  - `printed_rank()` reads the grade off either sheet: the landscape
    column at `X_RANK`, or the kyū sheet's ink text larger than 18.5 mm
    (the grade, 22; the heading is 16). So AC-7, AC-9, AC-10 and AC-11's
    rank checks run unchanged on the new sheet.
  - `test_ac4_grade_stays_in_its_zone`: the dan and licence cases only.
    `test_ac4_an_empty_precept_moves_nothing` kept (no `motto` key
    involved). `test_ac10_sample_rank_cleared`: the proof zone check went
    (kyu-redesign AC-7).
  - AC-1: no `crest`/`motto = false` or formula on the shipped kyū block.
    AC-2: kyū names `a4` (`mudansha` in AC-11 too). AC-11: the kyū block
    turned dan also gets a formula; `test_ac11_bad_sheet_key_is_an_error`
    for `crest` only; `save()` no longer writes `crest`/`motto` for kyū.
    AC-12: 𠮷 is in Noto Serif JP, so the missing character is 한
    (U+D55C); the formula check went (not printed on kyū). AC-15 (wheel):
    the shipped example, `kyu-overlay-flat-a4-white-yellow`, A4 portrait.
    AC-16: no `crest`/`motto = false` in the README; the DECISIONS entry
    found by its heading; the explainer without 右認定ス. AC-17: 0.6.0.
- `test_ac_plain_white.py`: `size(award)` (`a4` for kyū), `INKED` and
  `stages(award)`; AC-1, AC-4, AC-5, AC-7, AC-20 name kyū `a4`; the default
  run is nine steps plus kyū's `pdf` (10); text layers for the inked awards
  only; AC-6 totals `--all -f pdf,png` 30 (was 32), `-f pdf,png,svg` 30
  steps and 39 files (was 32 and 40).
- `test_ac_json.py` AC-8: 30 steps (was 32). `test_ac_paper_format.py`
  AC-15: kyū PDFs A4 portrait. `test_ac_remove_supersample.py` AC-6: three
  text layers. `test_ac_wheel.py` AC-3: kyū `a4`.
  `test_ac_render_without_inkscape.py`: `EXPECTED_VERSION = "0.6.0"`.
- Nothing in `tests/regression/`: the goldens run on the example without
  kyū (`golden_lib.baseline_awards_only`, which strips a multi-line
  `body = [ … ]` too), and `minimal.toml` sets no `motto`, so removing the
  key and the shift leaves it byte for byte.
- Not mine to change: `tests/test_kyu.py` and the other developer tests
  outside `tests/acceptance/` and `tests/regression/`
  (`test_kyu.py` writes `crest = false` for a kyū award in `save()`; the
  developer adjusts it).
- Notes for the developer: plain-white's lint (`FORBIDDEN`, AC-14) bans,
  among others, `k-only`, `\bgs\b`, `\bcream\b`, `\bbought\b`, `drawn
  border`; `FORBIDDEN_IN_SRC` bans `colour =`, `.colour`, `'colour'` in
  `src/menkyo/*.py`. remove-supersample's AC-11 bans that item's flag name
  everywhere.

## Open questions

Each has a recommendation; the contract and the tests assume it until the
user says otherwise.

- **OQ-1 What `--paper` means for the kyū sheet.** Recommendation: **A4
  portrait by default; `[paper] size` does not apply to it; an explicit
  `--paper` applies to every award, so `--paper a3` gives A3 portrait (the
  A4 layout × √2).** The approved sheet is A4, while a dōjō's `[paper]
  size` (the example's is `a3`) is chosen for the landscape certificates,
  so following it would make every default kyū sheet A3. An explicit flag
  should never be ignored silently, and refusing it would break
  `-a all --paper a3`; scaling up costs one wrapper, the same mechanism as
  dan's A4. Names carry the real size (`kyu-overlay-a4-…` next to
  `dan-overlay-a3-…`). Cost: every listing of the example changes its kyū
  name from `a3` to `a4` (see 'Ripple').
- **OQ-2 Variants for kyū.** Recommendation: **all three stay;
  `overlay` is flat (no ink) and `overlay-flat` is the same drawing,
  identical bytes; `proof` adds the guides.** `--all` and `-v all` keep
  meaning every award × every variant, the portal's 0.5.0 call
  (`--variants=overlay-flat`) keeps working, and `--no-ink` does nothing on
  kyū. Omitting `overlay-flat` for kyū would make `-v overlay-flat -a kyu`
  an error or an empty run.
- **OQ-3 How an award declares the layout, and the 0.5.0 sheet.**
  Recommendation: **a per-award `layout = "vertical" | "horizontal"`,
  default vertical; the example's `kyu` sets horizontal.** A 0.5.0
  `dojo.toml` (kyū with `crest = false`, `motto = false`) keeps drawing the
  vertical simpler sheet byte for byte until it adds `layout =
  "horizontal"`; the README says so. Nothing breaks and nobody's printed
  stock changes without a decision. Alternative: `grade_column = "kyu"`
  implies horizontal; that ties layout to the unit, which 0.5.0 decided
  against for `crest`/`motto`, and silently changes an existing kyū
  configuration. Note for the user: a kyū award in your own `dojo.toml`
  needs `layout = "horizontal"` (and the portal nothing).
- **OQ-4 `crest` and `motto` on the horizontal sheet.** Recommendation:
  **`crest` switches the watermark (on by default); `motto` has no effect,
  since the horizontal sheet has no precept.** On a vertical award both
  mean what they meant in 0.5.0.
- **OQ-5 The watermark's grey.** Recommendation: **per award,
  `watermark = 0.08`, a fraction of black (0 < w ≤ 1), drawn as grey
  `round(255 × (1 − w))`** (0.08 → #ebebeb, the mock's). Per award because
  only the horizontal sheet has one and its other keys live there; `[dojo]`
  would suit a printer-wide setting, but there is one such sheet. The
  README's 'Printing' warns: a light grey may vanish, band or mottle on a
  home laser; make a test print and adjust. It is ignored on a vertical
  award (whose crest is solid).
- **OQ-6 The body text.** Recommendation: **`body = [ … ]` per award, one
  string per printed line, one to three lines; without it, the approved
  two lines (本会, as mocked).** The line breaks are the dōjō's, which
  Japanese needs (no word spaces to break at). `formula` is optional on a
  horizontal award and ignored there, so a 0.5.0 kyū block plus one line
  (`layout = "horizontal"`) gives the approved sheet. 本会 against 当道場:
  the user accepted 本会; a dōjō changes `body`.
- **OQ-7 Blank slots horizontally.** Recommendation: as on the dan sheet,
  **no name, no 殿**; a blank grade leaves its line empty; a blank date
  prints 西暦, 年, 月, 日 with room for 4, 2 and 3 characters. The proof
  shows each zone.
- **OQ-8 The seal circle.** Recommendation: **on the proof only**, as the
  dan sheet's: a dashed circle printed on the certificate reads as a form
  to fill in, and stamping is the dōjō's choice.
- **OQ-9 Long text.** Recommendation: **the grade is never shrunk** (every
  kyū form, 準五級 included, fits easily); a long name and a long body line
  shrink to fit the safe width; the name stays centred. A grade literal too
  wide for the sheet (seven or more characters) is not specified; the
  developer may shrink it to fit.
- **OQ-10 File names.** `kyu-<variant>-a4[-<suffix>].<ext>`, `a3` with
  `--paper a3`; the suffix rules unchanged.
- **OQ-11 `--json` and progress.** Unchanged events, fields and stage
  names; a horizontal sheet has no `text`/`ink` steps, so its totals are
  smaller (the default run 10, was 12). The portal reads `step / total` and
  should not notice.
- **OQ-12 Version.** Recommendation: **0.6.0**: the example's kyū
  certificate looks entirely different and is named `a4`.
- **OQ-13 The missing-glyph check.** Everything the horizontal sheet prints
  is checked against Noto Serif JP (it has 16,700 characters against Yuji
  Boku's 8,000, so a name that fails on dan may print on kyū: 𠮷). Not
  drawn, not checked: the precept and the formula. Stated, not open.
- **OQ-14 The annotated Dutch sheet.** A later item; nothing here.

## Agreement

Round 2 (2026-10-30), developer and tester, through the coordinator. The
developer builds on the recommendations once point 1 is in the contract
(it is). The user's approval of the open questions is pending.

1. **Long issuer lines (developer, must).** AC-4 checked only the example's
   issuer. A katakana signatory such as 師範　ジョン・スミス・ドウ (a
   placeholder) is about 106 mm and ran past 183.1 mm at the mock's left
   edge (the prototype ended at 202.6 mm). Rule added to AC-4: the block
   keeps the mock's left edge unless its longest line plus the seal's room
   (about 20 mm, reserved on every variant, so the proof's text equals the
   overlay's) would cross the safe inset; then it moves left, and shrinks
   only if moving left would pass the centre. A heading of seven or more
   characters tightens its letter spacing before shrinking. New tests:
   `test_ac4_a_long_issuer_line_stays_inside` (the three issuer lines share
   a left edge inside the inset, the proof's seal circle right of the
   signatory line and inside the inset, proof text == overlay text) and
   `test_ac4_a_long_heading_stays_inside` (級位認定証明書類 inside the
   inset, centred). Both fail on the prototype for that reason only.
2. **AC-2, implementation (developer):** `PAPERS`/`SCALE` stay the
   landscape tables (`tests/test_paper.py` pins them), a portrait pair
   beside them; the sheet is chosen per award in the `--list` and build
   loops; the `--paper` help keeps '(default: a3, from [paper] size…)' and
   puts the portrait/kyū clause outside the brackets. No contract change.
   Correction (VALIDATE, review R-1): as first written,
   `test_ac2_help_says_portrait` split on the first `--paper SIZE`, the
   usage line's, and so read the usage and description, not the option's
   help. It now splits on `\n  --paper SIZE` and reads only the option's
   own help line (`COLUMNS=1000`); the contract is unchanged.
3. **AC-5 / AC-11, `watermark`:** a bool is refused explicitly, an integer
   (`1`) is accepted (already tested: `true` refused, `1` → #000000). The
   README notes that from about 0.933 the ring is as dark as the text
   (#111111): for the docs agent, not tested.
4. **AC-10:** with `grade_column = false` the horizontal sheet may keep its
   fixed line positions, leaving a gap where the grade would be. Allowed.
   Correction (review round 3, R-10): no `test_ac10_without_a_grade_column`
   was written; after the user's approval a kyū block with `grade_column =
   false` draws the vertical sheet, which
   `test_ac10_the_unit_decides_the_sheet[false]` checks.
5. **AC-11, validation:** order slug, heading → `layout`
   (`a.get("layout", "vertical")`; `""` is an error) → `formula` required
   only on a vertical award. `body` and `watermark` are validated on a
   vertical award too, then ignored there (new:
   `test_ac11_checked_on_a_vertical_award_too`, with `layout = ""` as
   well). A whitespace-only body line (`" "`, U+3000) is an error (two cases
   added to `test_ac11_bad_body`). `save()` omits an empty formula on a
   horizontal award and always writes `body` and `watermark` there; the
   round trip test already covers it, and vertical blocks still get none
   of the three.
6. **OQ-6, body block placement (developer's call):** with one or three
   lines the block is centred on y 186.5 (two lines stay at 180 and 193;
   three clear the date). No test change: AC-4 pins the two-line example;
   other counts are checked only for content, the inset and the left edge.
7. **AC-15:** the new DECISIONS entry may also name ‘Rendered without
   Inkscape’ (`document()` is no longer the one description of the sheet)
   and ‘Calligraphic typeface’ (kyū is not set in the brush face) as
   overridden. For the docs agent; the test requires only the two titles it
   names.
8. **`test_ac20_help_flags`:** passes on the checkout's Python 3.13.18; the
   failure in the prototype run was the 3.12 venv's help format, as
   kyu-grades recorded.

`test_ac_kyu_redesign.py`: then about 125 tests (one slow; 123 as it
shipped for VALIDATE, 97 after review round 3). Against the prototype,
everything passed except docs, help, version and the four tests of points
1 and 5 that the prototype does not implement.

## User approval (2026-10-30)

Through the coordinator, the user decided:

- **OQ-1: yes.** The kyū sheet is A4 portrait by default whatever `[paper]
  size` says; an explicit `--paper` applies to every award (`--paper a3`:
  A3 portrait, × √2).
- **OQ-3: changed.** 'Drop the vertical kyū sheet, don't worry about
  backwards compatibility. Horizontal layout on portrait paper will be the
  only option for kyū.' So there is no `layout` key: an award with
  `grade_column = "kyu"` always draws the horizontal portrait sheet, a dan
  award or a licence always the vertical one. The 0.5.0 compatibility
  requirements are dropped (AC-11 rewritten; round 1's pins and the
  vertical kyū tests removed, see 'Test changes').
- **Approved as recommended:** OQ-2 (both variant names, one sheet; the
  proof with guides), OQ-5 (`watermark` per award, 0.08, the test-print
  note), OQ-6 (one to three body lines, default 本会 wording, the block
  centred on y 186.5), OQ-8 (seal circle on the proof only), OQ-9 and
  Agreement 1 (long lines: the issuer block moves left first), OQ-12
  (0.6.0), the rest as recommended.

Decided by the tester with the developer, as the user asked (recorded here;
the user may overrule):

- **`motto` and `NO_MOTTO_SHIFT` removed.** They existed only for the
  vertical kyū sheet. A dan award without a precept leaves the column empty,
  as before 0.5.0; `minimal.toml`'s goldens are unaffected (it never set
  the key). **A `motto` key is an error** naming the file, the award and
  the key, on any award: in 0.5.0 `motto = false` moved every column 10 mm,
  so ignoring it would silently move a dōjō's columns back. Compatibility
  is not required, and the message says what to delete.
- **`layout` is not special.** It was never released, so it is an unknown
  key, ignored like `colour` (plain-white's rule for unknown keys). Making
  it an error would be the only unreleased key with a message.
- **`crest` stays on every award.** On a vertical sheet `crest = false`
  still draws no crest (0.5.0's meaning, one branch, already there); on the
  kyū sheet it turns the watermark off.

Changed ACs: AC-1 (no `layout`, `motto`, `crest` or `formula` in the kyū
block; the legend without `motto`), AC-5 (the precept clause), AC-10 (the
unit decides the sheet), AC-11 (rewritten: no `layout`, `motto` an error,
`crest` everywhere, no 0.5.0 compatibility, `save()` of a configuration
without kyū pinned), AC-14 and AC-15 (no `layout` in the example and docs;
the DECISIONS entry names the removed `motto`). Scope and 'Test changes'
rewritten. The Open questions above are kept as they were asked; OQ-3 and
OQ-4 are superseded by this section, and 'horizontal award' there means a
kyū award.


## Review round 3 (2026-10-31): fewer, faster tests

Under the user's new rule (maximum coverage with the fewest tests), the
reviewer's round 3 asked for tests-only changes. No AC changed; every AC
stays covered, and the table above names where each check now lives.

- R-1: `test_ac13_the_landscape_awards_unchanged` compares `-v all
  --no-ink` trees, the 0.5.0 configuration written once. The inked overlay
  is the regression goldens' (`inked`, `inked-sample`, `inked-svg`), run on
  the example without kyū. `svgs()` takes `no_ink`.
- R-2, R-3: `test_ac12_default_run` dropped (it duplicated
  `test_ac_plain_white.py::test_ac4_default_run`); `test_ac12_totals`
  folded into `test_ac8_renders_every_variant`, which now runs with `-d
  2026-12-31` (十, 一) and `-r white-yellow` (準), so
  `test_ac8_every_grade_form_renders` went too.
- R-5: `test_ac10_grades_as_before` and `test_ac10_refused_as_before`
  dropped; kg's `test_ac7_kyu_rank_forms` and
  `test_ac8_unknown_kyu_rank_names_the_forms` read the grade off the kyū
  sheet and cover every form AC-10 lists.
- R-6: the `--rank=purple` refusal moved into `test_ac14_installed_wheel`;
  kg's `test_ac15_installed_wheel` dropped.
- R-7: a module-scoped `filled` fixture draws the FILLED A4 sheet once.
  `test_ac4_centred_and_aligned` and `test_ac4_letter_spaced_heading_and_grade`
  merged into `test_ac4_positions_and_sizes_as_mocked`, which so checks them
  at A3 as well; `test_ac2_sheet_and_scale` folded into
  `test_ac2_a3_is_the_a4_layout_scaled`; `test_ac4_a_long_grade_is_not_shrunk[5]`
  (五級 against itself) and `test_ac5_no_precept_on_the_horizontal_sheet`
  dropped (its motto precondition is in `test_ac3_lines_top_to_bottom`,
  whose exact lines already exclude the precept); the implied
  `texts_of(svg) == FILLED_LINES` in `test_ac5_crest_false_means_no_watermark`
  dropped.
- R-8: the value tables of AC-11 (`body`, `watermark`, `motto`, the
  missing dan `formula`) are checked in-process on `config.load()`'s
  message; the command line (a plain run and `--list`, one `error` under
  `--json`) keeps one case per key: `motto` in
  `test_ac11_the_050_example_is_refused`, `body` and `watermark` in
  `test_ac11_checked_on_a_vertical_award_too`.
- R-4 (kg, kept consistent; its paperwork is history and not edited):
  dropped `test_ac1_example_config_prints_it`, `test_ac2_planned_events`,
  six of nine `NAME_CASES` (kept the `-r white-yellow`, `-r 5` and
  `準五級` suffixes), the default and `--all` listings of
  `test_ac2_default_and_all_include_kyu` (kept `-a all --paper a4`),
  `test_ac9_mixed_run_each_in_its_unit`, `test_ac12_kyu_heading_checked_first`,
  `test_ac11_save_round_trip` (its blank `-r white-yellow` kyū comparison
  moved into this file's round trip, as a proof), `test_ac16_recipient_explainer`,
  `test_ac17_version`, and the DECISIONS pin in `test_ac16_decisions_entry`
  (the same 21 blocks as `test_ac_house_style_sweep.py::test_ac11_history_pinned`).
  This file's `test_ac16_version` dropped too: the version is checked once,
  in `test_ac_render_without_inkscape.py::test_ac37_version`.
  `test_ac15_history_unchanged` keeps its pin of 23 blocks, which covers two
  entries the sweep's pin does not.
- R-9: `tests/test_kyu.py` overlaps kept. R-10: counts, Agreement 4 and the
  table corrected; the unused `home` in `test_ac6_variants` gone.

`test_ac_kyu_redesign.py` 123 → 97 tests, `test_ac_kyu_grades.py` 156 → 142.
