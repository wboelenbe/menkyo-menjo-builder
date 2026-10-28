# Review: cli-only

## Round 1

REVIEW: CHANGES REQUESTED (code sound; one scope finding, minor docs)

Checked: `uv run pytest` 238 passed / 10 render skips; `uv lock --check` passes, no fastapi/httpx/starlette/uvicorn; workflow parses (one job, push main + PR, contents: read, uv build, suite with REQUIRE_RENDER=1, smoke test); wheel = the 11 files under src/menkyo, no service.py; README `uv add <wheel>` verified in a throwaway uv project; README `--json` example matches a real run; paths.py lost only the frozen branch; no commits after 90e5799.

[R-1] major scope — CLAUDE.md:55-65, .claude/agents/developer.md:33-36, .claude/skills/feature/SKILL.md:75-78, DECISIONS.md:213-217, DECISIONS.md:483-486
What: Edits outside acceptance.md not reported by the developer: (a) CLAUDE.md test-docker command, "run both test commands" rule, NAS/github remotes; (b) developer.md hand-off rule; (c) SKILL.md final local gate; (d) DECISIONS "Testing stays as strict" bullet; (e) `## Open` "Plain white only" item.
Suggested fix: Orchestrator confirms who made them; record or revert.
**Orchestrator: resolved, not a defect.** (a)-(c) and (e) were made by the orchestrator on the user's instructions in this session: "make sure that you also run the test suite as part of the development locally" (after the user made the NAS the primary remote), and "drop the coloured variants with fancy backgrounds, stick to the plain white diploma" (recorded as an Open item for a later work item `plain-white`; it is not built here). (d) was written by the developer at the orchestrator's instruction (AC-11 rationale). Kept.

[R-2] minor docs — src/menkyo/config.py:11
What: "(an installed copy's own)" is wrong: `default_path()` checks the per-user file before the repo-root one in a checkout too, so a leftover per-user dojo.toml overrides the checkout's.
Suggested fix: "(any copy, checkout included; written by `config.save()`)"; optionally say in README's configuring section that the per-user file takes precedence.

[R-3] minor docs — README.md:54-62
What: Install examples hardcode `menkyo-0.1.0-...whl`; a bump changes the file name; `pip install` of a rebuilt same-version wheel is a no-op without `--force-reinstall` (uv reinstalls).
Suggested fix: `menkyo-<version>-py3-none-any.whl`, one sentence on re-pointing the path source after a bump, and `--force-reinstall` for pip.

[R-4] minor docs — .claude/skills/feature/SKILL.md:19-20, tests/README.md:25
What: SKILL.md "pushes and tags releases"; tests/README.md "the release workflow" (also test_ac_render.py:4, test_ac_wheel.py:133, tester-owned).
**Orchestrator: SKILL.md fixed. tests/README.md and the two docstrings go to the tester.**

[R-5] nit docs — DECISIONS.md:200-201, CLAUDE.md:62-65
What: The Homebrew formula was not "the app's"; the workflow runs on pushes to `main` (and PRs), not on any `github` push.
Suggested fix: "the PyInstaller `.app`, the Homebrew formula"; "when `main` is pushed to the `github` remote".

## Round 2

REVIEW: CHANGES REQUESTED

`uv run pytest`: 238 passed, 10 render skips. No commits after 90e5799. DECISIONS.md history untouched. R-1 resolved (orchestrator). R-2 fixed. R-3 partly fixed (see R-6). R-4 SKILL.md fixed (tests/ part with the tester). R-5 fixed (one leftover, R-7).

[R-6] major docs/correctness — README.md ("As a package", paragraph after the uv add / pip install block)
What: "uv reinstalls it on its own" is false for a uv path source. Verified in a throwaway project: after a same-version rebuild, `uv sync` fails with "Hash mismatch for `menkyo @ file://…`" (uv.lock pins the sha256); `uv sync --reinstall-package menkyo` fails the same way; only `uv lock --upgrade-package menkyo && uv sync` installs the new code.
Why it matters: the documented hand-over to the portal either fails with a confusing hash error or keeps old code.
Suggested fix: "with uv, run `uv lock --upgrade-package menkyo && uv sync`, because uv.lock pins the wheel's hash; or bump the version for every build the portal takes."

[R-7] nit docs — DECISIONS.md (2026-10-28 entry, "Testing stays as strict")
What: "when the `github` remote is pushed" — the workflow runs on pushes to `main` and on pull requests.
Suggested fix: "when `main` is pushed to the `github` remote (and on pull requests there)".

[R-8] nit docs — README.md (uv add / pip install block)
What: the two commands assume different working directories without saying so.
Suggested fix: same `../menkyo-menjo-builder/dist/…` path for both, or a comment per line.

## Round 3

REVIEW: APPROVE

R-6 fixed (README uv/pip guidance re-verified against real installs: plain `uv sync` stops on a hash mismatch, `uv lock --upgrade-package menkyo && uv sync` installs the rebuild; pip needs `--force-reinstall`). R-7 fixed. R-8 fixed. Tester's no-git fallback verified in a copy without .git (20 passed, 2 expected skips). `uv run pytest`: 238 passed, 10 render skips. No commits during the run.
