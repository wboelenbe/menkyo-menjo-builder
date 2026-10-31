# kyu-redesign: validation

## Round 1 (2026-10-30)

VERDICT: FAIL (AC-7 only: the proof's seal circle crosses the safe inset at
the bottom). Every other AC passes.

Validated against the working tree on top of `ec62ba5` (0.6.0, the
developer's build after review round 1). Every render pinned
`-c src/menkyo/example.toml` or a config written in the scratchpad, with
HOME and XDG_CONFIG_HOME pointing into the scratchpad. Placeholder names
only. Renders were written to the scratchpad, not the repository.

### Tester changes this round (tests/acceptance, contract)

- **R-1 (review):** `test_ac2_help_says_portrait` now splits on
  `\n  --paper SIZE`, so it reads the option's own help line (COLUMNS=1000),
  not the usage line. It passes: the line says 'The kyū sheet is portrait
  and A4 by default'. Agreement 2 in acceptance.md corrected to say so.
- **AC-7, test made to match the contract:** AC-7 says the seal circle lies
  'inside the safe inset'; `test_ac7_seal_circle_on_the_proof_only` and
  `test_ac4_a_long_issuer_line_stays_inside` checked only its right edge.
  Both now check the bottom edge as well, and the first one checks every
  side. The contract is unchanged. Both fail on the build (see AC-7).

### Runs

- `uv run pytest` (with R-1's fix, before the AC-7 tightening): **1117
  passed** in 4 min 31 s, slow wheel test included.
- After the AC-7 tightening, with validation.md in place: **2 failed, 1115
  passed**. The two are the tests above, each failing on the bottom edge
  only (`assert (264.0 + 9.0) <= (297.0 - 26.87) + 0.01`).
- `scripts/test-docker.sh`: 1111 passed, 6 skipped (see 'Linux' below).

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 | PASS | `test_ac1_*` green; the kyū block in `src/menkyo/example.toml` sets `body` and `watermark = 0.08`, no `crest`/`motto`/`layout`/`formula`; the wheel's `--example-config` has `watermark = 0.08` (line 142). |
| AC-2 | PASS | `test_ac2_*` green, R-1 fixed. Manual: `--all --paper A3 --list` lists `kyu-{overlay,overlay-flat,proof}-a3-sample.pdf`; A3 overlay rendered and viewed (the A4 layout scaled up). |
| AC-3 | PASS | `test_ac3_*` green. The wheel's SVG for `--rank=jun3`: 級位認定証, ヤン・ヤンセン殿, 準三級, the two body lines, 西暦二〇二六年九月五日, 〇〇流柔術, 〇〇道場, 師範 山田太郎; root `210.0mm × 297.0mm`. |
| AC-4 | PASS | `test_ac4_*` green (the long-issuer test fails only on its AC-7 assertion, see AC-7). Developer note checked: with signatory ジョン・スミス・ドウ the block moves to x 56.87 (the safe edge) and shrinks to 8.174 mm, so its centre is exactly 5 mm right of the page centre; with 18 and 26 characters it shrinks to 5.06 and 3.32 mm, still flush at the safe edge. A 24-character name: 26.87 to 183.13 mm, centred. A three-line body (third line long): set at 6.51 mm, clear of the date. A one-line body: centred on y 186.5. |
| AC-5 | PASS | `test_ac5_*` green. Proof SVG: rings `stroke="#ebebeb"`, r 60. |
| AC-6 | PASS | `test_ac6_*` green. |
| AC-7 | **FAIL** | Margins, zones, date slots and 'proof only' pass. The seal circle is `cx=164.4 cy=264.0 r=9.0` (example) or `cx=174.13` (long signatory): bottom at 273.0 mm, below the safe inset's 270.13 mm (A4 layout mm). Visible in the proof PNG: the dashed circle crosses the inner (blue) guide. |
| AC-8 | PASS | `test_ac8_*` green (render). Manual: overlay PNGs `LA`, proof PNGs `RGBA`, 827 × 1169 px at 100 dpi (A4) and 1169 × 1654 px (A3). |
| AC-9 | PASS | `test_ac9_*` green. Wheel: `--name=ヤン한 --json` gives one `error`: 'the character 한 (U+D55C) in --name is not in Noto Serif JP SemiBold …', exit 1. |
| AC-10 | PASS | `test_ac10_*` green; kyu-grades' rank tests green. |
| AC-11 | PASS | `test_ac11_*` green. Extra probes: `motto = true` on `dan` with `--list --json` is one `error` naming the file, `'dan'`, `motto` and 'removed in 0.6.0'; a body line `"\t"`, `watermark = nan` and `watermark = inf` are each one `error` naming file, award and key. `&`, `<`, `>` in a body line are escaped (SVG parses). |
| AC-12 | PASS | `test_ac12_*` green. Wheel run: exactly one `progress` (1 of 1, `pdf`, 'kyu overlay: writing the PDF'), two `file`, one `done`. |
| AC-13 | PASS | `tests/regression` goldens and `test_ac13_the_landscape_awards_unchanged` green. |
| AC-14 | PASS | `test_ac14_installed_wheel` green; M-3 below. |
| AC-15 | PASS | `test_ac15_*` and the house-style sweep green. M-4 below. |
| AC-16 | PASS | `menkyo 0.6.0` from the checkout and from the wheel. |

### AC-7 failure: reproduction

```sh
H=$(mktemp -d); HOME=$H XDG_CONFIG_HOME=$H/.config \
  uv run menkyo -c src/menkyo/example.toml -a kyu -v proof -f svg \
  -n ヤン・ヤンセン -r white-yellow -d 2026-09-05 -o $H/out
grep -o '<circle cx[^>]*>' $H/out/*.svg
```

Expected (AC-7): the seal circle inside the safe inset, so
`cy + r <= 297 − 26.87 = 270.13` (layout mm), with its centre within 3 mm of
the signatory line's (y 264) and a radius of 6–12 mm.

Actual: `<circle cx="164.400" cy="264.0" r="9.0" …>`, bottom 273.0 mm,
2.87 mm past the inset. The same with a long signatory (`cx="174.130"`).
`uv run pytest tests/acceptance/test_ac_kyu_redesign.py -k "seal or
long_issuer"` fails on that assertion.

Fixes that satisfy the contract as it stands (developer's choice): a radius
of at most about 6.1 mm at cy 264, or the centre raised to about 261
(still within 3 mm of the line) with r ≤ 9.1. Alternatively the user may
decide that the circle, a guide for a hand stamp that is never printed, may
cross the safe inset; then the contract changes, not the code. I recommend
the code fix: the mock puts the circle in the same place, but AC-7 was
written and agreed with 'inside the safe inset'.

### Manual checks

- **M-1 Look at it.** Filled overlay and proof (A4, 100 dpi), blank proof
  and A3 overlay rendered and viewed beside `kyu-a4-crest-C.png`. Same
  sheet: the heading, name, grade, body, date and issuer block in the
  mock's places and sizes (the body block sits about 1 mm further right);
  the watermark as light as in the mock and behind the text; the text crisp
  and black. The overlay has no seal circle; the proof has the border, the
  safe inset, the seal circle and, when blank, the name and grade zones and
  the nine date slots. A3: the same layout scaled up.
- **M-2 Test print.** Not done (no printer here); for the user.
- **M-3 Installed wheel.** `uv build --wheel` into the scratchpad, installed
  into a throwaway Python 3.13 venv, run from `/tmp` with an isolated HOME:
  `--version` gives `menkyo 0.6.0`; `--list` ends with
  `kyu-overlay-a4-sample.pdf`; the portal's form with `--rank=jun3 --json`
  writes `~/Documents/Menkyo/kyu-overlay-a4-jun3-ヤン-ヤンセン.{pdf,svg}`,
  A4 portrait, AC-3's lines with 準三級; `--name=ヤン한 --json` is one
  `error` naming Noto Serif JP SemiBold, exit 1.
- **M-4 Docs.** The DECISIONS entry ('Kyū grades in horizontal lines, on
  portrait paper', no 'A4' in the heading as the developer noted) names
  what it overrides and states the print risk plainly; the Open item 'A
  smaller footprint' now has its bold title on one line (the developer's
  note); 'A second brush font' is gone. The README's paper table row,
  configuration block, variants, printing (a test print, raise or lower
  `watermark`) and typeface paragraphs read correctly. `docs/kyu-explained.md`
  follows the new sheet top to bottom; its crest section correctly puts the
  art on the upper arc and the dōjō on the lower. R-2 done: the example's
  kyū comments are reflowed (the one line over 80 characters, line 58, was
  already there at `ec62ba5`).
- **M-5 Linux.** See below.

### Linux

`scripts/test-docker.sh` (Linux, slim image): **1111 passed, 6 skipped**
in 4 min 50 s. The six skips are the git-history checks (no `.git` in the
image), as in earlier items; every render test ran. That image was built
with R-1's fix but before the AC-7 tightening, so it ran the two seal tests
in their old form. The geometry is the same on every platform (an SVG
attribute), and they fail on the Mac.

### New findings, not in contract

- None blocking. Wording nit: the `body` error says 'one to 3 lines'
  (a word and a figure mixed); 'one to three' would read better.

## Round 2 (2026-10-31)

VERDICT: PASS. AC-7 now passes. Every other AC still passes.

Validated against the working tree after the AC-7 fix. That fix keeps the
seal circle's radius at 9 mm and puts its centre at
`min(signatory line, page height − safe inset − 9)`. It also changes the
`body` error to 'one to three lines' and adds a DECISIONS sentence. Every
render pinned `-c src/menkyo/example.toml`, a variant of it written to the
scratchpad, or the wheel's own `--example-config`. HOME and XDG_CONFIG_HOME
pointed into the scratchpad. Placeholder names only, and all output went to
the scratchpad. No test files were changed this round, so the contract is
unchanged.

### Runs

- `uv run pytest`: **1117 passed** in 4 min 57 s.
- `tests/acceptance/test_ac_kyu_redesign.py`: 123 passed. The two tests
  tightened in round 1 both pass:
  `test_ac7_seal_circle_on_the_proof_only` (every side inside the safe
  inset) and `test_ac4_a_long_issuer_line_stays_inside` (right and bottom).
- `scripts/test-docker.sh` (image rebuilt, so it includes the tightened
  AC-7 tests): **1111 passed, 6 skipped** in 4 min 44 s. The six skipped
  tests are the git-history checks, which skip because the image has no
  `.git`. Every render test ran. The first attempt died at about 40 % with
  'error waiting for container: unexpected EOF' (OrbStack had gone to
  sleep). The rerun after the restart was clean.

### AC-7: round 1 reproduction rerun

| case | circle (layout mm) | check |
|---|---|---|
| example, A4 proof | `cx=164.400 cy=261.130 r=9.0` | bottom 270.13 = 297 − 26.87: on the inset; 2.87 mm from the line (y 264) |
| example, `--paper a3` | same, inside the scale wrapper | as A4 |
| signatory ジョン・スミス・ドウ | `cx=174.130 cy=261.130` | right edge 183.13 = 210 − 26.87: on the inset |
| blank signatory | `cx=123.400 cy=261.130` | right of the title, clear of it |
| `safe_inset = 20` | `cy=264.000` | centred on the line (the `min` takes the line) |
| `safe_inset = 50` | `cy=252.645` | inside the inset, but 11.4 mm above the line (see the follow-up below) |
| overlay | no `#e4b9b9` at all | proof only |
| installed wheel, `--example-config` | `cx=164.400 cy=261.130 r=9.0` | as the checkout |

Rendered and checked by eye (A4 proof at 100 dpi, and the issuer corner
cropped from a 300 dpi render). The dashed circle sits right of 山田太郎,
clear of the name. Its bottom touches the inner (blue) guide without
crossing it, and its top is clear of the 〇〇道場 line. Nothing else on the
sheet moved compared with round 1.

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 to AC-6 | PASS | Suites green on the Mac and on Linux. Nothing touched by the fix. |
| AC-7 | PASS | See above: the circle is inside the safe inset on every side, its centre is 2.87 mm from the signatory line's, r 9, proof only. Zones and date slots are unchanged and their tests are green. |
| AC-8 to AC-13 | PASS | Suites green. `test_ac11_*` covers the `body` error. Manual: a four-line `body` with `--list --json` gives one `error`, '… should be a list of one to three lines of text, one string per printed line, none of them empty', and exit code 1. |
| AC-14 | PASS | Wheel built into the scratchpad and installed into a throwaway venv. Run from the scratchpad: `menkyo 0.6.0`. The kyū proof from `--example-config` with `--json` ends in a `done` event, and the circle is as in the checkout. |
| AC-15 | PASS | DECISIONS 'Variants' paragraph: 'The circle has a stamp's radius, 9 mm. Centred on the signatory's line (264 mm), it would cross the safe inset, so its centre rises until the circle's bottom sits on the inset: 261.1 mm by default.' That matches the code. The house-style sweep is green. |
| AC-16 | PASS | 0.6.0, from the checkout and from the wheel. |

### Follow-ups, not in contract (agree with review round 2, R-1)

- With a larger `safe_inset` the circle keeps rising with no limit. It
  first breaks AC-7's 'within 3 mm of the line' at about 42 mm (A3 terms);
  at 50 it sits 11.4 mm above the line. The contract was agreed for the
  default configuration, which passes, and the circle is a guide on the
  proof only. A follow-up could shrink `r` to fit, or clamp it.
- At the default inset the circle's top (252.13 mm) is about 1 mm from the
  dōjō line's baseline. It does not collide in the render, but the margin
  is thin.
- Review R-2 (the message hard-codes 'three' while the check uses
  `MAX_BODY_LINES`) and R-3 (the seal test renders A4 only; A3 is in the
  manual check above) remain nits.

## Round 3 (2026-10-31)

VERDICT: PASS. Only tests changed this round (review round 3: the most
coverage from the fewest tests). No production code, no goldens and no AC
changed. Each moved check is recorded in acceptance.md ('Review round 3'
and the AC table), and every AC is still covered.

### Changes

- `test_ac_kyu_redesign.py`: 123 → 97 tests. AC-13 now compares flat
  `-v all --no-ink` trees and writes the 0.5.0 configuration once. AC-12's
  totals and the grade-form renders are folded into AC-8's render. The
  duplicate default run, the AC-10 grade forms and the `purple` refusal
  are dropped (the default run is plain-white's; the grade forms and
  `purple` are kyu-grades' rank tests). A module-scoped `filled` sheet
  feeds the AC-2 to AC-7 checks, and three AC-4 tests became one. AC-11's
  value tables run in-process, keeping one command-line case per key. The
  version test is dropped (`test_ac37_version` stays). The wheel test now
  also checks `--rank=purple`.
- `test_ac_kyu_grades.py`: 156 → 142 tests. The duplicates of the above
  are dropped, including its wheel test, its version test and its
  DECISIONS pin (house-style-sweep's pin covers the same 21 blocks).

### Runs

| run | before (round 2) | after |
|---|---|---|
| `uv run pytest --durations=25` | 1117 passed, 4 min 57 s | **1077 passed, 249.9 s (4 min 10 s)** |
| `scripts/test-docker.sh` | 1111 passed, 6 skipped, 4 min 44 s | **1071 passed, 6 skipped, 234.5 s (3 min 54 s)** |

The six skips on Linux are the git-history checks, because the image has
no `.git`. Every render test ran. The two edited files alone take 9.8 s
(239 passed). `test_ac13_the_landscape_awards_unchanged` (35.9 s before) is
no longer among the 25 slowest. The slowest test is now the setup of
`test_ac14_installed_wheel` (23.5 s, building the wheel).

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 to AC-16 | PASS | Both suites green. The tests behind each AC are listed in acceptance.md's table. |
