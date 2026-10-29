VERDICT: PASS

# house-style-sweep: validation

## Round 1 (29 October 2026)

Contract: [acceptance.md](acceptance.md), with the user's approval of
29 October 2026 (Q-1 full restyle) and review round 2 (APPROVE). Baseline
`3f025b9`.

### Before validating: tooling fixes (tester)

- **R-9** (review round 2): `cjk_lost` raised IndexError when swapped runs
  came last. Rewritten to walk `now` once with a bounds check; on the real
  file, swapping ‘〇〇道場 and 師範’ in ‘The default build fills every slot’
  is now reported (`kanji or kana lost ['〇〇道場 (out of order)']`) instead
  of raising. `test_ac10_kanji_are_facts` covers `[A, B]` → `[B, A]` and
  `[A, B, C]` → `[A, C, B]`.
- Found in this round: `test_ac_house_style_sweep.py`'s `_git` called `git`
  unguarded, so the first Docker run failed
  `test_ac10_history_edits_follow_the_baseline` (FileNotFoundError: git)
  instead of skipping. Guarded like the older tests' helpers; the Docker
  re-run passes. Both recorded under ‘Test changes’ in acceptance.md.

### Suites

- `uv run pytest` (Mac, after the pin): **631 passed**, none skipped.
- `scripts/test-docker.sh -q -rs` (after the pin and the `_git` fix):
  **625 passed, 6 skipped**. Every skip is a git-history check (no `.git`
  in the image); render tests ran. `test_ac11_history_pinned` ran and passed
  there.
- `check_sweep.py`: **OK**, exit 0.
- `house_style.py` lint: **0 findings**.

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 no em dash | PASS | `test_ac1_no_em_dash[*]` and `test_ac1_code_keeps_its_dashes` pass; the README TOML comments keep `—`. |
| AC-2 quotation marks | PASS | `test_ac2_quotation_marks[*]`, `test_ac2_lint_cases`. |
| AC-3 sentence case | PASS | `test_ac3_*`; the recipient pages' titles are now ‘Dan rank certificate’ and ‘Shihan/Renshi teaching licence’ (Q-6: the ‘Reads as’ lines follow). |
| AC-4 serial comma | PASS | `test_ac4_known_serial_commas_gone[*]` pass. Heuristic candidates reviewed below (M-4). |
| AC-5 dates | PASS | `test_ac5_*`; ‘29 October 2026’ and ‘28 October 2026’ in DECISIONS.md, ‘5 September 2026’ in the recipient pages. |
| AC-6 British spelling | PASS | `test_ac6_*`; outward/inward/onward/toward became -s forms. ‘unrecognized arguments’ stays (quoted program output). |
| AC-7 glosses | PASS | M-1 below. |
| AC-8 no hollow constructions | PASS | M-2 below; grep for VOI-041 phrases finds none. |
| AC-9 facts unchanged | PASS | `check_sweep.py` facts section: no change to code blocks, spans, numbers, targets, tables, and no kanji or kana lost or reordered. |
| AC-10 history keeps facts and meaning | PASS | `test_ac10_decisions_history_keeps_its_facts` passes against `3f025b9` (bullets compared too, R-1). M-2 entry-by-entry read below: no shift. |
| AC-11 history pinned | PASS | `pin_history.py` wrote 21 blocks after M-2 (its own facts check against `3f025b9` passed first). `test_ac11_history_pinned` passes on the Mac and in Docker. |
| AC-12 Open item closed | PASS | `test_ac12_open_item_closed`; `check_sweep.py` Open section OK (5 items, facts intact); M-2: only the Kyū item gained glosses. |
| AC-13 depended-on text kept | PASS | `test_ac13_*` and the whole suite pass. |
| AC-14 older tests migrated | PASS | cli-only AC-11, plain-white AC-16, render-without-inkscape AC-35 and remove-supersample AC-10 pass locally. |
| AC-15 nothing else changes | PASS | `check_sweep.py` file list: the eight docs, `tests/acceptance/**`, `docs/work/house-style-sweep/**`. `git diff --quiet 3f025b9 -- src tests/regression pyproject.toml uv.lock CLAUDE.md .claude LICENSE` is clean; version 0.3.0. |
| AC-16 markup intact | PASS | `test_ac16_*` pass. |
| AC-17 suite and wheel | PASS | Suites above, plus M-5 below. |

### Manual checks

**M-1 (first mentions, AC-7).** `check_sweep.py`'s term report, read per
file. Every term outside the four exemptions (dōjō, dan, kanji, katakana)
is glossed at its first prose mention, or in the table row Q-2 allows:

- README.md: 賞状 (award certificate), 〇〇 (‘the ordinary Japanese placeholder’), crest (mon), yotsume-bishi (four lozenges in a diamond), family crest (kamon), romaji (Japanese in Latin letters), 西暦 (the Western calendar), kaisho (regular script), mincho (the printed serif style), 殿 (the honorific after the name), sumi (brush ink, in the Options table).
- DECISIONS.md: mon (crest), 西暦 (Gregorian), 賞状 (award certificate), yotsume-bishi and kasure (defining phrases, unchanged), kaisho (regular script), mincho (in the body after its bold title), sumi (brush ink), 殿, romaji, 大字 (the numerals of legal documents, such as 弐), menkyo (licence, in the body after the bold title), shihan (master instructor), 〇〇 (the Japanese placeholder, ‘so-and-so’), kamon (family crest), kyū (coloured-belt) and shodan (first dan) in the Open item's sentence, not its bold title.
- NOTICE: yotsume-bishi and kamon.
- docs/README.md: 殿, shihan (master instructor), renshi (polished expert, as the user asked).
- The recipient pages: their tables gloss menjō, seireki, ryū, jūjutsu, dōjō and shihan; dono and 殿 in the sentence that introduces them; renshi and shihan in the opening sentence; dan (a numbered rank).

