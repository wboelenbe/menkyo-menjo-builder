# CLAUDE.md

Generator for Japanese dan-grade and menkyo certificates (A3 landscape,
vertical text), shipped as the Python package `menkyo` with a `menkyo` CLI.
Read [README.md](README.md) for usage and [DECISIONS.md](DECISIONS.md) for
why things are the way they are; its `## Open` section is the todo list.

## Context & working with the user

- Owner: Wouter, who teaches Hakko Ryu jujutsu (dōjō in Vorselaar). The
  certificates are printed and issued for real.
- Consumer: `~/dev/dojo-portal` (Django) will pin a release wheel and run
  `menkyo … --json` in a subprocess. Keep the CLI flags and the `--json`
  events (README, "As a package") backwards compatible; changing them is a
  decision for the user.
- When something is unclear, **ask questions one at a time** (requirements
  first, then design, then details). Recommend an option rather than listing
  every alternative.
- Build work runs through the `/feature` skill: tester, developer, reviewer
  ([.claude/agents/](.claude/agents/)).
- **Commits:** the orchestrator makes exactly two per `/feature` run (a
  snapshot before, the validated result after). Never push, tag, amend,
  stash, reset, rebase or switch branches; the user pushes and tags releases.
  Subagents never change git state.

## Personal data (non-negotiable)

- `dojo.toml` in the repository root and
  `~/Library/Application Support/Menkyo/dojo.toml` hold a real dōjō's
  identity, and a run without `-c` picks them up. **Every render in tests,
  checks and docs pins `-c src/menkyo/example.toml`** (or a config written
  by the test). Tests must also isolate `HOME` / `XDG_CONFIG_HOME` so the
  per-user file is never read.
- Never commit `dojo.toml`, `crest/`, `ref/`, `build/` or any rendered
  certificate carrying a real name.

## Layout & rules

- `src/menkyo/` is the package (everything the wheel ships). `src/gui.py`,
  `web/`, `packaging/`, `deploy/` build on it and are not in the wheel.
- The generator keeps its state in module globals (`CFG`, `BUILD`,
  `PROGRESS`); one run at a time per process.
- Inkscape renders, Ghostscript converts for `--press`. Neither is installed
  on the Mac; use the Docker test image for real renders (see Commands).
- Python 3.11+ (`tomllib`). Match the surrounding code: its comment density,
  docstring tone and naming. No formatter is applied to existing code.
- The version lives only in `pyproject.toml`.

## Commands

```sh
uv run menkyo -c src/menkyo/example.toml --list   # what a build would write
uv run pytest                                      # tests; renders skip without Inkscape
uv build                                           # wheel + sdist into dist/
```

Releases: bump `pyproject.toml`, commit, the user tags `vX.Y.Z` and pushes;
`.github/workflows/package.yml` tests and publishes.
