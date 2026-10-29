# render-without-inkscape: review

## Round 1

Verdict: APPROVE. No blocker or major finding.

**Checks run:**
- `uv run pytest` on the Mac: 539 passed, 0 skipped.
- `scripts/test-docker.sh`: 535 passed, 4 skipped. All 4 are the existing
  'no git history in the image' skips; none is a `render` test.
- Overlay, overlay-flat and proof PDFs pass `qpdf --check` and pikepdf
  `check_pdf_syntax()`.
- The wheel is 0.3.0 and 10.53 MB, with both fonts and both licences
  (also in `dist-info/licenses/`). `Requires-Dist` is exactly pillow,
  numpy, scipy, `fonttools>=4.68` and `pypdfium2==5.14.0`.

**What holds up:**
- **PDF writer:** 20-byte xref entries, `startxref` and `/Pages` correct,
  fixed-point matrices, allow-list refusals.
- **Glyph check:** runs after `--list` returns and before `--clean`; its
  scope matches `document()`.
- **Clean-up:** `.work` is removed in a `finally`, and `.part` files live
  inside it.
- **Unchanged:** `ink.py` grading arithmetic, and the `--honorific`
  behaviour.
- **PNG reader:** probed at band boundaries, no rows lost.

**Fact checks:**
- (a) The README overstates what is checked; the code and DECISIONS are
  right (R-1).
- (b) NOTICE is correct. `OFL-NotoSerifJP.txt` is byte-identical to
  upstream noto-cjk `Serif2.003/Serif/LICENSE`, with no Reserved Font Name,
  and the font's name table names none either.

**[R-1] minor, docs.** `README.md:118` says 'every configured string' is
checked. In fact only what is drawn is checked. Say: the selected awards,
the honorific only with a name, a sample grade only where there is a grade
column. *Owner:* docs.

**[R-2] minor, correctness.** With `-f png`, `--dpi 0` ends in a
`ZeroDivisionError` traceback (`render.py:620`) and `--dpi -5` in a
`struct.error` (`png.py:43`). Reject values below 1, and above a sane cap
such as 2400, in `main()` with a `SystemExit` message. *Owner:* developer.

**[R-3] minor, CI.** At `.github/workflows/package.yml:48`, the negated
`grep` loop only checks the last PDF, because `!` never trips errexit. Use
`! grep -alq "/FontFile" out/*.pdf`. *Owner:* developer.

**[R-4] minor, process.** CLAUDE.md, `.claude/agents/developer.md` and
`tester.md` still describe Inkscape renders, `REQUIRE_RENDER` and 'missing
Inkscape'. *Owner:* orchestrator.

**[R-5] nit.** `build_diploma.py:683` duplicates `_traced_glyph`'s
crest-path construction. Add a `_traced_path(ch)` helper. *Owner:*
developer.

**[R-6] nit.** `FONT_DIR = renderer.FONT_DIR` at `build_diploma.py:67` is
a read-only alias, and monkeypatching it has no effect. Comment it.
*Owner:* developer.

**[R-7] nit, tests.** `tests/regression/test_golden.py:71` dedupes only the
current side of the text-layer comparison. Compare like with like. *Owner:*
tester.

## Round 2

Verdict: APPROVE. All of R-1 to R-7 are fixed: R-1 at `README.md:117-126`,
R-2 at `build_diploma.py:878` with `MAX_DPI` at line 512 and a test, R-3
at `package.yml:47`, R-4 in CLAUDE.md and the agent and skill files, R-5
with `_traced_path` at line 128, R-6 as a comment at line 67, R-7 at
`test_golden.py:72`. `uv run pytest` is green once the tester's
`pdf_sha256.json` (Q-7) exists. Checked by hand: `--dpi` bounds, the
`--json` error event, `--list`. The portal never passes `--dpi`.

**[R-8] minor, contract/docs.** `--dpi` now refuses 0, negative values
and anything above 2400 for every format, `--list` included. Before, any
integer was accepted, and ignored without PNG output. Neither
acceptance.md nor the README says so. Add the range to the README row,
the argparse help and DECISIONS.md, and tell the user at hand-off (CLI
contract).

**[R-9] minor, tests.** `tests/test_render.py:227` calls `bd.main()`
only. Add one case through `cli([... "--list", "--dpi=0", "--json"])`
asserting a single `error` event and exit 1 (helpers in
`tests/test_packaging_fixes.py:46`).

**[R-10] nit.** The comment at `build_diploma.py:876-877` reads 'past 2400
dpi an A3 page is over a gigapixel'. It already is at 2400 (1.11 Gpx). Say
'at MAX_DPI an A3 page is already over a gigapixel'.

**[R-11] nit, tests/docs.**
- Q-7 in acceptance.md names `make_golden.py --current`; the flag is
  `--pdf-hashes`.
- `test_golden.py` reads `pdf_sha256.json` at import, so a missing file
  breaks collection. Optionally load the hashes inside the test.
- Commit `pdf_sha256.json`.
