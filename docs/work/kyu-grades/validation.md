# kyu-grades: validation

## Round 1 (2026-10-30)

VERDICT: PASS

Against the working tree on top of `04f45ec`, version 0.5.0, after review
round 1 (APPROVE) and its fixes R-1, R-2, R-4, full-width digits on kyū,
R-3 and R-5.

### Suites

| run | result |
|---|---|
| `uv run pytest` (Mac, Python 3.13, wheel tests included) | 1012 passed, 0 skipped, 269 s |
| `scripts/test-docker.sh` (Linux, slim image) | 1006 passed, 6 skipped, 283 s |

The six Docker skips all need git, which the image does not have:
house-style-sweep (×2), render-without-inkscape (×2) and cli-only (×2).
No render test skipped; the slow (wheel) tests ran in both.

### Per criterion

| AC | verdict | evidence |
|---|---|---|
| 1 | PASS | `test_ac1_*` (3); the installed wheel's `--list` names four awards |
| 2 | PASS | `test_ac2_*` (11); wheel: `kyu-overlay-a3-yellow-ヤン-ヤンセン.pdf` |
| 3 | PASS | `test_ac3_*` (4), `test_ac5_inked_svg_has_no_crest`; M-1 |
| 4 | PASS | `test_ac4_*` (option B, 10 mm shift, centring, empty precept, grade fit: 24); M-1 |
| 5 | PASS | `test_ac5_*` (7), A3 and A4, in Docker too |
| 6 | PASS | `test_ac6_proof_guides` (8); M-1 proof |
| 7 | PASS | `test_ac7_kyu_rank_forms` (55, incl. full-width and NFD) |
| 8 | PASS | `test_ac8_*` (22); M-3 |
| 9 | PASS | `test_ac9_*` (27), `tests/regression/test_pure.py` |
| 10 | PASS | `test_ac10_*` (4) |
| 11 | PASS | `test_ac11_*` (20), `tests/regression/test_config.py` |
| 12 | PASS | `test_ac12_*` (3) |
| 13 | PASS | `test_ac13_*` (2) |
| 14 | PASS | `tests/regression/test_golden.py` (33, byte for byte), `test_ac14_*` (4) |
| 15 | PASS | `test_ac15_installed_wheel`; M-2 |
| 16 | PASS | `test_ac16_*` (4), house-style-sweep (lint, pins, Open list); M-4 |
| 17 | PASS | `test_ac17_version`; the wheel is `menkyo-0.5.0-py3-none-any.whl`, `--version` says 0.5.0 |

### Manual checks

- **M-1 Look at it.** `-a dan,kyu -v overlay,proof -f png --dpi 60 -d
  2026-09-05` at A3 and A4, plus `-a kyu -v proof -n '' -r white-yellow
  -d ''` and `-a kyu -n ヤン・ヤンセン -r orange-green`, composited on white
  side by side. The kyū sheet has no crest, no ring and no precept; its
  block is visibly centred (option B, as the user accepted) and the seal
  guide has moved with it. Every column of the dan sheet appears on the kyū
  sheet in the same order and heights. 準五級 and 準三級 are set smaller
  and end above the name zone on the proof (OQ-12). A4 is the same sheet,
  smaller.
- **The explainer's wording against the real sheet.** ‘The first column of
  the lower block names the art’ reads right: on the kyū sheet the art,
  dōjō, office and signatory columns visibly start lower (y ≈ 107 mm)
  than the heading, grade and formula (y ≈ 79–85 mm). The phrase does not
  depend on the crest. It still makes sense even though the kyū page has
  no crest section before it. ‘Written in a smaller hand, so that its three characters take the space
  two would’ matches the render.
- **M-2 Installed wheel.** `uv build --wheel`, a fresh venv, run from a
  directory outside the checkout with HOME isolated, and `-c` set to the installed copy's
  `example.toml`: `--version`, `--list` (four), the portal's form
  `--config=… --awards=kyu --variants=overlay --formats=pdf
  --name=ヤン・ヤンセン --rank=yellow --date=2026-09-05 --out=… --json`
  (one `file`, `done`), `--rank=jun3` on `overlay-flat`/svg prints
  準三級, `--rank=purple` and `-a dan --rank=yellow` each one `error`,
  exit 1.
- **M-3 The errors read well.** `--rank purple: not a kyū grade on
  [[awards]] 'kyu'. Use 1 to 10, the romaji (ikkyu, nikyu … gokyu …
  jukkyu), a belt (white, yellow, orange, green, blue, brown), a children's
  step (white-yellow, yellow-orange, orange-green, or jun5, jun4, jun3), or
  the kanji as it should print (三級).` and `--rank yellow: a kyū grade,
  but [[awards]] 'dan' counts in dan; give a dan grade (1 to 10, nidan,
  二段) or the text to print`. Both can be shown by a portal as they are.
- **M-4 The docs.** The DECISIONS entry states the decisions and names
  what it overrides; the Open item is closed and a new one (a second
  brush font) added. The house-style lint passes.
- **M-5 Linux.** As above: 1006 passed, no render test skipped.

### Edge cases tried (beyond the tests)

All behave sensibly. The ones that are not obvious are listed under
‘New findings’.

- `--rank`: `05` → 五級; `jun-3` → 準三級; `Gokyuu`, `ROKKYŪ`, `ikkyū`,
  `\t5\n` read correctly; `jun 5`, `white yellow`, `white/yellow`, `０`,
  `１１`, `1.5`, `kyū`, `SHODAN` refused on kyū with the list of forms;
  `準十級` (literal) set at 20 mm; on dan `５` → 五段, `jūdan` → 十段,
  `kyudan` → 九段, `１１` → the range message, `White-Yellow` refused naming
  the award; `-r Shihan` on a licence set at 10 mm.
- Configuration: `grade_column = "KYU"` accepted and saved as `"kyu"`;
  `grade_column = 2026-09-05` (a TOML date) and `crest = [1]` are clean
  errors naming the file, the award and the key (R-1); `[sample] rank =
  "11"` and `"purple"` are errors naming `[sample] rank`.

### New findings, not in the contract

None of these blocks the item; each is for the user to decide.

1. **A blank-looking grade.** `-a kyu -r ' '` (spaces only) is an error,
   `--rank  : not a kyū grade …`. On a dan award the same value prints
   nothing, as in 0.4.0. The portal passes `''`, which works on both, so
   this only matters for a hand-typed command.
2. **`jūkyū` is refused.** After folding it is `jukyu`; the accepted
   spellings are `jukkyu` and `jikkyu` (OQ-7). `jūkyū` is a common
   romanisation, so it may be worth accepting.
3. **The DECISIONS entry does not mention full-width digits** (`５` → 五級
   on kyū, the user's decision after review), nor the NFC normalisation
   (R-2). The behaviour is tested (AC-7); only the record lacks a line.
4. **The explainers' ‘below’.** ‘Below the art stands the dōjō’ and
   ‘Immediately below the heading stands the grade’ are inherited from
   `dan-explained.md`. On the sheet these are the next column to the left,
   not below. This is pre-existing wording, kept for consistency; it could
   be fixed in all the explainers together.
