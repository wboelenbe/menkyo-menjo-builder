# remove-supersample: acceptance

Item: the user's decision of 2026-10-29: remove the `--supersample` flag and
every supersampling code path. Planned against `96140e0` (HEAD, clean).

## Scope

In:

- `src/menkyo/build_diploma.py`: the `--supersample` argument, its range
  check and its error message ("must be between 1 and 4 ... Cairo ...
  32767 px"), its help text, the `supersample` parameter of
  `_inked_text_image` and of `build_one`, the `supersample=` keyword in
  `main()`'s call to `build_one`, the `if supersample > 1:` branch (alpha
  resize to the 600 dpi box), the `INK_DPI * supersample` export DPI, and
  the docstring and comment wording that mentions supersampling.
- `README.md`: the `--supersample N` row of the Options table.
- `DECISIONS.md`:
  - a new entry of its own, `## 2026-10-29 — …` with a heading that names
    the removal, recording that the flag is gone and why, and that there is
    no `--supersample` left to port for the no-Inkscape item (in the entry,
    not in `## Open`);
  - 2026-09-05 "Output, and the supersampling cap": the heading stays (the
    2026-10-28 plain-white entry cites it by name); its bullets are
    reworded: the second ("`--supersample` is capped at 4 …") and the third
    ("… is what makes any supersampling affordable; Pillow's
    decompression-bomb guard … multi-hundred-megapixel render") no longer
    present supersampling as current;
  - 2026-10-29 "The ink pass grades the alpha alone": the present-tense
    bullet "**`--supersample` scales the alpha alone.** …" is removed or put
    in the past tense; the table's measurements stay as history (Open
    question 1).
