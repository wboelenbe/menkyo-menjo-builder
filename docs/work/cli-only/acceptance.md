# Acceptance: cli-only (no Mac app, no web front end, no deploy, no release flow)

Work item on top of `90e5799`. The user decided: "there will be no mac app,
remove all references to it", and, asked how far: "also drop web/ +
deploy/". Later, also decided by the user: there is no GitHub Release flow;
the portal builds the wheel from the sibling checkout (`uv build --wheel`,
from the portal's own deploy script, in the portal repository).

dojo-portal (a separate repository) is the only front end. It runs
`menkyo … --json` in a subprocess. A future requirement: pip-installable
with no system dependencies. A parallel spike looks at replacing Inkscape;
that is **not** part of this item, and Inkscape and Ghostscript stay.

## Scope

**In**

- Remove `src/gui.py`, all of `packaging/` (PyInstaller spec,
  `build_app.sh`, `entitlements.plist`, the Homebrew formula), `web/`,
  `deploy/`, `src/menkyo/service.py`, and the root `.dockerignore`. The root
  `.dockerignore` was the context for `deploy/Dockerfile`; the test image
  keeps its own `tests/docker/Dockerfile.dockerignore`.
- `src/menkyo/paths.py`: remove the frozen-app code (`sys.frozen`,
  `_MEIPASS`) and the comments about it. Keep `user_data_dir`, tool lookup
  (`find_tool`, `require_tool`, `tool_env`, `_EXTRA_BIN`), `checkout_root`
  and the `default_output_dir` behaviour for a checkout and for an installed
  copy.
- `pyproject.toml`: the dev group loses fastapi and httpx, the starlette
  `filterwarnings` entry goes, the comments that name the front ends go, and
  `uv.lock` is regenerated to match.
- `.gitignore`: drop `build-app/`, `packaging/.venv/` and `deploy/.env`.
  Keep `dist/` (uv build output). The same stale entries also go from
  `tests/docker/Dockerfile.dockerignore` (see open question 1).
- `.github/workflows/package.yml`: remove the `release` job, the
  tag-equals-version step, the `v*` tag trigger and the dist upload. Keep
  `uv build`, the suite with `REQUIRE_RENDER=1` and the installed-wheel smoke
  test on push and pull request.
- Docs:
  - README: rewrite the parts about the app, Homebrew, the Tk window, the web
    page and deploy. Install means the wheel or `uv run` from a checkout, and
    the front end is dojo-portal. Replace "Making a release" and the
    GitHub-Release `uv add` URL with: build the wheel with
    `uv build --wheel`, and the consumer installs that file (for example as a
    uv path source). Keep "the version lives in pyproject.toml" and
    `menkyo --version`.
  - CLAUDE.md: the layout section, the consumer line, and the
    commands/releases lines.
  - DECISIONS.md: add one new dated entry, `## 2026-10-28 — …`, placed
    before `## Open`. It records both decisions (no app, web or deploy; no
    release flow) and why: a single consumer, built on the same Mac, and CI
    still tests every push. Earlier entries stay exactly as written.
  - `.claude/agents/reviewer.md`: its "frozen .app and Homebrew" checklist
    line (see open question 3).
- `config.save()` stays a supported helper for writing a `dojo.toml`, and
  stays tested.

**Out**

- Replacing Inkscape or Ghostscript.
- Deleting the user's local, ignored artifacts (`dist/Menkyo.app`,
  `build-app/`, `packaging/.venv/`, `web/__pycache__/`). See open question 1.
- The portal's own build and install script.
- Any change to output, CLI flags, or the `--json` contract.

## Acceptance criteria

**AC-1: The removed paths are gone.** None of `src/gui.py`,
`src/menkyo/service.py`, the root `.dockerignore`, or any file under
`packaging/`, `web/` or `deploy/` is tracked or present as an unignored file.
The tests that existed only for removed code are gone too:
`tests/regression/test_web.py`, `tests/regression/test_service.py` and
`tests/acceptance/test_ac_frontends.py`.

