# plain-white: validation

## Round 1 (2026-10-29)

**Verdict: PASS.** All 23 acceptance criteria and the manual checks M-1..M-5
pass. No failures.

Tree: the developer's working tree on top of `823af58` (uncommitted). The
`ink-memory` files (`tests/acceptance/test_ac_ink_memory.py`,
`tests/acceptance/ink_memory/`, `docs/work/ink-memory/`) belong to the next
item and were excluded from every run. All renders pinned
`-c src/menkyo/example.toml`, with `HOME` / `XDG_CONFIG_HOME` isolated or set
to a scratch directory. Nothing was written to `build/`.

### Suites

| run | command | result |
|---|---|---|
| local (macOS, no Inkscape) | `uv run pytest --ignore=tests/acceptance/test_ac_ink_memory.py --ignore=tests/acceptance/ink_memory` | **300 passed, 9 skipped**. Every skip is a render test: 8 in `test_ac_render.py` and `test_ac_wheel.py::test_ac3_installed_wheel_renders_with_the_font`. Slow tests ran. |
| Docker (`REQUIRE_RENDER=1`) | `scripts/test-docker.sh --ignore=… --ignore=… -rs -q` | **307 passed, 2 skipped**, exit 0. Both skips are git-only (`test_ac_cli_only.py`: no `.git` in the image, `90e5799` unavailable). The render tests ran. |

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 | PASS | the `test_ac1_*` tests pass (the `--all`-with-`-a dan` case was dropped in round 2 of the Agreement) |
| AC-2 | PASS | `test_ac2_*`. Manual: `-v overlay,FULL`, `--variants=full-cream --json` and `-v full --json` from the installed wheel each give one `unknown variant` error and exit 1 |
| AC-3 | PASS | `test_ac3_*`. Manual: `--list --press --json` gives `{"event": "error", "message": "unrecognized arguments: --press"}` and exit 1; the installed wheel's `--press` exits 2 |
| AC-4 | PASS | `test_ac4_*`; installed `--list` prints the 3 overlay PDFs |
| AC-5 | PASS | `test_ac5_*`; `paths._INSTALL_HINT` has only `inkscape` |
| AC-6 | PASS | `test_ac6_*`; packaging `test_ac_json.py` passes |
| AC-7 | PASS | `test_ac7_*`; installed `--list --all` prints 9 lines |
| AC-8 | PASS | `tests/regression/test_golden.py`, goldens from `823af58`. Real renders in Docker are also pixel-identical to `823af58`: dan overlay / overlay-flat / proof, 300 dpi PNG and PDF at 50 dpi, max difference 0 (see M-2) |
| AC-9 | PASS | `test_ac9_*`. Manual: `colour = ["#fff", 3]`, an extra `border_colour`, and an `[awards.colour]` table all load and list normally; `save()` writes 0 `colour` lines and loads back |
| AC-10 | PASS | `test_ac10_*`; the `[paper]` comment speaks of margins on plain white A3 |
| AC-11 | PASS | `test_ac11_*`; `Config.stock_border` kept; README "Printing" item 3 and `example.toml` describe the margins |
| AC-12 | PASS | `test_ac12_help`. Installed `--help`: `comma-separated: overlay,overlay-flat,proof (default: overlay)`, no `--press` |
| AC-13 | PASS | `test_ac13_*`; `border.py` deleted (staged `D`); the installed site-packages has no `border.py` |
| AC-14 | PASS | `test_ac14_*` (bare `\bgs\b` included) |
| AC-15 | PASS | `test_ac15_*`; README read through, see M-5 |
| AC-16 | PASS | `test_ac16_*`. New entry "2026-10-28 — Plain white paper only" names the entries it overrides. Open: the 賞状用紙, drawn-border, `-K` and "Plain white only" items are gone; "Render without Inkscape" and "An annotated version in Dutch" remain |
| AC-17 | PASS | `test_ac17_*`; CLAUDE.md says "Inkscape renders. It is not installed on the Mac" |
| AC-18 | PASS | `test_ac18_*`. The image has no `gs` (`command -v gs` prints nothing, `dpkg -l | grep -ci ghostscript` gives 0); the Docker suite passes with renders |
| AC-19 | PASS | `test_ac_render.py` ran in Docker and passed, including `test_ac13_nothing_coloured` |
| AC-20 | PASS | `test_ac20_installed_wheel` (slow) passed locally and in Docker; M-4 |
| AC-21 | PASS | `test_ac21_readme_image_is_plain_white`; looked at the image (M-3) |
| AC-22 | PASS | the rest of both suites pass |
| AC-23 | PASS | `test_ac23_*`; M-4: `menkyo-0.2.0-py3-none-any.whl`, `menkyo 0.2.0`; `uv.lock` follows (`version = "0.2.0"`) |