- Tests (developer): `tests/test_ink_memory.py::test_alpha_alone_resizes_as_rgba_did`
  is **deleted** (not reworded), and its module docstring's mention goes;
  the `--supersample` comment in `tests/fakes/fake_tool.py` is reworded (the
  `QUERY` box stays; only the comment's reason changes).
- Tests (tester, already done in this PLAN, see "Test changes"):
  `tests/regression/`, `tests/acceptance/test_ac_ink_memory.py` AC-9,
  and the three existing acceptance tests that listed or exercised the flag.

Out:

- Any change to what a run without the flag writes, to the other flags, to
  the `--json` events, to `ink.py` (`ink.coverage` stays: `ink_layer` uses
  it), to `INK_DPI` (600) or to `--dpi`.
- No deprecation shim: `--supersample` becomes an unknown flag like any
  other. The portal never passes it: README's portal guidance names
  `--config --awards --variants --formats --name --rank --date --out --json`
  only, and `grep -rl supersample ~/dev/dojo-portal` finds nothing.
- `Image.MAX_IMAGE_PIXELS = None` in `_inked_text_image`: the developer's
  call (Open question 2); not part of the contract beyond its comment not
  mentioning supersampling.
- `docs/work/*/` paperwork of earlier items: history, left as is.
- No version bump unless the user asks (Open question 3).

## Acceptance criteria

### The flag is gone

- **AC-1 Unknown flag, plain.** `menkyo -c src/menkyo/example.toml … --supersample 2`
  exits **2**, stdout empty, stderr starts `usage: menkyo` and contains
  `unrecognized arguments: --supersample`; no traceback, no "must be
  between"; nothing is written to `--out` and Inkscape is never called.
  The same for `--supersample=2`, `--supersample 1` (the old default),
  `4`, `5`, and the old prefix `--supers 2`; and with `--list` (exit 2,
  nothing listed).
- **AC-2 Unknown flag, `--json`.** The same runs with `--json` exit **1**
  with exactly one stdout line, an `error` event whose `message` contains
  `unrecognized arguments: --supersample` (or `--supers`), stderr empty,
  no `done`, no `planned`, nothing written. Checked in-process through
  `cli()` and as a subprocess using the portal's `--flag=value` form.
- **AC-3 The range check is gone.** `build_diploma.py` no longer contains
  the "must be between 1 and 4" message or its 32767 px explanation.
- **AC-4 Help.** `menkyo --help` does not mention supersampling (any case);
  every other flag is still listed (`--awards --variants --formats --no-ink
  --name --rank --date --honorific --suffix --dpi --all --out --clean --list
  --json --version --example-config --config`).
- **AC-5 Code paths.** `_inked_text_image` takes exactly
  `(base, verb, heading, kw, env)`; no parameter of `build_one`, `main`,
  `cli`, `render` or `document` is about supersampling; no file in
  `src/menkyo/` contains `supersampl` (case-insensitive), docstrings and
  comments included.

### Nothing else changes

- **AC-6 The text layer is exported at 600 dpi.** Every inked overlay asks
  Inkscape for its text layer with `--export-dpi=600` (one call per award,
  stand-in Inkscape); `INK_DPI` is still 600.
- **AC-7 Goldens.** `tests/regression/test_golden.py` passes. Every case
  other than the replaced one is byte-identical to the goldens from
  `823af58` (unchanged by this item); the replaced case `inked-svg`
  (`-a dan -v overlay -f svg -d ''`) pins the same SVG
  (`ccfc5162…`) and text layer (`97caf31f…`) the old `supersample` case
  pinned, with `--export-dpi=600` where that case had 1200. No case passes
  the flag.
- **AC-8 Real render.** With the real Inkscape, `-a dan -v overlay -f svg,pdf
  -d '' --json` exits 0, ends in `done`, progress stages are `text, ink,
  pdf`; the shipped `dan-overlay-sample-textlayer.png` is RGBA, its size is
  the `<image>` box at 600 dpi (±2 px, i.e. not resampled), and every
  non-transparent pixel is the ink colour `#111111` (it went through
  `ink_layer`).
- **AC-9 Installed wheel.** From a wheel installed in a throwaway venv,
  outside the checkout: `--supersample 2` exits 2 with `unrecognized
  arguments`; `--supersample=2 --json` gives one `error` event and exit 1;
  `--help` does not mention it; no installed `menkyo/*.py` mentions it; a
  plain inked run (`-a dan -v overlay -f svg -d '' --json`) still ends in
  `done`.
- **AC-12 Everything else.** The full suite passes locally (`uv run pytest`)
  and in Docker (`scripts/test-docker.sh`), render tests running, not
  skipping. The `--json` event set and fields (README table) and every
  other flag's behaviour are unchanged; the existing acceptance suites
  (`test_ac_json`, `test_ac_cli`, `test_ac_render`, `test_ac_plain_white`,
  `test_ac_ink_memory`, `test_ac_wheel`, …) pass with no edits beyond
  those listed under "Test changes".

### The record

- **AC-10 Docs.** `README.md` does not mention supersampling.
  `DECISIONS.md` has a `## 2026-10-29 …` entry **other than** "The ink pass
  grades the alpha alone", whose heading names supersampling and whose
  body names `--supersample`, says it was removed (wording containing
  removed / gone / dropped / no longer), gives the reason, and mentions
  Inkscape (nothing left to port for the no-Inkscape item). The ink-pass
  entry keeps its heading. The `## Open` section does not mention it. These
  present-tense texts are gone: "`--supersample` is capped at 4 and
  defaults to 1.", "The knob is exposed because it is honest to",
  "is what makes any supersampling affordable" (2026-09-05), and
  "**`--supersample` scales the alpha alone.**" (2026-10-29, ink pass).
  Measurements may stay, in the past tense, pointing at the new entry.
- **AC-11 Nothing else mentions it.** No tracked or untracked-not-ignored
  file contains `supersampl` (case-insensitive), except `DECISIONS.md`,
  `docs/work/**`, `tests/regression/golden_cases.py` (one comment saying
  which case `inked-svg` replaced) and
  `tests/acceptance/test_ac_remove_supersample.py`. That covers
  `tests/test_ink_memory.py`, `tests/fakes/fake_tool.py`, `.github/`,
  `scripts/`, `CLAUDE.md`.

## Test approach per AC

All in `tests/acceptance/test_ac_remove_supersample.py` unless noted.

| AC | automated | manual |
|---|---|---|
| AC-1 | `test_ac1_flag_is_unrecognized[6 forms]`, `test_ac1_flag_is_unrecognized_by_list_too` | |
| AC-2 | `test_ac2_flag_is_a_json_error[6 forms]`, `test_ac2_json_error_from_a_subprocess`, `test_ac2_list_json_error` | |
| AC-3 | `test_ac3_range_message_is_gone` | |
| AC-4 | `test_ac4_help` | |
| AC-5 | `test_ac5_no_supersample_parameter`, `test_ac5_package_never_mentions_it` | |
| AC-6 | `test_ac6_text_layer_exported_at_600_dpi` | |
| AC-7 | `test_ac7_golden_case_replaced`; `tests/regression/test_golden.py` | |
| AC-8 | `test_ac8_real_render_text_layer_is_600_dpi` (render) | M-1 |
| AC-9 | `test_ac9_installed_wheel` (slow) | M-2 |
| AC-10 | `test_ac10_readme`, `test_ac10_decisions_records_the_removal`, `test_ac10_decisions_no_longer_presents_it_as_current` | read the new entry |
| AC-11 | `test_ac11_repository_never_mentions_it` | `grep -rni supersampl` |
| AC-12 | the whole suite, locally and `scripts/test-docker.sh` | |

AC-6 and AC-7 pass already (they guard what must not change); every other
new test fails until the item is built, for the expected reason (exit 0
instead of 2, the range message, the parameter, the mentions).

### Manual checks

- **M-1 Rendered output identical to before (Docker).** In the Docker test
  image, with HOME isolated, render
  `menkyo -c src/menkyo/example.toml -a dan -v overlay -f png,svg -n '' -r '' -d 2026-09-05 --out=<dir>`
  once from the pre-change snapshot (`git archive <snapshot commit>` into a
  temp dir, run with that `src/` on `PYTHONPATH`) and once from the result.
  Expect: the SVGs byte-identical; the `-textlayer.png` byte-identical (the
  ink pass is deterministic); the PNGs pixel-identical (compare with
  Pillow, not bytes). Convert the PNG to a small preview and look at it.
- **M-2 Installed wheel from outside the checkout.** `uv build --wheel`,
  install into a throwaway venv, from `/tmp`-like scratch with HOME
  isolated: `menkyo --version`; `menkyo -c <example> --supersample 2`
  (exit 2); the same with `--json` (one error line, exit 1); `menkyo
  --help | grep -i supersampl` (nothing).

## Test changes (tests/acceptance, tests/regression)

Made by the tester in PLAN; each one follows from the user's decision to
remove the flag, so the earlier contracts that pinned it no longer hold.

- **`tests/regression/golden_cases.py` and `golden/manifest.json`.** The
  case `supersample` (`-a dan -v overlay -f svg --supersample 2 -d ''`)
  pinned output of a flag that no longer exists; it is replaced by
  `inked-svg`, the same argv without the flag. The goldens were
  regenerated with `make_golden.py` from the same baseline, `823af58`:
  every other case and every list case came out identical, the SVG blobs
  in `golden/svg/` are unchanged (the two the old case pinned are the new
  case's too), and the only difference in the manifest is the case's id,
  its argv and `--export-dpi=600` in place of `1200`. This keeps coverage
  of the inked `-f svg` path for the dan overlay with sample fill-ins,
  which no other case had.
- **`tests/acceptance/test_ac_ink_memory.py`.** `test_ac9_supersample_2`
  removed (ink-memory AC-9 tested the flag); `MEMORY_RATIO`'s comment and
  AC-8's docstring no longer refer to it. ink-memory's validation of AC-9
  stands as history.
- **`tests/acceptance/test_ac_json.py`.** The `--supersample 5` case of
  `test_ac9_user_errors` removed; AC-2 here covers the flag under `--json`.
- **`tests/acceptance/test_ac_cli.py`** (`test_ac17_help`) and
  **`tests/acceptance/test_ac_plain_white.py`** (`test_ac12_help`):
  `--supersample` removed from the flags the help must list.

Made by the tester during the build (amendment), after the developer's
change made three earlier tests fail locally. They passed in Docker only
because the image has no `.git`, so the comparisons with old commits skip
there.

- **`tests/acceptance/test_ac_cli_only.py::test_ac7_cli_help_unchanged`.**
  It compares the help's flags with `90e5799`'s minus `--press`.
  `--supersample` is now added to the removed flags as well (AC-1). No
  other flag may disappear, and none may appear.
- **`tests/acceptance/test_ac_cli_only.py::test_ac11_decisions_entry_appended_history_untouched`**
  and **`tests/acceptance/test_ac_plain_white.py::test_ac16_decisions_entry_appended_history_untouched`.**
  Both require DECISIONS.md to start byte for byte with the entries at
  `90e5799` and `823af58`. AC-10 (agreed, user-approved) rewords the last
  two bullets of "2026-09-05 — Output, and the supersampling cap" (the
  `--supersample` cap bullet and the `--export-area-drawing` bullet) into
  the past tense. Both tests now replace exactly that span with a
  placeholder on both sides before comparing: it runs from the line
  starting ``- **`--supersample` `` to the "Printing the three hand
  slots" heading. The rest of the history is still compared byte for byte.
  The helper asserts that it found the span, so if the bullets are renamed
  or moved, the test fails instead of matching nothing. The ink-pass
  bullet that AC-10 also rewords needs no exception here, because it was
  written in `96140e0`, after both baselines.
- In all three edits the flag's name is split in two (`"--super" "sample"`),
  and the comments do not spell it, so the two files stay out of AC-11's
  scan for mentions and its `ALLOWED` list stays unchanged (reviewer R-1).

These edits pass both before and after the change; with them and without the
new file the suite is green today (351 passed, 11 skipped locally).

Later, by render-without-inkscape (2026-10-29, tester):

- `test_ac5_no_supersample_parameter` pinned `_inked_text_image`'s whole
  signature, `(base, verb, heading, kw, env)`. `env` carried the Inkscape tool
  environment, which no longer exists. The test now pins the first four
  parameters and checks that none of the parameters is a supersampling one,
  which is this AC's substance. The contract is unchanged; only the
  incidental `env` is released.
- The tests that used the stand-in inkscape now render for real (see that
  item's acceptance.md, "Changes to the existing suite").

## Open questions

1. **DECISIONS.md's own rule.** (Settled as recommended, round 2.) Its preamble says decisions later
   overridden are *deleted rather than annotated*. The work item says
   history entries stay and the record is adjusted. Recommendation: follow
   the work item (the user's instruction is the later and more specific
   one): keep the 2026-09-05 measurements and the ink-memory table, rewrite
   the 2026-09-05 bullet in the past tense pointing at the new entry, and
   add the 2026-10-29 entry. The tests only pin the new entry and the two
   present-tense sentences, so deleting the old material instead would
   also pass.
2. **`Image.MAX_IMAGE_PIXELS = None`.** (Settled as recommended, round 2.) At 1x the C-1 text layer is
   7299 x 3733 = 27 Mpx, below Pillow's 89 Mpx warning; the comment
   justifies it by "the higher factors". Recommendation: keep the line
   (a larger sheet or a long block could approach the limit; removing it
   is a separate decision), reword the comment. Not tested beyond AC-5.
3. **Version bump.** (Settled by the user: keep 0.2.0, no bump.) Removing a CLI flag is a CLI change (CLAUDE.md: a
   decision for the user). The portal never passes it, so nothing breaks.
   Recommendation: bump to 0.3.0 when the user next releases; not part of
   this item unless the user says so.
4. **Side effect on `--su`.** (Accepted, round 2.) Today `--su X` is "ambiguous option: --su
   could match --suffix, --supersample"; afterwards argparse takes it as
   `--suffix X`. Harmless (the portal uses full flag names), recorded so
   it is not a surprise; not tested, to avoid pinning an argparse quirk.

## Agreement

Round 2 (2026-10-29), developer feedback "ready to build: yes", all taken:

- AC-9: the wheel's `--help` now runs with cwd the test's tmp_path, not
  the checkout (`_help(..., cwd=tmp_path)`).
- AC-10 widened: the ink-pass entry's present-tense bullet
  "**`--supersample` scales the alpha alone.**" and the 2026-09-05 third
  bullet ("what makes any supersampling affordable …") must go or become
  past tense; both are named in Scope and pinned in
  `test_ac10_decisions_no_longer_presents_it_as_current`.
- AC-10 tightened: the removal entry must be its own 2026-10-29 section,
  heading naming supersampling, not the ink-pass entry reworded
  (`test_ac10_decisions_records_the_removal` excludes that heading and
  checks it still exists), and it must mention Inkscape (nothing to port
  for the no-Inkscape item).
- The 2026-09-05 heading "Output, and the supersampling cap" stays, since
  the plain-white entry cites it; AC-11 allows it (DECISIONS.md is exempt).
- `test_alpha_alone_resizes_as_rgba_did` is deleted, not reworded.
- Open questions 1, 2 and 4: the developer agrees with the recommendations;
  they are settled as recommended. Question 3 (version bump) stays open:
  the coordinator asks the user.

Round 3 (2026-10-29): the user decided open question 3: keep 0.2.0, no
version bump. During the build, three earlier tests were amended for AC-1
and AC-10; see "Test changes".
