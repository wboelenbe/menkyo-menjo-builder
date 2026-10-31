# Review: kyu-redesign

## Round 1

REVIEW: APPROVE

No blocker or major findings; two minor findings and three nits.

Checks run (read-only; every render pinned to `-c src/menkyo/example.toml` or a scratchpad config; HOME and XDG_CONFIG_HOME isolated):
- `uv run pytest -q`: 1117 passed, slow wheel test included.
- `scripts/test-docker.sh`: 1111 passed, 6 skipped (no git history in the image).
- Manual probes: escaping of `body`/heading with `&`, `<`; `--json` events of the same shape; `--list --json --paper A3` gives `kyu-overlay-a3-sample.pdf`; `-a dan,kyu -r 3 --list` gives `dan-overlay-a3-3.pdf` and `kyu-overlay-a4-3.pdf`.

Clean: sheet choice per award (one `sheets` dict for `--list` and build), progress totals, glyph checks per face, validation order, `save()`, packaging, personal data. Developer items 3–5 acceptable as they are.

[R-1] minor tests — tests/acceptance/test_ac_kyu_redesign.py:447
`test_ac2_help_says_portrait` splits on the first `--paper SIZE` (the usage line) and so reads the usage and description, not the option's help. AC-2's help requirement is effectively untested. Fix: split on `\n  --paper SIZE`.

[R-2] minor structure/docs — src/menkyo/example.toml:71, 78–79
Two comments edited without reflowing (a 103-character line; a stub line 'sheet, in rows, keeps its own places. 0.05 (a'). `--example-config` prints this file and dōjōs copy it. Fix: reflow to the file's ~78-character width; comments only.

[N-1] nit docs — DECISIONS.md, Open, 'A smaller footprint' item rewrapped (unrelated churn). Restore unless a lint required it.

[N-2] nit docs — CLAUDE.md:4, NOTICE:25–26, README glyph-check paragraph: edited lines not rewrapped.

[N-3] nit contract/help — build_diploma.py:1239–1241: the `--paper` help's kyū sentence appears even for a config without a kyū award. Optional.

VERDICT: APPROVED (R-1 and R-2 worth fixing before the result commit).

### Orchestrator's disposition
- R-1: to the tester (owns acceptance tests), in VALIDATE.
- R-2, N-2 (NOTICE, README): to the developer and docs.
- N-1: kept; `test_ac15_open_items` needs a bold Open title on one line.
- N-2 (CLAUDE.md): rewrapped by the orchestrator.
- N-3: not done; the help stays static.

## Round 2 (fix diff: AC-7 seal circle, `body` error wording, tester's test changes)

REVIEW: APPROVE

Checks: acceptance/kyu/paper tests 244 passed; seal circle at the default inset `cy 261.130 r 9.0` (bottom on the inset), at `safe_inset = 10` `cy 264.000`, at `--paper a3` the same inside the scale wrapper; long issuer line keeps `x_seal + r <= W - safe`; circle still drawn only with guides; AC-2 and AC-7 tests now test what the ACs say.

[R-1] minor correctness — src/menkyo/build_diploma.py:783
With a larger `safe_inset` the circle keeps rising with no floor (`safe_inset = 55` gives `cy 249.109`, on the dōjō line); AC-7's 'within 3 mm' breaks from about 42.2. At the default inset the circle's top is about 1 mm from the dōjō line's baseline. Proof-only guide, cosmetic. No fix needed this round; optionally clamp or shrink `r`.

[R-2] nit structure — src/menkyo/config.py:276
The message hard-codes 'three' while the check uses `MAX_BODY_LINES`.

[R-3] nit tests — tests/acceptance/test_ac_kyu_redesign.py:722
The seal-circle test renders A4 only; A3 covered by shared geometry.

VERDICT: APPROVED.

### Orchestrator's disposition
- R-1: accepted as is (proof-only guide; insets above about 42 mm already push the printed issuer text past the inset). Proposed follow-up.
- R-2, R-3: not done; follow-up nits.

## Round 3 (tests only, under the extended reviewer rule: maximum coverage, fewest and fastest tests)

REVIEW: CHANGES REQUESTED

Run: `uv run pytest --durations=60` on the 10 files in scope, 230.5 s, 734 passed. Estimated saving about 42 s (18 %) from R-1 and R-2; R-3 to R-9 remove about 40 tests. Every AC stays covered.

[R-1] major tests (expensive) — tests/acceptance/test_ac_kyu_redesign.py:1102 (`svgs()` at :166)
`test_ac13_the_landscape_awards_unchanged` (35.9 s) inks dan, shihan and renshi in 8 overlay passes because `svgs()` leaves out `--no-ink`. Pass `--no-ink` here (or compare inked bytes once), call `landscape_050(tmp_path)` once. Saves about 35 s; no coverage lost.

[R-2] major tests (redundant, expensive) — test_ac_kyu_redesign.py:1086
`test_ac12_default_run` (6.9 s) duplicates `test_ac_plain_white.py::test_ac4_default_run`. Drop it and point AC-12 there. Saves about 7 s.

[R-3] minor — test_ac_kyu_redesign.py:1072, :833
Fold `test_ac12_totals` into `test_ac8_renders_every_variant`'s events; use `-d 2026-12-31` there and drop `test_ac8_every_grade_form_renders` (5 renders checking only page size).

[R-4] minor — test_ac_kyu_grades.py vs test_ac_kyu_redesign.py
Drop the kyu_grades side of duplicate pairs (example-config, planned events, 6 of 9 NAME_CASES, default listings, mixed run, heading check, save round trip, recipient explainer, version x3, DECISIONS history pinned x3). Keep kg's `-a all --paper a4` listing and its white-yellow/5/準五級 name cases; version only in `test_ac37_version`.

[R-5] minor — test_ac_kyu_redesign.py:910
`test_ac10_grades_as_before` and `test_ac10_refused_as_before` duplicate kyu_grades' rank tests; drop, point AC-10 there.

[R-6] minor — slow wheel tests duplicated: move kg's purple refusal into `kr::test_ac14_installed_wheel`, drop `kg::test_ac15_installed_wheel`.

[R-7] minor — merge the three AC-4 tests over the same SVG; one A4 case for `test_ac2_sheet_and_scale`; drop `test_ac4_a_long_grade_is_not_shrunk[5-五級]`, `test_ac5_no_precept_on_the_horizontal_sheet` (keep its precondition in test_ac3) and the implied assertion in `test_ac5_crest_false_means_no_watermark`.

[R-8] minor — :940–996 `_config_error` runs 2 subprocesses for 19 cases; keep one subprocess case per key, check value tables in-process.

[R-9] nit — tests/test_kyu.py overlaps (pure-function level; acceptable, add no more).

[R-10] nit paperwork — acceptance.md says 123 and 125 tests; Agreement 4 names a non-existent test; update the AC table after the merges; unused `home` in `test_ac6_variants`.

VERDICT: CHANGES REQUESTED.

### Orchestrator's disposition
- R-1 to R-8, R-10: to the tester (owns tests/acceptance and acceptance.md).
- R-9: kept.