No gloss is repeated within a file (grep for each gloss phrase per file).
The NOTICE ‘menkyo’ hit is the path `src/menkyo/`, not a term.

**M-2 (meaning, AC-8, AC-9, AC-10, AC-12).** `git diff --word-diff 3f025b9`
of every in-scope file, and every DECISIONS.md entry read old against new.

DECISIONS.md, entry by entry. Every one has the same meaning:

| block | entry | changes | meaning |
|---|---|---|---|
| 0 | preamble | dash, serial comma | same |
| 1 | Brief | dashes, mon (crest) | same |
| 2 | Three documents… | dashes, 賞状 gloss | same |
| 3 | The drawn border | dash, serial comma, quotes | same |
| 4 | Calligraphic typeface | dashes, kaisho and mincho glosses | same |
| 5 | Ink density | dashes, outwards/inwards, sumi gloss | same |
| 6 | Output, and the … cap | dashes, quotes, date spelled out | same (numbers, cap 4, default 1, 32767 px, 6622 px all kept) |
| 7 | Printing the three hand slots | dashes, 殿, romaji, 大字 glosses | same; the 大字 gloss is accurate |
| 8 | The licences have no grade column | dash | same |
| 9 | Purple menkyo… | dashes, shihan and menkyo glosses | same |
| 10 | Translations for recipients | dashes, quotes | same |
| 11 | Made publishable | dash, 〇〇 and kamon glosses, quotes | same |
| 12 | The default build fills every slot | dashes, quotes; ‘needed somewhere for its defaults to come from that is visible and editable’ → ‘needed a visible, editable place for its defaults to come from’ | same |
| 13 | A configurable start point | dashes, quotes | same |
| 14 | A package, for the dojo portal | dashes, serial comma | same |
| 15 | `xlink:href` … | dashes | same |
| 16 | The command is the product | heading dash only | same |
| 17 | Plain white paper only | quotes | same |
| 18 | The ink pass grades the alpha alone | quotes | same |
| 19 | Supersampling removed | quotes | same; ‘unrecognized arguments’ keeps argparse's spelling |
| 20 | Rendered without Inkscape | heading only (already in house style) | same |

`## Open`: the house-style item removed; ‘(asked 28 October 2026)’; the Kyū
item glossed. Same meaning.

README.md, NOTICE, tests/README.md, docs/README.md and the recipient pages
change only in dashes, quotes, serial commas, dates, -wards spellings,
heading case and glosses (‘four lozenges in a diamond’ for the yotsume-bishi
matches the recipient pages' ‘four lozenges, each pierced by a smaller
one’). The README's AI-authorship note lost only its serial comma (Q-5). No
shift. No construction from VOI-040 or VOI-041 found, and no doubtful claim
gained or lost a qualification (CLM-001).

**M-3.** `check_sweep.py` exits 0 (see Suites).

**M-4 (serial commas, AC-4).** 18 heuristic candidates. Fourteen are commas
between clauses. Four stay because they prevent ambiguity or are inside a
title:

- DECISIONS.md 304, ‘printed a heading, a formula, 〇〇流柔術, 〇〇道場 and 師範, and empty space where…’: the comma closes an inner list that ends in ‘and’.
- DECISIONS.md 467, the overrides in ‘Plain white paper only’: the first hit is the comma inside the title ‘Output, and the supersampling cap’ (not serial, AC-4); the second, ‘, and the colours of’, separates items that themselves contain ‘and’.
- DECISIONS.md 496, ‘pass `--variants` explicitly, map only the stages `text`, `ink`, `pdf`, `png`, and build …’: without the comma, ‘`png` and build’ reads as part of the stage list.

**M-5 (wheel, `--help`, AC-17).**

- `uv build --wheel` → `menkyo-0.3.0-py3-none-any.whl`. Installed into a throwaway venv and run from a scratch directory, with `HOME` and `XDG_CONFIG_HOME` pointed into it:
  - `menkyo --version` printed `menkyo 0.3.0`;
  - `--list` with `-c <checkout>/src/menkyo/example.toml` listed the three default files;
  - a `-a dan -v overlay -f pdf -d '' --json` run ended in `done` and wrote the PDF;
  - the wheel's NOTICE is the restyled one.
- `--help`: `src/` at `3f025b9`, extracted with `git archive` (no checkout switch), and the working tree print the same bytes under the same interpreter, except the `-o` default directory. That differs only because the extracted copy is not a checkout and so defaults to `~/Documents/Menkyo`. `src/` is byte for byte unchanged (`git diff --quiet 3f025b9 -- src`).

### Edge cases tried

- Swapped kanji in a history entry (〇〇道場 and 師範, and 初段 and 一段):
  reported.
- A number inside the HISTORY_EDITS region changed against `3f025b9` (‘32767
  px’ → ‘32768’, ‘capped at 4’ → ‘capped at 8’): reported.
- Re-pinning after a changed block without `--allow`: refused (exercised
  on a scratch copy in planning).

### Observations, not in the contract

- **Ragged wrapping in DECISIONS.md** at lines 156–158 (‘Cairo, which /
  Inkscape / renders through’) and 177–179 (‘by default. 16 mm / nominal’),
  left by inserting text without rewrapping (as instructed, to keep code
  spans intact). It is cosmetic: the Markdown renders the same. A rewrap now
  would change the pinned bytes, so it needs a re-pin if anyone does it.
