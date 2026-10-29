# remove-supersample: review

## Round 1

Verdict: APPROVE. The change matches the contract: the flag, help, range
check and message, the `supersample` parameters of `_inked_text_image` and
`build_one`, the keyword in `main()`, the `> 1` branch and the scaled
export DPI are gone; the export is `--export-dpi=600`, the old 1x path. The
bbox `w`/`h` still feed the `<image>` element, so nothing became dead;
`ink.coverage` is still used by `ink_layer`. `--json` events and every
other flag are unchanged; a rejected `--supersample` takes the existing
argparse path. README loses only its Options row. DECISIONS.md: 2026-09-05
bullets past tense with the heading kept, ink-pass bullet past tense with
the table marked as history, the new removal entry honest and consistent
with the table, `## Open` silent. No commit during the run.

Checks: `uv run pytest`: 4 failed (three history tests being amended by
the tester, plus R-1), 372 passed, 12 skipped.

**[R-1] minor, tests.** `test_ac11_repository_never_mentions_it` fails:
the tester's in-progress helpers in `tests/acceptance/test_ac_cli_only.py`
and `tests/acceptance/test_ac_plain_white.py` spell "supersampl" and are
not in AC-11's allow-list. Passed to the tester (allow-list them and record
it, or avoid the word).

**[R-2] nit, docs.** DECISIONS.md:551-552 says "the version stays 0.2.0"
while open question 3 was pending. Resolved: the user chose to keep 0.2.0
(2026-10-29), so the sentence stands.

**[R-3] nit, structure.** `tests/fakes/fake_tool.py:27-28`: the new reason
for the small `QUERY` box ("keeps the placement easy to check") is not
relied on by any test. Say what is true now, e.g. "Arbitrary; the box only
places the <image>, and the goldens pin it." Passed to the developer.
