# Review: plain-white

## Round 1

REVIEW: CHANGES REQUESTED (code correct and complete; one wrong test, the pending image, docs nits)

Checked: `uv run pytest` 321 passed / 3 failed (ink-memory AC-2, excluded; plain-white AC-1 [flags2]; AC-21) / 12 render skips; goldens = 43 deleted blobs, the retained hashes a strict subset of HEAD's; wheel `menkyo-0.2.0-py3-none-any.whl` without border.py; `uv lock --check` clean; `--version` 0.2.0; `-v full --json` one error event; `--pr` rejected; stages text/ink/pdf/png consistent; `colour` ignored, Award has 4 fields; workflow/Dockerfile/script without ghostscript; DECISIONS history intact; no commits during the run.

Dispute on `test_ac1_all_means_the_plain_three[flags2]`: **developer is right**; `--all` has always overridden `-a` (unchanged since before 823af58, documented in --help), AC-22 keeps it.

[R-1] major Tests — tests/acceptance/test_ac_plain_white.py:123-127
What: the `["--all"]` case combined with `-a dan` expects only dan-* files; `--all` overrides `-a`.
Suggested fix: drop the `["--all"]` case (already covered by `test_ac1_all_flag_lists_every_award_and_variant` and `..._writes_what_the_explicit_list_writes`), or run it without `-a dan` expecting all nine.
**Orchestrator: to the tester.**

[R-2] major Docs — docs/three_up.png
What: still the full-cream image; AC-21 fails. Pending Docker.
**Orchestrator: pending until Docker is back.**

[R-3] minor Docs/AC-14 — tests/test_packaging_fixes.py:5
What: docstring still says "stand-in inkscape / gs"; there is no gs stand-in. AC-14's pattern only catches quoted "gs".
Suggested fix: "the stand-in inkscape"; tester may tighten AC-14 to `\bgs\b`.

[R-4] nit Docs — README.md:36: an unwrapped 139-character line in Quick start.

[R-5] nit Docs — README.md:175-176, 243-244: "every document prints in black on plain white" / "black text and crest, no frame, no background" for all three variants, but `proof` draws pale coloured guides. Say it of the two print variants; the proof adds pale guides.

[R-6] nit Docs — README.md:276-277: new paper advice ("200–250 gsm", "uncoated stock takes a stamped seal best") not backed by DECISIONS. Keep it to "plain white A3 paper".

## Round 2

REVIEW: APPROVE

R-1 fixed (tester; --all still covered by two tests). R-2 fixed (three_up.png: three plain white sheets, thin grey outline, example stand-ins only). R-3 fixed (docstring; AC-14 rejects bare `gs`). R-4, R-5, R-6 fixed. No new findings. `uv run pytest --ignore=tests/acceptance/test_ac_ink_memory.py`: 300 passed, 9 render skips. No commits during the run.
