# house-style-sweep: acceptance

Work item: restyle the existing docs to the house style in `~/dev/house-style`
and close the Open item ‘A house-style sweep of the existing docs’ (decided
by the user on 29 October 2026). The `docs` agent
([.claude/agents/docs.md](../../../.claude/agents/docs.md)) does the
editing.

Baseline: `3f025b9`, HEAD when the item was planned. ‘Before’ below means
that commit.

## User decisions (not reopened here)

- Files: `README.md`, `DECISIONS.md`, `tests/README.md`, `NOTICE` and
  `docs/*.md`. Not `docs/work/**`.
- Rules: British English (WRI-004), sentence-case headings (WRI-001), single
  quotation marks ‘…’ with double “…” inside (WRI-005), a spaced en dash
  ` – ` instead of an em dash (WRI-005), no serial comma unless it prevents
  ambiguity (WRI-006), dates spelled out day first in running text and ISO
  in headings, tables and file names (WRI-007), a Japanese term glossed at
  its first mention in each document (TRM-001), no hollow constructions
  (VOI-040 to VOI-042), one qualification per doubtful claim (CLM-001). The
  narrator rules (VOI-NL-\*, VOI-010 to VOI-019) do not apply.
- Facts, flags, figures, commands, paths, code spans, code blocks and quoted
  program output stay unchanged.
- The Open item is closed when the sweep is done.

## Scope

**In**

