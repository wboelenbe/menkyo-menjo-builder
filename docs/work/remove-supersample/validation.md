# remove-supersample: validation

## Round 1

Date 2026-10-29. Baseline `96140e0` (HEAD); the change is the uncommitted
working tree. Contract: acceptance.md (Round 3), review.md Round 1 APPROVE.

**Verdict: PASS.**

### Suite runs

- `uv run pytest` (Mac, no Inkscape): **376 passed, 12 skipped** in 43 s.
  The 12 skips are all "Inkscape not installed" (render tests).
  `tests/acceptance/test_ac_remove_supersample.py`: 26 passed, 1 skipped
  (AC-8, render).
- `scripts/test-docker.sh` (real Inkscape, `REQUIRE_RENDER=1`): **386
  passed, 2 skipped** in 75 s. The only skips are
  `test_ac_cli_only.py:50` and `:297` (no `.git` in the image). There are no
  render skips, so AC-8 and the other render tests ran.
- `uvx pyflakes src/menkyo/build_diploma.py`: clean. The bbox `w`/`h` are
  still used and nothing is left unused.

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 | PASS | `test_ac1_*` (7 cases) pass. Wheel, by hand: `--supersample 2` and `--supersample 1 --list` give exit 2, the usage line plus `unrecognized arguments: --supersample …`, no output dir created |
| AC-2 | PASS | `test_ac2_*` (8) pass. Wheel: `--supersample=2 --json` gives exit 1, stdout exactly `{"event": "error", "message": "unrecognized arguments: --supersample=2"}`, stderr 0 bytes, nothing written |
| AC-3 | PASS | `test_ac3_range_message_is_gone`. The diff removes the `raise SystemExit("--supersample must be between …")` block |
| AC-4 | PASS | `test_ac4_help`. Installed wheel: `--help \| grep -ci supersampl` returns 0 |
| AC-5 | PASS | `test_ac5_*`. The diff shows `_inked_text_image(base, verb, heading, kw, env)` and no `supersample` in `build_one`/`main` |
| AC-6 | PASS | `test_ac6_text_layer_exported_at_600_dpi`. The diff shows `f"--export-dpi={INK_DPI:g}"` |
| AC-7 | PASS | `test_ac7_golden_case_replaced` and `tests/regression/test_golden.py` pass, locally and in Docker |
| AC-8 | PASS | `test_ac8_real_render_text_layer_is_600_dpi` ran in Docker (no render skips) and passed. M-1 below confirms by hand: the text layer is RGBA 7299x3733, its only colour is (17,17,17) |
| AC-9 | PASS | `test_ac9_installed_wheel` passes. M-2 below covers the same by hand |
| AC-10 | PASS | `test_ac10_*` (3) pass. I read the new "2026-10-29 — Supersampling removed" entry: it states the reason (analytic AA, ~0.012/255), gives the no-shim behaviour, notes the `--su` side effect, and covers Inkscape and nothing to port. The 2026-09-05 bullets and the ink-pass bullet are now past tense. `## Open` is untouched. README loses only the Options row |
| AC-11 | PASS | `test_ac11_repository_never_mentions_it`. `git ls-files -co --exclude-standard \| xargs grep -li supersampl` lists only DECISIONS.md, `docs/work/**`, `tests/regression/golden_cases.py` and `tests/acceptance/test_ac_remove_supersample.py` |
| AC-12 | PASS | both full runs are green (above). The acceptance suites carry only the edits listed under "Test changes" |

### M-1: rendered output identical (Docker)

I extracted `git archive 96140e0 src` and mounted it into the `menkyo-test`
image. Both runs used `HOME=/tmp/h XDG_CONFIG_HOME=/tmp/x` and cwd `/tmp`:

    PYTHONPATH=<tree>/src python -m menkyo -c /src/src/menkyo/example.toml \
      -a dan -v overlay -f png,svg -n '' -r '' -d 2026-09-05 --out=/out/<tree>

I checked that `PYTHONPATH` really selects the tree: `menkyo.__file__` is
`/head/src/...` and `/src/src/...` respectively. The SHA-256 of each file
from HEAD and from the working tree:

- `dan-overlay.svg`: `5d608212…` for both, byte-identical
- `dan-overlay-textlayer.png`: `fb6ac5e4…` for both, byte-identical
- `dan-overlay.png`: `283f48cb…` for both. It is byte-identical, which is
  stronger than the contract asks. Pillow's difference bbox is `None` (RGBA
  4961x3508, 300 dpi)

I viewed a 1400 px preview. The A3 landscape sheet has 段位免状 at the
right, a large inked 右授与ス, the date 西暦二〇二六年九月五日, ○○流柔術 /
○○道場 / 師範 山田太郎 / 柔能制剛 (example placeholders) and the crest
seal. The name and rank slots are blank as requested. Nothing is missing
or misplaced.

### M-2: installed wheel outside the checkout

`uv build --wheel` gave `menkyo-0.2.0-py3-none-any.whl`. I installed it into
a scratch venv and ran it from `/tmp` with `HOME`/`XDG_CONFIG_HOME`
isolated and the example config copied out:

- `menkyo --version`: `menkyo 0.2.0`
- `menkyo -c example.toml -a dan --supersample 2 --out=…`: exit 2, usage
  plus `unrecognized arguments: --supersample 2`, no output dir
- `… --supersample=2 --json`: exit 1, one `error` line, empty stderr
- `menkyo --help | grep -ci supersampl`: 0
- `grep -rli supersampl site-packages/menkyo/`: no matches

### Edge cases (installed wheel, bash)

| argv (plus `-c example.toml --out=…`) | result |
|---|---|
| `--supersample` (no value) | exit 2, `unrecognized arguments: --supersample` |
| `--supersample= --json` | exit 1, one error event (`--supersample=`) |
| `--supersample=abc --json` | exit 1, one error event |
| `--SUPERSAMPLE 2` | exit 2, unrecognized |
| `--supersample 2 --bogus 3 --json` | exit 1, one event naming both |
| `-a nope --supersample 2 --json` | exit 1. The unknown flag is reported before the award check, as for any unknown flag |
| `--json --list --supersample 2` | exit 1, one error event, nothing listed |
| `--su X --list` | exit 0, lists `…-overlay-X.pdf`. `--su` is now `--suffix` (Open question 4, accepted and recorded in DECISIONS.md) |
| `--version --supersample 2` | exit 0, `menkyo 0.2.0`. argparse's `--version` action exits before unknown arguments are checked. This happens for any unknown flag, so it is not a regression |

No output directory was created in any of these runs.

### New findings, not in contract

None.