**AC-2: No references are left.** No tracked or unignored text file mentions
the removed things. Excluded: `DECISIONS.md` (its history is kept), `docs/work/`,
the golden snapshots, and the test file that lists the patterns. The patterns
are: `gui.py`, `menkyo-gui`, `Tk`/`tkinter`/`python-tk`, PyInstaller,
`_MEIPASS`, `frozen` (except uv's `--frozen` flag), `.dmg`, `Menkyo.app` or a
bare `.app`, `build_app`/`build-app`, entitlements, notarize/notarytool,
codesign, "desktop app/window", "Mac app", `packaging/homebrew`, `menkyo.rb`,
`<tap>`, `brew tap`, the path prefixes `packaging/`, `web/` and `deploy/`,
Caddy, fastapi, uvicorn, httpx, starlette, `service.py`, `menkyo.service`,
imports of `service`, `make_argv`, `run_build`, `FormError`,
"GitHub Release(s)", `releases/download`, and "Making a release".
Deliberately still allowed: Inkscape's own `Inkscape.app` directory and the
Homebrew *tool* directories that `find_tool()` searches (open question 2).

**AC-3: `paths.py` has no frozen-app branch, and nothing else changes.**
- With `sys.frozen = True` and `sys._MEIPASS` set, a checkout still reports
  its repository root, `./build`, the root `dojo.toml` path, and the
  package's own fonts.
- `checkout_root`, `resource`, `user_data_dir`, `default_output_dir`,
  `find_tool`, `require_tool`, `tool_env` and `system_font_dirs` all still
  exist.
- Checkout vs installed behaviour is unchanged: the packaging item's AC-4
  tests in `test_ac_paths.py` and `test_checkout_needs_this_projects_pyproject`
  still pass, unedited.

**AC-4: The wheel is the package minus `service.py`.** The non-dist-info
entries of the built wheel are exactly the files under `src/menkyo/` (minus
caches), and `menkyo/service.py` is not among them. `import menkyo.service`
raises `ModuleNotFoundError`. The sdist holds no `service.py`, no
`src/gui.py`, and nothing under `packaging/`, `web/` or `deploy/`. Wheel
name, metadata, entry point and installed-wheel behaviour stay as they are
(packaging AC-2 and AC-3).

**AC-5: Dependencies.** The `dev` dependency group is `pytest` only. No
`filterwarnings` entry mentions httpx or starlette. Runtime dependencies are
unchanged (`pillow>=9.0`, `numpy>=1.22`, `scipy>=1.8`), and so is the
`menkyo` script. `uv.lock` has no fastapi, httpx, starlette or uvicorn
package, and its `menkyo` dev group is `pytest` only. `uv lock --check`
passes, because CI runs `uv run --frozen`.

**AC-6: Ignore files.** `.gitignore` no longer lists `build-app/`,
`packaging/.venv/` or `deploy/.env`. It still lists `build/`, `dojo.toml`,
`crest/`, `ref/`, `dist/`, `__pycache__/` and `*.pyc`. The test image's
`Dockerfile.dockerignore` drops the same three and keeps every
personal-data and machine-local entry. After the change,
`git ls-files --others --exclude-standard` shows nothing under `build-app/`,
`packaging/`, `web/` or `deploy/`, so no local leftover can be committed by
accident.

**AC-7: The CLI is unchanged.** `menkyo --help` from the checkout is
byte-identical to the help at `90e5799` once the checkout path is normalised.
The existing CLI and `--json` acceptance tests (`test_ac_cli.py`,
`test_ac_json.py`, `test_packaging_fixes.py`) pass unedited.

**AC-8: `config.save()` is kept and tested.** `menkyo.config.save` exists,
and `tests/regression/test_config.py` still has and passes
`test_save_load_round_trip` and `test_save_defaults_to_the_user_config`.

**AC-9: The suite collects and the golden output is unchanged.**
`uv run pytest --collect-only` exits 0 and collects nothing from the removed
test files. `tests/regression/test_golden.py` passes unedited against the
unchanged `golden/manifest.json`: byte-identical SVGs, text layers,
Inkscape/Ghostscript calls, stdout and `--list`. The full suite passes
locally and in the Docker image with `REQUIRE_RENDER=1`, where render tests
run and do not skip.

**AC-10: README and CLAUDE.md describe a command-line tool.**
- README: no heading about the Mac, the app, building the app or a web
  page. README mentions dojo-portal as the front end and `uv run menkyo`, and
  still documents the `--json` events (`progress`, `file`, `done`, `error`).
- CLAUDE.md's `## Layout` section names `src/menkyo/` and none of gui, web,
  packaging or deploy.

**AC-11: DECISIONS.md.** Everything above `## Open` at `90e5799` is still
there, unchanged, as a prefix. Exactly one new entry follows it, headed
`## 2026-10-28 — …`. Its text mentions the portal and `--json`, and the
removal of the app, the web front end and deploy. It also covers the release
flow and `uv build` (AC-14's reason).

**AC-12: The recipient docs stay.** `docs/three_up.png`, `docs/README.md` and
`docs/{dan,renshi,shihan}-explained.md` still exist.

**AC-13: The CI workflow tests and publishes nothing.** It triggers on push
(to main) and on pull_request, with no tag trigger. It has one job, which runs
`uv build`, then the suite via `uv run … pytest` with `REQUIRE_RENDER=1`, then
"Smoke test the installed wheel" on the wheel it built. It has no `release`
job, no `refs/tags`/`GITHUB_REF_NAME` check, no `gh release`, no
upload/download-artifact, and no `contents: write`. The personal-data checks
on the test image (packaging AC-15) are unchanged.

**AC-14: Building the wheel locally is the documented release.** README says
`uv build --wheel` and shows the consumer installing the built `.whl` (for
example `uv add <path>.whl`, a uv path source, or `pip install …whl`). It
still mentions `menkyo --version` and that the version lives in
`pyproject.toml`. It has no `git tag` release step. CLAUDE.md says
`uv build --wheel` and no longer describes a tag-driven release that the
workflow publishes.

## Validation that moves nowhere (for the user to confirm the portal owns it)

`service.make_argv` validated the form before calling the generator. The CLI
does not repeat these checks. Once `service.py` is gone, **dojo-portal has to
do these itself**:

| service.py did | the CLI does | so the portal must |
|---|---|---|
| name stripped; at most `MAX_NAME` = 40 characters | no strip, no length limit (a long name shrinks to fit the column) | strip, and cap the length (40) |
| grade must be one of `GRADES`: '' or 初段 … 十段 | accepts 1–10, romaji (`nidan`), kanji, **and any literal text** (師範, 弐段, anything) | whitelist the grades |
| grade silently dropped on an award without a grade column (shihan, renshi) | a `--rank` on a licence **is printed** (rank column forced on) | send `--rank=` for licences |
| output limited to `overlay`, `full-cream`, or both | accepts any variant (`proof`, `full`, `overlay-flat`, …) | offer only the kinds it wants |
| always `--formats=pdf` | default formats per variant | pass `--formats=pdf` |
| **every slot passed explicitly** (`--name=`, `--rank=`, `--date=`), so the example's `[sample]` can never reach a real certificate | an omitted flag falls back to `[sample]` | always pass all three, empty if blank |
| `--flag=value` form, so a value starting with `-` is never read as a flag | argparse reads `--name -n` as a flag | use `--flag=value` |
| date must be valid ISO; 'today' rejected | ISO, '' or 'today'; otherwise exits with an error (an `error` event under `--json`) | nothing new (the CLI reports it), but expect 'today' to work |
| folder required | defaults to `./build` (checkout) or `~/Documents/Menkyo` (installed) | always pass `--out` |
| unknown award → "Unknown certificate type." | `unknown award: …` error | nothing new |
| `run_build` mapped a failing or missing Inkscape to a message | `--json` `error` event with the same information (packaging AC-9) | nothing new |

## Test approach

| AC | test |
|---|---|
| AC-1 | `tests/acceptance/test_ac_cli_only.py::test_ac1_removed_paths_are_gone` |
| AC-2 | `test_ac_cli_only.py::test_ac2_no_references_left` |
| AC-3 | `test_ac_cli_only.py::test_ac3_frozen_flag_no_longer_matters`, `test_ac3_paths_api_kept`; the existing `test_ac_paths.py` (AC-4) and `test_packaging_fixes.py::test_checkout_needs_this_projects_pyproject` |
| AC-4 | `test_ac_cli_only.py::test_ac4_package_has_no_service_module`, `test_ac4_wheel_is_exactly_the_package` (slow), `test_ac4_sdist_has_no_removed_paths` (slow); the existing `test_ac_wheel.py` |
| AC-5 | `test_ac5_dev_group_is_pytest_only`, `test_ac5_runtime_dependencies_unchanged`, `test_ac5_lockfile_has_no_web_packages`; **manual:** `uv lock --check` exits 0 |
| AC-6 | `test_ac6_gitignore_cleaned_up`, `test_ac6_test_image_ignore_cleaned_up`, `test_ac6_no_leftovers_become_untracked` (skips without git) |
| AC-7 | `test_ac7_cli_help_unchanged` (git archive of `90e5799`; skips without git); the existing `test_ac_cli.py`, `test_ac_json.py`, `test_packaging_fixes.py` |
| AC-8 | `test_ac8_config_save_kept`; the existing `tests/regression/test_config.py` |
| AC-9 | `test_ac9_suite_collects`; the existing `tests/regression/test_golden.py`; **manual:** `scripts/test-docker.sh` passes with no render skips |
| AC-10 | `test_ac10_readme`, `test_ac10_claude_md_layout`; **manual:** read the README top to bottom, to confirm the install story is coherent and the dojo-portal is named as the front end |
| AC-11 | `test_ac11_decisions_entry_appended_history_untouched` (the prefix check needs git) |
| AC-12 | `test_ac12_recipient_docs_kept` |
| AC-13 | `tests/acceptance/test_ac_release.py::test_ac14_workflow_tests_every_push_with_renders`, `test_ac14_workflow_publishes_nothing` (packaging's AC-14 tests, rewritten to the new contract); `test_ac15_*` unchanged |
| AC-14 | `test_ac_cli_only.py::test_ac14_readme_builds_the_wheel_locally`, `test_ac14_claude_md_has_no_release_flow`; **manual:** `uv build --wheel` in the checkout, then install the wheel into a throwaway venv and run `menkyo --version` and `menkyo -c <example> --list` from outside the checkout |

State at planning time (`90e5799`, before any production change): with
`-m "not slow"`, 15 tests fail as expected, all of them the new or rewritten
cli-only tests, and 213 pass. The slow run fails exactly the two AC-4 wheel
and sdist tests. AC-6's leftover check, AC-7, AC-8, AC-9 and AC-12 already
pass; they guard against regressions.

## Test changes in this item (tester-owned)

- Deleted `tests/regression/test_web.py`, `tests/regression/test_service.py`
  and `tests/acceptance/test_ac_frontends.py` (packaging AC-12). Each tested
  only removed code.
- `tests/acceptance/test_ac_wheel.py`: `service` is out of `MODULES`, and
  the checks that the wheel and sdist leave out `gui.py`, `app.py`,
  `index.html`, `web`, `packaging` and `deploy` are gone, because nothing
  exists to leave out. AC-4 here checks for an exact match instead.
- `tests/acceptance/test_ac_release.py`: packaging's AC-14 is rewritten to
  the no-release contract (AC-13 here).
- New file: `tests/acceptance/test_ac_cli_only.py`.

Not tester-owned, and left for the developer: `tests/conftest.py`'s comment
"(Homebrew etc.)" is about tool lookup and may stay.
`tests/docker/Dockerfile.dockerignore` loses its stale lines (AC-6).

## Open questions

1. **Local leftovers versus `.gitignore`.** `build-app/` and
   `packaging/.venv/` exist on this Mac, and `web/__pycache__/` stays
   ignored through `__pycache__/`. Removing their `.gitignore` lines (in
   scope) while keeping the directories (deleting them is out of scope)
   would turn them into untracked files that a commit could pick up.
   AC-6's `test_ac6_no_leftovers_become_untracked` fails in that case.
   **Recommendation:** the user deletes `build-app/`, `packaging/.venv/`
   (and `dist/Menkyo.app`, if wanted) before the orchestrator's final
   commit. The alternative is to keep those two ignore lines until they are
   gone. Which one?
2. **Homebrew as a place to find Inkscape.** `paths.py` still searches
   `/opt/homebrew/bin`, `/usr/local/bin`, MacPorts and
   `/Applications/Inkscape.app`, and the missing-tool hint says
   `brew install --cask inkscape` / `brew install ghostscript`. That is tool
   lookup, which stays in scope, and not the removed menkyo formula, so AC-2
   allows it. The comment about a "Finder-launched app" has to be reworded,
   because it falls under "frozen/.app". Confirm that tool lookup keeps the
   Homebrew paths.
3. **`.claude/agents/reviewer.md`** asks whether code works "from a
   checkout, an installed wheel, a frozen .app and Homebrew". AC-2 scans it,
   so the developer must reword it (recommended: "a checkout and an
   installed wheel"). Is editing the agent definitions inside this item OK?
4. **DECISIONS.md history versus its own rule.** The file's preamble says
   overridden decisions are deleted. The 2026-10-28 package entry still says
   "The Tk window, the FastAPI front end, PyInstaller and Docker build on it",
   and describes the tag-and-release flow and `service.run_build`. The brief
   says history stays as written, and AC-11 enforces that. Confirm that this
   wins over the preamble.
5. **Validation table above.** Does the user confirm dojo-portal owns each
   "the portal must" row, in particular always passing `--name= --rank=
   --date=` (or the `[sample]` placeholder reaches a real certificate) and
   blanking the rank for licences? If any of these should move into the CLI
   instead (e.g. a name-length cap), that is a separate item, because it
   would change CLI behaviour.
6. **Workflow job name and the sdist.** AC-13 requires exactly one job, of
   any name. The plain `uv build` still makes an sdist, which the AC-4 sdist
   test and packaging AC-2 check. Keep building both, or switch CI to
   `uv build --wheel` and drop the sdist tests? Recommendation: keep both,
   since it costs nothing.

## Agreement

Orchestrator decisions on the open questions (recorded by the tester at the
start of VALIDATE round 1):

1. **Local leftovers:** the orchestrator deleted the local leftovers
   (`build-app/`, `packaging/.venv/` and the like) with the user's approval,
   so the three `.gitignore` lines go as planned and AC-6's leftover check
   stands as written.
2. **Inkscape lookup paths** (Homebrew, MacPorts, `Inkscape.app`) stay until
   the no-inkscape spike decides. AC-2 keeps allowing them.
3. **Agent definitions:** the developer may edit `.claude/agents/reviewer.md`
   and `CLAUDE.md` in this item (the user approved).
4. **DECISIONS.md history** stays as written; AC-11's prefix check wins over
   the file's preamble.
5. **Validation table:** dojo-portal owns every "the portal must" row. No
   CLI behaviour changes in this item.
6. **CI keeps the sdist:** the workflow runs plain `uv build`, and the AC-4
   sdist test and packaging AC-2 stay.

Review R-1 (edits outside this contract): the changes to CLAUDE.md (test
commands, the "run both test commands" rule, the NAS/github remotes),
`.claude/agents/developer.md`, `.claude/skills/feature/SKILL.md`, the
DECISIONS "Testing stays as strict" bullet and the `## Open` "Plain white
only" item are the orchestrator's, made on the user's instructions. They are
accepted as part of this item and are not defects against this contract.

Tester-side fixes in VALIDATE round 1 (the contract is unchanged):
`test_ac11_decisions_entry_appended_history_untouched` kept the heading in
its no-git fallback (it was dropped and then counted, so the test failed in
Docker); "release workflow" became "CI workflow" in `tests/README.md`,
`tests/acceptance/test_ac_render.py` and `tests/acceptance/test_ac_wheel.py`.