- Restyling the eight files above in full: punctuation, quotation marks,
  dashes, heading case, date format, spelling, glosses, and rewriting hollow
  or wordy sentences, DECISIONS.md history included (the user's Q-1).
- `DECISIONS.md` `## Open`: the house-style item removed, the rest restyled.
- Tests (tester): `tests/acceptance/house_style.py` (the lint and the history
  comparison), `tests/acceptance/test_ac_house_style_sweep.py`,
  `tests/acceptance/house_style_sweep/` (`pin_history.py`, `check_sweep.py`
  and, at validation, `decisions_history.sha256`), and the migration of four
  older history tests (AC-14).

**Out**

- Any change to code, comments, docstrings or `--help` text in `src/`,
  `src/menkyo/example.toml`, `pyproject.toml`, `uv.lock`, `LICENSE` and the
  OFL texts. The CLI keeps printing its em dashes (for example the epilog's
  ‘graded like sumi — the one to print’); the README paraphrases it in house
  style and does not quote it.
- `CLAUDE.md` and `.claude/` (the docs agent never edits CLAUDE.md; see Q-7).
- `docs/work/**`, including earlier items' paperwork.
- `tests/regression/**`, the goldens above all.
- New content: no new section, entry or explanation beyond a gloss. No
  splitting or merging of paragraphs for WRI-002 (Q-8).
- A new DECISIONS.md entry for the sweep (Q-4).

## How history stays protected

Four acceptance tests compare DECISIONS.md byte for byte with an old commit
(`test_ac_cli_only.py` AC-11, `test_ac_plain_white.py` AC-16,
`test_ac_render_without_inkscape.py` AC-35, and `test_ac_remove_supersample.py`
AC-10 by heading). The user chose a full restyle of the history (Q-1), so
neither byte for byte nor word for word can hold across the sweep. Three
layers replace them:

1. **The facts survive, entry by entry** (`house_style.history_problems`).
   The preamble and every entry keep their place, their count and their
   dated heading (case and dash aside). Within each block these must come
   back as the same multiset: every number (dates folded, so ‘29 October
   2026’ is `2026-10-29`), every code span (whitespace collapsed, so a span
   rewrapped over a line break is the same), every link target, and every
   quotation of a title (an entry heading or a bold item title, by its
   opening words) or of program output (‘unknown variant’, ‘unrecognized
   arguments’). Every run of kanji or kana comes back too, in the same
   order (runs may be added: a gloss can bring 弐 or 大字). A bold item title
   that a quotation anywhere in the log refers to keeps its words. Nothing may state a new decision: no more
   top-level bullets or bold-led paragraphs than before, and an entry grows
   by at most 15 % plus 25 words (room for glosses). Edits an item's
   contract allowed after the fact are listed once, in
   `house_style.HISTORY_EDITS` (slug, the commit that made the edit, and
   the region). A comparison sets a region aside only against a baseline
   from before that commit (`git merge-base --is-ancestor`; without git, all
   of them); against a later baseline the region is compared like the rest.
   Today that is remove-supersample's reworded bullets, made in `8509b85`.
2. **Meaning, read by hand** (M-2): the tester at validation, and the
   reviewer, read every entry old against new and list any whose meaning
   shifted. That list must be empty before pinning.
3. **Byte for byte from the sweep on** (`decisions_history.sha256`). After
   the M-2 read, the tester pins the sha256 of the preamble and of each of
   the 20 entries. `test_ac11_history_pinned` holds them from then on, with
   or without git, so the Docker run checks history too (today the history
   tests skip there). A later item that may change an old entry says so in
   its acceptance.md, adds a line to `HISTORY_EDITS`, and the tester re-pins
   with `pin_history.py --allow <block>`; the script prints which blocks
   changed and refuses any block not named.

Layer 3 is the strong one. The git-based comparisons (layer 1, in this
item's AC-10 and in the four older tests) are kept while they cost nothing;
the first time one of them has to change, it may be retired in favour of
the pin, recorded in that item's acceptance.md.

## Acceptance criteria

The lint checks prose only. Fenced and indented code blocks, inline code
spans, HTML tags and link targets are skipped, so what a program prints or a
TOML or shell example contains is never reported. The lint runs on every
later change too.

**AC-1 No em dash.** No em dash (U+2014) outside code in any in-scope file.
Code keeps its dashes: the README's TOML example keeps `— see "Printing"` and
`— see "Where the columns start"` in its comments. A code span may run over a
line break; the lint reads it as code (DECISIONS.md has two, at
‘`[art]` / `name`’ and ‘`inkscape fontconfig` / `fonts-noto-cjk-extra`’).
The docs agent does not rewrap a line that carries a code span unless the
sentence itself changes.

**AC-2 Quotation marks.** No straight double quote in prose and no straight
single quote used as a quotation mark (an apostrophe inside a word, as in
dōjō's, is not one; see Q-3). Curly double quotes “…” appear only inside a
pair of single quotes ‘…’.

**AC-3 Sentence-case headings.** In every heading, a capital letter appears
only on the first word, the first word after a ` – ` separator or a colon, a
proper noun from the lint's list (Inkscape, Yuji Boku, Noto Serif, Japanese,
Dutch and so on), an acronym or code. The three recipient pages' titles
(today ‘Dan Rank Certificate’, ‘Shihan Teaching Licence’, ‘Renshi Teaching
Licence’) are in sentence case.

**AC-4 No serial comma.** The six serial commas found at planning are gone:

| file | text |
|---|---|
| README.md | ‘checked against Japanese practice, and are printed’ |
| README.md | ‘bump it, commit, and build’ |
| DECISIONS.md | ‘its teachers, or the certificate’ |
| DECISIONS.md | ‘peacock eye-feathers, and a chain’ |
| DECISIONS.md | ‘outside the checkout, renders, and checks’ |
| tests/README.md | ‘the set of files written, and the’ |

Every other candidate the heuristic reports is either a comma between
clauses or a serial comma kept because it prevents ambiguity, with the
reason in validation.md. (Candidates that may qualify: DECISIONS.md's list
of overridden entries in ‘Plain white paper only’, whose items contain
‘and’, and the list of what a fresh clone printed in ‘The default build
fills every slot’.)

Not serial commas, and they stay: the commas inside the entry titles
‘Output, and the supersampling cap’ and ‘Purple menkyo, and a precept
column’, wherever those titles are written or quoted (DECISIONS.md headings
and the quotations of them in ‘Plain white paper only’, ‘Supersampling
removed’ and ‘Rendered without Inkscape’).

**AC-5 Dates.** No ISO date in running text (the two in DECISIONS.md today:
‘see "Supersampling removed", 2026-10-29’ and ‘(asked 2026-10-28)’). No date
in running text written other than day first (‘the 5th of September, 2026’
in the three recipient pages). Every DECISIONS.md entry heading stays
`## YYYY-MM-DD – Title`, with an en dash.

**AC-6 British English.** None of the lint's American spellings (‑ize and
‑ization, color, gray, center, behavior, toward and others) outside code and
outside quotation marks. Quoted program output keeps the program's spelling
(AC-13).

**AC-7 Glosses.** In each in-scope file, the first prose mention of each
Japanese term has a short English gloss in one of TRM-001's three forms
(parentheses, in the sentence, or a defining sentence), and later mentions
in the same file do not repeat it. Which terms count is Q-2. A gloss never
goes into a heading, a bold item title or a quoted title; it goes into the
body where the term first appears there (for example shodan in the ‘Kyū
grades’ Open item gets its gloss in the item's sentence, not in its bold
title).

**AC-8 No hollow constructions.** No hollow ‘not X, but Y’ (VOI-040), filler
transition, fake balance, grandeur word construction, ‘it is important to
note that’, filler triad or stacked hedge (VOI-041) in the in-scope files,
and a doubtful claim is qualified once (CLM-001). Constructions are hunted,
not single words (VOI-042). This includes DECISIONS.md history (Q-1).

**AC-9 Facts unchanged.** For README.md, tests/README.md, NOTICE and
docs/\*.md, against before: every code block byte for byte and in order; the
same inline code spans; the same numbers in the prose (dates folded to ISO);
the same link targets, images and HTML tags; the same table shapes and the
code spans in each row; every run of kanji or kana in the prose, in the same
order (runs may be added). Any reworded sentence keeps its meaning (manual
review of the rewording report).

**AC-10 DECISIONS.md history keeps its facts and its meaning.** The
preamble and every entry up to and including ‘Rendered without Inkscape’
pass layer 1 above against before: the same blocks in the same order with
the same dated headings; per block the same numbers, dates, code spans,
links, quoted titles and quoted program output, and every run of kanji or
kana in order; referenced bold item titles
word for word; no new decision; bounded growth. And the M-2 read finds no
entry whose meaning shifted (layer 2).

**AC-11 History pinned.** `tests/acceptance/house_style_sweep/decisions_history.sha256`
holds the sha256 of the 21 blocks (the preamble and 20 entries;
`house_style.PINNED_BLOCKS`) as the sweep left them, and DECISIONS.md
matches it byte for byte. The tester writes it at validation with
`pin_history.py`. The file holds no text, so the scans for removed names in
other items' tests do not see it. Until then `test_ac11_history_pinned` is
red by design: the docs agent's hand-off cannot be fully green, and that one
failure is expected there (every other test must pass).

**AC-12 Open item closed.** `## Open` has no house-style item. The other
Open items are the same items in the same order, each keeping its numbers,
dates, code spans and links, and their meaning (M-2).

**AC-13 Text other tests and programs depend on is kept.**

- README `##` headings: Quick start, As a package, Configuring it for your
  dōjō, Options, Variants, Filling the document in, Printing, How it looks
  the way it does, Layout, Writing for the recipient, Licence.
- README `###` heading: Where the columns start (the TOML example's comment
  points to it).
- DECISIONS.md entry titles other tests look up: ‘Printing the three hand
  slots’, ‘Output, and the supersampling cap’, ‘Purple menkyo, and a precept
  column’, ‘The command is the product’, ‘Plain white paper only’, ‘The ink
  pass grades the alpha alone’, ‘Rendered without Inkscape’.
- The titles ‘Rendered without Inkscape’ quotes and
  `test_ac35_decisions_entry` looks for: ‘The font is vendored’, ‘Output, and
  the supersampling cap’, ‘Installed-copy behaviour’, ‘Packaging is tested by
  rendering’; and the bold item titles they quote, unchanged.
- The Open items other tests find by how they start
  (`test_ac35_open_item_closed`, `test_ac16_open_items_retired`): ‘Paper
  format’, ‘Kyū grades’, ‘An annotated version in Dutch’.
- Program output quoted in prose keeps its wording and spelling inside the
  new quotation marks: ‘unrecognized arguments’ and ‘unknown variant’ in
  DECISIONS.md.
- Every phrase other acceptance tests look for still passes them (for
  example ‘version’ and `pyproject.toml` on one README line, the `stage` line
  beginning ‘`stage` is one of’, the `-v` row's ``(default: `overlay`)``, ‘Noto Serif JP’ in
  NOTICE and README, `823af58`, `render_without_inkscape` and `--ref` in
  tests/README.md).

**AC-14 Older history tests migrated.** Their byte-for-byte history checks
use `house_style.history_problems` (the facts-preserving comparison of
layer 1, against their own baseline commits), their own copies of the
reworded-bullets exception are gone in favour of `HISTORY_EDITS`, and their
heading lookups accept either dash (see ‘Changes to the existing suite’).
They pass before the sweep and after it.

**AC-15 Nothing else changes.** Against before, the only changed or new
files are the eight in-scope files, `tests/acceptance/**` and
`docs/work/house-style-sweep/**`. `src/`, `tests/regression/` (goldens
included), `pyproject.toml`, `uv.lock`, `CLAUDE.md`, `.claude/`, `LICENSE`
and other items' `docs/work/` are untouched. The version stays 0.3.0.

**AC-16 Markup intact.** In every in-scope file: code fences balanced, every
table's rows have its header's cell count, backticks paired within each
paragraph, every relative link and image resolves. The README still opens
with `# menkyo-menjo-builder `, keeps its `> [!NOTE]` block and the
`docs/three_up.png` image.

**AC-17 Suite and wheel.** `uv run pytest` and `scripts/test-docker.sh` pass,
render tests running and not skipping in Docker. The wheel builds, installs
into a throwaway venv and runs from outside the checkout with
`-c src/menkyo/example.toml`, and `menkyo --help` prints the same bytes as
before.

## Test approach

| AC | how |
|---|---|
| AC-1 | `test_ac_house_style_sweep.py::test_ac1_no_em_dash[<file>]`, `test_ac1_code_keeps_its_dashes` |
| AC-2 | `test_ac2_quotation_marks[<file>]`, `test_ac2_lint_cases` (emphasis before a possessive, nested quotes, a code span over a line break) |
| AC-3 | `test_ac3_headings_in_sentence_case[<file>]`, `test_ac3_lint_catches_title_case` (the check is not vacuous) |
| AC-4 | `test_ac4_known_serial_commas_gone[<file>]`; manual M-4 for the other candidates |
| AC-5 | `test_ac5_dates[<file>]`, `test_ac5_headings_keep_iso_dates` |
| AC-6 | `test_ac6_british_spelling[<file>]`, `test_ac6_lint_cases` (honorary, maize, resizing, greyscale pass; grayscale, practiced, toward fail) |
| AC-7 | manual M-1; `test_ac7_first_mentions_case_insensitive` for the report |
| AC-8 | manual M-2 |
| AC-9 | `check_sweep.py` (M-3), and the rewording report read in M-2 |
| AC-10 | `test_ac10_decisions_history_keeps_its_facts` (git), `test_ac10_comparison_accepts_a_full_restyle`, `test_ac10_comparison_is_not_vacuous[…]` (a number changed, dropped or added; a code span changed or dropped; a link; a referenced bold title; a quotation of a title; quoted program output; a dated heading's date or title; a new bullet; runaway growth), `test_ac10_an_entry_dropped_or_reordered_fails`; manual M-2 for meaning |
| AC-11 | `test_ac11_history_pinned` (also in Docker) |
| AC-12 | `test_ac12_open_item_closed`; the rest of the Open list in `check_sweep.py` (M-3) |
| AC-13 | `test_ac13_readme_sections_kept`, `test_ac13_quoted_program_output_kept`, `test_ac13_decisions_headings_other_tests_find`, `test_ac13_titles_quoted_by_the_renderer_entry`, `test_ac12_open_item_closed`, and the rest of the suite |
| AC-14 | the migrated tests themselves (listed below), `test_ac14_history_edits_registry` |
| AC-15 | `check_sweep.py` (M-3) |
| AC-16 | `test_ac16_markup_intact[<file>]`, `test_ac16_readme_note_and_image` |
| AC-17 | manual M-5 |

AC-9, AC-12's second half and AC-15 compare with `3f025b9`, which later
items move on from (a new flag changes the README's code spans), so they run
as a one-off script at validation and not in the permanent suite.
`check_sweep.py` and `pin_history.py` are not collected by pytest.

### Manual checks

- **M-1 (AC-7).** `uv run python tests/acceptance/house_style.py --terms`
  prints the first prose mention of each term per file. For each, check
  there is a gloss in that file's first mention and none repeated later. A
  term first met in a heading or a table is glossed at its first prose
  mention, or in the table itself (the recipient pages' tables are glosses).
- **M-2 (AC-8, AC-9, AC-10, AC-12).** Read `git diff --word-diff 3f025b9 --
  README.md tests/README.md NOTICE docs/*.md` and the ‘rewording’ part of
  `check_sweep.py`'s output: every reworded phrase keeps its facts and
  claims; no construction from VOI-040 or VOI-041 remains; CLM-001 holds.
  Then DECISIONS.md, entry by entry: put each old entry (`git show
  3f025b9:DECISIONS.md`) beside the new one and read both in full. For each,
  record in validation.md ‘same meaning’ or what shifted: a claim weakened
  or strengthened (never, always, only, about), a reason dropped or changed,
  a cause turned into a correlation, an alternative or caveat lost, a
  measurement's conditions lost, a gloss that is wrong, a quotation around
  the wrong words. Any shift is a FAIL of AC-10 (AC-12 for an Open item).
  The reviewer does the same read independently.
- **M-3 (AC-9, AC-12, AC-15).** `uv run python
  tests/acceptance/house_style_sweep/check_sweep.py` exits 0.
- **M-4 (AC-4).** In the same output, every serial-comma candidate is a
  comma between clauses or a serial comma that prevents ambiguity; list the
  kept ones with the reason in validation.md. Also skim for serial commas
  the heuristic cannot see (an item longer than 40 characters).
- **M-5 (AC-17).** `uv run pytest`, `scripts/test-docker.sh` (render tests
  run), `uv build --wheel`, install the wheel into a throwaway venv, then
  from a directory outside the checkout with `HOME` and `XDG_CONFIG_HOME`
  pointed at a temporary directory: `menkyo --version` prints `menkyo
  0.3.0`, and `menkyo -c <checkout>/src/menkyo/example.toml --list` lists
  the default build. `menkyo -c src/menkyo/example.toml --help` from the
  checkout matches the output at `3f025b9` (`git archive` into a temporary
  directory, never a checkout switch).
- **Pinning (AC-11).** When AC-10's test passes and the M-2 read lists no
  shift: `uv run python
  tests/acceptance/house_style_sweep/pin_history.py`, then the suite again.
  If a fix round touches DECISIONS.md history after that, re-pin with
  `--allow` for each changed block, which the script lists.

## Changes to the existing suite

Made by the tester at planning; each passes before and after the sweep.
After the user's Q-1 they keep their structure: `history_problems` itself
changed from word for word to facts-preserving, so they now check that
their baseline's history kept its facts. They are not retired: they cost
nothing while they pass, and they cover baselines the pin does not.

- `test_ac_cli_only.py`: AC-11 compares the history at `90e5799` through
  `house_style.history_problems`, and finds its entry by heading with either
  dash. Its `_REWORDED_BULLETS` and `_without_reworded_bullets` are gone:
  `HISTORY_EDITS` sets that region aside for every comparison.
- `test_ac_plain_white.py`: AC-16 the same against `823af58`; the entries
  after the baseline are found by block count, not by string prefix. Its
  copy of the reworded-bullets exception is gone as above.
- `test_ac_render_without_inkscape.py`: AC-35 compares the history at
  `8509b85` through `history_problems`, and matches earlier headings with the
  dash normalised. `test_ac35_open_item_closed` no longer requires the
  house-style item it added to the Open list: this item closes it (AC-12).
- `test_ac_remove_supersample.py`: `_sections` reads the dash after an
  entry's date as an en dash, and `INK_PASS` uses the en dash.

## Test changes

### Review round 1 (29 October 2026)

The review (`review.md`) found five gaps in the tooling; all fixed by the
tester. The sweep's text was not involved.

- **R-1.** `HISTORY_EDITS` entries carry the commit that made the edit
  (`8509b85`), and `history_problems(..., baseline=)` sets a region aside
  only when the baseline predates it (`house_style.edits_before`). Every
  git-based caller passes its baseline: this item's AC-10 (`3f025b9`) and
  render-without-inkscape's AC-35 (`8509b85`) now compare the reworded
  bullets; cli-only (`90e5799`) and plain-white (`823af58`) still set them
  aside. New test `test_ac10_history_edits_follow_the_baseline` changes a
  number inside the region and expects a failure against `3f025b9`.
- **R-2.** Kanji and kana are facts: `entry_facts` and `facts()` carry the
  runs of Japanese characters in order, and `cjk_lost` requires the old runs
  to come back as an ordered subsequence (a gloss may add runs). The order
  matters because swapping 初段 and 一段 keeps the multiset. `check_sweep.py`
  applies it to README.md, tests/README.md, NOTICE, docs/\*.md and the Open
  items. New test `test_ac10_kanji_are_facts` (a swap, a replaced run and a
  dropped run fail; an added 和暦 passes; a changed date in `facts()` is
  reported).
- **R-3.** The rewording report tokenises prose only (`house_style.prose_text`
  strips fenced and indented code blocks), so backticks no longer pair across
  a fence. `facts()` shares the same splitter (`split_code`).
- **R-4.** The docstrings of the older history tests describe the
  facts-preserving comparison, not ‘word for word’.
- **R-5.** `pin_history.py` checks the history against `3f025b9` with
  `history_problems` first and refuses to pin if a fact was lost (a warning
  without git); for each changed block it names the `HISTORY_EDITS` entries
  that cover it.

### Review round 2 (29 October 2026)

- **R-9.** `cjk_lost`'s out-of-order branch indexed past the end of `now`
  when the swapped runs came last (`['A', 'B']` against `['B', 'A']`), so a
  swap of ‘〇〇道場 and 師範’ in ‘The default build fills every slot’ raised
  instead of being reported, and `check_sweep.py` and `pin_history.py`
  crashed. It now walks `now` once with a bounds check and reports the
  first run that no longer comes in order. `test_ac10_kanji_are_facts`
  covers `[A, B]` → `[B, A]`, `[A, B, C]` → `[A, C, B]`, runs added in
  between and a run lost.

### Validation round 1 (29 October 2026)

- `test_ac_house_style_sweep.py`'s `_git` called `git` unguarded, so
  `test_ac10_history_edits_follow_the_baseline` failed in the Docker image
  (no git there) instead of skipping. It now returns None without git or
  `.git`, like the older tests' helpers.
- The pin was written (`decisions_history.sha256`, 21 blocks) after the M-2
  read found no shift.

## Open questions

- **Q-1. Rewording inside DECISIONS.md history.** Decided by the user: a
  full restyle (see ‘User approval’). My recommendation had been mechanical
  changes and glosses only.
- **Q-2. Which Japanese terms need a gloss.** Recommendation: every
  romanised Japanese term and every kanji word in prose, at its first
  mention per file, except four that English dictionaries carry and every
  reader of this repository knows: dōjō, dan, kanji, katakana. So mon,
  kamon, yotsume-bishi, sumi, kaisho, mincho, kasure, romaji, menkyo,
  menjō, shihan, renshi, shodan, kyū, dono, seireki, jūjutsu, ryū, 賞状,
  西暦, 殿, 大字 and 〇〇 are glossed. A kanji string quoted as output (二段,
  西暦二〇二六年九月五日) needs a gloss only where the sentence does not
  already give its meaning. In the three recipient pages the tables are the
  glosses: 免状 menjō, 西暦 seireki, 流 ryū, 柔術 jūjutsu, 道場 dōjō and 師範
  shihan each have a row with the reading and meaning, and 殿 dono is glossed
  in the sentence that introduces it. A term the page meets in prose before
  its table row (for example dan in ‘This certificate records a dan grade’,
  or mon in the crest section) still needs one there.
- **Q-3. Apostrophes.** Recommendation: they stay straight (`'`). WRI-005
  governs quotation marks; the docs mix code and prose, and a curly
  apostrophe would touch hundreds of lines for no reader. The lint accepts
  either.
- **Q-4. A DECISIONS.md entry for the sweep.** Recommendation: none. The
  item changes no design; closing the Open item and the commit message
  record it. (An entry would also be the first one not about the
  certificates or the generator.)
- **Q-5. The README's AI-authorship note.** Recommendation: punctuation and
  serial comma only (AC-4 includes one there); its wording is a statement
  the user made deliberately (DECISIONS.md, ‘Made publishable’).
- **Q-6. Translated titles in the recipient pages.** ‘**Reads as:** *Dan
  Rank Certificate.*’ renders a title, not a heading. Recommendation:
  sentence case there too, matching the heading. Not tested.
- **Q-7. CLAUDE.md (resolved).** It was updated in `27e904d` and no longer
  names Inkscape; neither do the agents in `.claude/agents/`. Nothing to do.
- **Q-8. WRI-002 (one idea per paragraph).** Not in the item's rule list.
  Recommendation: no paragraph is split or merged in this sweep.
- **Q-9. ‘toward’.** Recommendation: ‘towards’ (the British form); the lint
  reports ‘toward’ and ‘afterward’.

## User approval (2026-10-29)

The user approved the plan on 29 October 2026 with one change.

- **Q-1: full restyle of DECISIONS.md history.** Hollow or wordy sentences in
  old entries may be rewritten, not only mechanically restyled. The contract
  changed accordingly: AC-10's word-for-word comparison became the
  facts-preserving comparison of ‘How history stays protected’, layer 1;
  meaning is checked by hand, entry by entry (M-2, the tester and the
  reviewer); the pin (AC-11) is written after that read; `HISTORY_EDITS`
  stays for later items. The four older history tests call the same
  comparison against their baselines and are kept, not retired. AC-12's
  Open check is facts-based as well (`check_sweep.py`). The non-vacuity
  tests now check that a dropped, changed or added number, code span, link,
  quoted title, referenced bold title, dated heading or entry fails, and that
  a full restyle with a rewritten sentence passes.
- **Q-2, Q-3, Q-4, Q-5, Q-6, Q-8, Q-9:** my recommendations, approved as
  written above.
- **Q-7:** resolved before approval (CLAUDE.md updated in `27e904d`).

## Agreement

### Round 2 (29 October 2026): the developer's feedback, all taken

1. **AC-13 completed.** Added the titles `test_ac35_decisions_entry` finds
   in ‘Rendered without Inkscape’ (‘The font is vendored’, ‘Output, and the
   supersampling cap’, ‘Installed-copy behaviour’, ‘Packaging is tested by
   rendering’) with the bold item titles they quote, the entry titles
   ‘Output, and the supersampling cap’ and ‘Purple menkyo, and a precept
   column’ (whose commas AC-4 now names as not serial), the Open item
   openings ‘Paper format’, ‘Kyū grades’ and ‘An annotated version in
   Dutch’, and the README's `### Where the columns start`. Rule recorded in
   AC-7: no gloss in a heading, a bold item title or a quoted title.
2. **Layer 1 tightened** (superseded by the user's Q-1; the word-for-word
   check survives only as `restyle_problems`, a report for M-2). An insertion is accepted only straight after a
   Japanese term, and never with a negating word; inserting ‘not’, ‘never’
   or ‘only partly’ fails (non-vacuity tests added). Bold and quoted titles
   are compared on their own as well.
3. **`first_mentions` is case-insensitive for every romanised term** (Kyū,
   Dōjō, Jūjutsu, Ryū at the start of a sentence); kanji terms match as
   written. Test added.
4. **`HISTORY_EDITS`**, one registry in `house_style.py` applied by every
   history comparison; the two copies of the reworded-bullets exception in
   the older tests are gone. Recorded that the git-based comparisons are
   weaker than the pin and may be retired the first time one has to change.
5. **`pin_history.py`** prints the blocks that changed and refuses to write
   unless each is named with `--allow`; `PINNED_BLOCKS` lives once, in
   `house_style.py`.
6. **Scope test** no longer lists the docs/\*.md files; the glob defines the
   scope.
7. **`PROPER`** gained Cairo, Ghostscript, Latin, Debian, Windows, Homebrew,
   Vorselaar and Brief, and the failure message says to add a proper noun
   there.
8. **Code spans over a line break**: `history_tokens` collapses whitespace
   before tokenising, the lint carries an open span from one line to the
   next, `facts()` reads spans across a break, and AC-1 tells the docs agent
   not to rewrap a line that carries a code span.

Lint bugs fixed, each with a test: an apostrophe after emphasis
(`*dono*'s`) is not a quotation mark; `grayscale` is reported (the old
pattern could never match); `practiced` and `practicing` are reported;
honorary and honorarium are not; maize is not. AC-11 now says the docs
agent's hand-off has `test_ac11_history_pinned` red until the tester pins.
Q-2 covers dono, seireki, jūjutsu, ryū and menjō and says where the tables
already gloss them. Q-7 is resolved.
