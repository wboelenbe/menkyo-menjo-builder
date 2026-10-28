# Validation: cli-only

## Round 1

**VERDICT: PASS**

Before validating, the tester fixed its own tests (contract unchanged; recorded
under `## Agreement` in acceptance.md):

- `test_ac11_decisions_entry_appended_history_untouched`: the no-git fallback
  now keeps the `## 2026-10-28 — ` heading it counts (it was dropped by
  `rsplit`, so the test failed in the Docker image, which has no `.git`).
- "release workflow" -> "CI workflow" in `tests/README.md`,
  `tests/acceptance/test_ac_render.py` (docstring) and
  `tests/acceptance/test_ac_wheel.py` (smoke-test docstring).

### Runs

| run | result |
|---|---|
| `uv run pytest` (Mac, no Inkscape) | 238 passed, 10 skipped (all `render`: 9 in `test_ac_render.py`, 1 in `test_ac_wheel.py`) |
| `scripts/test-docker.sh` (`REQUIRE_RENDER=1`) | 245 passed, 2 skipped, 1 xfailed |

Docker skips: `test_ac6_no_leftovers_become_untracked` and
`test_ac7_cli_help_unchanged` (no `.git` in the image); both pass locally.
The xfail is the agreed, deferred `test_ac13_press_inked_k_only` (DECISIONS,
Open). No render test skipped in Docker.

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 | PASS | `test_ac1_removed_paths_are_gone`; `ls build-app packaging web deploy` all absent |
| AC-2 | PASS | `test_ac2_no_references_left`; remaining Homebrew/`Inkscape.app` mentions are tool lookup in `paths.py:64-75` (allowed, Agreement 2) |
| AC-3 | PASS | `test_ac3_*`, `test_ac_paths.py`, `test_checkout_needs_this_projects_pyproject` pass; installed copy: `checkout_root()` is `None`, `default_output_dir()` is `$HOME/Documents/Menkyo` |
| AC-4 | PASS | slow wheel/sdist tests pass; manual `uv build --wheel`: non-dist-info entries are exactly the 11 files under `src/menkyo/`; `import menkyo.service` -> `ModuleNotFoundError` in the installed venv |
| AC-5 | PASS | `test_ac5_*`; manual `uv lock --check` exits 0 ("Resolved 12 packages") |
| AC-6 | PASS | `test_ac6_*` (local); `git ls-files --others --exclude-standard` lists only `docs/work/...` and `tests/acceptance/test_ac_cli_only.py` |
| AC-7 | PASS | `test_ac7_cli_help_unchanged`; manual: `menkyo --help` of a `git archive 90e5799` tree vs the checkout, `COLUMNS=400`, checkout path replaced by `ROOT`: identical. (At the default width the old tree's longer scratch path wraps differently in the `--out` default; that is the path, not the help.) `test_ac_cli.py`, `test_ac_json.py`, `test_packaging_fixes.py` pass |
| AC-8 | PASS | `test_ac8_config_save_kept`; `test_save_load_round_trip`, `test_save_defaults_to_the_user_config` pass |
| AC-9 | PASS | `test_ac9_suite_collects`; `test_golden.py` passes locally and in Docker; Docker: no render skips |
| AC-10 | PASS | `test_ac10_*`; manual read of README Quick start / As a package: dojo-portal named as the front end, install = `uv run` from a checkout or the built wheel, coherent |
| AC-11 | PASS | passes locally (git prefix check against `90e5799`) and in Docker (fixed fallback); `git diff 90e5799 -- DECISIONS.md` only adds the new entry before `## Open` and one `## Open` item |
| AC-12 | PASS | `test_ac12_recipient_docs_kept` |
| AC-13 | PASS | `test_ac_release.py::test_ac14_*`, `test_ac15_*` pass |
| AC-14 | PASS | `test_ac14_*`; manual: wheel built to a scratch dir, installed into a throwaway venv, run from the scratch dir with isolated `HOME`: `menkyo --version` -> `menkyo 0.1.0`; `menkyo -c <checkout>/src/menkyo/example.toml --list` lists the six default PDFs |

### Edge cases beyond the tests

- README's rebuild guidance checked in a throwaway uv consumer project
  (`uv add <path>.whl`): after rebuilding the same version with changed
  content, `uv sync` stops on a hash mismatch, and
  `uv lock --upgrade-package menkyo && uv sync` installs the new build. As
  documented.
- `menkyo -c src/menkyo/example.toml --json -a nope` emits one `error` event
  (`unknown award: nope ...`), unchanged.

### New findings, not in contract

- `dist/Menkyo.app` still exists on this Mac. It is ignored through `dist/`,
  so it cannot be committed; deleting it was out of scope (the user may
  remove it).
- Reviewer R-5 nit is still open in `DECISIONS.md` ("when the `github`
  remote is pushed"; the workflow runs on pushes of `main` and on PRs). Not an
  AC failure; for the developer/reviewer round 2.