### Manual checks

- **M-1** Docker suite as above: renders ran, none skipped for want of
  Inkscape; no Ghostscript in the image.
- **M-2** In the image: rendered `-a dan -v all -f pdf,png -n ヤン・ヤンセン
  -r 2 -d 2026-09-05` with the working tree and `-v
  overlay,overlay-flat,proof` with the same flags from `git archive 823af58`,
  then converted each PDF with `pdftoppm -r 50`. All six images are
  identical (max pixel difference 0), and the 300 dpi PNGs are identical as
  well (4961 × 3508). I looked at the new overlay page: black graded columns
  and crest on white, no frame, no tint. The proof shows its pale dashed
  guides and seal circle as before.
- **M-3** `docs/three_up.png`, 1890 × 455: three sheets side by side, each
  a white sheet with a thin light-grey outline and white margin around it,
  black text and crest, no border, no cream. The sample date reads
  西暦二〇二六年十月二十九日 (the example's `today` on the day it was
  rendered), which is acceptable for an unconfigured build. The README
  caption still fits.
- **M-4** `uv build --wheel` built `menkyo-0.2.0-py3-none-any.whl`. I
  installed it into a fresh venv in the scratchpad and ran it from there,
  with HOME redirected:
  - `--version` printed `menkyo 0.2.0`;
  - `--example-config > ex.toml` worked;
  - `-c ex.toml --list` printed 3 lines, and `--list --all` printed 9;
  - `-v full --json` gave one error event and exit 1;
  - `--press` exited 2, and `--press --json` gave one error event and exit 1;
  - `--help` showed the new `-v` line;
  - site-packages holds no `border.py`.

  Nothing was written to the scratch HOME.
- **M-5** Read the README diff, the `example.toml` `[paper]` comment and the
  `build_diploma.py` docstring:
  - printing is on plain white A3 only, with a single "## Printing" section;
  - bought stock, 賞状用紙, the border and the press are not mentioned;
  - `border` and `safe_inset` are explained as margins that `-v proof` draws;
  - the `colour` paragraph says the key is accepted and ignored;
  - the Variants note says `proof` adds pale guides (review R-5 addressed).

### Edge cases tried beyond the tests

- `colour` as an array, as a table (`[awards.colour]`), and alongside an
  unknown `border_colour` key: all ignored, and listing works.
- `-v overlay,FULL` and `--variants=full-cream --json`: the expected
  `unknown variant` error.
- `-v 'proof, overlay'`: order and spacing are kept, as before.
- `--all -v full` exits 0 and lists all nine files. `--all` overrides `-v`,
  as it always has (AC-22, review R-1), so a caller that still combines
  `--all` with a removed variant gets no error. The behaviour is unchanged
  from before this item. This is a note, not a failure (see below).

### New findings, not in the contract

- **N-1 (note).** `--all` silently overrides an invalid `-v` (and `-a`), so
  `--all -v full` succeeds. This predates the item, and the contract keeps
  it. The portal should not combine `--all` with `-v`. No action proposed.
- **N-2 (for the commit, not the item).** The `DECISIONS.md` diff also
  carries two `## Open` edits that belong to other work: the sentence about
  the flat overlay's peak memory on "Render without Inkscape" (ink-memory),
  and the new "An annotated version in Dutch" item (`annotated-nl`). AC-16
  expects the latter to be present, so it can stay in this commit. The
  orchestrator should decide where the ink-memory sentence goes. The
  `.claude/agents/*.md` edits are the orchestrator's own (open question 9).
- **N-3 (nit).** `build_diploma.py`'s module docstring reflows unevenly:
  "…to be printed on plain white A3\npaper, landscape.  The three things a\n
  calligrapher…". It is cosmetic.
